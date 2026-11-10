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
# does not look for an installed hwloc: it calls
# add_subdirectory(src/3rdparty/hwloc), which compiles its vendored copy (hwloc
# 2.12.1, the hwloc family's release) as a static library named `hwloc` into
# the miner, and no option changes that. So that hwloc is not counted under
# XMRig, the recipe builds the hwloc family's DLL first (the release tarball,
# contrib/windows-cmake, the same options as hwloc.py's MSVC recipe, under
# deps-<arch>\hwloc) and hands CMake exercisers/xmrig_hwloc_shared.cmake
# through CMAKE_PROJECT_xmrig_INCLUDE: it replaces that one add_subdirectory
# call with an imported target of the same name whose import library is
# hwloc.lib, so cpu.cmake's `set(CPUID_LIB hwloc)` links the DLL. No XMRig
# file is modified (the vendored headers, the same 2.12.1, are still the ones
# on the include path); the image imports hwloc.dll as the Linux and MinGW
# images import libhwloc. What MSVC still emits from hwloc's headers, the
# `static __hwloc_inline` helpers of hwloc.h and hwloc/helper.h that GCC
# inlines, is 18 functions under 7 names per image, each PicHash-equal to the
# same-named function of data/hwloc's MSVC hwloc.dll; they are excluded by
# exact name (_stack_vendored.py, category hwloc). Built in run 42822515768:
# kept + removed + excluded = total, x64 18,313 + 2,329 + 141 = 20,783, x86
# 18,895 + 2,210 + 136 = 21,241; no function of 10+ instructions is
# PicHash-shared with hwloc.dll. Against XMRig_6.25.0_msvc (distinct PicHashes,
# 10+ instructions): 3,732 of 4,964 (x64), 4,050 of 4,955 (x86).
from .hwloc import MSVC_CMAKE_OPTIONS as _HWLOC_CMAKE  # noqa: E402
from .hwloc import SOURCE as _HWLOC_SOURCE  # noqa: E402

_HWLOC_UNTAR = (
    'python -c "'
    "import sys,tarfile;t=tarfile.open(sys.argv[1]);"
    "m=[x for x in t.getmembers() if '/' in x.name];"
    "[setattr(x,'name',x.name.split('/',1)[1]) for x in m];"
    "t.extractall(sys.argv[2],members=m)"
    '" "{hwloc}" deps-{arch}\\hwloc')

_CMAKE_STOCK = (_CMAKE.replace("-DWITH_HWLOC=OFF -DWITH_OPENCL=OFF -DWITH_CUDA=OFF",
                               "-DWITH_HWLOC=ON -DWITH_OPENCL=ON -DWITH_CUDA=ON")
                + " -DCMAKE_PROJECT_xmrig_INCLUDE="
                "{repo}/scripts/corpus/exercisers/xmrig_hwloc_shared.cmake "
                "-DXM_HWLOC_IMPLIB=%CD%/deps-{arch}/hwloc-build/hwloc.lib "
                "-DXM_HWLOC_DLL=%CD%/deps-{arch}/hwloc-build/hwloc.dll")

RECIPES["XMRig_6.25.0-gpu-hwloc_msvc"] = Recipe(
    family="XMRig",
    version="6.25.0-gpu-hwloc",
    upstream="https://github.com/xmrig/xmrig",
    license="GPL-3.0-or-later (SPDX identifier in src/version.h)",
    source=Source(git_url="https://github.com/xmrig/xmrig.git",
                  git_ref="v6.25.0"),
    extra_sources=dict(deps.EXTRA_SOURCES, hwloc=_HWLOC_SOURCE),
    build=(deps.msvc_openssl() + deps.msvc_libuv() + [
        BuildStep(_HWLOC_UNTAR),
        BuildStep("cmake -S deps-{arch}\\hwloc\\contrib\\windows-cmake "
                  "-B deps-{arch}\\hwloc-build " + _HWLOC_CMAKE),
        BuildStep("cmake --build deps-{arch}\\hwloc-build --target hwloc"),
        BuildStep('if "{arch}"=="x64" ' + _CMAKE_STOCK),
        BuildStep('if "{arch}"=="x86" ' + _CMAKE_STOCK + " -DWITH_ASM=OFF"),
        BuildStep("cmake --build build-{arch}"),
        BuildStep("dir build-{arch} deps-{arch}\\hwloc-build", allow_failure=True),
    ]),
    artifacts=[Artifact(path="build-{arch}/xmrig.exe",
                        component="xmrig.exe",
                        pdb="build-{arch}/xmrig.pdb")],
    toolchains=["msvc_x86", "msvc_x64"],
    exclude_functions=vendored.patterns("XMRig_6.25.0-gpu-hwloc_msvc"),
    build_flags="/MD /O2 /Oi /DNDEBUG /Zi (build type Corpus, without "
                "XMRig's /MT and /GL); /DEBUG /Brepro /INCREMENTAL:NO "
                "/OPT:NOREF /OPT:NOICF at link; WITH_HWLOC=ON WITH_OPENCL=ON "
                "WITH_CUDA=ON (stock); hwloc 2.12.1 DLL imported in place of "
                "the vendored static hwloc (CMAKE_PROJECT_xmrig_INCLUDE)",
    notes="Stock feature set: WITH_HWLOC, WITH_OPENCL and WITH_CUDA ON "
          "(XMRig's defaults; NVML and ADL with them); the GPU backends need "
          "no SDK and load their runtimes at run time. XMRig's MSVC build "
          "would compile its vendored hwloc 2.12.1 statically; the recipe "
          "builds the hwloc family's 2.12.1 DLL from the release tarball "
          "(sha256 38a90328bb86259f9bb2fe1dc57fd841e111d1e6358012bef23dfd95d21dc66b) "
          "and replaces add_subdirectory(src/3rdparty/hwloc) with an imported "
          "target (exercisers/xmrig_hwloc_shared.cmake, through "
          "CMAKE_PROJECT_xmrig_INCLUDE), so hwloc is imported and not in the "
          "image; no source file is modified. hwloc's header inline helpers "
          "that MSVC emits (7 names) are excluded by exact name. llhttp, Argon2/Blake2b and "
          "ed25519 helpers, rapidjson, C++ standard library functions and "
          "__scrt_common_main_seh are removed by exact name as for the 6.25.0 "
          "image (_stack_vendored.py). libuv and OpenSSL are linked as DLL "
          "import libraries and are not in the image.",
)
