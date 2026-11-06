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
hash is that unnamed ``___chkstk`` probe. Names do overlap - 16 to 17 of the
same symbols (``argon2_ctx``, ``argon2_hash``, ``argon2{i,id}_hash_raw``,
``argon2{i,id}_verify``, ``blake2b_*``, ``fill_block``) - but libsodium's copy
is restructured (``argon2_fill_segment_{ref,ssse3,avx2,avx512f}`` selected at
run time, BLAKE2b shared with its generichash, argon2d removed) and compiles
to different code. So the standalone reference is a distinct, complementary
reference, not a duplicate of ``data/libsodium``.
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
              "own, different Argon2 - see the recipe docstring.",
        build_flags="-O3 -std=c89 -g -march=x86-64 (x64) / -march=pentium4 (x86), "
                    "src/opt.c (Makefile default)",
    ),
}
