"""libgpg-error (Libgpg-error, GnuPG project) - error codes and the gpgrt runtime.

Draft docstring; replaced with the measured one once the artefacts exist.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_BASE = "https://gnupg.org/ftp/gcrypt/libgpg-error/libgpg-error-%s.tar.bz2"

# sha256 of release tarballs whose detached .sig verified with gpg (see the
# docstring); upstream publishes signatures, not checksum files.
_SHA256 = {
    "1.35": "cbd5ee62a8a8c88d48c158fff4fc9ead4132aacd1b4a56eb791f9f997d07e067",
    "1.61": "7a85413f2bc354f4f8aa832b718af122e48965e9e0eb9012ee659c13c6385c93",
}
# libtool file name of the ELF shared object: major 0, then AGE.REVISION.
_SO = {"1.35": "0.26.1", "1.61": "0.42.1"}

# One spelling of the options for this recipe and for the libgcrypt recipes,
# which build the same release as their dependency: the bytes in the two
# places are then the same bytes. NLS is off so the result does not depend on
# whether the host has gettext (this one does not). Switches a release does
# not know (--disable-tests and --disable-languages came after 1.35) are
# reported by configure as unrecognised and ignored.
_OPTIONS = ("--disable-static --enable-shared --disable-doc "
            "--disable-tests --disable-languages --disable-nls")


def configure_options(version):
    """The options for one release, shared with the libgcrypt recipes.

    1.35 predates GCC 10's -fno-common default and defines
    _gpgrt_functions_w32_pollable as a tentative definition in several
    translation units; the MinGW x64 link stops with "multiple definition".
    -fcommon restores the behaviour the release was written for, as a flag
    and not a source change. It is passed to every 1.35 build, ELF included,
    so the four artefacts of that release are compiled the same way.
    """
    if version == "1.35":
        return _OPTIONS + ' CFLAGS="{cflags} -fcommon"'
    return _OPTIONS


def _recipe(version, linux):
    if linux:
        configure = "mkdir -p build-{arch} && cd build-{arch} && " \
                    "{source_root}/configure " + configure_options(version)
        artifact = Artifact(path="build-{arch}/src/.libs/libgpg-error.so.%s"
                            % _SO[version], component="libgpg-error.so")
        toolchains = ["linux_x86", "linux_x64"]
    else:
        configure = "mkdir -p build-{arch} && cd build-{arch} && " \
                    "{source_root}/configure --host={host} " + configure_options(version)
        artifact = Artifact(path="build-{arch}/libgpg-error-0.dll",
                            component="libgpg-error-0.dll")
        toolchains = ["mingw_x86", "mingw_x64"]
    # Releases before 1.51 name the x64 DLL libgpg-error6-0.dll and the x86
    # one libgpg-error-0.dll; the copy gives both one name, so the two
    # architectures carry one component and the README row pairs them.
    extra = [] if linux else [BuildStep(
        "cp src/.libs/libgpg-error*-0.dll libgpg-error-0.dll", cwd="build-{arch}")]
    return Recipe(
        family="libgpg-error",
        version=version,
        upstream="https://gnupg.org/software/libgpg-error/",
        license="LGPL-2.1-or-later (library), GPL-1.0-or-later (tools)",
        source=Source(url=_BASE % version, sha256=_SHA256[version]),
        build=[BuildStep(configure),
               BuildStep("make -j$(nproc)", cwd="build-{arch}")] + extra,
        artifacts=[artifact],
        toolchains=toolchains,
        build_flags="-O2, shared, upstream configure defaults otherwise",
        notes="",
    )


RECIPES = {}
for _v in _SHA256:
    RECIPES["libgpg-error_%s" % _v] = _recipe(_v, linux=False)
    RECIPES["libgpg-error_%s_linux" % _v] = _recipe(_v, linux=True)
