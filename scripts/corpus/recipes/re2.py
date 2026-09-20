"""RE2 - Google's regular expression engine.

The two versions here bracket the largest code-level split in this part of
the corpus: 2022-06-01 is the last release before RE2 took a dependency on
Abseil, so it is entirely standalone, while current RE2 is built on Abseil
throughout. They are effectively different code bases rather than adjacent
versions.

Abseil is built into the tree first for the newer one, so the recipe stays
self-contained.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CXX = "{cxx}-posix"

_CMAKE_STANDALONE = (
    "cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
    "-DCMAKE_CXX_COMPILER=" + _CXX + " -DCMAKE_FIND_ROOT_PATH=/usr/{host} "
    "-DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17 "
    "-DRE2_BUILD_TESTING=OFF -DBUILD_SHARED_LIBS=ON")

_LINK = ("echo 'int anchor(){return 0;}' > anchor.cc && " + _CXX +
         " -std=c++17 -O2 -shared -o re2.dll anchor.cc "
         "-Wl,--whole-archive $(find build-{arch} -name 'libre2.a' | tr '\\n' ' ') "
         "-Wl,--no-whole-archive -shared-libgcc")


RECIPES = {
    # Last standalone release, before the Abseil dependency.
    "re2_2022-06-01": Recipe(
        family="re2",
        version="2022-06-01",
        upstream="https://github.com/google/re2",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/google/re2.git",
                      git_ref="2022-06-01"),
        build=[
            BuildStep(_CMAKE_STANDALONE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
            BuildStep(_LINK),
        ],
        artifacts=[Artifact(path="re2.dll", component="re2.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 -std=c++17",
        notes="Standalone; no Abseil. Built with the posix-threads compiler, "
              "because the win32-threads <mutex> is unusable.",
    ),
}
