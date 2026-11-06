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
of their own. 1158 functions, 9 removed as runtime.

One source defect needs a compiler switch: xmrstak/misc/console.hpp uses FILE
without including <cstdio> and does not compile with GCC 13 (`'FILE' does not
name a type`), so the build passes -include cstdio. The file is not touched.

Axes built: Linux x64 (here) and MSVC x64 (xmr_stak_msvc.py); at ten
instructions or more they share 0 of 659 and 1346 PicHashes. 32-bit is
impossible on every toolchain, by upstream's own declaration:
cryptonight_aesni.h:52 is `#error You are trying to do a 32-bit build. This
will all end in tears.` (reproduced here with -m32), and the MSVC x86 build
died in MASM on the 64-bit registers of cryptonight_v8_main_loop_ivybridge
_win64.inc (error A2006, undefined symbol r11, r8, rbp, r9, ...). MinGW x64
does not build either without changing upstream: cryptonight_aesni.h:40
defines a static inline _umul128 that conflicts with mingw-w64's own
declaration ("declared 'extern' and later 'static'"; defining
__INTRINSIC_DEFINED__umul128 does not help, the prototype comes from
elsewhere), and jext.hpp:60 includes <byteswap.h>, a glibc header. Both are in
the "Targets investigated but not built" table.

Overlap: 99 of the Linux x64 artefact's PicHashes are in data/XMRig and 99 in
data/xmrig-proxy (rapidjson, std::), 452 and 385 on MSVC x64.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _stack_deps as deps


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
    "adds -msse2 -maes itself. CMake Release (-O3 -DNDEBUG)."
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
        build_flags="-O3 -DNDEBUG (CMake Release), -msse2 -maes",
        notes=_NOTES,
    )


RECIPES = {
    "xmr-stak_2.10.8_linux": _stak(),
}
