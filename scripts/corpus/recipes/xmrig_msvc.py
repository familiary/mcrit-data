"""XMRig 6.25.0 built with MSVC, beside the MinGW and Linux builds of the tag.

Issue #8; xmrig.py says what is built, what is left out and how the vendored
trees are filed. Miners are shipped as Windows PE and the release builds are
MSVC, so this is the axis a Windows sample is most likely to match.

XMRig's flags.cmake replaces CMAKE_C_FLAGS_RELEASE and CMAKE_CXX_FLAGS_RELEASE
outright for MSVC with `/MP /MT /O2 /Oi /DNDEBUG /GL`: the static C runtime,
which would put the MSVC CRT in the image under XMRig's name, and
whole-program optimisation, which this corpus excludes. It touches no other
configuration, so the build type is `Corpus` (as in xmrig.py) and carries
`/MD /O2 /Oi /DNDEBUG /Zi` and the usual link switches: /DEBUG for a PDB,
/Brepro, /INCREMENTAL:NO, /OPT:NOREF /OPT:NOICF.

libuv (uv.dll) and OpenSSL (libcrypto and libssl, built no-asm as
openssl_msvc.py does) are built from the pinned sources and linked through
their import libraries. FindOpenSSL's MSVC branch reads LIB_EAY_RELEASE and
SSL_EAY_RELEASE and, because XMRig forces OPENSSL_USE_STATIC_LIBS, would look
for libcrypto_static.lib; presetting the two cache entries to the import
libraries is what makes the miner link the DLLs.

randomx.cmake adds jit_compiler_x86_static.asm under MSVC with no test of the
pointer size, and ml.exe is the 16/32-bit assembler on a 32-bit target, so
the x86 leg passes -DWITH_ASM=OFF, which is also what cpu.cmake does for any
32-bit build; both randomx.cmake and asm.cmake then take their portable
branches, the same sources the Linux and MinGW x86 artefacts use.

Built on windows-2022: 14,377 functions on x64 and 14,593 on x86 after 2,307
and 2,179 compiler-runtime functions were removed. 123 and 118 more, the
llhttp, Argon2/Blake2b, ed25519 (load_3, load_4), rapidjson, standard library
and __scrt_common_main_seh functions that `validate --deep` reported and that are shown to be those
libraries' (_stack_vendored.py), were then removed by exact name from the
committed archives without a rebuild (Recipe.exclude_functions;
excluded_function_count), which leaves 14,254 and 14,475. About 6,000 of the
kept ones are `std::` instantiations; MSVC emits the standard library's templates into the
image and /OPT:NOREF keeps every unreferenced COMDAT, so the count is four
times the GCC one and describes an MSVC-built miner, not an inflation.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _stack_deps as deps
from . import _stack_vendored as vendored


_OPT = "/MD /O2 /Oi /DNDEBUG /Zi"

# Build type Corpus: XMRig's flags.cmake replaces CMAKE_C/CXX_FLAGS_RELEASE
# outright with "/MP /MT /O2 /Oi /DNDEBUG /GL", i.e. the static CRT and
# whole-program optimisation, both of which this corpus excludes. It touches
# no other configuration's flags, so a configuration of our own carries
# exactly what the corpus wants.
_CONFIG = ('-DCMAKE_BUILD_TYPE=Corpus -DCMAKE_C_FLAGS_CORPUS="%s" '
           '-DCMAKE_CXX_FLAGS_CORPUS="%s" '
           '-DCMAKE_EXE_LINKER_FLAGS_CORPUS="%s" '
           "-DWITH_HWLOC=OFF -DWITH_OPENCL=OFF -DWITH_CUDA=OFF"
           % (_OPT, _OPT, deps.MSVC_LINK))

_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" ' + _CONFIG + " "
          + deps.msvc_dep_options())

RECIPES = {
    "XMRig_6.25.0_msvc": Recipe(
        family="XMRig",
        version="6.25.0",
        upstream="https://github.com/xmrig/xmrig",
        license="GPL-3.0-or-later (SPDX identifier in src/version.h)",
        source=Source(git_url="https://github.com/xmrig/xmrig.git",
                      git_ref="v6.25.0"),
        extra_sources=dict(deps.EXTRA_SOURCES),
        build=(deps.msvc_openssl() + deps.msvc_libuv() + [
            # randomx.cmake adds jit_compiler_x86_static.asm under MSVC with
            # no check on pointer size, and ml.exe cannot assemble it for a
            # 32-bit target, so the 32-bit leg turns WITH_ASM off - after which
            # randomx.cmake and asm.cmake both fall through to the portable
            # sources they use for any 32-bit build.
            BuildStep('if "{arch}"=="x64" ' + _CMAKE),
            BuildStep('if "{arch}"=="x86" ' + _CMAKE + " -DWITH_ASM=OFF"),
            BuildStep("cmake --build build-{arch}"),
            BuildStep("dir build-{arch}", allow_failure=True),
        ]),
        artifacts=[Artifact(path="build-{arch}/xmrig.exe",
                            component="xmrig.exe",
                            pdb="build-{arch}/xmrig.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        exclude_functions=vendored.patterns("XMRig_6.25.0_msvc"),
        build_flags="/MD /O2 /Oi /DNDEBUG /Zi (build type Corpus, without "
                    "XMRig's /MT and /GL); /DEBUG /Brepro /INCREMENTAL:NO "
                    "/OPT:NOREF /OPT:NOICF at link",
        notes="llhttp, Argon2/Blake2b and ed25519 (load_3, load_4) helpers, rapidjson and C++ standard library "
              "functions that other families also carry, and __scrt_common_main_seh, are "
              "removed by exact name (exclude_functions, excluded_function_count; see "
              "_stack_vendored.py); the images were re-derived from the committed "
              "archives, not rebuilt. libuv and OpenSSL are linked as DLL import "
              "libraries and are not in the image.",
    ),
}


# XMRig 6.25.0 with its stock feature set (WITH_HWLOC, WITH_OPENCL and
# WITH_CUDA ON), as xmrig.py's 6.25.0-gpu-hwloc. On MSVC XMRig's cpu.cmake
# does not look for an installed hwloc: it compiles its vendored copy,
# src/3rdparty/hwloc (hwloc 2.12.1, the hwloc family's release), as a static
# library into the miner, and no option changes that. Its functions are
# therefore in the image; the ones carrying hwloc's public or internal prefix
# (hwloc_*, hwloc__*) are removed by name and counted as excluded, and its
# few static helpers without the prefix stay under XMRig.
_HWLOC_EXCLUDE = [r"^_{0,2}hwloc_"]

_CMAKE_STOCK = _CMAKE.replace("-DWITH_HWLOC=OFF -DWITH_OPENCL=OFF -DWITH_CUDA=OFF",
                              "-DWITH_HWLOC=ON -DWITH_OPENCL=ON -DWITH_CUDA=ON")

RECIPES["XMRig_6.25.0-gpu-hwloc_msvc"] = Recipe(
    family="XMRig",
    version="6.25.0-gpu-hwloc",
    upstream="https://github.com/xmrig/xmrig",
    license="GPL-3.0-or-later (SPDX identifier in src/version.h); the "
            "vendored src/3rdparty/hwloc is BSD-3-Clause",
    source=Source(git_url="https://github.com/xmrig/xmrig.git",
                  git_ref="v6.25.0"),
    extra_sources=dict(deps.EXTRA_SOURCES),
    build=(deps.msvc_openssl() + deps.msvc_libuv() + [
        BuildStep('if "{arch}"=="x64" ' + _CMAKE_STOCK),
        BuildStep('if "{arch}"=="x86" ' + _CMAKE_STOCK + " -DWITH_ASM=OFF"),
        BuildStep("cmake --build build-{arch}"),
        BuildStep("dir build-{arch}", allow_failure=True),
    ]),
    artifacts=[Artifact(path="build-{arch}/xmrig.exe",
                        component="xmrig.exe",
                        pdb="build-{arch}/xmrig.pdb")],
    toolchains=["msvc_x86", "msvc_x64"],
    exclude_functions=vendored.patterns("XMRig_6.25.0_msvc") + _HWLOC_EXCLUDE,
    build_flags="/MD /O2 /Oi /DNDEBUG /Zi (build type Corpus, without "
                "XMRig's /MT and /GL); /DEBUG /Brepro /INCREMENTAL:NO "
                "/OPT:NOREF /OPT:NOICF at link; WITH_HWLOC=ON WITH_OPENCL=ON "
                "WITH_CUDA=ON (stock)",
    notes="Stock feature set: WITH_HWLOC, WITH_OPENCL and WITH_CUDA ON "
          "(XMRig's defaults; NVML and ADL with them); the GPU backends need "
          "no SDK and load their runtimes at run time. XMRig compiles its "
          "vendored hwloc 2.12.1 statically on MSVC (no option selects an "
          "external one); hwloc_* and hwloc__* functions are removed by name "
          "and counted in excluded_function_count, its unprefixed static "
          "helpers stay. llhttp, Argon2/Blake2b and ed25519 helpers, "
          "rapidjson, C++ standard library functions and "
          "__scrt_common_main_seh are removed by exact name as for the 6.25.0 "
          "image (_stack_vendored.py). libuv and OpenSSL are linked as DLL "
          "import libraries and are not in the image.",
)
