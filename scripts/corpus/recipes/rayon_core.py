"""rayon-core 1.12.1 and the crossbeam crates it links, from a driver crate.

Tracker issue #7 pairs "rayon-core-1.12.1" with "orion-0.19.9", both quoted
out of a Rust ransomware sample in Microsoft's RIFT post of 2025-06-27.
orion.py builds the orion half and records that 0.19.9 does not exist; it
was re-checked for this recipe on 2026-11-09 and still does not: the
crates.io index for orion lists 0.17.x, 0.18.0-rc.1, 0.18.0 and 0.18.1 and
nothing later, and orion-rs/orion's tags stop at 0.18.1. rayon-core 1.12.1
does exist and is pinned by the sha256 of its crates.io tarball, which is
crates.io's own checksum (1465873a3dfd...dfce2, from index.crates.io).

**Why build it when data/Rust has it.** data/Rust's
rust-crates_1.83.0_x86_64-pc-windows-msvc_opt3-ltooff export carries a
lib.rust.rayon-core family (7052 functions with rayon_core in the name),
but as one x64 MSVC image of one rustc. This adds the other axes - ELF and
MinGW on both architectures, MSVC x86 and x64 - under a family of its own,
and it is a different build: of the PicHashes of 10 or more instructions,
the MinGW x64 artefact shares 11 with that export and 3 with the 1.95.0
optz one, the MSVC x64 artefact 14 and 3, and every other artefact here
none with any of the eight data/Rust files.

**The crossbeam crates.** rayon-core's scheduler is built on
crossbeam-deque (work-stealing deques) and crossbeam-epoch (their memory
reclamation), with crossbeam-utils for backoff and cache padding. The issue
asks for those to be recorded as covered, so they are kept in the image
under their own crate namespaces rather than excluded: a function named
crossbeam_deque:: or crossbeam_epoch:: is that crate's, and the counts are
given separately below. crossbeam-utils contributes no function of its own
in any artefact - Backoff and CachePadded are inlined into their callers -
so it is covered only as inlined code. The versions are pinned by checksum
in the driver's Cargo.lock: crossbeam-deque 0.8.6, crossbeam-epoch 0.9.18,
crossbeam-utils 0.8.21, which are the newest releases that existed on
2025-06-27 (the next ones, 0.8.7, 0.9.19 and 0.8.22, are from 2026-07-06),
so the lock resolves the way a build of that date would have.

**Why a driver crate.** rayon-core's join, scope, spawn and broadcast are
generic over the closures they run, so nothing of it is emitted until a
consumer instantiates it. scripts/corpus/exercisers/rayon_core_driver is
that consumer: one #[no_mangle] extern "C" rc_x_* function per public entry
point (a configured ThreadPoolBuilder, the pool's install/join/scope/
scope_fifo/in_place_scope/spawn/spawn_fifo/broadcast/spawn_broadcast, the
same on the global pool, join_context, yield_now/yield_local and
build_scoped). rayon-core is compiled from the pinned tarball through a
cargo patch.crates-io path override, exactly as orion is.

**std, and what is excluded.** Unlike orion this cannot be no_std:
rayon-core needs threads and carries panics between them with
catch_unwind, so the profile is cargo's own release profile with
panic=unwind, and a cdylib links all of std statically.
Recipe.exclude_functions keeps only names under rayon_core::,
crossbeam_deque::, crossbeam_epoch:: or crossbeam_utils:: (and their
<...>/legacy-mangled spellings) and removes everything else - std, core,
alloc, compiler_builtins, the C runtime and the driver's own rc_x_*
exports - after the glue baseline. Drop glue for rayon types
(core::ptr::drop_in_place<rayon_core::...>) goes with core, as orion's
does.

**Measured** (kept + removed as glue + excluded by name = image total; the
rustc is the stable toolchain at build time: 1.97.0 (2d8144b78 2026-07-07)
in the container for ELF and MinGW, and the windows-2022 runner's
(image win22/20261101.353, run 42679913869) for MSVC):

    artefact          x86 kept/glue/excl/total     x64 kept/glue/excl/total
    ELF (gcc13)       190 /   3 /  978 = 1171      192 /   6 /  814 = 1012
    MinGW (mingw13)   303 /  75 / 3203 = 3581      229 /  65 / 2434 = 2728
    MSVC (msvc143)    280 / 176 / 4327 = 4783      279 / 168 / 3285 = 3732

    kept by crate     rayon_core / crossbeam_deque / crossbeam_epoch
    ELF               152 / 14 / 24 (x86)          154 / 14 / 24 (x64)
    MinGW             232 / 23 / 48                172 / 22 / 35
    MSVC              208 / 23 / 49                207 / 23 / 49

**PicHash overlap** (distinct PicHashes of functions with 10 or more
instructions): MinGW x64 against MSVC x64 35 of 163/199, the two LLVM PE
code generators; every other pair of the six artefacts shares none, x86
against x64 included.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_VERSION = "1.12.1"
# crates.io's own checksum of rayon-core-1.12.1.crate (index.crates.io).
_SHA256 = "1465873a3dfdaa8ae7cb14b4383657caab0b3e8a0aa9ae8e04b044854c8dfce2"

_UPSTREAM = "https://github.com/rayon-rs/rayon"
_LICENSE = ("MIT OR Apache-2.0 (rayon-core; crossbeam-deque, crossbeam-epoch "
            "and crossbeam-utils are MIT OR Apache-2.0 as well)")

_CARGO = ("cargo build --release --locked --target-dir target "
          "--manifest-path {repo}/scripts/corpus/exercisers/rayon_core_driver/"
          "1.12.1/Cargo.toml "
          "--config \"patch.crates-io.rayon-core.path='.'\" --target %s")

_RUSTC = BuildStep("rustc -vV")

# The corpus link policy for MSVC: rustc's default is already /MD and passes
# no /GL; these come after rustc's own /OPT:REF,ICF and override them.
_MSVC_RUSTFLAGS = ("-C link-arg=/OPT:NOREF -C link-arg=/OPT:NOICF "
                   "-C link-arg=/Brepro -C link-arg=/INCREMENTAL:NO")

# Keep rayon-core's own code and the three crossbeam crates the issue asks to
# have recorded, each under its own crate namespace; everything else - the
# statically linked std, core and alloc, compiler_builtins, the C runtime and
# the driver's own rc_x_* exports - is excluded by name. Legacy-mangled
# spellings are listed for a build whose symbols arrive undemangled.
_KEEP = r"rayon_core|crossbeam_deque|crossbeam_epoch|crossbeam_utils"
_EXCLUDE = [r"^(?!<?(?:%s)::|_{1,2}ZN\d+(?:%s)|_{1,2}ZN\d+_\$LT\$(?:%s)\.\.)"
            % (_KEEP, _KEEP, _KEEP)]


def _flags(extra):
    return ("cargo --release (opt-level 3, LTO off, codegen-units 16, "
            "panic=unwind, debug info off) --locked; " + extra)


def _make(target, toolchains, artifact, build_flags, notes, steps_before=(),
          env=None, pdb=None):
    return Recipe(
        family="rayon-core",
        version=_VERSION,
        upstream=_UPSTREAM,
        license=_LICENSE,
        source=Source(url="https://static.crates.io/crates/rayon-core/"
                          "rayon-core-%s.crate" % _VERSION,
                      sha256=_SHA256),
        build=list(steps_before) + [
            _RUSTC, BuildStep(_CARGO % target, env=dict(env or {}))],
        artifacts=[Artifact(path="target/%s/release/%s" % (target, artifact),
                            component=artifact.replace("lib", "", 1)
                            if artifact.startswith("lib") else artifact,
                            pdb=pdb)],
        toolchains=toolchains,
        requires=["cargo"],
        exclude_functions=list(_EXCLUDE),
        build_flags=build_flags,
        notes=("Built from a driver crate (scripts/corpus/exercisers/"
               "rayon_core_driver) that instantiates every public entry point "
               "of rayon-core; rayon-core is compiled from the crates.io "
               "tarball pinned by sha256 (= crates.io's checksum) through a "
               "cargo patch.crates-io path override, and crossbeam-deque "
               "0.8.6, crossbeam-epoch 0.9.18 and crossbeam-utils 0.8.21 (the "
               "newest on 2025-06-27, the date of the RIFT post the tracker "
               "issue cites) are pinned by checksum in its Cargo.lock and "
               "built --locked. The crossbeam crates are kept under their own "
               "namespaces and recorded as covered; crossbeam-utils is fully "
               "inlined and contributes no function of its own. std, core, "
               "alloc, the C runtime and the driver's rc_x_* exports are "
               "excluded by name. orion 0.19.9, which the issue pairs with "
               "this, does not exist on crates.io or in orion's tags "
               "(newest 0.18.1; see orion.py). " + notes),
    )


RECIPES = {
    "rayon-core_1.12.1_linux": _make(
        "{platform}-unknown-linux-gnu", ["linux_x86", "linux_x64"],
        "librayon_core_driver.so",
        _flags("i686-unknown-linux-gnu / x86_64-unknown-linux-gnu"),
        "ELF build with rustc 1.97.0 (2d8144b78 2026-07-07). Measured x86: "
        "190 kept + 3 glue + 978 excluded = 1171; x64: 192 + 6 + 814 = 1012."),
    "rayon-core_1.12.1": _make(
        "{platform}-pc-windows-gnu", ["mingw_x86", "mingw_x64"],
        "rayon_core_driver.dll",
        _flags("i686-pc-windows-gnu / x86_64-pc-windows-gnu"),
        "MinGW (windows-gnu) build with rustc 1.97.0 (2d8144b78 2026-07-07). "
        "Measured x86: 303 kept + 75 glue + 3203 excluded = 3581; x64: 229 + "
        "65 + 2434 = 2728."),
}
for _arch, _triple in (("x86", "i686-pc-windows-msvc"),
                       ("x64", "x86_64-pc-windows-msvc")):
    RECIPES["rayon-core_1.12.1_msvc_" + _arch] = _make(
        _triple, ["msvc_" + _arch], "rayon_core_driver.dll",
        _flags(_triple + ", dynamic CRT (/MD), link /OPT:NOREF /OPT:NOICF "
               "/Brepro /INCREMENTAL:NO"),
        "MSVC build (%s) with the stable rustc of the windows-2022 runner "
        "image win22/20261101.353. Measured %s." % (_triple, {
            "x86": "280 kept + 176 glue + 4327 excluded = 4783",
            "x64": "279 kept + 168 glue + 3285 excluded = 3732"}[_arch]),
        steps_before=[BuildStep("rustup target add " + _triple)],
        env={"RUSTFLAGS": _MSVC_RUSTFLAGS},
        pdb="target/%s/release/rayon_core_driver.pdb" % _triple)


# The `debug = true` builds the tracker issue asks for, beside the release
# ones: CARGO_PROFILE_RELEASE_DEBUG=true switches the release profile to full
# debug info and nothing else, under version 1.12.1-debug. Every leg pins its
# rustc with rustup: 1.97.0 for ELF and MinGW (the container's, which built
# the release images), 1.99.1 for MSVC (the runner's stable of the orion MSVC
# release images; the rayon-core release run did not record its rustc).
_MSVC_DEBUG_RUSTC = "1.99.1"
_LOCAL_DEBUG_RUSTC = "1.97.0"


def _debug(name, recipe):
    import dataclasses
    msvc = any(t.startswith("msvc") for t in recipe.toolchains)
    rustc = _MSVC_DEBUG_RUSTC if msvc else _LOCAL_DEBUG_RUSTC
    build = []
    for step in recipe.build:
        env = dict(step.env)
        if step.command.startswith("cargo build"):
            env["CARGO_PROFILE_RELEASE_DEBUG"] = "true"
        env["RUSTUP_TOOLCHAIN"] = rustc
        build.append(dataclasses.replace(step, env=env))
    triple = recipe.artifacts[0].path.split("/")[1]
    build.insert(0, BuildStep("rustup toolchain install %s --profile minimal "
                              "--target %s" % (rustc, triple)))
    head, _, compiler = recipe.notes.partition("(newest 0.18.1; see orion.py). ")
    compiler = compiler.split(" Measured ")[0]
    if msvc:
        compiler = compiler.replace(
            "with the stable rustc of the windows-2022 runner image "
            "win22/20261101.353.",
            "with rustc %s pinned by rustup." % rustc)
    else:
        compiler = compiler.rstrip(" .") + ", pinned by rustup"
    return dataclasses.replace(
        recipe, version=_VERSION + "-debug", build=build,
        build_flags=recipe.build_flags.replace("debug info off",
                                               "debug = true (full debug info)"),
        notes=("debug = true build: identical to the %s recipe except that "
               "CARGO_PROFILE_RELEASE_DEBUG=true turns on full debug info in "
               "the release profile. " % name) + head
              + "(newest 0.18.1; see orion.py). " + compiler.rstrip(" .") + ".")


for _name in list(RECIPES):
    RECIPES[_name.replace("1.12.1", "1.12.1-debug", 1)] = _debug(
        _name, RECIPES[_name])
