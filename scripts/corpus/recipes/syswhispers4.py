"""SysWhispers4 (JoasASantos) - the generator's output, MinGW x64.

SysWhispers4 is the fourth generation of jthuraisamy's syscall stub
generator, and the first whose option space is large enough that "cover the
project" has to mean something more specific than "build it". It takes four
architectures, four compilers, four invocation methods, eight SSN resolution
strategies, four name-hash algorithms, eleven independent evasion flags and
eleven function presets. The cross product is about four million points, so
what is built here was chosen by measurement: every point was generated,
compiled and disassembled, and a point is kept only where it contributed a
function body no kept point already had.

What that measurement found, and what it means for an analyst, is that the
axes are not equally interesting.

**The resolver is the signal.** Each `--resolve` strategy contributes exactly
one distinctive body - `SW4_StaticResolve`, `SW4_HellsGate`, `SW4_HalosGate`,
`SW4_TartarusGate` (plus `SW4_IsHooked`), `SW4_SyscallsFromDisk`,
`SW4_RecycledGate`, `SW4_FreshyCalls` - over a shared base of eight helpers
(`SW4_HashStr`, `SW4_GetNtdllBase`, `SW4_GetOwnImageBase`,
`SW4_GetProcByHash`, `SW4_GetProcByName`, `SW4_SortExports`,
`SW4_FindSection`, `SW4_Initialize`). That is the same conclusion
syswhispers.py reached about v2 and v3 from the other direction: the code
worth matching is the single shared resolver, not the per-function stub.

**The stubs are usually below the floor, and sometimes well above it.** At
`--method embedded` a stub is five instructions - `mov r10, rcx`, a
RIP-relative load of the SSN table, `mov eax`, `syscall`, `ret` - and 24 of
them are a degenerate cluster carrying no minhash. Three options change that
completely. `--method randomized` inlines RDTSC-derived entropy into every
stub, `--encrypt-ssn` inlines the XOR decryption, and `--obfuscate` injects
junk from a 14-variant pool; under each, all 24 stubs cross ten instructions
and become 24 distinct bodies. Those three are where this generator's output
is actually recognisable per-function, which is why they are built at both
optimisation levels and in combination.

**Optimisation level is an axis here, not a detail.** The resolver helpers are
`static`, reachable only from `SW4_Initialize`, so at `-O2` - which is what
upstream's own examples/Makefile passes - GCC inlines all eight into the
resolver and the artefact has two bodies over the floor instead of nine. Both
shapes are encountered: `-O2` is what someone building the generator's output
as shipped produces, `-O0` preserves the helpers as separate bodies and is
what a debug build of the same source gives. Neither is a substitute for the
other - measured, they share no body at all - so both are kept. This is the
same reason `data/MinGW` registers `_PROBE_STDIO` at two optimisation levels.

**Determinism had to be arranged.** `core/generator.py` seeds its obfuscator
and its `--encrypt-ssn` key from `os.urandom`, so `--obfuscate`,
`--encrypt-ssn` and `--method egg` emit different source on every run - three
runs of each produced three distinct outputs. Reference data records a sha256
per artefact and is expected to rebuild byte-identically, so
`exercisers/syswhispers_gen.py` seeds a stand-in and the seed is pinned below.
Upstream is not modified.

**What this recipe cannot reach**, with the reason measured rather than
assumed:

* `--arch x86`, `--arch arm64` under `-c mingw` and `-c clang`: the GAS stub
  emitter ignores `--arch` and writes x64 unconditionally. Generated for
  arm64 it emits `mov r10, rcx` and `syscall` and not one `svc` or `w8`; for
  x86 it emits `lea rcx, [rip + ...]`, which i686 GAS rejects with "operand
  type mismatch for `lea'". Those arches are real only on the MASM path, and
  are built by syswhispers4_msvc.py.
* `--arch wow64`: the generator emits `SW.wow64.asm` whatever `-c` says, so
  there is no GAS path at all. MSVC side.
* `--resolve hw_breakpoint`: the generated C uses `__try`/`__except`, which
  mingw-w64 GCC does not implement - "'__try' undeclared". MSVC side.
* `-c clang`: clang 18 cross-compiles this source to a mingw target and its
  codegen differs from GCC's - measured, six bodies that no GCC point
  produces, among them its own `SW4_FreshyCalls`, `SW4_HashStr` and
  `SW4_SortExports`. It is not built because `corpus.toolchain` registers no
  clang toolchain, and adding one means editing a file the MSVC workflow
  treats as pipeline code. Recorded in the README's not-built table.
* `-c nasm`: builds, and adds nothing. The NASM stubs assemble to the same
  instructions as the GAS ones and came back with the same two bodies as
  `freshycalls_O2`, while nasm emits no COFF `.def` directives so the stub
  symbols are lost (3 named SysWhispers4 functions against 28). Dropped on
  the evidence.

Ten more points were built and dropped for contributing no body a kept point
did not already have: `--method embedded` and `--hash-algo djb2` at both
levels (they are the defaults, and identical to the base points),
`--stack-spoof` at both levels (it changes only the MASM stub prologue, which
the GAS path does not emit), `--obfuscate -O0` and all-evasion `-O0` (both
subsumed by the union of the kept points), and `--method egg --resolve
tartarus` (the two compose without producing a third shape).

Honest count: 60 points built, 50 kept, 10 dropped. The kept points carry 199
of the 205 distinct bodies the whole measurement produced; the six missing are
clang's.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# The option points this recipe builds, and what each was measured to
# contribute. `bodies' counts functions of ten instructions or more -
# the floor below which a shared PicHash says nothing - after the
# exerciser's own corpus_exercise is excluded, since that is this
# corpus's code and not SysWhispers4's.
#
#   component                      opt  mode   preset  bodies  fns
#   freshycalls_O0                 -O0  sep    common  9      35
#   freshycalls_O2                 -O2  sep    common  2      28
#   static_O0                      -O0  sep    common  8      35
#   static_O2                      -O2  sep    common  1      27
#   hellsgate_O0                   -O0  sep    common  9      35
#   hellsgate_O2                   -O2  sep    common  1      27
#   halosgate_O0                   -O0  sep    common  9      35
#   halosgate_O2                   -O2  sep    common  2      28
#   tartarusgate_O0                -O0  sep    common  10     36
#   tartarusgate_O2                -O2  sep    common  2      28
#   fromdisk_O0                    -O0  sep    common  9      35
#   fromdisk_O2                    -O2  sep    common  2      28
#   recycledgate_O0                -O0  sep    common  9      35
#   recycledgate_O2                -O2  sep    common  2      28
#   indirect_O2                    -O2  sep    common  2      28
#   indirect_O0                    -O0  sep    common  9      35
#   randomized_O2                  -O2  sep    common  27     28
#   randomized_O0                  -O0  sep    common  35     36
#   egghunt_O2                     -O2  sep    common  4      5
#   egghunt_O0                     -O0  sep    common  11     12
#   hash_crc32_O0                  -O0  sep    common  9      35
#   hash_crc32_O2                  -O2  sep    common  2      28
#   hash_fnv1a_O0                  -O0  sep    common  9      35
#   hash_fnv1a_O2                  -O2  sep    common  2      28
#   hash_ror13_O0                  -O0  sep    common  9      35
#   hash_ror13_O2                  -O2  sep    common  2      28
#   obfuscate_O2                   -O2  sep    common  24     28
#   encryptssn_O2                  -O2  onetu  common  27     28
#   encryptssn_O0                  -O0  onetu  common  34     35
#   etwbypass_O2                   -O2  sep    common  3      29
#   etwbypass_O0                   -O0  sep    common  10     36
#   amsibypass_O2                  -O2  sep    common  3      29
#   amsibypass_O0                  -O0  sep    common  10     36
#   unhookntdll_O2                 -O2  sep    common  5      31
#   unhookntdll_O0                 -O0  sep    common  10     36
#   antidebug_O2                   -O2  sep    common  3      29
#   antidebug_O0                   -O0  sep    common  10     36
#   sleepencrypt_O2                -O2  sep    common  4      31
#   sleepencrypt_O0                -O0  sep    common  11     38
#   vehencrypt_O2                  -O2  sep    common  5      31
#   vehencrypt_O0                  -O0  sep    common  13     39
#   stringencrypt_O2               -O2  sep    common  3      31
#   stringencrypt_O0               -O0  sep    common  12     38
#   modulestomp_O2                 -O2  sep    common  3      29
#   modulestomp_O0                 -O0  sep    common  11     37
#   allevasion_O2                  -O2  onetu  common  40     44
#   randomized_obfuscated_O2       -O2  sep    common  27     28
#   indirect_recycledgate_O0       -O0  sep    common  9      35
#   presetall_O2                   -O2  sep    all     2      89
#   presetall_O0                   -O0  sep    all     9      96
_VARIANTS = (
    ("freshycalls_O0", "-O0", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded")),
    ("freshycalls_O2", "-O2", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded")),
    ("static_O0", "-O0", "sep", "common",
     ("-r", "static", "-m", "embedded")),
    ("static_O2", "-O2", "sep", "common",
     ("-r", "static", "-m", "embedded")),
    ("hellsgate_O0", "-O0", "sep", "common",
     ("-r", "hells_gate", "-m", "embedded")),
    ("hellsgate_O2", "-O2", "sep", "common",
     ("-r", "hells_gate", "-m", "embedded")),
    ("halosgate_O0", "-O0", "sep", "common",
     ("-r", "halos_gate", "-m", "embedded")),
    ("halosgate_O2", "-O2", "sep", "common",
     ("-r", "halos_gate", "-m", "embedded")),
    ("tartarusgate_O0", "-O0", "sep", "common",
     ("-r", "tartarus", "-m", "embedded")),
    ("tartarusgate_O2", "-O2", "sep", "common",
     ("-r", "tartarus", "-m", "embedded")),
    ("fromdisk_O0", "-O0", "sep", "common",
     ("-r", "from_disk", "-m", "embedded")),
    ("fromdisk_O2", "-O2", "sep", "common",
     ("-r", "from_disk", "-m", "embedded")),
    ("recycledgate_O0", "-O0", "sep", "common",
     ("-r", "recycled", "-m", "embedded")),
    ("recycledgate_O2", "-O2", "sep", "common",
     ("-r", "recycled", "-m", "embedded")),
    ("indirect_O2", "-O2", "sep", "common",
     ("-r", "freshycalls", "-m", "indirect")),
    ("indirect_O0", "-O0", "sep", "common",
     ("-r", "freshycalls", "-m", "indirect")),
    ("randomized_O2", "-O2", "sep", "common",
     ("-r", "freshycalls", "-m", "randomized")),
    ("randomized_O0", "-O0", "sep", "common",
     ("-r", "freshycalls", "-m", "randomized")),
    ("egghunt_O2", "-O2", "sep", "common",
     ("-r", "freshycalls", "-m", "egg")),
    ("egghunt_O0", "-O0", "sep", "common",
     ("-r", "freshycalls", "-m", "egg")),
    ("hash_crc32_O0", "-O0", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--hash-algo", "crc32")),
    ("hash_crc32_O2", "-O2", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--hash-algo", "crc32")),
    ("hash_fnv1a_O0", "-O0", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--hash-algo", "fnv1a")),
    ("hash_fnv1a_O2", "-O2", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--hash-algo", "fnv1a")),
    ("hash_ror13_O0", "-O0", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--hash-algo", "ror13")),
    ("hash_ror13_O2", "-O2", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--hash-algo", "ror13")),
    ("obfuscate_O2", "-O2", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--obfuscate")),
    ("encryptssn_O2", "-O2", "onetu", "common",
     ("-r", "freshycalls", "-m", "embedded", "--encrypt-ssn")),
    ("encryptssn_O0", "-O0", "onetu", "common",
     ("-r", "freshycalls", "-m", "embedded", "--encrypt-ssn")),
    ("etwbypass_O2", "-O2", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--etw-bypass")),
    ("etwbypass_O0", "-O0", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--etw-bypass")),
    ("amsibypass_O2", "-O2", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--amsi-bypass")),
    ("amsibypass_O0", "-O0", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--amsi-bypass")),
    ("unhookntdll_O2", "-O2", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--unhook-ntdll")),
    ("unhookntdll_O0", "-O0", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--unhook-ntdll")),
    ("antidebug_O2", "-O2", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--anti-debug")),
    ("antidebug_O0", "-O0", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--anti-debug")),
    ("sleepencrypt_O2", "-O2", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--sleep-encrypt")),
    ("sleepencrypt_O0", "-O0", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--sleep-encrypt")),
    ("vehencrypt_O2", "-O2", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--veh-encrypt")),
    ("vehencrypt_O0", "-O0", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--veh-encrypt")),
    ("stringencrypt_O2", "-O2", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--string-encrypt")),
    ("stringencrypt_O0", "-O0", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--string-encrypt")),
    ("modulestomp_O2", "-O2", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--module-stomp")),
    ("modulestomp_O0", "-O0", "sep", "common",
     ("-r", "freshycalls", "-m", "embedded", "--module-stomp")),
    ("allevasion_O2", "-O2", "onetu", "common",
     ("-r", "freshycalls", "-m", "embedded", "--obfuscate", "--encrypt-ssn", "--stack-spoof", "--etw-bypass", "--amsi-bypass", "--unhook-ntdll", "--anti-debug", "--sleep-encrypt", "--veh-encrypt", "--string-encrypt", "--module-stomp")),
    ("randomized_obfuscated_O2", "-O2", "sep", "common",
     ("-r", "freshycalls", "-m", "randomized", "--obfuscate")),
    ("indirect_recycledgate_O0", "-O0", "sep", "common",
     ("-r", "recycled", "-m", "indirect")),
    ("presetall_O2", "-O2", "sep", "all",
     ("-r", "freshycalls", "-m", "embedded")),
    ("presetall_O0", "-O0", "sep", "all",
     ("-r", "freshycalls", "-m", "embedded")),
)

_SEED = "20260101"
_GEN = "{repo}/scripts/corpus/exercisers/sw4_build.py"

# Upstream's examples/Makefile passes -O2; -O0 is the second flavour the
# docstring explains. Nothing else of the compile line varies between points.
_FLAGS = ("-shared, -O2 or -O0 per component, -DWAIT_TYPE=ULONG "
          "-DTIMER_TYPE=ULONG for the two enum types mingw-w64 omits; "
          "linked -Wl,--no-insert-timestamp -Wl,--disable-auto-image-base "
          "-Wl,--image-base,0x180000000 so the recorded sha256 is stable "
          "across rebuilds; generated with SW_SEED=" + _SEED)


def _steps_and_artifacts():
    """One generate/derive/compile step and one artefact per option point."""
    steps, artifacts = [], []
    for component, opt, mode, preset, args in _VARIANTS:
        out = "bld/%s/sw4_%s.dll" % (component, component)
        steps.append(BuildStep(
            'python %s --cc "{cc}" --opt=%s --mode %s --seed %s --out %s '
            "-- -p %s -c mingw -a x64 %s"
            % (_GEN, opt, mode, _SEED, out, preset, " ".join(args))))
        artifacts.append(Artifact(path=out, component=component))
    return steps, artifacts


_STEPS, _ARTIFACTS = _steps_and_artifacts()


RECIPES = {
    "SysWhispers4_4.2.0": Recipe(
        family="SysWhispers4",
        version="4.2.0",
        upstream="https://github.com/JoasASantos/SysWhispers4",
        # No LICENSE file of any kind in the repository, and the README states
        # no terms either. Recorded as the fact it is, which is what
        # provenance is for.
        license="none stated",
        source=Source(git_url="https://github.com/JoasASantos/SysWhispers4.git",
                      git_ref="8940ee6bb96175840bcae35fde7c7be41ea49ff1"),
        build=_STEPS,
        artifacts=_ARTIFACTS,
        toolchains=["mingw_x64"],
        build_flags=_FLAGS,
        # Set to what the smallest legitimate point actually contains, which
        # is egghunt_O2 at 15 functions after glue removal, against the
        # corpus-wide floor of 8 - so this raises the floor for 48 of the 50
        # points and lowers it for none.
        #
        # --method egg is small by design rather than by accident, and the
        # artefact was read to confirm it: the egg hunter emits one large
        # stub instead of 24 five-instruction ones, so egghunt_O2's five
        # SysWhispers4 functions are SW4_FreshyCalls at 157 instructions,
        # SW4_NtAllocateVirtualMemory at 125, SW4_HatchEggs at 98,
        # SW4_Initialize at 10 and the exerciser. That is better per-function
        # signal than the embedded points carry, not worse, and it is the
        # opposite of the truncated build this floor exists to catch.
        min_functions=15,
        notes="Built from the generator's own output through a derived "
              "exerciser: the resolver chain is static and reachable only "
              "from SW4_Initialize, and the stubs are reached by nothing at "
              "all, so exercisers/sw4_exerciser.py reads the generated "
              "header and emits a translation unit that calls the one and "
              "takes the address of each of the others. Fifty option points, "
              "chosen by measuring which combinations contribute a function "
              "body no other does; the module docstring records the ten that "
              "were built and dropped, and why.",
    ),
}
