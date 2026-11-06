"""peinjector's reusable library files, without the server or protocol.

Issue #72 pins the final 2016-05-11 upstream commit. Linux ELF and MinGW link all four files: libpefile.c, libpeinfect.c, libpeinfect_obfuscator.c and libpetool.c. MSVC builds only libpefile.c and libpetool.c because cl rejects the upstream variable-length array at libpeinfect_obfuscator.c:97; no source is changed. libpeprotocol, libpeserver and minIni are excluded.

Measurements, >=10 instruction functions and PicHashes:
  Linux x64 67+5=72 total, 29/29; Linux x86 93+5=98, 35/35.
  MinGW x64 63+116=179, 32/32; MinGW x86 51+122=173, 34/34.
  MSVC partial x64 15+11=26, 12/12; x86 15+11=26, 12/12.
  Linux x86 versus MinGW x86 shares 2 hashes; every other cross-compiler or cross-architecture pair shares 0. MSVC x86 versus x64 shares 0.

The Linux x86 image retains _init 0xda23d7f0d78226f7 (11 instructions), deregister_tm_clones 0x930296f4ff4b0b00 (18), register_tm_clones 0xcd189d0b900985c3 (26), __do_global_dtors_aux 0x9d9807ada1cb6058 (21), __x86.get_pc_thunk.bp 0x7c99608cc56520ba (2) and _fini 0x92f45e02492408a1 (7). The MSVC partial image's named pefile_init is below ten instructions (3 x64, 6 x86); it has no named runtime survivor at the comparison floor. Images are linked and disassembled only.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_SOURCE = Source(git_url="https://github.com/JonDoNym/peinjector.git",
                 git_ref="fc3a3a56573d8e1b7df8784c060ef2adadb7220b")
_FILES = "peinjector/libpefile.c peinjector/libpeinfect.c peinjector/libpeinfect_obfuscator.c peinjector/libpetool.c"
RECIPES = {}
for _kind, _tcs in (("mingw", ["mingw_x86", "mingw_x64"]), ("linux", ["linux_x86", "linux_x64"]), ("msvc", ["msvc_x86", "msvc_x64"])):
    if _kind == "msvc":
        _command = "cl /nologo /O2 /MD /Zi /TC /D_CRT_SECURE_NO_WARNINGS " + "peinjector/libpefile.c peinjector/libpetool.c" + " /link /DLL /NOENTRY kernel32.lib ucrt.lib vcruntime.lib msvcrt.lib /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO /OUT:pefile_petool.dll /PDB:pefile_petool.pdb"
        _artifact = Artifact(path="pefile_petool.dll", component="pefile_petool.dll", pdb="pefile_petool.pdb")
        _flags = "/O2 /MD /Zi /DLL /NOENTRY kernel32.lib ucrt.lib vcruntime.lib msvcrt.lib /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO"
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
        notes=("MSVC collects only libpefile.c and libpetool.c. The obfuscator "
               "has a variable-length array rejected by cl (C2057/C2466/C2133), "
               "and libpeinfect requires it. No source is patched. No server, "
               "protocol code, minIni or executable wrapper; disassembly only."
               if _kind == "msvc" else
               "Only libpefile.c, libpeinfect.c, libpeinfect_obfuscator.c and "
               "libpetool.c are linked, the same four library files identified "
               "in Meterpreter's extension build. No server/protocol code, "
               "minIni, executable wrapper or payload. All four objects are "
               "retained without source changes; linked and disassembled only."),
    )
