"""libgpg-error and libgcrypt with cl (probe; see exercisers/gnupg_cl.py)."""

from ..recipe import Artifact, BuildStep, Recipe, Source
from .libgpg_error import _BASE, _SHA256

_PY = "python {repo}/scripts/corpus/exercisers/gnupg_cl.py {arch} gpg-error {source_root}"


def _ge(version):
    env = {"GNUPG_CL_DIAG": "1"} if version == "1.61" else {}
    return Recipe(
        family="libgpg-error", version=version, upstream="https://gnupg.org/",
        license="LGPL-2.1-or-later",
        source=Source(url=_BASE % version, sha256=_SHA256[version]),
        build=[BuildStep(_PY, env=env)],
        artifacts=[Artifact(path="msvc-{arch}/ge/src/libgpg-error-0.dll",
                            component="libgpg-error-0.dll",
                            pdb="msvc-{arch}/ge/src/libgpg-error-0.pdb")],
        toolchains=["msvc_x86", "msvc_x64"], notes="probe")


RECIPES = {"libgpg-error_%s_msvc" % v: _ge(v) for v in _SHA256}
