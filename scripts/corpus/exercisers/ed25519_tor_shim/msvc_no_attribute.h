/* Forced in (/FI) by the MSVC build of Tor's digest code only
 * (ed25519-donna_2026-10-07-tor-openssl_msvc). Tor does not build with cl:
 * src/ext/keccak-tiny/keccak-tiny.h declares keccak_state with GCC's
 * __attribute__((aligned(8))), which cl rejects, and cl's /D cannot define a
 * function-like macro. Removing the attribute here, outside the Tor tree, is
 * the command-line equivalent; the struct takes cl's natural alignment. */
#ifndef CORPUS_MSVC_NO_ATTRIBUTE_H
#define CORPUS_MSVC_NO_ATTRIBUTE_H
#define __attribute__(x)
#endif
