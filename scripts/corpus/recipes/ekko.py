"""Ekko (Cracked5pider) - sleep obfuscation via CreateTimerQueueTimer.

The proof of concept CoffeeLoader's sleep obfuscation is named after, and the
one most widely copied of the timer-queue variants. It captures a thread
context with RtlCaptureContext, clones it six times, rewrites Rip/Rcx/Rdx/R8/R9
in each clone into a call frame for VirtualProtect, SystemFunction032,
WaitForSingleObject, SystemFunction032, VirtualProtect and SetEvent in turn,
then queues all six as NtContinue callbacks on a timer queue at 100 ms
intervals. The thread sleeps with its own image encrypted and
PAGE_READWRITE for the duration.

**This family is two functions, and that is the entire project.** ``EkkoObf``
in Src/Ekko.c (112 lines) and ``main`` in Src/Main.c (14 lines). There is no
third. ``min_functions`` is therefore set to 2 against the corpus-wide floor
of eight, which is what that field exists for - a project that genuinely
contains that few functions, with the number set to the count that was
measured. Both survive as separate bodies at upstream's -Os: main is a
three-line ``do { EkkoObf(4000); } while (TRUE)`` loop and is not folded into
its callee, and EkkoObf carries the whole technique.

Its reference value should be read with that in mind, and the honest
statement is that it is thin. ``main`` is a loop around one call and will
not match anything meaningful. What is worth having is ``EkkoObf``: it is a
single large body - six memcpy'd CONTEXT structures and thirty-odd register
assignments - and a vendored copy of this technique compiled at any
optimisation level keeps recognisably that shape, which is why the technique
is worth one function of reference data even though the project is not worth
a family by the usual standard.

What it is *not* is a substitute for detecting the technique. The thing an
analyst meets is an API sequence - CreateTimerQueue, CreateTimerQueueTimer
with RtlCaptureContext, then the same with NtContinue, around
SystemFunction032 - and that is a behavioural signature for a YARA rule or a
sandbox trace rather than something code similarity finds. Cronos, the
waitable-timer sibling in this corpus, ships its own Cronos.yara for exactly
that purpose.

x64 only, and not by choice of this recipe: Src/Ekko.c assigns to
``CtxThread.Rsp``, ``.Rip``, ``.Rcx``, ``.Rdx``, ``.R8`` and ``.R9``, which
exist only in the 64-bit CONTEXT, and upstream's makefile has an x64 target
and no x86 one. It defines CCX86 and never uses it.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Upstream's own makefile target, with CFLAGS restated because it is built up
# with ":=" and "+=" across five lines and a command-line override replaces
# the lot. Everything upstream passes is kept except the two -s:
#
#   -s in CFLAGS and -Wl,-s on the link line both strip the symbol table.
#   MinGW writing a COFF symbol table is what gets these reports to roughly
#   the symbol quality of the IDA-with-symbols path, and smdaify refuses a
#   report whose functions are mostly anonymous - with two own functions in
#   an image of import thunks and mingw startup glue, a stripped build would
#   name nothing at all and be refused, correctly.
#
# -Os is upstream's and is kept rather than raised to -O2. This is the
# opposite of the choice memorymodule.py and minhook.py make, and for a
# reason specific to this project: MemoryModule and MinHook are libraries
# vendored into other people's builds and compiled at the consumer's
# optimisation level, so -O2 is the shape encountered. Ekko is a
# self-contained proof of concept that people copy and build as it stands,
# with this makefile, so -Os *is* the shape encountered. It also matters that
# -Os is what keeps main and EkkoObf apart here.
#
# -fPIC is upstream's and is a no-op with a warning on a PE target; -w is
# upstream's and suppresses that warning. Both are kept so the command line
# is upstream's, not a tidied version of it.
_BUILD = ('make x64 CCX64={cc} '
          'CFLAGS="-Os -fno-asynchronous-unwind-tables -fno-ident '
          '-fpack-struct=8 -falign-functions=1 -ffunction-sections '
          '-falign-jumps=1 -w -falign-labels=1 -fPIC '
          '-Wl,--no-seh,--enable-stdcall-fixup"')

_FLAGS = ("-Os -fno-asynchronous-unwind-tables -fno-ident -fpack-struct=8 "
          "-falign-functions=1 -ffunction-sections -falign-jumps=1 "
          "-falign-labels=1 -fPIC -w, linked -Wl,--no-seh,"
          "--enable-stdcall-fixup; upstream's -s and -Wl,-s are dropped so "
          "the COFF symbol table survives, and -Os is upstream's own")


RECIPES = {
    # No tags anywhere in the repository, so pinned by full commit and
    # versioned by its date, the convention MemoryModule_2019-02-24 and
    # BlackBone_2023-07-17 already use here. HEAD at the time of writing is
    # 91c28afef00b9832cbcdddcee0298d32448a993a, 2022-08-24, whose only change
    # over its predecessor is the README note warning that the
    # implementation has known flaws.
    "Ekko_2022-08-24": Recipe(
        family="Ekko",
        version="2022-08-24",
        upstream="https://github.com/Cracked5pider/Ekko",
        # No LICENSE or COPYING file, and no copyright or licence line in
        # either source file, either header, the makefile or the README. The
        # README credits Austin Hudson and Peter Winter-Smith for the
        # technique and states no terms for the code. "none" is the fact, and
        # it is copied verbatim into provenance.json - the same treatment
        # callobfuscator.py records for the same situation.
        license="none",
        source=Source(
            git_url="https://github.com/Cracked5pider/Ekko.git",
            git_ref="91c28afef00b9832cbcdddcee0298d32448a993a"),
        build=[BuildStep(_BUILD)],
        artifacts=[
            Artifact(path="Ekko.x64.exe", component="Ekko.x64.exe"),
            # is_library stays true, as it is for every executable in
            # this corpus; validate.py requires it and
            # obfuscator4g3nt47.py records the same convention.
        ],
        toolchains=["mingw_x64"],
        # Two, measured in the artefact, and the whole project: EkkoObf and
        # main. Not a threshold moved to let something through - there is no
        # library API here to instantiate and no driver that could raise the
        # count, so eight is unreachable by any means short of writing code
        # that is not upstream's. See Recipe.min_functions.
        min_functions=2,
        build_flags=_FLAGS,
        notes="Sleep obfuscation via CreateTimerQueueTimer - the proof of "
              "concept CoffeeLoader's sleep obfuscation is named after. The "
              "whole project is two functions, EkkoObf (Src/Ekko.c, 112 "
              "lines) and main (Src/Main.c, 14 lines), so min_functions=2 "
              "against the corpus floor of eight; both survive as separate "
              "bodies at upstream's -Os. Its reference value is thin and "
              "this recipe says so: main is a loop around one call and will "
              "match nothing useful, and what is worth having is EkkoObf's "
              "single large body - six memcpy'd CONTEXT structures and the "
              "register assignments that turn each into a call frame for "
              "VirtualProtect, SystemFunction032, WaitForSingleObject and "
              "SetEvent. The technique itself is better caught as an API "
              "sequence in a YARA rule or a sandbox trace than by code "
              "similarity; the Cronos family here ships its own Cronos.yara "
              "for that. x64 only because Src/Ekko.c assigns to Rsp, Rip, "
              "Rcx, Rdx, R8 and R9, which exist only in the 64-bit CONTEXT, "
              "and upstream's makefile has no x86 target - it defines CCX86 "
              "and never uses it. -Os is upstream's own and is kept rather "
              "than raised to -O2, because unlike a vendored library this is "
              "a self-contained proof of concept people build as it stands. "
              "No licence of any kind: no LICENSE or COPYING file and no "
              "copyright line in any source file, header, the makefile or "
              "the README. Nothing is vendored and nothing in the tree is "
              "prebuilt.",
    ),
}
