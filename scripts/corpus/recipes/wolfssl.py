"""wolfSSL - embedded TLS stack.

One version only, deliberately. wolfSSL is genuinely uncommon in Windows
malware compared with OpenSSL and mbedTLS, and the default feature set
already yields a large function count, so a second version would add bulk
without adding reach.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_RC_COMPILER={windres} "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
          "-DBUILD_SHARED_LIBS=ON -DWOLFSSL_EXAMPLES=no "
          "-DWOLFSSL_CRYPT_TESTS=no")


RECIPES = {
    "wolfSSL_5.9.2": Recipe(
        family="wolfSSL",
        version="5.9.2",
        upstream="https://github.com/wolfSSL/wolfssl",
        # COPYING at v5.9.2-stable is GPLv3 and every source header offers
        # "version 3 ... or any later version". The GPLv2 fallback in LICENSING
        # is not general: it applies only when wolfSSL is combined with one of
        # the named Exception Software projects, which is not this build.
        license="GPL-3.0-or-later",
        source=Source(git_url="https://github.com/wolfSSL/wolfssl.git",
                      git_ref="v5.9.2-stable"),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="build-{arch}/libwolfssl.dll",
                            component="libwolfssl.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 (CMake Release)",
    ),
}
