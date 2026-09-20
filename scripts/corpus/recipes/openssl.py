"""OpenSSL - the largest crypto body in the corpus.

Three versions, chosen for architecture rather than recency: 1.1.1 has no
provider layer at all and is still by far the most encountered OpenSSL, 3.0
introduced the provider architecture, and 3.5 is the current LTS. A 3.x point
release would add almost nothing next to these.

Upstream publishes a SHA-256 beside every release asset, and the digests
recorded here were taken from those files.

Honest caveat: OpenSSL in the wild is overwhelmingly MSVC-built, so a MinGW
reference matches those only weakly. Its strength here is matching
MinGW/GCC-built Windows binaries, and by proxy ELF builds.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# The DLL names carry both the soversion and, on 64-bit only, an -x64 suffix
# (libcrypto-3-x64.dll vs libcrypto-3.dll), so the outputs are normalised to
# stable names rather than spelling out four variants per version.
_NORMALISE = ("cp $(ls libcrypto-*.dll | head -1) libcrypto.dll && "
              "cp $(ls libssl-*.dll | head -1) libssl.dll")

# --cross-compile-prefix prepends the triple to the tool names itself, so the
# usual fully-qualified CC would come out doubled as
# x86_64-w64-mingw32-x86_64-w64-mingw32-gcc. Hand it the bare names.
_ENV = {"CC": "gcc", "CXX": "g++", "AR": "ar", "RANLIB": "ranlib",
        "WINDRES": "windres"}


def _openssl(version, sha256, url):
    return Recipe(
        family="OpenSSL",
        version=version,
        upstream="https://github.com/openssl/openssl",
        license="Apache-2.0" if version.startswith("3") else "OpenSSL / SSLeay",
        source=Source(url=url, sha256=sha256),
        build=[
            BuildStep("./Configure {openssl_target} "
                      "--cross-compile-prefix={prefix} shared no-tests",
                      env=_ENV),
            # OpenSSL's parallel make has a dependency-file race that can lose
            # a .d.tmp rename; a second invocation completes cleanly.
            BuildStep("make -j$(nproc) build_libs build_programs || "
                      "make -j$(nproc) build_libs build_programs", env=_ENV),
            BuildStep(_NORMALISE),
        ],
        artifacts=[
            Artifact(path="libcrypto.dll", component="libcrypto"),
            Artifact(path="libssl.dll", component="libssl"),
        ],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (upstream default)",
        requires=["perl"],
        notes="perlasm generates GAS assembly, so no nasm is needed for the "
              "mingw targets.",
    )


RECIPES = {
    # No provider layer; still the most encountered OpenSSL by a wide margin.
    "OpenSSL_1.1.1w": _openssl(
        "1.1.1w", "cf3098950cb4d853ad95c0841f1f9c6d3dc102dccfcacd521d93925208b76ac8",
        "https://github.com/openssl/openssl/releases/download/OpenSSL_1_1_1w/openssl-1.1.1w.tar.gz"),
    # First LTS of the provider architecture.
    "OpenSSL_3.0.15": _openssl(
        "3.0.15", "23c666d0edf20f14249b3d8f0368acaee9ab585b09e1de82107c66e1f3ec9533",
        "https://github.com/openssl/openssl/releases/download/openssl-3.0.15/openssl-3.0.15.tar.gz"),
    # Current LTS.
    "OpenSSL_3.5.8": _openssl(
        "3.5.8", "a8f84a39918ec6415ce765d9b429d313ba97b8143169c172e734b9514464f5b2",
        "https://github.com/openssl/openssl/releases/download/openssl-3.5.8/openssl-3.5.8.tar.gz"),
}
