"""XMRig 6.25.0 - the miner, as PE (MinGW) and ELF (glibc) executables.

Backlog issue #8. The tag v6.25.0 is commit 753859ca. MSVC is in xmrig_msvc.py.

What is built. The stock configuration, as a release ships it: RandomX,
CryptoNight and its Lite/Heavy/Pico/UPX2 variants, Argon2, KawPow,
GhostRider, the HTTP API and daemon client, TLS, MSR, DMI and the benchmark;
with the two things a CPU reference does not want switched off:

  -DWITH_OPENCL=OFF -DWITH_CUDA=OFF   the GPU backends need vendor SDKs and
        are code a CPU sample does not carry.
  -DWITH_HWLOC=OFF                    hwloc is covered nowhere in the corpus,
        and src/3rdparty/hwloc is the tree xmrig-deps builds hwloc from, not
        something this CMakeLists adds. The issue asks for exactly this first
        cut. It costs four small files: NUMAMemoryPool.cpp,
        VirtualMemory_hwloc.cpp, Platform_hwloc.cpp and RxNUMAStorage.cpp.

libuv and OpenSSL are linked as shared libraries (see _stack_deps.py), so the
executable holds the miner and the trees it vendors and not those two
families, which data/libuv and data/OpenSSL already carry. Linked the way
XMRig's own FindUV.cmake prefers (its find_library list starts with
`libuv.a`) about 540 uv_* functions and all of libcrypto would be filed
here.

The vendored trees. XMRig has no .gitmodules; src/3rdparty is compiled in.
Decided with the comparison below, and recorded here because the same code is
in other families:

  * RandomX (src/crypto/randomx, 17 sources) stays in this artefact: it is
    part of what XMRig is and what a sample carries. data/RandomX holds
    upstream tevador/RandomX, and the overlap between the two is small - 22
    of this artefact's 2504 functions of ten instructions or more share a
    PicHash with it on Linux x64, five of them the same RandomX function
    under the same name (randomx.py lists them). XMRig's own plumbing around
    it (src/crypto/rx, MSR and the Ryzen fix) is only here.
  * llhttp 9.3.0 (src/3rdparty/llhttp, the same version as data/llhttp), and
    Argon2 (src/3rdparty/argon2 with its SSE2/SSSE3/XOP/AVX2/AVX-512F
    variants; forced on by randomx.cmake whenever RandomX is): filed here,
    because XMRig's CMake offers no switch that removes either without also
    removing the HTTP stack or RandomX. They DO collide with those families:
    with the (not yet merged) llhttp and argon2 branches' data present,
    `validate --deep` finds 121 PicHashes shared by this family,
    xmrig-proxy and llhttp under identical names (MinGW and MSVC, both
    architectures; the ELF axis has no llhttp artefact to meet) and 10
    Argon2/Blake2b helper hashes shared with data/argon2, data/libsodium and
    data/RandomX. That is the same code legitimately in several places, not
    glue, and is recorded for whoever merges those branches.
  * libethash, epee, fmt, base32, rapidjson and getopt: filed here; no
    other family covers them. rapidjson is also compiled into xmrig-proxy and
    xmr-stak, which is the largest group of findings `validate --deep` gives
    this stack (36 PicHashes, one symbol, three families).

Flags. XMRig's flags.cmake sets `-Ofast -s` for Release on GNU, `-static`
(MinGW) or `-static-libgcc -static-libstdc++` (ELF) at link, and -maes for
every file; the first two would damage this data:

  * `-s` strips the symbol table, which SMDA reads. The build type is
    therefore `Corpus`, a name CMake has no defaults for and flags.cmake no
    branch on, with what Release arrives at - CMake's `-O3 -DNDEBUG`, then
    XMRig's `-Ofast` - written out in CMAKE_C_FLAGS_CORPUS and
    CMAKE_CXX_FLAGS_CORPUS. XMRig's per-file flags (`-Ofast
    -fno-tree-vectorize` on CnHash.cpp, `-mavx2 -mvaes` on the VAES unit,
    `-msse4.1` and `-mavx2` on the two Blake2b ones) apply regardless.
  * `-static` and `-static-libstdc++` would put about 13,500 libstdc++ and
    libgcc functions in the artefact under the miner's name (README: "a
    third trap"). On ELF, CMAKE_CXX_LINK_EXECUTABLE is set to the stock rule
    without `<LINK_FLAGS>`, which is where CMAKE_EXE_LINKER_FLAGS lands.
    CMake's Windows-GNU platform file defines the rule unconditionally, so
    on MinGW that does not work, and the compiler is wrapped instead
    (exercisers/link_dynamic_cxx.sh) to drop the three static switches from
    every command line and append -shared-libgcc and the libuv import
    library, which has to follow libargon2.a for GNU ld to resolve
    uv_hrtime. The upstream tree is not touched either way. Checked on the
    output: the ELF needs libssl.so.3, libcrypto.so.3, libuv.so.1,
    libstdc++.so.6 and libgcc_s.so.1; the PE imports libssl, libcrypto,
    libuv, libstdc++-6 and libgcc_s.
  * -maes is kept; it licenses AES intrinsics and nothing else. No -march is
    set, so the baseline instruction set is x86-64 with SSE2 (i686 with SSE2
    on x86). AES-NI, SSE4.1, AVX2, VAES and AVX-512 live in separate
    translation units that XMRig selects at run time from CPUID. On 32-bit
    cpu.cmake switches WITH_SSE4_1, WITH_AVX2 and WITH_VAES off and WITH_ASM
    is 64-bit only, so the x86 artefacts have neither those units, the RandomX
    JIT (jit_compiler_fallback.cpp instead) nor the CryptoNight main loops
    the x64 ones carry as assembly.

MinGW needs one more thing that is not a flag: XMRig includes <Windows.h>,
<Shobjidl.h>, <Objbase.h> and <BaseTsd.h> with capitals, which a
case-sensitive cross-build cannot find. Symlinks to mingw-w64's lower-case
headers in a directory of their own, passed with -isystem, supply them; the
header that is read is the same file.

Axes. MinGW x86 and x64, Linux ELF x86 and x64 and MSVC x86 and x64: six, and
measured to differ. At ten instructions or more, x64 shares 0 PicHashes
between any two of GCC (2248), MinGW (2128) and MSVC (4224); x86 shares 76
between GCC and MinGW and none with MSVC. Counts (kept functions, and
those removed as compiler runtime): Linux x64 3783 and 9, x86 3887 and 6;
MinGW x64 3707 and 174, x86 4072 and 186; MSVC x64 14,384 and 2,300, x86
14,600 and 2,172. The MSVC figure is four times the GCC one because MSVC
instantiates the standard library's templates into the image (5,837 `std::`
functions on x64) and keeps every unreferenced COMDAT under /OPT:NOREF; it is
what an MSVC-built miner contains.

Not built: the static-musl ELF the issue lists. See scripts/corpus/README.md,
"Targets investigated but not built".
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _stack_deps as deps


_TAG = "v6.25.0"

_OPT = "-O3 -DNDEBUG -Ofast"

# The stock link rule minus <LINK_FLAGS>; see the module docstring.
#
# libuv's library is repeated at the end: the vendored Argon2 archive
# (libargon2.a) calls uv_hrtime and CMake lists it after libuv, and GNU ld
# resolves an archive's references only from libraries that come later.
_LINK_RULE = ("-DCMAKE_CXX_LINK_EXECUTABLE='<CMAKE_CXX_COMPILER> <FLAGS> "
              "<CMAKE_CXX_LINK_FLAGS> <OBJECTS> -o <TARGET> <LINK_LIBRARIES> "
              "'\"$PWD\"'/deps-{arch}/uv/%s'")

_CONFIG = ("-DCMAKE_BUILD_TYPE=Corpus -DCMAKE_C_FLAGS_CORPUS='%s' "
           "-DCMAKE_CXX_FLAGS_CORPUS='%s' -DWITH_HWLOC=OFF -DWITH_OPENCL=OFF "
           "-DWITH_CUDA=OFF" % (_OPT, _OPT))

_LICENSE = ('GPL-3.0-or-later (SPDX identifier in src/version.h). Vendored trees in src/3rdparty carry their own: RandomX BSD-3-Clause (source headers), llhttp MIT (LICENSE-MIT), Argon2 MIT (LICENSE, Ondrej Mosnacek); fmt, rapidjson and epee ship licence files; libethash, base32 and getopt ship none')

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
        license=_LICENSE,
        source=Source(git_url="https://github.com/xmrig/xmrig.git",
                      git_ref=_TAG),
        extra_sources=dict(deps.EXTRA_SOURCES),
        build=(deps.mingw_openssl() + deps.mingw_libuv() + [
            deps.mingw_header_shim(),
            BuildStep(
                "cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
                "-DCMAKE_SYSTEM_PROCESSOR={platform} "
                "-DCMAKE_C_COMPILER={cc} " + deps.MINGW_WRAPPER + " "
                "-DCMAKE_RC_COMPILER={windres} "
                "-DCMAKE_FIND_ROOT_PATH=/usr/{host} "
                + _CONFIG + " " + deps.mingw_dep_options() + " " + deps.MINGW_SHIM_FLAGS,
                env=dict(deps.MINGW_WRAPPER_ENV, CFLAGS="", CXXFLAGS="")),
            BuildStep("cmake --build build-{arch} -j$(nproc)",
                      env=dict(deps.MINGW_WRAPPER_ENV)),
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
        license=_LICENSE,
        source=Source(git_url="https://github.com/xmrig/xmrig.git",
                      git_ref=_TAG),
        extra_sources=dict(deps.EXTRA_SOURCES),
        build=(deps.linux_openssl() + deps.linux_libuv() + [
            BuildStep(
                "cmake -S . -B build-{arch} " + _CONFIG + " "
                + deps.linux_dep_options() + " " + _LINK_RULE % "libuv.so",
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
