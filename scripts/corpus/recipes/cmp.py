"""cmp - camgunz/cmp, the single-file C MessagePack serializer (backlog #47).

Compiled into c-toxcore and so into the Crytox ransomware. No coverage exists
in the corpus under this or any other name (no data/cmp, no MessagePack
family, nothing in either README). Upstream publishes no checksums and has no
GitHub releases, only git tags, so these are pinned to the tags.

What c-toxcore actually vendors, established from its sources rather than
assumed: third_party/cmp is a git submodule of https://github.com/TokTok/cmp,
not of camgunz/cmp, pinned at 52bfcfa (2024-11-08 on the TokTok side).
c-toxcore only gained cmp on 2022-03-24 (ee154da4, "Use cmp instead of
msgpack-c for events packing"), so no toxcore older than that carries it. That
fork is upstream master at 9b8fa1e (2024-05-03, 25 commits past v20, still
reporting cmp_version_ = 20) plus six TokTok cleanups, and c-toxcore builds it
with -DCMP_NO_FLOAT (third_party/BUILD.bazel). No camgunz tag is therefore
byte-identical to the vendored copy; v20, the newest tag and the one the copy
says it is, is the nearest. The two camgunz versions below are upstream's
default, without -DCMP_NO_FLOAT, which removes the float/double readers and
writers. The vendored copy itself is the third artefact set,
``cmp_toktok_52bfcfa`` (version ``toktok-52bfcfa``): TokTok/cmp at the full
commit 52bfcfa17d2eb4322da2037ad625f5575129cece (the tip of its master, from
``git ls-remote``; the prefix is the one toxcore.py records for c-toxcore
v0.2.24), compiled as below with -DCMP_NO_FLOAT=1 and -O2. Kept + removed =
image total: x86 166 + 49 = 215, x64 175 + 50 = 225 (v20 keeps 175 / 184, so
the float-free copy is 9 functions smaller on both arches). PicHash overlap, functions of 10+
instructions (x86 / x64), of the vendored build's 144 / 134 distinct hashes
with v20: 93 / 80; with v10: 65 / 55. So the vendored copy is closer to v20
than v10 is, but 36 to 40% of it differs from the nearest camgunz tag, which
is why it is its own artefact and not a rename of v20.

The flags c-toxcore gives cmp.c, read from its CMakeLists.txt at v0.2.24 (the
submodule is at 52bfcfa in every tag from v0.2.21 to v0.2.24 and on master;
v0.2.20 has 2ac6bca): cmp.c is listed in toxcore_SOURCES (lines 234-235), so
it is compiled into the toxcore library with the project-wide settings and no
per-file flags. Those are ``add_definitions(-DCMP_NO_FLOAT=1)`` (line 213),
CMAKE_C_STANDARD 11 with CMAKE_C_EXTENSIONS OFF (lines 99-106, so -std=c11
under GCC) and, for non-MSVC compilers, no optimisation or warning option of
the project's own. The file never sets CMAKE_BUILD_TYPE (INSTALL.md gives its
default as the empty string and uses ``-D CMAKE_BUILD_TYPE=Release`` in its
example), so -O3 -DNDEBUG is CMake's own GNU Release default
(CMAKE_C_FLAGS_RELEASE), in effect only when the builder asks for Release; a
build with no build type has no -O at all. The Release line is the second
artefact of ``cmp_toktok_52bfcfa``, ``cmp-O3.dll``: -O3 -DNDEBUG -std=c11
-DCMP_NO_FLOAT=1, otherwise as cmp.dll. cmp.c has no assert and does not test
NDEBUG, so that define is recorded for fidelity and changes nothing. Kept +
removed = image total: x86 165 + 49 = 214, x64 174 + 50 = 224. PicHash
overlap with the -O2 cmp.dll of the same commit, functions of 10+
instructions: x86 55 shared of 146 (-O3) and 144 (-O2) distinct hashes, x64
45 of 136 and 134. So about two thirds of the -O3 image is not in the -O2 one.
What is still not built is the object as c-toxcore links it: the same file
inside the toxcore library, where a link-time or unity build
(CMAKE_UNITY_BUILD, which the CMakeLists.txt makes provision for) can inline
across it.

Build: cmp.c compiled directly into a DLL, no driver translation unit. cmp is
a library of exported functions (about 170 definitions in cmp.c at v20) with no state
and no configuration, so every public function is linked in simply by being
non-static; a driver would only have selected a subset. mingw-w64 exports all
globals of a DLL that declares none, so no .def file is needed. The Makefile
and CMakeLists.txt are test/example harnesses and are not used.

Function counts, kept after the MinGW glue baseline removed 49 (x86) or 50
(x64) runtime functions, so kept plus removed is the image total (v20: 175 + 49
= 224 x86, 184 + 50 = 234 x64): v10 160 x86 / 169 x64, v20 175 x86 / 184 x64.
174 are named on either arch of v20 (the x64 remainder is unnamed thunks and
short stubs). Well clear of the floor of eight; at -O2 GCC inlines
little because nearly everything is an exported function. The count is a few
above the public API because file-local helpers (read_obj_data, the be16/32/64
swaps and so on) survive as separate functions.

Versions, chosen by measured PicHash overlap of functions of 10+ instructions
(x86 / x64, share of the first version's sample):

  v17 v18 v19 v20   99-100% against each other. v17..v20 differ by 0-4
                    PicHashes: not worth a second row, so only v20 is kept.
  v10 v20           50 / 46% of v10's 137 / 125, 45 / 41% of v20's 153 / 140
  v5  v10           94%  (v5 and v10 also have the same 365 symbols)
  v1  v3            93%; v1 against v20 only 22-30%, but v1 against v10 78%

v10 is kept as the pre-rewrite representative (v17 added 14 functions and the
reworked object-reading path) and v20 as the current tag, the one c-toxcore's
copy descends from. v1, v3, v5 and v17-v19 were built and measured and are not
committed.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


def _cmp(version, git_ref):
    return Recipe(
        family="cmp",
        version=version,
        upstream="https://github.com/camgunz/cmp",
        license="MIT",
        source=Source(git_url="https://github.com/camgunz/cmp.git",
                      git_ref=git_ref),
        build=[BuildStep("{cc} -O2 -shared -o cmp.dll cmp.c")],
        artifacts=[Artifact(path="cmp.dll", component="cmp.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 (cmp.c compiled directly with -shared; upstream's "
                    "Makefile and CMakeLists.txt are test harnesses and are "
                    "not used; no -DCMP_NO_FLOAT)",
    )


# The copy c-toxcore actually vendors (backlog #47): third_party/cmp is a
# submodule of TokTok/cmp, pinned at 52bfcfa, which is the tip of its master
# (git ls-remote https://github.com/TokTok/cmp.git master ->
# 52bfcfa17d2eb4322da2037ad625f5575129cece; the prefix is the one recorded by
# toxcore.py for c-toxcore v0.2.24). Built with the flag c-toxcore builds it
# with (-DCMP_NO_FLOAT=1, CMakeLists.txt line 213 at v0.2.24; lines 234-235
# list cmp.c in toxcore_SOURCES), which removes the float and double readers
# and writers, at -O2 like the rest of this family, and a second time with
# the flags of c-toxcore's CMake Release build (cmp-O3.dll).
_TOKTOK_SHA = "52bfcfa17d2eb4322da2037ad625f5575129cece"

_TOKTOK = Recipe(
    family="cmp",
    version="toktok-52bfcfa",
    upstream="https://github.com/TokTok/cmp",
    license="MIT",
    source=Source(git_url="https://github.com/TokTok/cmp.git",
                  git_ref=_TOKTOK_SHA),
    build=[
        BuildStep("{cc} -O2 -DCMP_NO_FLOAT=1 -shared -o cmp.dll cmp.c"),
        # The flags c-toxcore's own CMake Release build gives cmp.c with GCC
        # (see the docstring for what was read and where).
        BuildStep("{cc} -O3 -DNDEBUG -std=c11 -DCMP_NO_FLOAT=1 -shared "
                  "-o cmp-O3.dll cmp.c"),
    ],
    artifacts=[
        Artifact(path="cmp.dll", component="cmp.dll"),
        Artifact(path="cmp-O3.dll", component="cmp-O3.dll",
                 build_flags="-O3 -DNDEBUG -std=c11 -DCMP_NO_FLOAT=1 (cmp.c "
                             "compiled directly with -shared; the flags of "
                             "c-toxcore's CMake Release build under GCC)"),
    ],
    toolchains=["mingw_x86", "mingw_x64"],
    build_flags="-O2 -DCMP_NO_FLOAT=1 (cmp.c compiled directly with -shared, "
                "the define c-toxcore builds its vendored copy with)",
    notes="The TokTok fork c-toxcore vendors as third_party/cmp, at the "
          "commit pinned there (52bfcfa), built with -DCMP_NO_FLOAT=1.",
)


RECIPES = {
    "cmp_10": _cmp("10", "v10"),
    "cmp_20": _cmp("20", "v20"),
    "cmp_toktok_52bfcfa": _TOKTOK,
}
