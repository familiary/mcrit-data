"""Argon2 - the P-H-C reference implementation (Password Hashing Competition).

Pinned to the 20190702 release tag (commit
62358ba2123abd17fccf2a108a301d4b52c01a7c, verified with ls-remote). It is the
last tag upstream cut and what every distro and vendoring project means by
"argon2".

Relation to ``data/libsodium``: libsodium carries its own, independently
maintained copy of Argon2 (``crypto_pwhash/argon2``: argon2-core.c,
argon2-fill-block-ref.c, -ssse3.c, -avx2.c, -avx512f.c, argon2-encoding.c,
blake2b-long), written against the same specification and derived from this
code. The two were measured against each other rather than assumed to match;
the overlap and the numbers are in ``notes`` below and in the pull request.
Because the code is spec-derived and shares its structure, a hit on one is a
lead for the other, but a binary statically linking the standalone library is
only matched exactly by this family.

Decisions, each measured on the 20190702 tree:

* **opt, not ref.** The Makefile picks ``src/opt.c`` (SSE2/SSSE3/AVX
  intrinsics) when ``$(CC) -march=$(OPTTARGET) src/opt.c`` compiles, and falls
  back to the portable ``src/ref.c`` otherwise. Anything built with the
  stock ``make`` or from the upstream ``vs2015`` project on an x86 machine
  gets ``opt.c``, so that is the code which reaches Windows binaries; the
  reference fill is the non-x86 fallback. The two share ``argon2.c``,
  ``core.c``, ``encoding.c``, ``thread.c`` and BLAKE2b and differ only in
  the block-fill functions.
* **``OPTTARGET`` is pinned, not left at ``native``.** ``native`` resolves to
  whatever the build host's CPU is, so the same recipe would emit AVX2 or
  AVX-512 code on one machine and SSE2 on another and the corpus would not be
  reproducible. ``x86-64`` (x64) and ``pentium4`` (x86) select the SSE2
  baseline, the only level every Windows machine has.
* **Linux flags overridden on the command line.** The Makefile decides the
  library name and link flags from ``uname -s``; building on Linux selects
  ``-fPIC -fvisibility=hidden -DA2_VISCTL`` and a ``.so.1`` name. The
  ``LIB_EXT``/``LIB_CFLAGS``/``SO_LDFLAGS`` variables are therefore set to
  the MinGW branch's own values from the same Makefile. No source is patched.
  Without ``A2_VISCTL`` every ``ARGON2_PUBLIC`` symbol is exported, which is
  also what the upstream Windows build does.
* **opt and ref are one build, not two, because they barely differ.** Both
  were built per architecture and the PicHashes of their functions of ten
  instructions or more compared: 54 of 56 match on x86 and 51 of 53 on x64
  (x86 ref was built with ``-march=pentium4`` as well - without it the
  fallback gets i686 code generation and only 4 of 57 match, a tuning
  difference and not a source one). The two that differ are ``fill_block``
  and ``fill_segment`` and nothing else, so a second family-version would
  duplicate 95% of the first. Binaries that vendor only the portable fill
  (RandomX ships its own ``argon2_ref.c``) still match on everything else.
* Threads stay on: ``thread.c`` uses native ``_beginthreadex`` under
  ``_WIN32``, so no pthread DLL is dragged in.

Function counts (SMDA 5.0.2), partitioning each image exactly. x86: 113 =
53 compiler/CRT removed by the baseline + 60 kept, of which 59 are Argon2
code (56 of ten instructions or more) and 1 is the unnamed ``___chkstk``
probe. x64: 126 = 53 removed + 73 kept, of which 59 are Argon2 code, 13 are
unnamed one-instruction import jump stubs and 1 is the unnamed
``___chkstk_ms``. The baseline matches on symbol name as well as PicHash,
and these 15-instruction stack probes carry no symbol, so they survive it;
they are libgcc code, not Argon2, and are left in rather than patched around.

Overlap with libsodium 1.0.20 (MinGW, x86 and x64, PicHash of functions of ten
instructions or more): **none of Argon2's own code matches**. The only shared
hash is the unnamed 15-instruction ``___chkstk`` stack probe (MinGW runtime
code, not Argon2). Names do overlap - 16 to 17 of the
same symbols (``argon2_ctx``, ``argon2_hash``, ``argon2{i,id}_hash_raw``,
``argon2{i,id}_verify``, ``blake2b_*``, ``fill_block``) - but libsodium's copy
is restructured (``argon2_fill_segment_{ref,ssse3,avx2,avx512f}`` selected at
run time, BLAKE2b shared with its generichash, argon2d removed) and compiles
to different code. So the standalone reference is a distinct, complementary
reference, not a duplicate of ``data/libsodium``.

Measurement against all of data/libsodium (tracker issue 35 asked for it),
re-measured from the committed exports. PicHashes of functions of ten
instructions or more, this family's two MinGW images against the eight
libsodium images (1.0.18 and 1.0.20, MinGW and MSVC, x86 and x64): no Argon2
body matches in any of them. The only shared hash is the unnamed
15-instruction MinGW runtime routine ``___chkstk``, in the four MinGW libsodium
images and in none of the MSVC ones. (An MSVC build of this reference, kept on
its own branch, does share hashes with the two MSVC x64 libsodium images:
``load_block``/``store_block`` (one hash), ``decode_decimal``,
``b64_byte_to_char`` and ``b64_char_to_byte``, 4 PicHashes in both 1.0.18 and
1.0.20, and nothing on MSVC x86.) Counted by name, libsodium carries the
Argon2 core as its own functions (``argon2_ctx``, ``argon2_hash``,
``argon2{i,id}_hash_{raw,encoded}``, ``argon2_verify``, ``argon2_initialize``,
``argon2_finalize``, ``argon2_fill_memory_blocks``,
``argon2_fill_first_blocks``, ``argon2_fill_segment_{ref,ssse3,avx2,avx512f}``,
``argon2_encode_string``, ``argon2_decode_string``,
``argon2_validate_inputs``, ``argon2_initial_hash``, ``blake2b_long``, ...):
counting every function whose name contains ``argon2``, 57 per image in 1.0.18
(MinGW and MSVC, both architectures) and 68 to 70 per image in 1.0.20, of
which 14 to 17 (1.0.18) and 26 to 28 (1.0.20) have ten instructions or more.
They are Argon2 bodies by function and by name, and vendored
(src/libsodium/crypto_pwhash/argon2/), but with the MinGW builds they are not
this code: none of them has this image's PicHash, so a sample statically
linking the standalone reference is matched only by this family. libsodium
carries Argon2i and Argon2id and no Argon2d (no ``argon2d``-named function in
any of the eight images; this image has ``argon2d_ctx``, ``argon2d_hash_raw``,
``argon2d_hash_encoded``, ``argon2d_verify`` and ``argon2d_verify_ctx``).

The libsodium provenance note that issue 35 asks for is still owed, and
cannot be written from here: data/libsodium lives on main and this branch's
sparse tree does not hold it. What it should say, from the numbers above:
libsodium vendors a restructured Argon2 (crypto_pwhash/argon2/, derived from
P-H-C/phc-winner-argon2 with run-time dispatched fill functions, BLAKE2b
shared with generichash and Argon2d removed), 57 to 70 Argon2-named functions
per image (14 to 28 of ten instructions or more), and none of them matches this
family's MinGW images by PicHash. (The
BLAKE2b reference code in libsodium has its own provenance record on the
BLAKE2 branch.)

The Argon2d-subset question. RandomX vendors only the Argon2d addressing path
(tevador/RandomX, commit 6fe0e390acc28a50bfe7f59603c2a6effae4a7cd:
src/argon2_core.c, argon2_ref.c, argon2_ssse3.c, argon2_avx2.c and
blake2/blake2b.c, public names prefixed ``randomx_``), which is why issue 35 is
a prerequisite of the RandomX and XMRig issues. Built here only to measure,
with MinGW GCC 13 at -O3 (``-march=x86-64`` / ``pentium4``, ``-mssse3`` and
``-mavx2`` on the two SIMD units), linked as a DLL with unresolved RandomX
symbols ignored, and not committed as data because it is RandomX's code and
belongs to that family: x64 33 kept + 52 removed = 85 (21 of ten instructions
or more), x86 24 + 52 = 76 (22). Against this family's images, 5 PicHashes
match on each architecture: ``randomx_argon2_index_alpha`` (``index_alpha``),
``blake2b_compress``, ``randomx_blake2b_init_param`` (``blake2b_init_param``),
``randomx_blake2b_update`` (``blake2b_update``) and the unnamed
``___chkstk``. Everything that is the Argon2 algorithm proper differs:
``fill_block`` (three variants, one per fill unit, against this image's one),
``fill_segment`` (``randomx_argon2_fill_segment_{ref,ssse3,avx2}``),
``initialize``, ``fill_memory_blocks``, ``fill_first_blocks``,
``validate_inputs`` and ``initial_hash``. So the Argon2d subset RandomX carries
is a different code shape from the reference's generic ``fill_segment``, which
handles Argon2d, Argon2i and Argon2id in one function; only the BLAKE2b parts
and the address computation are shared. It shares nothing with libsodium
beyond ``___chkstk`` (0 hashes of ten instructions or more in the eight
images). A build of the RandomX subset belongs to that family's recipe.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_MAKE = ("make libargon2.dll ARGON2_VERSION=20190702 CC={cc} OPTTARGET={opttarget} "
         "LIB_EXT=dll LIB_CFLAGS='-shared -Wl,--out-implib,libargon2.dll.a' "
         "SO_LDFLAGS=")


def _argon2(opttarget_x86, opttarget_x64):
    # The recipe is shared by both architectures; pick the baseline by {bitness}.
    return [
        BuildStep("rm -f libargon2.dll src/*.o src/blake2/*.o", allow_failure=True),
        BuildStep("if [ {bitness} = 64 ]; then T=%s; else T=%s; fi; %s"
                  % (opttarget_x64, opttarget_x86,
                     _MAKE.replace("{opttarget}", "$T"))),
    ]


RECIPES = {
    "argon2_20190702": Recipe(
        family="argon2",
        version="20190702",
        upstream="https://github.com/P-H-C/phc-winner-argon2",
        license="CC0-1.0 OR Apache-2.0",
        source=Source(git_url="https://github.com/P-H-C/phc-winner-argon2.git",
                      git_ref="20190702"),
        build=_argon2("pentium4", "x86-64"),
        artifacts=[Artifact(path="libargon2.dll", component="libargon2.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        notes="Reference Argon2 (opt.c, SSE2 baseline); libsodium bundles its "
              "own, different Argon2 - see the recipe docstring. Measured "
              "against all eight data/libsodium images: no PicHash of ten "
              "instructions or more is shared by the MinGW images apart from "
              "the unnamed 15-instruction MinGW runtime routine ___chkstk, "
              "although libsodium has 57 to 70 Argon2-named functions per "
              "image (14 to 28 of ten instructions or more: argon2_ctx, "
              "argon2_fill_*, argon2_encode_string, blake2b_long, ...) and "
              "no Argon2d. "
              "RandomX's Argon2d subset (randomx_argon2_*, measured, not "
              "committed) shares 5 hashes with this image: index_alpha, "
              "blake2b_compress, blake2b_init_param, blake2b_update and "
              "___chkstk; the fill, initialize and validate functions "
              "differ. The libsodium provenance note is still owed.",
        build_flags="-O3 -std=c89 -g -march=x86-64 (x64) / -march=pentium4 (x86), "
                    "src/opt.c (Makefile default)",
    ),
}
