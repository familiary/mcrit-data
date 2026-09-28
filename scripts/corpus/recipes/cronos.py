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

This is the MinGW half of the family; cronos_msvc.py is the MSVC half, and
that one matches most real sightings better because upstream's makefile drives
``cl``. Both now exist, so this recipe is no longer a compromise - it is the
GCC point of a two-compiler pair, the same arrangement MinHook and the other
``*_msvc`` families here have.

Getting the MSVC half took a workflow change worth knowing about, because
``src/asm/rop.asm`` is NASM syntax (``[BITS 64]``, ``[SECTION .text]``,
``GLOBAL``) that ml64 will not assemble, and nasm was absent from the
windows-2022 image. Translating the assembly would have meant patching
upstream source, which this corpus refuses outright, so the workflow installs
nasm instead - deliberately **off PATH**, exposed as ``$env:NASM``, because
OpenSSL's Configure probes ``nasm -v`` before its ``$disabled{asm}`` branch
and would otherwise switch its uplink shim away from ml64 despite ``no-asm``.
cronos_msvc.py's docstring carries the detail.

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
              "This is the MinGW half of a two-compiler pair: "
              "cronos_msvc.py builds the same commit with cl, which is what "
              "upstream's own makefile drives and what a real sighting most "
              "likely matches. The MSVC half needed nasm on the Windows "
              "runner, because src/asm/rop.asm is NASM syntax that ml64 will "
              "not assemble and translating it would mean patching upstream "
              "source, which this corpus refuses; the workflow now installs "
              "nasm deliberately OFF PATH and exposes it as %NASM%, so "
              "OpenSSL's Configure - which probes nasm before its "
              "$disabled{asm} branch - keeps taking its ml64 no-asm route "
              "unchanged. The C compiles unmodified under mingw-w64 GCC 13 "
              "with no warnings at -O0, and all seven functions survive into "
              "the image. Built "
              "at -O0 because upstream passes no optimisation switch at all. "
              "x64 only, as upstream is: rop.asm is win64 and src/Cronos.c "
              "assigns to Rsp, Rip, Rcx, Rdx, R8 and R9, which exist only in "
              "the 64-bit CONTEXT. Nothing in the tree is prebuilt and "
              "nothing is vendored.",
    ),
}
