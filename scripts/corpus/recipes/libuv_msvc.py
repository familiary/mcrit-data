"""libuv built with MSVC, beside the MinGW builds of the same tags.

Node.js and Electron on Windows are MSVC-built and vendor libuv, so every one
of those sightings is currently answered by GCC code: data/libuv carries only
MinGW artefacts. Upstream's CMake build targets MSVC directly - it carries an
if(MSVC) block, a /we4013 it only applies there, and at 1.52.1 an explicit
cmake_policy(SET CMP0091 NEW) "Enable MSVC_RUNTIME_LIBRARY setting".

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

What was read rather than assumed, in CMakeLists.txt at both pinned tags:

  * the shared target is called "uv" at both versions. 1.52.1 guards it with
    if(LIBUV_BUILD_SHARED) and sets OUTPUT_NAME "uv"; 1.44.2 has no such
    option and declares add_library(uv SHARED ${uv_sources}) unconditionally
    with no OUTPUT_NAME, so the output name is the target name, "uv", there
    too. Both also always declare a static uv_a, which is why --target uv
    matters: SMDA cannot read a .lib.
  * that makes the file **uv.dll**, not the MinGW build's libuv.dll - MSVC's
    CMAKE_SHARED_LIBRARY_PREFIX is empty where GCC's is "lib". Only uv_a
    carries an explicit PREFIX "lib" (1.52.1), and that is the static
    library. The component is recorded as the name this build produces, as
    lz4_msvc.py records lz4.dll against MinGW's liblz4.dll.
  * 1.52.1 sets VERSION/SOVERSION on uv "mirroring the behaviour of
    autotools", but CMake drops both from the file name where the platform
    has no soname - the MinGW recipe's own artefact path, build-<arch>/
    libuv.dll with no version in it, is the evidence for that.
  * nothing sets CMAKE_RUNTIME_OUTPUT_DIRECTORY, so the DLL lands in the
    build root, exactly where the MinGW recipe finds libuv.dll. The PDB
    lands beside it: CMake's MSVC shared-library rule passes
    /pdb:<TARGET_PDB>, that name is the runtime artefact's own prefix and
    base name with a .pdb suffix, and its directory falls back to the
    runtime output directory, which no target here overrides.
  * the if(MSVC) block sets CMAKE_DEBUG_POSTFIX d. That is the Debug
    configuration only and does not touch this Release build.
  * the uv_cflags list is assembled from check_c_compiler_flag probes, so
    the MSVC leg picks up /W4 and the /wd4100-style suppressions and drops
    -Wall and -fno-strict-aliasing by itself. It is not -Werror-shaped; the only
    promotion is /we4013, upstream's own, on calling undeclared functions.
  * BUILD_SHARED_LIBS only selects which target the libuv::libuv alias
    points at (1.52.1) and is unused at 1.44.2. It is passed anyway because
    the MinGW recipe passes it, and an unused cache variable is a warning
    rather than a failure - measured here against a different recipe's
    configure of this same shape.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# See xz_msvc.py for why these two per-configuration variables rather than
# CMAKE_C_FLAGS / CMAKE_SHARED_LINKER_FLAGS: overriding the per-config ones
# leaves CMake's own initialisation - /machine on the 32-bit leg among it -
# in place.
#
# /MD is restated because the two versions get it by different routes and
# only one of them is safe to leave implicit. 1.44.2's cmake_minimum_required
# is 3.4, so CMP0091 is OLD and the runtime flag comes only from
# CMAKE_C_FLAGS_<CONFIG>, whose Release default is "/MD /O2 /Ob2 /DNDEBUG" -
# replacing that string without /MD in it would hand the build cl's own
# default, /MT, and a static CRT put 1947 of VX-API's 4219 functions into
# that artefact as MSVC C runtime. 1.52.1 sets CMP0091 NEW itself, where
# CMake emits -MD from CMAKE_MSVC_RUNTIME_LIBRARY (whose default is
# MultiThreaded$<$<CONFIG:Debug>:Debug>DLL) and leaves it out of the flags
# variable; there the /MD below is simply repeated on the command line, which
# cl accepts. Both routes give /MD, and stating it means neither has to be
# taken on trust.
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
# LIBUV_BUILD_TESTS=OFF and BUILD_SHARED_LIBS=ON are the MinGW recipe's own
# options, carried across unchanged. LIBUV_BUILD_SHARED=ON is added because
# at 1.52.1 that is the switch that actually decides whether the shared
# target exists at all; it does not exist at 1.44.2, where it costs an
# unused-variable warning and nothing else.
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON '
          '-DLIBUV_BUILD_SHARED=ON -DLIBUV_BUILD_TESTS=OFF %s %s'
          % (_CFLAGS, _LDFLAGS))

# 1.44.2 declares cmake_minimum_required(VERSION 3.4) and CMake 4 refuses a
# project asking for less than 3.5 outright, so that leg's success would
# otherwise depend on which CMake the windows-2022 image happens to carry.
# This is a cache variable, not a patch, and it raises the policy floor
# rather than replacing it, so nothing changes on a CMake that would have
# accepted 3.4; on a CMake too old to know the variable it is an
# unused-variable warning. It is not passed to 1.52.1, whose own minimum is
# 3.10 and needs nothing.
_POLICY_FLOOR = ' -DCMAKE_POLICY_VERSION_MINIMUM=3.5'


def _libuv_msvc(version, git_ref, policy_floor=False):
    return Recipe(
        family="libuv",
        version=version,
        upstream="https://github.com/libuv/libuv",
        license="MIT",
        source=Source(git_url="https://github.com/libuv/libuv.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE + (_POLICY_FLOOR if policy_floor else "")),
            BuildStep("cmake --build build-{arch} --target uv"),
            # Cheap insurance, as in xz_msvc.py: build.py reports a missing
            # artefact by the path it expected and nothing else, so this puts
            # the names the build actually wrote into the log the workflow
            # prints on failure.
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/uv.dll", component="uv.dll",
                            pdb="build-{arch}/uv.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release, /Zi added), plus /W4 "
                    "and upstream's own /wd4100-style suppressions from its "
                    "compiler probes; /DEBUG /Brepro /OPT:NOREF /OPT:NOICF "
                    "at link",
        notes="The same tag as the MinGW recipe for this version, so the two "
              "artefacts differ in the compiler rather than in what was "
              "built. Named uv.dll rather than the MinGW build's libuv.dll "
              "because MSVC has no library prefix; it is the same library "
              "and the same tag. Only the shared uv target is built, so the "
              "static uv_a - which SMDA cannot read - and the tests are not "
              "in this run. No dependencies: libuv links only the CRT and "
              "Win32, and is built against the DLL runtime so the MSVC C "
              "runtime is imported rather than linked in and stays "
              "attributed to data/MSVC. The MinGW build is -O3 from CMake's "
              "GCC Release, this one /O2 /Ob2 from CMake's MSVC Release, so "
              "the difference between the two artefacts is the compiler and "
              "its optimiser settings both.",
    )


RECIPES = {
    # What Node 16/18 shipped, so it is vendored very widely - and those
    # vendored copies are compiled by the host project, with MSVC.
    "libuv_1.44.2_msvc": _libuv_msvc("1.44.2", "v1.44.2", policy_floor=True),
    # Current, and the direct counterpart of the newest MinGW artefact.
    "libuv_1.52.1_msvc": _libuv_msvc("1.52.1", "v1.52.1"),
}
