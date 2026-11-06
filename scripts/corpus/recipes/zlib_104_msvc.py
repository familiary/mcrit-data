"""zlib 1.0.4 draft MSVC."""

from ..recipe import Artifact, BuildStep, Recipe, Source
from .zlib_104 import _PPP_SOURCE, _SOURCES, _Z104_SOURCE

_LINK = ("-link -DEBUG -PDB:%s -Brepro -INCREMENTAL:NO -OPT:NOREF "
         "-OPT:NOICF")
_CL = "cl -nologo -MD -O2 -Z7 -Dlocal= -LD "

_PPP = _CL + "common\\zlib.c -Fe:ppp_zlib.dll " + _LINK % "ppp_zlib.pdb"
_Z104 = _CL + _SOURCES + " -Fe:zlib1.dll " + _LINK % "zlib1.pdb"


def _r(version, source, command, dll, pdb, upstream):
    return Recipe(
        family="libzlib", version=version, upstream=upstream, license="zlib",
        source=source,
        build=[BuildStep(command), BuildStep("dir", allow_failure=True)],
        artifacts=[Artifact(path=dll, component=dll, pdb=pdb)],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="-MD -O2 -Z7 -Dlocal=")


RECIPES = {
    "libzlib_1.0.4-ppp2.4.9_msvc": _r(
        "1.0.4-ppp2.4.9", _PPP_SOURCE, _PPP, "ppp_zlib.dll", "ppp_zlib.pdb",
        "https://github.com/ppp-project/ppp"),
    "libzlib_1.0.4_msvc": _r(
        "1.0.4", _Z104_SOURCE, _Z104, "zlib1.dll", "zlib1.pdb",
        "https://github.com/madler/zlib"),
}
