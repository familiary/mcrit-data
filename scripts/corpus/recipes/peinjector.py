"""peinjector's four reusable library translation units, without the server.

Issue #72 pins upstream's final commit. Directly linking all four objects
retains the complete library without an infection driver or exerciser.
libpeprotocol, libpeserver and minIni are excluded. The resulting library is
linked and disassembled only. Local Linux/MinGW and Windows MSVC builds use
the same files and -O2 or /O2. No upstream source is changed.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_SOURCE = Source(git_url="https://github.com/JonDoNym/peinjector.git",
                 git_ref="fc3a3a56573d8e1b7df8784c060ef2adadb7220b")
_FILES = "peinjector/libpefile.c peinjector/libpeinfect.c peinjector/libpeinfect_obfuscator.c peinjector/libpetool.c"
RECIPES = {}
for _kind, _tcs in (("mingw", ["mingw_x86", "mingw_x64"]), ("linux", ["linux_x86", "linux_x64"]), ("msvc", ["msvc_x86", "msvc_x64"])):
    if _kind == "msvc":
        _command = "cl /nologo /O2 /MD /Zi /TC /D_CRT_SECURE_NO_WARNINGS " + _FILES + " /link /DLL /NOENTRY /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO /OUT:peinjector.dll /PDB:peinjector.pdb"
        _artifact = Artifact(path="peinjector.dll", component="peinjector.dll", pdb="peinjector.pdb")
        _flags = "/O2 /MD /Zi /DLL /NOENTRY /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO"
    else:
        _extension = "so" if _kind == "linux" else "dll"
        _command = "{cc} {archflag} -O2 -g -shared " + ("-fPIC -fvisibility=hidden -Wl,-Bsymbolic " if _kind == "linux" else "-Wl,--no-insert-timestamp ") + _FILES + " -o peinjector." + _extension
        _artifact = Artifact(path="peinjector." + _extension, component="peinjector." + _extension)
        _flags = "-O2 -g -shared " + ("-fPIC -fvisibility=hidden -Wl,-Bsymbolic" if _kind == "linux" else "-Wl,--no-insert-timestamp")
    RECIPES["peinjector_2016-05-11_" + _kind] = Recipe(
        family="peinjector", version="2016-05-11", source=_SOURCE,
        upstream="https://github.com/JonDoNym/peinjector", license="Unlicense",
        build=[BuildStep(_command)], artifacts=[_artifact], toolchains=_tcs,
        build_flags=_flags,
        notes="Only libpefile.c, libpeinfect.c, libpeinfect_obfuscator.c and "
              "libpetool.c are linked, the same four library files identified "
              "in Meterpreter's extension build. No server/protocol code, "
              "minIni, executable wrapper or payload. All four objects are "
              "retained without source changes; linked and disassembled only.",
    )
