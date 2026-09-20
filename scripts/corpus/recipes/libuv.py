"""libuv - the event loop behind Node.js and a good deal of C tooling.

No coverage exists in the corpus today. Pinned to git tags: GitHub's codeload
archive endpoint is not reliably reachable and upstream publishes no checksum
files, whereas a tag resolves to an immutable commit.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_RC_COMPILER={windres} "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
          "-DBUILD_SHARED_LIBS=ON -DLIBUV_BUILD_TESTS=OFF")


def _libuv(version, git_ref):
    return Recipe(
        family="libuv",
        version=version,
        upstream="https://github.com/libuv/libuv",
        license="MIT",
        source=Source(git_url="https://github.com/libuv/libuv.git", git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="build-{arch}/libuv.dll", component="libuv.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (CMake Release)",
    )


RECIPES = {
    # What Node 16/18 shipped, so it is vendored very widely.
    "libuv_1.44.2": _libuv("1.44.2", "v1.44.2"),
    "libuv_1.52.1": _libuv("1.52.1", "v1.52.1"),
}
