/* The Tor library entry points ed25519_tor.c calls, outside the Tor tree.
 *
 * Tor's ed25519-donna glue (src/ext/ed25519/donna/ed25519_tor.c at commit
 * 8dbbbe6, built with -DED25519_CUSTOMRANDOM -DED25519_CUSTOMHASH
 * -DED25519_SUFFIX=_donna as src/ext/include.am does) reaches the rest of Tor
 * through six functions: the digest hooks of its ed25519-hash-custom.h
 * (crypto_digest512_new, crypto_digest_add_bytes, crypto_digest_get_digest,
 * crypto_digest_free_ and crypto_digest512), the random hooks of
 * ed25519-randombytes-custom.h and of ed25519_donna_seckey
 * (crypto_rand_unmocked, crypto_strongest_rand), and memwipe. In Tor they are
 * lib/crypt_ops over libcrypto or NSS. A reference build cannot link either
 * without filing their code under this family, so this file supplies them with
 * the prototypes of Tor's own unmodified headers:
 *
 * - SHA-512 is donna's reference implementation, the code -DED25519_REFHASH
 *   selects in the pinned tree's own src/ext/ed25519/donna/ed25519-hash.h,
 *   included here with its names renamed (corpus_sha512_*), behind Tor's
 *   heap-allocated crypto_digest_t.
 * - The random source is the operating system's: BCryptGenRandom on Windows,
 *   /dev/urandom elsewhere. Failure aborts, as Tor's does.
 * - memwipe is memset through a volatile function pointer.
 *
 * Never run; the artefact is only disassembled. Nothing here is Tor code, and
 * these functions are listed in the recipe so they can be told apart from it.
 */
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "lib/crypt_ops/crypto_digest.h"
#include "lib/crypt_ops/crypto_rand.h"
#include "lib/crypt_ops/crypto_util.h"

#define ED25519_REFHASH
#define ed25519_hash_context corpus_sha512_context
#define ed25519_hash_init    corpus_sha512_init
#define ed25519_hash_update  corpus_sha512_update
#define ed25519_hash_final   corpus_sha512_final
#define ed25519_hash         corpus_sha512
#include "ed25519-hash.h"
#undef ed25519_hash_context
#undef ed25519_hash_init
#undef ed25519_hash_update
#undef ed25519_hash_final
#undef ed25519_hash
#undef ED25519_REFHASH

struct crypto_digest_t {
	corpus_sha512_context state;
};

crypto_digest_t *
crypto_digest512_new(digest_algorithm_t algorithm)
{
	crypto_digest_t *d = (crypto_digest_t *)malloc(sizeof(*d));
	(void)algorithm;
	if (!d)
		abort();
	corpus_sha512_init(&d->state);
	return d;
}

void
crypto_digest_add_bytes(crypto_digest_t *digest, const char *data, size_t len)
{
	corpus_sha512_update(&digest->state, (const uint8_t *)data, len);
}

void
crypto_digest_get_digest(crypto_digest_t *digest, char *out, size_t out_len)
{
	corpus_sha512_context copy = digest->state;
	uint8_t full[64];
	corpus_sha512_final(&copy, full);
	memcpy(out, full, out_len < sizeof(full) ? out_len : sizeof(full));
}

void
crypto_digest_free_(crypto_digest_t *digest)
{
	free(digest);
}

int
crypto_digest512(char *digest, const char *m, size_t len,
                 digest_algorithm_t algorithm)
{
	(void)algorithm;
	corpus_sha512((uint8_t *)digest, (const uint8_t *)m, len);
	return 0;
}

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

static void *(*volatile corpus_memset)(void *, int, size_t) = memset;

void
memwipe(void *mem, uint8_t byte, size_t sz)
{
	corpus_memset(mem, byte, sz);
}
