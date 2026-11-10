"""cmp built with MSVC, beside the MinGW builds of the same tags.

camgunz/cmp is compiled into c-toxcore and so into Crytox, and a Windows
binary that carries it is built by whatever the host project uses - cl as
often as gcc. data/cmp holds only the MinGW pair (v10, v20); these recipes add
the same two tags under MSVC so a cl-built sample can match. The pins, the
reasons for the two versions and the vendoring story are in cmp.py.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

Build: cmp.c compiled directly with cl and linked to a DLL, the analogue of
the MinGW recipe's single gcc line. No driver translation unit, no use of the
Makefile or CMakeLists.txt (test/example harnesses).

Exports, the one real decision. cmp.h has no export macro, and the MinGW
build gets its exports for free because mingw-w64 exports every global of a
DLL that declares none. link has no such mode, so a .def file is needed -
and upstream must not be patched. The recipe generates it from the compiled
object instead of from the header: a python step runs ``dumpbin /SYMBOLS
cmp.obj``, keeps every defined External function and writes cmp.def (a
build output next to the object, not an upstream file). That is the same
rule as MinGW's - every non-static function, including the few file-local
helpers upstream leaves non-static - rather than a hand-written list that
could drift between v10 and v20. cmp has no non-static data (its version
constants are ``static const``), so only functions are exported. On the
32-bit leg dumpbin reports the cdecl leading underscore (``_cmp_init``) and
the .def wants the undecorated name, so the step strips one underscore when
{arch} is x86; cdecl is the only convention cmp uses, so there are no
@N-decorated names to handle. Exported ordinals/names are what lets SMDA name
the functions even before the PDB is consulted.

Flags, from the corpus mandates: /MD (the DLL runtime is imported, so the CRT
stays attributed to data/MSVC rather than being linked in as /MT would), /O2
(implies /Ob2), /Zi with an explicit /Fd for the PDB, no /GL and no /LTCG,
and at link /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF. MSBuild is
not involved, so there is no props file and nothing for
ForceImportBeforeCppTargets to carry: the overrides are the command line. The
MinGW build is plain -O2 with no --gc-sections, so NOREF/NOICF keeps the pair
comparable. The flags that actually ran are read back from the tracker log
rather than assumed (see the README's MSVC section).

Measurements, from the runner build (windows-2022, cl 19.44.35229, v143).
The exports step worked on the second attempt: the first dumpbin filter
matched '() External' with one space, but dumpbin pads the column with
several, so cmp.def came out as a bare EXPORTS and the DLL exported nothing
(SMDA is_exported 0 of 194). With the filter fixed the DLL exports 159 (v10)
and 170 (v20) names on both arches, identical to the MinGW artefacts' counts,
and the step asserts a non-empty list so that cannot pass silently again.

Function counts, kept after the MSVC glue baseline removed 123 (x86) or 129
(x64) runtime functions, so kept plus removed is the image total:

  v10  x86 194 + 123 = 317   x64 171 + 129 = 300
  v20  x86 213 + 123 = 336   x64 189 + 129 = 318

(MinGW, for comparison: v10 160 / 169, v20 175 / 184 kept.) Every kept
function is named from the PDB (0 unnamed). What the baseline removed is the
static CRT startup that /MD still links into a DLL: _DllMainCRTStartup,
dllmain_dispatch and friends, __scrt_*, the __castguard_* stubs, the SEH and
GS-cookie helpers, _initterm, atexit/onexit, and the memcpy/memset thunks.
No runtime glue survives by name: the non-exported survivors (35 on v10 x86,
19 on v20 x64) are cmp's own file-local helpers - be16/be32/be64, read_byte,
read_type_marker, write_byte, write_fixed_value, read_obj_data, skip_bytes,
type_marker_to_cmp_type - and SMDA's 'cmp_read_int$+0x109'-style names, which
are code chunks of exported functions that /O2 split off. Because v10 has the
chunks and MinGW does not, the MSVC counts run above the MinGW ones even
though the source is the same.

MinGW against MSVC PicHash overlap, functions of 10+ instructions (x86 /
x64): 0 shared of 137 / 125 (v10) and of 153 / 140 (v20) on the MinGW side.
At any size the overlap is 6-7 hashes per pair, all of them two- to
five-instruction accessors (cmp_version, cmp_mp_version, cmp_object_is_nil,
_is_bool, _is_float, _is_double, and cmp_init on v10 x64). So this axis shares
essentially nothing with the MinGW one, which is the case for building it.
MSVC v10 against MSVC v20: 79 / 59 shared of 153 / 145 (x86 / x64), against
69 / 57 of 137 / 125 for MinGW, so the two tags differ by about as much under
either compiler and both are worth keeping.

The copy c-toxcore vendors (backlog #47) is built too: recipe
``cmp_toktok_52bfcfa_msvc`` (version ``toktok-52bfcfa``), TokTok/cmp at
52bfcfa17d2eb4322da2037ad625f5575129cece with /DCMP_NO_FLOAT=1 and otherwise
the steps above (pin and derivation in cmp.py on the MinGW branch). Counted
on the runner (run 42676010529, v143), kept + removed = image total: x86
204 + 123 = 327, x64 183 + 129 = 312. PicHash overlap of functions of 10+
instructions (x86 / x64), of its 163 / 152 distinct: 110 / 80 with v20 and
73 / 55 with v10 (the MSVC v20 has 175 / 161), and 0 / 0 with its MinGW
counterpart.

No separate "c-toxcore Release" image on this axis, unlike MinGW's cmp-O3.dll,
because it would be a copy. c-toxcore's CMakeLists.txt (v0.2.24) gives cl
/W4 /analyze and a list of /wd warning switches (lines 113-138), C11 through
CMAKE_C_STANDARD (/std:c11) and /DCMP_NO_FLOAT=1; CMake's MSVC Release default
adds /MD /O2 /Ob2 /DNDEBUG. Against the line built here (/O2 /MD
/DCMP_NO_FLOAT=1) that is /Ob2, which /O2 implies, /DNDEBUG, which cmp.c and
cmp.h never test, and warning, analysis and language-mode switches. It was
measured, not only read: run 42770123676 (windows-2022, v143) built cmp.c a
second time with ``/O2 /Ob2 /DNDEBUG /std:c11 /W4 /analyze /MD /Zi
/DCMP_NO_FLOAT=1`` and the same link line, and every function of that image
has the name, instruction count and PicHash of the corresponding function in
the committed toktok-52bfcfa cmp.dll, on both arches (x86 204 kept + 123
removed, 163 of 163 distinct PicHashes of 10+ instructions shared; x64 183 +
129, 152 of 152). The duplicate is not committed and its build step is not
kept in this recipe; the toktok-52bfcfa image above is the c-toxcore MSVC
Release compile of cmp.c.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Written as a python -c one-liner with no braces and no double quotes, so it
# survives both cmd.exe and the {placeholder} substitution. Only symbols that
# dumpbin lists as defined (SECTn) functions ("()") with External linkage are
# taken; UNDEF entries are the CRT imports and are skipped.
_DEF = (
    'python -c "'
    "import subprocess;"
    "o=subprocess.check_output(['dumpbin','/SYMBOLS','cmp.obj']).decode();"
    "l=[t[t.index('|')+1] for t in map(str.split,o.splitlines()) "
    "if '|' in t and '()' in t and 'External' in t "
    "and any([w.startswith('SECT') for w in t])];"
    "p='{arch}'=='x86';"
    "n=sorted(set([s[1:] if p and s.startswith('_') else s for s in l]));"
    "assert n,'no exports found';"
    "open('cmp.def','w').write('EXPORTS\\n'+'\\n'.join(n)+'\\n');"
    "print(len(n),'exports')"
    '"')

_COMPILE = 'cl /nologo /c /O2 /MD /Zi /Fdcmp.pdb /Focmp.obj cmp.c'

# /INCREMENTAL:NO because /DEBUG implies /INCREMENTAL and the /OPT:NO* forms
# do not suppress it; see sqlite3_msvc.py for the jump-thunk measurement.
_LINK = ('link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO '
         '/OPT:NOREF /OPT:NOICF /DEF:cmp.def '
         '/PDB:cmp.pdb /OUT:cmp.dll cmp.obj')

_FLAGS = ("/O2 /MD /Zi (cmp.c compiled directly, no -DCMP_NO_FLOAT); "
          "/DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link; "
          "exports from a /DEF generated from the object's defined "
          "external functions")


def _cmp_msvc(version, git_ref):
    return Recipe(
        family="cmp",
        version=version,
        upstream="https://github.com/camgunz/cmp",
        license="MIT",
        source=Source(git_url="https://github.com/camgunz/cmp.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_COMPILE),
            BuildStep(_DEF),
            BuildStep(_LINK),
            BuildStep("dir", allow_failure=True),
        ],
        artifacts=[Artifact(path="cmp.dll", component="cmp.dll",
                            pdb="cmp.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS,
        notes="The same two tags as the MinGW recipe, so the artefacts can "
              "be compared directly. Upstream is unpatched; the export "
              "table is generated at build time from the compiled object "
              "because cmp.h has no export macro. Built against the DLL "
              "runtime, so the MSVC C runtime is imported rather than "
              "linked in and stays attributed to data/MSVC.",
    )


# The copy c-toxcore vendors (TokTok/cmp at 52bfcfa, see cmp.py on the MinGW
# branch for how the pin was established), built with the define c-toxcore
# builds it with. Same steps as above plus /DCMP_NO_FLOAT=1.
_TOKTOK_COMPILE = ('cl /nologo /c /O2 /MD /Zi /DCMP_NO_FLOAT=1 '
                   '/Fdcmp.pdb /Focmp.obj cmp.c')

_TOKTOK = Recipe(
    family="cmp",
    version="toktok-52bfcfa",
    upstream="https://github.com/TokTok/cmp",
    license="MIT",
    source=Source(git_url="https://github.com/TokTok/cmp.git",
                  git_ref="52bfcfa17d2eb4322da2037ad625f5575129cece"),
    build=[
        BuildStep(_TOKTOK_COMPILE),
        BuildStep(_DEF),
        BuildStep(_LINK),
        BuildStep("dir", allow_failure=True),
    ],
    artifacts=[Artifact(path="cmp.dll", component="cmp.dll",
                        pdb="cmp.pdb")],
    toolchains=["msvc_x86", "msvc_x64"],
    build_flags=("/O2 /MD /Zi /DCMP_NO_FLOAT=1 (cmp.c compiled directly); "
                 "/DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at "
                 "link; exports from a /DEF generated from the object's "
                 "defined external functions"),
    notes="The TokTok fork c-toxcore vendors as third_party/cmp, at the "
          "commit pinned there (52bfcfa), built with -DCMP_NO_FLOAT=1 as "
          "c-toxcore does. Upstream is unpatched; exports are generated "
          "from the compiled object. Built against the DLL runtime.",
)


RECIPES = {
    "cmp_10_msvc": _cmp_msvc("10", "v10"),
    "cmp_20_msvc": _cmp_msvc("20", "v20"),
    "cmp_toktok_52bfcfa_msvc": _TOKTOK,
}
