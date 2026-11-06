"""Hell's Gate (am0nsec, RtlMclovin) - SSN recovery from ntdll's own stub.

The technique every later gate is named after, and the one SysWhispers4
offers as ``--resolve hells_gate``. It walks ntdll's export directory,
hashes each name with djb2, and for the ones it wants reads the service
number straight out of the stub's first bytes - the ``mov r10, rcx; mov eax,
<ssn>`` prologue - rather than carrying a table. If the stub has been
hooked, the bytes it reads are the hook's and the read fails, which is the
limitation Halo's Gate and Tartarus' Gate exist to work around.

Eight C functions and two MASM procedures, which is the whole project:
``RtlGetThreadEnvironmentBlock`` reads the TEB from ``gs:[0x30]``, ``djb2``
hashes, ``GetImageExportDirectory`` and ``GetVxTableEntry`` do the parse and
the SSN read, ``VxMoveMemory`` is a hand-rolled memcpy, ``Payload`` is the
demonstration, ``wmain`` drives it, and ``HellsGate``/``HellDescent`` in
hellsgate.asm are the two halves of the indirect invocation - the first
stores the service number in a module-level variable, the second issues the
``syscall``.

**MSVC and x64 only, and not by this recipe's choice.** hellsgate.asm is
MASM and is rejected by both nasm and GAS, so it needs ``ml64``; the same
constraint that puts SysWhispers v1 on a Windows runner. The project ships
a .sln with a single x64 configuration.

**Built as an EXE**, which is what the project is - ``wmain`` is its entry
point and the solution produces a console application. That does put the
MSVC startup glue in the image, and the measured baseline in
``corpus/baseline.py`` subtracts what its probes reach;
``__scrt_common_main_seh`` is the known survivor and is a baseline question
rather than this recipe's. Driving cl, ml64 and link directly rather than
msbuild because the .sln adds nothing here and the three commands are
shorter than the retargeting a project file would need.

**No LICENSE file** of any kind in the repository, at this commit or any
other. Recorded as the fact it is.

Nothing is run. The EXE is compiled, assembled, linked and disassembled.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# /MD not /MT; /Zi and a PDB because MSVC writes no COFF symbol table and
# the project exports nothing, so without one SMDA names almost nothing.
# No /GL. /Brepro, /OPT:NOREF, /OPT:NOICF and /INCREMENTAL:NO for the
# reasons the corpus README records.
_STEPS = (
    BuildStep("cl /nologo /c /O2 /MD /Zi /FdHellsGate\\hg.pdb "
              "/FoHellsGate\\main.obj HellsGate\\main.c"),
    BuildStep("ml64 /nologo /c /FoHellsGate\\hellsgate_asm.obj "
              "HellsGate\\hellsgate.asm"),
    BuildStep("link /nologo /DEBUG /Brepro /OPT:NOREF /OPT:NOICF "
              "/INCREMENTAL:NO /PDB:HellsGate\\hg.pdb "
              "/OUT:HellsGate\\hellsgate.exe "
              "HellsGate\\main.obj HellsGate\\hellsgate_asm.obj"),
)


RECIPES = {
    "HellsGate_2021-06-28": Recipe(
        family="HellsGate",
        version="2021-06-28",
        upstream="https://github.com/am0nsec/HellsGate",
        license="none stated",
        source=Source(git_url="https://github.com/am0nsec/HellsGate.git",
                      git_ref="1d860c0734c0e35a2f026d9a04856ded19dfdf31"),
        build=list(_STEPS),
        artifacts=[Artifact(path="HellsGate/hellsgate.exe",
                            component="hellsgate.exe",
                            pdb="HellsGate/hg.pdb",
                            # is_library stays true, as it is for every
                            # executable in this corpus: MCRIT keys its
                            # library-versus-malware views off that flag and
                            # validate refuses a reference sample without it.
                            # It says "this is reference material", not "this
                            # is a .dll".
                            is_library=True)],
        toolchains=["msvc_x64"],
        build_flags=("cl /O2 /MD /Zi, assembled with ml64, linked /DEBUG "
                     "/Brepro /OPT:NOREF /OPT:NOICF /INCREMENTAL:NO"),
        # The project is eight C functions and two MASM procedures and there
        # is no eleventh. Set to ten so a build that loses the assembly half
        # - the one accident that matters here - still fails.
        min_functions=10,
        notes="The whole project: eight C functions and the two MASM "
              "procedures in hellsgate.asm. Built as the EXE it is, so the "
              "MSVC startup glue is present and is subtracted by the "
              "measured baseline rather than by this recipe. MASM means "
              "ml64 and a Windows runner; no GCC equivalent exists.",
    ),
}
