"""LZO 2.10 built with MSVC, beside the MinGW build of the same release.

LZO turns up in VNC servers, packers and game-data tools, and a Windows
binary that carries it is built by whatever the host project uses - cl as
often as gcc. data/lzo holds only the MinGW pair; this recipe adds the same
2.10 tarball under MSVC so a cl-built sample can match. The pin, the reason
for the full library rather than miniLZO and the UltraVNC story are in
lzo.py; the tarball and its SHA-256 are the same here.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

Build: every src/*.c compiled directly with cl and linked to a DLL, the
analogue of the MinGW recipe's libtool link of the same set. Upstream's
CMakeLists.txt was read and not used: it declares cmake_minimum_required
3.0, which CMake 4 refuses unless a policy-minimum variable is passed, so the
build would depend on which CMake the runner image carries, and it also
builds the examples and test programs. What it does for the library is
GLOB src/*.c, add include/ and the root to the include path and define
LZO_CFG_NO_CONFIG_HEADER=1, LZO_ABI_LITTLE_ENDIAN=1 and (MSVC only) the four
_CRT_* silencers; those defines are passed here. Its configure-style probes
(HAVE_*, SIZEOF_*) are not replicated: lzodefs.h detects MSVC and the
integer sizes itself. No source patch.

Exports. lzoconf.h routes every public function through LZO_PUBLIC, whose
__LZO_EXPORT1 hook is empty unless the builder defines it, so cl exports
nothing by itself. The MinGW build gets 108 (x86) / 96 (x64) exported
functions from libtool, which exports every global. link has no such mode, so
a .def is generated, outside the upstream tree, from the compiled objects:
a python step runs ``dumpbin /SYMBOLS`` over each .obj, keeps every defined
External function and writes lzo.def, stripping the cdecl leading underscore
on the 32-bit leg. That is the same rule as MinGW's - every non-static
function - rather than a hand-written list that could drift. Only functions
are taken ('()' in the type column); the few exported data objects
(``_lzo_version_string`` and the like) are not. The step asserts a non-empty
list and prints the count, which should be compared with the MinGW artefact's.

Flags, from the corpus mandates: /MD (the DLL runtime is imported, so the CRT
stays attributed to data/MSVC), /O2 (implies /Ob2 and /Gy), /Zi with an
explicit /Fd, no /GL and no /LTCG, and at link /DEBUG /Brepro /INCREMENTAL:NO
/OPT:NOREF /OPT:NOICF. These are as written in the build steps; they were not
read back from a tracker log. The MinGW build is -g -O2 without
--gc-sections, so NOREF/NOICF keeps the pair comparable.

Measurements, from the runner build (windows-2022, cl 19.44.35229, v143).
The build worked on the first dispatch. Function counts, kept after the MSVC
glue baseline removed 123 (x86) or 129 (x64) runtime functions, so kept plus
removed is the image total:

  x86 250 + 123 = 373     x64 250 + 129 = 379

(MinGW, for comparison: 164 / 155 kept.) Every kept function is named from the
PDB (0 unnamed). No runtime glue survives by name: the baseline took the
static CRT startup that /MD still links into a DLL (_DllMainCRTStartup,
dllmain_dispatch, __scrt_*, the __castguard_* stubs, SEH and GS-cookie
helpers, _initterm, atexit/onexit, the memset thunk), and everything left is
lzo code - the public lzo1x/lzo1y/... API plus upstream's file-local helpers
(swd_*, find_match, do_compress, code_match, ...) and lzo_bitops_* inlines.
MSVC keeps more of those helpers as separate functions than gcc -O2 does
(25 do_compress and 7 swd_accept bodies, against none under those names in
the MinGW artefact, where they are inlined or renamed by gcc), which is why it
has more functions from the same source.

Exports: 96 functions on both arches, equal to the MinGW x64 artefact's 96.
The MinGW x86 artefact exports 108; the 12 extra are exactly the x86-only
assembler entry points (lzo1c/1f/1x/1y_decompress_asm*), which this build,
compiling only src/*.c, does not have. Every other MinGW x86 export is
exported here too.

MinGW against MSVC PicHash overlap, functions of 10+ instructions (x86 /
x64): 0 shared, of 139 / 107 on the MinGW side and 204 / 196 on the MSVC
side. So this axis shares nothing with the MinGW one, which is the case for
building it. The --deep cross-family check on this family is clean (0).

miniLZO (backlog #59) is built as its own artefact: recipe
``lzo_minilzo_2.10_msvc`` (version ``minilzo-2.10``, component minilzo.dll),
minilzo.c from the minilzo-2.10 tarball pinned in lzo.py on the MinGW branch
(sha256 eb4ce543aad19533c83550746e0e9d7bcf716b35a42429e3ba17d60fa0f3e47a;
minilzo.c 213674 bytes, md5 c3d88dfeeabec417b0e3ed0f74e9e91f), compiled by one
cl line with the same flags and the same generated .def rule. Counted on the
runner (run 42676010529, v143), kept + removed = image total: x86 25 + 125 =
150, x64 25 + 131 = 156. Overlap with the full library built here: 8 of its 9
(x86) / 8 of 8 (x64) distinct PicHashes of 10+ instructions are in the full
build; with its MinGW counterpart 0 / 0.

Overlap with UltraVNC (data on branch claude/corpus-ultravnc-tightvnc, winvnc
1.8.3.2 MSVC): on x64 all 18 distinct PicHashes of miniLZO are in the UltraVNC
image, including all 8 functions of 10+ instructions (``lzo1x_1_compress``
147, ``lzo1x_1_compress_core`` 233, ``lzo1x_decompress`` 265,
``lzo1x_decompress_safe`` 369, ``lzo_adler32`` 131, ``_lzo_config_check`` 197,
``__lzo_init_v2`` 47, ``__lzo_align_gap`` 13 instructions), so UltraVNC's
vendored copy compiles to exactly this code at /O2 on x64. On x86 only 8 of
the 18 (all under 10 instructions) match and none of the large ones, so the
UltraVNC x86 image is not built with these flags. Against UltraVNC's MinGW
winvnc 1.8.3.1: 4 of 18, none of 10+ instructions.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Written as a python -c one-liner with no braces and no double quotes, so it
# survives both cmd.exe and the {placeholder} substitution. Only symbols that
# dumpbin lists as defined (SECTn) functions ("()") with External linkage are
# taken; UNDEF entries are CRT imports and are skipped.
_DEF = (
    'python -c "'
    "import subprocess,glob;"
    "o=''.join([subprocess.check_output(['dumpbin','/SYMBOLS',f]).decode() "
    "for f in sorted(glob.glob('*.obj'))]);"
    "l=[t[t.index('|')+1] for t in map(str.split,o.splitlines()) "
    "if '|' in t and '()' in t and 'External' in t "
    "and any([w.startswith('SECT') for w in t])];"
    "p='{arch}'=='x86';"
    "n=sorted(set([s[1:] if p and s.startswith('_') else s for s in l]));"
    "assert n,'no exports found';"
    "open('lzo.def','w').write('EXPORTS\\n'+'\\n'.join(n)+'\\n');"
    "print(len(n),'exports')"
    '"')

_COMPILE = ('cl /nologo /c /O2 /MD /Zi /Fdlzo2.pdb '
            '/Iinclude /I. /DLZO_CFG_NO_CONFIG_HEADER=1 '
            '/DLZO_ABI_LITTLE_ENDIAN=1 /D_CRT_NONSTDC_NO_DEPRECATE '
            '/D_CRT_NONSTDC_NO_WARNINGS /D_CRT_SECURE_NO_DEPRECATE '
            '/D_CRT_SECURE_NO_WARNINGS src\\*.c')

# /INCREMENTAL:NO because /DEBUG implies /INCREMENTAL and the /OPT:NO* forms
# do not suppress it; see sqlite3_msvc.py for the jump-thunk measurement.
# link expands the *.obj wildcard itself (lua_msvc.py relies on it).
_LINK = ('link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO '
         '/OPT:NOREF /OPT:NOICF /DEF:lzo.def '
         '/PDB:lzo2.pdb /OUT:lzo2.dll *.obj')

_FLAGS = ("/O2 /MD /Zi, -DLZO_CFG_NO_CONFIG_HEADER=1 -DLZO_ABI_LITTLE_ENDIAN=1 "
          "(src/*.c compiled directly); /DEBUG /Brepro /INCREMENTAL:NO "
          "/OPT:NOREF /OPT:NOICF at link; exports from a /DEF generated from "
          "the objects' defined external functions")


# miniLZO (backlog #59), the form UltraVNC vendors; pin and size in lzo.py on
# the MinGW branch. One translation unit, so the .def step globs the single
# minilzo.obj. Same flags as the full library, minus its include paths.
_MINI_COMPILE = ('cl /nologo /c /O2 /MD /Zi /Fdminilzo.pdb '
                 '/D_CRT_NONSTDC_NO_DEPRECATE /D_CRT_NONSTDC_NO_WARNINGS '
                 '/D_CRT_SECURE_NO_DEPRECATE /D_CRT_SECURE_NO_WARNINGS '
                 'minilzo.c')
_MINI_DEF = _DEF.replace("lzo.def", "minilzo.def")
_MINI_LINK = ('link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO '
              '/OPT:NOREF /OPT:NOICF /DEF:minilzo.def '
              '/PDB:minilzo.pdb /OUT:minilzo.dll minilzo.obj')

_MINILZO = Recipe(
    family="lzo",
    version="minilzo-2.10",
    upstream="https://www.oberhumer.com/opensource/lzo/",
    license="GPL-2.0-or-later",
    source=Source(
        url="https://www.oberhumer.com/opensource/lzo/download/minilzo-2.10.tar.gz",
        sha256="eb4ce543aad19533c83550746e0e9d7bcf716b35a42429e3ba17d60fa0f3e47a"),
    build=[
        BuildStep(_MINI_COMPILE),
        BuildStep(_MINI_DEF),
        BuildStep(_MINI_LINK),
        BuildStep("dir", allow_failure=True),
    ],
    artifacts=[Artifact(path="minilzo.dll", component="minilzo.dll",
                        pdb="minilzo.pdb")],
    toolchains=["msvc_x86", "msvc_x64"],
    build_flags=("/O2 /MD /Zi (minilzo.c compiled directly); /DEBUG /Brepro "
                 "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link; exports "
                 "from a /DEF generated from the object's defined external "
                 "functions"),
    notes="miniLZO 2.10, the lzo1x subset vendored byte-identically in "
          "UltraVNC (minilzo.c 213674 bytes), built from the minilzo-2.10 "
          "tarball. Upstream is unpatched; exports are generated from the "
          "compiled object. Built against the DLL runtime.",
)


RECIPES = {
    "lzo_minilzo_2.10_msvc": _MINILZO,
    "lzo_2.10_msvc": Recipe(
        family="lzo",
        version="2.10",
        upstream="https://www.oberhumer.com/opensource/lzo/",
        license="GPL-2.0-or-later",
        # The same tarball and digest the MinGW recipe pins.
        source=Source(
            url="https://www.oberhumer.com/opensource/lzo/download/lzo-2.10.tar.gz",
            sha256="c0f892943208266f9b6543b3ae308fab6284c5c90e627931446fb49b4221a072"),
        build=[
            BuildStep(_COMPILE),
            BuildStep(_DEF),
            BuildStep(_LINK),
            BuildStep("dir", allow_failure=True),
        ],
        artifacts=[Artifact(path="lzo2.dll", component="lzo2.dll",
                            pdb="lzo2.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS,
        notes="Full liblzo2, the same source set as the MinGW recipe. "
              "Upstream is unpatched; the export table is generated at build "
              "time from the compiled objects because lzoconf.h exports "
              "nothing under cl. Built against the DLL runtime, so the MSVC "
              "C runtime is imported rather than linked in and stays "
              "attributed to data/MSVC. Named lzo2.dll rather than the MinGW "
              "build's liblzo2-2.dll; same library, same release.",
    ),
}
