"""libxml2 built with MSVC, beside the MinGW builds of the same tags.

The MinGW recipe's own docstring already says this one should exist:
"ShiftMediaProject publishes MSVC builds of libxml2 with PDBs across
msvc12-msvc17, which would be closer to what is met in the wild than a MinGW
build; that route is worth adding separately rather than instead, since the
two compilers produce genuinely different code." This is that route, built
here from source at the same two tags rather than imported, so the MSVC and
MinGW artefacts share a pinned commit.

Upstream's CMake build has an explicit MSVC path - it copies
include/win32config.h over config.h for MSVC at 2.9.14, and sets the MSVC
Debug and static-library name postfixes - which is why it is used here in
preference to win32/Makefile.msvc. win32/Makefile.msvc exists at both tags
and is the historically representative build, but it is a second build
system to get right at the same time as the toolchain, and CMake keeps this
pair comparable with the MinGW one.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

What was read rather than assumed, in CMakeLists.txt at both v2.9.14 and
v2.14.3:

  * the library target is called "LibXml2" - add_library(LibXml2 ...) with
    no STATIC/SHARED keyword, so BUILD_SHARED_LIBS decides, and without it
    the build is a static library SMDA cannot read.
  * set_target_properties gives it PREFIX "lib" and OUTPUT_NAME "xml2"
    unconditionally, not on a WIN32 or MinGW branch. So unlike libuv,
    libtiff and libevent in this wave, the MSVC file name is the **same**
    libxml2.dll the MinGW recipe records, and the PDB beside it is
    libxml2.pdb - CMake's MSVC shared-library rule passes
    /pdb:<TARGET_PDB>, and that name is built from the runtime artefact's
    own prefix and base name, which here are "lib" and "xml2".
  * the MSVC name postfixes are DEBUG_POSTFIX only when BUILD_SHARED_LIBS is
    on; RELEASE_POSTFIX "s" is in the static branch. This is a shared
    Release build, so neither applies.
  * nothing sets CMAKE_RUNTIME_OUTPUT_DIRECTORY, so the DLL lands in the
    build root, exactly where the MinGW recipe finds it.
  * there is no .rc and no .def in the tree; exports come from the
    XMLPUBFUN/__declspec(dllexport) machinery in the public headers.

Dependencies, which is where this family can go wrong:

  * LIBXML2_WITH_ZLIB, _LZMA and _ICONV all default to something that can
    turn on by itself. At 2.9.14 zlib and lzma default plainly ON and iconv
    ON, each doing a find_package that on a Windows runner carrying vcpkg
    could succeed; at 2.14.3 LIBXML2_WITH_ZLIB is a cmake_dependent_option
    that is forced ON whenever LIBXML2_WITH_LEGACY is on. All three are
    passed OFF here, exactly as the MinGW recipe passes them, so no zlib or
    liblzma code can land inside a libxml2 artefact and be attributed to
    this family. zlib is its own family in this corpus, liblzma is another,
    and libpng16.dll has already shown what statically absorbing one costs:
    66 of 116 PicHashes overlapping data/libzlib.
  * LIBXML2_WITH_ICONV=OFF is not optional in practice either - there is no
    iconv on a stock Windows runner, and the option's find_package is
    REQUIRED - but it is passed for the attribution reason first.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# See xz_msvc.py for why these two per-configuration variables rather than
# CMAKE_C_FLAGS / CMAKE_SHARED_LINKER_FLAGS: overriding the per-config ones
# leaves CMake's own initialisation - /machine on the 32-bit leg among it -
# in place.
#
# /MD is restated even though both tags declare a cmake_minimum_required of
# 3.15 or later, which makes CMP0091 NEW and has CMake emit -MD from
# CMAKE_MSVC_RUNTIME_LIBRARY's default rather than from the flags variable.
# Under that policy the /MD below is simply repeated on the command line,
# which cl accepts; under the OLD policy it would be the only source of the
# flag. Saying it once here means the recipe does not depend on which of the
# two is in force, and cl's own default is /MT - a static CRT put 1947 of
# VX-API's 4219 functions into that artefact as MSVC C runtime.
#
# /Zi because CMake's Release carries no debug information and MSVC keeps
# symbols in the PDB rather than in a COFF symbol table; /DEBUG so a PDB is
# written at all; /Brepro so the PE carries no build timestamp and two runs
# of identical source record the same sha256; /OPT:NOREF /OPT:NOICF so
# unreferenced and identically-compiled routines both survive as separate
# reference samples. /INCREMENTAL:NO is CMake's own Release default and is
# restated because setting the variable replaces it.
_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

# NMake Makefiles: nmake ships with MSVC itself, the generator is
# single-configuration so the DLL lands in the build root rather than under a
# Release/ subdirectory, and the target architecture comes from the developer
# environment the workflow sets up.
#
# The option set is the MinGW recipe's, carried across unchanged, so the two
# artefacts differ in the compiler and not in what was compiled. LIBXML2_WITH_
# PYTHON and _TESTS and _PROGRAMS keep the build to the library; the three
# codec switches are the dependency isolation described above. All six names
# were checked against the option() and cmake_dependent_option() lists of
# both tags and exist at both, so none of them is a silently ignored cache
# variable - the 2.14 series did drop a number of other WITH_ switches, but
# not these.
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON '
          '-DLIBXML2_WITH_PYTHON=OFF -DLIBXML2_WITH_ZLIB=OFF '
          '-DLIBXML2_WITH_LZMA=OFF -DLIBXML2_WITH_ICONV=OFF '
          '-DLIBXML2_WITH_TESTS=OFF -DLIBXML2_WITH_PROGRAMS=OFF %s %s'
          % (_CFLAGS, _LDFLAGS))


def _libxml2_msvc(version, git_ref):
    return Recipe(
        family="libxml2",
        version=version,
        upstream="https://gitlab.gnome.org/GNOME/libxml2",
        license="MIT",
        source=Source(git_url="https://github.com/GNOME/libxml2.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} --target LibXml2"),
            # Cheap insurance, as in xz_msvc.py: build.py reports a missing
            # artefact by the path it expected and nothing else, so this puts
            # the names the build actually wrote into the log the workflow
            # prints on failure.
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/libxml2.dll",
                            component="libxml2.dll",
                            pdb="build-{arch}/libxml2.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release, /Zi added), optional "
                    "codecs disabled; /DEBUG /Brepro /OPT:NOREF /OPT:NOICF "
                    "at link",
        notes="The same tag and the same option set as the MinGW recipe for "
              "this version, so the two artefacts differ in the compiler "
              "rather than in what was built - and, unusually for this "
              "wave, they even carry the same file name, because upstream "
              "sets PREFIX lib and OUTPUT_NAME xml2 on every platform "
              "instead of letting the toolchain's library prefix decide. No "
              "dependencies: zlib, liblzma and iconv are all switched off "
              "explicitly, so none of that code lands inside this artefact "
              "and gets attributed to libxml2 - zlib and liblzma are their "
              "own families here. Built against the DLL runtime, so the "
              "MSVC C runtime is imported rather than linked in and stays "
              "attributed to data/MSVC; the rest links only ws2_32. The "
              "MinGW build is -O3 from CMake's GCC Release, this one "
              "/O2 /Ob2 from CMake's MSVC Release.",
    )


RECIPES = {
    # The same two tags as the MinGW recipe. 2.9.14 is the last of the very
    # long-lived 2.9 series that most vendored copies still are; 2.14.3 is
    # current, after the parser rework.
    "libxml2_2.9.14_msvc": _libxml2_msvc("2.9.14", "v2.9.14"),
    "libxml2_2.14.3_msvc": _libxml2_msvc("2.14.3", "v2.14.3"),
}
