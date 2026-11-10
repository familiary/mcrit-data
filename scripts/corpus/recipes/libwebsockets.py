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

Variants of the same four tags, each its own version string so the images
sit beside the OpenSSL ones without replacing them:

- -nossl: LWS_WITH_SSL=OFF, no TLS library at all, otherwise the same
  switches. Distinct 10+ instruction PicHashes shared with the OpenSSL
  MinGW image of the same version and architecture, as a share of the
  -nossl image's own: 4.0.21 x86 217/428 (51%), x64 199/406 (49%); 4.3.10
  305/538 (57%), 282/513 (55%); 4.5.8 465/747 (62%), 443/719 (62%); 5.1.0
  839/1312 (64%), 805/1267 (64%).
- -mbedtls: LWS_WITH_MBEDTLS=ON against an mbedTLS release tarball pinned by
  digest, the same tags data/mbedTLS is built from. lws's own sources decide
  which: 4.0.21's lib/tls/mbedtls has no MBEDTLS_VERSION_NUMBER >= 0x03000000
  branch, so it only speaks the 2.x API and gets 2.28.10; 4.3.10, 4.5.8 and
  5.1.0 carry the 3.x branches (5.1.0 a 4.x one as well, which needs the
  separate TF-PSA-Crypto library) and get the 3.6 LTS, 3.6.7. mbedTLS is
  built by the recipe as its own shared libmbedtls, libmbedx509 and
  libmbedcrypto DLLs outside the lws tree and linked through their import
  libraries, so the only mbedtls_* functions in these images are the
  one-instruction import thunks (141 on 4.5.8 x64); the SSL_* functions
  that remain are lws's own OpenSSL-compatibility wrapper in
  lib/tls/mbedtls/wrapper, which is lws code. Shared with the OpenSSL MinGW
  image, as above: 4.0.21 x86 400/534 (75%), x64 378/507 (75%); 4.3.10
  339/658 (52%), 317/628 (50%); 4.5.8 487/905 (54%), 465/871 (53%); 5.1.0
  1055/1490 (71%), 1013/1439 (70%).

The ELF build of the same tags and OpenSSL backend is libwebsockets_linux.py.
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


# The same configure line without a TLS library: everything _CMAKE says
# except the OpenSSL paths, which are what changes between the variants.
_CMAKE_BASE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
               "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx} "
               "-DCMAKE_RC_COMPILER={windres} -DCMAKE_FIND_ROOT_PATH=/usr/{host} "
               "-DCMAKE_BUILD_TYPE=Release "
               "-DLWS_WITH_SHARED=ON -DLWS_WITH_STATIC=OFF "
               "-DLWS_WITHOUT_TESTAPPS=ON -DLWS_WITH_MINIMAL_EXAMPLES=OFF "
               "-DLWS_WITH_PLUGINS=OFF -DDISABLE_WERROR=ON ")

_CMAKE_NOSSL = (_CMAKE_BASE + "\"-DCMAKE_C_FLAGS=-Wno-error\" "
                "-DLWS_WITH_SSL=OFF")

# mbedTLS releases, the same tags data/mbedTLS is built from
# (recipes/mbedtls.py), as release tarballs pinned by digest. 4.0.21 only
# knows the 2.x API (no MBEDTLS_VERSION_NUMBER >= 0x03000000 branch anywhere
# in lib/tls/mbedtls), so it gets 2.28.10; 4.3.10, 4.5.8 and 5.1.0 carry the
# 3.x branches (and 5.1.0 a 4.x one as well), so they get the 3.6 LTS.
_MBEDTLS = {
    "2.28.10": "19e5b81fdac0fe22009b9e2bdcd52d7dcafbf62bc67fc59cf0a76b5b5540d149",
    "3.6.7": "a7e8bcbec0e6f761b4af24f25677626b35f762f68eef79c08677a363212d11f6",
}

_MBED = "{out}/lws-mbedtls-{arch}"

_STAGE_MBEDTLS = (
    "rm -rf " + _MBED + " && mkdir -p " + _MBED + " && "
    "tar xf {mbedtls_archive} -C " + _MBED + " --strip-components=1 && "
    "cmake -S " + _MBED + " -B " + _MBED + "/build -DCMAKE_SYSTEM_NAME=Windows "
    "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx} "
    "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
    "-DUSE_SHARED_MBEDTLS_LIBRARY=ON -DUSE_STATIC_MBEDTLS_LIBRARY=OFF "
    "-DENABLE_TESTING=OFF -DENABLE_PROGRAMS=OFF -DMBEDTLS_FATAL_WARNINGS=OFF && "
    "cmake --build " + _MBED + "/build -j$(nproc)")

_MBED_LIBS = ";".join(_MBED + "/build/library/lib%s.dll.a" % n
                      for n in ("mbedtls", "mbedx509", "mbedcrypto"))

_CMAKE_MBEDTLS = (_CMAKE_BASE +
                  "\"-DCMAKE_C_FLAGS=-I" + _MBED + "/include -Wno-error\" "
                  "-DLWS_WITH_SSL=ON -DLWS_WITH_MBEDTLS=ON "
                  "-DLWS_MBEDTLS_INCLUDE_DIRS=" + _MBED + "/include "
                  "\"-DLWS_MBEDTLS_LIBRARIES=" + _MBED_LIBS + "\"")


def _openssl_source():
    return Source(
        url="https://github.com/openssl/openssl/releases/download/"
            "OpenSSL_1_1_1w/openssl-%s.tar.gz" % _OPENSSL_VERSION,
        sha256=_OPENSSL_SHA256)


def _libwebsockets(version, git_ref, cmake_extra=""):
    return Recipe(
        family="libwebsockets",
        version=version,
        upstream="https://github.com/warmcat/libwebsockets",
        license="MIT",
        source=Source(git_url="https://github.com/warmcat/libwebsockets.git",
                      git_ref=git_ref),
        extra_sources={"openssl_archive": _openssl_source()},
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
        notes="OpenSSL is imported, not linked in. The no-TLS and mbedTLS "
              "builds of the same tag are separate artefacts of this family "
              "(versions -nossl and -mbedtls).",
    )


def _libwebsockets_nossl(version, git_ref, cmake_extra=""):
    return Recipe(
        family="libwebsockets",
        version=version + "-nossl",
        upstream="https://github.com/warmcat/libwebsockets",
        license="MIT",
        source=Source(git_url="https://github.com/warmcat/libwebsockets.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE_NOSSL + cmake_extra),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="build-{arch}/bin/libwebsockets.dll",
                            component="libwebsockets.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (CMake Release), LWS_WITH_SSL=OFF (no TLS library)",
        notes="Same tag and switches as the OpenSSL build of %s, with "
              "LWS_WITH_SSL=OFF: no TLS backend at all." % version,
    )


def _libwebsockets_mbedtls(version, git_ref, mbedtls, cmake_extra=""):
    return Recipe(
        family="libwebsockets",
        version=version + "-mbedtls",
        upstream="https://github.com/warmcat/libwebsockets",
        license="MIT",
        source=Source(git_url="https://github.com/warmcat/libwebsockets.git",
                      git_ref=git_ref),
        extra_sources={"mbedtls_archive": Source(
            url="https://github.com/Mbed-TLS/mbedtls/releases/download/"
                "mbedtls-%s/mbedtls-%s.tar.bz2" % (mbedtls, mbedtls),
            sha256=_MBEDTLS[mbedtls])},
        build=[
            BuildStep(_STAGE_MBEDTLS),
            BuildStep(_CMAKE_MBEDTLS + cmake_extra),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="build-{arch}/bin/libwebsockets.dll",
                            component="libwebsockets.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (CMake Release), LWS_WITH_MBEDTLS=ON, TLS via "
                    "mbedTLS %s as separate DLLs (libmbedtls, libmbedx509, "
                    "libmbedcrypto; not part of the artefact)" % mbedtls,
        notes="mbedTLS %s is imported, not linked in: none of its code is in "
              "this image (see data/mbedTLS for it)." % mbedtls,
    )


_TAGS = [
    # Last 4.0.x, last 4.3.x, last 4.5.x (the current 4.x), current 5.x.
    ("4.0.21", "v4.0.21", "", "2.28.10"),
    ("4.3.10", "v4.3.10", "", "3.6.7"),
    ("4.5.8", "v4.5.8", "", "3.6.7"),
    ("5.1.0", "v5.1.0", _CMAKE_V5, "3.6.7"),
]

RECIPES = {}
for _v, _tag, _extra, _mbed in _TAGS:
    RECIPES["libwebsockets_%s" % _v] = _libwebsockets(_v, _tag, _extra)
    RECIPES["libwebsockets_%s_nossl" % _v] = _libwebsockets_nossl(
        _v, _tag, _extra)
    RECIPES["libwebsockets_%s_mbedtls" % _v] = _libwebsockets_mbedtls(
        _v, _tag, _mbed, _extra)
