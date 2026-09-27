"""lz4 - fast compression, common in modern loaders, packers and installers.

No coverage exists in the corpus today. Upstream publishes no checksums for
the release tarballs, and the 1.10.0 asset was re-uploaded after publication,
so these are pinned to the immutable git tags instead.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


def _lz4(version, git_ref, dll_path):
    return Recipe(
        family="lz4",
        version=version,
        upstream="https://github.com/lz4/lz4",
        license="BSD-2-Clause (library), GPL-2.0 (programs)",
        source=Source(git_url="https://github.com/lz4/lz4.git", git_ref=git_ref),
        # lib/Makefile only takes its DLL path when TARGET_OS names a MinGW
        # flavour, which cross-building from Linux does not set by itself.
        build=[
            BuildStep("make -C lib clean", allow_failure=True),
            BuildStep("make -C lib -j$(nproc) TARGET_OS={mingw_os} CC={cc} "
                      "WINDRES={windres} liblz4"),
        ],
        # 1.9.x links the DLL into lib/dll/; 1.10.0 moved it up to lib/.
        artifacts=[Artifact(path=dll_path, component="liblz4.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (lib/Makefile default)",
        notes="The DLL carries lz4.c, lz4hc.c, lz4frame.c and xxhash.c.",
    )


RECIPES = {
    # By far the most widely deployed release.
    "lz4_1.9.4": _lz4("1.9.4", "v1.9.4", "lib/dll/liblz4.dll"),
    # Current; new compression level 2, reworked HC and a rewritten lz4frame
    # small-data path, so the code differs materially from 1.9.x.
    "lz4_1.10.0": _lz4("1.10.0", "v1.10.0", "lib/liblz4.dll"),
}
