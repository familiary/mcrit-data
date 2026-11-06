"""xmrig-proxy 6.26.0 - the stratum proxy, MinGW (PE) and Linux (ELF).

Backlog issue #84. DRAFT DOCSTRING - rewritten after measurement.
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
                      "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx} "
                      "-DCMAKE_RC_COMPILER={windres} "
                      "-DCMAKE_FIND_ROOT_PATH=/usr/{host} "
                      "-DCMAKE_BUILD_TYPE=Release "
                      + deps.mingw_dep_options() + " " + deps.MINGW_SHIM_FLAGS + " "
                      + _LINK_RULE % " -shared-libgcc",
                      env={"CFLAGS": "", "CXXFLAGS": ""}),
        ]
        artifact = Artifact(path="build-{arch}/xmrig-proxy.exe",
                            component="xmrig-proxy.exe")
        toolchains = ["mingw_x86", "mingw_x64"]
    steps.append(BuildStep("cmake --build build-{arch} -j$(nproc)"))
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
