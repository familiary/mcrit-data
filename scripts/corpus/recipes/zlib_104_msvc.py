"""zlib 1.0.4 and ppp's zlib.c built with MSVC, the compiler Meterpreter uses.

The MSVC counterpart of zlib_104.py; see that module for what the two sources
are, why ``/Dlocal=`` is passed and why the ShiftMediaProject and msvc143 rows
already in data/libzlib cannot stand in (0 - 3 shared PicHashes). The issue
that asked for this pre-1.2 inflate noted the sample it came from is built
with MSVC, which is why this leg matters more than the MinGW one.

Neither source has a usable MSVC build here. 1.0.4's Makefile.msc builds a
static zlib.lib plus example and minigzip, ppp has no build system, and
neither takes -MD, so cl is invoked directly: one command, every source file
on the line, ``/LD`` for a DLL with no .def (the PDB names the functions, as
for every MSVC recipe here).

Mandates, all passed explicitly: ``-MD`` (cl's default would be -MT and file
the static C runtime under libzlib), ``-O2`` as the other zlib rows, ``-Z7``
(debug info in the objects; one PDB is made at link), and at link ``-DEBUG
-Brepro -INCREMENTAL:NO -OPT:NOREF -OPT:NOICF``. No /GL, no /LTCG. Upstream's
Makefile.msc would default to -MT and a static library, so this departs from
it knowingly. cl needed no dialect option for the K&R sources; the only
diagnostic was warning C4005 for crc32.c redefining ``local``.
"""

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
        build_flags="-MD -O2 -Z7 -Dlocal= (single cl invocation); -DEBUG "
                    "-Brepro -INCREMENTAL:NO -OPT:NOREF -OPT:NOICF at link",
        notes="Built with one cl command rather than upstream's "
              "Makefile.msc (static library, -MT): -MD so the MSVC C "
              "runtime stays attributed to data/MSVC, -Dlocal= so internal "
              "routines are kept as functions. See zlib_104.py.")


RECIPES = {
    "libzlib_1.0.4-ppp2.4.9_msvc": _r(
        "1.0.4-ppp2.4.9", _PPP_SOURCE, _PPP, "ppp_zlib.dll", "ppp_zlib.pdb",
        "https://github.com/ppp-project/ppp"),
    "libzlib_1.0.4_msvc": _r(
        "1.0.4", _Z104_SOURCE, _Z104, "zlib1.dll", "zlib1.pdb",
        "https://github.com/madler/zlib"),
}
