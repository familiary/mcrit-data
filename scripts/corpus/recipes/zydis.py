"""Zydis and Zycore - the x86/x86-64 decoder, built with MinGW (placeholder)."""

from ..recipe import Artifact, BuildStep, Recipe, Source

_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_POLICY_VERSION_MINIMUM=3.5 "
          "-DCMAKE_SYSTEM_NAME=Windows -DCMAKE_C_COMPILER={cc} "
          "-DCMAKE_CXX_COMPILER={cxx} -DCMAKE_RC_COMPILER={windres} "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
          "-DZYDIS_BUILD_EXAMPLES=OFF -DZYDIS_BUILD_TOOLS=OFF")
_LINK = ("{cc} -shared -o zydis.dll -Wl,--whole-archive "
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
        artifacts=[Artifact(path="zydis.dll", component="zydis.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (CMake Release)",
        notes="Placeholder.",
    )


RECIPES = {
    "Zydis_3.1.0": _zydis("3.1.0", "v3.1.0"),
    "Zydis_4.1.1": _zydis("4.1.1", "v4.1.1"),
}
