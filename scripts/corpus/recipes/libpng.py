"""libpng - found in old packers, installers and image-handling tooling.

libpng needs zlib, which is staged into the source tree first so the whole
build stays inside one source root and needs nothing preinstalled.

Two picks: the 1.2 branch, which is structurally different from 1.6 and
still turns up in older software, and the current 1.6 release. Intra-branch
churn in 1.6 is very low, so covering several 1.6 point releases would be
padding.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_ZLIB = ("curl -sSL --fail -o zlib.tar.gz https://zlib.net/fossils/zlib-1.3.1.tar.gz "
         "&& tar xf zlib.tar.gz && mv zlib-1.3.1 zlib "
         "&& make -C zlib -f win32/Makefile.gcc PREFIX={prefix} STRIP=true "
         "-j$(nproc) libz.a")

_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_RC_COMPILER={windres} "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
          "-DPNG_SHARED=ON -DPNG_STATIC=OFF -DPNG_TESTS=OFF -DPNG_TOOLS=OFF "
          # Absolute, or CMake records it as a make target and the link step
          # fails with "No rule to make target 'zlib/libz.a'".
          "-DZLIB_INCLUDE_DIR=$PWD/zlib -DZLIB_LIBRARY=$PWD/zlib/libz.a")


RECIPES = {
    "libpng_1.6.50": Recipe(
        family="libpng",
        version="1.6.50",
        upstream="https://github.com/pnggroup/libpng",
        license="libpng-2.0",
        source=Source(git_url="https://github.com/pnggroup/libpng.git",
                      git_ref="v1.6.50"),
        build=[
            BuildStep(_ZLIB),
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="build-{arch}/libpng16.dll",
                            component="libpng16.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (CMake Release)",
    ),
}
