"""libgcrypt (GnuPG project) - draft docstring."""

from ..recipe import Artifact, BuildStep, Recipe, Source
from .libgpg_error import configure_options as _gpgerr_options
from .libgpg_error import _BASE as _GPGERR_URL
from .libgpg_error import _SHA256 as _GPGERR_SHA256

_BASE = "https://gnupg.org/ftp/gcrypt/libgcrypt/libgcrypt-%s.tar.bz2"

_SHA256 = {
    "1.8.14": "9608d222917e3747336993a24ef9e18bf5aa6b2d35c67a13219f9172b5b84a77",
    "1.10.4": "d6d2f835a79711ceba54b53d1081d388d24fb0341d79a268a6557e12908a90a0",
    "1.11.3": "2c6d562e894b2b06eefbc427d12d51ee9d3e50e90012ad6596b4cb3e421a95f2",
}
_SO = {"1.8.14": "20.2.15", "1.10.4": "20.4.4", "1.11.3": "20.6.1"}
# libgcrypt version -> the libgpg-error it is built against.
PAIRING = {"1.8.14": "1.35", "1.10.4": "1.61", "1.11.3": "1.61"}

# Subdirectories of the top-level Makefile.am minus doc and tests: neither
# contributes to the shared object.
_SUBDIRS = 'SUBDIRS="compat mpi cipher random src"'


def _recipe(version, linux):
    err = PAIRING[version]
    # The MinGW dependency is cross-built and needs the triple. The ELF one
    # is built natively (CC carries -m32 for the 32-bit leg), but libgcrypt
    # itself must be given the triple on both: mpi/config.links picks the
    # assembler modules from the host, and without --host a -m32 build on an
    # x86_64 machine selects the amd64 .S files, which gas rejects in 32-bit
    # mode ("`adcq' is only supported in 64-bit mode").
    host = "" if linux else "--host={host} "
    gcrypt_host = "--host={host} "
    # libgpg-error is built (not just fetched) beside libgcrypt, shared, so the
    # artefact imports it rather than containing it - libgpg-error is its own
    # family. gpgrt-config is found through PATH, which is how libgcrypt's
    # AM_PATH_GPG_ERROR looks for it when the prefix is not a system one.
    deps = ("tar xjf {gpg_error} && mkdir -p ge-{arch} && cd ge-{arch} && "
            "../libgpg-error-%s/configure %s--prefix=$PWD/inst %s && "
            "make -j$(nproc) && make -C src install") % (err, host, _gpgerr_options(err))
    configure = ("mkdir -p build-{arch} && cd build-{arch} && "
                 "PATH=$PWD/../ge-{arch}/inst/bin:$PATH "
                 "{source_root}/configure %s--disable-static --enable-shared "
                 "--disable-doc --with-libgpg-error-prefix=$PWD/../ge-{arch}/inst"
                 % gcrypt_host)
    if linux:
        artifact = Artifact(path="build-{arch}/src/.libs/libgcrypt.so.%s" % _SO[version],
                            component="libgcrypt.so")
        toolchains = ["linux_x86", "linux_x64"]
    else:
        artifact = Artifact(path="build-{arch}/src/.libs/libgcrypt-20.dll",
                            component="libgcrypt-20.dll")
        toolchains = ["mingw_x86", "mingw_x64"]
    return Recipe(
        family="libgcrypt",
        version=version,
        upstream="https://gnupg.org/software/libgcrypt/",
        license="LGPL-2.1-or-later (library), GPL-2.0-or-later (tests and tools)",
        source=Source(url=_BASE % version, sha256=_SHA256[version]),
        extra_sources={"gpg_error": Source(url=_GPGERR_URL % err,
                                           sha256=_GPGERR_SHA256[err])},
        build=[BuildStep(deps), BuildStep(configure),
               BuildStep("make -j$(nproc) " + _SUBDIRS, cwd="build-{arch}")],
        artifacts=[artifact],
        toolchains=toolchains,
        build_flags="-O2, shared, upstream configure defaults otherwise "
                    "(assembler modules, jitter entropy and hardware "
                    "acceleration on)",
        notes="",
    )


RECIPES = {}
for _v in _SHA256:
    RECIPES["libgcrypt_%s" % _v] = _recipe(_v, linux=False)
    RECIPES["libgcrypt_%s_linux" % _v] = _recipe(_v, linux=True)
