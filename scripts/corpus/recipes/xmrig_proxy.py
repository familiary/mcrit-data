"""xmrig-proxy 6.26.0 - the stratum proxy, as PE (MinGW) and ELF (glibc).

Backlog issue #84. The tag v6.26.0 is commit 0dc23f69. MSVC is in
xmrig_proxy_msvc.py.

The proxy is not the miner: it has no RandomX or CryptoNight backend, so the
vendoring question of issue #18 does not arise. It is the stratum handling in
src/proxy and src/net, around a copy of XMRig's src/base. src/3rdparty holds
epee, fmt, getopt, llhttp and rapidjson, compiled in with no module identity,
filed here. llhttp is 9.3.0, identical to XMRig's apart from an extra api.h.

The cost of that shared base, measured and not avoided: at ten instructions
or more, 807 of this artefact's 1320 PicHashes on Linux x64 (747 of 1218 on
MinGW x64, 2078 of 2748 on MSVC x64) are also in data/XMRig. `validate --deep`
reports a PicHash only when three or more families carry it, so a pair of
families sharing hundreds is not flagged, and nothing in the build removes
src/base from either side. The findings it does give are rapidjson (shared
with XMRig and xmr-stak) and standard library code, plus - with the open
llhttp branch's data present - llhttp.

Configuration: stock (TLS, HTTP API, environment variables). Unlike XMRig,
xmrig-proxy's flags.cmake sets no -O level and no -s, so CMake's own Release
(-O3 -DNDEBUG) is used as it stands; the -static / -static-libstdc++ link
flags are the same problem and are dealt with as in xmrig.py (the stock link
rule without <LINK_FLAGS> on ELF, the compiler wrapper on MinGW, the
lower-case <Windows.h> alias). libuv 1.52.1 and OpenSSL 3.5.8 are built from
pinned sources and linked as shared libraries. No -march and no -maes: the
proxy does no AES.

Counts (kept, removed as runtime): Linux x64 2546 and 8, x86 2543 and 6;
MinGW x64 2157 and 170, x86 2671 and 180; MSVC x64 10,065 and 2,141, x86
10,735 and 2,087. Six axes; PicHashes shared between two axes of the same
architecture at ten instructions or more: none on x64, 39 (GCC/MinGW) and 1
(MinGW/MSVC) on x86.

Evidence for the target is the issue's own: naming only (the TRIBACK script
builds xmrig-proxy from source on the victim host with whatever gcc it has),
so the Linux x64 axis is the one the evidence supports and the rest is
coverage.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _stack_deps as deps


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
    "stay filed here."
)

_LICENSE = ("GPL-3.0-or-later (SPDX identifier in src/version.h); vendored "
            "trees carry their own: llhttp MIT, fmt MIT, rapidjson MIT")


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
        build_flags="-O3 -DNDEBUG (CMake Release), no -s, no -static",
        notes=_NOTES,
    )


RECIPES = {
    "xmrig-proxy_6.26.0": _proxy(False),
    "xmrig-proxy_6.26.0_linux": _proxy(True),
}
