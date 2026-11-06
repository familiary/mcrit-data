"""libgcrypt with cl (scratch candidates)."""

from ..recipe import Artifact, BuildStep, Recipe, Source
from .libgcrypt import PAIRING, _BASE, _GPGERR_SHA256, _GPGERR_URL, _SHA256

_BASH = "C:\\msys64\\usr\\bin\\bash.exe {repo}/scripts/corpus/exercisers/gnupg_msvc.sh"


def _gc(version):
    err = PAIRING[version]
    return Recipe(
        family="libgcrypt", version=version, upstream="https://gnupg.org/",
        license="LGPL-2.1-or-later",
        source=Source(url=_BASE % version, sha256=_SHA256[version]),
        extra_sources={"gpg_error": Source(url=_GPGERR_URL % err,
                                           sha256=_GPGERR_SHA256[err])},
        build=[BuildStep(_BASH + " {arch} gcrypt {source_root} {gpg_error}",
                         env={"MSYS2_PATH_TYPE": "inherit"})],
        artifacts=[Artifact(path="msvc-{arch}/gc/src/.libs/libgcrypt-20.dll",
                            component="libgcrypt-20.dll",
                            pdb="msvc-{arch}/gc/src/.libs/libgcrypt-20.pdb")],
        toolchains=["msvc_x86", "msvc_x64"], notes="scratch candidate")


RECIPES = {"libgcrypt_%s_msvc" % v: _gc(v) for v in _SHA256}
