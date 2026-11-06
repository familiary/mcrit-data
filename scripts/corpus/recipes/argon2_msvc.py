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
    x86           83       137      220
    x64           82       140      222

Removed: DllMain and the static vcruntime startup (_DllMainCRTStartup,
__scrt_*, __castguard_*, __security_*, __report_*), SEH helpers, CRT memory
and string routines (malloc, free, calloc, memcpy, memset, strlen, strncmp)
and kernel32 import thunks. Survivors that are not Argon2 code, by name and
PicHash:

  * import thunks, one instruction each, all PicHash 1253497258561142223:
    x86 _WaitForSingleObject@8, __beginthreadex, __endthreadex; x64
    WaitForSingleObject, _beginthreadex, _endthreadex. Below the 10
    instruction floor of the cross-family check.
  * RtlSecureZeroMemory, the winnt.h inline behind SecureZeroMemory (used by
    clear_internal_memory): 11 instructions, PicHash 3164917767828542777 on
    x86; 9, 4269566191566944164 on x64.
  * sprintf (x86 only), the UCRT stdio inline wrapper compiled into
    encoding.c: 18 instructions, PicHash 17914501890890951995.
  No unnamed function survives in either image. The other 77 (x86) / 76 (x64)
  kept functions are Argon2's own.

MinGW against MSVC, PicHash overlap over functions of 10 instructions or
more (same tag, same arch):

                 mingw / msvc    shared
    x86            56 / 58          0
    x64            53 / 54          0

Disjoint, as with Jansson: the two compilers share no exact function body, so
a cl-built Argon2 is only matched by this axis.
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
