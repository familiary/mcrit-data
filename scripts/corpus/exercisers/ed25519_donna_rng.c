/* The one function ed25519-donna leaves for its consumer to supply.
 *
 * ed25519.c is the whole library, but with ED25519_CUSTOMRANDOM it declares
 * ed25519_randombytes_unsafe - batch verification draws its random scalars
 * from it - and expects the including project to define it; upstream's
 * ed25519-randombytes-custom.h is a comment and nothing else. Without a
 * definition a shared object has an undefined symbol, and a PE DLL does not
 * link at all. The default alternative is OpenSSL's RAND_bytes, which would
 * put a dependency on libcrypto in front of a reference build.
 *
 * This lives outside the upstream tree and is compiled beside ed25519.c, the
 * way the C++ exercisers here consume their libraries. It zero-fills, so it
 * must never run: it exists to resolve a symbol in a binary that is only
 * ever disassembled. Written as memset so it compiles to a jump into the C
 * runtime at -O2 rather than to a loop of its own - a loop of ten
 * instructions would sit at the corpus's cross-family floor and be filed
 * under ed25519-donna's name as if it were upstream code.
 */
#include <stddef.h>
#include <string.h>

/* ED25519_SUFFIX renames the hook the library calls (ed25519_randombytes_
 * unsafe_donna in the Tor-style build), so that build names the stub with
 * -DED25519_RNG_NAME; every other build defines the upstream name. */
#ifndef ED25519_RNG_NAME
#define ED25519_RNG_NAME ed25519_randombytes_unsafe
#endif

void ED25519_RNG_NAME(void *out, size_t count) {
	memset(out, 0, count);
}
