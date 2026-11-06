"""Jansson - C library for encoding, decoding and manipulating JSON.

No coverage exists in the corpus today (checked data/, README.md and this
file's siblings for the name under any spelling; cJSON and nlohmann_json are
different projects). Upstream publishes no checksums, hence git tags.

Two versions, 2.13.1 and 2.15.1. 2.15.1 (2026-06-30) is the current release.
2.13.1 is the pick for the older line. GitHub code search for the literal
`#define JANSSON_VERSION "<v>"` in vendored jansson.h copies gives 111 hits
for 2.13.1 and 116 for 2.14, then 24 for 2.14.1, 14 for 2.15.0, 13 for 2.13,
7 for 2.15.1 and at most 1 each for 2.7, 2.9, 2.10, 2.11 and 2.12. The two
leaders are a statistical tie on a search that is itself rough. 2.13.1 was
taken because it is also the version that overlaps least with the current
release, which is what a second reference is for, as the measurement below
shows. (It is the version Ubuntu 22.04 and Debian 12 ship as well, but that
was not measured here.)

Overlap was measured, not guessed, over functions of at least 10
instructions, by PicHash, after the glue filter ran (the 2.13.1 : 2.15.1
row was re-measured after the MinGW libc baseline dropped gettimeofday and
its two helpers from every artefact; the 2.14 rows predate that and the
candidate was not kept, so they could not be re-run):

                    x86                      x64
    2.13.1 : 2.14   98 of 120 / 125          91 of 113 / 118
    2.14   : 2.15.1 101 of 125 / 142         93 of 118 / 136
    2.13.1 : 2.15.1 83 of 118 / 140          75 of 111 / 134

So 2.13.1 shares 70% (x86) and 68% (x64) of its functions with 2.15.1, and
2.15.1 shares 59% and 56% of its own. 2.14, built as a candidate and not
kept, would have sat in between and added little: it shares 81% and 79% of
its functions with 2.15.1. And 2.13.1 and 2.15.1 differ where it counts:
the largest bodies of the parser and dumper, do_dump (do_dump.constprop.0 1250 and do_dump 672 instructions at 2.13.1 against
1263 and 680 at 2.15.1, x64), unpack (682 against 774) and parse_value (312
against 319), all have no PicHash twin across the two, and so do pack, do_deep_copy,
read_string, json_copy, hashtable_set and json_equal.

2.15.0 also added src/dtoa.c, David Gay's shortest-round-trip float
conversion, 6265 lines against 11245 for all of src/*.c at 2.15.1 and not
present at all in 2.13.1 or 2.14 (USE_DTOA is a CMake option, ON by default).
That is where the largest functions in 2.15.1 come from (strtod__unused 2741
instructions, dtoa_r 2049, gethex 897, d2b, b2d, lshift, pow5mult, quorem),
and it is jansson's own vendored copy, not mingw's: libmingwex's copy of the
same algorithm is named *_D2A and is removed by the glue filter as runtime,
while these carry the unsuffixed upstream names and are kept. The 2.13.1
sample therefore cannot recognise a 2.15 binary's float path at all, which
is the strongest single reason to hold both.

Build: CMake with the MinGW cross compilers, as cJSON does. Four options
are set on the command line, none of them a source patch:
  - JANSSON_BUILD_SHARED_LIBS=ON, because this pipeline needs a DLL (default
    is a static archive, which SMDA cannot load);
  - JANSSON_BUILD_DOCS=OFF, so the build does not need python-sphinx;
  - JANSSON_EXAMPLES=OFF and JANSSON_WITHOUT_TESTS=ON, so no test or example
    executable is linked and nothing but the library is built.
Nothing else is needed: both tags configure and build unchanged. The
DLL lands in build-<arch>/bin/libjansson.dll at both tags (measured).

Flags actually given to the compiler, read from flags.make rather than
assumed, identical at both tags: `-O2 -Wno-format-truncation -O3 -DNDEBUG`.
The -O2 is this tooling's own CFLAGS, -Wno-format-truncation is upstream's
and -O3 -DNDEBUG is CMake's Release default; the last -O wins, so the code is
-O3. Jansson adds no hardening or visibility flags of its own, unlike cJSON.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_FIND_ROOT_PATH=/usr/{host} "
          "-DCMAKE_BUILD_TYPE=Release -DJANSSON_BUILD_SHARED_LIBS=ON "
          "-DJANSSON_BUILD_DOCS=OFF -DJANSSON_EXAMPLES=OFF "
          "-DJANSSON_WITHOUT_TESTS=ON")


def _jansson(version, git_ref):
    return Recipe(
        family="Jansson",
        version=version,
        upstream="https://github.com/akheron/jansson",
        license="MIT",
        source=Source(git_url="https://github.com/akheron/jansson.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="build-{arch}/bin/libjansson.dll", component="libjansson.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 -DNDEBUG (CMake Release), plus the toolchain's -O2 "
                    "and upstream's -Wno-format-truncation; -O3 wins",
    )


RECIPES = {
    # Most vendored older line (tied with 2.14, see above) and the one that
    # overlaps least with the current release.
    "Jansson_2.13.1": _jansson("2.13.1", "v2.13.1"),
    # Current release; adds the vendored dtoa.
    "Jansson_2.15.1": _jansson("2.15.1", "v2.15.1"),
}
