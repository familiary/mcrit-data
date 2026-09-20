"""cJSON - small C JSON parser, very widely vendored into C tooling.

No coverage exists in the corpus today. Upstream publishes no checksums,
hence git tags.

Three versions, chosen to actually span distinct code rather than to sweep
the release list. 1.7.15 and 1.7.19 differ by about 120 lines of cJSON.c out
of 3100 - roughly 4%, which for an ~80-function library is close to a
duplicate - so a pre-1.7 release is included to give the family a genuinely
different parser to match against: 1.6.0 differs from 1.7.15 by some 660
lines. 1.6.0 is the pick within that era because it is the single most
vendored pre-1.7 tag (148 copies of its cJSON.h in GitHub code search against
62 for 1.5.9, the largest of the ten 1.5.x releases) and is the last state of
the code before the 1.7 series.
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
    # Last release before the 1.7 series, and the pre-1.7 tag still most often
    # found vendored into other trees.
    "cJSON_1.6.0": _cjson("1.6.0", "v1.6.0"),
    "cJSON_1.7.15": _cjson("1.7.15", "v1.7.15"),
    "cJSON_1.7.19": _cjson("1.7.19", "v1.7.19"),
}
