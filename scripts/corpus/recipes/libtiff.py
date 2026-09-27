"""libtiff - image library with a long CVE history, embedded widely.

Codecs that would pull external dependencies are disabled, so the build needs
nothing preinstalled; the core TIFF reader and writer is what matters for
recognising reuse.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx} "
          "-DCMAKE_RC_COMPILER={windres} -DCMAKE_FIND_ROOT_PATH=/usr/{host} "
          "-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON "
          "-Dtiff-tests=OFF -Dtiff-tools=OFF -Dtiff-docs=OFF "
          "-Dzlib=OFF -Djpeg=OFF -Djbig=OFF -Dlzma=OFF -Dzstd=OFF -Dwebp=OFF "
          "-Dlerc=OFF -Dlibdeflate=OFF")


def _libtiff(version, git_ref):
    return Recipe(
        family="libtiff",
        version=version,
        upstream="https://gitlab.com/libtiff/libtiff",
        license="libtiff (MIT-like)",
        source=Source(git_url="https://gitlab.com/libtiff/libtiff.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="build-{arch}/libtiff/libtiff.dll",
                            component="libtiff.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (CMake Release), optional codecs disabled",
    )


RECIPES = {
    # The CVE-heavy generation embedded in a lot of shipped software.
    "libtiff_4.0.10": _libtiff("4.0.10", "v4.0.10"),
    # Current; 4.5 moved to a CMake-first, refactored codec layer.
    "libtiff_4.7.0": _libtiff("4.7.0", "v4.7.0"),
}
