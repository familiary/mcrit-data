"""jitasm - header-only runtime x86/x64 assembler, built with MinGW.

jitasm (hikaru-i/jitasm, one header, jitasm.h) writes x86 and x64 machine
code at run time from C++ that reads like inline assembly. Kaspersky's
2026-06-24 StrikeShark / SharkLoader report describes it building direct
syscall stubs for NtOpenProcessToken and NtAdjustPrivilegesToken. That is an
analyst's identification - no function name, constant or encoder-table byte is
published - and it is the same chain as MinHook and Detours (issues 11, 12
and 14 of the tracker), so one sample is a validation target for all three.
The original Google Code project is gone and the filed GitHub URL
(hattori/jitasm) is a 404; the pin is the last commit of the hikaru-i mirror,
7cb9d729, 2018-11-24, whose README says new BSD and whose jitasm.h carries
the full three-clause text. This is not AsmJit, which data/BlackBone already
vendors; the two share no code.

The question the issue asked first: what survives -O. Measured, with the
exerciser below and the same MinGW compilers as the corpus: the optimiser
takes almost nothing out. Text symbols in the linked DLL, -O0 against -O2,
x64 12489 against 3925 and i686 11634 against 3235 - a factor of three and a
half, and the -O2 images still carry 1570 (x64) and 1308 (x86) jitasm::
functions after the glue filter. They survive because jitasm is not a set of
one-line inlines: every mnemonic is a distinct Frontend member that appends an
Instr, the encoder is Backend::Assemble and its Encode* helpers, and the
register allocator in jitasm::compiler is a few thousand lines of ordinary
out-of-line C++ over std::vector, std::deque and std::map. MSVC is checked in
jitasm_msvc.py and shows the same thing at /O2.

The unoptimised leg the issue expects (-O0 for MinGW, /Od for MSVC) is built
as well, as its own version string (2018-11-24-O0 here, 2018-11-24-Od in
jitasm_msvc.py) so it sits beside the -O2 artefact rather than replacing it.
It is not a superset of the -O2 one, it is a different image: -O0 keeps
every Frontend member and every STL helper out of line, so it carries about
three times as many functions, and PicHash overlap at the ten-instruction
floor with the -O2 build of the same compiler is 1 hash on each
architecture. A consumer that builds its syscall-stub generator in a Debug
configuration matches this artefact and not the other. Counts, kept + removed
= total: x86 5949 + 52 = 6001, x64 6268 + 53 = 6321, of which 5520 and 5925
are ten instructions or more (2572 and 2752 distinct PicHashes) and 4993 and
5352 carry jitasm in their name. The -O0 build shares no PicHash at that
floor with the ELF build, the MSVC /Od build or across its two
architectures. The same exerciser, so the same consumer scaffolding is in it.

What the exerciser has to do, which is the real decision in this recipe. The
emitter covers x86, x64, MMX, SSE through SSE4.2, AVX, AVX2, FMA, FMA4, XOP,
F16C and BMI, and a Frontend member only exists in the image if some
translation unit calls it. exercisers/jitasm.cpp therefore includes upstream's
own test/test_backend.cpp unmodified: sixty jitasm::function structs, one per
instruction family from SAL through x87, MMX, SSE and AVX2 gather, whose
naked_main bodies call the mnemonics. That file's test driver is empty unless
MASM_TEST or NASM_TEST is defined and those need object files this corpus
does not have, so it instantiates nothing by itself; the exerciser assembles
each struct. Seven more functions written for it reach what naked_main does
not - the register allocator, If/ElseIf/While control flow, argument passing
in registers and on the stack, float, double and __m128 arguments and
returns. Upstream's samples were not used: they are four small programs.

What that costs, stated plainly because it is not zero. naked_main is
consumer code - the sixty test cases are the largest functions in the image
by instruction count, thousands each - and they and the exerciser's own
assemble_one<> and ex_* functions are filed under this family. They are
recognisable by name (test_*, ex_*, assemble_one, test_backend and the one
static-initialiser GLOBAL__sub_I__Z12test_backendv), 197 of 1563 functions on
x86 and 252 of 1867 on x64, and they will not be PicHash-matched by a real
sample whose own code is different. The remaining roughly seven in eight are
jitasm's and the C++ standard library instantiations it makes. Counts, kept
+ removed = total: x86 1563 + 54 = 1617, x64 1867 + 55 = 1922, of which 1308
and 1627 are ten instructions or more. -mmmx -msse -msse2 are upstream's own
32-bit test flags and -fno-operator-names is upstream's, because the
mnemonics and, or, xor and not are member names.

Overlaps. The PicHash overlap at the ten-instruction floor with the MSVC
build is zero on both architectures (x64 312 distinct hashes here against
2516) and with the ELF build zero on x64 and 4 of 863 on x86, so each is its
own reference. Distinct hashes are far fewer than functions because most of
the image is repeats: destructors, and each instruction family's naked_main
differing only in its operands.

Glue survivors, by name and PicHash: _GLOBAL__sub_I__Z12test_backendv (x64
15070570138432079284, 721 instructions; x86 13547478633205230882, 385) is the
static initialiser for <iostream>, pulled in by upstream's test.h and not
libstdc++'s code to remove by name; _Unwind_Resume, __cxa_begin_catch,
__cxa_end_catch, __cxa_rethrow and __gxx_personality_seh0 (x64) and the same
with ___register_frame_info and ___deregister_frame_info (x86) are
one-instruction import thunks, PicHash 1253497258561142223.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

# -O2 is the measured choice - see the docstring. -I. puts jitasm.h and
# test/test_backend.cpp on the include path from the source root.
# -shared-libgcc so no libgcc is linked statically; the exerciser uses
# std::vector and std::deque through jitasm.h, so some libstdc++ template
# instantiation is unavoidable and is what the glue filter is for.
_BUILD = ("{cxx} -O2 -fno-operator-names -mmmx -msse -msse2 -shared -I. "
          "-o jitasm.dll {repo}/scripts/corpus/exercisers/jitasm.cpp "
          "-shared-libgcc")

# The unoptimised leg the tracker issue asks for (-O0 for MinGW, /Od for
# MSVC in jitasm_msvc.py). Identical to _BUILD except for the -O level, so
# the two artefacts differ in the optimiser and nothing else.
_BUILD_O0 = _BUILD.replace(" -O2 ", " -O0 ")

RECIPES = {
    "jitasm_2018-11-24": Recipe(
        family="jitasm",
        version="2018-11-24",
        upstream="https://github.com/hikaru-i/jitasm",
        license="New BSD (three-clause), Copyright (c) 2009-2011 Hikaru "
                "Inoue, Akihiro Yamasaki",
        source=Source(git_url="https://github.com/hikaru-i/jitasm.git",
                      git_ref="7cb9d72982c793374c49b804bec842deb1506d92"),
        build=[BuildStep(_BUILD)],
        artifacts=[Artifact(path="jitasm.dll", component="jitasm.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 -fno-operator-names -mmmx -msse -msse2 -shared "
                    "-shared-libgcc",
        notes="Built from an exerciser translation unit, since the library "
              "is one header: upstream's test/test_backend.cpp, included "
              "unmodified, supplies sixty instruction-family structs that the "
              "exerciser assembles, and seven functions of its own reach the "
              "register allocator, control flow and calling conventions. "
              "Measured at -O2 on this compiler: 1563 functions kept of 1617 "
              "on x86 (54 MinGW runtime removed), 1867 of 1922 on x64 (55), "
              "1308 and 1627 of them ten instructions or more. -O0 gives "
              "12489 text symbols against 3925 at -O2 on x64 (11634 against "
              "3235 on x86), so the library survives optimisation; the "
              "unoptimised consumer is described by the separate "
              "2018-11-24-O0 artefact. About "
              "one function in eight is not jitasm's: the sixty test_*::"
              "naked_main bodies are upstream's test cases and, with the "
              "exerciser's ex_* and assemble_one functions and the "
              "<iostream> static initialiser, 197 functions on x86 and 252 "
              "on x64 are consumer code recognisable by name. The MSVC and "
              "ELF counterparts are built from the same exerciser and share "
              "no PicHash with this one at the ten-instruction floor "
              "(4 of 863 on x86 against the ELF build). Evidence behind "
              "the family is structural only: Kaspersky describes jitasm "
              "building NtOpenProcessToken and NtAdjustPrivilegesToken "
              "syscall stubs and publishes no function, constant or table.",
    ),
    "jitasm_2018-11-24-O0": Recipe(
        family="jitasm",
        version="2018-11-24-O0",
        upstream="https://github.com/hikaru-i/jitasm",
        license="New BSD (three-clause), Copyright (c) 2009-2011 Hikaru "
                "Inoue, Akihiro Yamasaki",
        source=Source(git_url="https://github.com/hikaru-i/jitasm.git",
                      git_ref="7cb9d72982c793374c49b804bec842deb1506d92"),
        build=[BuildStep(_BUILD_O0)],
        artifacts=[Artifact(path="jitasm.dll", component="jitasm.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O0 -fno-operator-names -mmmx -msse -msse2 -shared "
                    "-shared-libgcc",
        notes="The unoptimised counterpart of jitasm_2018-11-24 that the "
              "tracker issue expects for MinGW: the same commit, exerciser "
              "and command line with -O0 in place of -O2, filed under its own "
              "version string so both stay. Measured: 5949 functions kept of "
              "6001 on x86 (52 MinGW runtime removed), 6268 of 6321 on x64 "
              "(53), 5520 and 5925 of them ten instructions or more, 4993 and "
              "5352 carrying jitasm in their name. Not a superset of the -O2 "
              "build: one PicHash in common with it per architecture at the "
              "ten-instruction floor, and none with the ELF or the MSVC /Od "
              "builds. As in the -O2 artefact, upstream's sixty test_*::"
              "naked_main cases and the exerciser's ex_* and assemble_one "
              "functions are consumer code recognisable by name.",
    ),
}
