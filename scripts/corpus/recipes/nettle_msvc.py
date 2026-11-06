"""Nettle built with MSVC, beside the MinGW and Linux builds of the same releases.

DRAFT docstring; filled in after the runner build.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from .nettle import _LICENSE, _UPSTREAM, _VERSIONS


_BUILD = ("python {repo}/scripts/corpus/exercisers/nettle_msvc_build.py "
          "--arch {arch}")


def _recipe(version):
    sha256 = _VERSIONS[version][0]
    hogweed = _VERSIONS[version][3] is not None
    artifacts = [Artifact(path="libnettle.dll", component="libnettle.dll",
                          pdb="libnettle.pdb")]
    if hogweed:
        artifacts.append(Artifact(path="libhogweed.dll",
                                  component="libhogweed.dll",
                                  pdb="libhogweed.pdb"))
    return Recipe(
        family="Nettle",
        version=version,
        upstream=_UPSTREAM,
        license=_LICENSE,
        source=Source(url="https://ftp.gnu.org/gnu/nettle/nettle-%s.tar.gz" % version,
                      sha256=sha256),
        build=[BuildStep(_BUILD + ("" if hogweed else " --no-hogweed")),
               BuildStep("dir", allow_failure=True)],
        artifacts=artifacts,
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi, HAVE_CONFIG_H, C only (no assembler); "
                    "/DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at "
                    "link; exports generated from the objects",
        notes="",
    )


RECIPES = {"Nettle_%s_msvc" % version: _recipe(version) for version in _VERSIONS}
