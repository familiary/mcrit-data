"""peinjector's four reusable library translation units, without the server.

Issue #72 pins upstream's final commit. Directly linking all four objects
retains the complete library without an infection driver or exerciser.
libpeprotocol, libpeserver and minIni are excluded. The resulting library is
linked and disassembled only. Local Linux/MinGW and Windows MSVC builds use
the same files and -O2 or /O2. No upstream source is changed.

Local measurements, SMDA 5.0.2 (functions >=10 instructions):
  peinjector_2016-05-11_gcc14_x64_peinjector.so: 67 kept + 5 removed = 72 image functions; 29 >=10, 29 unique PicHashes.
  peinjector_2016-05-11_gcc14_x86_peinjector.so: 93 kept + 5 removed = 98 image functions; 35 >=10, 35 unique PicHashes.
  peinjector_2016-05-11_mingw13_x64_peinjector.dll: 63 kept + 116 removed = 179 image functions; 32 >=10, 32 unique PicHashes.
  peinjector_2016-05-11_mingw13_x86_peinjector.dll: 51 kept + 122 removed = 173 image functions; 34 >=10, 34 unique PicHashes.
  peinjector_2016-05-11_gcc14_x64_peinjector.so vs peinjector_2016-05-11_gcc14_x86_peinjector.so: 0 shared; 29/35 unique to each.
  peinjector_2016-05-11_gcc14_x64_peinjector.so vs peinjector_2016-05-11_mingw13_x64_peinjector.dll: 0 shared; 29/32 unique to each.
  peinjector_2016-05-11_gcc14_x64_peinjector.so vs peinjector_2016-05-11_mingw13_x86_peinjector.dll: 0 shared; 29/34 unique to each.
  peinjector_2016-05-11_gcc14_x86_peinjector.so vs peinjector_2016-05-11_mingw13_x64_peinjector.dll: 0 shared; 35/32 unique to each.
  peinjector_2016-05-11_gcc14_x86_peinjector.so vs peinjector_2016-05-11_mingw13_x86_peinjector.dll: 2 shared; 33/32 unique to each.
  peinjector_2016-05-11_mingw13_x64_peinjector.dll vs peinjector_2016-05-11_mingw13_x86_peinjector.dll: 0 shared; 32/34 unique to each.

Named link/glue survivors:
  peinjector_2016-05-11_gcc14_x64_peinjector.so: none.
  peinjector_2016-05-11_gcc14_x86_peinjector.so: _init 0xda23d7f0d78226f7 (11 instructions); deregister_tm_clones 0x930296f4ff4b0b00 (18 instructions); register_tm_clones 0xcd189d0b900985c3 (26 instructions); __do_global_dtors_aux 0x9d9807ada1cb6058 (21 instructions); __x86.get_pc_thunk.bp 0x7c99608cc56520ba (2 instructions); _fini 0x92f45e02492408a1 (7 instructions)
  peinjector_2016-05-11_mingw13_x64_peinjector.dll: none.
  peinjector_2016-05-11_mingw13_x86_peinjector.dll: none.
Unnamed import stubs are retained below the comparison floor. MSVC
counts, survivors and overlap remain pending the Windows probe.
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
