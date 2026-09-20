"""donut - position-independent loader generator (mcrit-data issue #5).

The issue suggests "MinGW, MSVC, and the docker (might cover mingw already)".
It does not: the Dockerfile installs mingw-w64 but only runs the plain
Makefile, which builds the Linux ELF generator. Makefile.mingw is the target
that produces Windows binaries, and it drives both cross compilers itself, so
one run emits 32- and 64-bit output together.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


def _donut(version, git_ref):
    return Recipe(
        family="donut",
        version=version,
        upstream="https://github.com/TheWover/donut",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/TheWover/donut.git", git_ref=git_ref),
        # The committed loader_exe_*.h are MSVC-compiled and are what ships in
        # the release binaries and the donut-shellcode PyPI package, so they
        # are the more representative artefact. They must be extracted before
        # the build, because Makefile.mingw regenerates those same headers
        # from its own GCC output and overwrites them.
        build=[
            BuildStep("python3 {repo}/scripts/corpus/extract_blob.py carray "
                      "loader_exe_x86.h donut_loader_x86.bin"),
            BuildStep("python3 {repo}/scripts/corpus/extract_blob.py carray "
                      "loader_exe_x64.h donut_loader_x64.bin"),
            BuildStep("make -f Makefile.mingw clean", allow_failure=True),
            BuildStep("make -f Makefile.mingw"),
        ],
        artifacts=[
            Artifact(path="donut_loader_x86.bin", component="loader_msvc_x86",
                     is_blob=True, bitness=32, is_library=False),
            Artifact(path="donut_loader_x64.bin", component="loader_msvc_x64",
                     is_blob=True, bitness=64, is_library=False),
            Artifact(path="donut.exe", component="donut.exe", is_library=False),
        ],
        # Makefile.mingw is not parameterised by toolchain; it selects both
        # cross compilers internally, so it is run once.
        toolchains=["mingw_x64"],
        build_flags="-O2 (Makefile.mingw default for the generator)",
        notes="Upstream also ships MSVC-compiled loader blobs in "
              "loader/loader_exe_x86.h and loader_exe_x64.h; this recipe covers "
              "the generator as built by GCC on Linux, which is what the "
              "project's own Docker image and source builds produce.",
    )


RECIPES = {
    # Current release. v1.0 carries byte-identical loader blobs, so it adds
    # nothing on that axis and is not covered separately.
    "donut_1.1": _donut("1.1", "47758d787209dd1744f58c140102ac91b649df16"),
}
