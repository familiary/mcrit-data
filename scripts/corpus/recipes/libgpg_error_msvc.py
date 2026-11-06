"""libgpg-error and libgcrypt with cl (scratch candidates; see README)."""

from ..recipe import Artifact, BuildStep, Recipe, Source
from .libgpg_error import _BASE, _SHA256

_BASH = "C:\\msys64\\usr\\bin\\bash.exe {repo}/scripts/corpus/exercisers/gnupg_msvc.sh"


def _ge(version):
    return Recipe(
        family="libgpg-error", version=version, upstream="https://gnupg.org/",
        license="LGPL-2.1-or-later",
        source=Source(url=_BASE % version, sha256=_SHA256[version]),
        build=[BuildStep(_BASH + " {arch} gpg-error {source_root}",
                         env={"MSYS2_PATH_TYPE": "inherit"})],
        artifacts=[Artifact(path="msvc-{arch}/src/.libs/libgpg-error-0.dll",
                            component="libgpg-error-0.dll",
                            pdb="msvc-{arch}/src/.libs/libgpg-error-0.pdb")],
        toolchains=["msvc_x86", "msvc_x64"], notes="scratch candidate")


RECIPES = {"libgpg-error_%s_msvc" % v: _ge(v) for v in _SHA256}
