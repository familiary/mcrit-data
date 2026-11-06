"""Zydis and Zycore built for Linux (placeholder)."""

from ..recipe import Artifact, BuildStep, Recipe, Source

_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_POLICY_VERSION_MINIMUM=3.5 "
          "-DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON "
          '-DCMAKE_C_FLAGS="{archflag} -fvisibility=hidden" '
          '-DCMAKE_CXX_FLAGS="{archflag} -fvisibility=hidden" '
          "-DZYDIS_BUILD_EXAMPLES=OFF -DZYDIS_BUILD_TOOLS=OFF")
_LINK = ("{cc} {archflag} -shared -o libzydis.so -Wl,--whole-archive "
         "build-{arch}/libZydis.a build-{arch}/zycore/libZycore.a "
         "-Wl,--no-whole-archive")


def _zydis(version, tag):
    return Recipe(
        family="Zydis",
        version=version,
        upstream="https://github.com/zyantific/zydis",
        license="MIT",
        source=Source(git_url="https://github.com/zyantific/zydis.git",
                      git_ref=tag),
        build=[BuildStep(_CMAKE),
               BuildStep("cmake --build build-{arch} -j$(nproc)"),
               BuildStep(_LINK)],
        artifacts=[Artifact(path="libzydis.so", component="libzydis.so")],
        toolchains=["linux_x86", "linux_x64"],
        build_flags="-O3 -fPIC -fvisibility=hidden (CMake Release)",
        notes="Placeholder.",
    )


RECIPES = {
    "Zydis_3.1.0_linux": _zydis("3.1.0", "v3.1.0"),
    "Zydis_4.1.1_linux": _zydis("4.1.1", "v4.1.1"),
}
