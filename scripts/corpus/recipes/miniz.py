"""miniz - single-author zlib subset (deflate, inflate, zip) in a handful of C files.

Backlog issue r0ny123/mcrit-data#81. miniz is what small agents and loaders
vendor when they want zlib's API without zlib's build: AdaptixC2's beacon agent
carries a copy, which is why it is wanted here. AdaptixC2 itself is not built -
that is issue #80 and a separate decision.

No miniz coverage existed under any name: no data/miniz, no mention in either
README, and no vendored copy inside another family's image (the corpus has
only built each project's own tree).

Pinned to the git tag 3.1.0 (commit 174573d60290f447c13a2b1b3405de2b96e27d6c),
the version the issue names. 3.1.1 and 3.1.2 exist upstream; a second version
was not added because the source files under test are the same and the point of
the family is the 3.1 line, but it is a one-line addition if wanted.

Build decisions:
  * Upstream's own CMakeLists.txt with BUILD_SHARED_LIBS=ON, which builds
    miniz.c, miniz_zip.c, miniz_tinfl.c and miniz_tdef.c as separate
    translation units into one DLL. It uses generate_export_header, and every
    public function carries MINIZ_EXPORT, so the DLL exports the whole API
    (mz_*, tdefl_*, tinfl_*, mz_zip_*) and no driver TU is needed. The
    amalgamation (AMALGAMATE_SOURCES) was not used: it is the same code
    concatenated, but what a vendoring project compiles is a choice of its own
    and upstream's default is the multi-file layout.
  * C_VISIBILITY_PRESET hidden is set by upstream for the shared build. That
    is what the corpus's own ELF notes ask for, and it keeps internal helpers
    direct-called rather than reached through stubs.
  * BUILD_EXAMPLES, BUILD_TESTS and INSTALL_PROJECT default to ON for a
    standalone project, so all three are turned off to keep the build to the
    library; the examples would otherwise add example1-6 executables.
  * CMake Release flags (-O3 -DNDEBUG), plus upstream's -Wall -pedantic
    -std=gnu90. Nothing patched.

Counts (smda 5.0.2, mcrit 1.16.0): the DLL holds 211 functions on x86 and 230
on x64; the glue baseline removes 62 and 66 (MinGW startup, stdio, heap and
_wstat64 imports), leaving 149 and 164 - 148 and 147 of them named. Kept plus removed
equals the image total exactly. 130 and 121 carry ten or more instructions.
The 17 unnamed x64 functions are one-instruction thunks and one 15-instruction
stub. The DLL is bin/libminiz.dll, not under the CMake build directory, which
is why the artefact path is not build-{arch}/.

Overlap with data/libzlib, measured by PicHash against every libzlib report
(MinGW 1.2.8-1.3.1 and MSVC 12-143): essentially none. The mz_deflate and
mz_inflate wrappers are miniz's own code over tdefl/tinfl, not zlib's
deflate.c/inflate.c, so the compression cores share nothing. Against
libzlib 1.3.1 MinGW the shared hashes are 8 (x86) and 20 (x64), and of those
all but one are bodies of one to four instructions (mz_free, mz_version,
miniz_def_free_func, tdefl/tinfl_decompressor_free, CRT thunks such as
_utime); the single larger one is a 15-instruction unnamed stub that appears
in both. Only the API names (adler32, crc32, compress, uncompress) overlap.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_RC_COMPILER={windres} "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} "
          "-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON "
          "-DBUILD_EXAMPLES=OFF -DBUILD_TESTS=OFF -DINSTALL_PROJECT=OFF")


def _miniz(version, git_ref):
    return Recipe(
        family="miniz",
        version=version,
        upstream="https://github.com/richgel999/miniz",
        license="MIT",
        source=Source(git_url="https://github.com/richgel999/miniz.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="bin/libminiz.dll",
                            component="libminiz.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 -DNDEBUG -std=gnu90 (CMake Release, upstream CMakeLists)",
        notes="Shared build of upstream CMake: miniz.c, miniz_zip.c, "
              "miniz_tinfl.c and miniz_tdef.c; the whole API is exported.",
    )


RECIPES = {
    "miniz_3.1.0": _miniz("3.1.0", "3.1.0"),
}
