"""libcurl - extremely commonly statically linked into downloaders and droppers.

The TLS backend shapes the emitted code more than the version does, so these
build against Schannel, which is both the dependency-free choice here and
what a Windows build most often uses.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_RC_COMPILER={windres} "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
          "-DBUILD_SHARED_LIBS=ON -DCURL_USE_SCHANNEL=ON "
          "-DCURL_USE_LIBPSL=OFF -DCURL_ZLIB=OFF -DCURL_BROTLI=OFF "
          "-DCURL_ZSTD=OFF -DUSE_LIBIDN2=OFF -DBUILD_TESTING=OFF "
          "-DBUILD_CURL_EXE=OFF")


def _libcurl(version, git_ref):
    return Recipe(
        family="libcurl",
        version=version,
        upstream="https://github.com/curl/curl",
        license="curl (MIT-like)",
        source=Source(git_url="https://github.com/curl/curl.git", git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="build-{arch}/lib/libcurl.dll",
                            component="libcurl.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (CMake Release), Schannel TLS backend",
        notes="A second build against OpenSSL would be a genuinely different "
              "code shape and is worth adding once OpenSSL is in the corpus.",
    )


RECIPES = {
    # Widely vendored 2023 release.
    "libcurl_8.4.0": _libcurl("8.4.0", "curl-8_4_0"),
    # Current.
    "libcurl_8.15.0": _libcurl("8.15.0", "curl-8_15_0"),
}
