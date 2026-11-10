"""Shared-library build dependencies for the Linux ELF recipes (tcpdump, OpenSSH).

Both projects link libraries this tooling does not want inside their image
(libpcap, OpenSSL's libcrypto, zlib), so each is built once per architecture
from its pinned tarball into a private prefix and linked dynamically, the way
a distribution package is: NEEDED, not linked in, so none of their bodies are
filed under the host project's name. Building a private copy also removes the
host as a variable: the 32-bit half has no -dev packages on a 64-bit machine,
and the versions below are the ones the recipes record.

The prefixes are cached under $MCRIT_DATA_WORK_DIR/deps/<name>-<arch> (the
repository's build/ directory when unset), keyed by the pinned name and
version, so the eight tcpdump and the OpenSSH recipes do not each rebuild
OpenSSL. The cache holds only the output of a pinned source built by the
commands below; an interrupted build leaves no ``.done`` marker and is
redone. This module starts with an underscore so the recipe registry skips it.
"""

from ..recipe import Source

# Pinned dependency tarballs. OpenSSL 1.0.2u and 1.1.1w are the last releases
# of their lines; 3.0.15 is the 3.0 point release data/OpenSSL carries.
ZLIB = Source(
    url="https://zlib.net/fossils/zlib-1.3.1.tar.gz",
    sha256="9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23")

# crypt(3). glibc 2.39 does not provide it (libxcrypt does, as -lcrypt), and a
# 64-bit host has no 32-bit libcrypt-dev, so sshd's password check cannot link
# for x86 without it. Built for both architectures so they are the same code.
XCRYPT = Source(
    url="https://github.com/besser82/libxcrypt/releases/download/v4.4.38/"
        "libxcrypt-4.4.38.tar.xz",
    sha256="80304b9c306ea799327f01d9a7549bdb28317789182631f1b54f4511b4206dd6")

OPENSSL = {
    "1.0.2u": Source(
        url="https://www.openssl.org/source/old/1.0.2/openssl-1.0.2u.tar.gz",
        sha256="ecd0c6ffb493dd06707d38b14bb4d8c2288bb7033735606569d8f90f89669d16"),
    "1.1.1w": Source(
        url="https://github.com/openssl/openssl/releases/download/OpenSSL_1_1_1w/"
            "openssl-1.1.1w.tar.gz",
        sha256="cf3098950cb4d853ad95c0841f1f9c6d3dc102dccfcacd521d93925208b76ac8"),
    "3.0.15": Source(
        url="https://github.com/openssl/openssl/releases/download/openssl-3.0.15/"
            "openssl-3.0.15.tar.gz",
        sha256="23c666d0edf20f14249b3d8f0368acaee9ab585b09e1de82107c66e1f3ec9533"),
}

LIBPCAP = Source(
    url="https://www.tcpdump.org/release/libpcap-1.10.5.tar.gz",
    sha256="37ced90a19a302a7f32e458224a00c365c117905c2cd35ac544b6880a81488f0")

_DEPS = "${MCRIT_DATA_WORK_DIR:-{repo}/build}/deps"


def prefix(name):
    """Shell expression for the cached install prefix of ``name`` (per arch)."""
    return '"%s/%s-{arch}"' % (_DEPS, name)


def _cached(name, body):
    """Run ``body`` in a scratch directory unless the prefix is already built.

    ``body`` sees $P (the prefix) and is entered inside the unpacked scratch
    directory; the scratch directory is removed afterwards.
    """
    return (
        'P=%s && T="$P.tmp" && '
        '{ [ -f "$P/.done" ] || { rm -rf "$P" "$T" && mkdir -p "$P" "$T" && '
        'cd "$T" && %s && cd / && rm -rf "$T" && touch "$P/.done"; }; }'
        % (prefix(name), body))


def zlib_step():
    return _cached(
        "zlib-1.3.1",
        'tar xzf {zlib_src} && cd zlib-1.3.1 && '
        './configure --prefix="$P" && make -j$(nproc) && make install')


def openssl_step(version):
    """OpenSSL ``version``'s libraries and headers, shared, no apps installed.

    The three generations are configured differently. 1.0.2u has the
    ``linux-x86_64`` / ``linux-elf`` targets and no install_dev, so it is
    configured with ``make depend`` first and installed with install_sw;
    1.1.1w and 3.0.15 use ``linux-x86_64`` / ``linux-x86`` and install_dev. OpenSSL's parallel make has a
    dependency-file race that can lose a .d.tmp rename, so a failed -j run is
    repeated once and then run serially.
    """
    src = "{openssl_src}"
    make_libs = ('(make -j$(nproc) build_libs || make -j$(nproc) build_libs '
                 '|| make build_libs)')
    if version.startswith("1.0.2"):
        target = ('$([ {bitness} = 64 ] && echo linux-x86_64 || echo linux-elf)')
        # install_sw copies the openssl program, so the applications are built
        # too (plain make, not build_libs).
        body = ('tar xzf %s && cd openssl-%s && ./Configure %s shared '
                '--prefix="$P" --openssldir="$P/ssl" && make depend && '
                '(make -j$(nproc) || make) && make install_sw'
                % (src, version, target))
    else:
        target = ('$([ {bitness} = 64 ] && echo linux-x86_64 || echo linux-x86)')
        body = ('tar xzf %s && cd openssl-%s && ./Configure %s shared no-tests '
                '--prefix="$P" --libdir=lib && %s && make install_dev'
                % (src, version, target, make_libs))
    return _cached("openssl-%s" % version, body)


def libpcap_step():
    """libpcap 1.10.5, shared, default PF_PACKET backend, optional backends off."""
    return _cached(
        "libpcap-1.10.5",
        'tar xzf {libpcap_src} && mkdir build && cd build && '
        '../libpcap-1.10.5/configure --prefix="$P" --libdir="$P/lib" '
        '--disable-dbus --disable-bluetooth --disable-rdma --disable-netmap '
        '--disable-usb --without-libnl && make -j$(nproc) && make install')


def xcrypt_step():
    return _cached(
        "libxcrypt-4.4.38",
        'tar xf {xcrypt_src} && cd libxcrypt-4.4.38 && '
        './configure --prefix="$P" && make -j$(nproc) && make install')


# ---------------------------------------------------------------------------
# Static archives for the musl axis.
#
# The same pinned zlib and OpenSSL as above, built as .a files with the musl
# toolchain's own compiler (CC, AR and RANLIB come from its environment) into
# prefixes of their own, so a glibc prefix of the same name is never reused. A
# static musl ELF cannot load a shared library, which is why the glibc legs'
# dynamic linking is not available: the recipes that use these archives find
# zlib and libcrypto inside their image and remove them by name
# (Recipe.exclude_functions), see openssh.py.

def zlib_musl_step():
    return _cached(
        "zlib-1.3.1-musl",
        'tar xzf {zlib_src} && cd zlib-1.3.1 && '
        './configure --prefix="$P" --static && make -j$(nproc) && make install')


def openssl_musl_step(version):
    """OpenSSL ``version`` as static libcrypto.a / libssl.a, no applications.

    ``no-shared`` and build_libs, so only the libraries are
    built and installed (install_dev). Configure's own linux-x86_64 /
    linux-x86 target; for linux-x86 it adds -m32, which the i686 musl
    compiler accepts. The musl libc has no getcontext, so the asynchronous
    job code is left out with ``no-async``.
    """
    src = "{openssl_src}"
    target = ('$([ {bitness} = 64 ] && echo linux-x86_64 || echo linux-x86)')
    make_libs = ('(make -j$(nproc) build_libs || make -j$(nproc) build_libs '
                 '|| make build_libs)')
    body = ('tar xzf %s && cd openssl-%s && ./Configure %s no-shared '
            'no-tests no-async --prefix="$P" --libdir=lib && %s && '
            'make install_dev' % (src, version, target, make_libs))
    return _cached("openssl-%s-musl" % version, body)


MUSL_PIN_TEXT = (
    "Toolchains from musl.cc, pinned: x64 "
    "https://musl.cc/x86_64-linux-musl-native.tgz sha256 "
    "eb1db6f0f3c2bdbdbfb993d7ef7e2eeef82ac1259f6a6e1757c33a97dbcef3ad, x86 "
    "https://musl.cc/i686-linux-musl-cross.tgz sha256 "
    "93bd5504d5d0349258c43d7a668b506acbd627d31c0843a96e4b4c47b27a0180 "
    "(GCC 11.2.1 20211120, musl 1.2.2-git-50-gb76f37fd)."
)
