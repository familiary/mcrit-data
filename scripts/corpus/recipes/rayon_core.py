"""rayon-core 1.12.1 and the crossbeam crates it links, from a driver crate.

TODO docstring
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
        notes="TODO " + notes,
    )


RECIPES = {
    "rayon-core_1.12.1_linux": _make(
        "{platform}-unknown-linux-gnu", ["linux_x86", "linux_x64"],
        "librayon_core_driver.so",
        _flags("i686-unknown-linux-gnu / x86_64-unknown-linux-gnu"), "ELF"),
    "rayon-core_1.12.1": _make(
        "{platform}-pc-windows-gnu", ["mingw_x86", "mingw_x64"],
        "rayon_core_driver.dll",
        _flags("i686-pc-windows-gnu / x86_64-pc-windows-gnu"), "MinGW"),
}
for _arch, _triple in (("x86", "i686-pc-windows-msvc"),
                       ("x64", "x86_64-pc-windows-msvc")):
    RECIPES["rayon-core_1.12.1_msvc_" + _arch] = _make(
        _triple, ["msvc_" + _arch], "rayon_core_driver.dll",
        _flags(_triple + ", dynamic CRT (/MD), link /OPT:NOREF /OPT:NOICF "
               "/Brepro /INCREMENTAL:NO"), "MSVC",
        steps_before=[BuildStep("rustup target add " + _triple)],
        env={"RUSTFLAGS": _MSVC_RUSTFLAGS},
        pdb="target/%s/release/rayon_core_driver.pdb" % _triple)
