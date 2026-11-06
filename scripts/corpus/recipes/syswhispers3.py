"""SysWhispers3 (klezVirus) - the shared resolver, MinGW inline-GAS stubs.

The v3 half of the question syswhispers.py's docstring left open: the code
worth matching in v2 and v3 is the single shared resolver, not the
per-function stub. v3's resolver is five ``EXTERN_C`` functions -
``SW3_PopulateSyscallList``, ``SW3_GetSyscallNumber``,
``SW3_GetSyscallAddress``, ``SW3_GetRandomSyscallAddress`` and
``SW3_HashSyscall`` - so a DLL built from the generated ``.c`` carries them
without an exerciser, and MinGW's COFF symbol table names them.

What v3 adds over v2, and what this recipe is therefore built to show, is
the indirect-syscall machinery: ``SW3_GetSyscallAddress`` locates the
``syscall`` instruction inside ntdll's own stub so the call can jump there
rather than execute ``syscall`` from the implant's own pages, which is what
the ``jumper`` methods use and what makes a return address inside ntdll
rather than inside the sample.

**The seed is pinned**, as for v2 and for the same reason:
``syswhispers.py:174-176`` draws ``SW3_SEED`` from ``random.randint`` and a
two-character egg from ``random.choices``, and the seed keys every
name hash. Measured unseeded, each ``--method`` appeared to contribute its
own ``SW3_HashSyscall`` and ``SW3_PopulateSyscallList``; seeded, those
collapse to the handful of real bodies below. That difference - 42 distinct
bodies unseeded against 31 seeded, over the same thirteen points - is the
clearest argument for pinning it, because the unseeded measurement would
have justified four artefacts where the evidence supports two.

**Which points are built.** ``--method`` is the axis that changes the
resolver; ``--arch`` is a separate axis because mingw-w64 decorates 32-bit C
symbols with a leading underscore and 32-bit PIC reaches the GOT
differently, so the x86 bodies are not the x64 ones. Measured over the four
method/arch points kept:

* ``embedded`` x64 at ``--preset all`` - 549 functions, and the two
  resolver bodies the ``common`` point also had, so ``all`` is kept as the
  broader stub sample and ``common`` dropped as contained in it.
* ``embedded`` x86 - two bodies no x64 point has.
* ``jumper`` x64 and x86 - one body each that ``embedded`` does not have,
  a different ``SW3_PopulateSyscallList``, because the jumper path stores
  the per-stub syscall address alongside the number.

**What is not built here**, measured rather than assumed:

* ``--method jumper_randomized`` contributed no body ``jumper`` did not
  already have, at either width. The randomisation is in the stub assembly,
  which is below the ten-instruction floor, and the C resolver is identical.
  Dropped on the evidence.
* ``--method egg_hunter`` is refused by the generator itself under
  ``-c mingw``: "[-] Egg-Hunter not compatible with MinGW". It needs the
  MASM path and a Windows runner.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_SEED = "20260101"
_BUILD = "{repo}/scripts/corpus/exercisers/syswhispers23_build.py"

#   component   arch   method      preset
_VARIANTS = (
    ("embedded_presetall", "x64", "embedded", "all"),
    ("jumper",             "x64", "jumper",   "common"),
    ("embedded",           "x86", "embedded", "common"),
    ("jumper",             "x86", "jumper",   "common"),
)

_UPSTREAM = "https://github.com/klezVirus/SysWhispers3"
_REF = "31cfc93c9466b52ae79d60925b0b5e0a1f653b88"
_VERSION = "2023-12-23"

_NOTES = ("Built from the generator's own output; no exerciser is needed "
          "because the resolver is EXTERN_C. The artefact carries the five "
          "shared resolver functions, which is what an implant copying this "
          "generator contains; the per-function stubs are short thunks "
          "below the ten-instruction floor. SW3_SEED is pinned by "
          "exercisers/syswhispers_gen.py - unseeded, the name-hash "
          "immediates and every body carrying them differ on every run, and "
          "a measurement made that way reports four distinct resolvers "
          "where there are two.")
_FLAGS = ("-O2 -masm=intel -shared; -masm=intel is required because the "
          "generated inline assembly is Intel syntax with no directive of "
          "its own and GAS otherwise rejects every stub. Generated with "
          "SW_SEED=" + _SEED)


def _recipe(arch, upstream, ref, family, version, min_functions,
            extra_notes=""):
    steps, artifacts = [], []
    for component, var_arch, method, preset in _VARIANTS:
        if var_arch != arch:
            continue
        out = "bld/%s/sw3_%s.dll" % (component, component)
        steps.append(BuildStep(
            'python %s --cc "{cc}" --opt=-O2 --seed %s --out %s '
            '--cflags=-masm=intel -- -p %s -c mingw -m %s -a %s'
            % (_BUILD, _SEED, out, preset, method, arch)))
        artifacts.append(Artifact(path=out, component=component))
    return Recipe(
        family=family,
        version=version,
        upstream=upstream,
        license="MIT",
        source=Source(git_url=upstream + ".git", git_ref=ref),
        build=steps,
        artifacts=artifacts,
        toolchains=["mingw_%s" % arch],
        build_flags=_FLAGS,
        # The count the pipeline applies is after the measured MinGW glue
        # baseline has been subtracted, which removes about fifty runtime
        # functions from each of these artefacts - so this is well below the
        # raw SMDA totals (98 to 549) and is the smallest post-filter count
        # measured on the points this recipe builds. Passed in per
        # architecture because the two differ: 48 on x64 jumper, 72 on x86
        # embedded.
        min_functions=min_functions,
        notes=_NOTES + extra_notes,
    )


RECIPES = {
    "SysWhispers3_%s_x64" % _VERSION: _recipe("x64", _UPSTREAM, _REF,
                                              "SysWhispers3", _VERSION, 45),
    "SysWhispers3_%s_x86" % _VERSION: _recipe("x86", _UPSTREAM, _REF,
                                              "SysWhispers3", _VERSION, 70),
}
