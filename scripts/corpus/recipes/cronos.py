"""Cronos (Idov31) - sleep obfuscation via waitable timers and a ROP chain.

The waitable-timer variant of the technique, beside Ekko (timer queues) and
Foliage (APCs). It captures a context by handing RtlCaptureContext to
SetWaitableTimer as the completion routine, clones it into four frames for
VirtualProtect, SystemFunction032, SystemFunction032 and VirtualProtect, arms
four timers at staggered due times, and then hands control to a hand-written
ROP chain so the thread's own return address is not on any module a scanner
will walk.

Seven functions, which is the whole project:

    src/Main.c       main
    src/Utils.c      bCompare, findPattern, findInModule, findGadget
    src/Cronos.c     CronosSleep
    src/asm/rop.asm  QuadSleep

``min_functions`` is 7, the count that was measured. ``InitializeTimerMs`` is
a macro in headers/Cronos.h, not a function, and the ``end`` label inside
``QuadSleep`` is a two-instruction ``add rsp, 0x28; ret`` tail - a branch
target rather than a routine, and below the ten-instruction floor the
cross-family census counts at even where SMDA recovers it separately. Neither
is counted.

What is actually worth having here is not the timer code. ``CronosSleep`` is
the technique and is the obvious body, but the gadget search - walk the loaded
modules with EnumProcessModules, parse each one's first section header, and
scan it for ``\\x59\\xC3`` (pop rcx; ret), ``\\x5A\\xC3`` (pop rdx; ret) and
``\\x48\\x83\\xC4\\x20\\x5F\\xC3`` (add rsp, 0x20; pop rdi; ret) - is a
pattern-scanner shape that propagates into other tooling far more often than
the sleep trick does. ``bCompare`` and ``findPattern`` are the classic
masked-signature-scan pair.

**Built with MinGW although upstream builds with cl, and that deviation is
the one thing to read before trusting this artefact.** Upstream's makefile
drives ``cl``, so an MSVC artefact is what a sighting of this project would
most likely match. It is not built that way here because it cannot be, on
this repository's own runner: ``src/asm/rop.asm`` is NASM syntax
(``[BITS 64]``, ``[SECTION .text]``, ``GLOBAL``), ml64 will not assemble it,
and nasm is absent from the windows-2022 image - openssl_msvc.py already
records that "windows-2022's toolset manifest does not list NASM", and
syswhispers.py records the mirror-image problem, that MASM syntax is
"rejected by both nasm and GAS". Translating rop.asm to MASM would mean
patching upstream source, which this corpus refuses outright. So the options
were a GCC build now or an MSVC build after adding nasm to
`.github/workflows/windows-reference-data.yml`, and the second is a change to
shared CI that affects every family and belongs in its own review. The MinGW
artefact is what exists; an MSVC counterpart is a follow-up, and until it
exists this family's coverage of real sightings is weaker than the other
MSVC-native families here.

The C compiles unmodified under mingw-w64 GCC 13 - no warnings at -O0 - and
all six C functions plus the assembly routine survive into the image.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Upstream's makefile is not used, and there are two independent reasons.
# It drives cl, which is not the compiler here for the reason in the
# docstring; and its default target is "all: clean compile_asm compile
# clean_obj", where "clean" is "del /Q bin\\*" against a directory a fresh
# checkout does not have - a cmd-only recipe that aborts before anything is
# built, and not something an override from outside the file can fix. The two
# commands that matter are spelled out instead.
_ASM = "nasm -f win64 src/asm/rop.asm -o rop.obj"

# -O0 rather than -O2, matching upstream's own state rather than improving on
# it: its makefile passes no optimisation switch at all, so cl would compile
# at /Od, and -O0 is the GCC equivalent. It is also what keeps the six C
# functions as six bodies - at -O2 bCompare folds into findPattern and the
# masked-compare body, one of the more reusable things in this project, stops
# existing separately.
#
# -lpsapi for EnumProcessModules and GetModuleFileNameExA, which src/Utils.c
# calls. Upstream's single cl invocation gets them from the default libraries
# the MSVC driver passes on; GCC needs the library named.
#
# No -s anywhere, unlike ekko.py and foliage.py which have to strip it out of
# upstream's flags: this project never passes it, so the COFF symbol table
# survives without an override.
_BUILD = ('{cc} src/Main.c src/Utils.c src/Cronos.c rop.obj '
          '-o Cronos.exe -I headers -O0 -lpsapi')

_FLAGS = ("-O0 -I headers -lpsapi, with nasm -f win64 for src/asm/rop.asm. "
          "-O0 matches upstream's own state - its makefile passes no "
          "optimisation switch, so cl would compile at /Od - and keeps "
          "bCompare from folding into findPattern. Built with MinGW rather "
          "than upstream's cl because rop.asm is NASM syntax, ml64 will not "
          "assemble it, and nasm is absent from the windows-2022 runner")


RECIPES = {
    # No tags in the repository, so pinned by full commit and versioned by
    # its date, the convention MemoryModule_2019-02-24 already uses here.
    # HEAD is 474954c90afee6fe7da191fd9a5dc677ef46ccf0, 2023-09-26, whose
    # only change over its predecessor is the LICENSE file.
    "Cronos_2023-09-26": Recipe(
        family="Cronos",
        version="2023-09-26",
        upstream="https://github.com/Idov31/Cronos",
        # A real licence, unlike its two siblings here: 35 KB of GPL-3.0,
        # which is why this recipe can state terms where ekko.py and
        # foliage.py both have to record "none".
        license="GPL-3.0",
        source=Source(
            git_url="https://github.com/Idov31/Cronos.git",
            git_ref="474954c90afee6fe7da191fd9a5dc677ef46ccf0"),
        build=[BuildStep(_ASM), BuildStep(_BUILD)],
        artifacts=[
            Artifact(path="Cronos.exe", component="Cronos.exe"),
            # is_library stays true, as it is for every executable in this
            # corpus; validate.py requires it and obfuscator4g3nt47.py
            # records the same convention.
        ],
        toolchains=["mingw_x64"],
        requires=["nasm"],
        # Seven, measured, and the whole project: main, CronosSleep,
        # bCompare, findPattern, findInModule, findGadget and the NASM
        # routine QuadSleep. See Recipe.min_functions - a project that
        # genuinely contains that few functions, not a build that produced
        # too few.
        min_functions=7,
        build_flags=_FLAGS,
        notes="Sleep obfuscation via waitable timers and a hand-written ROP "
              "chain, beside Ekko (timer queues) and Foliage (APCs) here. "
              "Seven functions is the whole project - main, CronosSleep, "
              "bCompare, findPattern, findInModule, findGadget and the NASM "
              "routine QuadSleep - so min_functions=7, the same treatment "
              "Obfuscator4g3nt47 gets at the same count. InitializeTimerMs "
              "is a macro rather than a function and the 'end' label inside "
              "QuadSleep is a two-instruction add/ret tail below the census "
              "floor, so neither is counted. The reusable part is not the "
              "timer code but findGadget and its helpers: an "
              "EnumProcessModules walk, a first-section-header parse, and a "
              "masked scan for pop rcx/ret, pop rdx/ret and add rsp,0x20/pop "
              "rdi/ret - bCompare and findPattern are the classic "
              "masked-signature-scan pair, and that shape propagates into "
              "other tooling far more often than the sleep trick does. "
              "IMPORTANT DEVIATION: upstream's makefile drives cl, so an "
              "MSVC build is what a real sighting would most likely match, "
              "and this artefact is GCC. It is not built with MSVC because "
              "it cannot be on this repository's runner - src/asm/rop.asm is "
              "NASM syntax, ml64 will not assemble it, and nasm is absent "
              "from the windows-2022 image, as openssl_msvc.py already "
              "records. Translating the assembly to MASM would mean patching "
              "upstream source, which this corpus refuses. An MSVC "
              "counterpart needs nasm added to the Windows workflow and is a "
              "follow-up; until then this family's coverage of real "
              "sightings is weaker than the MSVC-native families here. The C "
              "compiles unmodified under mingw-w64 GCC 13 with no warnings "
              "at -O0, and all seven functions survive into the image. Built "
              "at -O0 because upstream passes no optimisation switch at all. "
              "x64 only, as upstream is: rop.asm is win64 and src/Cronos.c "
              "assigns to Rsp, Rip, Rcx, Rdx, R8 and R9, which exist only in "
              "the 64-bit CONTEXT. Nothing in the tree is prebuilt and "
              "nothing is vendored.",
    ),
}
