"""Detours built with MSVC, three ways: the commit at /O2, v4.0.1 at /O2, and
the commit as upstream's own Makefile builds it.

Detours is MSVC-native - the issue calls MSVC the lineage and MinGW an
addition - and this is where the family matters most. See detours.py for what
the library is, why it is here and why the objects go into a DLL, and for the
MinGW build, which is only one of two renderings of the same commit.

Three builds, and the reason for each is the measured PicHash overlap at the
ten-instruction floor between them (x64, with x86 within one hash of the same
picture): the commit at /O2 has 164 distinct hashes, v4.0.1 at /O2 has 145,
the Makefile build has 205, the MinGW build 117, and the only overlap anywhere
is 55 (x86 56) between the commit and v4.0.1 at /O2. The Makefile build shares
nothing with either /O2 build, and no MinGW build shares anything with an MSVC
one. So each leg is its own reference and none duplicates another.

  Detours_2026-09-29_msvc        cl /O2 /MD of the pinned commit, seven
                                 objects linked into a DLL. The counterpart of
                                 the MinGW -O2 build.
  Detours_4.0.1_msvc             the same command line over the v4.0.1 tag
                                 (2018-04-06, MIT). The tagged release, and
                                 the one the nuget and vcpkg packages carry,
                                 so the likeliest to match a sample that
                                 vendors it. It has no EVEX or REX2 copiers.
  Detours_2026-09-29-nmake_msvc  `nmake` run in src/ exactly as upstream's
                                 README and vc/Detours.vcxproj do (the
                                 vcxproj is a Makefile project that calls the
                                 same nmake), with upstream's own flags:
                                 /W4 /WX /Zi /MT /Gy /Zl /Od. Then the seven
                                 objects it left in src\\obj.<ARCH> are linked
                                 into the DLL. This is what a consumer who
                                 built Detours the documented way ships, and
                                 it is an unoptimised build: upstream's
                                 Makefile has no other configuration, so
                                 /Od is not this recipe's choice. Its version
                                 string carries -nmake so the file names do
                                 not collide with the /O2 build of the same
                                 commit.

Linking. cl compiles seven translation units into objects, link makes a DLL
of them: /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF, so the PE is
reproducible, nothing is reached through an incremental thunk table, and
functions nothing references (most of the API) survive. /Gy is upstream's own
and puts each function in its own COMDAT, which /OPT:NOREF then keeps. The
Makefile build compiles with /Zl, which leaves no default-library directive in
the objects, so that leg names msvcrt.lib, vcruntime.lib and ucrt.lib on the
link line itself; /MT in upstream's CFLAGS therefore has no effect on what is
linked, only on what the headers declare.

Measured (kept + removed = total; ten instructions or more in brackets):

  commit /O2        x86 321 + 174 = 495 (221)    x64 324 + 181 = 505 (218)
  v4.0.1 /O2        x86 287 + 173 = 460 (197)    x64 290 + 180 = 470 (198)
  commit nmake /Od  x86 382 + 171 = 553 (284)    x64 332 + 176 = 508 (276)

Every kept function is named (PDB symbols). The removed ones are MSVC runtime
that /MD still links statically. Detours' own code is the CDetourDis*, CImage*,
Detour* and detour_* functions.

Glue survivors, by name and PicHash, that the measured baseline does not
remove. StringCchPrintfA and StringCchPrintfW are strsafe.h inline functions
from the Windows SDK compiled into detours.cpp, so any consumer carries them:
/O2 commit and v4.0.1 x64 14609153554826729091 and 11995049151350133856, x86
5167829856593231400 and 17855045609201516648; nmake build x64
5028736481919831228 and 3143614553131410775, x86 17713316887944295158 and
6400887483420132758. The unoptimised build additionally kept the UCRT stdio
inline wrappers /Od does not fold away: _vsnprintf and _vsnwprintf (x64
17774970396563084508, x86 7719431429195281600), _vsnprintf_l and
_vsnwprintf_l (x64 11262974418567998103, x86 15628369269008054154) and, on x86
only, __local_stdio_printf_options (5181772436194851115). The wide-stdio glue
baseline now removes _vsnwprintf on x64, and _vsnprintf, _vsnwprintf and
__local_stdio_printf_options on x86; _vsnprintf on x64 and the _l pair on both
architectures still survive. _vsnprintf and _vsnwprintf share one PicHash
because they are the same body.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_OBJS = "detours modules disasm image creatwth disolx86 disolx64".split()

_COMMIT = "1dbd4ea281d73d478aa8d09a8b83fbd265f715f7"

# /Fd names the compiler PDB; the linker PDB is /PDB:detours.pdb and is the one
# declared on the Artifact, the compiler one being the file the linker reads
# its type information from. /Gy /Gm- /DWIN32_LEAN_AND_MEAN
# /D_WIN32_WINNT=0x501 /DDETOUR_DEBUG=0 are the Makefile's own; /W4 /WX are not
# repeated because they gate nothing in the output.
_COMPILE = ("cl /nologo /c /O2 /MD /Zi /Gy /Gm- /DWIN32_LEAN_AND_MEAN "
            "/D_WIN32_WINNT=0x501 /DDETOUR_DEBUG=0 /Fddetours.compiler.pdb "
            + " ".join("src\\%s.cpp" % o for o in _OBJS))
_LINK = ("link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF "
         "/OPT:NOICF /PDB:detours.pdb /OUT:detours.dll "
         + " ".join(o + ".obj" for o in _OBJS) + " kernel32.lib")

# Upstream's own build, run where its README says to run it. The objects
# land in src\obj.X64 or src\obj.X86 - DETOURS_TARGET_PROCESSOR comes from
# VSCMD_ARG_TGT_ARCH, which the developer environment sets - and the three
# objects that are not linked (ia64, arm, arm64) are built and left there.
# /Zl objects carry no default library, hence the explicit CRT libraries.
_NMAKE = "nmake /nologo"
_LINK_NMAKE = ("link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF "
               "/OPT:NOICF /PDB:detours.pdb /OUT:detours.dll "
               + " ".join("src\\obj.{arch}\\%s.obj" % o for o in _OBJS)
               + " msvcrt.lib vcruntime.lib ucrt.lib kernel32.lib")

_LICENSE = "MIT, Copyright (c) Microsoft Corporation"
_UPSTREAM = "https://github.com/microsoft/Detours"
_GIT = "https://github.com/microsoft/Detours.git"


def _direct(version, ref, notes):
    return Recipe(
        family="Detours", version=version, upstream=_UPSTREAM,
        license=_LICENSE,
        source=Source(git_url=_GIT, git_ref=ref),
        build=[BuildStep(_COMPILE), BuildStep(_LINK)],
        artifacts=[Artifact(path="detours.dll", component="detours.dll",
                            pdb="detours.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi /Gy /Gm- /DWIN32_LEAN_AND_MEAN "
                    "/D_WIN32_WINNT=0x501 /DDETOUR_DEBUG=0; /DEBUG /Brepro "
                    "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link",
        notes=notes)


def _nmake(version, ref):
    return Recipe(
        family="Detours", version=version, upstream=_UPSTREAM,
        license=_LICENSE,
        source=Source(git_url=_GIT, git_ref=ref),
        build=[BuildStep(_NMAKE, cwd="src"),
               BuildStep("dir src\\obj.{arch}", allow_failure=True),
               BuildStep(_LINK_NMAKE)],
        artifacts=[Artifact(path="detours.dll", component="detours.dll",
                            pdb="detours.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="upstream src/Makefile unchanged: /W4 /WX /Zi /MT /Gy "
                    "/Gm- /Zl /Od, /DWIN32_LEAN_AND_MEAN "
                    "/D_WIN32_WINNT=0x501 /DDETOUR_DEBUG=0; the seven x86/x64 "
                    "objects are then linked with /DEBUG /Brepro "
                    "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF against "
                    "msvcrt.lib vcruntime.lib ucrt.lib",
        notes="The same commit as the /O2 build, compiled the way upstream "
              "documents: nmake in src/, whose Makefile hardcodes /Od /MT /Zl "
              "and has no release configuration, so this is an unoptimised "
              "build by upstream's own choice and describes a consumer who "
              "built Detours as shipped. The Makefile also builds the "
              "Itanium, ARM and ARM64 objects; the seven x86 and x64 ones "
              "are linked into a DLL here, because upstream's static "
              "detours.lib cannot be read. Measured: x86 382 functions kept "
              "of 553 (171 MSVC runtime removed), x64 332 of 508 (176), 284 "
              "and 276 of them ten instructions or more, all named. The "
              "PicHash overlap with the /O2 build, the v4.0.1 build and the "
              "MinGW build is zero at the ten-instruction floor on both "
              "architectures. Unoptimised code keeps the UCRT stdio inline "
              "wrappers (_vsnprintf, _vsnwprintf and their _l forms, and "
              "__local_stdio_printf_options on x86) that the optimiser "
              "folds away in the other builds; they are SDK code, not "
              "Detours'. The wide-stdio glue baseline removes _vsnwprintf "
              "on x64 and _vsnprintf, _vsnwprintf and "
              "__local_stdio_printf_options on x86; _vsnprintf on x64 and "
              "the _l forms on both architectures survive.")


RECIPES = {
    "Detours_2026-09-29_msvc": _direct(
        "2026-09-29", _COMMIT,
        "Commit 1dbd4ea of microsoft/Detours, 2026-09-29, built /O2 /MD as "
        "seven objects linked into a DLL (upstream's static detours.lib "
        "cannot be read); the MSVC counterpart of the MinGW build of the "
        "same commit. Measured: x86 321 functions kept of 495 (174 MSVC "
        "runtime removed), x64 324 of 505 (181), 221 and 218 of them ten "
        "instructions or more, all named. PicHash overlap at the "
        "ten-instruction floor: zero with the MinGW build and zero with the "
        "Makefile build, 55 (x86 56) with v4.0.1. The strsafe.h inline "
        "wrappers StringCchPrintfA/W are Windows SDK code and survive the "
        "glue filter."),
    "Detours_4.0.1_msvc": _direct(
        "4.0.1", "v4.0.1",
        "The v4.0.1 tag (2018-04-06, MIT), the last tagged release and what "
        "the nuget and vcpkg packages carry, built with the same command "
        "line as the 2026-09-29 /O2 build. It predates the EVEX and REX2 "
        "copiers. Measured: x86 287 functions kept of 460 (173 MSVC runtime "
        "removed), x64 290 of 470 (180), 197 and 198 of them ten "
        "instructions or more, all named. 55 of its 145 distinct x64 hashes "
        "(x86 56 of 149) are also in the /O2 build of the later commit and "
        "none is in the Makefile or MinGW builds. Not built with MinGW: "
        "v4.0.1's detours.h does not compile under GCC."),
    "Detours_2026-09-29-nmake_msvc": _nmake(
        "2026-09-29-nmake", _COMMIT),
}
