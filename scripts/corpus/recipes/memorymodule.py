"""MemoryModule - the canonical in-memory PE loader (mcrit-data issue #7).

Reused verbatim by a long tail of packers and loaders, almost always as a
vendored copy frozen at some old commit, so the last tagged release and the
current master bracket the realistic range of what is encountered.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


def _memory_module(version, git_ref):
    return Recipe(
        family="MemoryModule",
        version=version,
        upstream="https://github.com/fancycode/MemoryModule",
        license="MPL-2.0",
        source=Source(git_url="https://github.com/fancycode/MemoryModule.git",
                      git_ref=git_ref),
        # The sub-makefiles use CFLAGS = rather than ?=, so overriding it on
        # the command line drops -DSAMPLEDLL_EXPORTS and the sample DLL fails
        # to build; it has to be repeated. Upstream defaults to -O0, which is
        # not the shape vendored copies are compiled at, hence -O2.
        # Only the example target is built. On master the default target also
        # builds tests/, where TestSuite.c is compiled as C++ against a C
        # declaration and fails to link - an upstream test-suite problem that
        # happens after the loader binaries have already linked fine.
        build=[
            BuildStep("make clean", allow_failure=True),
            BuildStep('make example PLATFORM={platform} '
                      'CFLAGS="-Wall -O2 -DSAMPLEDLL_EXPORTS"'),
        ],
        artifacts=[
            Artifact(path="example/DllLoader/DllLoader.exe",
                     component="DllLoader.exe"),
        ],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 (upstream default is -O0)",
        notes="Upstream's makefiles compile MemoryModule.c with g++, so static "
              "helpers carry C++ mangling; this does not affect code matching.",
    )


RECIPES = {
    # Last tagged release, and the version copy-pasted into a decade of tooling.
    "MemoryModule_0.0.4": _memory_module("0.0.4", "v0_0_4"),
    # Master carries six years of post-tag changes that alter code shape:
    # binary-search export lookup (2017), case-sensitive name fix (2018) and
    # the >4 GB span fix.
    "MemoryModule_2019-02-24": _memory_module(
        "2019-02-24", "5f83e41c3a3e7c6e8284a5c1afa5a38790809461"),
}
