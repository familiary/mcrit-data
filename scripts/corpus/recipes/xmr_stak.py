"""xmr-stak 2.10.8 - CPU backend, MinGW (PE) and Linux (ELF).

Backlog issue #63. DRAFT DOCSTRING - rewritten after measurement.
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

_NOTES = (
    "CPU backend only (CUDA and OpenCL off), without libmicrohttpd and hwloc, "
    "with TLS: OpenSSL 3.5.8 built from a pinned source and linked as a "
    "shared library. XMR-STAK_COMPILE=generic, so no -march=native; xmr-stak "
    "adds -msse2 -maes itself. CMake Release (-O3 -DNDEBUG)."
)


def _stak(linux):
    if linux:
        steps = deps.linux_openssl() + [
            BuildStep("cmake -S . -B build-{arch} " + _CONFIG + " "
                      + deps.linux_dep_options(uv=False),
                      env={"CFLAGS": "", "CXXFLAGS": ""}),
        ]
        artifact = Artifact(path="build-{arch}/bin/xmr-stak",
                            component="xmr-stak")
        toolchains = ["linux_x64"]
    else:
        steps = deps.mingw_openssl() + [
            BuildStep("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
                      "-DCMAKE_SYSTEM_PROCESSOR={platform} "
                      "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx} "
                      "-DCMAKE_RC_COMPILER={windres} "
                      "-DCMAKE_FIND_ROOT_PATH=/usr/{host} " + _CONFIG + " "
                      + deps.mingw_dep_options(uv=False),
                      env={"CFLAGS": "", "CXXFLAGS": ""}),
        ]
        artifact = Artifact(path="build-{arch}/bin/xmr-stak.exe",
                            component="xmr-stak.exe")
        toolchains = ["mingw_x64"]
    steps.append(BuildStep("cmake --build build-{arch} -j$(nproc)"))
    return Recipe(
        family="xmr-stak",
        version="2.10.8",
        upstream="https://github.com/fireice-uk/xmr-stak",
        license="GPL-3.0",
        source=Source(git_url="https://github.com/fireice-uk/xmr-stak.git",
                      git_ref=_TAG),
        extra_sources=dict(deps.OPENSSL_ONLY),
        build=steps,
        artifacts=[artifact],
        toolchains=toolchains,
        build_flags="-O3 -DNDEBUG (CMake Release), -msse2 -maes",
        notes=_NOTES,
    )


RECIPES = {
    "xmr-stak_2.10.8": _stak(False),
    "xmr-stak_2.10.8_linux": _stak(True),
}
