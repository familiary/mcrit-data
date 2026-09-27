"""cJSON built with MSVC, beside the MinGW builds of the same tags.

cJSON is vendored into other people's trees more often than it is linked as
a library, and a vendored copy is compiled by whatever the host project uses
- which on Windows is cl far more often than gcc. data/cJSON currently holds
six MinGW artefacts and nothing else, so every such sighting is answered by
GCC code.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

What was read rather than assumed, in CMakeLists.txt at both pinned tags:
  * the library target is called "cjson" (set(CJSON_LIB cjson)), and MSVC has
    no library prefix, so the DLL is cjson.dll where the MinGW build produces
    libcjson.dll. The component is recorded as the name this build writes.
  * BUILD_SHARED_LIBS defaults to ON and selects SHARED for that target;
    without it the build is a static cjson.lib, which SMDA cannot read.
  * ENABLE_PUBLIC_SYMBOLS defaults to ON and does
    add_definitions(-DCJSON_EXPORT_SYMBOLS -DCJSON_API_VISIBILITY), which in
    cJSON.h expands CJSON_PUBLIC to "__declspec(dllexport) type __stdcall"
    on Windows. So the DLL exports its API without this recipe asking for it,
    and there is no need for CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS here.
  * ENABLE_CUSTOM_COMPILER_FLAGS - the option that shapes the MinGW artefacts
    with -std=c89 -fstack-protector-strong -fvisibility=hidden - is gated on
    "${CMAKE_C_COMPILER_ID}" being GNU or Clang at all three tags, so under
    MSVC the whole list is empty but for the -fvisibility=hidden that
    ENABLE_PUBLIC_SYMBOLS appends outside the gate. That one is run through
    CHECK_C_COMPILER_FLAG, and CMake's shared fail patterns include
    'ignoring unknown option' and 'warning D9002' (Modules/
    CMakeCheckCompilerFlagCommonPatterns.cmake, read here), which is exactly
    what cl says about it. So it is rejected rather than silently accepted.
    The MSVC artefacts therefore differ from the MinGW ones by more than the
    code generator, and build_flags below says so rather than copying the
    MinGW string.
  * cJSON.c includes only string.h, stdio.h, math.h, stdlib.h, limits.h,
    ctype.h, float.h and locale.h at both tags - nothing POSIX-only.

Two of the three MinGW versions are covered. 1.7.19 is the counterpart of
the newest MinGW artefact; 1.6.0 is the one the MinGW recipe measured as
genuinely different code (27-41% of PicHashes shared with either 1.7.x,
against 70-74% between 1.7.15 and 1.7.19). 1.7.15 is left out because under
MSVC it would be the third rendering of the same parser.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# CMake's MSVC Release default carries no /Zi and no /DEBUG at link, so the
# artefact would come back with no PDB and no names. See xz_msvc.py for why
# the per-configuration variables are overridden rather than CMAKE_C_FLAGS /
# CMAKE_SHARED_LINKER_FLAGS: that leaves CMake's own initialisation, /machine
# on the 32-bit leg among it, in place.
#
# /MD is not decoration here. All three cJSON tags declare a
# cmake_minimum_required below 3.15, so CMP0091 is OLD and the C runtime flag
# lives in CMAKE_C_FLAGS_RELEASE itself rather than in the
# CMAKE_MSVC_RUNTIME_LIBRARY abstraction - overriding that variable without
# restating /MD would hand the build cl's default /MT and file the static CRT
# under cJSON, which is what put 1947 of VX-API's 4219 functions in that
# artefact. /INCREMENTAL:NO is CMake's own Release default, restated because
# setting the variable replaces it.
_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

# NMake Makefiles rather than Ninja or the Visual Studio generator: nmake
# ships with MSVC itself, the generator is single-configuration so the DLL
# lands in the build root rather than under a Release/ subdirectory, and the
# target architecture comes from the developer environment the workflow set
# up instead of being named a second time.
#
# CMAKE_POLICY_VERSION_MINIMUM is insurance against the runner's CMake, not a
# behaviour change: 1.6.0 declares cmake_minimum_required(VERSION 2.8.5) and
# 1.7.19 declares 3.0, both of which CMake 4 refuses outright. On a CMake
# that does not know the variable it is an unused cache entry - verified here
# against CMake 3.28, which configures cJSON 1.6.0 successfully and prints
# "Manually-specified variables were not used by the project". Both tags
# declare below 3.5, so this is not a choice between versions: without it the
# family's success depends on which CMake the runner image happens to carry.
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
          '-DBUILD_SHARED_LIBS=ON -DENABLE_CJSON_TEST=Off '
          '-DBUILD_SHARED_AND_STATIC_LIBS=Off %s %s' % (_CFLAGS, _LDFLAGS))

_FLAGS = ("/MD /O2 /Ob2 /Zi (CMake Release, /Zi added); "
          "-DCJSON_EXPORT_SYMBOLS -DCJSON_API_VISIBILITY from cJSON's own "
          "ENABLE_PUBLIC_SYMBOLS default; /DEBUG /Brepro /OPT:NOREF "
          "/OPT:NOICF at link. Unlike the MinGW pair, none of cJSON's "
          "ENABLE_CUSTOM_COMPILER_FLAGS list reaches this build: the list is "
          "gated on GNU/Clang and the -fvisibility=hidden appended outside "
          "that gate is rejected by CHECK_C_COMPILER_FLAG under cl. So there "
          "is no -std=c89, no -fstack-protector-strong and no -Werror here")


def _cjson_msvc(version, git_ref):
    return Recipe(
        family="cJSON",
        version=version,
        upstream="https://github.com/DaveGamble/cJSON",
        license="MIT",
        source=Source(git_url="https://github.com/DaveGamble/cJSON.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} --target cjson"),
            # Cheap insurance, as in xz_msvc.py: build.py reports a missing
            # artefact by the path it expected and nothing else, so this puts
            # the names the build actually wrote into the log the workflow
            # prints on failure.
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/cjson.dll",
                            component="cjson.dll",
                            pdb="build-{arch}/cjson.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS,
        notes="The same two tags as the MinGW recipe, so the artefacts can be "
              "compared directly - but the comparison is not compiler-only: "
              "cJSON's own custom flag list is GCC/Clang-gated and does not "
              "apply here, so this code is not -std=c89 and is not stack-"
              "protected, and these artefacts do not import __stack_chk_fail "
              "the way all six MinGW ones do. Named cjson.dll rather than the "
              "MinGW build's libcjson.dll because MSVC has no library prefix; "
              "same target, same source. The exported API is __stdcall, which "
              "on the 32-bit leg means decorated export names. No "
              "dependencies: cJSON is one translation unit over the C "
              "standard library, and is built against the DLL runtime so the "
              "MSVC C runtime is imported rather than linked in and stays "
              "attributed to data/MSVC.",
    )


RECIPES = {
    # The pre-1.7 parser, and the tag the MinGW recipe measured as carrying
    # genuinely different code from the 1.7 series.
    "cJSON_1.6.0_msvc": _cjson_msvc("1.6.0", "v1.6.0"),
    # Current, and the direct counterpart of the newest MinGW artefact.
    "cJSON_1.7.19_msvc": _cjson_msvc("1.7.19", "v1.7.19"),
}
