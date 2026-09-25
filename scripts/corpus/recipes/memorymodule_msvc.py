"""MemoryModule built with MSVC, beside the MinGW build of the same commit.

MemoryModule is copy-pasted verbatim into loaders and packers and compiled by
whatever the host project uses, which on Windows is MSVC far more often than
GCC - so for this family the MSVC artefact is arguably the one that should
have existed first. data/MemoryModule carries only MinGW builds.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

Only the 2019-02-24 master commit is covered. At ``v0_0_4`` the tree has no
CMakeLists.txt at all - its only MSVC path is ``example/DllMemory.sln`` with
two VS2008-format ``.vcproj`` files [read, full 19-file tree at that tag],
which MSBuild v143 cannot consume without a ``devenv /upgrade``. That version
therefore needs two hand-written ``cl`` lines rather than an upstream build
file, and it is left for a later wave rather than guessed at now.

What was read rather than assumed, at commit 5f83e41c:

  * the root CMakeLists.txt puts its whole cross-compiling block behind
    ``if (NOT MSVC)`` - compiler names, CMAKE_SYSTEM_NAME, the windres rule -
    so under MSVC none of it applies and the ``PLATFORM`` cache variable the
    MinGW recipe drives the build with is unused. Under MSVC it instead does
    ``add_definitions("-W4")``.
  * ``MemoryModule`` is a STATIC library and ``DllLoader`` is an executable
    that links it, so DllLoader.exe carries all of MemoryModule.c - the same
    arrangement the MinGW artefact has. UNICODE and TESTSUITE are upstream
    options and both default to OFF, matching the MinGW build.
  * ``set_target_properties(... SUFFIX ".exe")`` and the ``--image-base``
    link flags are also inside ``if (NOT MSVC)``; MSVC gets .exe anyway, so
    the component name is unchanged.
  * ``add_subdirectory(tests)`` is unconditional, but tests/CMakeLists.txt
    only declares the TestSuite target - nothing in it runs at configure
    time - so naming ``--target DllLoader`` is enough to keep it out of the
    build. That matters: the MinGW recipe already records that the default
    target fails in tests/ after the loader binaries have linked fine.
  * ``add_library(MemoryModule STATIC MemoryModule.c ...)`` means CMake
    compiles MemoryModule.c as C here. Upstream's GNU makefiles, which the
    MinGW recipe drives, compile the same file with g++ - so the static
    helpers carry C++ mangling in the MinGW artefact and C names in this one.
    Neither affects code matching.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# See xz_msvc.py for why the per-configuration variables and not CMAKE_C_FLAGS
# / CMAKE_EXE_LINKER_FLAGS: CMake's MSVC Release default is "/MD /O2 /Ob2
# /DNDEBUG" with no /Zi and no /DEBUG at link, so the artefact would come back
# with no PDB and no names, and overriding the _RELEASE variables leaves
# CMake's own initialisation - /machine on the 32-bit leg among it - in place.
# Both languages are set because DllLoader.cpp is C++ and MemoryModule.c is C.
#
# /MD rather than cl's default /MT: a static CRT put 1947 of VX-API's 4219
# functions into that artefact as MSVC C runtime, duplicating data/MSVC.
_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_CXXFLAGS = '-DCMAKE_CXX_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
# /DEBUG so a PDB is written at all, /Brepro so the PE carries no build
# timestamp and two runs of identical source record the same sha256, and
# /OPT:NOREF /OPT:NOICF so unreferenced and identically-compiled routines both
# survive as separate reference samples. /INCREMENTAL:NO is CMake's own
# Release default and is restated because setting the variable replaces it.
_LDFLAGS = ('-DCMAKE_EXE_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

# NMake Makefiles rather than Ninja or the Visual Studio generator: nmake
# ships with MSVC itself, the generator is single-configuration so
# CMAKE_BUILD_TYPE means what it says and the binaries land beside their
# source directories rather than under a Release/ subdirectory, and the target
# architecture comes from the developer environment the workflow set up.
#
# CMAKE_POLICY_VERSION_MINIMUM is insurance, not a requirement: upstream's
# cmake_minimum_required is 2.8.7, which CMake 3.x accepts with a deprecation
# warning and CMake 4 refuses outright. It is a cache variable, so passing it
# is not a patch, and on a CMake that does not know it the configure reports
# an unused variable and continues either way. lz4_msvc.py skipped a version
# over exactly this; here there is no second version to fall back to.
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
          '%s %s %s' % (_CFLAGS, _CXXFLAGS, _LDFLAGS))


RECIPES = {
    # The same commit the MinGW recipe pins: master carries six years of
    # post-tag changes that alter code shape - binary-search export lookup
    # (2017), the case-sensitive name fix (2018) and the >4 GB span fix.
    "MemoryModule_2019-02-24_msvc": Recipe(
        family="MemoryModule",
        version="2019-02-24",
        upstream="https://github.com/fancycode/MemoryModule",
        license="MPL-2.0",
        source=Source(git_url="https://github.com/fancycode/MemoryModule.git",
                      git_ref="5f83e41c3a3e7c6e8284a5c1afa5a38790809461"),
        build=[
            BuildStep(_CMAKE),
            # Only the loader, never the default target: upstream's tests/
            # target fails to link and does so after the binary this recipe
            # wants has already been produced.
            BuildStep("cmake --build build-{arch} --target DllLoader"),
            # build.py reports a missing artefact by the path it expected and
            # nothing else; this puts what the build actually wrote into the
            # log the workflow prints on failure.
            BuildStep("dir build-{arch}\\example\\DllLoader",
                      allow_failure=True),
        ],
        artifacts=[
            Artifact(path="build-{arch}/example/DllLoader/DllLoader.exe",
                     component="DllLoader.exe",
                     pdb="build-{arch}/example/DllLoader/DllLoader.pdb"),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi /W4 (CMake Release, /Zi added; /W4 is "
                    "upstream's own MSVC branch); /DEBUG /Brepro /OPT:NOREF "
                    "/OPT:NOICF at link",
        notes="DllLoader.exe with MemoryModule.c linked in, the same "
              "component the MinGW recipe files. Two differences from that "
              "artefact beyond the compiler, both upstream's own doing: this "
              "build comes from upstream's CMakeLists, which compiles "
              "MemoryModule.c as C, where the GNU makefiles the MinGW recipe "
              "drives compile it with g++; and the MinGW build links the GCC "
              "runtime statically while this one imports the MSVC C runtime, "
              "which therefore stays attributed to data/MSVC. The MinGW "
              "recipe's -O2 is its own override of an upstream -O0 default; "
              "CMake's MSVC Release is /O2 /Ob2 with no such default to "
              "override. No dependencies.",
    ),
}
