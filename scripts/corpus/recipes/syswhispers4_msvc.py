"""SysWhispers4 (JoasASantos) - the MASM half, on a Windows runner.

syswhispers4.py covers what mingw-w64 can reach, which is x64 with GAS
stubs. Four things are only on this side, and the first three are not
choices:

* **WoW64.** See below; it is the one 32-bit output that assembles.
* **WoW64.** The generator writes ``SW.wow64.asm`` whatever ``-c`` says, so
  there is no GAS path at all. The file is Heaven's Gate: 151 far-jump and
  segment-selector references against zero in the x64 output, and it
  declares ``.686``, so ``ml`` accepts it.
* **``--resolve hw_breakpoint``.** The generated C uses ``__try``/
  ``__except``, which mingw-w64 GCC does not implement. This is the only
  resolver of the eight that MinGW cannot build, and it is the one that
  reads SSNs out of debug registers through a vectored exception handler
  rather than out of ntdll's bytes.

**Two of the four architectures are not built, and the reasons are
different.** ``--arch x86`` emits a MASM file that declares ``.386`` and then
issues ``sysenter``; ``ml`` rejects every stub with "error A2085: instruction
or register not accepted in current CPU mode". That is a defect in the
generated file - no option to ``ml`` overrides a CPU directive, and the
directive is in the output, so nobody can assemble SysWhispers4's x86 MASM as
shipped. ``--arch arm64`` emits real ARM64 (76 ``svc``/``w8`` references) but
needs ``armasm64``, which the runner does not have. Both are in the README's
not-built table; WoW64 covers the 32-bit side instead.

Beyond those, MSVC is a separate axis in its own right for the same reason
the README's MSVC section gives: a MinGW reference matches an MSVC-built
binary only weakly, and most Windows software an analyst meets is
MSVC-built. The resolver points below are therefore the same strategies
syswhispers4.py builds, through a different code generator.

**Symbols come from the PDB.** MSVC writes no COFF symbol table, and the
resolver chain is ``static``, so without ``/Zi`` and a declared PDB SMDA can
name only the exported stubs - which is how a VX-API DLL that exports
nothing came back with 1 of 4147 functions named. Each point declares its
own.

**The object names collide.** ``SW.c`` and ``SW.asm`` both want ``SW.obj``;
upstream's own NMakefile works around the same clash. The assembler output
goes to ``SW_asm.obj``.

MSVC mandates followed, each for the reason the README records: ``/MD`` not
``/MT``, no ``/GL`` or ``/LTCG``, ``/OPT:NOREF /OPT:NOICF`` so nothing the
exerciser only takes the address of is folded away, ``/Brepro`` so two runs
of one commit produce identical bytes, and ``/INCREMENTAL:NO`` because
``/DEBUG`` implies ``/INCREMENTAL`` and the ``/OPT:NO*`` forms do not
suppress it.

**Known gap, not worked around.** These artefacts are linked ``/MD``, so the
C runtime is imported rather than compiled in, but the C++/EH and startup
glue MSVC emits into every image is subtracted by the measured baseline in
``corpus/baseline.py`` and not by this recipe. Where a probe does not reach
a symbol it survives under this family's name; ``printf``/``vprintf`` and
``__scrt_common_main_seh`` are the known cases, the last of which
``validate --deep`` already fails on across Lua, MemoryModule and bzip2.
Work on those probes is in flight elsewhere and nothing here tries to
anticipate it.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_SEED = "20260101"
_BUILD = "{repo}/scripts/corpus/exercisers/sw4_build_msvc.py"

#   component                 arch     resolver        method      preset
_VARIANTS = (
    # The eight resolvers through MSVC's code generator, x64.
    ("freshycalls",           "x64", "freshycalls",   "embedded", "common"),
    ("static",                "x64", "static",        "embedded", "common"),
    ("hellsgate",             "x64", "hells_gate",    "embedded", "common"),
    ("halosgate",             "x64", "halos_gate",    "embedded", "common"),
    ("tartarusgate",          "x64", "tartarus",      "embedded", "common"),
    ("fromdisk",              "x64", "from_disk",     "embedded", "common"),
    ("recycledgate",          "x64", "recycled",      "embedded", "common"),
    # MinGW cannot build this one at all: __try/__except.
    ("hwbreakpoint",          "x64", "hw_breakpoint", "embedded", "common"),
    # The stub-shaping methods, which are where MASM differs from GAS.
    ("indirect",              "x64", "freshycalls",   "indirect", "common"),
    ("randomized",            "x64", "freshycalls",   "randomized", "common"),
    ("egghunt",               "x64", "freshycalls",   "egg",      "common"),
    ("presetall",             "x64", "freshycalls",   "embedded", "all"),
    # --arch x86 is NOT here: see the docstring. Its MASM declares .386 and
    # then emits sysenter, which ml rejects outright.
    # WoW64: Heaven's Gate, MASM only, built by the x86 leg.
    ("wow64_freshycalls",     "x86", "freshycalls",   "embedded", "common"),
    ("wow64_hellsgate",       "x86", "hells_gate",    "embedded", "common"),
)

# ARM64 is not built. The generator does emit real ARM64 - 76 svc/w8
# references against zero in anything the GAS emitter produces for the same
# --arch - but assembling it needs armasm64, and a step that may fail cannot
# carry a declared artefact: the pipeline fails the whole recipe on a missing
# one, which is what run 42222222313 did, taking five good artefacts with it.
# Recorded in the README's not-built table instead.


def _arch_of(component, var_arch):
    if component.startswith("wow64_"):
        return "wow64"
    return var_arch


def _for(leg):
    steps, artifacts = [], []
    for component, var_arch, resolve, method, preset in _VARIANTS:
        if var_arch != leg:
            continue
        arch = _arch_of(component, var_arch)
        out = "bld\\%s\\sw4_%s.dll" % (component, component)
        steps.append(BuildStep(
            "python %s --arch %s --seed %s --out %s "
            "-- -p %s -c msvc -a %s -r %s -m %s"
            % (_BUILD, arch, _SEED, out, preset, arch, resolve, method)))
        artifacts.append(Artifact(
            path=out.replace("\\", "/"), component=component,
            pdb="bld/%s/sw4_%s.pdb" % (component, component)))
    return steps, artifacts


_X64_STEPS, _X64_ARTIFACTS = _for("x64")
_X86_STEPS, _X86_ARTIFACTS = _for("x86")

_FLAGS = ("cl /O2 /MD /Zi, assembled with ml64/ml/armasm64, linked /DLL "
          "/DEBUG /Brepro /OPT:NOREF /OPT:NOICF /INCREMENTAL:NO; generated "
          "with SW_SEED=" + _SEED)
_NOTES = ("The MASM half of the generator's output: x86, WoW64 and ARM64 "
          "stubs exist in no other form, and --resolve hw_breakpoint is the "
          "one resolver of the eight that mingw-w64 cannot compile because "
          "it uses __try/__except. Built through the same derived exerciser "
          "as the MinGW side, since the resolver chain is static and the "
          "stubs are called by nothing; symbols come from the PDB because "
          "MSVC writes no COFF symbol table.")


RECIPES = {
    "SysWhispers4_4.2.0_msvc_x64": Recipe(
        family="SysWhispers4",
        version="4.2.0",
        upstream="https://github.com/JoasASantos/SysWhispers4",
        license="none stated",
        source=Source(git_url="https://github.com/JoasASantos/SysWhispers4.git",
                      git_ref="8940ee6bb96175840bcae35fde7c7be41ea49ff1"),
        build=_X64_STEPS,
        artifacts=_X64_ARTIFACTS,
        toolchains=["msvc_x64"],
        build_flags=_FLAGS,
        # Set to what the smallest legitimate point actually contains, which
        # is the egg-hunt one at 9 functions after glue removal - measured on
        # run 42223469188, where it was the single artefact that failed a
        # floor of 15. The egg hunter emits one large stub instead of 24
        # five-instruction ones, so it is small by design; the MinGW side of
        # the same point measured 15 because mingw links more runtime into
        # the image than /MD does, not because it contains more of the
        # project.
        min_functions=9,
        notes=_NOTES,
    ),
    "SysWhispers4_4.2.0_msvc_x86": Recipe(
        family="SysWhispers4",
        version="4.2.0",
        upstream="https://github.com/JoasASantos/SysWhispers4",
        license="none stated",
        source=Source(git_url="https://github.com/JoasASantos/SysWhispers4.git",
                      git_ref="8940ee6bb96175840bcae35fde7c7be41ea49ff1"),
        build=_X86_STEPS,
        artifacts=_X86_ARTIFACTS,
        toolchains=["msvc_x86"],
        build_flags=_FLAGS,
        # Same floor as the x64 leg, for the same reason: these are the two
        # WoW64 points, whose stubs are in the image but unreferenced, and a
        # floor above what the smallest legitimate point measures is how a
        # good artefact gets thrown away.
        min_functions=9,
        notes=_NOTES,
    ),
}
