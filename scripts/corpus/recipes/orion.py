"""orion-rs/orion - a pure-Rust cryptography library, two versions, six axes.

**Which versions, and why not 0.19.9.** Tracker issue #7 asks for "orion
0.19.9", taken from a Microsoft RIFT blog post of 2025-06-27 that quotes the
strings `rayon-core-1.12.1` and `orion-0.19.9` out of a Rust ransomware
sample. No such version exists: crates.io and the GitHub tags of
orion-rs/orion both stop at 0.18.1 (0.17.11 was the newest release on
2025-06-07, i.e. when the post appeared; 0.17.12 to 0.17.16, 0.18.0 and
0.18.1 are later). The quoted string cannot be matched to a registry
artefact, so this recipe builds the two real versions that bracket it, as
one family `orion`:

  * **0.17.11** - the newest release when the post appeared, and so the most
    plausible real dependency of a sample analysed then;
  * **0.18.1** - the newest published release.

Both are pinned by the sha256 of the crates.io `.crate` tarball, which is
crates.io's own checksum for that version (0.17.11:
21b3da83b2b4cdc74ab6a556b2e7b473da046d5aa4008c0a7a3ae96b1b4aabb4, 0.18.1:
ce166f9a98c32a49ccf0684ea3be1a99cdebc0694d96e487ee5df844591a3403; both
checked against index.crates.io). The rayon-core 1.12.1 the issue pairs it
with is already in the corpus (family lib.rust.rayon-core, inside
data/Rust/x64/mcrit/rust-crates_1.83.0_x86_64-pc-windows-msvc_opt3-ltooff.mcrit)
and is not repeated here.

**Why a driver crate.** A library crate emits no code until something uses
its API, and orion's primitives are generic or `#[inline]`. The driver,
scripts/corpus/exercisers/orion_driver, is a consumer of the library and
changes nothing in it: one `#[unsafe(no_mangle)] pub extern "C"`
`orion_x_*` function per public primitive of orion's `hazardous` module,
taking pointers and lengths from the caller so nothing folds away. orion is
not copied or edited: the build points cargo at the fetched, checksummed
tarball with `--config patch.crates-io.orion.path='.'`, so what is
compiled is exactly the pinned source. The driver's own dependencies are
the ones orion pulls in (subtle, zeroize, fiat-crypto, and cmov from 0.18),
pinned by crates.io checksum in each version's Cargo.lock and built with
`--locked`.

**no_std, and what that leaves out.** orion's high-level API (`orion::aead`,
`orion::hash`, `orion::kdf`, `orion::pwhash`, `orion::kex`...) needs the
`safe_api` feature, which turns on `std` and `getrandom`. A Rust cdylib with
std links all of std statically, and every one of those thousands of
functions would be filed under the orion family; the pipeline has no
by-name function filter (only the measured C-runtime baseline), so the
`obfstr` route is the one used here: a `#![no_std]`, `panic = "abort"`
driver. orion's `hazardous` module is where the cryptography lives and is
available without std (Argon2 and scrypt need an allocator, which the driver
supplies as a bump allocator over a static arena). The high-level modules
are thin wrappers over it, so what is not covered is the wrapper layer
(PasswordHash/encoded-form handling, `Secret` generation through
getrandom, `kex`, hpke, ct-codecs hex/base64), not the algorithms.
Covered: XChaCha20-Poly1305, ChaCha20-Poly1305, streaming AEAD, the
ChaCha20/XChaCha20 stream ciphers, the CTX committing AEAD, SHA-2 (256, 384,
512), SHA-3 (224-512), SHAKE128/256, BLAKE2b hash and MAC, Poly1305,
HMAC-SHA2, HKDF, PBKDF2, Argon2i, X25519; and on 0.18 additionally BLAKE3
(hash, keyed, MAC), Argon2id and scrypt. Not covered in either version: ML-KEM,
ML-DSA, X-Wing and the HPKE suites (post-quantum and hybrid modules no
sample of this kind is expected to use).

Because 0.17 and 0.18 differ in API (0.18 replaced the free functions with
associated functions on `Secret<T>`/`Public<T>`-typed structs), each version
has its own driver source, v17.rs and v18.rs, with the same function names
and the same coverage of what 0.17 has.

**The driver's own code stays in the family.** The pipeline cannot exclude
functions by name. The driver's 47 exports are all called `orion_x_*`, are
`#[inline(never)]`, and contain the calls that instantiate orion; plus a
bump allocator (`__rustc::__rust_alloc` and friends), `rust_eh_personality`
(or `__CxxFrameHandler3` on MSVC: precompiled `core` refers to the unwind
personality even though this crate never unwinds, and without a stub the
`.so` fails to load) and the panic handler. Their names are recorded in
the notes of each recipe so a consumer can tell them from orion's code.

**Measured** (kept + removed-as-glue + excluded-by-name = image total; the
rustc is the stable toolchain at build time: 1.97.0 (2d8144b78 2026-07-07,
LLVM 22.1.6) for ELF and MinGW built in the container, 1.99.1 (58cf8f9c3
2026-10-13, LLVM 23.1.1) on the windows-2022 runner for MSVC):

    artefact                  x86 kept/glue/excl/total     x64 kept/glue/excl/total
    0.17.11 ELF (gcc13)       175 /   3 /  86 =  264       174 /   6 /  86 =  266
    0.17.11 MinGW (mingw13)   503 /  73 / 823 = 1399       389 /  63 / 682 = 1134
    0.17.11 MSVC (msvc143)    488 / 129 / 891 = 1508       487 / 121 / 818 = 1426
    0.18.1  ELF (gcc13)       175 /   3 /  98 =  276       173 /   6 /  96 =  275
    0.18.1  MinGW (mingw13)   603 /  73 / 871 = 1547       545 /  63 / 739 = 1347
    0.18.1  MSVC (msvc143)    573 / 130 / 973 = 1676       568 / 121 / 893 = 1582

The ELF images are garbage-collected by the linker, so they carry the
functions the driver reaches (about 175). The PE images carry roughly three
times as many orion functions: GNU ld's --gc-sections cannot drop anything
that has unwind data (the PE linker script keeps .eh_frame/.pdata), and this
corpus's MSVC policy (/OPT:NOREF /OPT:NOICF) keeps every function of every
object pulled in. So the PE artefacts also hold orion code the driver never
calls (the ML-KEM and HPKE modules, among others), which is more complete
reference data, not an accident; the same policy is why the precompiled
`core`/`alloc` come along, and why they are excluded by name.

**What the exclusion removes.** `Recipe.exclude_functions` (new, with the
pipeline hooks in smdaify.py/pipeline.py) drops every function whose
demangled name does not start with `orion::` or `<orion::` (plus the
legacy-mangled spellings), after the glue baseline: the precompiled core,
alloc and compiler_builtins, the C runtime, the driver's own `orion_x_*`
exports, allocator and panic glue, and the statically linked dependencies.
Of those, `subtle` and `zeroize` already have families of their own in
data/Rust (lib.rust.subtle, lib.rust.zeroize); `fiat-crypto` and `cmov` do
not, and are excluded rather than misfiled (they are small; a family of
their own is a follow-up). Each provenance entry records the pattern,
`excluded_function_count` and `num_functions_before_exclusion`.
Trait impls of orion types for core traits (`<orion::T as
core::fmt::Debug>::fmt`) stay; blanket impls of core types over orion types
(`<&orion::T as ...>`) and `core::ptr::drop_in_place<orion::T>` do not.

**PicHash overlap** (distinct PicHashes of functions with 10 or more
instructions; kept functions only):

  * within one version, ELF against MinGW: 0 of 136/274 (0.17.11 x64),
    0 of 149/332 (x86), 0 of 142/420 and 0 of 160/475 (0.18.1); x64 against
    x86: 0 everywhere. Different compilers, relocation models and
    inlining decisions give different bytes even from one Rust source.
  * MSVC against MinGW: 169 of 319/274 (0.17.11 x64), 37 (x86), 263 of
    420/420 (0.18.1 x64), 54 (x86): both are LLVM-built PE images with the
    same code generator, so they share code. MSVC against ELF: 0 on x64, 10
    on x86.
  * 0.17.11 against 0.18.1: ELF x64 39 of 136/142, x86 12; MinGW x64 68 of
    274/420, x86 101; MSVC x64 86 of 319/420, x86 87. The two versions share
    their primitives (BLAKE2b, SHA-2, ChaCha20, Poly1305) and differ in the
    API layer and in the 0.18 additions.
  * against the existing Rust data (all eight files of data/Rust, 106,219
    distinct PicHashes of 10-or-more-instruction functions across 100+
    lib.rust.* families, among them lib.rust.chacha20, sha2, sha3, hmac,
    subtle, zeroize and curve25519-dalek): 0 shared with any of the twelve
    orion artefacts. orion implements its primitives itself rather than
    depending on the RustCrypto crates (its dependencies are only subtle,
    zeroize, fiat-crypto, cmov and, with safe_api, getrandom and
    ct-codecs), so chacha20/poly1305/blake2b_simd-style families do not
    appear under orion and nothing in it repeats them.

The same counts are in each recipe's notes.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_VERSIONS = {
    "0.17.11": "21b3da83b2b4cdc74ab6a556b2e7b473da046d5aa4008c0a7a3ae96b1b4aabb4",
    "0.18.1": "ce166f9a98c32a49ccf0684ea3be1a99cdebc0694d96e487ee5df844591a3403",
}

_COMMON_NOTES = (
    "Built from a #![no_std] panic=abort driver crate "
    "(scripts/corpus/exercisers/orion_driver) because a library emits "
    "nothing until used; orion's hazardous module is instantiated, the "
    "std-requiring high-level wrapper layer is not (see the recipe module "
    "docstring). Version note: the tracker issue names orion 0.19.9, which "
    "does not exist in crates.io or in the GitHub tags (newest is 0.18.1); "
    "0.17.11 (newest when the 2025-06-27 Microsoft RIFT post appeared) and "
    "0.18.1 (newest published) are built instead. orion is compiled from the "
    "crates.io tarball pinned by sha256 (= crates.io's checksum), through a "
    "cargo patch.crates-io path override; subtle, zeroize, fiat-crypto "
    "(and cmov on 0.18) are pinned by checksum in the driver's Cargo.lock "
    "and built --locked. The driver's own functions are the orion_x_* "
    "exports, a bump allocator, the panic handler and an eh-personality stub. "
    "Compiler: ")


def _crate(version):
    return Source(url="https://static.crates.io/crates/orion/orion-%s.crate" % version,
                  sha256=_VERSIONS[version])


_CARGO = ("cargo build --release --locked --target-dir target "
          "--manifest-path {repo}/scripts/corpus/exercisers/orion_driver/%s/Cargo.toml "
          "--config \"patch.crates-io.orion.path='.'\" --target %s")

_LICENSE = "MIT, Copyright (c) 2018-%s The orion Developers"

_UPSTREAM = "https://github.com/orion-rs/orion"

# Record the compiler in the build log: the container's is recorded in the
# notes, the Windows runner's is whatever its image ships.
_RUSTC = BuildStep("rustc -vV")

# MSVC: /MD is rustc's default for *-pc-windows-msvc (dynamic CRT) and rustc
# passes no /GL, so only the link policy of this corpus is added. They come
# after rustc's own /OPT:REF,ICF, and a later /OPT overrides an earlier one.
#
# rustc links an MSVC target with /NODEFAULTLIB, and a #![no_std] crate has no
# std to ask for the C runtime, so without help the DLL has neither an entry
# point (_DllMainCRTStartup) nor memcpy/memset. The /MD runtime is therefore
# named explicitly: msvcrt.lib (startup stubs and the import library for the
# dynamic CRT), vcruntime.lib and ucrt.lib. Its code is excluded by name like
# all non-orion code (see _EXCLUDE).
_MSVC_RUSTFLAGS = ("-C link-arg=/OPT:NOREF -C link-arg=/OPT:NOICF "
                   "-C link-arg=/Brepro -C link-arg=/INCREMENTAL:NO "
                   "-C link-arg=msvcrt.lib -C link-arg=vcruntime.lib "
                   "-C link-arg=ucrt.lib")


def _flags(extra):
    return ("cargo --release (opt-level 3, LTO off, codegen-units 16, "
            "panic=abort, debug info off) --locked, driver crate "
            "#![no_std]; " + extra)


# Keep only the orion crate's own code. SMDA demangles Rust names, so the
# usual form is `orion::hazardous::...` or `<orion::T as core::Trait>::m`;
# the legacy-mangled spellings (`_ZN5orion...`, with one more underscore on
# 32-bit PE) are listed too for a build whose symbols arrive undemangled.
# Everything else is
# excluded: precompiled core/alloc, compiler_builtins, the driver's own
# orion_x_* exports, allocator and panic glue, and the statically linked
# dependencies - subtle and zeroize already have families in data/Rust
# (lib.rust.subtle, lib.rust.zeroize); fiat-crypto and cmov are excluded too
# and counted in the notes.
_EXCLUDE = [r"^(?!<?orion::|_{1,2}ZN5orion|_{1,2}ZN\d+_\$LT\$orion\.\.)"]


def _make(version, target, toolchains, artifact, component, build_flags,
          notes, steps_before=(), env=None, pdb=None):
    cargo = BuildStep(_CARGO % (version, target), env=dict(env or {}))
    return Recipe(
        family="orion",
        version=version,
        upstream=_UPSTREAM,
        license=_LICENSE % ("2026" if version == "0.18.1" else "2025"),
        source=_crate(version),
        build=list(steps_before) + [_RUSTC, cargo],
        artifacts=[Artifact(path="target/%s/release/%s" % (target, artifact),
                            component=component, pdb=pdb)],
        toolchains=toolchains,
        requires=["cargo"],
        exclude_functions=list(_EXCLUDE),
        build_flags=build_flags,
        notes=_COMMON_NOTES + notes,
    )


_RUSTC_LOCAL = ("rustc 1.97.0 (2d8144b78 2026-07-07), LLVM 22.1.6, the stable "
                "toolchain of the build container")
_RUSTC_RUNNER = ("rustc 1.99.1 (58cf8f9c3 2026-10-13), LLVM 23.1.1, the stable "
                 "toolchain of the windows-2022 runner image")

# (kept, glue removed, excluded by name) per version, kind and architecture;
# kept + glue + excluded is the image total.
_COUNTS = {
    ("0.17.11", "elf"): {"x86": (175, 3, 86), "x64": (174, 6, 86)},
    ("0.17.11", "mingw"): {"x86": (503, 73, 823), "x64": (389, 63, 682)},
    ("0.17.11", "msvc"): {"x86": (488, 129, 891), "x64": (487, 121, 818)},
    ("0.18.1", "elf"): {"x86": (175, 3, 98), "x64": (173, 6, 96)},
    ("0.18.1", "mingw"): {"x86": (603, 73, 871), "x64": (545, 63, 739)},
    ("0.18.1", "msvc"): {"x86": (573, 130, 973), "x64": (568, 121, 893)},
}


def _measured(version, kind, arches=("x86", "x64")):
    parts = []
    for arch in arches:
        kept, glue, excluded = _COUNTS[(version, kind)][arch]
        parts.append("%s: %d kept + %d glue + %d excluded = %d" %
                     (arch, kept, glue, excluded, kept + glue + excluded))
    return "Measured " + "; ".join(parts) + ". "


def _all(version):
    tag = "orion_" + version
    recipes = {
        tag + "_linux": _make(
            version, "{platform}-unknown-linux-gnu", ["linux_x86", "linux_x64"],
            "liborion_driver.so", "orion_driver.so",
            _flags("i686-unknown-linux-gnu / x86_64-unknown-linux-gnu"),
            "ELF build with " + _RUSTC_LOCAL + ". " + _measured(version, "elf")),
        tag: _make(
            version, "{platform}-pc-windows-gnu", ["mingw_x86", "mingw_x64"],
            "orion_driver.dll", "orion_driver.dll",
            _flags("i686-pc-windows-gnu / x86_64-pc-windows-gnu"),
            "MinGW (windows-gnu) build with " + _RUSTC_LOCAL + ". "
            + _measured(version, "mingw")),
    }
    for arch, triple in (("x86", "i686-pc-windows-msvc"),
                         ("x64", "x86_64-pc-windows-msvc")):
        recipes["%s_msvc_%s" % (tag, arch)] = _make(
            version, triple, ["msvc_" + arch], "orion_driver.dll",
            "orion_driver.dll",
            _flags(triple + ", dynamic CRT (/MD), link /OPT:NOREF "
                   "/OPT:NOICF /Brepro /INCREMENTAL:NO"),
            "MSVC build (%s) with %s. %s" % (triple, _RUSTC_RUNNER,
                                              _measured(version, "msvc", (arch,))),
            steps_before=[BuildStep("rustup target add " + triple)],
            env={"RUSTFLAGS": _MSVC_RUSTFLAGS},
            pdb="target/%s/release/orion_driver.pdb" % triple)
    return recipes


RECIPES = {}
for _v in _VERSIONS:
    RECIPES.update(_all(_v))


# The `debug = true` builds the tracker issue asks for beside the release
# ones: the same recipes with cargo's release profile switched to full debug
# info (CARGO_PROFILE_RELEASE_DEBUG=true overrides the driver's `debug =
# false`), filed as version <v>-debug so the two never share a provenance key.
# Every leg pins with rustup the rustc its release build used (1.99.1 for
# MSVC, the runner's; 1.97.0 for ELF and MinGW, the container's), so that
# debug info is the only difference wherever the leg is built.
_DEBUG_NOTE = ("debug = true build: identical to the %s recipe except that "
               "CARGO_PROFILE_RELEASE_DEBUG=true turns on full debug info in "
               "the release profile (opt-level, codegen units, LTO and panic "
               "strategy unchanged). ")

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
    compiler = recipe.notes[len(_COMMON_NOTES):].split(" Measured ")[0]
    compiler = compiler.replace(
        "the stable toolchain of the windows-2022 runner image" if msvc
        else "the stable toolchain of the build container",
        "pinned with rustup (RUSTUP_TOOLCHAIN=%s), the rustc of the "
        "release build" % rustc)
    return dataclasses.replace(
        recipe, version=recipe.version + "-debug", build=build,
        build_flags=recipe.build_flags.replace("debug info off",
                                               "debug = true (full debug info)"),
        notes=(_DEBUG_NOTE % name) + _COMMON_NOTES + compiler.rstrip(" ."))


for _name in list(RECIPES):
    _v, _, _rest = _name[len("orion_"):].partition("_")
    RECIPES["orion_%s-debug%s" % (_v, ("_" + _rest) if _rest else "")] = \
        _debug(_name, RECIPES[_name])


# The high-level API (the `safe_api` feature: orion::aead and its streaming
# API, orion::auth, orion::hash, orion::kdf, orion::pwhash, and orion::kex on
# 0.17 or orion::kem, orion::hpke and orion::signer on 0.18), which tracker
# issue #7 names (orion::aead) and the no_std driver cannot reach because
# safe_api turns on std and getrandom. A std cdylib driver
# (exercisers/orion_driver/src/safe_api17.rs, safe_api18.rs) calls every
# entry point, filed as version <v>-safe_api. std, core, alloc, getrandom and
# the other dependencies are linked statically and excluded by name with the
# same orion-only pattern as the no_std builds, so only orion's own code is
# kept. The driver lockfiles were resolved by cargo at the time of writing and
# are built --locked. Every leg pins its rustc with rustup like the debug
# variants: 1.97.0 for ELF and MinGW, 1.99.1 for MSVC.
_SAFE_NOTES = (
    "Built from a std cdylib driver crate (scripts/corpus/exercisers/"
    "orion_driver/%s-safe_api, src/%s) that calls orion's high-level API "
    "(safe_api, orion's default features): aead (with streaming), auth, "
    "hash, kdf, pwhash and %s. orion is compiled from the crates.io tarball "
    "pinned by sha256 through a cargo patch.crates-io path override; every "
    "other crate is pinned in the driver's Cargo.lock and built --locked. "
    "Only the orion:: namespace is kept; std, core, alloc, getrandom, "
    "subtle, zeroize, the other dependencies and the driver's orion_sx_* "
    "exports are excluded by name. Compiler: %s, pinned with rustup "
    "(RUSTUP_TOOLCHAIN).")


def _safe(version, target, toolchains, artifact, rustc, kind, steps_before=(),
          env=None, pdb=None):
    src = "safe_api18.rs" if version == "0.18.1" else "safe_api17.rs"
    extra = ("kem, hpke and signer" if version == "0.18.1" else "kex")
    env = dict(env or {}, RUSTUP_TOOLCHAIN=rustc)
    cargo = BuildStep(_CARGO % (version + "-safe_api", target), env=dict(env))
    build = [BuildStep("rustup toolchain install %s --profile minimal "
                       "--target %s" % (rustc, target))]
    build += [__import__("dataclasses").replace(s, env=dict(s.env, **env))
              for s in steps_before]
    build += [BuildStep("rustc -vV", env=dict(env)), cargo]
    return Recipe(
        family="orion",
        version=version + "-safe_api",
        upstream=_UPSTREAM,
        license=_LICENSE % ("2026" if version == "0.18.1" else "2025"),
        source=_crate(version),
        build=build,
        artifacts=[Artifact(path="target/%s/release/%s" % (target, artifact),
                            component=artifact.replace("lib", "", 1)
                            if artifact.startswith("lib") else artifact,
                            pdb=pdb)],
        toolchains=toolchains,
        requires=["cargo"],
        exclude_functions=list(_EXCLUDE),
        build_flags=("cargo --release (opt-level 3, LTO off, codegen-units "
                     "16, panic=abort, debug info off) --locked, std driver "
                     "crate, orion default features (safe_api); " + kind),
        notes=_SAFE_NOTES % (version, src, extra,
                             "rustc %s (%s)" % (rustc, kind)),
    )


for _v in _VERSIONS:
    _t = "orion_%s-safe_api" % _v
    RECIPES[_t + "_linux"] = _safe(
        _v, "{platform}-unknown-linux-gnu", ["linux_x86", "linux_x64"],
        "liborion_driver.so", "1.97.0",
        "i686-unknown-linux-gnu / x86_64-unknown-linux-gnu")
    RECIPES[_t] = _safe(
        _v, "{platform}-pc-windows-gnu", ["mingw_x86", "mingw_x64"],
        "orion_driver.dll", "1.97.0",
        "i686-pc-windows-gnu / x86_64-pc-windows-gnu")
    for _arch, _triple in (("x86", "i686-pc-windows-msvc"),
                           ("x64", "x86_64-pc-windows-msvc")):
        RECIPES["%s_msvc_%s" % (_t, _arch)] = _safe(
            _v, _triple, ["msvc_" + _arch], "orion_driver.dll", "1.99.1",
            _triple + ", dynamic CRT (/MD), link /OPT:NOREF /OPT:NOICF "
            "/Brepro /INCREMENTAL:NO",
            steps_before=[BuildStep("rustup target add " + _triple)],
            env={"RUSTFLAGS": "-C link-arg=/OPT:NOREF -C link-arg=/OPT:NOICF "
                              "-C link-arg=/Brepro -C link-arg=/INCREMENTAL:NO"},
            pdb="target/%s/release/orion_driver.pdb" % _triple)
