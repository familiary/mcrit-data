/* Entry points for the ed25519-donna "2026-10-07-tor-openssl" build, outside
 * the Tor tree.
 *
 * That build compiles Tor's own digest code - src/lib/crypt_ops/
 * crypto_digest_openssl.c and crypto_digest.c, with Tor's keccak-tiny, its
 * lib/malloc/malloc.c and lib/crypt_ops/crypto_util.c (memwipe) - against a
 * pinned OpenSSL libcrypto, so the digest behind ed25519_tor.c is Tor's
 * crypto_digest_t over libcrypto rather than the stand-in of
 * ed25519_tor_shim.c. What Tor's code still calls and that build does not
 * compile is here: the random source (Tor's crypto_rand.c pulls in the whole
 * of its PRNG and OpenSSL/NSS RAND machinery) and the assertion and bug
 * reporters of lib/log/util_bug.c and lib/err/torerr.c (which pull in Tor's
 * logging). None of these is Tor's code, each is named so it can be set
 * aside, and none must ever run: this file exists only so the image links.
 */
#include "orconfig.h"

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
#include <bcrypt.h>
static void
corpus_os_random(void *out, size_t len)
{
	if (BCryptGenRandom(NULL, (PUCHAR)out, (ULONG)len,
	                    BCRYPT_USE_SYSTEM_PREFERRED_RNG) != 0)
		abort();
}
#else
#include <stdio.h>
static void
corpus_os_random(void *out, size_t len)
{
	FILE *f = fopen("/dev/urandom", "rb");
	if (!f || fread(out, 1, len, f) != len)
		abort();
	fclose(f);
}
#endif

void
crypto_rand_unmocked(char *to, size_t n)
{
	corpus_os_random(to, n);
}

void
crypto_strongest_rand(uint8_t *out, size_t out_len)
{
	corpus_os_random(out, out_len);
}

void
tor_assertion_failed_(const char *fname, unsigned int line,
                      const char *func, const char *expr,
                      const char *fmt, ...)
{
	(void)fname; (void)line; (void)func; (void)expr; (void)fmt;
	abort();
}

void
tor_bug_increment_count_(void)
{
}

void
tor_bug_occurred_(const char *fname, unsigned int line,
                  const char *func, const char *expr,
                  int once, const char *fmt, ...)
{
	(void)fname; (void)line; (void)func; (void)expr; (void)once; (void)fmt;
	abort();
}

#ifdef _WIN32
/* util_bug.h makes SHORT_FILE__ a call to this on Windows only. */
const char *
tor_fix_source_file(const char *fname)
{
	return fname;
}
#endif

void
tor_abort_(void)
{
	abort();
}

void
tor_raw_abort_(void)
{
	abort();
}

void
tor_raw_assertion_failed_msg_(const char *file, int line,
                              const char *expr, const char *msg)
{
	(void)file; (void)line; (void)expr; (void)msg;
	abort();
}
