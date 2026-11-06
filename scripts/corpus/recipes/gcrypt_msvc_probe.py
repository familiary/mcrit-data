"""Scratch probe, never merged: reports what cl does with the GnuPG tarballs."""
from ..recipe import Artifact, BuildStep, Recipe, Source

_GE = Source(url="https://gnupg.org/ftp/gcrypt/libgpg-error/libgpg-error-1.61.tar.bz2",
             sha256="7a85413f2bc354f4f8aa832b718af122e48965e9e0eb9012ee659c13c6385c93")
_GC = Source(url="https://gnupg.org/ftp/gcrypt/libgcrypt/libgcrypt-1.11.3.tar.bz2",
             sha256="2c6d562e894b2b06eefbc427d12d51ee9d3e50e90012ad6596b4cb3e421a95f2")


def _probe(variant):
    return Recipe(
        family="libgpg-error", version="1.61", upstream="https://gnupg.org/",
        license="LGPL-2.1-or-later", source=_GE, extra_sources={"gcrypt": _GC},
        build=[BuildStep(
            "C:\\msys64\\usr\\bin\\bash.exe "
            "{repo}/scripts/corpus/exercisers/gcrypt_msvc_probe.sh %s {arch} {gcrypt}"
            % variant, env={"MSYS2_PATH_TYPE": "inherit"})],
        artifacts=[Artifact(path="../probe-%s-{arch}/ge/src/.libs/libgpg-error-0.dll" % variant,
                            component="libgpg-error-0.dll")],
        toolchains=["msvc_x86", "msvc_x64"],
        notes="scratch probe", min_named_ratio=0)


RECIPES = {"gcrypt_probe_A_msvc": _probe("A"), "gcrypt_probe_B_msvc": _probe("B")}
