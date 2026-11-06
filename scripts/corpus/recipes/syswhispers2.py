"""SysWhispers2 (jthuraisamy) - the shared resolver, MinGW GAS stubs.

The README's "Targets investigated but not built" table had a row saying
SysWhispers2 and SysWhispers3 "cross-build cleanly, but the generated stubs
are 2-15 instructions differing by one immediate - a large, low-value
cluster", and covered v1 instead. That reading of the stubs is correct and is
confirmed again here. What it left out is the other half, which
syswhispers.py's own docstring names: "in v2 and v3 the code worth matching
is not the per-function stub at all but the single shared resolver they call,
which is C and needs no MASM; covering it is a separate question from this
recipe." This is that question answered.

The resolver is four functions and they are the whole point:
``SW2_PopulateSyscallList`` walks ntdll's export directory, collects every
``Zw*`` entry and sorts them by virtual address - 118 instructions at -O2 -
``SW2_GetSyscallNumber`` indexes that sorted table, ``SW2_HashSyscall``
computes the ROR13-style name hash, and under the randomised flavour
``SW2_GetRandomSyscallAddress`` picks an unrelated ntdll stub's ``syscall``
instruction to jump to. All four are ``EXTERN_C`` with external linkage, so
unlike SysWhispers4 they need no exerciser: a DLL built from the generated
``.c`` contains them and MinGW's COFF symbol table names them.

**The seed had to be pinned.** ``syswhispers.py:14`` takes
``random.randint(2**28, 2**32-1)`` as ``SW2_SEED``, and that seed keys every
function-name hash in the output, so three runs produce three different
``SW2_HashSyscall`` bodies and three different hash tables. Measured
unseeded, each option point looked as though it contributed its own
resolver; seeded, the four bodies above are one per flavour, which is what
the evidence actually supports. ``exercisers/syswhispers_gen.py`` does the
seeding without modifying upstream.

**Which points are built, and why these.** One generator run emits all
twelve combinations of {std, rnd} x {x86, x64} x {masm, nasm, gas}, so the
axes that matter are the stub flavour and the architecture, and the recipe
names the file it wants. GAS is the flavour here because it is the one
mingw-w64 assembles; the MASM flavour is the same instructions through
``ml``/``ml64`` and belongs to a Windows runner.

Measured over the four points, 38 distinct bodies across this family and the
two v3 repositories, of which this family contributes nine:

* ``rnd`` at both widths contributes four bodies each, all four of them
  unique to the randomised flavour - the extra ``SW2_GetRandomSyscallAddress``
  and a different ``SW2_PopulateSyscallList``, ``SW2_GetSyscallNumber`` and
  ``SW2_HashSyscall``, because the randomised path changes what the resolver
  stores.
* ``std`` x86 contributes one body the x64 points do not have. x86 is a
  separate axis rather than a smaller copy: mingw-w64 decorates C symbols
  with a leading underscore and 32-bit PIC reaches the GOT through a
  different sequence, so ``_SW2_PopulateSyscallList`` is not
  ``SW2_PopulateSyscallList``.
* ``std`` x64 is built at ``--preset all`` rather than ``common``. Measured at
  ``common`` it contributed no body that the ``all`` point does not also
  have, and ``all`` carries 546 functions against 95, so it is the broader
  stub sample for the same resolver.

**SysWhispers2_x86 is a different thing and is still absent.** That is the
pre-generated MASM directory in the upstream repository, which ships no
licence file; this recipe generates its own output from ``syswhispers.py``
and the repository's own LICENSE covers it.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_SEED = "20260101"
_BUILD = "{repo}/scripts/corpus/exercisers/syswhispers23_build.py"

#   component            arch  stub file               preset  extra cflags
_VARIANTS = (
    ("std_presetall",    "x64", "*Stubs.std.x64.s",    "all",    ""),
    ("std",              "x86", "*Stubs.std.x86.s",    "common", ""),
    ("rnd",              "x64", "*Stubs.rnd.x64.s",    "common", "-DRANDSYSCALL"),
    ("rnd",              "x86", "*Stubs.rnd.x86.s",    "common", "-DRANDSYSCALL"),
)


def _for(arch):
    steps, artifacts = [], []
    for component, var_arch, stub, preset, cflags in _VARIANTS:
        if var_arch != arch:
            continue
        out = "bld/%s/sw2_%s.dll" % (component, component)
        steps.append(BuildStep(
            'python %s --cc "{cc}" --opt=-O2 --seed %s --out %s --stub %s '
            '--cflags="%s" -- -p %s -a %s -l all'
            % (_BUILD, _SEED, out, stub, cflags, preset, arch)))
        artifacts.append(Artifact(path=out, component=component))
    return steps, artifacts


_X64_STEPS, _X64_ARTIFACTS = _for("x64")
_X86_STEPS, _X86_ARTIFACTS = _for("x86")

_NOTES = ("Built from the generator's own output. The artefact carries the "
          "four shared resolver functions, which are what an implant copying "
          "this generator contains and what is worth matching; the "
          "per-function stubs are 2 to 15 instructions each and sit below "
          "the ten-instruction floor, as the README's original row said. "
          "The generator's SW2_SEED is pinned by "
          "exercisers/syswhispers_gen.py, without which the name-hash "
          "immediates - and so every body carrying them - differ on every "
          "run.")
_FLAGS = ("-O2 -shared, GAS stub flavour assembled by the mingw-w64 "
          "assembler, -DRANDSYSCALL on the randomised points; generated with "
          "SW_SEED=" + _SEED)


RECIPES = {
    "SysWhispers2_2022-09-03_x64": Recipe(
        family="SysWhispers2",
        version="2022-09-03",
        upstream="https://github.com/jthuraisamy/SysWhispers2",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/jthuraisamy/SysWhispers2.git",
                      git_ref="05ad0d9ec769fac2776c992d2cb55b09bd604f9a"),
        build=_X64_STEPS,
        artifacts=_X64_ARTIFACTS,
        toolchains=["mingw_x64"],
        build_flags=_FLAGS,
        # After the measured MinGW glue baseline is subtracted, which takes
        # about fifty runtime functions out of each artefact - so this is far
        # below the raw SMDA totals (95 at --preset common, 546 at
        # --preset all) and is the smallest post-filter count measured here.
        min_functions=35,
        notes=_NOTES,
    ),
    "SysWhispers2_2022-09-03_x86": Recipe(
        family="SysWhispers2",
        version="2022-09-03",
        upstream="https://github.com/jthuraisamy/SysWhispers2",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/jthuraisamy/SysWhispers2.git",
                      git_ref="05ad0d9ec769fac2776c992d2cb55b09bd604f9a"),
        build=_X86_STEPS,
        artifacts=_X86_ARTIFACTS,
        toolchains=["mingw_x86"],
        build_flags=_FLAGS,
        # Post-glue-filter, as above: measured 36 on the std point and 38 on
        # the randomised one.
        min_functions=35,
        notes=_NOTES,
    ),
}
