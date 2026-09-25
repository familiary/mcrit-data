"""RE2 built with MSVC, beside the MinGW builds of the same two refs.

The two refs bracket the largest code-level split in this part of the
corpus: 2022-06-01 is the last release before RE2 took a dependency on
Abseil, and 2025-11-05 is built on Abseil throughout. data/re2 carries only
MinGW artefacts for both.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

Keeping Abseil out of the re2 artefact is the whole difficulty here, and the
arrangement is carried across from the MinGW recipe: Abseil is built as
shared libraries and installed into a prefix inside the source tree, and RE2
is then built through its own CMake against that prefix, so Abseil is
imported rather than linked in. Without that, tens of thousands of Abseil
functions would be filed under the re2 family name.

Under MSVC the mechanism is stronger than under MinGW rather than weaker,
and the difference was read in the pinned Abseil tree:

  * absl/copts/AbseilConfigureCopts.cmake sets ABSL_BUILD_DLL TRUE and
    CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON whenever BUILD_SHARED_LIBS is on and
    the compiler is MSVC. CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS is passed here as
    well as by Abseil itself, because it is the switch this whole
    arrangement rests on and it should be visible in the recipe.
  * that puts Abseil into its single-DLL mode, where the sources are
    compiled with ABSL_BUILD_DLL and absl/base/config.h expands ABSL_DLL to
    __declspec(dllexport); consumers get ABSL_CONSUME_DLL as an INTERFACE
    definition and the same macro becomes __declspec(dllimport). So RE2's
    references to Abseil's exported data - not just its functions - resolve
    through real import thunks, which a bare export-all .def would not give.
  * ABSL_ENABLE_INSTALL=ON is what makes the prefix exist, and
    CMAKE_PREFIX_PATH is what RE2's find_package(absl REQUIRED) then finds.
    absl_DIR is passed as well, pointing straight at lib/cmake/absl, so a
    prefix-search failure cannot be mistaken for a missing Abseil.

That chain was verified by running it here, on the one path that does not
need MSVC. Configuring Abseil 20250512.1 with BUILD_SHARED_LIBS=ON plus
ABSL_BUILD_MONOLITHIC_SHARED_LIBS=ON takes the identical ABSL_BUILD_DLL
branch, building and installing it produces one shared abseil_dll plus an
abslConfig.cmake in which absl::strings and its siblings are INTERFACE
IMPORTED targets carrying INTERFACE_COMPILE_DEFINITIONS "ABSL_CONSUME_DLL",
and RE2 configured against that prefix compiled with ABSL_CONSUME_DLL and
linked against abseil_dll alone - no Abseil archive on its link line. The
resulting re2 library defined 42 absl:: symbols and left 38 undefined; every
one of the 42 was a template instantiation over RE2's own types
(CallOnceImpl<re2::Prog::GetDFA...>, raw_hash_set<...re2::DFA::State*...>,
LogMessage::operator<< <re2::InstOp>), which is the inline and template code
any RE2 binary carries, and none of Abseil's own object code was present.
That is the same result the MinGW notes claim, measured rather than assumed.

Both versions go through RE2's own CMake, including 2022-06-01, where the
MinGW recipe compiles the sources directly instead. The reason that recipe
gives for avoiding CMake - that it produces a static archive SMDA cannot
read - is answered by BUILD_SHARED_LIBS, and the coverage worry is answered
by reading RE2_SOURCES at that ref: it is exactly re2/*.cc (all twenty
files) plus util/rune.cc and util/strutil.cc, i.e. the MinGW recipe's
allow-list, file for file. Going through CMake also picks up the defines and
switches upstream applies to a Windows MSVC build, which a hand-written cl
line would have to reproduce by guesswork - and at least one of them,
-DNOMINMAX, is not optional: util/mutex.h includes <windows.h> on _WIN32 and
six of the compiled files use std::min or std::max.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# CMake's MSVC Release default carries no /Zi and no /DEBUG at link, so the
# artefact would come back with no PDB and no names. See xz_msvc.py for why
# the per-configuration variables are overridden rather than CMAKE_CXX_FLAGS
# / CMAKE_SHARED_LINKER_FLAGS. /MD is restated because overriding the
# variable replaces CMake's initialisation of it, and a /MT build files the
# static CRT under this family.
_CXXFLAGS = '-DCMAKE_CXX_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

# NMake Makefiles: nmake ships with MSVC itself, the generator is
# single-configuration so the DLL lands in the build root, and the target
# architecture comes from the developer environment the workflow set up.
#
# CMAKE_POLICY_VERSION_MINIMUM is insurance against the runner's CMake rather
# than a behaviour change: RE2 2022-06-01 declares
# cmake_minimum_required(VERSION 3.10.2), which CMake 4 refuses outright. On
# a CMake that does not know the variable it is an unused cache entry, which
# is a warning and not a failure - verified here against CMake 3.28. Abseil
# and RE2 2025-11-05 declare 3.16 and 3.22, both above the floor, so it does
# nothing to them.
_COMMON = ('-G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release '
           '-DCMAKE_CXX_STANDARD=17 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
           '%s %s' % (_CXXFLAGS, _LDFLAGS))

# RE2_BUILD_TESTING defaults ON at 2022-06-01 and its TESTING_SOURCES include
# util/pcre.cc, a test helper that wants PCRE - which is its own family here.
# Turning it off keeps the build to the library and keeps PCRE out of it.
_RE2_2022 = ('cmake -S . -B build-{arch} ' + _COMMON + ' '
             '-DBUILD_SHARED_LIBS=ON -DCMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON '
             '-DRE2_BUILD_TESTING=OFF -DBUILD_TESTING=OFF')

# Abseil as one DLL, installed into a prefix inside the source tree so
# nothing outside the build is written and so the next architecture cannot
# pick up the previous one's import libraries.
_ABSL_CONFIGURE = ('cmake -S {absl} -B absl-build-{arch} ' + _COMMON + ' '
                   '-DBUILD_TESTING=OFF -DABSL_BUILD_TESTING=OFF '
                   '-DABSL_PROPAGATE_CXX_STD=ON -DABSL_ENABLE_INSTALL=ON '
                   '-DBUILD_SHARED_LIBS=ON -DABSL_MSVC_STATIC_RUNTIME=OFF '
                   '-DCMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON '
                   '-DCMAKE_MSVC_DEBUG_INFORMATION_FORMAT=ProgramDatabase '
                   '-DCMAKE_INSTALL_PREFIX={source_root}/absl-prefix-{arch}')

_ABSL_INSTALL = "cmake --build absl-build-{arch} --target install"

# RE2_INSTALL is off because nothing is installed from this tree.
_RE2_2025 = ('cmake -S . -B build-{arch} ' + _COMMON + ' '
             '-DBUILD_SHARED_LIBS=ON -DCMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON '
             '-DRE2_INSTALL=OFF -DRE2_BUILD_TESTING=OFF -DBUILD_TESTING=OFF '
             '-DCMAKE_PREFIX_PATH={source_root}/absl-prefix-{arch} '
             '-Dabsl_DIR={source_root}/absl-prefix-{arch}/lib/cmake/absl')

# The target is "re2" at both refs, and MSVC has no library prefix, so the
# DLL is re2.dll where the MinGW 2025 build produces libre2.dll. The linker
# PDB is re2.pdb beside it: CMake's MSVC shared-library rule passes
# /pdb:<TARGET_PDB>, that name is the runtime artefact's own base name, and
# its directory falls back to the runtime output directory - which neither
# RE2 CMakeLists overrides, so it is the build root.
_ARTIFACTS = [Artifact(path="build-{arch}/re2.dll", component="re2.dll",
                       pdb="build-{arch}/re2.pdb")]

_FLAGS = ("/MD /O2 /Ob2 /Zi /std:c++17 (CMake Release, /Zi added), plus the "
          "switches RE2's own CMakeLists applies to an MSVC/WIN32 build: "
          "/utf-8, /wd4100 /wd4201 /wd4456 /wd4457 /wd4702 /wd4815, "
          "-DUNICODE -D_UNICODE -DSTRICT -DNOMINMAX "
          "-D_CRT_SECURE_NO_WARNINGS -D_SCL_SECURE_NO_WARNINGS; "
          "/DEBUG /Brepro /OPT:NOREF /OPT:NOICF at link")


RECIPES = {
    # Last standalone release, before the Abseil dependency.
    "re2_2022-06-01_msvc": Recipe(
        family="re2",
        version="2022-06-01",
        upstream="https://github.com/google/re2",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/google/re2.git",
                      git_ref="2022-06-01"),
        build=[
            BuildStep(_RE2_2022),
            BuildStep("cmake --build build-{arch} --target re2"),
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=_ARTIFACTS,
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS,
        notes="Standalone; no Abseil, so there is nothing to keep out of this "
              "one. Built through RE2's own CMake rather than by compiling "
              "the sources directly as the MinGW recipe does, but over the "
              "same file set: RE2_SOURCES at this ref is re2/*.cc plus "
              "util/rune.cc and util/strutil.cc, which is the MinGW recipe's "
              "allow-list exactly. re2/testing and util/pcre.cc are not "
              "built, so no PCRE code reaches this artefact. The flags do "
              "differ from the MinGW pair by more than the code generator: "
              "upstream's CMakeLists adds a set of Windows and MSVC defines "
              "that the direct gcc line never received, and they are listed "
              "in build_flags. Built against the DLL runtime, so the MSVC C "
              "runtime is imported rather than linked in and stays "
              "attributed to data/MSVC.",
    ),
    # Current, and Abseil-based throughout.
    "re2_2025-11-05_msvc": Recipe(
        family="re2",
        version="2025-11-05",
        upstream="https://github.com/google/re2",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/google/re2.git",
                      git_ref="2025-11-05"),
        extra_sources={
            # The same Abseil release the MinGW recipe pins, which is the one
            # this RE2 tag's own MODULE.bazel names. It decides both the
            # inline code RE2 instantiates and the DLL it imports from, so
            # the MSVC and MinGW artefacts have to agree on it or they are
            # not comparable.
            "absl": Source(git_url="https://github.com/abseil/abseil-cpp.git",
                           git_ref="20250512.1"),
        },
        build=[
            BuildStep(_ABSL_CONFIGURE),
            BuildStep(_ABSL_INSTALL),
            BuildStep(_RE2_2025),
            BuildStep("cmake --build build-{arch} --target re2"),
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=_ARTIFACTS,
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS,
        notes="Upstream's own re2 DLL. Abseil is built alongside as a DLL and "
              "only imported, so no Abseil object code is attributed to re2; "
              "what is present is the Abseil inline and template code RE2 "
              "instantiates over its own types, as it would be in any RE2 "
              "binary. Building that same arrangement on the one path that "
              "can be run without MSVC measured it at 42 such instantiations "
              "against 38 imported Abseil symbols, with no Abseil archive on "
              "the link line. Note that the Abseil DLL beside this artefact "
              "is not itself collected here - data/abseil gets its MSVC "
              "sample from abseil_msvc.py, at the LTS tag rather than at this "
              "one. Built against the DLL runtime, so the MSVC C runtime is "
              "imported rather than linked in. Expect a visible share of MSVC "
              "STL instantiations in this sample, shared with the abseil and "
              "nlohmann_json MSVC artefacts; that is what the glue baseline "
              "is for and is not worked around here.",
    ),
}
