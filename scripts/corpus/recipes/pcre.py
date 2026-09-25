"""PCRE2 and legacy PCRE - regular expression engines.

Both code bases are covered because they share almost no code: PCRE1 ended at
8.45 but is still linked into a great deal of legacy Windows software, while
PCRE2 is what anything current uses. Within PCRE2 the split is around 10.43,
which reworked the compile and JIT internals.

JIT is enabled everywhere here: it is the default in most distributions and
adds a substantial, distinctive body of code. PCRE1's CMake build defaults
JIT and UTF off, unlike PCRE2's, so 8.45 has to ask for them explicitly to
match what a distribution or a vendored copy actually ships.
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


_CMAKE_PCRE1 = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
                "-DCMAKE_C_COMPILER={cc} -DCMAKE_RC_COMPILER={windres} "
                "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
                "-DBUILD_SHARED_LIBS=ON -DPCRE_SUPPORT_JIT=ON "
                "-DPCRE_SUPPORT_UTF=ON -DPCRE_SUPPORT_UNICODE_PROPERTIES=ON "
                # The C++ wrapper is a separate library that would drag
                # libstdc++ in; what is wanted here is the C engine.
                "-DPCRE_BUILD_PCRECPP=OFF "
                "-DPCRE_BUILD_TESTS=OFF -DPCRE_BUILD_PCREGREP=OFF")


RECIPES = {
    # The end of the line for PCRE1, and what every legacy binary still
    # carrying PCRE has. A release tarball rather than a git tag: upstream's
    # repository moved to PCRE2 and the 8.x sources only exist as the
    # SourceForge archives, so this is pinned by digest instead.
    "pcre_8.45": Recipe(
        family="pcre",
        version="8.45",
        upstream="https://www.pcre.org/",
        license="BSD-3-Clause",
        source=Source(
            url="https://downloads.sourceforge.net/project/pcre/pcre/8.45/"
                "pcre-8.45.tar.bz2",
            sha256="4dae6fdcd2bb0bb6c37b5f97c33c2be954da743985369cddac3546e3218bffb8"),
        build=[
            BuildStep(_CMAKE_PCRE1),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="build-{arch}/libpcre.dll",
                            component="libpcre.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (CMake Release), JIT and UTF enabled",
    ),
    # Before the 10.43 compile/JIT rework.
    "pcre2_10.39": _pcre2("10.39", "pcre2-10.39"),
    # Current.
    "pcre2_10.45": _pcre2("10.45", "pcre2-10.45"),
}
