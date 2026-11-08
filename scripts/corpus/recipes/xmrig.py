"""XMRig 6.25.0 - the miner, as PE (MinGW), ELF (glibc) and static ELF (musl) executables.

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

libuv and OpenSSL are linked as shared libraries (see _stack_deps.py) on the
MinGW, glibc and MSVC axes, so the executable holds the miner and the trees it
vendors and not those two families, which data/libuv and data/OpenSSL already
carry. The static musl image cannot do that; see "The musl axis" below. Linked the way
XMRig's own FindUV.cmake prefers (its find_library list starts with
`libuv.a`) about 540 uv_* functions and all of libcrypto would be filed
here.

The vendored trees. XMRig has no .gitmodules; src/3rdparty is compiled in.
Decided with the comparison below, and recorded here because the same code is
in other families:

  * RandomX (src/crypto/randomx, 17 sources) stays in this artefact: it is
    part of what XMRig is and what a sample carries. data/RandomX holds
    upstream tevador/RandomX, and the overlap between the two is small - 22
    of this artefact's 2466 functions of ten instructions or more share a
    PicHash with it on Linux x64, five of them the same RandomX function
    under the same name (randomx.py lists them). XMRig's own plumbing around
    it (src/crypto/rx, MSR and the Ryzen fix) is only here.
  * llhttp 9.3.0 (src/3rdparty/llhttp, the same version as data/llhttp), and
    Argon2 (src/3rdparty/argon2 with its SSE2/SSSE3/XOP/AVX2/AVX-512F
    variants; forced on by randomx.cmake whenever RandomX is): filed here,
    because XMRig's CMake offers no switch that removes either without also
    removing the HTTP stack or RandomX. They DO collide with those families:
    with the (not yet merged) llhttp and argon2 branches' data present,
    `validate --deep` found 121 PicHashes shared by this family, xmrig-proxy
    and llhttp under identical names (MinGW and MSVC, both architectures; the
    ELF axis has no llhttp artefact to meet) and 10 Argon2/Blake2b helper
    hashes shared with data/argon2, data/BLAKE2, data/libsodium and
    data/RandomX. The functions that are llhttp's or Argon2's own are now
    removed by exact name, see "Vendored code removed by name" below.
  * libethash, epee, fmt, base32, rapidjson and getopt: filed here; no
    other family covers them. rapidjson is also compiled into xmrig-proxy and
    xmr-stak, which was the largest group of findings `validate --deep` gave
    this stack (83 PicHashes, one symbol, three families): the rapidjson
    functions that all three carry are removed by exact name too, as are the
    C++ standard library templates they share, see below.

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

Axes. MinGW x86 and x64, Linux ELF x86 and x64, MSVC x86 and x64 and static
musl x86 and x64: eight, and measured to differ. At ten instructions or more, x64 shares 0 PicHashes
between any two of GCC (2215), MinGW (2095) and MSVC (4140); x86 shares 57
between GCC and MinGW and none with MSVC. Counts (kept functions, and
those removed as compiler runtime): Linux x64 3735 and 9, x86 3847 and 6;
MinGW x64 3647 and 174, x86 4032 and 186; MSVC x64 14,256 and 2,307, x86
14,477 and 2,179; a further 48 and 40 (Linux), 60 and 40 (MinGW) and 121 and
116 (MSVC) are removed by exact name, see "Vendored code removed by name"
below. The MSVC figure is four times the GCC one because MSVC
instantiates the standard library's templates into the image (5,996 `std::`
functions on x64) and keeps every unreferenced COMDAT under /OPT:NOREF; it is
what an MSVC-built miner contains.

The musl axis (XMRig_6.25.0_musl, x86 and x64) is the static ELF the issue
lists. It is built with musl.cc's GCC 11.2.1 20211120 on musl
1.2.2-git-50-gb76f37fd (x64 https://musl.cc/x86_64-linux-musl-native.tgz,
SHA-256 eb1db6f0f3c2bdbdbfb993d7ef7e2eeef82ac1259f6a6e1757c33a97dbcef3ad;
x86 https://musl.cc/i686-linux-musl-cross.tgz, SHA-256
93bd5504d5d0349258c43d7a668b506acbd627d31c0843a96e4b4c47b27a0180; pinned in
corpus.toolchain.MUSL_PINS and fetched by exercisers/fetch_musl_toolchain.sh)
with XMRig's own -DBUILD_STATIC=ON, and it is the one image where the
dependencies cannot be shared: a static ELF cannot load libuv.so or
libssl.so, so libuv 1.52.1 and OpenSSL 3.5.8, the pinned sources of every
other axis, are built as static archives and are in the image, with musl
libc, libgcc, libstdc++ and libatomic. Two filters keep the family to the
miner, and what they leave is measured:

  * The musl glue baseline (corpus.baseline, scripts/corpus/README.md "The
    musl half") removes the libc, libgcc, libgcc_eh, libstdc++ and libatomic
    code by name and PicHash (name and opcode hash as well on these
    toolchains, because a 32-bit PIC function's PicHash follows the image's
    layout): 4,060 functions on x64, 4,242 on x86.
  * Recipe.exclude_functions removes libuv and OpenSSL by name, with two
    patterns generated from the function symbols of the pinned libuv.a,
    libcrypto.a and libssl.a of both architectures (_musl_dep_symbols.py:
    495 prefix rules and 1,643 exact names, by exercisers/musl_dep_symbols.py;
    19,956 names in all). The archives define them, not the image, so what
    the rule removes does not depend on what this miner happens to pull in:
    19,827 functions on x64, 19,572 on x86, recorded as
    excluded_function_count.

Counts, kept + removed as runtime + excluded = total: x64 3,771 + 4,060 +
19,858 = 27,689; x86 3,403 + 4,242 + 19,595 = 27,240. Of the excluded,
19,827 and 19,572 are libuv and OpenSSL (the two patterns above) and 31 and 23
are the vendored code removed by name (below); the image was 3,802 and 3,426
functions kept before that. For scale, the glibc axis keeps 3,735 (x64) and
3,847 (x86) functions of the same source: the miner is the same ~3,800
functions, and the rest of the file is libc, libgcc, libstdc++, libuv and
OpenSSL.

How well that separates, measured against the linker and not against the
names, on the images as they were before the vendored-code rule below removed
31 and 23 more functions: each image was relinked with -Wl,-Map (byte-identical) and every SMDA
function attributed to the archive member holding its input section. Of the
3,802 functions x64 keeps, 3,553 are in the miner's own objects (and its
vendored libraries), 123 are unnamed with no input section (SMDA's .cold
partitions and tail fragments), and 126 are not the miner's: 70 libstdc++, 4
libc, 1 libgcc_eh (named like the baseline's copy but with other bytes - a
symbol several archive members define), and 51 libuv/OpenSSL (19 unnamed, 32
whose names the miner also defines, e.g. Argon2's blake2b_compress and
fill_block, and OpenSSL's ed25519 fe_*/ge_*, which the rule leaves alone
because deleting them would delete miner code). On x86, of 3,426: 3,251, 80
unattributed, 95 (19 libstdc++, 11 libc, 1 libgcc, 64 libuv/OpenSSL of which
32 unnamed and 32 shared names). Those 126 and 95 are in the image under the
miner's name and are the measured limit of this axis.

The axis against the others, ten instructions or more: musl x64 has 2,310
PicHashes and shares 31 with GCC/glibc (2,215), none with MinGW (2,095) and 1
with MSVC (4,140) - so the earlier "0 between any two toolchains" holds for
GCC, MinGW and MSVC and not for the second GCC; x86 has 2,633 and shares 113,
30 and 0 with GCC, MinGW and MSVC. Against the dependency families, for the
code the exclusion removes (measured before it): of the musl x64 image's 8,430
libcrypto PicHashes, 64 are in data/OpenSSL 3.5.8 (MinGW); of 2,529 libssl, 0;
of 374 libuv, 0 are in data/libuv 1.52.1 (MinGW, MSVC). On x86: 104 of 13,218,
0 of 3,528 and 2 of 441. The static musl OpenSSL and libuv are not carried
by those families (neither has an ELF image), so excluding them leaves a
gap in the corpus rather than a duplicate; they are not filed under the
miner.

Vendored code removed by name. Recipe.exclude_functions on all eight images
also removes the functions of llhttp, the Argon2/Blake2b helpers, rapidjson and
the C++ standard library that other corpus families carry too, by exact name
and only where every function of that name in the recipe's images is shown to
be the library's (_stack_vendored.py states the tests: PicHash against
data/llhttp, data/argon2 and data/BLAKE2, a weaker same-name opcode similarity
of at least 80% counted separately, and for rapidjson and the standard library
the declaring namespace). 479 functions leave the eight images: 255 llhttp
(212 PicHash-confirmed, 43 by opcode similarity), 18 Argon2/Blake2b
helpers (PicHash-confirmed), 113 rapidjson, 92 standard library and 1
`__scrt_common_main_seh`. Kept / removed as runtime / excluded by name, per
image: Linux x64 3,735 / 9 / 48, x86 3,847 / 6 / 40; MinGW x64 3,647 / 174 / 60,
x86 4,032 / 186 / 40; MSVC x64 14,256 / 2,307 / 121, x86 14,477 / 2,179 / 116;
the musl pair is above. `validate --deep` with the llhttp, argon2 and BLAKE2
branches' data present: 266 leakage findings before, 14 after, 13 of which still
name XMRig. Left in on purpose, with the reasons in _stack_vendored.py: the
ge_p1p1_*, slide and load_3/load_4 helpers of the ed25519 code the miner
bundles (equal to OpenSSL's by PicHash in places, but 26 of its 61 names are not
OpenSSL's), rotr64, the llhttp identifiers whose other-architecture function
is not 80% similar, and the three MinGW CRT helpers.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _musl_dep_symbols
from . import _stack_deps as deps
from . import _stack_vendored as vendored


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
    "filed here, except the functions of llhttp, Argon2/Blake2b, rapidjson and "
    "the C++ standard library that other families also carry, which are "
    "removed by exact name (exclude_functions, see _stack_vendored.py)."
)


MUSL_EXCLUDE = _musl_dep_symbols.EXCLUDE

_VENDORED_TEXT = (
    "The llhttp, Argon2/Blake2b, rapidjson and C++ standard library functions "
    "that other families also carry are removed by exact name as well "
    "(_stack_vendored.py), in the same excluded_function_count."
)

_NOTES_MUSL = (
    "Static musl ELF built with XMRig's own -DBUILD_STATIC=ON: stock "
    "configuration with the GPU backends and hwloc off, libuv 1.52.1 and "
    "OpenSSL 3.5.8 built from pinned sources as static archives. Build type "
    "Corpus carries CMake's Release optimisation and XMRig's -Ofast without "
    "XMRig's -s. -maes is XMRig's own; no -march is set. musl libc, libgcc, "
    "libgcc_eh, libstdc++ and libatomic code is removed by the musl glue "
    "baseline (removed_runtime_functions). " + deps.MUSL_EXCLUDE_TEXT + " "
    + _VENDORED_TEXT + " " + deps.MUSL_PIN_TEXT
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
        exclude_functions=vendored.patterns("XMRig_6.25.0"),
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
        exclude_functions=vendored.patterns("XMRig_6.25.0_linux"),
        build_flags="-O3 -DNDEBUG -Ofast (build type Corpus), -maes, "
                    "per-file -msse4.1/-mavx2/-mvaes as XMRig's CMake sets; "
                    "no -s, no -static-libstdc++",
        notes=_NOTES,
    )


def _musl():
    return Recipe(
        family="XMRig",
        version="6.25.0",
        upstream="https://github.com/xmrig/xmrig",
        license=_LICENSE,
        source=Source(git_url="https://github.com/xmrig/xmrig.git",
                      git_ref=_TAG),
        extra_sources=dict(deps.EXTRA_SOURCES),
        build=(deps.musl_openssl() + deps.musl_libuv() + [
            BuildStep(
                "cmake -S . -B build-{arch} -DCMAKE_C_COMPILER={cc} "
                "-DCMAKE_CXX_COMPILER={cxx} -DBUILD_STATIC=ON "
                + _CONFIG + " " + deps.musl_dep_options(),
                env={"CFLAGS": "", "CXXFLAGS": ""}),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ]),
        artifacts=[Artifact(path="build-{arch}/xmrig", component="xmrig")],
        toolchains=["musl_x86", "musl_x64"],
        exclude_functions=(list(MUSL_EXCLUDE)
                           + vendored.patterns("XMRig_6.25.0_musl")),
        build_flags="-O3 -DNDEBUG -Ofast (build type Corpus), -maes, "
                    "per-file -msse4.1/-mavx2/-mvaes as XMRig's CMake sets; "
                    "no -s; -DBUILD_STATIC=ON (-static, static-pie by the "
                    "toolchain's default), libuv.a and OpenSSL libcrypto.a/"
                    "libssl.a",
        notes=_NOTES_MUSL,
    )


RECIPES = {
    "XMRig_6.25.0": _mingw(),
    "XMRig_6.25.0_linux": _linux(),
    "XMRig_6.25.0_musl": _musl(),
}
