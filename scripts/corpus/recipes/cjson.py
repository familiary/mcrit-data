"""cJSON - small C JSON parser, very widely vendored into C tooling.

No coverage exists in the corpus today. Upstream publishes no checksums,
hence git tags.

Three versions, chosen to actually span distinct code rather than to sweep
the release list. 1.7.15 and 1.7.19 differ by 119 lines of cJSON.c out of
3110, so a pre-1.7 release is included to give the family a genuinely
different parser to match against: 1.6.0 differs from 1.7.15 by 662 lines.
1.6.0 is the pick within that era because it is the single most vendored
pre-1.7 tag (148 copies of its cJSON.h in GitHub code search against 62 for
1.5.9, the largest of the ten 1.5.x releases) and is the last state of the
code before the 1.7 series.

Two 1.7 releases are kept although they overlap heavily, and the overlap was
measured rather than guessed at. Counting functions of at least 10
instructions, 1.7.15 and 1.7.19 share 44 PicHashes of 62 and 63 on x64 and
50 of 68 and 69 on x86 - about 70 to 74% of each sample. 1.6.0 shares only
17 to 22 with either, 27 to 41%. That is high, and much higher than the
families whose versions are years apart (cryptopp's oldest against its
newest overlaps 8 to 12%, protobuf's 3 to 4%), so the case for keeping both
has to be made on what the non-shared part contains rather than on its size:

  - It is not noise. On x64, 1.7.19 carries 19 functions with no PicHash
    twin in 1.7.15, and MinHash does not close the gap for the ones that
    matter: cJSON_Duplicate (501 instructions) scores 0.39 against its
    1.7.15 counterpart and parse_value (509) scores 0.66. Those are the two
    largest functions in the library. A matcher holding only 1.7.15 would
    score exactly the code a cJSON sample is most likely to be recognised by
    as a poor match.
  - 1.7.19 also carries cJSON_Duplicate_rec, the recursion-depth-limited
    helper the 1.7.18 rewrite split out, which exists in neither 1.7.15 nor
    1.6.0 at all.

Adjacent releases overlapping this much is normal for this corpus rather
than peculiar to cJSON - libsodium 1.0.18 against 1.0.20 sits at 77%,
nlohmann_json 3.11.3 against 3.12.0 at 68%, 7-Zip 23.01 against 26.03 at 63%
- and the duplication the project brief warns about is a second reference
for code the corpus already holds, not two distinct builds of a library that
happen to share most of their functions. Neither of these samples is a
subset of the other, so both are kept.
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
        # CMAKE_BUILD_TYPE=Release supplies only -O3 -DNDEBUG (CMake's GNU
        # default; cJSON sets no CMAKE_C_FLAGS_RELEASE of its own). The rest
        # comes from cJSON's own ENABLE_CUSTOM_COMPILER_FLAGS, which is ON by
        # default at all three tags and appends its list to CMAKE_C_FLAGS, so
        # the build receives it whether or not this tooling asked for it.
        # Recording only the -O3 understated what the compiler was given:
        # -std=c89 changes what the front end accepts and -fstack-protector-strong
        # changes the emitted code, which is visible in the artefacts - all six
        # import __stack_chk_fail from libssp-0.dll, which an unhardened build
        # would not. The flags are filtered through CHECK_C_COMPILER_FLAG
        # first, so the three Clang-only warning options in that list
        # (-Wcomma, -Wmissing-variable-declarations, -Wused-but-marked-unused)
        # are dropped by GCC and are not named here. The warning options that
        # do survive are left summarised: they gate the build but do not reach
        # the code generator.
        build_flags="-O3 -DNDEBUG (CMake Release) plus cJSON's own "
                    "ENABLE_CUSTOM_COMPILER_FLAGS default: -std=c89 -pedantic "
                    "-fstack-protector-strong -fvisibility=hidden, "
                    "-DCJSON_EXPORT_SYMBOLS -DCJSON_API_VISIBILITY, and "
                    "-Wall -Wextra -Werror with a long warning list",
    )


RECIPES = {
    # Last release before the 1.7 series, and the pre-1.7 tag still most often
    # found vendored into other trees.
    "cJSON_1.6.0": _cjson("1.6.0", "v1.6.0"),
    "cJSON_1.7.15": _cjson("1.7.15", "v1.7.15"),
    "cJSON_1.7.19": _cjson("1.7.19", "v1.7.19"),
}
