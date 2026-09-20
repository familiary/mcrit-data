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
          "-DENABLE_TESTING=OFF -DENABLE_PROGRAMS=OFF")


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


RECIPES = {
    # The 2.28 LTS line, which is what the embedded/IoT installed base ships.
    "mbedTLS_2.28.10": _mbedtls("2.28.10", "mbedtls-2.28.10"),
    # Current 3.6 LTS.
    "mbedTLS_3.6.7": _mbedtls("3.6.7", "mbedtls-3.6.7"),
}
