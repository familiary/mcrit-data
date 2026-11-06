"""Nettle - the GNU low-level cryptographic library, MinGW and Linux ELF.

DRAFT docstring; the measured part is filled in after the builds.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_UPSTREAM = "https://git.lysator.liu.se/nettle/nettle"
_LICENSE = ("LGPL-3.0-or-later OR GPL-2.0-or-later (dual: LGPLv3+ or GPLv2+, "
            "licensee's choice; 2.7.1 and 3.4.1 are LGPL-2.1-or-later and "
            "GPL-2.0-or-later)")

# Upstream's own configure, out of tree, one build directory per architecture.
_COMMON = ("--enable-shared --disable-static --disable-documentation "
           "--disable-openssl")
_CONFIGURE_PE = ("mkdir -p build-{arch} && cd build-{arch} && "
                 "{source_root}/configure --host={host} " + _COMMON)
_CONFIGURE_ELF = ("mkdir -p build-{arch} && cd build-{arch} && "
                  "{source_root}/configure " + _COMMON)
# SUBDIRS= keeps make to the libraries: tools, testsuite and examples are
# programs this corpus does not use, and the testsuite is most of the time.
_MAKE = "make -j$(nproc) SUBDIRS="

# version -> (sha256, libnettle PE, libnettle ELF, libhogweed PE, libhogweed ELF)
# The file names are what upstream's configure.ac gives the shared libraries
# (LIBNETTLE_MAJOR/MINOR, LIBHOGWEED_MAJOR/MINOR); 2.7.1 puts the minor in the
# Windows name too, and has no mini-gmp option, so no hogweed here.
_VERSIONS = {
    "2.7.1": ("bc71ebd43435537d767799e414fce88e521b7278d48c860651216e1fc6555b40",
              "libnettle-4-7.dll", "libnettle.so.4.7", None, None),
    "3.4.1": ("f941cf1535cd5d1819be5ccae5babef01f6db611f9b5a777bae9c7604b8a92ad",
              "libnettle-6.dll", "libnettle.so.6.5",
              "libhogweed-4.dll", "libhogweed.so.4.5"),
    "3.7.3": ("661f5eb03f048a3b924c3a8ad2515d4068e40f67e774e8a26827658007e3bcf0",
              "libnettle-8.dll", "libnettle.so.8.4",
              "libhogweed-6.dll", "libhogweed.so.6.4"),
    "3.9.1": ("ccfeff981b0ca71bbd6fbcb054f407c60ffb644389a5be80d6716d5b550c6ce3",
              "libnettle-8.dll", "libnettle.so.8.8",
              "libhogweed-6.dll", "libhogweed.so.6.8"),
    "3.10.2": ("fe9ff51cb1f2abb5e65a6b8c10a92da0ab5ab6eaf26e7fc2b675c45f1fb519b5",
               "libnettle-8.dll", "libnettle.so.8.11",
               "libhogweed-6.dll", "libhogweed.so.6.11"),
    "4.0": ("3addbc00da01846b232fb3bc453538ea5468da43033f21bb345cb1e9073f5094",
            "libnettle-9.dll", "libnettle.so.9.0",
            "libhogweed-7.dll", "libhogweed.so.7.0"),
}


def _recipe(version, linux):
    sha256, pe_nettle, elf_nettle, pe_hogweed, elf_hogweed = _VERSIONS[version]
    hogweed = pe_hogweed is not None
    option = " --enable-mini-gmp" if hogweed else " --disable-public-key"
    configure = (_CONFIGURE_ELF if linux else _CONFIGURE_PE) + option
    # make leaves the shared object as libnettle.so; the versioned names are
    # symlinks that only `make install` creates.
    artifacts = [Artifact(path="build-{arch}/" + ("libnettle.so" if linux else pe_nettle),
                          component="libnettle.so" if linux else "libnettle.dll")]
    if hogweed:
        artifacts.append(Artifact(
            path="build-{arch}/" + ("libhogweed.so" if linux else pe_hogweed),
            component="libhogweed.so" if linux else "libhogweed.dll"))
    return Recipe(
        family="Nettle",
        version=version,
        upstream=_UPSTREAM,
        license=_LICENSE,
        source=Source(url="https://ftp.gnu.org/gnu/nettle/nettle-%s.tar.gz" % version,
                      sha256=sha256),
        build=[BuildStep(configure),
               BuildStep(_MAKE, cwd="build-{arch}")],
        artifacts=artifacts,
        toolchains=["linux_x86", "linux_x64"] if linux else ["mingw_x86", "mingw_x64"],
        build_flags="-O2 -ggdb3 (upstream's own flags over the toolchain's -O2), "
                    "upstream default assembler" + (", fat build on x86_64"
                                                    if version >= "3.7" else ""),
        notes="",
    )


RECIPES = {}
for _version in _VERSIONS:
    RECIPES["Nettle_%s" % _version] = _recipe(_version, linux=False)
    RECIPES["Nettle_%s_linux" % _version] = _recipe(_version, linux=True)
