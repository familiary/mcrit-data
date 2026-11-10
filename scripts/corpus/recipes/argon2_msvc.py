"""Argon2 built with MSVC, beside the MinGW build of the same tag.

Argon2 is vendored into Windows software built with cl at least as often as
with gcc (the upstream repository ships a Visual Studio 2015 solution), and
data/argon2 held MinGW artefacts only. The two compilers lay the same source
out differently, hence this axis. Same pin as argon2.py (tag 20190702, commit
62358ba2123abd17fccf2a108a301d4b52c01a7c), so each MinGW/MSVC pair differs by
compiler and nothing else on the source side. A separate registry entry, for
the reason in sqlite3_msvc.py: one Recipe has one build list and these steps
are cmd.exe.

Decisions:

* **Direct cl, not the vs2015 solution.** The Makefile cannot be used under
  cl, and the solution (Argon2OptDll.vcxproj) would need a
  ForceImportBeforeCppTargets props file to impose the corpus mandates. The
  project is only six translation units, so one ``cl /LD`` over the same six
  files (argon2.c, core.c, blake2/blake2b.c, thread.c, encoding.c, opt.c -
  its ClCompile list) is simpler and shows the flags in the log. Nothing is
  patched and no file is written into the upstream tree: ``ARGON2_PUBLIC`` is
  ``__declspec(dllexport)`` under ``_MSC_VER`` (include/argon2.h), so the API
  is exported without a .def file.
* **opt.c**, as in the MinGW recipe (and as the upstream VS project does).
* **Flags.** The project's Release settings are /O2 (MaxSpeed), /Oi, /Gy and
  /sdl, kept; /MD is used instead of cl's default /MT (a static CRT would put
  the C runtime into the image); /Zi for the PDB; /D_CRT_SECURE_NO_WARNINGS
  as the project has it. Link: /INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF
  /OPT:NOICF (the project's own /OPT:REF /OPT:ICF are deliberately not used);
  no /GL, no /LTCG. Read back from the runner's log (windows-2022, MSVC
  19.44.35229), the command line is exactly _BUILD below.
* **Instruction-set baseline: SSE2 on both, same as the MinGW artefacts.** No
  /arch is given. cl defines none of __SSSE3__, __AVX2__, __AVX512F__ or
  __XOP__ (GCC-style macros), so opt.c and blamka-round-opt.h take their
  ``#else /* SSE2 */`` paths whatever the host CPU is; and cl's default is
  SSE2 on x86 (VS2022) and x64 (where SSE2 is architectural). MinGW pins
  -march=pentium4 / x86-64 for the same SSE2 path. Checked on the disassembly
  of all four images: no VEX (v*) instruction and no pshufb/palignr in any;
  pmuludq and paddq present in all. So the MinGW/MSVC difference is code
  generation only, not instruction set.
* Threads are on: thread.c uses _beginthreadex under _WIN32, so no pthread DLL.

Counted on the windows-2022 runner, kept + removed = image total (removed is
the baseline's compiler-runtime filter):

                kept    removed    image
    x86           82       138      220
    x64           82       140      222

Removed: DllMain and the static vcruntime startup (_DllMainCRTStartup,
__scrt_*, __castguard_*, __security_*, __report_*), SEH helpers, CRT memory
and string routines (malloc, free, calloc, memcpy, memset, strlen, strncmp,
sprintf on x86), and kernel32 import thunks. Survivors that are not Argon2
code, by name and PicHash:

  * import thunks, one instruction each, all PicHash 1253497258561142223:
    x86 _WaitForSingleObject@8, __beginthreadex, __endthreadex; x64
    WaitForSingleObject, _beginthreadex, _endthreadex. Below the 10
    instruction floor of the cross-family check.
  * RtlSecureZeroMemory, the winnt.h inline behind SecureZeroMemory (used by
    clear_internal_memory): 11 instructions, PicHash 3164917767828542777 on
    x86; 9, 4269566191566944164 on x64.
  * sprintf (x86 only) was the UCRT stdio inline wrapper compiled into
    encoding.c (18 instructions, PicHash 17914501890890951995); the wide-stdio
    glue baseline now removes it, so it is no longer a survivor.
  No unnamed function survives in either image. The other 78 (x86) / 78 (x64)
  kept functions are Argon2's own.

MinGW against MSVC, PicHash overlap over functions of 10 instructions or
more (same tag, same arch):

                 mingw / msvc    shared
    x86            56 / 57          0
    x64            53 / 54          0

Disjoint, as with Jansson: the two compilers share no exact function body, so
a cl-built Argon2 is only matched by this axis.

Overlap with data/libsodium (PicHash, functions of 10 instructions or more,
re-measured from the committed exports): the MSVC x64 image shares 4 PicHashes
with both libsodium MSVC x64 builds (1.0.18 and 1.0.20): ``load_block`` and
``store_block`` (one hash), ``decode_decimal``, ``b64_byte_to_char`` and
``b64_char_to_byte``. The MSVC x86 image shares none with the MSVC x86
libsodium builds, and the MinGW libsodium images share nothing with it. The
MinGW images of this family share only the unnamed 15-instruction MinGW
runtime routine with the MinGW libsodium images. libsodium has 57 to 70
Argon2-named functions per image (14 to 28 of 10 instructions or more) and no
Argon2d.

Second pass (scoped run 42776861712), two more versions beside the images
above, which are unchanged. ``20190702-ref``: the same tag through upstream's
vs2015/Argon2RefDll project (src/ref.c instead of src/opt.c), x86 83 + 137 =
220, x64 83 + 139 = 222 (kept + removed = total, no exclusions); against the
opt.c build 54 of 57 (x86) and 51 of 54 (x64) PicHashes of ten instructions or
more are shared, fill_block and fill_segment being the difference.
``randomx-6fe0e39``: the Argon2d subset tevador/RandomX vendors (argon2_core,
argon2_ref, argon2_ssse3, argon2_avx2 and blake2b at commit 6fe0e39, names
prefixed randomx_), x86 43 + 128 = 171, x64 43 + 129 = 172; it shares 8 of its
26 (x86) and 7 of its 24 (x64) hashes with the opt.c and the ref.c images
(BLAKE2b and index_alpha), so the RandomX shape of Argon2d is its own
reference.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# The six translation units of upstream's own Argon2OptDll project
# (vs2015/Argon2OptDll/Argon2OptDll.vcxproj ClCompile list), in one cl
# invocation so /Fd names the single compiler PDB the linker turns into
# libargon2.pdb.
_SOURCES = ("src\\argon2.c src\\core.c src\\blake2\\blake2b.c src\\thread.c "
            "src\\encoding.c src\\opt.c")

# /O2 /Oi /Gy /sdl are the project's Release settings (MaxSpeed,
# IntrinsicFunctions, FunctionLevelLinking, SDLCheck), /MD replaces the cl
# default /MT, /Zi is for the PDB. -I include because the sources use
# "argon2.h". /LD builds a DLL; ARGON2_PUBLIC is __declspec(dllexport) under
# _MSC_VER, so no .def file is needed.
_BUILD = ('cl /nologo /LD /O2 /Oi /Gy /sdl /MD /Zi /Iinclude '
          '/D_CRT_SECURE_NO_WARNINGS /Fdlibargon2.pdb /Felibargon2.dll '
          + _SOURCES +
          ' /link /INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF')


RECIPES = {
    "argon2_20190702_msvc": Recipe(
        family="argon2",
        version="20190702",
        upstream="https://github.com/P-H-C/phc-winner-argon2",
        license="CC0-1.0 OR Apache-2.0",
        source=Source(git_url="https://github.com/P-H-C/phc-winner-argon2.git",
                      git_ref="20190702"),
        build=[
            BuildStep(_BUILD),
            BuildStep("dir", allow_failure=True),
        ],
        artifacts=[Artifact(path="libargon2.dll", component="libargon2.dll",
                            pdb="libargon2.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /Oi /Gy /sdl /MD /Zi (the vs2015 Release project's "
                    "settings), src/opt.c; /DEBUG /Brepro /OPT:NOREF "
                    "/OPT:NOICF at link",
        notes="Same tag as the MinGW recipe, opt.c, SSE2 baseline. See the "
              "recipe docstring.",
    ),
}


# --- The ref.c build (upstream's Argon2RefDll project: the same six units
# with src\ref.c in place of src\opt.c and the same Release settings) and
# RandomX's vendored Argon2d subset (see argon2.py), with RandomX's MSVC
# flags for the SIMD units (/arch:AVX2 on argon2_avx2.c; SSSE3 needs no
# switch under cl on x64 and is the SSE2-baseline intrinsic path on x86).
# Separate versions so the committed images are unchanged.
_REF_BUILD = _BUILD.replace("src\\opt.c", "src\\ref.c")

RECIPES["argon2_20190702-ref_msvc"] = Recipe(
    family="argon2",
    version="20190702-ref",
    upstream="https://github.com/P-H-C/phc-winner-argon2",
    license="CC0-1.0 OR Apache-2.0",
    source=Source(git_url="https://github.com/P-H-C/phc-winner-argon2.git",
                  git_ref="20190702"),
    build=[BuildStep(_REF_BUILD), BuildStep("dir", allow_failure=True)],
    artifacts=[Artifact(path="libargon2.dll", component="libargon2.dll",
                        pdb="libargon2.pdb")],
    toolchains=["msvc_x86", "msvc_x64"],
    build_flags="/O2 /Oi /Gy /sdl /MD /Zi (the vs2015 Argon2RefDll Release "
                "settings), src/ref.c; /DEBUG /Brepro /OPT:NOREF /OPT:NOICF "
                "at link",
    notes="Same tag, the six translation units of upstream's "
          "vs2015/Argon2RefDll project (src/ref.c instead of src/opt.c), "
          "built with that project's Release settings and /MD. Nothing "
          "patched.",
)

_RX_SRC = "src\\argon2_core.c src\\argon2_ref.c src\\blake2\\blake2b.c"
RECIPES["argon2_randomx-6fe0e39_msvc"] = Recipe(
    family="argon2",
    version="randomx-6fe0e39",
    upstream="https://github.com/tevador/RandomX",
    license="BSD-3-Clause (RandomX); the Argon2 code is CC0-1.0 OR "
            "Apache-2.0 upstream",
    source=Source(git_url="https://github.com/tevador/RandomX.git",
                  git_ref="6fe0e390acc28a50bfe7f59603c2a6effae4a7cd"),
    build=[
        BuildStep("cl /nologo /c /O2 /Oi /MD /Zi /Fdrandomx-argon2.pdb %s"
                  % _RX_SRC),
        BuildStep("cl /nologo /c /O2 /Oi /MD /Zi /Fdrandomx-argon2.pdb "
                  "src\\argon2_ssse3.c"),
        BuildStep("cl /nologo /c /O2 /Oi /MD /Zi /arch:AVX2 "
                  "/Fdrandomx-argon2.pdb src\\argon2_avx2.c"),
        BuildStep('python -c "'
                  "import subprocess,glob;"
                  "o=''.join([subprocess.check_output(['dumpbin','/SYMBOLS',f]).decode() "
                  "for f in sorted(glob.glob('*.obj'))]);"
                  "l=[t[t.index('|')+1] for t in map(str.split,o.splitlines()) "
                  "if '|' in t and '()' in t and 'External' in t "
                  "and any([w.startswith('SECT') for w in t])];"
                  "p='{arch}'=='x86';"
                  "n=sorted(set([s[1:] if p and s.startswith('_') else s for s in l]));"
                  "assert n,'no exports found';"
                  "open('randomx-argon2.def','w').write('EXPORTS\\n'+'\\n'.join(n)+'\\n');"
                  "print(len(n),'exports')"
                  '"'),
        BuildStep("link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO "
                  "/OPT:NOREF /OPT:NOICF /DEF:randomx-argon2.def "
                  "/PDB:randomx-argon2.pdb /OUT:randomx-argon2.dll "
                  "argon2_core.obj argon2_ref.obj blake2b.obj "
                  "argon2_ssse3.obj argon2_avx2.obj"),
        BuildStep("dir", allow_failure=True),
    ],
    artifacts=[Artifact(path="randomx-argon2.dll",
                        component="randomx-argon2.dll",
                        pdb="randomx-argon2.pdb")],
    toolchains=["msvc_x86", "msvc_x64"],
    build_flags="/O2 /Oi /MD /Zi, /arch:AVX2 on argon2_avx2.c; /DEBUG "
                "/Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link, "
                "exports from a .def generated from the objects",
    notes="The Argon2d subset tevador/RandomX vendors (commit 6fe0e39), the "
          "five files compiled with cl and linked into one DLL with a .def "
          "generated from the objects' defined external functions. Filed "
          "under argon2 as Argon2's code in the form RandomX carries it. "
          "Nothing patched.",
)
