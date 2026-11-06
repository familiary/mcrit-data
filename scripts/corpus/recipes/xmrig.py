"""XMRig 6.25.0 - the miner, built for MinGW (PE) and for Linux (ELF).

Backlog issue #8. The tag v6.25.0 resolves to commit 753859ca, the release
that also pins issue #18's RandomX tree and the last miner release before the
xmrig-proxy 6.26.0 of issue #84.

What is in the artefact, and what deliberately is not.

The build is the stock one - every algorithm family XMRig enables by default
(RandomX, CryptoNight and its Lite/Heavy/Pico/UPX2 variants, Argon2, KawPow,
GhostRider), the HTTP API and daemon client, TLS, the benchmark, MSR and DMI -
with the GPU backends and hwloc off:

  -DWITH_OPENCL=OFF -DWITH_CUDA=OFF   no vendor SDK is needed, and a GPU
        backend would be code a CPU sample does not carry.
  -DWITH_HWLOC=OFF                    hwloc is covered nowhere in the corpus
        and is not vendored in a form the build uses (src/3rdparty/hwloc is
        the project xmrig-deps builds, not something add_subdirectory
        reaches); the issue asks for exactly this first cut. What it costs is
        src/crypto/common/NUMAMemoryPool.cpp, VirtualMemory_hwloc.cpp,
        Platform_hwloc.cpp and RxNUMAStorage.cpp - four files, NUMA handling.

libuv and OpenSSL are linked as shared libraries (see _stack_deps.py), so the
image holds the miner and its vendored trees and not those two families.

The vendored trees. XMRig has no .gitmodules; src/3rdparty is compiled in.
What it holds, how it is filed, and why:

  * RandomX (src/crypto/randomx, 17 sources). Stays in this artefact, because
    it is part of what a stock XMRig is and an XMRig sample carries it, and is
    also its own family: data/RandomX holds upstream tevador/RandomX, which
    XMRig forked and modified (XMRig's tree has no argon2 or assembly
    generator of its own, adds a RISC-V and a hugepage-aware allocator and
    changes the JIT). The overlap is measured, not assumed; see
    README.md's row for this family.
  * llhttp (src/3rdparty/llhttp) and Argon2 (src/3rdparty/argon2, with its
    five SIMD variants) and libethash, epee, fmt, base32, rapidjson, getopt:
    filed under XMRig. They are compiled into the miner with no module
    identity of their own, which is also how data/abseil files its cctz and
    data/7-Zip its zstd decoder, and none of the trees is separable by the
    build: they are static libraries inside one executable.

Flags. XMRig's CMake sets `-Ofast -s` for Release on GNU, `-static` (MinGW)
or `-static-libgcc -static-libstdc++` (ELF) at link, and `-maes` for every
translation unit; three things there would damage this data and one is
kept:

  * `-s` strips the symbol table, which SMDA reads. Release is therefore not
    used. The build type is `Corpus`, a name CMake has no defaults for and
    flags.cmake has no branch on, with the same optimisation XMRig's Release
    arrives at (CMake's Release `-O3 -DNDEBUG`, then XMRig's `-Ofast`) written
    out in CMAKE_C_FLAGS_CORPUS and CMAKE_CXX_FLAGS_CORPUS. XMRig's own
    per-file flags (`-Ofast -fno-tree-vectorize` on CnHash.cpp, `-mavx2 -mvaes`
    on the VAES translation unit, `-msse4.1` and `-mavx2` on the two Blake2b
    ones) are applied by its CMakeLists regardless of build type.
  * `-static` / `-static-libstdc++` would put about 13,500 libstdc++ and libgcc
    functions in the artefact under the miner's name (README: "a third trap").
    flags.cmake appends them to CMAKE_EXE_LINKER_FLAGS after any value passed
    on the command line, so they cannot be overridden from there; the recipe
    instead sets CMAKE_CXX_LINK_EXECUTABLE, which CMake only defaults when
    unset, to the stock link rule without `<LINK_FLAGS>` - the placeholder
    CMAKE_EXE_LINKER_FLAGS expands into. Nothing XMRig puts anywhere else in
    that variable is lost: it holds `-static`, `-static-libgcc`,
    `-static-libstdc++` and, on 32-bit PE, `--large-address-aware`, which is a
    PE header bit and changes no code. MinGW adds `-shared-libgcc`.
  * `-maes` is kept: it is what XMRig builds with, and it only licenses AES
    intrinsics. Nothing sets -march, so the baseline instruction set is
    plain x86-64 (SSE2) or, on x86, i686 with SSE2 as the mingw-w64 and
    Debian toolchains here default to; AES-NI, SSE4.1, AVX2, VAES and AVX-512
    are separate translation units that XMRig selects at run time by CPUID.
    On 32-bit builds cpu.cmake switches WITH_SSE4_1, WITH_AVX2 and WITH_VAES
    off, and WITH_ASM is 64-bit only, so the x86 artefacts have neither those
    units nor the JIT (jit_compiler_fallback.cpp) and the CryptoNight main
    loops that the x64 ones carry as assembly.

Axes. MinGW x86 and x64 and Linux x86 and x64 are built. The musl-static ELF
the issue lists is not: see README's "Targets investigated but not built".
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _stack_deps as deps


_TAG = "v6.25.0"

_OPT = "-O3 -DNDEBUG -Ofast"

# The stock link rule minus <LINK_FLAGS>; see the module docstring.
_LINK_RULE = ("-DCMAKE_CXX_LINK_EXECUTABLE='<CMAKE_CXX_COMPILER> <FLAGS> "
              "<CMAKE_CXX_LINK_FLAGS> <OBJECTS> -o <TARGET> <LINK_LIBRARIES>%s'")

_CONFIG = ("-DCMAKE_BUILD_TYPE=Corpus -DCMAKE_C_FLAGS_CORPUS='%s' "
           "-DCMAKE_CXX_FLAGS_CORPUS='%s' -DWITH_HWLOC=OFF -DWITH_OPENCL=OFF "
           "-DWITH_CUDA=OFF" % (_OPT, _OPT))

_NOTES = (
    "Stock configuration with the GPU backends and hwloc off, libuv 1.52.1 "
    "and OpenSSL 3.5.8 built from pinned sources and linked as shared "
    "libraries so neither is in the image. Build type Corpus carries CMake's "
    "Release optimisation and XMRig's -Ofast without XMRig's -s, and the link "
    "rule leaves out the -static / -static-libstdc++ flags XMRig's flags.cmake "
    "adds, which would file libstdc++ under this name. -maes is XMRig's own; "
    "no -march is set, and AES-NI, SSE4.1, AVX2, VAES and AVX-512 code is in "
    "separate units that XMRig picks at run time. The vendored RandomX, "
    "Argon2, llhttp, libethash, epee, fmt and base32 are compiled in and stay "
    "filed here."
)


def _mingw():
    return Recipe(
        family="XMRig",
        version="6.25.0",
        upstream="https://github.com/xmrig/xmrig",
        license="GPL-3.0-or-later (SPDX identifier in src/version.h); "
                "vendored trees carry their own: RandomX BSD-3-Clause, "
                "llhttp MIT, Argon2 CC0/Apache-2.0, libethash GPL-3.0, "
                "fmt MIT, rapidjson MIT",
        source=Source(git_url="https://github.com/xmrig/xmrig.git",
                      git_ref=_TAG),
        extra_sources=dict(deps.EXTRA_SOURCES),
        build=(deps.mingw_openssl() + deps.mingw_libuv() + [
            deps.mingw_header_shim(),
            BuildStep(
                "cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
                "-DCMAKE_SYSTEM_PROCESSOR={platform} "
                "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx} "
                "-DCMAKE_RC_COMPILER={windres} "
                "-DCMAKE_FIND_ROOT_PATH=/usr/{host} "
                + _CONFIG + " " + deps.mingw_dep_options() + " " + deps.MINGW_SHIM_FLAGS + " "
                + _LINK_RULE % " -shared-libgcc",
                env={"CFLAGS": "", "CXXFLAGS": ""}),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ]),
        artifacts=[Artifact(path="build-{arch}/xmrig.exe",
                            component="xmrig.exe")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 -DNDEBUG -Ofast (build type Corpus), -maes, "
                    "per-file -msse4.1/-mavx2/-mvaes as XMRig's CMake sets; "
                    "no -s, no -static",
        notes=_NOTES,
    )


def _linux():
    return Recipe(
        family="XMRig",
        version="6.25.0",
        upstream="https://github.com/xmrig/xmrig",
        license="GPL-3.0-or-later (SPDX identifier in src/version.h); "
                "vendored trees carry their own: RandomX BSD-3-Clause, "
                "llhttp MIT, Argon2 CC0/Apache-2.0, libethash GPL-3.0, "
                "fmt MIT, rapidjson MIT",
        source=Source(git_url="https://github.com/xmrig/xmrig.git",
                      git_ref=_TAG),
        extra_sources=dict(deps.EXTRA_SOURCES),
        build=(deps.linux_openssl() + deps.linux_libuv() + [
            BuildStep(
                "cmake -S . -B build-{arch} " + _CONFIG + " "
                + deps.linux_dep_options() + " " + _LINK_RULE % "",
                env={"CFLAGS": "", "CXXFLAGS": ""}),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ]),
        artifacts=[Artifact(path="build-{arch}/xmrig", component="xmrig")],
        toolchains=["linux_x86", "linux_x64"],
        build_flags="-O3 -DNDEBUG -Ofast (build type Corpus), -maes, "
                    "per-file -msse4.1/-mavx2/-mvaes as XMRig's CMake sets; "
                    "no -s, no -static-libstdc++",
        notes=_NOTES,
    )


RECIPES = {
    "XMRig_6.25.0": _mingw(),
    "XMRig_6.25.0_linux": _linux(),
}
