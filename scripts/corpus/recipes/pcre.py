"""PCRE2 and legacy PCRE - regular expression engines.

Both code bases are covered because they share almost no code: PCRE1 ended at
8.45 but is still linked into a great deal of legacy Windows software, while
PCRE2 is what anything current uses. Within PCRE2 the split is around 10.43,
which reworked the compile and JIT internals.

JIT is enabled: it is the default in most distributions and adds a
substantial, distinctive body of code.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_RC_COMPILER={windres} "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
          "-DBUILD_SHARED_LIBS=ON -DPCRE2_SUPPORT_JIT=ON "
          "-DPCRE2_BUILD_TESTS=OFF -DPCRE2_BUILD_PCRE2GREP=OFF")


def _pcre2(version, git_ref):
    return Recipe(
        family="pcre2",
        version=version,
        upstream="https://github.com/PCRE2Project/pcre2",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/PCRE2Project/pcre2.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="build-{arch}/libpcre2-8.dll",
                            component="libpcre2-8.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (CMake Release), JIT enabled",
    )


RECIPES = {
    # Before the 10.43 compile/JIT rework.
    "pcre2_10.39": _pcre2("10.39", "pcre2-10.39"),
    # Current.
    "pcre2_10.45": _pcre2("10.45", "pcre2-10.45"),
}
