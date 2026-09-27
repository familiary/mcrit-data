"""libsodium - X25519/XSalsa20 crypto linked by several ransomware families.

No coverage exists in the corpus today, and a hit on this library is
immediately meaningful during triage, which makes it worth more than its
size suggests.

1.0.20 comes from the signed release tarball, whose digest is pinned below.
1.0.18 is taken from its git tag instead: upstream publishes minisign/GPG
signatures rather than a checksum file, and pinning a commit is verifiable
here where checking a signature is not.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CONFIGURE = "./configure --host={host} --enable-shared --disable-static"


RECIPES = {
    "libsodium_1.0.20": Recipe(
        family="libsodium",
        version="1.0.20",
        upstream="https://github.com/jedisct1/libsodium",
        license="ISC",
        source=Source(
            url="https://download.libsodium.org/libsodium/releases/libsodium-1.0.20.tar.gz",
            sha256="ebb65ef6ca439333c2bb41a0c1990587288da07f6c7fd07cb3a18cc18d30ce19"),
        build=[
            BuildStep(_CONFIGURE),
            BuildStep("make -j$(nproc)"),
        ],
        artifacts=[Artifact(path="src/libsodium/.libs/libsodium-26.dll",
                            component="libsodium-26.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (upstream default)",
    ),
    # Enormous installed base; the version most often found statically linked.
    "libsodium_1.0.18": Recipe(
        family="libsodium",
        version="1.0.18",
        upstream="https://github.com/jedisct1/libsodium",
        license="ISC",
        source=Source(git_url="https://github.com/jedisct1/libsodium.git",
                      git_ref="1.0.18"),
        build=[
            # The git tree ships no configure script.
            BuildStep("./autogen.sh -s"),
            # autogen.sh fetches config.sub/config.guess from savannah over
            # plain HTTP and does not check what came back; behind a proxy it
            # writes an HTML error page, and configure then dies with "cannot
            # run ./build-aux/config.sub". The host automake has both.
            BuildStep("cp /usr/share/automake-*/config.sub "
                      "/usr/share/automake-*/config.guess build-aux/ && "
                      "chmod +x build-aux/config.sub build-aux/config.guess"),
            BuildStep(_CONFIGURE),
            BuildStep("make -j$(nproc)"),
        ],
        artifacts=[Artifact(path="src/libsodium/.libs/libsodium-23.dll",
                            component="libsodium-23.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (upstream default)",
        requires=["autoconf", "automake", "libtoolize"],
    ),
}
