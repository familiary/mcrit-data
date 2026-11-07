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

Measured results are in the per-recipe `notes`.
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
    "The rustc used is the stable toolchain installed on the build machine: ")


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
                   "-C link-arg=ucrt.lib "
                   "-C symbol-mangling-version=legacy")


def _flags(extra):
    return ("cargo --release (opt-level 3, LTO off, codegen-units 16, "
            "panic=abort, debug info off) --locked, driver crate "
            "#![no_std]; " + extra)


# Keep only the orion crate's own code. SMDA demangles Rust names, so the
# usual form is `orion::hazardous::...` or `<orion::T as core::Trait>::m`;
# the legacy-mangled spellings (`_ZN5orion...`, with one more underscore on
# 32-bit PE) are listed too for a build whose symbols arrive undemangled
# (MSVC builds use legacy mangling, see _MSVC_RUSTFLAGS). Everything else is
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


def _all(version):
    tag = "orion_" + version
    recipes = {
        tag + "_linux": _make(
            version, "{platform}-unknown-linux-gnu", ["linux_x86", "linux_x64"],
            "liborion_driver.so", "orion_driver.so",
            _flags("i686-unknown-linux-gnu / x86_64-unknown-linux-gnu"),
            "ELF build; see the README for the measured counts."),
        tag: _make(
            version, "{platform}-pc-windows-gnu", ["mingw_x86", "mingw_x64"],
            "orion_driver.dll", "orion_driver.dll",
            _flags("i686-pc-windows-gnu / x86_64-pc-windows-gnu"),
            "MinGW (windows-gnu) build; see the README for the measured counts."),
    }
    for arch, triple in (("x86", "i686-pc-windows-msvc"),
                         ("x64", "x86_64-pc-windows-msvc")):
        recipes["%s_msvc_%s" % (tag, arch)] = _make(
            version, triple, ["msvc_" + arch], "orion_driver.dll",
            "orion_driver.dll",
            _flags(triple + ", dynamic CRT (/MD), link /OPT:NOREF "
                   "/OPT:NOICF /Brepro /INCREMENTAL:NO, legacy symbol mangling"),
            "MSVC build (%s); see the README for the measured counts." % triple,
            steps_before=[BuildStep("rustup target add " + triple)],
            env={"RUSTFLAGS": _MSVC_RUSTFLAGS},
            pdb="target/%s/release/orion_driver.pdb" % triple)
    return recipes


RECIPES = {}
for _v in _VERSIONS:
    RECIPES.update(_all(_v))
