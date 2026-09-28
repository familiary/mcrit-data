"""MinHook (TsudaKageyu) - the canonical Windows inline hooking library.

Vendored across a great deal of tooling, and across a great deal of malware,
which is what makes naming its function bodies worth doing: an analyst who
meets a trampoline builder and a length disassembler inside a sample gets
them named instead of reverse engineering them again.

It is almost always a *vendored copy* rather than a linked dependency - the
five source files are dropped into a tree and compiled with the consumer's
own flags - so what an analyst meets is whatever release the vendoring froze.
Two releases are therefore pinned, and the reason is dates rather than taste:
v1.3.3 is 2017-01-07 and v1.3.4 is 2025-03-28, so v1.3.3 was the only release
in existence for eight years and is what the overwhelming majority of
vendored copies carry. v1.3.4 is what a copy made today carries.

They are not the same code. Between the two tags hook.c moves 144 lines,
trampoline.c 16, and both HDE translation units 12 each; buffer.c moves one.
The two parts a vendored copy freezes hardest - the trampoline builder and
the length disassembler - are both in that set, so a single pin would leave
the other shape unmatched.

What the project's own function count is, measured rather than asserted, at
v1.3.4 and per architecture:

    hook.c          27
    buffer.c         8
    trampoline.c     2
    hde64.c  or
    hde32.c          1
    ----------------
                    38

One HDE translation unit, not two: hde32.c and hde64.c each wrap their whole
body in ``#if defined(_M_IX86) || defined(__i386__)`` and its x64
counterpart, so the makefile compiles both and one of the two objects is
empty. v1.3.3 counts the same 38: the function *inventory* does not move
between these two tags at all - the same 27 names are in hook.c at both, and
what changed is their signatures (``void`` to ``VOID`` on DeleteHookEntry and
ProcessThreadIPs, ``VOID`` to ``BOOL`` on EnumerateThreads and to
``MH_STATUS`` on Freeze) and their bodies. So the two releases differ in code
shape, which is what a corpus records, and not in how many functions there
are, which is why the pin is justified on measured PicHashes below rather
than on a count.

Of those 38, one is vendored third-party code and is counted separately
below rather than claimed for MinHook: ``hde*_disasm`` is Hacker Disassembler
Engine, Copyright (c) 2008-2009 Vyacheslav Patkov. It stays in the artefact
because it is genuinely part of what a vendored copy carries and because
MinHook is the only place most analysts will meet it, but the honest
partition is 37 MinHook + 1 HDE.

At -O2 twelve of the 38 are inlined away and 26 survive as separate bodies -
FindHookEntry, AddHookEntry, DeleteHookEntry, FindOldIP, FindNewIP,
EnumerateThreads, EnterSpinLock, LeaveSpinLock, FindPrevFreeRegion,
FindNextFreeRegion, GetMemoryBlock and IsCodePadding are the twelve, all of
them small statics with one or two call sites. 26 is what this artefact
contains and is comfortably above the eight-function floor, so
``min_functions`` is not set: the floor is met on emitted bodies, not on a
number stated in a recipe.

Everything else in the image is compiler runtime or an import thunk and is
not MinHook's: the x64 -O2 build carries 115 named text symbols in all, of
which 26 are the above, roughly 30 are import thunks into kernel32
(VirtualAlloc, GetThreadContext, Thread32Next and the rest), and the
remainder is mingw-w64's DLL startup - DllMainCRTStartup, _CRT_INIT,
__mingw_* , the _FindPESection family, ___chkstk_ms, memcpy, strlen,
vfprintf and friends. ``corpus/baseline.py`` measures and drops that last
group rather than this recipe hardcoding it.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# build/MinGW/Makefile, driven from the repository root rather than from its
# own directory: its SRCS is "wildcard src/*.c src/hde/*.c" and its resource
# rule names dll_resources/MinHook.res, so those paths only resolve from the
# root. The sibling make.sh and make.bat run from build/MinGW/ and drive
# dllwrap instead; they are not used here because make.bat still names the
# pre-v1.3.3 uppercase src/HDE/ directory, which resolves on a
# case-insensitive filesystem and not on this one.
#
# CROSS_PREFIX is the makefile's own cross-compilation hook - it derives CC,
# WINDRES, DLLTOOL and AR from it - so selecting the architecture needs
# nothing else.
#
# Only the MinHook.dll target. The default "all" also builds libMinHook.a and
# libMinHook.dll.a, and SMDA has no COFF/ar loader, so a static archive is
# not reference data this pipeline can use.
#
# CFLAGS and LDFLAGS are both assigned with ":=" rather than "?=", so a
# command-line override replaces them outright and has to restate what is
# being kept. Both are restated from the makefile verbatim, with exactly one
# change each:
#
#   CFLAGS gains -O2. Upstream passes no -O at all, so its own MinGW build is
#   -O0, and that is not the shape a vendored copy is compiled at - the same
#   reasoning memorymodule.py records for the same reason. -Werror is kept
#   rather than dropped as a precaution: it was measured at -O2 on both
#   architectures and neither leg emits a single warning, so upstream's
#   strictness costs nothing here.
#
#   LDFLAGS loses -s. That flag strips the COFF symbol table, and MinGW
#   writing that table is the whole reason these reports reach IDA-with-
#   symbols quality; smdaify treats a mostly-anonymous report as a build
#   failure, so keeping -s would fail the build rather than produce weaker
#   data. -static-libgcc is kept, unlike the C++ recipes here which switch to
#   -shared-libgcc: that warning is about -static-libstdc++ pulling ~13,500
#   libstdc++ and libgcc bodies into a C++ sample, and this is C with no
#   exceptions, so what -static-libgcc adds is a handful of helpers
#   (___chkstk_ms and company) that baseline.py already measures and drops.
_MAKE = ('make -f build/MinGW/Makefile MinHook.dll '
         'CROSS_PREFIX={prefix} '
         'CFLAGS="-masm=intel -Wall -Werror -std=c11 -O2" '
         'LDFLAGS="-Wl,-enable-stdcall-fixup -static-libgcc"')

_FLAGS = ("-O2 -masm=intel -Wall -Werror -std=c11, linked -shared with "
          "-Wl,-enable-stdcall-fixup -static-libgcc; upstream passes no -O "
          "(so its own build is -O0) and strips with -s, which is dropped so "
          "the COFF symbol table survives")


def _minhook(version, git_ref):
    return Recipe(
        family="MinHook",
        version=version,
        upstream="https://github.com/TsudaKageyu/minhook",
        # LICENSE.txt is BSD 2-Clause: "Redistribution and use in source and
        # binary forms, with or without modification, are permitted provided
        # that the following conditions are met", followed by the source and
        # binary notice conditions and no third. src/hde/ carries its own
        # notice, Copyright (c) 2008-2009 Vyacheslav Patkov, which the notes
        # below record.
        license="BSD-2-Clause",
        source=Source(git_url="https://github.com/TsudaKageyu/minhook.git",
                      git_ref=git_ref),
        build=[
            BuildStep("make -f build/MinGW/Makefile clean",
                      allow_failure=True),
            BuildStep(_MAKE),
        ],
        artifacts=[
            Artifact(path="MinHook.dll", component="MinHook.dll"),
        ],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags=_FLAGS,
        notes="The canonical Windows inline hooking library, and in practice "
              "a vendored copy rather than a linked dependency: the five "
              "source files are dropped into a consumer's tree and compiled "
              "with the consumer's flags. Two releases are pinned because "
              "v1.3.3 (2017-01-07) was the only release for eight years and "
              "is what most vendored copies froze, while v1.3.4 (2025-03-28) "
              "is what a copy made today carries; between them hook.c moves "
              "144 lines, trampoline.c 16 and both HDE units 12 each, so the "
              "trampoline builder and the length disassembler - the two "
              "parts a vendored copy freezes hardest - differ between the "
              "two. The project's own count is 38 functions per "
              "architecture at v1.3.4 (hook.c 27, buffer.c 8, "
              "trampoline.c 2, one HDE unit 1) and the same 38 at v1.3.3, "
              "whose function inventory is identical and differs only in "
              "signatures and bodies; only one "
              "HDE translation unit compiles per architecture because each "
              "wraps its whole body in an _M_IX86/_M_X64 guard. One of the "
              "38 is vendored third-party code and is not MinHook's: "
              "hde32_disasm/hde64_disasm is Hacker Disassembler Engine, "
              "Copyright (c) 2008-2009 Vyacheslav Patkov, so the honest "
              "partition is 37 MinHook plus 1 HDE. At -O2 twelve small "
              "statics inline away and 26 bodies survive, which is what this "
              "artefact contains. Nothing in the tree is prebuilt - no .lib, "
              ".dll or .obj is committed at either tag - so no shipped "
              "binary is filed under this family. A DLL rather than the "
              "libMinHook.a the same makefile also builds, because SMDA has "
              "no COFF/ar loader.",
    )


RECIPES = {
    # 2017-01-07, and the only MinHook release in existence until 2025, so
    # this is the code in the overwhelming majority of vendored copies. Tag
    # v1.3.3 is commit 9fbd087432700d73fc571118d6a9697a36443d88.
    "MinHook_1.3.3": _minhook("1.3.3", "v1.3.3"),
    # 2025-03-28, current. Tag v1.3.4 is commit
    # c3fcafdc10146beb5919319d0683e44e3c30d537.
    "MinHook_1.3.4": _minhook("1.3.4", "v1.3.4"),
}
