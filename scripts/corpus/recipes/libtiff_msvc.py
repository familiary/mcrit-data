"""libtiff built with MSVC, beside the MinGW build of the same tag.

Image-handling stacks on Windows are MSVC-built and libtiff has a long CVE
history and is embedded widely, but data/libtiff carries only MinGW
artefacts. Upstream's CMake build is the supported Windows build: it compiles
a Windows version-information resource, it ships a module-definition file
that CMake hands to link.exe, and it deliberately builds the C++ wrapper as a
static library "on WIN32 AND NOT MINGW" because there is no .def for it.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

What was read rather than assumed, at v4.7.0:

  * the library target is called "tiff" - add_library(tiff libtiff.def) in
    libtiff/CMakeLists.txt, with the sources added by target_sources. It has
    no STATIC/SHARED keyword, so BUILD_SHARED_LIBS decides, and without it
    the build is a static tiff.lib that SMDA cannot read.
  * no OUTPUT_NAME or PREFIX is set on it, so the file is **tiff.dll**, not
    the MinGW build's libtiff.dll - MSVC's CMAKE_SHARED_LIBRARY_PREFIX is
    empty where GCC's is "lib". The component is recorded as the name this
    build produces, as lz4_msvc.py records lz4.dll against MinGW's
    liblz4.dll.
  * VERSION and SOVERSION are set on the target, but CMake drops both from
    the file name where the platform has no soname - the MinGW recipe's own
    artefact path, build-<arch>/libtiff/libtiff.dll with no version in it,
    is the evidence for that. The LINK_FLAGS that would clobber this
    recipe's linker flags are inside if(HAVE_LD_VERSION_SCRIPT), a GNU-ld
    probe that does not fire under MSVC.
  * nothing sets CMAKE_RUNTIME_OUTPUT_DIRECTORY, so the DLL lands in
    build-<arch>/libtiff, mirroring the source directory - again the path
    the MinGW recipe already uses. The PDB lands beside it: CMake's MSVC
    shared-library rule passes /pdb:<TARGET_PDB>, that name is the runtime
    artefact's own prefix and base name with a .pdb suffix, and its
    directory falls back to the runtime output directory, which no target
    here overrides.
  * tif_win32_versioninfo.rc is added to the target under if(WIN32), and
    project() names only C and CXX. It still compiles: CMake's
    Platform/Windows-MSVC.cmake calls enable_language(RC) itself when a
    compiler is enabled for an MSVC-like toolchain, and passes rc.exe only
    the platform defines, not this recipe's CMAKE_C_FLAGS_RELEASE.
  * the C++ wrapper is left enabled, as under MinGW, and upstream builds it
    as a static tiffxx.lib for MSVC, so it cannot turn into a second DLL
    with no exports. Building --target tiff means it is not compiled at all.

Only 4.7.0 is covered. 4.0.10's CMakeLists.txt declares
cmake_minimum_required(VERSION 2.8.11), which CMake 4 refuses outright; the
escape hatch is a cache variable and so would be legitimate here, but
raising a 2.8-era project's policy floor to 3.5 crosses CMP0054 - if() no
longer dereferencing quoted arguments - and that file is full of the old
spelling. That is a second thing to debug on top of the toolchain, which is
the same call lz4_msvc.py made about lz4 1.9.4.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# See xz_msvc.py for why these two per-configuration variables rather than
# CMAKE_C_FLAGS / CMAKE_SHARED_LINKER_FLAGS: overriding the per-config ones
# leaves CMake's own initialisation - /machine on the 32-bit leg among it -
# in place.
#
# /MD is restated because this variable is where it lives here. libtiff's
# cmake_minimum_required is 3.9.0, so CMP0091 is OLD and
# CMAKE_MSVC_RUNTIME_LIBRARY is not consulted at all; the runtime flag comes
# only from CMAKE_C_FLAGS_<CONFIG>, whose Release default
# (Platform/Windows-MSVC.cmake) is "/MD /O2 /Ob2 /DNDEBUG". Replacing that
# string without /MD in it would hand the build cl's own default, /MT, and a
# static CRT put 1947 of VX-API's 4219 functions into that artefact as MSVC C
# runtime.
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
# single-configuration so CMAKE_BUILD_TYPE means what it says, and the target
# architecture comes from the developer environment the workflow sets up.
#
# The codec switches are the MinGW recipe's, carried across character for
# character, and here they are load-bearing in a way they are not on the
# Linux host. Every one of zlib, jpeg, jbig, lzma, zstd, webp, lerc and
# libdeflate is an option whose default is the matching find_package's
# _FOUND variable, so on a runner carrying a vcpkg or a strawberry-perl
# tree with any of them installed, CMake would find it and link it in -
# putting another family's code inside a libtiff artefact. That is the
# mistake libpng16.dll made against data/libzlib. Turning them off also
# turns off the options that depend on them: old-jpeg follows jpeg, and
# pixarlog follows zlib.
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON '
          '-Dtiff-tests=OFF -Dtiff-tools=OFF -Dtiff-docs=OFF '
          '-Dzlib=OFF -Djpeg=OFF -Djbig=OFF -Dlzma=OFF -Dzstd=OFF '
          '-Dwebp=OFF -Dlerc=OFF -Dlibdeflate=OFF %s %s'
          % (_CFLAGS, _LDFLAGS))


RECIPES = {
    # The same tag as the newer of the two MinGW artefacts, so the pair can
    # be compared directly.
    "libtiff_4.7.0_msvc": Recipe(
        family="libtiff",
        version="4.7.0",
        upstream="https://gitlab.com/libtiff/libtiff",
        license="libtiff (MIT-like)",
        source=Source(git_url="https://gitlab.com/libtiff/libtiff.git",
                      git_ref="v4.7.0"),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} --target tiff"),
            # Cheap insurance, as in xz_msvc.py: build.py reports a missing
            # artefact by the path it expected and nothing else, so this puts
            # the names the build actually wrote into the log the workflow
            # prints on failure.
            BuildStep("dir build-{arch}\\libtiff", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/libtiff/tiff.dll",
                            component="tiff.dll",
                            pdb="build-{arch}/libtiff/tiff.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release, /Zi added), optional "
                    "codecs disabled; /DEBUG /Brepro /OPT:NOREF /OPT:NOICF "
                    "at link",
        notes="The same tag and the same codec set as the MinGW recipe for "
              "this version, so the two artefacts differ in the compiler "
              "rather than in what was built. Named tiff.dll rather than the "
              "MinGW build's libtiff.dll because MSVC has no library prefix; "
              "it is the same library and the same tag. No dependencies, and "
              "that is a decision rather than an accident: every codec that "
              "would pull in zlib, libjpeg, liblzma, zstd, webp, lerc, jbig "
              "or libdeflate is switched off explicitly, so none of that "
              "code can land inside this artefact and be attributed to "
              "libtiff - the codecs default to whatever find_package "
              "happens to locate on the build host, which on a Windows "
              "runner is a real risk and on the Linux host was not. Only the "
              "tiff target is built, so tiffxx - which upstream makes a "
              "static library under MSVC - and the tools are not in this "
              "run. Built against the DLL runtime, so the MSVC C runtime is "
              "imported rather than linked in and stays attributed to "
              "data/MSVC. The MinGW build is -O3 from CMake's GCC Release, "
              "this one /O2 /Ob2 from CMake's MSVC Release.",
    ),
}
