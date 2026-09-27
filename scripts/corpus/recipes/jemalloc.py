"""jemalloc - allocator with a real, if niche, Windows presence.

Turns up in Firefox-derived code and in some game and anti-cheat stacks.
The C++ wrapper is disabled: it adds libstdc++ surface without adding
allocator code, and libstdc++ belongs to the MinGW family, not here.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


RECIPES = {
    "jemalloc_5.3.0": Recipe(
        family="jemalloc",
        version="5.3.0",
        upstream="https://github.com/jemalloc/jemalloc",
        license="BSD-2-Clause",
        source=Source(git_url="https://github.com/jemalloc/jemalloc.git",
                      git_ref="5.3.0"),
        build=[
            BuildStep("./autogen.sh --host={host} --disable-cxx "
                      "--enable-shared --disable-static"),
            BuildStep("make -j$(nproc) build_lib_shared"),
        ],
        artifacts=[Artifact(path="lib/jemalloc.dll", component="jemalloc.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (upstream default)",
        requires=["autoconf"],
    ),
}
