"""libevent built with MSVC, beside the MinGW build of the same tag.

data/libevent carries only MinGW artefacts, and libevent on Windows - the
event loop inside a lot of older tooling and its derivatives - is MSVC-built.
Upstream's CMake support treats MSVC as a first-class target: the library
type defaults to SHARED under MSVC specifically because "building SHARED and
STATIC is not supported for MSVC", and include/event2/visibility.h spells out
the __declspec(dllexport) case for _MSC_VER.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

What was read rather than assumed, in CMakeLists.txt and
cmake/AddEventLibrary.cmake at release-2.1.12-stable:

  * the shared targets are event_core_shared and event_extra_shared - the
    names the MinGW cross build of this same file writes into
    CMakeFiles/event_core_shared.dir/link.txt, which is what was checked
    here rather than guessed.
  * add_event_library sets, under "if (WIN32)", OUTPUT_NAME "${LIB_NAME}" -
    that is "event_core" and "event_extra", with no "lib" in it. The MinGW
    DLLs are libevent_core.dll only because GCC's CMAKE_SHARED_LIBRARY_PREFIX
    is "lib"; MSVC's is empty, so this build writes **event_core.dll** and
    **event_extra.dll**. The components are recorded as the names this build
    produces, as lz4_msvc.py records lz4.dll against MinGW's liblz4.dll.
  * SOVERSION is set on the WIN32 branch too, but CMake drops VERSION and
    SOVERSION from the file name where the platform has no soname - the
    MinGW link line above is "-o bin/libevent_core.dll" with no version in
    it, which settles it for Windows generally.
  * CMAKE_RUNTIME_OUTPUT_DIRECTORY is set to ${PROJECT_BINARY_DIR}/bin when
    it is not already defined, so the DLLs land in build-<arch>/bin. The PDBs
    land next to them: CMake's MSVC shared-library rule passes
    /pdb:<TARGET_PDB>, GetPDBName builds that name from the runtime
    artefact's own prefix and base name, and the PDB directory falls back to
    the runtime output directory, which nothing here overrides.
  * EVENT__MSVC_STATIC_RUNTIME is upstream's own /MD-to-/MT switch. It
    defaults to ON only for EVENT__LIBRARY_TYPE=STATIC and rewrites
    CMAKE_C_FLAGS_RELEASE with a REGEX REPLACE of /MD to /MT. SHARED gives it
    the OFF default, but it is passed explicitly anyway: this is the one
    place in the tree that could silently produce a static-CRT artefact, and
    an override costs nothing.
  * the -Wall/-Wextra/-Werror-shaped flags libevent appends to CMAKE_C_FLAGS
    are inside "if (${GNUC})", so they are not in this build. There is no
    -Werror analogue to suppress under MSVC.
  * there is no .rc anywhere in the tree, so nothing here depends on the RC
    language CMake's Windows-MSVC platform module enables by itself.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# See xz_msvc.py for why these two per-configuration variables rather than
# CMAKE_C_FLAGS / CMAKE_SHARED_LINKER_FLAGS: overriding the per-config ones
# leaves CMake's own initialisation - /machine on the 32-bit leg among it -
# in place.
#
# /MD is restated because this variable is where it lives. libevent's
# cmake_minimum_required is 3.1, so CMP0091 is OLD and CMAKE_MSVC_RUNTIME_
# LIBRARY is not consulted at all; the runtime flag comes only from
# CMAKE_C_FLAGS_<CONFIG>, whose Release default (Platform/Windows-MSVC.cmake)
# is "/MD /O2 /Ob2 /DNDEBUG". Replacing that string without /MD in it would
# hand the build cl's own default, /MT, and a static CRT put 1947 of VX-API's
# 4219 functions into that artefact as MSVC C runtime.
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

# CMAKE_POLICY_VERSION_MINIMUM is insurance against the runner's CMake, not a
# behaviour choice. libevent 2.1.12 declares cmake_minimum_required(VERSION
# 3.1 FATAL_ERROR); CMake 4 refuses a project asking for less than 3.5
# outright, and the windows-2022 image's CMake is whatever the image happens
# to carry that week. Setting the floor to 3.5 is a cache variable, not a
# patch, and it raises the policy version rather than replacing it, so
# nothing changes on a CMake that would have accepted 3.1. On a CMake old
# enough not to know the variable it is an unused-variable warning - measured
# here by passing EVENT__MSVC_STATIC_RUNTIME to a non-MSVC configure of this
# same file, which warned and configured.
#
# NMake Makefiles rather than Ninja or the Visual Studio generator: nmake
# ships with MSVC itself, the generator is single-configuration so
# CMAKE_BUILD_TYPE means what it says and the artefacts land where the paths
# below expect them, and the target architecture comes from the developer
# environment the workflow sets up instead of being named a second time.
#
# The EVENT__DISABLE_* set is copied from the MinGW recipe unchanged, so the
# two artefacts differ in the compiler and not in what was compiled. Keeping
# EVENT__DISABLE_OPENSSL=ON is load-bearing rather than cosmetic: OpenSSL is
# its own family in this corpus, and a runner that happened to carry an
# OpenSSL development install would otherwise get a third DLL and a
# bufferevent_openssl.c worth of glue against it.
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
          '-DEVENT__LIBRARY_TYPE=SHARED -DEVENT__MSVC_STATIC_RUNTIME=OFF '
          '-DEVENT__DISABLE_OPENSSL=ON -DEVENT__DISABLE_TESTS=ON '
          '-DEVENT__DISABLE_SAMPLES=ON -DEVENT__DISABLE_BENCHMARK=ON '
          '%s %s' % (_CFLAGS, _LDFLAGS))


RECIPES = {
    # The same tag as the MinGW recipe, and for the same reason: 2.1.12 is
    # overwhelmingly the most deployed release.
    "libevent_2.1.12_msvc": Recipe(
        family="libevent",
        version="2.1.12",
        upstream="https://github.com/libevent/libevent",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/libevent/libevent.git",
                      git_ref="release-2.1.12-stable"),
        build=[
            BuildStep(_CMAKE),
            # Two steps rather than one --target with two names: multiple
            # targets in a single cmake --build need CMake 3.15, and there is
            # no reason to make this build depend on that. event_extra_shared
            # links against event_core_shared, so the order is upstream's.
            BuildStep("cmake --build build-{arch} --target event_core_shared"),
            BuildStep("cmake --build build-{arch} --target event_extra_shared"),
            # Cheap insurance, as in xz_msvc.py: build.py reports a missing
            # artefact by the path it expected and nothing else, so this puts
            # the names the build actually wrote into the log the workflow
            # prints on failure.
            BuildStep("dir build-{arch}\\bin", allow_failure=True),
        ],
        artifacts=[
            Artifact(path="build-{arch}/bin/event_core.dll",
                     component="event_core.dll",
                     pdb="build-{arch}/bin/event_core.pdb"),
            Artifact(path="build-{arch}/bin/event_extra.dll",
                     component="event_extra.dll",
                     pdb="build-{arch}/bin/event_extra.pdb"),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release, /Zi added); "
                    "/DEBUG /Brepro /OPT:NOREF /OPT:NOICF at link",
        notes="The same two libraries and the same feature set as the MinGW "
              "recipe for this tag, so the artefacts differ in the compiler "
              "rather than in what was built. They are named event_core.dll "
              "and event_extra.dll rather than libevent_core.dll and "
              "libevent_extra.dll because MSVC has no library prefix and "
              "upstream's OUTPUT_NAME on the WIN32 branch is the bare target "
              "name; it is the same library and the same tag. No "
              "dependencies: the OpenSSL backend is disabled, as under "
              "MinGW, so bufferevent_openssl.c is not compiled and no "
              "OpenSSL code can reach this artefact; the rest links only the "
              "CRT, ws2_32 and iphlpapi. Built against the DLL runtime, so "
              "the MSVC C runtime is imported rather than linked in and "
              "stays attributed to data/MSVC. Unlike the MinGW pair, this "
              "build carries none of libevent's GNUC-only warning and "
              "hardening flags - upstream guards that whole list on the "
              "compiler being GCC or Clang - and it is /O2 /Ob2 where the "
              "MinGW build is -O3.",
    ),
}
