"""NTTITON's Heaven's Gate demonstration - MSVC only, x86 only.

A fifth WOW64-transition family beside wow64pp, wowGrail, RtlWow64 and
HeavensGate2, and the one written the way the technique is usually written:
five functions are ``__declspec(naked)`` with a full ``__asm { }`` body and
two more embed ``__asm`` blocks inside ordinary C. The far-call itself is
emitted a byte at a time through ``#define EMIT(a) __asm __emit (a)``
(Heavens Gate.h:4), which is how a 64-bit instruction gets into a 32-bit
translation unit that the assembler would otherwise refuse. Where
HeavensGate2 and RtlWow64 keep the gate in a byte array that is patched and
executed at run time, here it is in the instruction stream of the functions
themselves, which is a different thing for a matcher to see.

SCOPE. Only the ``Heavens Gate/`` subdirectory is built - two files,
``Heavens Gate.c`` (443 lines) and ``Heavens Gate.h`` (74 lines) - and
nothing else in this repository is compiled, copied, referenced or recorded.
That subdirectory is a self-contained demonstration of the technique and is
the only part the wishlist issue asks for. The rest of the repository is
working offensive malware: a browser-credential formgrabber with command and
control, hooking and injection, a PE infector and a process dumper. None of
it belongs in a reference corpus, and this recipe's compile step names its
one translation unit explicitly rather than globbing a directory, so nothing
can be pulled in by accident.

MSVC only, and not as a preference. ``__emit`` is an MSVC intrinsic with no
GCC equivalent, GCC has no working ``naked`` attribute on x86 at all, and
the ``__asm { }`` bodies are Intel syntax against a GCC that wants AT&T or a
basic-asm string. There is no partial port here; the file is unbuildable
outside MSVC.

x86 only, and this one is a hard limit of the compiler rather than of the
code: MSVC supports no inline assembly at all on x64, and
``__declspec(naked)`` is unsupported there as well. Seven of the eleven
functions are inline assembly. As with the other gates, there is also
nothing for it to do on x64.

There is no build system anywhere in the repository - no .vcxproj, no .sln,
no Makefile, no CMakeLists - so the compile and link lines below are this
recipe's own rather than upstream's, and build_flags says so. The directory
name contains a space, which is why the source path is quoted.

Eleven functions: memcpy64, GetPEB64, m_memcmp, GetImageBase,
GetModuleHandle64, GetNextArgument, CallFunction64, strlen64,
GetProcAddress64, SysCall64, and main. That clears
config.MIN_USEFUL_FUNCTIONS (8) by three, and two of the eleven -
``SysCall64`` and ``GetImageBase`` - are defined but never called from
anywhere in the file. Dropping them would leave nine, still over the floor
but pointlessly poorer, so the compile is /Od (no /Gy, hence no per-function
COMDATs to discard) and the link passes /OPT:NOREF. /OPT:REF must not be
added here.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# .c, so cl compiles it as C without /TC being asked for, which is what the
# __asm and __declspec(naked) bodies were written against. The include of
# "Heavens Gate.h" is quoted and resolves next to the source file, so no /I
# is needed.
#
# /Od: two of the eleven functions are never called and inlining is the other
# way to lose one, so nothing here is optimised. It also keeps
# GetNextArgument - a nine-line helper called eight times from two callers,
# which /O2 would inline at every site - as a function of its own.
#
# /MD, not cl's default /MT. The file calls printf and links the CRT for it;
# a static CRT put 1947 of VX-API's 4219 functions into that artefact as MSVC
# runtime, duplicating data/MSVC, which is this corpus's reference for
# exactly that code. With /MD the CRT stays in ucrtbase and only the startup
# glue is in the image, where the glue filter deals with it.
#
# /Zi with an /Fd of its own: MSVC keeps symbols in a PDB rather than in a
# COFF symbol table, and the compiler PDB has to be a different file from the
# linker PDB or link.exe writes the file it is reading type information from.
_COMPILE = ('cl /nologo /c /Od /MD /Zi /W3 '
            '/FdHeavensGate.compiler.pdb /FoHeavensGate.obj '
            '"Heavens Gate\\Heavens Gate.c"')

# /INCREMENTAL:NO is mandatory and is the most common way these builds fail:
# /DEBUG implies /INCREMENTAL, /OPT:NOREF and /OPT:NOICF do not suppress it,
# and an incrementally linked image reaches every function through a table of
# one-instruction jump thunks that SMDA recovers as functions in their own
# right - smdaify.assert_not_incrementally_linked refuses a run of more than
# 32 of them.
#
# /OPT:NOREF keeps SysCall64 and GetImageBase, which nothing calls;
# /OPT:NOICF stops identical-COMDAT folding, which is on by default in a
# release link.
#
# /Brepro drops the link timestamp so two runs give identical sha256s.
#
# kernel32.lib is named for OpenProcess and CloseHandle. The CRT's own import
# libraries come in through the object's /DEFAULTLIB directives, which are
# honoured here - unlike in heavensgate2.py, whose project suppresses them.
_LINK = ('link /nologo /DEBUG /Brepro /INCREMENTAL:NO '
         '/OPT:NOREF /OPT:NOICF /SUBSYSTEM:CONSOLE '
         '/PDB:HeavensGate.pdb /OUT:HeavensGate.exe '
         'HeavensGate.obj kernel32.lib')


RECIPES = {
    # No tags; upstream has never released. The pin is the full commit hash
    # of master as of 2017-06-16 and the version string is that date.
    "NTTITONHeavensGate_2017-06-16": Recipe(
        # URL-safe and short: Recipe.slug() refuses a space or a bracket, and
        # the upstream repository is called "Malware", which names neither
        # this code nor anything a corpus family should be called.
        family="NTTITONHeavensGate",
        version="2017-06-16",
        upstream="https://github.com/NTTITON/Malware - the Heavens Gate "
                 "subdirectory only; nothing else in that repository is "
                 "built or recorded here",
        # No LICENSE or COPYING file, and not one copyright or licence line
        # in any file in the repository - checked across the whole tree, not
        # just the built subdirectory. The README is one line and says
        # nothing about terms. "none" is the fact; this field is copied
        # verbatim into provenance.json.
        license="none",
        source=Source(git_url="https://github.com/NTTITON/Malware.git",
                      git_ref="acbe25a3169eee6be3f54c28dd0c0e1eb4cbdbb4"),
        build=[BuildStep(_COMPILE), BuildStep(_LINK)],
        # HeavensGate.exe is this recipe's name for the image, since upstream
        # ships no build system and therefore no target name. It has no space
        # in it, which Recipe.slug() requires of anything that becomes a
        # filename and then a markdown link.
        artifacts=[
            Artifact(path="HeavensGate.exe", component="HeavensGate.exe",
                     pdb="HeavensGate.pdb"),
        ],
        # x86 only; MSVC has no inline assembly on x64 and seven of the
        # eleven functions are inline assembly.
        toolchains=["msvc_x86"],
        build_flags="/Od /MD /Zi /W3, compiled as C; link /DEBUG /Brepro "
                    "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF /SUBSYSTEM:CONSOLE "
                    "against kernel32.lib. Upstream ships no build system of "
                    "any kind, so every flag here is this recipe's choice "
                    "rather than a project setting",
        notes="Only the \"Heavens Gate\" subdirectory of this repository is "
              "built: Heavens Gate.c and Heavens Gate.h, a self-contained "
              "demonstration of the 32-to-64-bit transition. The rest of the "
              "repository is offensive malware - a browser-credential "
              "formgrabber with C2, hooking and injection, a PE infector and "
              "a process dumper - and none of it is compiled, referenced or "
              "present in this corpus. No licence of any kind: no LICENSE or "
              "COPYING file and no copyright notice in any file. Eleven "
              "functions, against a floor of eight, of which SysCall64 and "
              "GetImageBase are defined but never called and survive only "
              "because the build is /Od and the link passes /OPT:NOREF. "
              "Seven of the eleven are inline assembly - memcpy64, GetPEB64, "
              "m_memcmp, GetImageBase and strlen64 are __declspec(naked) "
              "with a full __asm body, and CallFunction64 and SysCall64 "
              "embed __asm blocks - so this artefact is largely hand-written "
              "code that a compiler did not choose the instructions for, "
              "which is what makes it recognisable and also what makes it "
              "MSVC-only and x86-only. The far-call sequence itself is "
              "emitted byte by byte through __asm __emit, so the gate is in "
              "the instruction stream here rather than in data as it is in "
              "HeavensGate2. Built against the DLL runtime, so the MSVC C "
              "runtime is imported rather than linked in and stays "
              "attributed to data/MSVC.",
    ),
}
