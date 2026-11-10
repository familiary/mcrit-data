"""xmr-stak 2.10.8 - CPU backend, as a glibc ELF executable (x64).

Backlog issue #63. Tag 2.10.8 is commit 67cf951b, the final release of an
archived project. An independent implementation, not a fork of XMRig and not
a RandomX wrapper; the evidence for it is naming only (a Zscaler report of an
SFX archive that bundles xmr-stak beside XMRig), so what justifies it is that
it builds, is large enough and is a stock build of a pinned release.

Configuration, all CMake options: CUDA_ENABLE=OFF and OpenCL_ENABLE=OFF (the
CPU backend only), MICROHTTPD_ENABLE=OFF and HWLOC_ENABLE=OFF (optional,
as the issue recommends), OpenSSL on, linked as a shared library built from
the pinned 3.5.8 source. XMR-STAK_COMPILE=generic: the default, native,
prepends -march=native -mtune=native and would make the baseline whatever CPU
built the data. xmr-stak adds -msse2 -maes to every file itself, so the
baseline is x86-64 with SSE2 and AES intrinsics. CMake
Release, -O3 -DNDEBUG; nothing strips and the link is dynamic, so no
libstdc++ is in the image. Own code, not separable: the CryptoNight and
Keccak/Blake/Groestl/JH/Skein implementations are xmr-stak's, not an upstream
of their own. 1158 functions, 9 removed as runtime, 20 more (rapidjson and C++
standard library code the miners share, removed by exact name) excluded: 1138
kept.

One source defect needs a compiler switch: xmrstak/misc/console.hpp uses FILE
without including <cstdio> and does not compile with GCC 13 (`'FILE' does not
name a type`), so the build passes -include cstdio. The file is not touched.

Axes built: Linux x64 (here), MSVC x64 (xmr_stak_msvc.py) and MinGW x64 and
x86 (xmr_stak_mingw.py). At ten instructions or more Linux and MSVC x64 share
0 of 643 and 1288 PicHashes. 32-bit is unsupported by upstream's own
declaration: cryptonight_aesni.h:52 is `#error You are trying to do a 32-bit
build. This will all end in tears.` (reproduced here with -m32). The MSVC x86
build died in MASM on the 64-bit registers of cryptonight_v8_main_loop_ivybridge
_win64.inc (error A2006, undefined symbol r11, r8, rbp, r9, ...). The MinGW
pair is built from a recipe-patched tree (a renamed static _umul128 that
conflicts with mingw-w64's extern declaration, and for x86 the #error removed
and the 64-bit assembly replaced by stubs), so those two images are not
byte-identical to unmodified upstream; xmr_stak_mingw.py has the exact diffs.

Overlap: 84 of the Linux x64 artefact's PicHashes are in data/XMRig and 84 in
data/xmrig-proxy (rapidjson, std::), 398 and 331 on MSVC x64. `validate --deep`
used to fail on 125 PicHashes the three miners share (83 rapidjson, 41 standard
library templates, 1 __scrt_common_main_seh); every function of those names is
now removed by exact name (Recipe.exclude_functions, _stack_vendored.py:
rapidjson and standard library code, name tier; 163 functions over the five
xmr-stak images; Linux x64 1,138 / 9 / 20 kept / removed as runtime /
excluded). The rest of the shared instantiations stay.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _stack_deps as deps
from . import _stack_vendored as vendored


_TAG = "2.10.8"

# XMR-STAK_COMPILE=generic is the one that does not prepend
# "-march=native -mtune=native"; the default, native, would make the baseline
# instruction set whatever machine built the reference data.
_CONFIG = ("-DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DXMR-STAK_COMPILE=generic "
           "-DCUDA_ENABLE=OFF -DOpenCL_ENABLE=OFF -DMICROHTTPD_ENABLE=OFF "
           "-DHWLOC_ENABLE=OFF")

# xmrstak/misc/console.hpp uses FILE without including <cstdio> and does not
# compile with GCC 13. A forced include supplies it without touching the file.
_FIX_CSTDIO = "-DCMAKE_CXX_FLAGS='-include cstdio'"

_NOTES = (
    "CPU backend only (CUDA and OpenCL off), without libmicrohttpd and hwloc, "
    "with TLS: OpenSSL 3.5.8 built from a pinned source and linked as a "
    "shared library. XMR-STAK_COMPILE=generic, so no -march=native; xmr-stak "
    "adds -msse2 -maes itself. CMake Release (-O3 -DNDEBUG). rapidjson and C++ "
    "standard library instantiations that other families also carry are "
    "removed by exact name (exclude_functions, see _stack_vendored.py)."
)


def _stak():
    steps = deps.linux_openssl() + [
        BuildStep("cmake -S . -B build-{arch} " + _CONFIG + " "
                  + deps.linux_dep_options(uv=False) + " " + _FIX_CSTDIO,
                  env={"CFLAGS": "", "CXXFLAGS": ""}),
        BuildStep("cmake --build build-{arch} -j$(nproc)"),
    ]
    return Recipe(
        family="xmr-stak",
        version="2.10.8",
        upstream="https://github.com/fireice-uk/xmr-stak",
        license="GPL-3.0",
        source=Source(git_url="https://github.com/fireice-uk/xmr-stak.git",
                      git_ref=_TAG),
        extra_sources=dict(deps.OPENSSL_ONLY),
        build=steps,
        artifacts=[Artifact(path="build-{arch}/bin/xmr-stak",
                            component="xmr-stak")],
        toolchains=["linux_x64"],
        exclude_functions=vendored.patterns("xmr-stak_2.10.8_linux"),
        build_flags="-O3 -DNDEBUG (CMake Release), -msse2 -maes",
        notes=_NOTES,
    )


RECIPES = {
    "xmr-stak_2.10.8_linux": _stak(),
}


# Linux x86, the 32-bit configuration upstream declares unsupported, built
# the way the MinGW x86 and MSVC x86 images are (xmr_stak_mingw.py,
# xmr_stak_msvc_x86.py) from a build tree the recipe patches. NOT
# byte-identical to a build of unmodified upstream. The patches, all applied
# here at build time and none committed:
#   * the `#error You are trying to do a 32-bit build` line of
#     cryptonight_aesni.h is deleted;
#   * its _umul128, whose body is `unsigned __int128 r = (unsigned __int128)a
#     * (unsigned __int128)b;` (GCC has no __int128 on i686), is rewritten to
#     the same 64x64->128 product from four 32x32->64 partial products
#     (xmr_stak_mingw.py's _UMUL32, unchanged);
#   * exercisers/xmr_stak_x86_compat.h is force-included for
#     _mm_cvtsi64_si128, _mm_cvtsi128_si64, _addcarry_u64 and _subborrow_u64,
#     which GCC's headers omit on a 32-bit target;
#   * the x86-64-only GAS sources cryptonight_v8_main_loop.S and
#     CryptonightR_template.S are overwritten with `ret` stubs for the symbols
#     they define (ELF names carry no leading underscore, unlike the PE x86
#     stubs of the MinGW recipe), so those generated stubs are in the image.
# Everything else is the x64 recipe: OpenSSL 3.5.8 shared, CPU backend only,
# XMR-STAK_COMPILE=generic, -include cstdio.
# Built in run 42794750598 (scratch/s4-xmrig-linux); its own exclusion table
# (_stack_vendored.py, _STDLIB_6) then removed two more functions from the
# archive without a rebuild: 1,899 kept + 6 removed + 12 excluded = 1,917.
from .xmr_stak_mingw import _ASM, _SRC, _UMUL32  # noqa: E402

_PATCH_LINUX_X86 = BuildStep(
    "sed -i -e '/#error You are trying to do a 32-bit build/d' " + _SRC
    + " && " + _UMUL32 + " && "
    "{ printf '.text\\n'; for f in cryptonight_v8_mainloop_ivybridge_asm "
    "cryptonight_v8_mainloop_ryzen_asm cryptonight_v8_double_mainloop_sandybridge_asm; do "
    "printf '.globl %s\\n%s:\\n\\tret\\n' $f $f; done; } > " + _ASM + "/cryptonight_v8_main_loop.S && "
    "{ printf '.text\\n'; for f in $(grep -o 'void [A-Za-z0-9_]*()' " + _ASM
    + "/cnR/CryptonightR_template.h | sed 's/void //;s/()//'); do "
    "printf '.globl %s\\n%s:\\n\\tret\\n' $f $f; done; } > " + _ASM + "/cnR/CryptonightR_template.S")


def _stak_x86():
    import dataclasses
    recipe = _stak()
    return dataclasses.replace(
        recipe,
        build=deps.linux_openssl() + [
            _PATCH_LINUX_X86,
            BuildStep("cmake -S . -B build-{arch} " + _CONFIG + " "
                      + deps.linux_dep_options(uv=False)
                      + " -DCMAKE_CXX_FLAGS='-include cstdio -include "
                      "{repo}/scripts/corpus/exercisers/xmr_stak_x86_compat.h'"
                      # CMake's ASM language does not take -m32 from CC, so
                      # the stub .S files were assembled as x86-64 ("i386:x86-64
                      # architecture of input file ... is incompatible with
                      # i386 output").
                      " -DCMAKE_ASM_FLAGS=-m32",
                      env={"CFLAGS": "", "CXXFLAGS": ""}),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        toolchains=["linux_x86"],
        exclude_functions=vendored.patterns("xmr-stak_2.10.8_linux_x86"),
        build_flags="-O3 -DNDEBUG (CMake Release), -msse2 -maes; build tree "
                    "patched by the recipe (32-bit #error removed, 32-bit "
                    "umul128, x86 compat header force-included, asm ret stubs)",
        notes="NOT byte-identical to a build of unmodified upstream: "
              "recipe-applied patch, see the xmr_stak.py docstring. An "
              "unsupported configuration (upstream #errors on 32-bit builds): "
              "its CryptoNight v8 and CryptonightR assembly is replaced by "
              "one-instruction ret stubs. " + _NOTES,
    )


RECIPES["xmr-stak_2.10.8_linux_x86"] = _stak_x86()
