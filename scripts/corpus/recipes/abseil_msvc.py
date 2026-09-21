"""Abseil built with MSVC, beside the MinGW build of the same LTS.

Abseil reaches analysts almost entirely inside protobuf, gRPC and Chrome
derivatives, all of which are MSVC-built, and data/abseil carries only MinGW
artefacts. It is also the family most exposed to the MSVC STL question: a
large C++ library compiled by cl instantiates a great deal of std:: into
itself, and abseil, re2 and protobuf will share those instantiations. That
is expected and is the glue baseline's problem, not something this recipe
works around.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

The MinGW recipe has to link Abseil's pile of static archives into one DLL
by hand with --whole-archive, because SMDA cannot read a .lib and Abseil
marks nothing dllexport. Under MSVC none of that is necessary, and the
reason was read in the pinned tree rather than inferred:

  * absl/copts/AbseilConfigureCopts.cmake says
      if (BUILD_SHARED_LIBS AND (MSVC OR ABSL_BUILD_MONOLITHIC_SHARED_LIBS))
        set(ABSL_BUILD_DLL TRUE)
        set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
    so under MSVC, BUILD_SHARED_LIBS=ON puts Abseil into its own DLL mode and
    turns CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS on by itself.
  * absl/CMakeLists.txt then calls absl_make_dll(), and CMake/AbseilDll.cmake
    builds exactly one SHARED target, "abseil_dll", out of the whole
    ABSL_INTERNAL_DLL_FILES list, compiling it with ABSL_BUILD_DLL defined.
    absl/base/config.h turns that into "#define ABSL_DLL
    __declspec(dllexport)". So this is upstream's own supported single-DLL
    arrangement with real dllexport annotations, not an export-everything
    trick - which is why it is also the right thing for re2_msvc.py to import
    from.
  * every absl::* target that is part of the DLL becomes an INTERFACE library
    pointing at abseil_dll (CMake/AbseilHelpers.cmake, the "dll" build type).
  * the top-level CMakeLists sets CMAKE_RUNTIME_OUTPUT_DIRECTORY to
    ${CMAKE_BINARY_DIR}/bin, so on Windows - where a DLL is the RUNTIME
    artefact - the file is build-<arch>/bin/abseil_dll.dll, and the linker
    PDB follows the runtime output directory because nothing sets
    PDB_OUTPUT_DIRECTORY.
  * ABSL_MSVC_STATIC_RUNTIME defaults OFF, and the top-level CMakeLists then
    sets CMAKE_MSVC_RUNTIME_LIBRARY to MultiThreaded$<$<CONFIG:Debug>:Debug>DLL,
    i.e. /MD. It is passed explicitly below anyway, because a /MT build came
    back 46% MSVC C runtime.

Verified by running it, on the one path that can be exercised without MSVC:
configuring the pinned tree with BUILD_SHARED_LIBS=ON plus
ABSL_BUILD_MONOLITHIC_SHARED_LIBS=ON takes the identical ABSL_BUILD_DLL
branch, and "cmake --build --target help" then lists abseil_dll as the only
library target beside six small leftovers (see notes).

Only 20250127.1 is covered. The other MinGW version, 20220623.1, declares
cmake_minimum_required(VERSION 3.5), which CMake 4 refuses outright; that is
a runner-image dependency this wave should not take on, and unlike cJSON it
is avoidable by simply covering the current LTS.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# CMake's MSVC Release default carries no /Zi and no /DEBUG at link. Abseil
# additionally sets cmake_policy(SET CMP0141 NEW), under which the debug
# information format comes from CMAKE_MSVC_DEBUG_INFORMATION_FORMAT and is
# empty for Release; that variable is therefore set as well as /Zi being put
# in the flags, so the PDB does not depend on which of the two mechanisms the
# runner's CMake honours. A doubled /Zi is idempotent.
#
# Only the per-configuration variables are overridden. Abseil's own
# ABSL_MSVC_FLAGS (/W3 /bigobj and the /wd... list, -DNOMINMAX,
# -DWIN32_LEAN_AND_MEAN, -D_CRT_SECURE_NO_WARNINGS, -D_SCL_SECURE_NO_WARNINGS,
# -D_ENABLE_EXTENDED_ALIGNED_STORAGE) arrive through target_compile_options
# and ABSL_MSVC_LINKOPTS (-ignore:4221) through the target's link libraries,
# so neither is displaced by this. /bigobj in particular is upstream's and
# is load-bearing for a C++ library this size.
_CXXFLAGS = '-DCMAKE_CXX_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

# NMake Makefiles: nmake ships with MSVC itself, the generator is
# single-configuration so CMAKE_BUILD_TYPE means what it says, and the target
# architecture comes from the developer environment the workflow set up.
#
# BUILD_TESTING=OFF and ABSL_BUILD_TESTING=OFF are both named: the first is
# CTest's, the second Abseil's own, and it is the second that decides whether
# the build wants GoogleTest at all.
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17 '
          '-DBUILD_TESTING=OFF -DABSL_BUILD_TESTING=OFF '
          '-DABSL_PROPAGATE_CXX_STD=ON -DBUILD_SHARED_LIBS=ON '
          '-DABSL_MSVC_STATIC_RUNTIME=OFF '
          '-DCMAKE_MSVC_DEBUG_INFORMATION_FORMAT=ProgramDatabase '
          '%s %s' % (_CXXFLAGS, _LDFLAGS))


RECIPES = {
    "abseil_20250127.1_msvc": Recipe(
        family="abseil",
        version="20250127.1",
        upstream="https://github.com/abseil/abseil-cpp",
        license="Apache-2.0",
        source=Source(git_url="https://github.com/abseil/abseil-cpp.git",
                      git_ref="20250127.1"),
        build=[
            BuildStep(_CMAKE),
            # abseil_dll is the whole library; the six leftover targets are
            # not part of it and depend on it rather than the other way
            # round, so naming it keeps the build to one link.
            BuildStep("cmake --build build-{arch} --target abseil_dll"),
            # Cheap insurance, as in xz_msvc.py: build.py reports a missing
            # artefact by the path it expected and nothing else, so this puts
            # the names the build actually wrote into the log the workflow
            # prints on failure.
            BuildStep("dir build-{arch}\\bin", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/bin/abseil_dll.dll",
                            component="abseil_dll.dll",
                            pdb="build-{arch}/bin/abseil_dll.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi /std:c++17 (CMake Release, /Zi added) "
                    "plus Abseil's own ABSL_MSVC_FLAGS: /W3 /bigobj /wd4005 "
                    "/wd4068 /wd4180 /wd4244 /wd4267 /wd4503 /wd4800 "
                    "-DNOMINMAX -DWIN32_LEAN_AND_MEAN "
                    "-D_CRT_SECURE_NO_WARNINGS -D_SCL_SECURE_NO_WARNINGS "
                    "-D_ENABLE_EXTENDED_ALIGNED_STORAGE, and -DABSL_BUILD_DLL "
                    "on the DLL's own sources; /DEBUG /Brepro /OPT:NOREF "
                    "/OPT:NOICF and upstream's -ignore:4221 at link",
        notes="Upstream's own single-DLL MSVC arrangement (ABSL_BUILD_DLL), "
              "not the hand-rolled --whole-archive link the MinGW recipe "
              "needs, so the exports are real __declspec(dllexport) "
              "annotations rather than a generated .def. Includes the "
              "vendored CCTZ, so google/cctz is not processed separately, as "
              "under MinGW. One honest difference from the MinGW artefact: "
              "six small targets are outside upstream's DLL file list at this "
              "tag - decode_rust_punycode, demangle_rust, "
              "log_internal_structured_proto, poison, tracing_internal and "
              "utf8_for_code_point - and their code is therefore absent here "
              "where --whole-archive sweeps it into the MinGW DLL. Building "
              "those six targets from the pinned tree measured them at about "
              "32 KB of static archive carrying six external functions, "
              "against a DLL of well over a megabyte, so the gap is real but "
              "small; it is named rather than estimated away. No external "
              "dependencies, and built against the DLL runtime so the MSVC C "
              "runtime is imported rather than linked in and stays "
              "attributed to data/MSVC.",
    ),
}
