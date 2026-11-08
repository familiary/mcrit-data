"""xmrig-proxy 6.26.0 - the stratum proxy, as PE (MinGW), ELF (glibc) and static ELF (musl).

Backlog issue #84. The tag v6.26.0 is commit 0dc23f69. MSVC is in
xmrig_proxy_msvc.py.

The proxy is not the miner: it has no RandomX or CryptoNight backend, so the
vendoring question of issue #18 does not arise. It is the stratum handling in
src/proxy and src/net, around a copy of XMRig's src/base. src/3rdparty holds
epee, fmt, getopt, llhttp and rapidjson, compiled in with no module identity,
filed here. llhttp is 9.3.0, identical to XMRig's apart from an extra api.h.

The cost of that shared base, measured and not avoided: at ten instructions
or more, 773 of this artefact's 1286 PicHashes on Linux x64 (716 of 1187 on
MinGW x64, 2005 of 2670 on MSVC x64) are also in data/XMRig. `validate --deep`
reports a PicHash only when three or more families carry it, so a pair of
families sharing hundreds is not flagged, and nothing in the build removes
src/base from either side. The findings it gave were rapidjson (shared
with XMRig and xmr-stak) and standard library code, plus - with the open
llhttp branch's data present - llhttp; those functions are removed by exact
name (Recipe.exclude_functions, _stack_vendored.py; "Vendored code removed
by name" below).

Configuration: stock (TLS, HTTP API, environment variables). Unlike XMRig,
xmrig-proxy's flags.cmake sets no -O level and no -s, so CMake's own Release
(-O3 -DNDEBUG) is used as it stands; the -static / -static-libstdc++ link
flags are the same problem and are dealt with as in xmrig.py (the stock link
rule without <LINK_FLAGS> on ELF, the compiler wrapper on MinGW, the
lower-case <Windows.h> alias). libuv 1.52.1 and OpenSSL 3.5.8 are built from
pinned sources and linked as shared libraries. No -march and no -maes: the
proxy does no AES.

Counts (kept, removed as runtime): Linux x64 2499 and 8, x86 2506 and 6;
MinGW x64 2101 and 170, x86 2632 and 180; MSVC x64 9,945 and 2,148, x86
10,620 and 2,094. Six axes; PicHashes shared between two axes of the same
architecture at ten instructions or more: none on x64, 19 (GCC/MinGW) and 1
(MinGW/MSVC) on x86.

The musl axis (xmrig-proxy_6.26.0_musl, x86 and x64) is the static ELF: built
with the musl.cc GCC 11.2.1 toolchains pinned in corpus.toolchain.MUSL_PINS
(x64 https://musl.cc/x86_64-linux-musl-native.tgz, SHA-256
eb1db6f0f3c2bdbdbfb993d7ef7e2eeef82ac1259f6a6e1757c33a97dbcef3ad; x86
https://musl.cc/i686-linux-musl-cross.tgz, SHA-256
93bd5504d5d0349258c43d7a668b506acbd627d31c0843a96e4b4c47b27a0180) and
-DBUILD_STATIC=ON, with CMake Release as on the other axes. A static ELF
cannot load libuv or OpenSSL, so they are linked in as static archives built
from the same pinned sources, and removed again as in xmrig.py: the musl glue
baseline (libc, libgcc, libstdc++, libatomic) and Recipe.exclude_functions
with the patterns generated from the pinned libuv.a, libcrypto.a and
libssl.a (_musl_dep_symbols.py; excluded_function_count). Counts, kept +
removed as runtime + excluded = total: x64 2,221 + 3,932 + 19,856 = 26,009;
x86 2,119 + 4,134 + 19,594 = 25,847 (of the excluded, 19,827 and 19,574 are
libuv and OpenSSL and 29 and 20 the vendored code removed by name). Against
the linker map, measured before that second rule (see xmrig.py for the
method), of the 2,250 functions x64 kept 2,059 are in the proxy's own
objects, 56 are unnamed with no input section and 135 are not the proxy's:
76 libstdc++, 6 libc, 1 libgcc_eh, 52 libuv/OpenSSL (20 unnamed, 32 whose
names the proxy also defines); x86, of 2,139: 1,993, 38 and 108 (23
libstdc++, 11 libc, 1 libgcc, 73 libuv/OpenSSL). At ten instructions or more
the musl axis has 1,423 PicHashes on x64 and 1,690 on x86; it shares 5 and
71 with GCC/glibc, 0 and 5 with MinGW and 0 and 0 with MSVC; and 862 (x64) and
136 (x86) with the musl XMRig image (2,310 and 2,633), the same shared
src/base the other axes show, much reduced on x86 because 32-bit PIC code
carries image-specific displacements.

Evidence for the target is the issue's own: naming only (the TRIBACK script
builds xmrig-proxy from source on the victim host with whatever gcc it has),
so the Linux x64 axis is the one the evidence supports and the rest is
coverage.

Vendored code removed by name. Recipe.exclude_functions on all eight images
removes, by exact name, the functions of llhttp, rapidjson and the C++
standard library that other corpus families carry too, where every function of
that name in the recipe's images is shown to be the library's (the tests,
tiers and the identifiers left in are in _stack_vendored.py and xmrig.py). 449
functions leave the eight images: 257 llhttp (213 PicHash-confirmed against
data/llhttp, 44 by opcode similarity of at least 80%, counted separately), 113
rapidjson, 78 standard library and 1 `__scrt_common_main_seh`. Kept / removed
as runtime / excluded by name, per image: Linux x64 2,499 / 8 / 47, x86 2,506 /
6 / 37; MinGW x64 2,101 / 170 / 56, x86 2,632 / 180 / 39; MSVC x64 9,945 /
2,148 / 113, x86 10,620 / 2,094 / 108; the musl pair is above. The images were
re-derived from their committed archives, not rebuilt.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _musl_dep_symbols
from . import _stack_deps as deps
from . import _stack_vendored as vendored


_TAG = "v6.26.0"

# Release is CMake's -O3 -DNDEBUG and xmrig-proxy's flags.cmake adds no -O or
# -s of its own, so Release is used as it stands on the GNU side.
_LINK_RULE = ("-DCMAKE_CXX_LINK_EXECUTABLE='<CMAKE_CXX_COMPILER> <FLAGS> "
              "<CMAKE_CXX_LINK_FLAGS> <OBJECTS> -o <TARGET> <LINK_LIBRARIES>%s'")

_NOTES = (
    "Stock configuration (TLS, HTTP API, environment variables), libuv "
    "1.52.1 and OpenSSL 3.5.8 built from pinned sources and linked as shared "
    "libraries so neither is in the image. CMake Release (-O3 -DNDEBUG); "
    "xmrig-proxy's flags.cmake adds no optimisation level and no -s. The "
    "link rule leaves out the -static / -static-libstdc++ flags flags.cmake "
    "adds, which would file libstdc++ under this name. No -march, no -maes. "
    "llhttp, fmt, epee, rapidjson and getopt are vendored in src/3rdparty and "
    "stay filed here, except the functions of llhttp, rapidjson and the C++ "
    "standard library that other families also carry, which are removed by "
    "exact name (exclude_functions, see _stack_vendored.py)."
)

_LICENSE = ("GPL-3.0-or-later (SPDX identifier in src/version.h); vendored "
            "trees carry their own: llhttp MIT, fmt MIT, rapidjson MIT")


MUSL_EXCLUDE = _musl_dep_symbols.EXCLUDE

_VENDORED_TEXT = (
    "The llhttp, Argon2/Blake2b, rapidjson and C++ standard library functions "
    "that other families also carry are removed by exact name as well "
    "(_stack_vendored.py), in the same excluded_function_count."
)

_NOTES_MUSL = (
    "Static musl ELF built with xmrig-proxy's -DBUILD_STATIC=ON: stock "
    "configuration (TLS, HTTP API, environment variables), libuv 1.52.1 and "
    "OpenSSL 3.5.8 built from pinned sources as static archives. CMake "
    "Release (-O3 -DNDEBUG); no -s, no -march, no -maes. musl libc, libgcc, "
    "libgcc_eh, libstdc++ and libatomic code is removed by the musl glue "
    "baseline (removed_runtime_functions). " + deps.MUSL_EXCLUDE_TEXT + " "
    + _VENDORED_TEXT + " " + deps.MUSL_PIN_TEXT
)


def _proxy(linux):
    if linux:
        steps = deps.linux_openssl() + deps.linux_libuv() + [
            BuildStep("cmake -S . -B build-{arch} -DCMAKE_BUILD_TYPE=Release "
                      + deps.linux_dep_options() + " " + _LINK_RULE % "",
                      env={"CFLAGS": "", "CXXFLAGS": ""}),
        ]
        artifact = Artifact(path="build-{arch}/xmrig-proxy",
                            component="xmrig-proxy")
        toolchains = ["linux_x86", "linux_x64"]
    else:
        steps = deps.mingw_openssl() + deps.mingw_libuv() + [
            deps.mingw_header_shim(),
            BuildStep("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
                      "-DCMAKE_SYSTEM_PROCESSOR={platform} "
                      "-DCMAKE_C_COMPILER={cc} " + deps.MINGW_WRAPPER + " "
                      "-DCMAKE_RC_COMPILER={windres} "
                      "-DCMAKE_FIND_ROOT_PATH=/usr/{host} "
                      "-DCMAKE_BUILD_TYPE=Release "
                      + deps.mingw_dep_options() + " " + deps.MINGW_SHIM_FLAGS + " "
                      ,
                      env=dict(deps.MINGW_WRAPPER_ENV, CFLAGS="", CXXFLAGS="")),
        ]
        artifact = Artifact(path="build-{arch}/xmrig-proxy.exe",
                            component="xmrig-proxy.exe")
        toolchains = ["mingw_x86", "mingw_x64"]
    steps.append(BuildStep("cmake --build build-{arch} -j$(nproc)",
                           env={} if linux else dict(deps.MINGW_WRAPPER_ENV)))
    return Recipe(
        family="xmrig-proxy",
        version="6.26.0",
        upstream="https://github.com/xmrig/xmrig-proxy",
        license=_LICENSE,
        source=Source(git_url="https://github.com/xmrig/xmrig-proxy.git",
                      git_ref=_TAG),
        extra_sources=dict(deps.EXTRA_SOURCES),
        build=steps,
        artifacts=[artifact],
        toolchains=toolchains,
        exclude_functions=vendored.patterns(
            "xmrig-proxy_6.26.0_linux" if linux else "xmrig-proxy_6.26.0"),
        build_flags="-O3 -DNDEBUG (CMake Release), no -s, no -static",
        notes=_NOTES,
    )


def _musl():
    return Recipe(
        family="xmrig-proxy",
        version="6.26.0",
        upstream="https://github.com/xmrig/xmrig-proxy",
        license=_LICENSE,
        source=Source(git_url="https://github.com/xmrig/xmrig-proxy.git",
                      git_ref=_TAG),
        extra_sources=dict(deps.EXTRA_SOURCES),
        build=(deps.musl_openssl() + deps.musl_libuv() + [
            BuildStep("cmake -S . -B build-{arch} -DCMAKE_C_COMPILER={cc} "
                      "-DCMAKE_CXX_COMPILER={cxx} -DBUILD_STATIC=ON "
                      "-DCMAKE_BUILD_TYPE=Release " + deps.musl_dep_options(),
                      env={"CFLAGS": "", "CXXFLAGS": ""}),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ]),
        artifacts=[Artifact(path="build-{arch}/xmrig-proxy",
                            component="xmrig-proxy")],
        toolchains=["musl_x86", "musl_x64"],
        exclude_functions=(list(MUSL_EXCLUDE)
                           + vendored.patterns("xmrig-proxy_6.26.0_musl")),
        build_flags="-O3 -DNDEBUG (CMake Release), no -s; -DBUILD_STATIC=ON "
                    "(-static, static-pie by the toolchain's default), "
                    "libuv.a and OpenSSL libcrypto.a/libssl.a",
        notes=_NOTES_MUSL,
    )


RECIPES = {
    "xmrig-proxy_6.26.0": _proxy(False),
    "xmrig-proxy_6.26.0_linux": _proxy(True),
    "xmrig-proxy_6.26.0_musl": _musl(),
}
