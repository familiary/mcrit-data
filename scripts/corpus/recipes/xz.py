"""liblzma (xz) - LZMA2, ubiquitous in installers and increasingly in droppers.

No coverage exists in the corpus today. Pinned to signed git tags rather than
release tarballs on purpose: the 2024 xz-utils backdoor (CVE-2024-3094) was
present only in the 5.6.0/5.6.1 release tarballs and not in the git tree, so
building from git is both reproducible and the safer provenance.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_RC_COMPILER={windres} "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} "
          "-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=OFF")


def _xz(version, git_ref):
    return Recipe(
        family="liblzma",
        version=version,
        upstream="https://github.com/tukaani-project/xz",
        license="0BSD (liblzma)",
        source=Source(git_url="https://github.com/tukaani-project/xz.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="build-{arch}/liblzma.dll", component="liblzma.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 (upstream overrides CMake Release's -O3)",
    )


RECIPES = {
    # Last of the 5.4 series, and the newest release predating the 5.6.0
    # tarball backdoor. 5.2.x would be the wider-deployed pick but its CMake
    # support is incomplete - the resource compiler cannot find config.h - so
    # covering it would mean the autotools path and an autogen.sh run.
    "liblzma_5.4.7": _xz("5.4.7", "v5.4.7"),
    # Current stable; the 5.4 -> 5.6 jump added the multithreaded .xz decoder,
    # a substantial block of new code relative to 5.2.
    "liblzma_5.8.1": _xz("5.8.1", "v5.8.1"),
}
