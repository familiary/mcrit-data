"""peinjector's reusable library files, without the server or protocol.

Issue #72 pins the final 2016-05-11 upstream commit. Every axis (Linux ELF, MinGW, MSVC) links the same four files: libpefile.c, libpeinfect.c, libpeinfect_obfuscator.c and libpetool.c. libpeprotocol, libpeserver and minIni are excluded.

MSVC PATCH (the MSVC image is NOT byte-identical to a build of unmodified upstream). cl rejects the variable-length array in libpeinfect_obfuscator.c (C2057 expected constant expression, C2466, C2133). The MSVC recipe applies this one-line change to the build tree before compiling (the repository holds no modified upstream source):

  --- a/peinjector/libpeinfect_obfuscator.c
  +++ b/peinjector/libpeinfect_obfuscator.c
  @@ -96,3 +96,3 @@ static void __peinfector_obfuscator_shuffle(void *array, size_t n, size_t size) {
  -  char tmp[size];
  +  char tmp[sizeof(SHELLCODE_ENTRY)];

The shuffle helper has one caller, which passes sizeof(SHELLCODE_ENTRY) as size, so the fixed bound is exactly the old runtime length and behaviour is unchanged. The step is a python one-liner that asserts the original line occurs exactly once. The MinGW and Linux images are built from unmodified source.

The earlier MSVC image (pefile_petool.dll, libpefile.c and libpetool.c only, 15+11=26 functions per arch) is superseded by the full peinjector.dll build and removed.

Measurements, >=10 instruction functions and PicHashes:
  Linux x64 67+5=72 total, 29/29; Linux x86 93+5=98, 35/35.
  MinGW x64 63+116=179, 32/32; MinGW x86 51+122=173, 34/34.
  MSVC (patched) x64 83+60=143, 56/56; x86 83+50=133, 55/55.
  Linux x86 versus MinGW x86 shares 2 hashes; every other cross-compiler or cross-architecture pair shares 0. MSVC (patched) shares 0 hashes with every Linux/MinGW image and between its own x86 and x64 images.

Surviving names at the 10-instruction floor in the MSVC images are all peinjector library functions (pefile_*, peinfect_*, petool_* and the obfuscator helpers); no runtime or glue name survives. The Linux x86 image retains _init 0xda23d7f0d78226f7 (11 instructions), deregister_tm_clones 0x930296f4ff4b0b00 (18), register_tm_clones 0xcd189d0b900985c3 (26), __do_global_dtors_aux 0x9d9807ada1cb6058 (21), __x86.get_pc_thunk.bp 0x7c99608cc56520ba (2) and _fini 0x92f45e02492408a1 (7). Images are linked and disassembled only.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_SOURCE = Source(git_url="https://github.com/JonDoNym/peinjector.git",
                 git_ref="fc3a3a56573d8e1b7df8784c060ef2adadb7220b")
_FILES = "peinjector/libpefile.c peinjector/libpeinfect.c peinjector/libpeinfect_obfuscator.c peinjector/libpetool.c"
_PATCH = ("python -c \"import pathlib;p=pathlib.Path('peinjector/libpeinfect_obfuscator.c');"
          "s=p.read_text();assert s.count('char tmp[size];')==1;"
          "p.write_text(s.replace('char tmp[size];','char tmp[sizeof(SHELLCODE_ENTRY)];'))\"")
RECIPES = {}
for _kind, _tcs in (("mingw", ["mingw_x86", "mingw_x64"]), ("linux", ["linux_x86", "linux_x64"]), ("msvc", ["msvc_x86", "msvc_x64"])):
    _steps = None
    if _kind == "msvc":
        _steps = [BuildStep(_PATCH), BuildStep("cl /nologo /O2 /MD /Zi /TC /D_CRT_SECURE_NO_WARNINGS " + _FILES + " /link /DLL /NOENTRY kernel32.lib ucrt.lib vcruntime.lib msvcrt.lib /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO /OUT:peinjector.dll /PDB:peinjector.pdb")]
        _artifact = Artifact(path="peinjector.dll", component="peinjector.dll", pdb="peinjector.pdb")
        _flags = "patched libpeinfect_obfuscator.c (char tmp[size] -> char tmp[sizeof(SHELLCODE_ENTRY)]) /O2 /MD /Zi /DLL /NOENTRY kernel32.lib ucrt.lib vcruntime.lib msvcrt.lib /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO"
    else:
        _extension = "so" if _kind == "linux" else "dll"
        _command = "{cc} {archflag} -O2 -g -shared " + ("-fPIC -fvisibility=hidden -Wl,-Bsymbolic " if _kind == "linux" else "-Wl,--no-insert-timestamp ") + _FILES + " -o peinjector." + _extension
        _artifact = Artifact(path="peinjector." + _extension, component="peinjector." + _extension)
        _flags = "-O2 -g -shared " + ("-fPIC -fvisibility=hidden -Wl,-Bsymbolic" if _kind == "linux" else "-Wl,--no-insert-timestamp")
    RECIPES["peinjector_2016-05-11_" + _kind] = Recipe(
        family="peinjector", version="2016-05-11", source=_SOURCE,
        upstream="https://github.com/JonDoNym/peinjector", license="Unlicense",
        build=_steps or [BuildStep(_command)], artifacts=[_artifact], toolchains=_tcs,
        build_flags=_flags,
        notes=("All four library files are built. The recipe patches the build tree: "
               "libpeinfect_obfuscator.c:97 `char tmp[size];` (variable-length "
               "array, cl C2057/C2466/C2133) becomes `char tmp[sizeof(SHELLCODE_ENTRY)];`, "
               "the only size its single caller passes. This image is NOT "
               "byte-identical to a build of unmodified upstream. No server, "
               "protocol code, minIni or executable wrapper; disassembly only."
               if _kind == "msvc" else
               "Only libpefile.c, libpeinfect.c, libpeinfect_obfuscator.c and "
               "libpetool.c are linked, the same four library files identified "
               "in Meterpreter's extension build. No server/protocol code, "
               "minIni, executable wrapper or payload. All four objects are "
               "retained without source changes; linked and disassembled only."),
    )
