"""mbedTLS - the TLS/crypto stack of the embedded and IoT world.

No coverage exists in the corpus today. Both currently maintained LTS lines
are covered; 4.x is deliberately left out, because it moved the crypto core
into a separate tf-psa-crypto submodule and has almost no deployed base yet.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx} "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
          "-DUSE_SHARED_MBEDTLS_LIBRARY=ON -DUSE_STATIC_MBEDTLS_LIBRARY=OFF "
          "-DENABLE_TESTING=OFF -DENABLE_PROGRAMS=OFF "
          # 2.28 formats a time_t with %d, which is fatal under mingw's
          # -Werror=format=. Turning fatal warnings off is a build setting;
          # the alternative would be editing upstream source.
          "-DMBEDTLS_FATAL_WARNINGS=OFF")


def _mbedtls(version, git_ref):
    return Recipe(
        family="mbedTLS",
        version=version,
        upstream="https://github.com/Mbed-TLS/mbedtls",
        license="Apache-2.0",
        # The fetch stage initialises submodules; mbedTLS >= 3.6 needs the
        # framework submodule at configure time even with testing disabled.
        source=Source(git_url="https://github.com/Mbed-TLS/mbedtls.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[
            Artifact(path="build-{arch}/library/libmbedcrypto.dll",
                     component="libmbedcrypto.dll"),
            Artifact(path="build-{arch}/library/libmbedx509.dll",
                     component="libmbedx509.dll"),
            Artifact(path="build-{arch}/library/libmbedtls.dll",
                     component="libmbedtls.dll"),
        ],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (CMake Release)",
    )


# Upstream has well over a hundred releases. Covering them all would be the
# combinatorial sweep this corpus does not want: consecutive point releases
# differ by a handful of patched functions, MCRIT deduplicates by PicHash
# anyway, and the result would be a large family of near-identical entries
# that dilutes matching rather than improving it. What is covered instead is
# one build per code generation - the points where the library was actually
# restructured.
RECIPES = {
    # Previous long-term line, embedded very widely through 2019-2021 and
    # predating the 2.28 restructure.
    "mbedTLS_2.16.12": _mbedtls("2.16.12", "mbedtls-2.16.12"),
    # The 2.28 LTS line, which is what the embedded/IoT installed base ships.
    "mbedTLS_2.28.10": _mbedtls("2.28.10", "mbedtls-2.28.10"),
    # 3.0 was a deliberate API and internal break from the 2.x series.
    "mbedTLS_3.0.0": _mbedtls("3.0.0", "mbedtls-3.0.0"),
    # Current 3.6 LTS.
    "mbedTLS_3.6.7": _mbedtls("3.6.7", "mbedtls-3.6.7"),
}
