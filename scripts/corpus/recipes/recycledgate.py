"""RecycledGate (thefLink) - FreshyCalls' ordering with Hell's Gate's check.

SysWhispers4 offers this as ``--resolve recycled`` and describes it as the
most resilient of the eight: take the candidate service number from the
stub's position in the virtual-address-sorted export list, the way
FreshyCalls does, and then - if and only if the stub looks clean - confirm it
against the number in the stub's own bytes, the way Hell's Gate does. A hook
that rewrites opcodes defeats the second check and not the first; a hook that
reorders stubs would defeat the first and there is no such hook. This is that
technique in its original form.

Six C functions in ``src/RecycledGate.c`` - ``findNtDll`` walking the PEB's
loader list, ``getSyscall`` doing the sort and the validation,
``djb2_unicode`` and ``djb2`` hashing, ``toLower``, and ``xor_hash``, which
is why the hashes are passed in encrypted - plus two MASM procedures in
``src/GateTrampolin.asm``: ``PrepareSyscall`` stores the number and the
gate address, ``DoSyscall`` jumps to it. ``Sample/Main.c`` is the driver and
supplies ``main``.

**MSVC and x64 only**: ``GateTrampolin.asm`` is MASM and needs ``ml64``.

**Built from ``src/`` plus ``Sample/Main.c``**, which is what
``Sample/Sample.vcxproj`` compiles, driven as three commands rather than
through msbuild. ``HashGenerator/`` is deliberately left out - it is a
separate host-side utility that prints hashes for the developer and shares
no code with the gate.

**No LICENSE file** in the repository. Recorded as the fact it is.

Nothing is run. The EXE is compiled, assembled, linked and disassembled.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_STEPS = (
    BuildStep("cl /nologo /c /O2 /MD /Zi /Isrc /ISample /Fdrg.pdb "
              "/Forecycledgate.obj src\\RecycledGate.c"),
    BuildStep("cl /nologo /c /O2 /MD /Zi /Isrc /ISample /Fdrg.pdb "
              "/Fomain.obj Sample\\Main.c"),
    BuildStep("ml64 /nologo /c /Fogate_asm.obj src\\GateTrampolin.asm"),
    BuildStep("link /nologo /DEBUG /Brepro /OPT:NOREF /OPT:NOICF "
              "/INCREMENTAL:NO /PDB:rg.pdb /OUT:recycledgate.exe "
              "recycledgate.obj main.obj gate_asm.obj"),
)


RECIPES = {
    "RecycledGate_2022-02-03": Recipe(
        family="RecycledGate",
        version="2022-02-03",
        upstream="https://github.com/thefLink/RecycledGate",
        license="none stated",
        source=Source(git_url="https://github.com/thefLink/RecycledGate.git",
                      git_ref="66a180460c8edf64d83626f6214530a2a3c51949"),
        build=list(_STEPS),
        artifacts=[Artifact(path="recycledgate.exe",
                            component="recycledgate.exe",
                            pdb="rg.pdb",
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
        # Six C functions in src/, two MASM procedures, and main. Nine is
        # what the project has; the floor is set to it so a build that drops
        # either object still fails.
        min_functions=9,
        notes="The gate itself plus the sample driver that instantiates it, "
              "which is what Sample.vcxproj compiles. HashGenerator/ is "
              "excluded: it is a host-side utility that prints hashes and "
              "shares no code with the gate. MASM means ml64 and a Windows "
              "runner.",
    ),
}
