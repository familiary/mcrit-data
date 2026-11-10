"""libwebsockets, built for Linux and ELF.

The ELF counterpart of libwebsockets.py: the same four tags, the same
OpenSSL 1.1.1w archive (pinned by the same digest) as the TLS backend, and
the same CMake switches as far as they apply to Linux. OpenSSL is built as
shared libssl.so/libcrypto.so outside the source tree (lws refuses an include
directory inside its own tree) and libwebsockets.so is linked against them
dynamically, so none of OpenSSL's code is in these artefacts. lws compiles
itself with -fvisibility=hidden when the compiler supports it, so the image
exports only the LWS_VISIBLE API.

The include and library directories go in through CMAKE_C_FLAGS as well as
OPENSSL_*, for the reason libwebsockets.py gives: lws probes the OpenSSL API
with check_c_source_compiles, which sees CMAKE_C_FLAGS only. {archflag}
(-m32/-m64) goes in the same way, and to OpenSSL's Configure, because the
32-bit half comes out of the same gcc driver. 5.x gets LWS_WITH_HTTP3=OFF,
which would otherwise demand GnuTLS; the Windows-only 5.x switches of the
MinGW recipe are not needed here. pkg-config is given an empty search path
for the configure step so lws cannot pick up the host's own OpenSSL (see
_NO_PKGCONFIG); readelf -d of every image lists libssl.so.1.1 and
libcrypto.so.1.1, the pinned build, as the only TLS libraries it needs.

A portable library built for a platform it is used on, not evidence that the
sample that prompted the family is an ELF.

Counts, kept + removed = total (the removed ones are _init and the
tm_clones/__do_global_dtors_aux/frame_dummy start files): 4.0.21 x86
1346 + 9 = 1355, x64 1333 + 5 = 1338; 4.3.10 x86 1677 + 9 = 1686, x64 1664 +
5 = 1669; 4.5.8 x86 2458 + 11 = 2469, x64 2439 + 5 = 2444; 5.1.0 x86 3845 +
11 = 3856, x64 3811 + 5 = 3816. About half of each image is unnamed .plt and
.plt.sec stubs of two or three instructions (1329 of 2439 on 4.5.8 x64):
lws's exported functions have default visibility, so its own calls to them
go through the PLT as well as the calls into libc and OpenSSL; none of them
reaches ten instructions. Distinct 10+ instruction PicHashes shared with the
OpenSSL MinGW image of the same version, as a share of the ELF image's own:
x64 0 of 473, 602, 842 and 1525 (4.0.21, 4.3.10, 4.5.8, 5.1.0); x86 34/527
(6%), 35/675 (5%), 61/945 (6%) and 101/1673 (6%), so the ELF images are
references of their own.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from .libwebsockets import _OPENSSL_SHA256, _OPENSSL_VERSION


_SSL = "{out}/lws-openssl-linux-{arch}"

_STAGE_OPENSSL = (
    "rm -rf " + _SSL + " && mkdir -p " + _SSL + " && "
    "tar xf {openssl_archive} -C " + _SSL + " --strip-components=1 && "
    "cd " + _SSL + " && "
    "./Configure $([ {bitness} = 64 ] && echo linux-x86_64 || echo linux-x86) "
    "{archflag} shared no-tests && "
    # OpenSSL's parallel make has a dependency-file race; a second
    # invocation completes cleanly.
    "(make -j$(nproc) build_libs || make -j$(nproc) build_libs)")

_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_BUILD_TYPE=Release "
          "\"-DCMAKE_C_FLAGS={archflag} -I" + _SSL + "/include -L" + _SSL + " "
          "-Wno-error\" "
          "-DLWS_WITH_SHARED=ON -DLWS_WITH_STATIC=OFF -DLWS_WITH_SSL=ON "
          "-DLWS_WITHOUT_TESTAPPS=ON -DLWS_WITH_MINIMAL_EXAMPLES=OFF "
          "-DLWS_WITH_PLUGINS=OFF -DDISABLE_WERROR=ON "
          "-DOPENSSL_ROOT_DIR=" + _SSL + " "
          "-DOPENSSL_INCLUDE_DIR=" + _SSL + "/include "
          "-DOPENSSL_SSL_LIBRARY=" + _SSL + "/libssl.so "
          "-DOPENSSL_CRYPTO_LIBRARY=" + _SSL + "/libcrypto.so")

_CMAKE_V5 = " -DLWS_WITH_HTTP3=OFF"

# lib/tls/CMakeLists.txt of 4.3.x and later asks pkg-config for "openssl"
# and appends whatever it returns to OPENSSL_LIBRARIES. On this host that is
# the system's own 64-bit libssl/libcrypto: the 32-bit configure probes then
# fail to link ("/usr/lib/x86_64-linux-gnu/libssl.so: error adding symbols:
# file in wrong format"), HMAC_CTX_new reads as absent and 4.3.10 stops at
# "field 'ctx' has incomplete type" in lws-genhash.h, and the 64-bit build
# would link the system library beside the pinned one. An empty pkg-config
# search path leaves only the OPENSSL_* paths given above.
_NO_PKGCONFIG = {"PKG_CONFIG_LIBDIR": "/nonexistent", "PKG_CONFIG_PATH": ""}


def _libwebsockets_linux(version, git_ref, cmake_extra=""):
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
            BuildStep(_STAGE_OPENSSL),
            BuildStep(_CMAKE + cmake_extra, env=_NO_PKGCONFIG),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="build-{arch}/lib/libwebsockets.so",
                            component="libwebsockets.so")],
        toolchains=["linux_x86", "linux_x64"],
        requires=["perl"],
        build_flags="-O3 -fvisibility=hidden (CMake Release, lws's own "
                    "visibility flag), TLS via OpenSSL %s as separate shared "
                    "objects (not part of the artefact)" % _OPENSSL_VERSION,
        notes="ELF build of the same tag and OpenSSL backend as the MinGW "
              "artefacts; libssl/libcrypto are linked dynamically.",
    )


RECIPES = {
    "libwebsockets_4.0.21_linux": _libwebsockets_linux("4.0.21", "v4.0.21"),
    "libwebsockets_4.3.10_linux": _libwebsockets_linux("4.3.10", "v4.3.10"),
    "libwebsockets_4.5.8_linux": _libwebsockets_linux("4.5.8", "v4.5.8"),
    "libwebsockets_5.1.0_linux": _libwebsockets_linux("5.1.0", "v5.1.0",
                                                      _CMAKE_V5),
}
