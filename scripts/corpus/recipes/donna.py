"""The two "donna" curve25519 libraries - ed25519-donna and curve25519-donna.

Backlog issues #48 (floodyberry/ed25519-donna, "Tor's signature core under a
renamed symbol set") and #50 (agl/curve25519-donna, "named behind a malware
key-generation routine"). One module for both because they share a build
shape - one C file compiled straight into a shared object, no build system -
and because the same four toolchains and the same flags serve both; the Linux
recipes sit beside the MinGW ones rather than in a `*_linux.py` module because
they differ from them by exactly `-fPIC -fvisibility=hidden`.

Existing coverage, checked before building. data/cryptopp already carries part
of ed25519-donna: Crypto++ 8.x ships a C++ port of it as `CryptoPP::Donna::
Ed25519`, with the same function names (`curve25519_square_times`,
`barrett_reduce256_modm`, `contract256_slidingwindow_modm`, ...). Measured
against data/cryptopp 8.9.0 MinGW, 8 of this recipe's 30 named functions of
ten instructions or more share a PicHash on x64 and 11 of 32 on x86 (5 and 6
for the SSE2 build); against Crypto++'s MSVC build, none. What Crypto++ does
not have is the public API (`ed25519_publickey`, `_sign`, `_sign_open`,
`_sign_open_batch`), `ge25519_pack`, `ge25519_unpack_negative_vartime`, the
hash and the 32-bit-on-64 selection, and it has no Linux artefact at all. None
of agl's curve25519-donna is in it: against the 6 or 7 named functions here the
overlap with Crypto++, libsodium and libtomcrypt is zero apart from the
unnamed libgcc `___chkstk_ms` the baseline already knows about. libsodium has
no donna at all - its ed25519 is ref10 and its curve25519 is the 51-bit
`fe51` code. So #48 is built in full and the overlap is recorded rather than
avoided, and #50 is built as a separate project whose code is not in the
corpus.

ed25519-donna
=============
The repository has no tags or releases; HEAD of master (2015-03-16,
8757bd4cd209cb032853ece0ce413f122eef212c) is the pin and the version is its
date. There is no build system either, only the README's compile lines, so the
build is `ed25519.c` compiled straight into a shared object. Two things the
recipe has to settle:

* The hash. Upstream defaults to OpenSSL's SHA-512 and offers
  `-DED25519_REFHASH`, a slow in-tree implementation "that should never be used
  except to verify the code works". That is what is built: it adds
  `sha512_blocks`, `ed25519_hash_init/update/final` and `ed25519_hram` to the
  artefact, which Tor does not have (it substitutes its own digest through
  `ED25519_CUSTOMHASH`), so a sample linked against Tor's donna will match on
  everything else and not on those. The alternative was a dependency on
  libcrypto, whose functions would then be filed under this name.
* The random source. `-DED25519_CUSTOMRANDOM` leaves
  `ed25519_randombytes_unsafe` to the consumer, and upstream's
  `ed25519-randombytes-custom.h` is a comment. A shared object keeps an
  undefined symbol and a PE DLL does not link, so
  `scripts/corpus/exercisers/ed25519_donna_rng.c` defines it, outside the
  upstream tree and compiled beside `ed25519.c`. It is `memset`, which becomes
  a jump into the C runtime and is well under the ten-instruction floor; an
  earlier trial version with a byte loop was 11 instructions on x86 and would
  have sat at the cross-family floor under this family's name.

`ED25519_SUFFIX` (which gives Tor's `ed25519_publickey_donna` names) is not
set in the generic components: it changes symbol names and nothing about the
code, and the plain names are what upstream ships. The Tor-style build is a
separate component (`ed25519-donna-tor`, recipes `ed25519-donna_2015-03-16_tor`
and `_tor_linux`, and `_tor_msvc` in donna_msvc.py): the flags Tor's
src/ext/include.am passes - `-DED25519_CUSTOMHASH -DED25519_CUSTOMRANDOM
-DED25519_SUFFIX=_donna` - with the digest supplied by
scripts/corpus/exercisers/ed25519_donna_tor_hash.h. Upstream's reference
SHA-512 (what ED25519_REFHASH selects, taken from the unmodified
ed25519-hash.h) is renamed `donna_ref_*` and wrapped in Tor's shape, a
heap-allocated digest behind a one-pointer context, and forced in with
`-include` because upstream's own `ed25519-hash-custom.h` is an empty comment
that the compiler finds before any `-I`. It stands in for Tor's digest (a
`crypto_digest_t` over libcrypto or NSS) and nothing in the upstream tree is
edited. The random hook `ed25519_randombytes_unsafe_donna` is the memset stub
under `-DED25519_RNG_NAME`. Measured against the same-target plain
(REFHASH) build, PicHashes at ten instructions or more are shared 29 of 33 on
MinGW x86, 29 of 31 on MinGW x64, 21 of 36 on Linux x86 and 27 of 30 on Linux
x64: the field and group arithmetic is the same code, and what differs is the
digest wrapper and the callers of the digest. Tor's own
`ed25519_tor.c` is built as well, from the Tor tree, as version
`2026-10-07-tor` (next section).

Tor's ed25519_tor.c
===================
Tor does not compile floodyberry's `ed25519.c`. Its `src/ext/include.am`
builds `libed25519_donna.a` from one file, `src/ext/ed25519/donna/
ed25519_tor.c`, with `@CFLAGS_CONSTTIME@ -DED25519_CUSTOMRANDOM
-DED25519_CUSTOMHASH -DED25519_SUFFIX=_donna` (CFLAGS_CONSTTIME is
`-fwrapv` in configure.ac), against Tor's own copies of the donna headers in
the same directory (README.tor lists Tor's edits: the API reworked to match
ref10, the expanded secret key, multiplicative key blinding, the curve25519
to ed25519 conversion, a static random hook calling Tor's crypto_rand, SSE2
forced on 32-bit x86 when `__SSE2__` is set). Recipes
`ed25519-donna_2026-10-07-tor` (MinGW) and `_tor_linux` (Linux) build exactly
that file from the Tor tree pinned at commit
8dbbbe6e86a6ca0d058ec3c6a4e937859857d7bb (2026-10-07, `AC_INIT([tor],
[0.5.0.0-alpha-dev])`; a depth-1 git fetch of gitlab.torproject.org works,
the GitLab raw route returns 403, and the GitHub mirror holds only a README).
The same pin is the one recorded for tracker issues #30 (Tor) and #49
(Equi-X/HashX, src/ext/equix), so a later build of either can reuse it. Two
components: `ed25519_tor` with Tor's flags, and `ed25519_tor-sse2` with
`-DED25519_SSE2 -msse2` added (what Tor's portable header forces on 32-bit x86
whenever the target has SSE2; built on x64 too, like the floodyberry SSE2
component). The version is the commit date, so the rows sort next to the
2015-03-16 floodyberry builds they derive from.

ed25519_tor.c reaches the rest of Tor through `orconfig.h`, five
lib/crypt_ops and lib/cc headers, and eight functions. The headers are used
unmodified from the pinned tree (`-Isrc`). What configure would generate and
what libcrypto/NSS would provide comes from a shim OUTSIDE the tree,
`scripts/corpus/exercisers/ed25519_tor_shim/`: `orconfig.h` (type sizes and
four feature tests, the values configure finds on these targets) and
`ed25519_tor_shim.c`, which defines `crypto_digest512_new`,
`crypto_digest_add_bytes`, `crypto_digest_get_digest`, `crypto_digest_free_`
and `crypto_digest512` over donna's reference SHA-512 (the code
`-DED25519_REFHASH` selects in the same tree's `ed25519-hash.h`, renamed
`corpus_sha512_*`; `sha512_blocks` keeps its name), `crypto_rand_unmocked` and
`crypto_strongest_rand` over `corpus_os_random` (`BCryptGenRandom`, linked
with `-lbcrypt`, on Windows; `/dev/urandom` on Linux), and `memwipe` (memset
through a volatile pointer). None of it runs, and none of it is Tor's: 7 or 8
distinct PicHashes of ten instructions or more per image are these shim
functions, named so they can be set aside. No file of the Tor tree is edited,
so the images are Tor's glue as Tor compiles it, with a stand-in digest and
random source.

Measured, kept + removed = total and, at ten instructions or more, functions /
distinct PicHashes: MinGW x86 56 + 53 = 109, 48/47 (SSE2 58 + 52 = 110,
50/49); MinGW x64 61 + 53 = 114, 47/46 (SSE2 66 + 53 = 119, 51/50); Linux x86
84 + 5 = 89, 50/50 (SSE2 89 + 5 = 94, 52/52); Linux x64 73 + 5 = 78, 44/44
(SSE2 80 + 5 = 85, 50/50). Overlap with the floodyberry-tree Tor-style
component (`ed25519-donna-tor`) of the same target, distinct PicHashes of ten
instructions or more: 21 of its 33 (MinGW x86), 24 of 31 (MinGW x64), 15 of 36
(Linux x86) and 21 of 30 (Linux x64); the SSE2 components share 25 of 34
(MinGW x86), 26 of 34 (MinGW x64), 11 of 38 (Linux x86) and 25 of 34 (Linux
x64) with the floodyberry SSE2 build. Leaving out the shim and the GCC glue,
17 to 30 distinct PicHashes per image are in none of the three floodyberry
components of the same target: the Tor API itself (`ed25519_donna_seckey`,
`_seckey_expand`, `_pubkey`, `_keygen`, `_sign`, `_open`,
`_blind_secret_key`, `_blind_public_key`, `_pubkey_from_curve25519_pubkey`,
`_scalarmult_with_group_order`, `_selftest`), `ed25519_hram` and
`ed25519_sign_open(_batch)_donna` as Tor's copy compiles them, and donna
internals whose inlining differs in Tor's translation unit
(`contract256_modm`, `contract256_slidingwindow_modm`,
`ge25519_double_scalarmult_vartime`, `ge25519_unpack_negative_vartime`,
`ge25519_scalarmult_base_niels`, and further `curve25519_*`/`ge25519_*`
helpers on x86). So the Tor glue adds coverage beyond `ed25519-donna-tor` and
is kept beside it; `ed25519-donna-tor` remains the reference for
floodyberry's `ed25519.c` built with Tor's flags. MSVC is in donna_msvc.py.

Force-inline measurement, which the issue asked for. donna defines
`DONNA_INLINE` as `inline __attribute__((always_inline))` on GCC, and the
field arithmetic in `curve25519-donna-*.h` and the group and modm routines all
go through it, so the question was whether the compiler would leave few
distinct functions. It does not. At -O2 the generic build keeps 30 named
functions of ten or more instructions on x64 and 32 on x86 (33 for SSE2), and
-O0, which still honours always_inline, keeps 62 and 64. Removing the
attribute from a scratch copy, which is not what is built, moves the -O2 count
to 29 on x64 and by one on x86, and the -O3 count from 36 to 34 on x64 and not
at all on x86: at most two functions appear or disappear (`ge25519_add`,
`ge25519_double` and `ge25519_double_partial` stay out of line when forced and
are folded in when not, `curve25519_mul` and `ge25519_add_p1p1` the other way
round), and 19 to 30 of the bodies hash identically either way. The large
field and group functions are `static` and called from several places, and
GCC evidently keeps them as functions at -O2 whether forced or not. The floor
of eight is cleared nearly four times over, with or without the attribute.

Variants, each measured. Generic means the unmodified build: `ED25519_64BIT`
(`__int128`) on x64, the 32-bit code on x86. `-DED25519_SSE2` selects separate
SSE2 field arithmetic: 9 of 33 hashes are shared with the generic build on
MinGW x86 and 13 of 31 on x64 (6 and 12 on Linux), so it is a different code
shape for the majority of its functions, and it is built as a second component.
Upstream's own benchmark has it four times faster than the 32-bit generic code
and slower than the 64-bit generic code, so it is a likely choice on x86 and
an unlikely but documented one on x64; it is built for both rather than
guessing. `-DED25519_FORCE_32BIT` on x64 (the 32-bit code with a 64-bit
`choose`) is not built: nothing in the README or the benchmark recommends it.

Optimisation level. One level, -O2, like the rest of the corpus and like the
probes the baseline is measured with. How much that matters was measured so it
is on record: the -O2 and -O3 builds share 11 of 30 hashes on x64 and 14 of 33
on x86, -Os shares 4 and 0, and -O0 and -O1 share none. A binary built at a
different level will match this data only partially; an -O3 axis was not added
because nothing here says donna is commonly built that way.

Operating systems. MinGW x86, MinGW x64, Linux ELF x86 and Linux ELF x64 are
built, all four because they were measured to differ. MinGW x64 and Linux x64
share no hash at all (0 of 30, 0 of 34): the Microsoft x64 and System V calling
conventions put the arguments in different registers, so every function
differs. On x86 the same calling convention is used but PIC code reaches data
through the GOT: 3 of 33 shared. Linux is plausible for this code - Tor ships
it there, and a small dependency-free routine like this is the kind Linux
malware embeds (a judgement, not something measured here). A
macOS (Mach-O) axis is not built: there is no Darwin toolchain on this host and
none is faked.

MSVC is a follow-up and is not written here. Both libraries are plain C that
`cl` accepts (`ed25519-donna-portable.h` has a full MSVC branch with
`_umul128` and `__forceinline` in place of `__int128` and `always_inline`), and
the README's own argument is that most Windows software an analyst meets is
MSVC-built, so it is the most valuable remaining axis; it needs the Windows
runner.

curve25519-donna
================
agl/curve25519-donna, tag 1.3 (pinned by the commit it names,
28772f37a4b8a57ab9439b9e79b19f9abee686da, 2015-02-08; the three later commits
change only the README). The Makefile builds `curve25519-donna.c` with
`gcc -O2 -m32` and `curve25519-donna-c64.c` with `gcc -O2`, and the recipe
does the same. Only the first is built.

Thin, and the recipe says so as 4g3nt47/Obfuscator's does. The 32-bit file keeps
20 named functions at -O0 and 6 to 7 of them survive -O2 as separate functions
in the image - `fsum`, `fproduct`, `freduce_degree`, `freduce_coefficients`,
`fsquare_inner` and `curve25519_donna` on x64, plus `swap_conditional` on x86 -
because the rest are folded into `curve25519_donna`, a
instruction function (1,484 to 1,702 instructions). That is under the floor of eight, and the artefacts only
reach eight by counting `___chkstk_ms` and nine import thunks on MinGW x64, or
PLT stubs on Linux, which are not this project. So `min_functions` is six, the
count measured on the x64 builds (6 named, own functions on MinGW and on Linux
alike; 7 on both x86 builds), and not a number chosen to let a build through:
an artefact that came out below six would still fail. The lowest-count x64
reports hold 16 and 10 functions in total, of which 6 are the project's.

The 64-bit `curve25519-donna-c64.c` is built as a second, x64-only component
(`curve25519-donna-c64`, recipes `curve25519-donna_1.3_c64` and `_c64_linux`).
It does not compile for x86 (`__attribute__((mode(TI)))` is unavailable), and
it is thin: -O2 leaves `curve25519_donna` (5,553 instructions on MinGW x64,
5,540 on Linux x64) and a two-instruction `load_limb`, so 1 function of ten
instructions or more against a floor of eight. At -O1 it is 4, at -Os 2 and at
-O0 9, which are not the compiler of a real sample. Its `force_inline` macro
is the same story - with the attribute removed from a scratch copy it is two
functions (`fmul` separates) - so the thinness is the file, not the inlining.
It was first left out for exactly that reason and is built now because the
project genuinely has two functions here and a sample that vendors the 64-bit
file matches nothing else in the corpus. `min_functions` is therefore 2, the
measured count of the project's own functions in both artefacts, stated in
the recipe: the floor of eight is reached on MinGW only by the unnamed
`___chkstk_ms` and nine one-instruction import jump stubs (12 kept + 50
removed = 62), and not on Linux (6 kept + 6 removed = 12, the four others
being two- and three-instruction PLT stubs). The count is the file's, not a
number picked to let a build through; a build that came out with fewer than
two would still fail. No PicHash of ten instructions or more is shared with
the 32-bit build apart from `___chkstk_ms`.

The two projects do not share code, as the issues expected only that they
"share ideas". Measured PicHash overlap at ten instructions or more between
curve25519-donna and ed25519-donna is zero on all four targets, apart from
`___chkstk_ms` on MinGW. ed25519-donna's `curve25519-donna-*.h` are
derivatives of agl's but were rewritten around different function names and
limb handling (`curve25519_mul`, `curve25519_square_times` against `fproduct`,
`fsquare_inner`).

What is not covered, honestly: Mach-O, the digest Tor really uses, and the -O3 and -Os builds of either. (MSVC is donna_msvc.py.) Everything stripped by a malware author is
also not covered: these are unstripped, with symbols, like the rest of the
corpus.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_ED_COMMIT = "8757bd4cd209cb032853ece0ce413f122eef212c"
_CV_COMMIT = "28772f37a4b8a57ab9439b9e79b19f9abee686da"

_RNG = "{repo}/scripts/corpus/exercisers/ed25519_donna_rng.c"
# {archflag} is -m32/-m64 for the native compiler and empty for the MinGW
# cross compilers. The two %s are the position-independence flags and the SSE2
# switches; the third is the output name.
_ED = ("{cc} {archflag} -O2 %s -shared -DED25519_REFHASH "
       "-DED25519_CUSTOMRANDOM %s -I. -o %s ed25519.c " + _RNG)
_CV = "{cc} {archflag} -O2 %s -shared -o %s curve25519-donna.c"

# Tor's build of the same files (src/ext/include.am): ED25519_CUSTOMHASH with
# its own digest in ed25519-hash-custom.h, ED25519_CUSTOMRANDOM, and every
# public symbol suffixed _donna. The digest is supplied by a header outside the
# upstream tree, forced in with -include because upstream's own
# ed25519-hash-custom.h is an empty comment that the compiler finds first.
_TOR_HASH = "{repo}/scripts/corpus/exercisers/ed25519_donna_tor_hash.h"
_TOR_FLAGS = ("-DED25519_CUSTOMHASH -DED25519_CUSTOMRANDOM "
              "-DED25519_SUFFIX=_donna -include ed25519_donna_tor_hash.h")
_ED_TOR = ("{cc} {archflag} -O2 %s -shared " + _TOR_FLAGS
           + " -DED25519_RNG_NAME=ed25519_randombytes_unsafe_donna"
           " -I{repo}/scripts/corpus/exercisers -I. -o %s ed25519.c " + _RNG)

_PIC = "-fPIC -fvisibility=hidden"


def _ed25519(linux):
    pic = _PIC if linux else ""
    ext = "so" if linux else "dll"
    plain = "ed25519-donna." + ext
    sse2 = "ed25519-donna-sse2." + ext
    tor = "ed25519-donna-tor." + ext
    return Recipe(
        family="ed25519-donna",
        version="2015-03-16",
        upstream="https://github.com/floodyberry/ed25519-donna",
        license="public domain, as declared in the header of each source "
                "file (Andrew M.); the repository ships no licence file",
        source=Source(git_url="https://github.com/floodyberry/ed25519-donna.git",
                      git_ref=_ED_COMMIT),
        build=[BuildStep(_ED % (pic, "", plain)),
               BuildStep(_ED % (pic, "-DED25519_SSE2 -msse2", sse2)),
               BuildStep(_ED_TOR % (pic, tor))],
        artifacts=[Artifact(path=plain, component=plain),
                   Artifact(path=tor, component=tor,
                            build_flags="-O2 " + ("-fPIC -fvisibility=hidden "
                                                  if linux else "")
                                        + _TOR_FLAGS),
                   Artifact(path=sse2, component=sse2,
                            build_flags="-O2 -DED25519_SSE2 -msse2 "
                                        + ("-fPIC -fvisibility=hidden "
                                           if linux else "")
                                        + "-DED25519_REFHASH "
                                          "-DED25519_CUSTOMRANDOM")],
        toolchains=["linux_x86", "linux_x64"] if linux else ["mingw_x86", "mingw_x64"],
        build_flags="-O2 " + ("-fPIC -fvisibility=hidden " if linux else "")
                    + "-DED25519_REFHASH -DED25519_CUSTOMRANDOM",
        notes="The master HEAD of a repository with no releases, built as "
              "ed25519.c compiled straight into a shared object, once as "
              "upstream's default code for the target (32-bit on x86, "
              "__int128 on x64) and once with -DED25519_SSE2. Uses "
              "upstream's reference SHA-512 (ED25519_REFHASH), which Tor "
              "replaces with its own digest, so sha512_blocks and the "
              "ed25519_hash_* functions are not in a Tor build. "
              "ed25519_randombytes_unsafe is the only function not from "
              "upstream: a memset stub in scripts/corpus/exercisers, which "
              "resolves the symbol ED25519_CUSTOMRANDOM leaves open and must "
              "never run. 30 named functions of ten instructions or more "
              "in the generic x64 artefacts, 32 in the x86 ones and 33 in "
              "the SSE2 ones: the DONNA_INLINE force-inlining does not "
              "reduce this - without it the count is within two. "
              "Crypto++ 8.x ships a port of part of this code, so about 8 "
              "(x64) to 11 (x86) of these functions also match "
              "data/cryptopp under its C++ names; libsodium shares none. "
              "ED25519_SUFFIX is not set in the plain and SSE2 components, "
              "so their symbols are ed25519_publickey and not Tor's "
              "ed25519_publickey_donna. The third component, "
              "ed25519-donna-tor, is the Tor-style build: "
              'ed25519.c built the way Tor builds it (src/ext/include.am): '
              '-DED25519_CUSTOMHASH, -DED25519_CUSTOMRANDOM and '
              '-DED25519_SUFFIX=_donna, so every public function is '
              'ed25519_publickey_donna, ed25519_sign_donna, '
              'ed25519_sign_open_donna, ed25519_sign_open_batch_donna and '
              "curved25519_scalarmult_basepoint_donna. Tor's digest "
              '(crypto_digest_t over libcrypto or NSS) is not a dependency a '
              'reference build can have, so the digest is the one '
              'scripts/corpus/exercisers/ed25519_donna_tor_hash.h supplies, '
              "forced in with -include: upstream's own reference SHA-512 (the"
              ' code ED25519_REFHASH selects, from the unmodified '
              'ed25519-hash.h at the pinned commit, its four public names '
              "renamed donna_ref_*) wrapped in Tor's shape, a heap-allocated "
              "digest behind a one-pointer context. Upstream's own "
              'ed25519-hash-custom.h is an empty comment, so nothing in the '
              "upstream tree is changed. It stands in for Tor's digest and "
              "says nothing about what libcrypto's SHA-512 compiles to. "
              'ed25519_randombytes_unsafe_donna is the memset stub of '
              'ed25519_donna_rng.c, named through -DED25519_RNG_NAME, and '
              "must never run. Tor's own ed25519_tor.c, with its "
              "Tor-specific API (_blind_secret_key, _blind_public_key, "
              "_pubkey_from_curve25519_pubkey, ...), is the separate "
              "2026-10-07-tor build from the Tor tree. MinGW x86"
              ' 36 kept + 53 removed = 89, x64 42 + 53 = 95; Linux x86 57 + 5'
              ' = 62, x64 44 + 6 = 50 (33, 31, 36 and 30 functions of ten '
              'instructions or more). Against the same-target REFHASH build '
              '(the plain ed25519-donna component) the PicHashes at ten '
              'instructions or more are shared 29 of 33 (MinGW x86), 29 of 31'
              ' (MinGW x64), 21 of 36 (Linux x86) and 27 of 30 (Linux x64); '
              'what differs is the digest wrapper and the functions that call'
              ' it (sign, hram, sign_open_batch on some targets), so a Tor-'
              'built sample matches this component on the field and group '
              'arithmetic and on the renamed public API, not on the hash.',
    )


_TOR_GLUE_NOTES = (
    "Tor's own ed25519-donna glue, src/ext/ed25519/donna/ed25519_tor.c from "
    "the Tor tree at commit 8dbbbe6e86a6 (2026-10-07, configure AC_INIT "
    "0.5.0.0-alpha-dev; the same pin serves the Tor notes of tracker issues "
    "#30 and #49), compiled with the flags of Tor's src/ext/include.am: "
    "-DED25519_CUSTOMRANDOM -DED25519_CUSTOMHASH -DED25519_SUFFIX=_donna and "
    "CFLAGS_CONSTTIME (-fwrapv), at -O2, against Tor's own copies of the donna "
    "headers in that directory (Tor's edits listed in its README.tor) and "
    "Tor's unmodified lib/ headers. This is Tor's API, not floodyberry's "
    "ed25519.c: ed25519_donna_seckey, _seckey_expand, _pubkey, _keygen, "
    "_open, _sign, _blind_secret_key, _blind_public_key, "
    "_pubkey_from_curve25519_pubkey, _scalarmult_with_group_order and "
    "_selftest, with the expanded secret key. The second component adds "
    "-DED25519_SSE2 -msse2 (what Tor's ed25519-donna-portable.h forces on "
    "32-bit x86 whenever __SSE2__ is set). Tor's crypto entry points are "
    "supplied OUTSIDE the tree by scripts/corpus/exercisers/ed25519_tor_shim/: "
    "orconfig.h stands in for configure's output (type sizes and four "
    "feature tests), and ed25519_tor_shim.c defines crypto_digest512_new, "
    "crypto_digest_add_bytes, crypto_digest_get_digest, crypto_digest_free_, "
    "crypto_digest512 (donna's reference SHA-512 from the same tree's "
    "ed25519-hash.h, renamed corpus_sha512_*), crypto_rand_unmocked and "
    "crypto_strongest_rand (BCryptGenRandom on Windows, /dev/urandom on "
    "Linux, through corpus_os_random) and memwipe. Those shim functions, "
    "and sha512_blocks, are not Tor's code and never run. No file of the "
    "Tor tree is edited. Measured at ten instructions or more: 15 to 24 "
    "distinct PicHashes shared with the same-target ed25519-donna-tor "
    "component (floodyberry's ed25519.c with Tor's flags), 11 to 26 between "
    "the SSE2 components, and 17 to 30 per image, the shim and GCC glue "
    "left out, in none of the floodyberry components: the Tor API and the "
    "donna internals as Tor's translation unit inlines them. Counts per "
    "image are in the recipe docstring."
)


# Tor's own glue around donna (src/ext/ed25519/donna/ed25519_tor.c), built from
# the Tor tree at a pinned commit with the flags of src/ext/include.am; see the
# "Tor's ed25519_tor.c" section of the module docstring.
_TOR_COMMIT = "8dbbbe6e86a6ca0d058ec3c6a4e937859857d7bb"
_TOR_SHIM = "{repo}/scripts/corpus/exercisers/ed25519_tor_shim"
_TOR_GLUE_FLAGS = ("-DED25519_CUSTOMRANDOM -DED25519_CUSTOMHASH "
                   "-DED25519_SUFFIX=_donna")
_TOR_GLUE = ("{cc} {archflag} -O2 -fwrapv %s -shared " + _TOR_GLUE_FLAGS
             + " %s -I" + _TOR_SHIM + " -Isrc -Isrc/ext/ed25519/donna -o %s "
             "src/ext/ed25519/donna/ed25519_tor.c " + _TOR_SHIM
             + "/ed25519_tor_shim.c%s")


def _ed25519_tor_glue(linux):
    pic = _PIC if linux else ""
    ext = "so" if linux else "dll"
    libs = "" if linux else " -lbcrypt"
    plain = "ed25519_tor." + ext
    sse2 = "ed25519_tor-sse2." + ext
    base_flags = ("-O2 -fwrapv " + (_PIC + " " if linux else "")
                  + _TOR_GLUE_FLAGS)
    return Recipe(
        family="ed25519-donna",
        version="2026-10-07-tor",
        upstream="https://gitlab.torproject.org/tpo/core/tor",
        license="BSD-3-Clause (Tor, LICENSE at the pinned commit) for "
                "ed25519_tor.c and Tor's edits; the donna code it includes "
                "is public domain (Andrew M.)",
        source=Source(git_url="https://gitlab.torproject.org/tpo/core/tor.git",
                      git_ref=_TOR_COMMIT),
        build=[BuildStep(_TOR_GLUE % (pic, "", plain, libs)),
               BuildStep(_TOR_GLUE % (pic, "-DED25519_SSE2 -msse2", sse2,
                                      libs))],
        artifacts=[Artifact(path=plain, component=plain),
                   Artifact(path=sse2, component=sse2,
                            build_flags=base_flags
                            + " -DED25519_SSE2 -msse2")],
        toolchains=["linux_x86", "linux_x64"] if linux else ["mingw_x86", "mingw_x64"],
        build_flags=base_flags,
        notes=_TOR_GLUE_NOTES,
    )


def _curve25519(linux):
    pic = _PIC if linux else ""
    name = "curve25519-donna." + ("so" if linux else "dll")
    return Recipe(
        family="curve25519-donna",
        version="1.3",
        upstream="https://github.com/agl/curve25519-donna",
        license="BSD-3-Clause, Copyright 2008 Google Inc.",
        source=Source(git_url="https://github.com/agl/curve25519-donna.git",
                      git_ref=_CV_COMMIT),
        build=[BuildStep(_CV % (pic, name))],
        artifacts=[Artifact(path=name, component=name)],
        toolchains=["linux_x86", "linux_x64"] if linux else ["mingw_x86", "mingw_x64"],
        build_flags="-O2 " + ("-fPIC -fvisibility=hidden" if linux else ""),
        # The smallest count of the project's own functions in any artefact,
        # measured: 6 on both x64 builds, 7 on both x86 builds. See the module
        # docstring for why this is the project's real size and not a number
        # picked to admit a build.
        min_functions=6,
        notes="Tag 1.3, the 32-bit curve25519-donna.c, built with the "
              "Makefile's -O2. Thin: 6 to 7 of the file's 20 functions "
              "survive as separate functions (fsum, fproduct, "
              "freduce_degree, freduce_coefficients, fsquare_inner, "
              "curve25519_donna, and swap_conditional on x86), the rest "
              "being folded into curve25519_donna, which is 1,484 to 1,702 "
              "instructions. Below the corpus floor of eight, so the recipe "
              "sets min_functions to 6; on MinGW x64 the report's other 10 "
              "functions are the unnamed ___chkstk_ms and nine import "
              "thunks, and on Linux 4 PLT stubs. The 64-bit "
              "curve25519-donna-c64.c is a separate x64-only component "
              "(curve25519-donna-c64): two functions, curve25519_donna and "
              "load_limb. No code in common with "
              "ed25519-donna or Crypto++'s donna port (measured: no shared "
              "PicHash at ten instructions or more).",
    )


def _curve25519_c64(linux):
    """The 64-bit agl file, x64 only: it needs a 128-bit integer type."""
    pic = _PIC if linux else ""
    name = "curve25519-donna-c64." + ("so" if linux else "dll")
    return Recipe(
        family="curve25519-donna",
        version="1.3-c64",
        upstream="https://github.com/agl/curve25519-donna",
        license="BSD-3-Clause, Copyright 2008 Google Inc.",
        source=Source(git_url="https://github.com/agl/curve25519-donna.git",
                      git_ref=_CV_COMMIT),
        build=[BuildStep("{cc} {archflag} -O2 %s -shared -o %s "
                         "curve25519-donna-c64.c" % (pic, name))],
        artifacts=[Artifact(path=name, component=name)],
        toolchains=["linux_x64"] if linux else ["mingw_x64"],
        build_flags="-O2 " + ("-fPIC -fvisibility=hidden" if linux else ""),
        min_functions=2,
        notes=(
              'Tag 1.3, the 64-bit curve25519-donna-c64.c, x64 only (it needs'
              ' a 128-bit integer: __attribute__((mode(TI))) does not compile'
              " for x86), built with the Makefile's -O2 and no -m32. One "
              'source file that GCC folds to two functions: curve25519_donna '
              '(5,553 instructions on MinGW, 5,540 on Linux) and the two-'
              'instruction load_limb. min_functions is 2, the measured count '
              "of the project's own functions in both artefacts, and not a "
              'number chosen to admit a build: the floor of eight is reached '
              'on MinGW only by the unnamed ___chkstk_ms (PicHash '
              '12578432865501340970) and nine one-instruction import jump '
              'stubs (PicHash 1253497258561142223), none of which is this '
              'project, and not at all on Linux, where 4 two- and three-'
              'instruction PLT stubs take the image to 6. MinGW x64 12 kept +'
              ' 50 removed = 62; Linux x64 6 kept + 6 removed = 12. Shares no'
              ' PicHash of ten instructions or more with the 32-bit '
              'curve25519-donna.c build apart from ___chkstk_ms. The 32-bit '
              'file is the better reference for what the project is."'),
    )


RECIPES = {
    "ed25519-donna_2015-03-16": _ed25519(False),
    "ed25519-donna_2015-03-16_linux": _ed25519(True),
    "ed25519-donna_2026-10-07-tor": _ed25519_tor_glue(False),
    "ed25519-donna_2026-10-07-tor_linux": _ed25519_tor_glue(True),
    "curve25519-donna_1.3": _curve25519(False),
    "curve25519-donna_1.3_linux": _curve25519(True),
    "curve25519-donna_1.3-c64": _curve25519_c64(False),
    "curve25519-donna_1.3-c64_linux": _curve25519_c64(True),
}
