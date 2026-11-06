"""RandomX - tevador's proof-of-work, MinGW and Linux builds.

Backlog issue #18. DRAFT DOCSTRING - rewritten after measurement.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_UPSTREAM = "https://github.com/tevador/RandomX"

# CMake's Release is -O3 -DNDEBUG and does not strip; -DARCH=default is
# upstream's own default and the one that does not pass -march=native.
_CONFIG = "-DCMAKE_BUILD_TYPE=Release -DARCH=default"
_HIDDEN = " -DCMAKE_C_FLAGS=-fvisibility=hidden -DCMAKE_CXX_FLAGS=-fvisibility=hidden"

_WHOLE = ("-Wl,--whole-archive build-{arch}/librandomx.a "
          "-Wl,--no-whole-archive")


def _randomx(version, tag, linux):
    if linux:
        configure = "cmake -S . -B build-{arch} " + _CONFIG + _HIDDEN
        link = ("{cxx} {archflag} -shared -o build-{arch}/librandomx.so "
                + _WHOLE)
        artifact = Artifact(path="build-{arch}/librandomx.so",
                            component="librandomx.so")
        toolchains = ["linux_x86", "linux_x64"]
    else:
        configure = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
                     "-DCMAKE_SYSTEM_PROCESSOR={platform} "
                     "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx} "
                     "-DCMAKE_RC_COMPILER={windres} "
                     "-DCMAKE_FIND_ROOT_PATH=/usr/{host} " + _CONFIG)
        link = ("{cxx} -shared -o build-{arch}/randomx.dll " + _WHOLE
                + " -shared-libgcc")
        artifact = Artifact(path="build-{arch}/randomx.dll",
                            component="randomx.dll")
        toolchains = ["mingw_x86", "mingw_x64"]
    return Recipe(
        family="RandomX",
        version=version,
        upstream=_UPSTREAM,
        license="BSD-3-Clause",
        source=Source(git_url=_UPSTREAM + ".git", git_ref=tag),
        build=[
            BuildStep(configure, env={"CFLAGS": "", "CXXFLAGS": ""}),
            BuildStep("cmake --build build-{arch} --target randomx -j$(nproc)"),
            BuildStep(link),
        ],
        artifacts=[artifact],
        toolchains=toolchains,
        build_flags="-O3 -DNDEBUG (CMake Release), -fvisibility=hidden, "
                    "ARCH=default (-maes, and -mssse3 / -mavx2 on the two "
                    "Argon2 units, on x86-64 only)",
    )


RECIPES = {
    "RandomX_1.2.1": _randomx("1.2.1", "v1.2.1", linux=False),
    "RandomX_1.2.1_linux": _randomx("1.2.1", "v1.2.1", linux=True),
    "RandomX_2.0.1": _randomx("2.0.1", "v2.0.1", linux=False),
    "RandomX_2.0.1_linux": _randomx("2.0.1", "v2.0.1", linux=True),
}
