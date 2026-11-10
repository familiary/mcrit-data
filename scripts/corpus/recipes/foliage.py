"""Foliage - sleep obfuscation via queued APCs and NtContinue.

The third of the three techniques CoffeeLoader's sleep obfuscation is named
after, beside Ekko (timer queues) and Cronos (waitable timers). It suspends a
sacrificial thread, queues a chain of APCs onto it with NtQueueApcThread, and
each APC runs NtContinue over a CONTEXT whose Rip has been pointed at the
next step - VirtualProtect, SystemFunction032, the wait, then back again -
before NtAlertResumeThread lets the chain run.

Three things about this family are unusual enough that they are stated here
rather than left for someone to rediscover, and none of them is a technical
objection: they are provenance, and the corpus records provenance.

**This is not the original repository, because the original is gone.** The
upstream the technique is named for is SecIdiot/FOLIAGE, and that repository
and its owning account both 404 today - the author's account was renamed.
What is built here is y11en/FOLIAGE, which describes itself as an experiment
in reproducing Obfuscate & Sleep. The copyright headers inside the tree still
read "Copyright (c) 2021 Austin Hudson" and "Copyright (c) 2021 GuidePoint
Security LLC", so the code is the original author's as carried by a
third-party mirror rather than a rewrite - but a reader should know that this
artefact's bytes were built from a mirror, and that no upstream release
exists to compare them against.

**There is no licence of any kind.** No LICENSE or COPYING file anywhere in
the tree, and the per-file copyright headers state a holder without granting
terms. ``license`` is "none", which is the fact and is copied verbatim into
provenance.json.

**The project is not a sleep-obfuscation library.** Its own file headers
describe it as a "dns over http(s) persistence stager", and the sleep
obfuscation is one part of that stager. Of the nine functions it contains,
two are the technique - ``ObfuscateAddFn`` and ``ObfuscateSleep`` - and the
other seven (``HashString``, ``PebGetModule``, ``PeGetFuncEat``,
``NtMemAlloc``, ``NtMemFree``, ``Start``, ``Leave``) are the ordinary
position-independent-stager furniture of API hashing, a PEB walk, an export
table parse and heap wrappers. They are still this project's own code and are
counted as such, but nobody should read a match on ``PebGetModule`` as
evidence of Foliage specifically: that shape is common to a whole genre of
PIC loaders.

Nine functions, so ``min_functions`` is 9 - below the corpus floor of eight
it is not, but it is stated anyway because -flto does not emit all nine and
the field has to describe the project rather than the build. See the flag
notes below.

Built with a lowered ``_WIN32_WINNT``, and that needs justifying because
without it the tree does not compile at all. Against current mingw-w64
headers ``source/tebpeb.h`` redefines ``struct _PROCESSOR_NUMBER`` (winnt.h
declares it under ``_WIN32_WINNT >= 0x0601``) and ``source/apidef.h``
declares ``SetProcessValidCallTargets`` returning ``BOOLEAN`` where
memoryapi.h declares ``WINBOOL`` under ``_WIN32_WINNT >= _WIN32_WINNT_WIN10``
- four hard errors, not warnings. ``-D_WIN32_WINNT=0x0600`` stops the SDK
declaring either, and Foliage's own headers then supply both, which is
plainly what the tree was written against. It is a command-line define and
not a source patch, which is the line that matters here: this corpus refuses
recipes that need upstream source edited, and this one does not need it.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Upstream's own Makefile, two targets rather than "all": "all" additionally
# runs scripts/pedump.py to carve the .text out into FOLIAGE.x64.bin, and the
# PE is what this pipeline wants - SMDA reads a PE image directly, and the
# carved blob would need is_blob with a stated bitness and an arbitrary base
# for no gain.
#
# CFLAGS and LFLAGS are restated because the Makefile builds CFLAGS up over
# five "CFLAGS := $(CFLAGS) ..." lines and a command-line override replaces
# the lot. Everything upstream passes is kept except the two -s, plus the one
# define added:
#
#   -s in CFLAGS and -Wl,-s in LFLAGS both strip the symbol table, and with
#   -nostdlib there is no CRT to name anything either - a stripped build of
#   this project reports every function anonymous and smdaify refuses it.
#
#   -D_WIN32_WINNT=0x0600 is what makes the tree compile at all; see the
#   docstring.
#
# -flto is upstream's and is kept, with a consequence worth stating plainly
# because it is the opposite of convenient: LTO inlines ObfuscateSleep and
# HashString into their callers, so the one function that *is* the sleep
# obfuscation technique does not exist as a separate body in this artefact -
# it is inside Start. Nine functions are the project's; the image carries
# seven of them plus three assembly routines. Dropping -flto would expose
# ObfuscateSleep, and would also mean shipping a shape upstream does not
# build, so it is kept and recorded instead. Anyone wanting the technique's
# own body should read Start.
#
# -nostdlib with -Tscripts/linker.ld is what makes the .text position
# independent and is the whole point of the project; the entry point is _BEG
# in source/asm/start.asm, which the linker script names.
#
# --image-base=0 is added, and it is the difference between an artefact and
# nothing. scripts/linker.ld replaces SECTIONS wholesale and gives .text no
# address, so it is laid down at 0 while the PE keeps mingw's default image
# base of 0x140000000 - ld then reports "section below image base" for .text,
# .xdata and .pdata and writes a PE whose section addresses are outside its
# own image. SMDA refuses it: measured, that image disassembles to 0
# functions with status "error", and setting the base to 0 instead gives 10
# functions and status "ok" from the identical code.
#
# The alternative was to record FOLIAGE.x64.bin - the buffer
# scripts/pedump.py carves out of section 0 up to the four 0xCC bytes - as an
# is_blob artefact, the way sRDI and pe_to_shellcode are recorded. That was
# rejected for a specific reason: Recipe.slug hardcodes the producer of a
# blob to "msvc", because every blob in this corpus so far is shellcode
# upstream compiled with MSVC and committed, and labelling it after the
# toolchain that merely extracted it would be a lie in the filename. Here
# the pipeline itself compiles the code with GCC, so "msvc" in the stem
# would be exactly that lie. Keeping the PE also keeps the COFF symbol
# table, which a raw buffer has no room for. Position independence is a
# property of the code and is unaffected by what the container's header
# says the base is.
_ASM = "make start.o"

_LINK = ('make FOLIAGE.x64.exe '
         'CFLAGS="-D_WIN32_WINNT=0x0600 -Os -fno-asynchronous-unwind-tables '
         '-nostdlib -fno-ident -Qn -fno-builtin-memcpy -fpack-struct=8 '
         '-falign-functions=1 -falign-jumps=1 -falign-labels=1 '
         '-falign-loops=1 -flto" '
         'LFLAGS="-Wl,--no-seh,--enable-stdcall-fixup,'
         '-Tscripts/linker.ld,--image-base=0"')

_FLAGS = ("-Os -flto -nostdlib -fno-asynchronous-unwind-tables -fno-ident "
          "-Qn -fno-builtin-memcpy -fpack-struct=8 -falign-functions=1 "
          "-falign-jumps=1 -falign-labels=1 -falign-loops=1, linked "
          "-Wl,--no-seh,--enable-stdcall-fixup,-Tscripts/linker.ld,"
          "--image-base=0 with "
          "nasm -f win64 for source/asm/start.asm; upstream's -s and -Wl,-s "
          "are dropped so the symbol table survives, and "
          "-D_WIN32_WINNT=0x0600 is added because without it tebpeb.h and "
          "apidef.h collide with current mingw-w64 headers and the tree does "
          "not compile")


RECIPES = {
    # No tags in the repository, so pinned by full commit and versioned by
    # its date, the convention MemoryModule_2019-02-24 already uses here.
    # y11en/FOLIAGE HEAD is 32a2da05282f38d8859b091312708ee9f2840297,
    # 2021-03-14.
    "Foliage_2021-03-14": Recipe(
        family="Foliage",
        version="2021-03-14",
        # The mirror that exists, not the original that does not. Recorded
        # this way deliberately: an upstream field pointing at a 404 would be
        # useless to anyone trying to verify this artefact.
        upstream="https://github.com/y11en/FOLIAGE",
        license="none",
        source=Source(
            git_url="https://github.com/y11en/FOLIAGE.git",
            git_ref="32a2da05282f38d8859b091312708ee9f2840297"),
        build=[BuildStep(_ASM), BuildStep(_LINK)],
        artifacts=[
            Artifact(path="FOLIAGE.x64.exe", component="FOLIAGE.x64.exe"),
            # is_library stays true, as it is for every executable in
            # this corpus; validate.py requires it and
            # obfuscator4g3nt47.py records the same convention.
        ],
        toolchains=["mingw_x64"],
        requires=["nasm"],
        # Nine is what the project contains: HashString, Leave, NtMemAlloc,
        # NtMemFree, PeGetFuncEat, PebGetModule, ObfuscateAddFn,
        # ObfuscateSleep and Start, each marked with the project's own D_SEC
        # section attribute. Stated because -flto emits only seven of them.
        min_functions=9,
        build_flags=_FLAGS,
        notes="Sleep obfuscation via queued APCs and NtContinue - the third "
              "of the three techniques CoffeeLoader's sleep obfuscation is "
              "named after, beside Ekko and Cronos. Three provenance facts "
              "matter here. First, this is not the original repository: "
              "SecIdiot/FOLIAGE and its owning account both 404 today, and "
              "what is built is the y11en mirror, which describes itself as "
              "an experiment in reproducing Obfuscate & Sleep. The in-tree "
              "copyright headers still read Austin Hudson and GuidePoint "
              "Security LLC, so the code is the original author's as carried "
              "by a third party rather than a rewrite - but these bytes come "
              "from a mirror and no upstream release exists to compare them "
              "against. Second, there is no licence of any kind: no LICENSE "
              "or COPYING file anywhere, and the per-file headers name a "
              "holder without granting terms. Third, the project is not a "
              "sleep-obfuscation library - its own headers call it a 'dns "
              "over http(s) persistence stager' - and of its nine functions "
              "only ObfuscateAddFn and ObfuscateSleep are the technique, the "
              "other seven being ordinary PIC-stager furniture (API hashing, "
              "a PEB walk, an export-table parse, heap wrappers) whose shape "
              "is common to a whole genre of loaders, so a match on "
              "PebGetModule is not evidence of Foliage specifically. Built "
              "with -D_WIN32_WINNT=0x0600, without which the tree does not "
              "compile at all against current mingw-w64 headers: tebpeb.h "
              "redefines struct _PROCESSOR_NUMBER and apidef.h declares "
              "SetProcessValidCallTargets with a different return type, four "
              "hard errors. That is a command-line define, not a source "
              "patch. Upstream's -flto is kept, which inlines ObfuscateSleep "
              "and HashString into their callers - so the function that is "
              "the technique has no separate body in this artefact and lives "
              "inside Start. x64 only, as upstream's makefile and its win64 "
              "assembly are. The PE is recorded rather than the "
              "FOLIAGE.x64.bin that scripts/pedump.py carves out of it, "
              "since SMDA reads a PE image directly.",
    ),
}
