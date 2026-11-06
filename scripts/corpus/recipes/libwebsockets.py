"""libwebsockets - the C WebSocket/HTTP library (warmcat/libwebsockets).

Motivation: Microsoft's NeedyMantis write-up says a second version of that
family's communications DLL "uses Libwebsockets (LWS) instead of WinINet".
The write-up gives no libwebsockets version, no TLS backend, no compiler and
no linking mode, so none of those is known; what follows is chosen by
measurement, not by what the sample embeds.

TLS: OpenSSL, as a separate DLL. The beacon is HTTPS on 443, 4.x has no
other Windows TLS backend that builds here (SChannel exists from 5.0 and does
not compile with this MinGW: 5.1.0 stops at the undeclared
BCRYPT_KDF_RAW_SECRET in lib/tls/schannel/lws-genec.c), and OpenSSL is
upstream's default backend. TLS support is not a detail of the build: the
no-TLS build of 4.5.8 shares only 62% of its 10+ instruction PicHashes with
the OpenSSL build (4.3.10: 55%, 5.1.0: 64%), because the TLS paths change
what is inlined across the core. OpenSSL 1.1.1w is used for every version,
the same pinned source as recipes/openssl.py: against OpenSSL 3.0.15 the
4.5.8 and 5.1.0 DLLs share 99-100% of their PicHashes, so the TLS library's
version does not change libwebsockets' code, and 1.1.1w builds all four
versions below. libssl and libcrypto stay
separate DLLs and are linked through import libraries only, so none of
OpenSSL's code is in these artefacts: the dependency contributes zero
functions (see data/OpenSSL for those).

Versions: the 4.x minors are not point releases of each other. Measured as
the share of 10+ instruction PicHashes (x64, OpenSSL build) the smaller
build has in common with the other, 4.0.21 against 4.3.10 is 19%, 4.3.10
against 4.5.8 33%, and 5.1.0 against 4.5.8 16%. 4.0.21, 4.3.10, 4.5.8 and
5.1.0 are the last releases of four such generations. 3.x is not here:
lib/misc/dir.c of 3.2.3 does `#error` on Windows without libuv. 4.1.x, 4.2.x
and 4.4.x fall between the four and are left out to keep the family small.

Flags only, upstream untouched. -Wno-error because 4.0.21 predates
DISABLE_WERROR and GCC 13 rejects its enum/int declarations. The OpenSSL
include and library directories go in through CMAKE_C_FLAGS as well as
OPENSSL_*: lws probes the OpenSSL API with check_c_source_compiles, which sees
CMAKE_C_FLAGS but neither the OPENSSL_* variables nor -L, and without them
every probe fails and 4.0-4.2 select the pre-1.1 struct layout and stop
compiling. For 5.x, LWS_WITH_SCHANNEL=OFF (see above), LWS_HAVE_PTHREAD_H=0
(a win32-threads MinGW has pthread.h but libwebsockets.h then uses
pthread_mutex_t), LWS_WITH_SPAWN=OFF (windows-spawn.c includes <Psapi.h>,
which only exists in this MinGW as psapi.h) and LWS_WITH_HTTP3=OFF (which
otherwise demands GnuTLS) are needed; the spawn API is therefore absent from
the 5.1.0 artefacts.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_OPENSSL_VERSION = "1.1.1w"
_OPENSSL_SHA256 = "cf3098950cb4d853ad95c0841f1f9c6d3dc102dccfcacd521d93925208b76ac8"

# Same spelling as recipes/openssl.py: --cross-compile-prefix prepends the
# triple itself, so the tools are named bare.
_ENV = {"CC": "gcc", "CXX": "g++", "AR": "ar", "RANLIB": "ranlib",
        "WINDRES": "windres"}

_STAGE_OPENSSL = (
    # Outside the source tree: lws refuses an include directory that lies
    # inside its own source directory.
    "rm -rf {out}/lws-openssl-{arch} && mkdir -p {out}/lws-openssl-{arch} && "
    "tar xf {openssl_archive} -C {out}/lws-openssl-{arch} --strip-components=1 && "
    "cd {out}/lws-openssl-{arch} && "
    "./Configure {openssl_target} --cross-compile-prefix={prefix} shared no-tests && "
    # OpenSSL's parallel make has a dependency-file race; a second
    # invocation completes cleanly.
    "(make -j$(nproc) build_libs || make -j$(nproc) build_libs)")

_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx} "
          "-DCMAKE_RC_COMPILER={windres} -DCMAKE_FIND_ROOT_PATH=/usr/{host} "
          "-DCMAKE_BUILD_TYPE=Release "
          "\"-DCMAKE_C_FLAGS=-I{out}/lws-openssl-{arch}/include -L{out}/lws-openssl-{arch} "
          "-Wno-error\" "
          "-DLWS_WITH_SHARED=ON -DLWS_WITH_STATIC=OFF -DLWS_WITH_SSL=ON "
          "-DLWS_WITHOUT_TESTAPPS=ON -DLWS_WITH_MINIMAL_EXAMPLES=OFF "
          "-DLWS_WITH_PLUGINS=OFF -DDISABLE_WERROR=ON "
          "-DOPENSSL_ROOT_DIR={out}/lws-openssl-{arch} "
          "-DOPENSSL_INCLUDE_DIR={out}/lws-openssl-{arch}/include "
          "-DOPENSSL_SSL_LIBRARY={out}/lws-openssl-{arch}/libssl.dll.a "
          "-DOPENSSL_CRYPTO_LIBRARY={out}/lws-openssl-{arch}/libcrypto.dll.a")

# 5.x only; see the docstring.
_CMAKE_V5 = (" -DLWS_WITH_SCHANNEL=OFF -DLWS_HAVE_PTHREAD_H=0 "
             "-DLWS_WITH_SPAWN=OFF -DLWS_WITH_HTTP3=OFF")


def _libwebsockets(version, git_ref, cmake_extra=""):
    return Recipe(
        family="libwebsockets",
        version=version,
        upstream="https://github.com/warmcat/libwebsockets",
        license="MIT",
        source=Source(git_url="https://github.com/warmcat/libwebsockets.git",
                      git_ref=git_ref),
        extra_sources={"openssl_archive": Source(
            url="https://github.com/openssl/openssl/releases/download/"
                "OpenSSL_1_1_1w/openssl-%s.tar.gz" % _OPENSSL_VERSION,
            sha256=_OPENSSL_SHA256)},
        build=[
            BuildStep(_STAGE_OPENSSL, env=_ENV),
            BuildStep(_CMAKE + cmake_extra),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="build-{arch}/bin/libwebsockets.dll",
                            component="libwebsockets.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        requires=["perl"],
        build_flags="-O3 (CMake Release), TLS via OpenSSL %s as a separate "
                    "DLL (not part of the artefact)" % _OPENSSL_VERSION,
        notes="OpenSSL is imported, not linked in. No-TLS (LWS_WITH_SSL=OFF) "
              "and mbedTLS builds are different code and are not covered.",
    )


RECIPES = {
    # Last 4.0.x.
    "libwebsockets_4.0.21": _libwebsockets("4.0.21", "v4.0.21"),
    # Last 4.3.x.
    "libwebsockets_4.3.10": _libwebsockets("4.3.10", "v4.3.10"),
    # Last 4.5.x, the current 4.x.
    "libwebsockets_4.5.8": _libwebsockets("4.5.8", "v4.5.8"),
    # Current 5.x.
    "libwebsockets_5.1.0": _libwebsockets("5.1.0", "v5.1.0", _CMAKE_V5),
}
