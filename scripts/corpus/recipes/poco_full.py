"""POCO C++ Libraries 1.15.4, the components poco.py leaves out (MinGW).

poco.py builds every component that needs no external library and turns six
groups off; this recipe is the same tag, link shape and flags with those
groups on, filed as version 1.15.4-full beside the 1.15.4 image:

  * Crypto, NetSSL_OpenSSL and JWT, against OpenSSL 3.5.8 (the OpenSSL
    family's pinned release tarball, sha256
    a8f84a39918ec6415ce765d9b429d313ba97b8143169c172e734b9514464f5b2), built
    here as libcrypto/libssl DLLs exactly as openssl.py builds them and
    imported, so no OpenSSL body is in the image.
  * NetSSL_Win, the Schannel implementation of NetSSL (Windows only, off by
    default upstream).
  * Data/ODBC, against mingw-w64's odbc32 import library (the Windows ODBC
    driver manager; no client library to build).
  * FastLogger, with the quill and fmtquill copies Poco bundles for it.
  * PDF, with Poco's bundled libharu and the libpng/zlib copies under it.
  * SevenZip, with Poco's bundled 7-Zip LZMA SDK subset.

These are on knowing what poco.py says about them: the bundled libharu,
libpng, LZMA SDK and quill code is filed under this name because a Poco
binary with these components contains it, and libpng and 7-Zip are families
of their own here; the overlap is measured in the README row.

Not built here: Data/MySQL and Data/PostgreSQL, which need the MySQL/MariaDB
and libpq client libraries built for the target first (see the README "not
built" table), ApacheConnector (an Apache httpd module, needs APR and httpd
headers) and DNSSD (needs the Bonjour SDK or Avahi).

PDF compiles its own copy of zlib (PDF/src/zutil.c and the rest) beside the
one Foundation compiles, and two whole archives holding the same zlib objects
do not link ("multiple definition of `zError'; libPocoFoundation.a(zutil.c.obj)
... first defined here"). The link therefore passes
-Wl,--allow-multiple-definition, which keeps the first definition (Foundation's,
which comes first in the archive list) and drops the duplicate; that is a link
option, not a source change, and the dropped copy is the same zlib release.

Same command-line settings as poco.py (CMAKE_MC_COMPILER, CMAKE_SYSTEM_PROCESSOR,
RelWithDebInfo with Release's flags, -lmswsock); FindOpenSSL's MinGW branch
reads LIB_EAY and SSL_EAY, which are preset to the import libraries so that
it does not pick the static archives OpenSSL also leaves beside them.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_OPENSSL = Source(
    url="https://github.com/openssl/openssl/releases/download/openssl-3.5.8/"
        "openssl-3.5.8.tar.gz",
    sha256="a8f84a39918ec6415ce765d9b429d313ba97b8143169c172e734b9514464f5b2")

_SSL_ENV = {"CC": "gcc", "CXX": "g++", "AR": "ar", "RANLIB": "ranlib",
            "WINDRES": "windres", "CFLAGS": "", "CXXFLAGS": ""}

_CMAKE = (
    "cmake -S . -B build-{arch} "
    "-DCMAKE_SYSTEM_NAME=Windows -DCMAKE_SYSTEM_PROCESSOR={platform} "
    "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx}-posix "
    "-DCMAKE_FIND_ROOT_PATH=/usr/{host} "
    "-DCMAKE_MC_COMPILER={prefix}windmc -DCMAKE_RC_COMPILER={windres} "
    "-DCMAKE_BUILD_TYPE=RelWithDebInfo "
    "-DCMAKE_C_FLAGS_RELWITHDEBINFO='-O3 -DNDEBUG' "
    "-DCMAKE_CXX_FLAGS_RELWITHDEBINFO='-O3 -DNDEBUG' "
    "-DBUILD_SHARED_LIBS=OFF "
    "-DENABLE_TESTS=OFF -DENABLE_SAMPLES=OFF "
    "-DENABLE_CRYPTO=ON -DENABLE_NETSSL=ON -DENABLE_JWT=ON "
    "-DENABLE_NETSSL_WIN=ON -DENABLE_DATA_ODBC=ON "
    "-DENABLE_DATA_MYSQL=OFF -DENABLE_DATA_POSTGRESQL=OFF "
    "-DENABLE_APACHECONNECTOR=OFF "
    "-DENABLE_FASTLOGGER=ON -DENABLE_PDF=ON -DENABLE_SEVENZIP=ON "
    "-DOPENSSL_ROOT_DIR=$PWD/deps-{arch}/ssl "
    "-DOPENSSL_INCLUDE_DIR=$PWD/deps-{arch}/ssl/include "
    "-DOPENSSL_USE_STATIC_LIBS=OFF "
    "-DSSL_EAY=$PWD/deps-{arch}/ssl/libssl.dll.a "
    "-DLIB_EAY=$PWD/deps-{arch}/ssl/libcrypto.dll.a "
    "-DOPENSSL_SSL_LIBRARY=$PWD/deps-{arch}/ssl/libssl.dll.a "
    "-DOPENSSL_CRYPTO_LIBRARY=$PWD/deps-{arch}/ssl/libcrypto.dll.a")

_LINK = ("printf 'int anchor(){return 0;}\\n' > anchor.cc && "
         "{cxx}-posix -std=c++20 -O2 -shared -o poco.dll anchor.cc "
         "-Wl,--allow-multiple-definition "
         "-Wl,--whole-archive $(ls build-{arch}/lib/libPoco*.a | tr '\\n' ' ') "
         "-Wl,--no-whole-archive "
         "deps-{arch}/ssl/libssl.dll.a deps-{arch}/ssl/libcrypto.dll.a "
         "-lodbc32 -lsecur32 -lncrypt -lmswsock -lws2_32 -liphlpapi "
         "-ladvapi32 -lcrypt32 -lole32 -loleaut32 -luuid -lwinpthread "
         "-shared-libgcc")

RECIPES = {
    "poco_1.15.4-full": Recipe(
        family="poco",
        version="1.15.4-full",
        upstream="https://github.com/pocoproject/poco",
        license="BSL-1.0; bundled libharu (zlib/libpng licence), libpng, "
                "LZMA SDK (public domain), quill and fmt (MIT) carry their own",
        source=Source(git_url="https://github.com/pocoproject/poco.git",
                      git_ref="poco-1.15.4-release"),
        extra_sources={"ssl": _OPENSSL},
        build=[
            BuildStep("rm -rf deps-{arch}/ssl && mkdir -p deps-{arch}/ssl && "
                      "tar xf {ssl} -C deps-{arch}/ssl --strip-components=1"),
            BuildStep("./Configure {openssl_target} "
                      "--cross-compile-prefix={prefix} shared no-tests no-docs",
                      cwd="deps-{arch}/ssl", env=_SSL_ENV),
            BuildStep("make -j$(nproc) build_libs || make -j$(nproc) build_libs",
                      cwd="deps-{arch}/ssl", env=_SSL_ENV),
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
            BuildStep("ls build-{arch}/lib"),
            BuildStep(_LINK),
        ],
        artifacts=[Artifact(path="poco.dll", component="poco.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        requires=["perl"],
        build_flags="-O3 -DNDEBUG -std=c++20 (CMake RelWithDebInfo with its "
                    "flags overridden to Release's); static libraries linked "
                    "into one DLL with --whole-archive; Crypto, NetSSL, JWT, "
                    "NetSSL_Win, Data/ODBC, FastLogger, PDF and SevenZip on; "
                    "OpenSSL 3.5.8 and odbc32 imported; -Wl,--allow-multiple-"
                    "definition for the second bundled zlib copy (PDF's)",
        notes="poco 1.15.4 with the components poco_1.15.4 leaves out: Crypto, "
              "NetSSL_OpenSSL and JWT against OpenSSL 3.5.8 DLLs built from "
              "the pinned release tarball (imported, not in the image), "
              "NetSSL_Win (Schannel), Data/ODBC (odbc32), FastLogger with the "
              "bundled quill, PDF with the bundled libharu/libpng/zlib and "
              "SevenZip with the bundled LZMA SDK; that bundled code is in "
              "the image under this name, as in a Poco binary with these "
              "components. Data/MySQL, Data/PostgreSQL, ApacheConnector and "
              "DNSSD stay off. No upstream file is changed.",
    ),
}
