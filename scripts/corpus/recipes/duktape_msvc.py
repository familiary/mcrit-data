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
