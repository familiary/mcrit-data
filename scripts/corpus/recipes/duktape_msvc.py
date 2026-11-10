"""Duktape built with MSVC, beside the MinGW builds of the same releases.

data/Duktape holds only MinGW artefacts. Duktape reaches Windows malware and
tooling (MeshAgent compiles its vendored 2.6.0 duktape.c into the agent) built
by whatever the host project uses, cl as often as gcc, so these recipes add
the same two release tarballs under MSVC. The pins, the choice of 2.6.0 and
2.7.0 and the reason the pre-generated source distribution is compiled
as shipped are in duktape.py; the sha256 values below are copied from it.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

Build: ``src/duktape.c`` compiled directly with cl and linked to a DLL, the
analogue of the MinGW recipe's single gcc line. The configuration is the
MinGW one: no configure.py run, no DUK_USE_* or DUK_OPT_* options, no -D
defines at all, so the shipped default ``duk_config.h`` autodetects the
platform (it selects the MSVC branch from _MSC_VER here, the GCC branch there).
Nothing in the tree is patched.

Exports, the one real decision. duktape.h has an export macro (DUK_EXTERNAL),
but it is plain ``extern`` unless DUK_F_DLL_BUILD-style defines are given, so
nothing gets __declspec(dllexport) from the default configuration; the MinGW
build gets its exports because mingw-w64 exports every global of a DLL that
declares none (all the duk_* API plus the DUK_INTERNAL functions, which are
also plain ``extern`` there). link has no such mode, and upstream must not be
patched, so the recipe generates the .def from the compiled object instead of
a hand-written list: a python step runs ``dumpbin /SYMBOLS duktape.obj``, keeps
every defined External function and writes duktape.def (a build output next to
the object, not an upstream file), which is the same rule as MinGW's for
functions. Non-static data (the unicode tables and similar) is not exported;
SMDA disassembles code, so it changes no function. On x86 dumpbin reports the
cdecl leading underscore and the .def wants the undecorated name, so one
underscore is stripped when {arch} is x86; Duktape uses cdecl only. The dumpbin
filter is the one that worked in cmp_msvc.py after its first attempt, and the
step asserts a non-empty list.

Flags: /O2 /MD /Zi /Fdduktape.pdb, no /GL and no /LTCG; at link /DEBUG /Brepro
/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF. cl and link print nothing of their
command lines here (plain cmd steps, no NMake or CMake), so the flags are as
written in this file rather than read back from a log.

Optimisation level. The MinGW recipe is -Os -std=c99, not -O2: upstream's own
Makefile.cmdline and Makefile.sharedlibrary use -Os, and the MinGW recipe
follows them. The MSVC side uses /O2, the corpus convention for MSVC and the
only level the mandates name; /O1 (minimise size) would be the closer MSVC
analogue of -Os but is not used. Duktape's bytecode executor is one very large
function whose shape depends on the level, so the two axes differ in
optimisation level as well as in compiler; /O2 is the one MSVC variant built.

Measurements, from the runner build (windows-2022, cl 19.44.35229, v143; flags
read back from the build log: the compile and link lines above are what ran).
The exports step found 287 external functions on x86 and x64 (2.6.0). That is
the duk_* API: the shipped duk_config.h defines DUK_INTERNAL as ``static`` in
single-file builds [read, duk_config.h line 1096], so the engine internals
are not external symbols for either compiler. The MinGW export count was not
measured, so no count comparison is made.

Function counts, kept after the MSVC glue baseline removed some runtime
functions, so kept plus removed is the image total:

  2.6.0  x86 1487 + 176 = 1663   x64 1473 + 163 = 1636
  2.7.0  x86 1489 + 177 = 1666   x64 1475 + 163 = 1638

(MinGW kept: 969 / 962 and 969 / 961.) The MSVC side keeps about 500 more
functions: probably because cl at /O2 inlines Duktape's many ``static`` helpers
less than gcc -Os does (not isolated) and it splits large functions into ``$`` chunks. Every
kept function is named from the PDB (0 unnamed).

Glue survivors, by name (2.6.0; 2.7.0 is the same). Eleven on x64 and 19 on
x86 are one-instruction import or linker thunks whose PicHash is
1253497258561142223 (x86: _QueryPerformanceFrequency, _GetSystemTimePrecise
AsFileTime, _FileTimeToSystemTime, _SystemTimeToFileTime, _SystemTimeToTz
SpecificLocalTime, _longjmp, __setjmp3, __dsign, __dclass, _cbrt, _log2,
__CIatan2, __CIfmod and six __libm_sse2_*_precise; x64: the five Win32 calls
plus longjmp, __intrinsic_setjmp, _dsign, _dclass, cbrt, log2). x86 has two more:
_ftoul2_legacy (7 instructions, PicHash 18195770136869812399) and the
__scrt_is_nonwritable_in_current_image$+0x77 chunk (1 instruction, PicHash
14488817810038351142). They are runtime/import stubs the baseline probes do not
cover (it removed sin, floor, memcpy and the like, not these); baseline.py is shared tooling and is not changed here.

MinGW against MSVC PicHash overlap, functions of 10+ instructions (x86 / x64):
0 / 1 shared, of 796 / 720 (2.6.0) and 796 / 719 (2.7.0) MinGW functions and
1175 / 1141 and 1176 / 1141 MSVC ones. The one hit is
duk_heap_remove_from_heap_allocated (11 instructions, x64). At any size the
overlap is 2 (x86) and 25 (x64) hashes per pair, almost all one-instruction
thunks. So this axis shares essentially nothing with the MinGW one.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# A python -c one-liner with no braces and no double quotes, so it survives
# both cmd.exe and the {placeholder} substitution. Only symbols dumpbin lists
# as defined (SECTn) functions ("()") with External linkage are taken; UNDEF
# entries are the CRT imports and are skipped.
_DEF = (
    'python -c "'
    "import subprocess;"
    "o=subprocess.check_output(['dumpbin','/SYMBOLS','duktape.obj']).decode();"
    "l=[t[t.index('|')+1] for t in map(str.split,o.splitlines()) "
    "if '|' in t and '()' in t and 'External' in t "
    "and any([w.startswith('SECT') for w in t])];"
    "p='{arch}'=='x86';"
    "n=sorted(set([s[1:] if p and s.startswith('_') else s for s in l]));"
    "assert n,'no exports found';"
    "open('duktape.def','w').write('EXPORTS\\n'+'\\n'.join(n)+'\\n');"
    "print(len(n),'exports')"
    '"')

_COMPILE = 'cl /nologo /c /O2 /MD /Zi /Fdduktape.pdb /Foduktape.obj duktape.c'

# /INCREMENTAL:NO because /DEBUG implies /INCREMENTAL and the /OPT:NO* forms
# do not suppress it; see lua_msvc.py for the jump-thunk measurement.
_LINK = ('link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO '
         '/OPT:NOREF /OPT:NOICF /DEF:duktape.def '
         '/PDB:duktape.pdb /OUT:duktape.dll duktape.obj')

_FLAGS = ("/O2 /MD /Zi (src/duktape.c compiled directly, default duk_config.h, "
          "no defines); /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF "
          "at link; exports from a /DEF generated from the object's defined "
          "external functions")


def _duktape_msvc(version, sha256):
    return Recipe(
        family="Duktape",
        version=version,
        upstream="https://github.com/svaarala/duktape",
        license="MIT",
        source=Source(
            url="https://github.com/svaarala/duktape/releases/download/"
                "v%s/duktape-%s.tar.xz" % (version, version),
            sha256=sha256),
        build=[
            BuildStep(_COMPILE, cwd="src"),
            BuildStep(_DEF, cwd="src"),
            BuildStep(_LINK, cwd="src"),
            BuildStep("dir", cwd="src", allow_failure=True),
        ],
        artifacts=[Artifact(path="src/duktape.dll", component="duktape.dll",
                            pdb="src/duktape.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS,
        notes="The same two tarballs as the MinGW recipe, so the artefacts "
              "can be compared directly. Upstream is unpatched; the export "
              "table is generated at build time from the compiled object. "
              "Built against the DLL runtime, so the MSVC C runtime is "
              "imported rather than linked in and stays attributed to "
              "data/MSVC. /O2, where the MinGW recipe is -Os.",
    )


RECIPES = {
    "Duktape_2.6.0_msvc": _duktape_msvc(
        "2.6.0", "96f4a05a6c84590e53b18c59bb776aaba80a205afbbd92b82be609ba7fe75fa7"),
    "Duktape_2.7.0_msvc": _duktape_msvc(
        "2.7.0", "90f8d2fa8b5567c6899830ddef2c03f3c27960b11aca222fa17aa7ac613c2890"),
}


# The final sweep: MeshAgent's vendored Duktape 2.6.0 with cl, the MSVC
# counterpart of Duktape_2.6.0_meshagent (duktape.py says why and how): the
# defines the MeshAgent MSVC recipe compiles the engine with, and the agent's
# exec-timeout callback imported from MeshAgent.exe through an import library
# lib.exe makes from a two-line .def, so no stub code is in the image.
from .duktape import MESHAGENT_REF  # noqa: E402

_MESH_DEFS = ("/DDUK_USE_DEBUGGER_SUPPORT /DDUK_USE_INTERRUPT_COUNTER "
              "/DDUK_USE_DEBUGGER_INSPECT /DDUK_USE_DEBUGGER_PAUSE_UNCAUGHT "
              "/DDUK_USE_DEBUGGER_DUMPHEAP")


def _meshagent_vendored_msvc():
    host_def = ('python -c "open(\'corpus-host.def\',\'w\').write('
                '\'LIBRARY MeshAgent.exe\\nEXPORTS\\n'
                'ILibDuktape_EXEC_TIMEOUT_CHECK\\n\')"')
    return Recipe(
        family="Duktape",
        version="2.6.0-meshagent",
        upstream="https://github.com/Ylianst/MeshAgent (vendored "
                 "https://github.com/svaarala/duktape 2.6.0)",
        license="MIT (Duktape); MeshAgent is Apache-2.0",
        source=Source(git_url="https://github.com/Ylianst/MeshAgent.git",
                      git_ref=MESHAGENT_REF),
        build=[
            BuildStep(host_def, cwd="microscript"),
            BuildStep('if "{arch}"=="x64" lib /nologo /DEF:corpus-host.def '
                      '/MACHINE:X64 /OUT:corpus-host.lib', cwd="microscript"),
            BuildStep('if "{arch}"=="x86" lib /nologo /DEF:corpus-host.def '
                      '/MACHINE:X86 /OUT:corpus-host.lib', cwd="microscript"),
            BuildStep(_COMPILE.replace("/Zi ", "/Zi " + _MESH_DEFS + " "),
                      cwd="microscript"),
            BuildStep(_DEF, cwd="microscript"),
            BuildStep(_LINK + " corpus-host.lib", cwd="microscript"),
            BuildStep("dir", cwd="microscript", allow_failure=True),
        ],
        artifacts=[Artifact(path="microscript/duktape.dll", component="duktape.dll",
                            pdb="microscript/duktape.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi " + _MESH_DEFS + " (MeshAgent's microscript/"
                    "duktape.c and its customised headers); /DEBUG /Brepro "
                    "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link; exports from "
                    "the object; ILibDuktape_EXEC_TIMEOUT_CHECK imported from "
                    "MeshAgent.exe through a generated import library",
        notes="MeshAgent's vendored Duktape 2.6.0 at the MeshAgent commit the "
              "MeshAgent recipes pin, compiled on its own as a DLL with cl. The "
              "agent's exec-timeout callback is imported from the host "
              "executable, as MeshAgent's own per-executable Duktape DLL does; "
              "no source is edited. Built against the DLL runtime.",
    )


RECIPES["Duktape_2.6.0_meshagent_msvc"] = _meshagent_vendored_msvc()

