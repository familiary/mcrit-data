"""cJSON - small C JSON parser, very widely vendored into C tooling.

No coverage exists in the corpus today. The library is tiny, so two versions
are plenty; upstream publishes no checksums, hence git tags.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_FIND_ROOT_PATH=/usr/{host} "
          "-DCMAKE_BUILD_TYPE=Release -DENABLE_CJSON_TEST=Off "
          "-DBUILD_SHARED_AND_STATIC_LIBS=Off")


def _cjson(version, git_ref):
    return Recipe(
        family="cJSON",
        version=version,
        upstream="https://github.com/DaveGamble/cJSON",
        license="MIT",
        source=Source(git_url="https://github.com/DaveGamble/cJSON.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="build-{arch}/libcjson.dll", component="libcjson.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (CMake Release)",
    )


RECIPES = {
    "cJSON_1.7.15": _cjson("1.7.15", "v1.7.15"),
    "cJSON_1.7.19": _cjson("1.7.19", "v1.7.19"),
}
