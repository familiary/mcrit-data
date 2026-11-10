/* Stand-in for the orconfig.h Tor's configure generates, outside the Tor tree.
 *
 * The ed25519-donna Tor glue (src/ext/ed25519/donna/ed25519_tor.c at Tor
 * commit 8dbbbe6) includes "orconfig.h" and, through it, Tor's own
 * lib/cc/compat_compiler.h, lib/cc/torint.h, lib/crypt_ops/crypto_digest.h,
 * crypto_rand.h and crypto_util.h, which are used unmodified from the pinned
 * tree (-Isrc). Those headers only ask the type sizes and a handful of
 * feature tests below; running Tor's configure for them would need libevent,
 * OpenSSL and zlib on the build host and would change nothing in the object
 * code of this one file. The values are what configure finds on the four
 * targets (x86/x64, PE and ELF). Nothing in the Tor tree is edited.
 */
#ifndef CORPUS_TOR_ORCONFIG_H
#define CORPUS_TOR_ORCONFIG_H

#if defined(_WIN64) || defined(__x86_64__) || defined(__LP64__)
#define SIZEOF_VOID_P 8
#define SIZEOF_SIZE_T 8
#else
#define SIZEOF_VOID_P 4
#define SIZEOF_SIZE_T 4
#endif
#define SIZEOF_INT 4
#define SIZEOF_SHORT 2
#define SIZEOF_LONG_LONG 8
#define SIZEOF_INT64_T 8
#if defined(_WIN32) || !defined(__LP64__)
#define SIZEOF_LONG 4
#else
#define SIZEOF_LONG 8
#endif
#if defined(_WIN32) || defined(__x86_64__)
#define SIZEOF_TIME_T 8
#else
#define SIZEOF_TIME_T 4
#endif

#define HAVE_SYS_TYPES_H 1
#if !defined(_MSC_VER)
#define HAVE_SSIZE_T 1
#endif
#if defined(_MSC_VER)
#define HAVE_MACRO__FUNCTION__ 1
#else
#define HAVE_MACRO__func__ 1
#endif
#define NULL_REP_IS_ZERO_BYTES 1
#define DOUBLE_0_REP_IS_ZERO_BYTES 1
#define USING_TWOS_COMPLEMENT 1

#endif /* CORPUS_TOR_ORCONFIG_H */
