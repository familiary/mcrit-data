"""Shared dependency steps for the cryptominer recipes (XMRig, xmrig-proxy,
xmr-stak).

Not a recipe module: the registry skips names that start with an underscore.

Why the dependencies are built at all. XMRig's CMake does not carry libuv or
OpenSSL; it expects them from the system or from the `xmrig-deps` tree its
README points at. Both of them are families in this corpus already
(data/libuv, data/OpenSSL), so the miner is built against them as *shared*
libraries - an ELF `.so` or a MinGW `.dll` with an import library - and the
image that is disassembled holds the miner's own code and nothing of theirs.
Linked statically, which is what XMRig's own FindUV.cmake prefers (its
`find_library` list starts with `libuv.a`) and what the release binaries do,
about 540 `uv_*` functions and the whole of libcrypto would be filed under the
miner's name and duplicate those two families.

Both are pinned: libuv by tag, as data/libuv is, and OpenSSL by SHA-256, at the
versions data/libuv and data/OpenSSL already carry (1.52.1 and 3.5.8), so the
recorded provenance and the existing families describe the same source.
"""

from ..recipe import BuildStep, Source


LIBUV_TAG = "v1.52.1"
OPENSSL_VERSION = "3.5.8"
OPENSSL_SHA256 = "a8f84a39918ec6415ce765d9b429d313ba97b8143169c172e734b9514464f5b2"

EXTRA_SOURCES = {
    "uv": Source(git_url="https://github.com/libuv/libuv.git",
                 git_ref=LIBUV_TAG),
    "ssl": Source(
        url="https://github.com/openssl/openssl/releases/download/"
            "openssl-3.5.8/openssl-3.5.8.tar.gz",
        sha256=OPENSSL_SHA256),
}

OPENSSL_ONLY = {"ssl": EXTRA_SOURCES["ssl"]}

# OpenSSL's own parallel make has a dependency-file race that can lose a
# .d.tmp rename (see openssl.py); a second invocation completes cleanly.
_SSL_MAKE = ("make -j$(nproc) build_libs || make -j$(nproc) build_libs")


def _untar_openssl():
    return ("rm -rf deps-{arch}/ssl && mkdir -p deps-{arch}/ssl && "
            "tar xf {ssl} -C deps-{arch}/ssl --strip-components=1")


def linux_openssl():
    """OpenSSL as shared libcrypto.so/libssl.so, under deps-<arch>/ssl."""
    return [
        BuildStep(_untar_openssl()),
        # linux-x86 already carries -m32; no-tests and no-docs only trim what
        # is never linked.
        BuildStep("./Configure $([ {bitness} = 64 ] && echo linux-x86_64 || "
                  "echo linux-x86) shared no-tests no-docs",
                  cwd="deps-{arch}/ssl", env={"CFLAGS": "", "CXXFLAGS": ""}),
        BuildStep(_SSL_MAKE, cwd="deps-{arch}/ssl",
                  env={"CFLAGS": "", "CXXFLAGS": ""}),
    ]


def linux_libuv():
    """libuv as a shared libuv.so, under deps-<arch>/uv."""
    return [
        BuildStep("cmake -S {uv} -B deps-{arch}/uv -DCMAKE_BUILD_TYPE=Release "
                  "-DLIBUV_BUILD_TESTS=OFF -DLIBUV_BUILD_SHARED=ON "
                  "-DBUILD_SHARED_LIBS=ON",
                  env={"CFLAGS": "", "CXXFLAGS": ""}),
        BuildStep("cmake --build deps-{arch}/uv --target uv -j$(nproc)"),
    ]


def mingw_openssl():
    """OpenSSL as libcrypto/libssl DLLs plus their import libraries."""
    env = {"CC": "gcc", "CXX": "g++", "AR": "ar", "RANLIB": "ranlib",
           "WINDRES": "windres", "CFLAGS": "", "CXXFLAGS": ""}
    return [
        BuildStep(_untar_openssl()),
        # Same Configure line as openssl.py. --cross-compile-prefix prepends
        # the triple itself, so the tools are named bare.
        BuildStep("./Configure {openssl_target} --cross-compile-prefix={prefix} "
                  "shared no-tests no-docs", cwd="deps-{arch}/ssl", env=env),
        BuildStep(_SSL_MAKE, cwd="deps-{arch}/ssl", env=env),
    ]


def mingw_libuv():
    """libuv as libuv.dll with its import library, under deps-<arch>/uv."""
    return [
        BuildStep("cmake -S {uv} -B deps-{arch}/uv -DCMAKE_SYSTEM_NAME=Windows "
                  "-DCMAKE_C_COMPILER={cc} -DCMAKE_RC_COMPILER={windres} "
                  "-DCMAKE_FIND_ROOT_PATH=/usr/{host} "
                  "-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON "
                  "-DLIBUV_BUILD_TESTS=OFF -DLIBUV_BUILD_SHARED=ON",
                  env={"CFLAGS": "", "CXXFLAGS": ""}),
        BuildStep("cmake --build deps-{arch}/uv --target uv -j$(nproc)"),
    ]


# The two -D options a build that links these needs, in the spelling of
# FindOpenSSL and of XMRig's FindUV. Spelled as absolute paths because the
# build tree is a sibling of deps-<arch>, and because XMRig's FindUV would
# otherwise find the system libuv.a first.
def linux_dep_options(uv=True):
    ssl = ("-DOPENSSL_ROOT_DIR=$PWD/deps-{arch}/ssl "
           "-DOPENSSL_INCLUDE_DIR=$PWD/deps-{arch}/ssl/include "
           "-DOPENSSL_SSL_LIBRARY=$PWD/deps-{arch}/ssl/libssl.so "
           "-DOPENSSL_CRYPTO_LIBRARY=$PWD/deps-{arch}/ssl/libcrypto.so")
    libuv = ("-DUV_INCLUDE_DIR={uv}/include "
             "-DUV_LIBRARY=$PWD/deps-{arch}/uv/libuv.so")
    return ssl + (" " + libuv if uv else "")


def mingw_dep_options(uv=True):
    ssl = ("-DOPENSSL_ROOT_DIR=$PWD/deps-{arch}/ssl "
           "-DOPENSSL_INCLUDE_DIR=$PWD/deps-{arch}/ssl/include "
           "-DOPENSSL_SSL_LIBRARY=$PWD/deps-{arch}/ssl/libssl.dll.a "
           "-DOPENSSL_CRYPTO_LIBRARY=$PWD/deps-{arch}/ssl/libcrypto.dll.a")
    libuv = ("-DUV_INCLUDE_DIR={uv}/include "
             "-DUV_LIBRARY=$PWD/deps-{arch}/uv/libuv.dll.a")
    return ssl + (" " + libuv if uv else "")


# ---------------------------------------------------------------------------
# MSVC. cmd.exe steps, run in a Visual Studio developer environment.

_MSVC_UNTAR = (
    'python -c "'
    "import sys,tarfile;t=tarfile.open(sys.argv[1]);"
    "m=[x for x in t.getmembers() if '/' in x.name];"
    "[setattr(x,'name',x.name.split('/',1)[1]) for x in m];"
    "t.extractall(sys.argv[2],members=m)"
    '" "{ssl}" deps-{arch}\\ssl')

# Restated in full for the reason openssl_msvc.py gives: LDFLAGS replaces the
# target's own "/nologo /debug" rather than adding to it.
_MSVC_SSL_LDFLAGS = ('"LDFLAGS=/nologo /debug /Brepro /INCREMENTAL:NO '
                     '/OPT:NOREF /OPT:NOICF"')
_MSVC_SSL_CONFIGURE = "shared no-tests no-asm no-makedepend " + _MSVC_SSL_LDFLAGS


def msvc_openssl():
    """OpenSSL's DLLs and import libraries, built no-asm as openssl_msvc.py
    does, under deps-<arch>\\ssl. Only the import libraries are linked."""
    return [
        BuildStep(_MSVC_UNTAR),
        BuildStep('if "{arch}"=="x64" perl Configure VC-WIN64A '
                  + _MSVC_SSL_CONFIGURE, cwd="deps-{arch}/ssl"),
        BuildStep('if "{arch}"=="x86" perl Configure VC-WIN32 '
                  + _MSVC_SSL_CONFIGURE, cwd="deps-{arch}/ssl"),
        BuildStep("nmake build_libs", cwd="deps-{arch}/ssl"),
    ]


def msvc_libuv():
    """libuv as uv.dll and its import library uv.lib, under deps-<arch>\\uv."""
    return [
        BuildStep('cmake -S {uv} -B deps-{arch}\\uv -G "NMake Makefiles" '
                  "-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON "
                  "-DLIBUV_BUILD_SHARED=ON -DLIBUV_BUILD_TESTS=OFF"),
        BuildStep("cmake --build deps-{arch}\\uv --target uv"),
    ]


def msvc_dep_options(uv=True):
    """FindOpenSSL's MSVC branch reads LIB_EAY_RELEASE and SSL_EAY_RELEASE
    rather than OPENSSL_SSL_LIBRARY, and XMRig forces it into static-library
    naming (OPENSSL_USE_STATIC_LIBS), which would look for libcrypto_static.lib
    - the static archive, not the import library. Presetting the two cache
    entries makes find_library return at once."""
    ssl = ("-DOPENSSL_INCLUDE_DIR=%CD%/deps-{arch}/ssl/include "
           "-DLIB_EAY_RELEASE=%CD%/deps-{arch}/ssl/libcrypto.lib "
           "-DSSL_EAY_RELEASE=%CD%/deps-{arch}/ssl/libssl.lib")
    libuv = ("-DUV_INCLUDE_DIR={uv}/include "
             "-DUV_LIBRARY=%CD%/deps-{arch}/uv/uv.lib")
    return ssl + (" " + libuv if uv else "")


# What every MSVC link in this corpus carries (see libuv_msvc.py for why each).
MSVC_LINK = "/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"
