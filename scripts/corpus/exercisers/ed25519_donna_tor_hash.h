/* The digest of the Tor-style ed25519-donna build, outside the upstream tree.
 *
 * Tor builds floodyberry's ed25519-donna with -DED25519_CUSTOMHASH and puts
 * its own ed25519-hash-custom.h in the tree (src/ext/ed25519/donna/), which
 * implements the four-function digest interface upstream documents in the
 * comment of its own ed25519-hash-custom.h: a context that is a pointer to a
 * digest object, ed25519_hash_init/_update/_final over it, and one-shot
 * ed25519_hash. In Tor the object is a crypto_digest_t and the SHA-512 behind
 * it is libcrypto's or NSS's. Neither is a dependency a reference build can
 * have, and upstream's file is a comment that `#include "ed25519-hash-
 * custom.h"` finds before any -I directory, so this header is forced in with
 * -include and the comment is then harmless.
 *
 * The digest implementation is upstream's own reference SHA-512, the one
 * -DED25519_REFHASH selects, taken from the unmodified ed25519-hash.h at the
 * pinned commit: it is included here with its four public names renamed
 * (donna_ref_*) and REFHASH set only for that one include, then wrapped in
 * Tor's shape - a heap-allocated digest behind a one-pointer context, freed
 * in _final. Nothing in the upstream tree is edited. It is a stand-in for
 * Tor's digest, and says nothing about what libcrypto's SHA-512 compiles to.
 * Never run; only disassembled.
 */
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define ED25519_REFHASH
#define ed25519_hash_context donna_ref_context
#define ed25519_hash_init    donna_ref_init
#define ed25519_hash_update  donna_ref_update
#define ed25519_hash_final   donna_ref_final
#define ed25519_hash         donna_ref_hash
#include "ed25519-hash.h"
#undef ed25519_hash_context
#undef ed25519_hash_init
#undef ed25519_hash_update
#undef ed25519_hash_final
#undef ed25519_hash
#undef ED25519_REFHASH

typedef struct ed25519_hash_context {
	donna_ref_context *ctx;
} ed25519_hash_context;

static void
ed25519_hash_init(ed25519_hash_context *ctx) {
	ctx->ctx = (donna_ref_context *)malloc(sizeof(donna_ref_context));
	donna_ref_init(ctx->ctx);
}

static void
ed25519_hash_update(ed25519_hash_context *ctx, const uint8_t *in, size_t inlen) {
	donna_ref_update(ctx->ctx, in, inlen);
}

static void
ed25519_hash_final(ed25519_hash_context *ctx, uint8_t *hash) {
	donna_ref_final(ctx->ctx, hash);
	free(ctx->ctx);
	ctx->ctx = NULL;
}

static void
ed25519_hash(uint8_t *hash, const uint8_t *in, size_t inlen) {
	donna_ref_hash(hash, in, inlen);
}
