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

The trimmed artefact (issue #81 asks for what AdaptixC2's beacon compiles).
``miniz_3.1.0_trim`` builds the same tag, the same CMake options, with
AdaptixC2's MINIZ_TRIM_FLAGS (Makefile lines 44-46, as the issue lists them)
added through CMAKE_C_FLAGS: -DMINIZ_NO_STDIO -DMINIZ_NO_ARCHIVE_APIS
-DMINIZ_NO_ARCHIVE_WRITING_APIS -DMINIZ_NO_TIME -DMINIZ_NO_ASSERT. flags.make
reads `-DMINIZ_NO_STDIO ... -DMINIZ_NO_ASSERT -Wshadow -Wformat=2 -Wall
-Wno-overlength-strings -pedantic -O3 -DNDEBUG -std=gnu90 -fvisibility=hidden`.
It is filed under the version label 3.1.0-trim (the provenance refresh matches
images to recipes by family, version and toolchain, and a second 3.1.0 recipe
would be ambiguous), component libminiz.dll. Differences from what the beacon
really compiles, stated so nobody mistakes this for a byte-level copy: the
beacon builds the amalgamated miniz.cpp with g++ and no -O flag, this is
upstream's multi-file C build at -O3; the trim macros are the same.

kept + removed = total: x86 56 + 52 = 108, x64 65 + 53 = 118 (the default
build is 149 + 62 = 211 and 164 + 66 = 230). With NO_ARCHIVE_APIS miniz_zip.c
compiles to nothing, so every mz_zip_*, mz_fopen, fseeki64/ftelli64 of the
default image (about 100 names) is gone and nothing is added: the trimmed image
is a strict subset. 43 of 43 (x64) and 44 of 44 (x86) of its 10+ instruction
PicHashes are also in the default image (43 of 119 and 44 of 127 the other
way), so for exact matching it adds no hash; what it records is the build the
issue asks for and its smaller function set. What stays is mz_adler32,
mz_crc32, mz_compress/compress2/compressBound, mz_uncompress/uncompress2,
mz_deflate*/mz_inflate*, the tdefl_* compressor, the tinfl_* decompressor
(tinfl_decompress 2.9k instructions on x64) and the three miniz_def_*_func
allocator stubs; 1 (x86) and 10 (x64) kept functions are unnamed import thunks.

Does miniz survive linking where nothing calls it (the issue's open question)?
Answered with a throwaway exerciser, linked only, never run: miniz compiled
with the same trim macros at -O0 (the beacon has no -O flag), a main() that
does not touch miniz, linked for MinGW x86 and x64 (sources in
scripts/corpus/exercisers/miniz_link_survival/). Whether tinfl_decompress ends up in the
executable, by how miniz reaches the linker:

  * object files on the link line, no --gc-sections: kept (tinfl_decompress,
    tdefl_compress, mz_crc32, mz_adler32, mz_compress2, mz_uncompress all
    present). Same with -ffunction-sections -fdata-sections.
  * the same with -Wl,--gc-sections: STILL kept, on both architectures, with
    and without -ffunction-sections. MinGW's unwind tables are linker roots:
    x64's .pdata/.xdata and x86's .eh_frame carry relocations against every
    function and are never collected, which keeps .text alive. Recompiling the
    objects with -fno-asynchronous-unwind-tables -fno-unwind-tables (alone,
    or with -ffunction-sections) and --gc-sections removes all of it.
  * a static archive (libminiz.a) on the link line with a main that does not
    reference miniz: dropped, with or without --gc-sections (an archive member
    is pulled in only to satisfy a reference).
  * control, the DNS variant calling compress/uncompress/compressBound: kept,
    as expected, in every mode.

So whether a non-DNS beacon carries miniz depends on the part of the build that
the issue says the Makefile does not contain (it stops at .o files): miniz.o
listed as an object survives the default MinGW link even under --gc-sections,
unless the beacon is also compiled without unwind tables. The beacon's real
link line was not examined (the AdaptixC2 repository is not reachable from the
build host), so this is a statement about the toolchain, not about the HTTP
variant itself; the issue's suggested test, looking for tinfl_decompress in a
built HTTP beacon, is still the one that settles it.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_RC_COMPILER={windres} "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} "
          "-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON "
          "-DBUILD_EXAMPLES=OFF -DBUILD_TESTS=OFF -DINSTALL_PROJECT=OFF")


# AdaptixC2's MINIZ_TRIM_FLAGS (Makefile lines 44-46), as issue #81 lists them.
# With NO_ARCHIVE_APIS the whole zip reader/writer (miniz_zip.c) preprocesses
# to nothing, NO_STDIO drops the FILE-based helpers, NO_TIME drops the
# time_t/utime paths and NO_ASSERT turns MZ_ASSERT into a no-op; what is left
# is the deflate/inflate core, checksums and the mz_* zlib-style wrappers that
# AdaptixC2's DnsCodec.cpp calls (compressBound, compress, uncompress).
_TRIM_FLAGS = ("-DMINIZ_NO_STDIO -DMINIZ_NO_ARCHIVE_APIS "
               "-DMINIZ_NO_ARCHIVE_WRITING_APIS -DMINIZ_NO_TIME "
               "-DMINIZ_NO_ASSERT")


def _miniz(version, git_ref, trimmed=False):
    """``trimmed`` builds the same tag with _TRIM_FLAGS. It is filed under the
    version label ``<tag>-trim`` rather than as a second component of the same
    version, because the provenance refresh matches an image to its recipe by
    family, version and toolchain and two recipes sharing all three are
    ambiguous."""
    cmake = _CMAKE
    if trimmed:
        cmake += ' "-DCMAKE_C_FLAGS=%s"' % _TRIM_FLAGS
    return Recipe(
        family="miniz",
        version=version + ("-trim" if trimmed else ""),
        upstream="https://github.com/richgel999/miniz",
        license="MIT",
        source=Source(git_url="https://github.com/richgel999/miniz.git",
                      git_ref=git_ref),
        build=[
            BuildStep(cmake),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="bin/libminiz.dll",
                            component="libminiz.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags=("-O3 -DNDEBUG -std=gnu90 (CMake Release, upstream "
                     "CMakeLists)" + (" plus " + _TRIM_FLAGS if trimmed else "")),
        notes=("Shared build of upstream CMake: miniz.c, miniz_zip.c, "
               "miniz_tinfl.c and miniz_tdef.c; the whole API is exported."
               if not trimmed else
               "The same CMake build with AdaptixC2's MINIZ_TRIM_FLAGS "
               "(" + _TRIM_FLAGS + ") added to CMAKE_C_FLAGS. Upstream "
               "CMake, not AdaptixC2's amalgamated miniz.cpp compiled by "
               "g++ at -O0, so the optimisation level and the language "
               "differ from the beacon's own object; the trim macros are "
               "the same."),
    )


RECIPES = {
    "miniz_3.1.0": _miniz("3.1.0", "3.1.0"),
    "miniz_3.1.0_trim": _miniz("3.1.0", "3.1.0", trimmed=True),
}


# --- The two later tags of the 3.1 line, default and trimmed, which the
# first revision did not build; separate versions as for 3.1.0.
RECIPES["miniz_3.1.1"] = _miniz("3.1.1", "3.1.1")
RECIPES["miniz_3.1.1_trim"] = _miniz("3.1.1", "3.1.1", trimmed=True)
RECIPES["miniz_3.1.2"] = _miniz("3.1.2", "3.1.2")
RECIPES["miniz_3.1.2_trim"] = _miniz("3.1.2", "3.1.2", trimmed=True)

# The beacon's form of the trimmed build: upstream's own amalgamated
# miniz.c (the release asset miniz-3.1.0.zip, which is what a project
# vendoring "miniz.c/miniz.h" copies; AdaptixC2 keeps it as miniz.cpp)
# compiled as C++ by g++ with no -O flag, which is what issue #81 records
# for the beacon, and the same MINIZ_TRIM_FLAGS. `-x c++` compiles the
# unmodified miniz.c as C++ instead of renaming it. A DLL of the one
# translation unit, so every global function is exported as with the
# CMake shared build; nothing patched.
RECIPES["miniz_3.1.0-amalg-trim-O0"] = Recipe(
    family="miniz",
    version="3.1.0-amalg-trim-O0",
    upstream="https://github.com/richgel999/miniz",
    license="MIT",
    source=Source(url="https://github.com/richgel999/miniz/releases/download/"
                      "3.1.0/miniz-3.1.0.zip",
                  sha256="f9d3e769ec5fd5583955a3c22eea457fe806be0d507805966d1a5b0410c77dda"),
    build=[BuildStep("{cxx} -x c++ %s -shared -o miniz.dll miniz.c"
                     % _TRIM_FLAGS)],
    artifacts=[Artifact(path="miniz.dll", component="miniz.dll")],
    toolchains=["mingw_x86", "mingw_x64"],
    build_flags="g++ -x c++, no -O flag (GCC's -O0 default), " + _TRIM_FLAGS
                + ", the amalgamated miniz.c of the 3.1.0 release asset",
    notes="The 3.1.0 release asset miniz-3.1.0.zip (sha256 computed from the "
          "download), whose miniz.c is upstream's amalgamation of the four "
          "source files, compiled as C++ with g++ and no optimisation flag, "
          "with AdaptixC2's MINIZ_TRIM_FLAGS: the shape issue #81 records "
          "for the beacon's vendored miniz.cpp. The beacon's own link line "
          "and source were not compared; this is upstream's code in that "
          "build shape, not a copy of the beacon's object. Nothing patched.",
)
