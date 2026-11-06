"""Tor 0.4.8.25 client and circuit core, with server-only modules disabled.

The 2014 report that motivated this target did not identify a Tor version; the
0.4.8 LTS line is the first that contains Equi-X. The Tor image covers the
client/circuit path from that line and is built dynamically against OpenSSL,
zlib and libevent so those dependency bodies are not attributed to Tor. The
PoW service module stays disabled; its separate Equi-X/HashX image is built
from the same release's vendored sources with Tor's ``HASHX_SIZE=8``.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_VERSION = "0.4.8.25"
_TOR_URL = "https://dist.torproject.org/tor-0.4.8.25.tar.gz"
_TOR_SHA256 = "371cd22178fa4b35e64b03933403890795ce3e304c5850a5b59adcc68820a799"
_TOR_SOURCE = Source(url=_TOR_URL, sha256=_TOR_SHA256)
_LIBEVENT_SOURCE = Source(
    git_url="https://github.com/libevent/libevent.git",
    git_ref="5df3037d10556bfcb675bc73e516978b75fc7bc7",
)
_OPENSSL_SOURCE = Source(
    url=("https://github.com/openssl/openssl/releases/download/"
         "OpenSSL_1_1_1w/openssl-1.1.1w.tar.gz"),
    sha256="cf3098950cb4d853ad95c0841f1f9c6d3dc102dccfcacd521d93925208b76ac8",
)
_ZLIB_SOURCE = Source(
    url="https://zlib.net/fossils/zlib-1.3.1.tar.gz",
    sha256="9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23",
)
_LIBEVENT_UPSTREAM = "https://github.com/libevent/libevent"


def _recipe(flavor, toolchains):
    command = (
        "python {repo}/scripts/corpus/exercisers/tor_build.py "
        "--flavor %s --arch {arch} --bitness {bitness} --cc {cc} "
        "--libevent {libevent}"
        % flavor
    )
    dependencies = {"libevent": _LIBEVENT_SOURCE}
    artifact = "src/app/tor"
    if flavor == "mingw":
        command += " --openssl {openssl} --zlib {zlib}"
        dependencies.update({"openssl": _OPENSSL_SOURCE, "zlib": _ZLIB_SOURCE})
        artifact += ".exe"
    return Recipe(
        family="Tor",
        version=_VERSION,
        upstream="https://gitlab.torproject.org/tpo/core/tor",
        license="See upstream source",
        source=_TOR_SOURCE,
        extra_sources=dependencies,
        build=[BuildStep(command)],
        artifacts=[Artifact(path=artifact,
                            component="tor-client")],
        toolchains=toolchains,
        build_flags=("-O2 -g; dynamic OpenSSL and zlib; libevent 2.1.12 "
                     "shared; --disable-module-relay --disable-module-dirauth "
                     "--disable-asciidoc --disable-unittests"),
        notes=("Built from the official Tor 0.4.8.25 source archive. Relay "
               "and directory-authority modules are disabled per the client "
               "scope. Linux dynamically imports system OpenSSL 3.5.7 and "
               "zlib 1.3.1; MinGW builds OpenSSL 1.1.1w and zlib 1.3.1 as "
               "shared dependencies. Both use shared libevent 2.1.12. "
               "Equi-X's PoW service is disabled and recorded as a separate "
               "EquiX family using HASHX_SIZE=8. The release exposes an "
               "Autotools build, not a Visual Studio project."),
        requires=["cmake", "make", "pkg-config"],
    )


RECIPES = {
    "Tor_0.4.8.25_linux": _recipe("linux", ["linux_x64"]),
    "Tor_0.4.8.25_mingw": _recipe("mingw", ["mingw_x86", "mingw_x64"]),
}
