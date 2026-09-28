"""Cronos (Idov31) - sleep obfuscation via waitable timers and a ROP chain.

The waitable-timer variant of the technique, beside Ekko (timer queues) and
Foliage (APCs). It captures a context by handing RtlCaptureContext to
SetWaitableTimer as the completion routine, clones it into four frames for
VirtualProtect, SystemFunction032, SystemFunction032 and VirtualProtect, arms
four timers at staggered due times, and then hands control to a hand-written
ROP chain so that the thread's own return address is not on any module the
scanner will walk.

Seven functions, which is the whole project and one short of the corpus
floor, so ``min_functions`` is 7 - the same treatment obfuscator4g3nt47.py
already gets here for the same reason, and the number is what was measured
rather than what would be convenient:

    src/Main.c    main
    src/Utils.c   bCompare, findPattern, findInModule, findGadget
    src/Cronos.c  CronosSleep
    src/asm/rop.asm  QuadSleep

``InitializeTimerMs`` is a macro in headers/Cronos.h, not a function, and the
``end`` label inside ``QuadSleep`` is a two-instruction ``add rsp, 0x28; ret``
tail - it is a branch target rather than a routine, and even where SMDA
recovers it separately it sits below the ten-instruction floor the
cross-family census counts at. Neither is counted.

What is actually worth having here is ``findGadget`` and its helpers.
``CronosSleep`` is the technique and is the obvious body, but the gadget
search - walk the loaded modules with EnumProcessModules, parse each one's
first section header, and scan it for ``\\x59\\xC3`` (pop rcx; ret),
``\\x5A\\xC3`` (pop rdx; ret) and ``\\x48\\x83\\xC4\\x20\\x5F\\xC3`` (add rsp,
0x20; pop rdi; ret) - is a pattern-scanner shape that propagates into other
tooling far more often than the timer code does. ``bCompare`` and
``findPattern`` are the classic masked-signature-scan pair, and at 8 and 13
instructions the first of them is below the census floor.

MSVC and x64 only, both by upstream's own declaration rather than this
recipe's choice: the makefile drives ``cl``, ``src/asm/rop.asm`` is
``[BITS 64]`` assembled ``-f win64``, and src/Cronos.c assigns to Rsp, Rip,
Rcx, Rdx, R8 and R9, which exist only in the 64-bit CONTEXT.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Upstream's makefile is not used, and the reason is mechanical rather than a
# preference. Its default target is "all: clean compile_asm compile
# clean_obj", and "clean" is "del /Q bin\\*" against a directory that does not
# exist in a fresh checkout - nmake aborts on it before anything is built,
# and "del" cannot be made to tolerate a missing directory from outside the
# file. The three commands it would have run are spelled out instead, with
# the compile split from the link so the two PDBs can be kept apart.
#
# nasm rather than ml64: rop.asm is NASM syntax ("[BITS 64]", "[SECTION
# .text]", "GLOBAL"), which ml64 will not assemble. nasm is on the
# windows-2022 image and openssl_msvc.py already depends on it there.
_MKDIR = "if not exist bin mkdir bin"

_ASM = "nasm -f win64 src/asm/rop.asm -o bin/rop.obj"

# /MD, against upstream's default. cl with no /M flag links the static
# release CRT (/MT), and that is what put 1947 of VX-API's 4219 functions
# into that artefact as Microsoft's code under the library's name. data/MSVC
# is this corpus's reference for exactly that code.
#
# /Zi and a real /DEBUG, which upstream has no equivalent of at all: its
# makefile passes no debug switch, so the build emits no PDB. MSVC keeps
# symbols in a PDB rather than in a COFF symbol table, and without one SMDA
# would name nothing in an EXE that exports nothing - the symbol-coverage
# gate would refuse the build, correctly.
#
# No /O switch, which is upstream's own state and is deliberate here rather
# than an omission: cl defaults to /Od, and at /Od all six C functions
# survive as separate bodies. That is the honest shape of this project, and
# raising it to /O2 would inline bCompare into findPattern and lose the
# masked-compare body that is one of the more reusable things here.
#
# /Fd names the compiler PDB separately from the linker PDB. Pointing both at
# one path would have link.exe write the file it is reading type information
# from; nlohmann_msvc.py records the same split for the same reason.
_COMPILE = ('cl /nologo /c /MD /Zi /I headers '
            '/Fdbin\\Cronos.compiler.pdb /Fobin\\ '
            'src\\Main.c src\\Utils.c src\\Cronos.c')

# psapi.lib for EnumProcessModules and GetModuleFileNameExA, which
# src/Utils.c calls and which upstream's single-command cl line gets away
# with only because cl passes the default libraries through to the linker.
#
# /Brepro drops the link timestamp so two runs record the same sha256.
# /INCREMENTAL:NO because /DEBUG implies /INCREMENTAL, and an incrementally
# linked image reaches every function through a one-instruction jump thunk
# that smdaify.assert_not_incrementally_linked refuses. /OPT:NOREF keeps
# bodies nothing references and /OPT:NOICF keeps two that compiled alike
# apart - relevant here because bCompare is small and the four
# findGadget call sites differ only in their pattern arguments.
_LINK = ('link /nologo /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF '
         '/PDB:bin\\Cronos.pdb /OUT:bin\\Cronos.exe '
         'bin\\Main.obj bin\\Utils.obj bin\\Cronos.obj bin\\rop.obj '
         'psapi.lib')

_FLAGS = ("/MD /Zi /I headers with no /O switch, so cl's default /Od - "
          "upstream passes no optimisation flag and at /Od all six C "
          "functions survive as separate bodies; linked /DEBUG /Brepro "
          "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF against psapi.lib, with "
          "nasm -f win64 for src/asm/rop.asm. Upstream's /MT default is "
          "replaced with /MD, and /Zi plus /DEBUG are added because upstream "
          "emits no PDB at all and MSVC keeps symbols there")


RECIPES = {
    # No tags in the repository, so pinned by full commit and versioned by
    # its date, the convention MemoryModule_2019-02-24 already uses here.
    # HEAD is 474954c90afee6fe7da191fd9a5dc677ef46ccf0, 2023-09-26, whose
    # only change over its predecessor is the LICENSE file.
    "Cronos_2023-09-26": Recipe(
        family="Cronos",
        version="2023-09-26",
        upstream="https://github.com/Idov31/Cronos",
        # A real LICENSE file, unlike its two siblings here: 35 KB of GPL-3.0,
        # which is why this recipe can state terms where ekko.py and
        # foliage.py both record "none".
        license="GPL-3.0",
        source=Source(
            git_url="https://github.com/Idov31/Cronos.git",
            git_ref="474954c90afee6fe7da191fd9a5dc677ef46ccf0"),
        build=[
            BuildStep(_MKDIR),
            BuildStep(_ASM),
            BuildStep(_COMPILE),
            BuildStep(_LINK),
            # build.py reports a missing artefact by the path it expected and
            # nothing else; this puts what the build actually wrote into the
            # log the workflow prints on failure.
            BuildStep("dir bin", allow_failure=True),
        ],
        artifacts=[
            Artifact(path="bin\\Cronos.exe", component="Cronos.exe",
                     is_library=False, pdb="bin\\Cronos.pdb"),
        ],
        toolchains=["msvc_x64"],
        requires=["nasm"],
        # Seven, measured, and the whole project: main, CronosSleep,
        # bCompare, findPattern, findInModule, findGadget and the NASM
        # routine QuadSleep. InitializeTimerMs is a macro and the "end"
        # label inside QuadSleep is a two-instruction tail, so neither is
        # counted. See Recipe.min_functions - this is a project that
        # genuinely contains that few functions, not a build that produced
        # too few.
        min_functions=7,
        build_flags=_FLAGS,
        notes="Sleep obfuscation via waitable timers and a hand-written ROP "
              "chain, beside Ekko (timer queues) and Foliage (APCs) in this "
              "corpus. Seven functions is the whole project - main, "
              "CronosSleep, bCompare, findPattern, findInModule, findGadget "
              "and the NASM routine QuadSleep - so min_functions=7 against "
              "the corpus floor of eight, the same treatment "
              "Obfuscator4g3nt47 gets. InitializeTimerMs is a macro rather "
              "than a function and the 'end' label inside QuadSleep is a "
              "two-instruction add/ret tail below the census floor, so "
              "neither is counted. The reusable part is not the timer code "
              "but findGadget and its helpers: EnumProcessModules over the "
              "loaded modules, a first-section-header parse, and a masked "
              "scan for pop rcx/ret, pop rdx/ret and add rsp,0x20/pop "
              "rdi/ret - bCompare and findPattern are the classic "
              "masked-signature-scan pair, and that shape propagates into "
              "other tooling far more often than the timer code does. MSVC "
              "and x64 only by upstream's own declaration: its makefile "
              "drives cl, rop.asm is NASM [BITS 64] assembled -f win64, and "
              "src/Cronos.c assigns to Rsp, Rip, Rcx, Rdx, R8 and R9, which "
              "exist only in the 64-bit CONTEXT. Built at cl's default /Od "
              "because upstream passes no /O and /O2 would inline bCompare "
              "into findPattern. Upstream's makefile is not used: its "
              "default target begins with 'del /Q bin\\\\*' against a "
              "directory a fresh checkout does not have, which aborts nmake "
              "before anything builds. GPL-3.0, and the only one of the "
              "three sleep-obfuscation families here that ships a licence at "
              "all. Built against the DLL runtime so the MSVC C runtime is "
              "imported rather than linked in. Nothing in the tree is "
              "prebuilt and nothing is vendored.",
    ),
}
