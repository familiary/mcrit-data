"""Cronos built with MSVC, beside the MinGW build of the same commit.

cronos.py records why its artefact is a GCC build and calls that a deviation
worth fixing: upstream's makefile drives ``cl``, so a real sighting of this
project is an MSVC build and a GCC reference matches it only weakly. This
recipe is the fix. The two artefacts differ in the compiler and nothing else -
same commit, same absence of an optimisation switch, same assembly.

What stood in the way was never the recipe. ``src/asm/rop.asm`` is NASM syntax
(``[BITS 64]``, ``[SECTION .text]``, ``GLOBAL``), ml64 will not assemble it,
translating it would mean patching upstream source - which this corpus refuses
- and nasm is not on the windows-2022 image. An earlier attempt at this recipe
failed in CI with exactly ``missing required tools: nasm``. The workflow now
installs nasm, and how it does that is the part to know about here.

**nasm is installed but deliberately kept off PATH**, and this recipe reaches
it through ``%NASM%`` rather than by name. That is not fastidiousness; it
protects data/OpenSSL. OpenSSL's ``Configurations/10-main.conf`` selects its
assembler in ``vc_win64a_info``, and the branch order - read at both pinned
tags rather than assumed - is::

    if (`nasm -v` =~ /NASM version .../) { AS => nasm, perlasm nasm }
    elsif ($disabled{asm})               { AS => ml64, perlasm masm }
    else                                 { die "NASM not found" }

The nasm probe comes first and is **not** guarded by ``$disabled{asm}``, so a
nasm on PATH is chosen even though openssl_msvc.py passes ``no-asm`` - and the
ml64 branch's own comment, "assembler is still used to compile uplink shim",
says an assembler really is invoked in a no-asm build. Putting nasm on PATH
would therefore switch OpenSSL's uplink shim from ml64/masm to nasm/nasm and
silently change, or break, the highest-value artefacts in the corpus. Keeping
it off PATH leaves ``nasm -v`` failing exactly as it always has, so every
existing recipe builds as before by construction. The workflow asserts the
invariant and fails the job if a future package leaks nasm onto PATH.

``requires`` is therefore not set to ``["nasm"]``: ``build.py`` checks that
list with ``shutil.which``, which by design will not find it. The first build
step checks ``%NASM%`` itself and fails loudly if the workflow did not set it,
which is the same guarantee in the place that can actually give it.

Seven functions, the whole project, and the count is the same as the MinGW
recipe's because it is a property of the source rather than of the compiler:
``main``, ``CronosSleep``, ``bCompare``, ``findPattern``, ``findInModule``,
``findGadget`` and the NASM routine ``QuadSleep``. ``InitializeTimerMs`` is a
macro, not a function, and the ``end`` label inside ``QuadSleep`` is a
two-instruction ``add rsp, 0x28; ret`` tail - a branch target below the
ten-instruction census floor. Neither is counted.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Upstream's makefile is not used, the same mechanical reason cronos.py gives:
# its default target is "all: clean compile_asm compile clean_obj", and "clean"
# is "del /Q bin\\*" against a directory a fresh checkout does not have, which
# aborts nmake before anything is built and cannot be fixed from outside the
# file. The commands it would have run are spelled out instead, with the
# compile split from the link so the two PDBs stay separate files.
_MKDIR = "if not exist bin mkdir bin"

# %NASM% rather than nasm, and a guard step rather than Recipe.requires; see
# the docstring.
#
# The guard is its OWN build step, and that is a correctness fix rather than a
# tidying. Written as one line - "if not defined NASM (echo ... & exit /b 1) &&
# "%NASM%" -f win64 ..." - cmd skips the parenthesised body when NASM *is*
# defined and then does not run the right-hand side of the && either, so nasm
# never executed, the step still exited 0, and the failure surfaced two steps
# later as "LINK : fatal error LNK1181: cannot open input file 'bin\\rop.obj'".
# Measured on run 36405142992. Two steps cannot do that: a guard that is a
# no-op when the variable is set, then the assembler on its own.
_GUARD = ('if not defined NASM (echo NASM is not set - the workflow step that '
          'installs nasm and exports it did not run & exit /b 1)')

_ASM = '"%NASM%" -f win64 src\\asm\\rop.asm -o bin\\rop.obj'

# /MD, against cl's default. With no /M switch cl links the static release CRT,
# and that is what put 1947 of VX-API's 4219 functions into that artefact as
# Microsoft's code under the library's name; data/MSVC is this corpus's
# reference for exactly that code.
#
# /Zi and a real /DEBUG, which upstream has no equivalent of at all - its
# makefile passes no debug switch, so the build emits no PDB. MSVC keeps
# symbols in a PDB rather than in a COFF symbol table, and this is an EXE that
# exports nothing, so without one SMDA would name nothing at all and the
# symbol-coverage gate would refuse the build, correctly.
#
# No /O switch, which is upstream's own state and is load-bearing rather than
# an oversight: cl defaults to /Od, and at /Od all six C functions survive as
# separate bodies. At /O2 bCompare folds into findPattern and the
# masked-compare body - one of the more reusable things in this project, and
# the part that propagates into other tooling far more often than the sleep
# trick does - stops existing separately. It also keeps this artefact
# comparable with the MinGW one, which is built at -O0 for the same reason.
#
# /Fd names the compiler PDB separately from the linker PDB. Pointing both at
# one path would have link.exe write the file it is reading type information
# from; nlohmann_msvc.py records the same split for the same reason.
_COMPILE = ('cl /nologo /c /MD /Zi /I headers '
            '/Fdbin\\Cronos.compiler.pdb /Fobin\\ '
            'src\\Main.c src\\Utils.c src\\Cronos.c')

# psapi.lib for EnumProcessModules and GetModuleFileNameExA, which src/Utils.c
# calls and which upstream's single cl invocation gets only because the
# compiler driver passes the default libraries through to the linker.
#
# /Brepro drops the link timestamp so two runs record the same sha256.
# /INCREMENTAL:NO because /DEBUG implies /INCREMENTAL and the /OPT:NO* forms
# below do not suppress it; an incrementally linked image reaches every
# function through a one-instruction jump thunk and
# smdaify.assert_not_incrementally_linked refuses it. /OPT:NOREF keeps bodies
# nothing references and /OPT:NOICF keeps two that compiled alike apart -
# relevant here because bCompare is small and the four findGadget call sites
# differ only in their pattern arguments.
_LINK = ('link /nologo /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF '
         '/PDB:bin\\Cronos.pdb /OUT:bin\\Cronos.exe '
         'bin\\Main.obj bin\\Utils.obj bin\\Cronos.obj bin\\rop.obj '
         'psapi.lib')

_FLAGS = ("/MD /Zi /I headers with no /O switch, so cl's default /Od - "
          "upstream passes no optimisation flag, and /Od is what keeps "
          "bCompare from folding into findPattern; linked /DEBUG /Brepro "
          "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF against psapi.lib, with "
          "nasm -f win64 for src/asm/rop.asm invoked through %NASM% because "
          "nasm is deliberately kept off PATH so OpenSSL's Configure keeps "
          "choosing its ml64 no-asm branch. Upstream's static-CRT default is "
          "replaced with /MD, and /Zi plus /DEBUG are added because upstream "
          "emits no PDB at all and MSVC keeps symbols there")


RECIPES = {
    # The same commit cronos.py pins, so the two artefacts differ in the
    # compiler and nothing else. No tags in the repository, so pinned by full
    # commit and versioned by its date.
    "Cronos_2023-09-26_msvc": Recipe(
        family="Cronos",
        version="2023-09-26",
        upstream="https://github.com/Idov31/Cronos",
        # 35 KB of GPL-3.0, and the only one of the three sleep-obfuscation
        # families here that ships a licence at all.
        license="GPL-3.0",
        source=Source(
            git_url="https://github.com/Idov31/Cronos.git",
            git_ref="474954c90afee6fe7da191fd9a5dc677ef46ccf0"),
        build=[
            BuildStep(_MKDIR),
            BuildStep(_GUARD),
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
                     pdb="bin\\Cronos.pdb"),
            # is_library stays true, as it is for every executable in this
            # corpus; validate.py requires it.
        ],
        toolchains=["msvc_x64"],
        # Deliberately NOT requires=["nasm"]: build.py checks that with
        # shutil.which and nasm is kept off PATH on purpose. The first build
        # step checks %NASM% instead. See the docstring.
        #
        # Seven, and the same seven the MinGW recipe counts, because the count
        # is a property of the source: main, CronosSleep, bCompare,
        # findPattern, findInModule, findGadget and QuadSleep.
        min_functions=7,
        build_flags=_FLAGS,
        notes="The MSVC build of the same commit cronos.py pins, which is the "
              "deviation that recipe flagged and asked to have fixed: "
              "upstream's makefile drives cl, so a real sighting of Cronos is "
              "an MSVC build and the GCC artefact matches it only weakly. The "
              "two now differ in the compiler and nothing else. Seven "
              "functions is the whole project and the count is the same as "
              "the MinGW recipe's because it is a property of the source - "
              "main, CronosSleep, bCompare, findPattern, findInModule, "
              "findGadget and the NASM routine QuadSleep - so "
              "min_functions=7, the same count Obfuscator4g3nt47 is admitted "
              "at. InitializeTimerMs is a macro rather than a function and "
              "the 'end' label inside QuadSleep is a two-instruction add/ret "
              "tail below the census floor, so neither is counted. The "
              "reusable part is not the timer code but findGadget and its "
              "helpers: an EnumProcessModules walk, a first-section-header "
              "parse, and a masked scan for pop rcx/ret, pop rdx/ret and add "
              "rsp,0x20/pop rdi/ret. src/asm/rop.asm is NASM syntax, which "
              "ml64 cannot assemble and which this corpus will not translate "
              "because that would mean patching upstream, so the Windows "
              "workflow installs nasm - but keeps it OFF PATH and exposes it "
              "as %NASM%, which this recipe uses. That is deliberate and "
              "protects data/OpenSSL: OpenSSL's vc_win64a_info probes nasm "
              "BEFORE its $disabled{asm} branch, so a nasm on PATH would be "
              "chosen despite openssl_msvc.py passing no-asm, switching its "
              "uplink shim from ml64/masm to nasm/nasm and changing the "
              "highest-value artefacts here. Built at cl's default /Od "
              "because upstream passes no /O, which keeps all six C functions "
              "separate and keeps this artefact comparable with the MinGW one "
              "built at -O0. Built against the DLL runtime, so the MSVC C "
              "runtime is imported rather than linked in and stays "
              "attributed to data/MSVC. x64 only, as upstream is: rop.asm is "
              "win64 and src/Cronos.c assigns to Rsp, Rip, Rcx, Rdx, R8 and "
              "R9, which exist only in the 64-bit CONTEXT. Nothing in the "
              "tree is prebuilt and nothing is vendored.",
    ),
}
