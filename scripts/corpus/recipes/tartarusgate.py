"""Tartarus' Gate (trickster0) - Hell's Gate extended to hooked stubs.

A fork of am0nsec/HellsGate, and a separate family rather than a second
component of it because what it changes is the technique. Hell's Gate reads
the service number out of ntdll's stub and gives up when the stub has been
hooked. Tartarus' Gate handles the hooked case: when the first bytes are not
the expected ``mov r10, rcx`` prologue it walks to a neighbouring stub -
``UP`` and ``DOWN`` are defined as -32 and +32, one stub's width - reads the
number there, and corrects by the number of stubs it moved, since the kernel
assigns them in image order. It also recognises both the near and the far
JMP forms a hook can take, which is what SysWhispers4's feature table means
by crediting it with "near+far JMP" where it marks SysWhispers3 as partial.

Measured against its parent: ``HellsGate/main.c`` differs by 185 diff lines
and ``hellsgate.asm`` by 18, so this is a real reimplementation of the
resolver and not a renamed copy. It adds an ``NtWriteVirtualMemory`` entry
to the VX table and pulls in ``<stdio.h>``, so unlike Hell's Gate it does
link part of the C runtime.

**MSVC and x64 only**, for its parent's reason: the assembly half is MASM
and needs ``ml64``.

**No LICENSE file** in the repository. Recorded as the fact it is.

The file layout is its parent's - a ``HellsGate/`` directory holding
``main.c``, ``hellsgate.asm`` and ``structs.h`` - so the build steps below
name those paths and not the project's own name. Nothing is run.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_STEPS = (
    BuildStep("cl /nologo /c /O2 /MD /Zi /FdHellsGate\\tg.pdb "
              "/FoHellsGate\\main.obj HellsGate\\main.c"),
    BuildStep("ml64 /nologo /c /FoHellsGate\\tartarus_asm.obj "
              "HellsGate\\hellsgate.asm"),
    BuildStep("link /nologo /DEBUG /Brepro /OPT:NOREF /OPT:NOICF "
              "/INCREMENTAL:NO /PDB:HellsGate\\tg.pdb "
              "/OUT:HellsGate\\tartarusgate.exe "
              "HellsGate\\main.obj HellsGate\\tartarus_asm.obj"),
)


RECIPES = {
    "TartarusGate_2022-01-25": Recipe(
        family="TartarusGate",
        version="2022-01-25",
        upstream="https://github.com/trickster0/TartarusGate",
        license="none stated",
        source=Source(git_url="https://github.com/trickster0/TartarusGate.git",
                      git_ref="ebe05eafd5ed466a6bb944b88ab422725a61d4f5"),
        build=list(_STEPS),
        artifacts=[Artifact(path="HellsGate/tartarusgate.exe",
                            component="tartarusgate.exe",
                            pdb="HellsGate/tg.pdb",
                            is_library=False)],
        toolchains=["msvc_x64"],
        build_flags=("cl /O2 /MD /Zi, assembled with ml64, linked /DEBUG "
                     "/Brepro /OPT:NOREF /OPT:NOICF /INCREMENTAL:NO"),
        # Its parent's eight C functions plus the hooked-stub walk, and the
        # two MASM procedures. Ten is the floor for the same reason as
        # hellsgate.py: it fails a build that loses the assembly half.
        min_functions=10,
        notes="A fork of am0nsec/HellsGate that handles the case its parent "
              "gives up on - a hooked stub, read by walking to a "
              "neighbouring one 32 bytes away and correcting the service "
              "number by the distance moved, recognising both the near and "
              "far JMP hook forms. 185 diff lines in main.c against its "
              "parent, so a separate family rather than a second component. "
              "MASM means ml64 and a Windows runner.",
    ),
}
