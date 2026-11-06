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
says it is, is the nearest. A -DCMP_NO_FLOAT build is not what is recorded
here: the flag removes the float/double readers and writers, and the recipe
builds upstream's default.

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


RECIPES = {
    "cmp_10": _cmp("10", "v10"),
    "cmp_20": _cmp("20", "v20"),
}
