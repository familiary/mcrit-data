"""libevent - event notification library linked into a lot of older tooling."""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_RC_COMPILER={windres} "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
          "-DEVENT__DISABLE_OPENSSL=ON -DEVENT__DISABLE_TESTS=ON "
          "-DEVENT__DISABLE_SAMPLES=ON -DEVENT__DISABLE_BENCHMARK=ON "
          "-DEVENT__LIBRARY_TYPE=SHARED")


def _libevent(version, git_ref):
    return Recipe(
        family="libevent",
        version=version,
        upstream="https://github.com/libevent/libevent",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/libevent/libevent.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[
            Artifact(path="build-{arch}/bin/libevent_core.dll",
                     component="libevent_core.dll"),
            Artifact(path="build-{arch}/bin/libevent_extra.dll",
                     component="libevent_extra.dll"),
        ],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (CMake Release), OpenSSL backend disabled",
    )


RECIPES = {
    # Overwhelmingly the most deployed release.
    "libevent_2.1.12": _libevent("2.1.12", "release-2.1.12-stable"),
}
