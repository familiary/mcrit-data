"""Legacy PCRE (PCRE1) built with MSVC, beside the MinGW build of 8.45.

8.45 is the end of the line for PCRE1 and there will never be another
version, but a great deal of legacy Windows software still carries it - and
that software is MSVC-built, where data/pcre holds GCC code only.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

What was read rather than assumed, in the 8.45 tarball's CMakeLists.txt:
  * ``SET(BUILD_SHARED_LIBS OFF CACHE BOOL …)``, so an unmodified configure
    produces the static ``pcre.lib`` that SMDA cannot read.
  * the library target is plain ``pcre`` - there is no separate shared
    target - and the ``PREFIX ""`` override is inside
    ``IF(MINGW AND NOT PCRE_STATIC)``. MSVC has no library prefix of its own,
    so the file is **pcre.dll**, where the MinGW artefact is libpcre.dll.
  * ``IF(NOT BUILD_SHARED_LIBS) SET(PCRE_STATIC 1)``, and ``pcre_internal.h``
    keys its ``__declspec(dllexport)`` off ``_WIN32 && !PCRE_STATIC``. So
    asking for a shared build is also what makes the DLL export its API;
    nothing else has to be passed and no source is touched.
  * ``pcrecpp`` is a separate C++ library. It stays off, as under MinGW: what
    is wanted here is the C engine.
  * sljit, PCRE1's JIT, has explicit ``_MSC_VER >= 1400`` paths in
    ``sljitNativeX86_common.c`` (the CPUID probe) and in
    ``sljitConfigInternal.h``, so its MSVC support is upstream's rather than
    something this recipe is hoping for. It has not been *compiled* with
    v143 here - see the confidence note below.

Two things about this family are worth stating plainly rather than burying.

``CMAKE_MINIMUM_REQUIRED(VERSION 2.8.5)``: CMake 4 refuses that outright, so
``-DCMAKE_POLICY_VERSION_MINIMUM=3.5`` is passed. lz4_msvc.py declined the
same workaround for lz4 1.9.4, and the difference is that lz4 had a newer tag
that needed nothing while PCRE1 has no newer anything. The variable was
measured on CMake 3.28 against this exact tree: it is reported as unused and
the configure succeeds unchanged, so it costs a warning line where it is not
needed and saves the family where it is.

2.8.5 also puts CMP0091 firmly OLD, which means CMake writes the runtime
library into ``CMAKE_C_FLAGS_<CONFIG>`` - the variable this recipe replaces.
The /MD below is therefore the only thing standing between this build and a
static CRT; it is not decoration.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# See xz_msvc.py for why these two variables rather than CMAKE_C_FLAGS /
# CMAKE_SHARED_LINKER_FLAGS: CMake's MSVC Release default carries neither /Zi
# nor /DEBUG, so the artefact would come back with no PDB and no names, and
# overriding the per-configuration variables leaves CMake's own
# initialisation - /machine on the 32-bit leg among it - in place. The /MD in
# it is load-bearing here, as the docstring explains.
_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

# NMake Makefiles: nmake ships with MSVC itself, the generator is
# single-configuration so the DLL lands in the build root, and the target
# architecture comes from the developer environment the workflow sets up.
#
# The option block is the MinGW recipe's, minus the cross-compilation
# variables. PCRE1's CMake defaults JIT and UTF *off*, unlike PCRE2's, so
# both have to be asked for to match what a distribution or a vendored copy
# actually ships - that reasoning is the MinGW recipe's and it does not
# change with the compiler.
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
          '-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON '
          '-DPCRE_SUPPORT_JIT=ON -DPCRE_SUPPORT_UTF=ON '
          '-DPCRE_SUPPORT_UNICODE_PROPERTIES=ON -DPCRE_BUILD_PCRECPP=OFF '
          '-DPCRE_BUILD_TESTS=OFF -DPCRE_BUILD_PCREGREP=OFF '
          '%s %s' % (_CFLAGS, _LDFLAGS))


RECIPES = {
    "pcre_8.45_msvc": Recipe(
        family="pcre",
        version="8.45",
        upstream="https://www.pcre.org/",
        license="BSD-3-Clause",
        # The same tarball and the same digest the MinGW recipe pins: the
        # upstream repository moved to PCRE2 and the 8.x sources only exist
        # as the SourceForge archives.
        source=Source(
            url="https://downloads.sourceforge.net/project/pcre/pcre/8.45/"
                "pcre-8.45.tar.bz2",
            sha256="4dae6fdcd2bb0bb6c37b5f97c33c2be954da743985369cddac3546e3218bffb8"),
        build=[
            BuildStep(_CMAKE),
            # pcreposix is a second, separate DLL that links against this
            # one; naming the target keeps the build to the engine, which is
            # the only thing data/pcre holds.
            BuildStep("cmake --build build-{arch} --target pcre"),
            # Cheap insurance, as in xz_msvc.py: build.py reports a missing
            # artefact by the path it expected and nothing else, and this
            # puts the names the build actually wrote into the log the
            # workflow prints on failure.
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/pcre.dll", component="pcre.dll",
                            pdb="build-{arch}/pcre.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release, /Zi added), JIT and UTF "
                    "enabled; /DEBUG /Brepro /OPT:NOREF /OPT:NOICF at link",
        notes="The same CMake options as the MinGW recipe, with JIT, UTF and "
              "Unicode properties on, so the two artefacts differ in the "
              "compiler rather than in the feature set. Named pcre.dll rather "
              "than the MinGW build's libpcre.dll because upstream applies "
              "the empty library prefix only under MINGW and MSVC has none of "
              "its own. Only the 8-bit engine is built - pcreposix is a "
              "separate DLL and the C++ wrapper is deliberately off. No "
              "dependencies: PCRE links only the CRT, and is built against "
              "the DLL runtime so the MSVC C runtime is imported rather than "
              "linked in and stays attributed to data/MSVC. "
              "CMAKE_POLICY_VERSION_MINIMUM is passed because upstream's "
              "cmake_minimum_required is 2.8.5, which CMake 4 rejects; it is "
              "reported as unused, harmlessly, by older CMake.",
    ),
}
