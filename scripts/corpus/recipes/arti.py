"""Arti - the Tor project's Rust Tor client (placeholder docstring, see end of work)."""

from ..recipe import Artifact, BuildStep, Recipe, Source


# arti 2.3.0 (crates.io sha256 937670cbf2189f02070a50275609a6d4057865bb6124b678e3aa2d5c3adcd714)
# ships Cargo.lock naming arti-client 0.42.0, whose crates.io checksum is the
# pin below.
_VERSIONS = {
    "2.3.0": ("arti-client", "0.42.0",
              "16739ee6ad4ee11073a8d12c34a911ea72977c5ce4abbb21a1f7cf5955f22a01"),
}

_UPSTREAM = "https://gitlab.torproject.org/tpo/core/arti"
_LICENSE = "MIT OR Apache-2.0, Copyright The Tor Project, Inc."

# The crates of the Arti workspace (plus the small crates it publishes for
# itself). Everything else - std/core/alloc, tokio, the RustCrypto and dalek
# crates, native-tls, zstd, sqlite, the driver - is excluded by name.
_OWN = (r"arti_client|tor_[a-z0-9_]+|safelog|fs_mistrust|caret|retry_error|"
        r"slotmap_careful|oneshot_fused_workaround|web_time_compat|pwd_grp")
_EXCLUDE = [r"^(?!<?(?:%s)::|_{1,2}ZN\d+(?:%s)|_{1,2}ZN\d+_\$LT\$(?:%s))"
            % (_OWN, _OWN, _OWN)]

_RUSTC = BuildStep("rustc -vV")

_MSVC_RUSTFLAGS = ("-C link-arg=/OPT:NOREF -C link-arg=/OPT:NOICF "
                   "-C link-arg=/Brepro -C link-arg=/INCREMENTAL:NO")

_CARGO = ("cargo build --release --locked --target-dir target "
          "--manifest-path {repo}/scripts/corpus/exercisers/arti_driver/%s/Cargo.toml "
          "--config \"patch.crates-io.arti-client.path='.'\" --target %s")

# 32-bit ELF: native-tls links the system OpenSSL, so point pkg-config at the
# i386 multiarch copy.
_ELF32 = ("if [ {bitness} = 32 ]; then export PKG_CONFIG_ALLOW_CROSS=1 "
          "PKG_CONFIG_PATH=/usr/lib/i386-linux-gnu/pkgconfig; fi; ")

_NOTES = ("Built from a std cdylib driver crate "
          "(scripts/corpus/exercisers/arti_driver) calling arti-client's "
          "public API (TorClient::create_bootstrapped, connect, resolve), "
          "default features (tokio, native-tls, compression). Only the Arti "
          "workspace's own code is kept; see the recipe module docstring. "
          "Compiler: ")


def _make(version, target, toolchains, artifact, component, build_flags,
          notes, steps_before=(), env=None, pdb=None, prefix=""):
    crate, crate_ver, sha = _VERSIONS[version]
    cargo = BuildStep(prefix + _CARGO % (version, target), env=dict(env or {}))
    return Recipe(
        family="arti",
        version=version,
        upstream=_UPSTREAM,
        license=_LICENSE,
        source=Source(url="https://static.crates.io/crates/%s/%s-%s.crate"
                      % (crate, crate, crate_ver), sha256=sha),
        build=list(steps_before) + [_RUSTC, cargo],
        artifacts=[Artifact(path="target/%s/release/%s" % (target, artifact),
                            component=component, pdb=pdb)],
        toolchains=toolchains,
        requires=["cargo"],
        exclude_functions=list(_EXCLUDE),
        build_flags=build_flags,
        notes=_NOTES + notes,
    )


def _flags(extra):
    return ("cargo --release (opt-level 3, LTO off, codegen-units 16, "
            "panic=abort, debug info off) --locked; " + extra)


_RUSTC_LOCAL = ("rustc 1.97.0 (2d8144b78 2026-07-07), LLVM 22.1.6, the stable "
                "toolchain of the build container")


_RUSTC_RUNNER = ("rustc of the windows-2022 runner image's stable toolchain "
                 "(recorded in the build log by `rustc -vV`)")


def _all(version):
    tag = "arti_" + version
    recipes = {
        tag + "_linux": _make(
            version, "{platform}-unknown-linux-gnu", ["linux_x86", "linux_x64"],
            "libarti_driver.so", "arti_driver.so",
            _flags("i686-unknown-linux-gnu / x86_64-unknown-linux-gnu, "
                   "system OpenSSL for native-tls"),
            "ELF build with " + _RUSTC_LOCAL + ". ", prefix=_ELF32),
        tag: _make(
            version, "{platform}-pc-windows-gnu", ["mingw_x86", "mingw_x64"],
            "arti_driver.dll", "arti_driver.dll",
            _flags("i686-pc-windows-gnu / x86_64-pc-windows-gnu, "
                   "native-tls through Schannel"),
            "MinGW (windows-gnu) build with " + _RUSTC_LOCAL + ". "),
    }
    for arch, triple in (("x86", "i686-pc-windows-msvc"),
                         ("x64", "x86_64-pc-windows-msvc")):
        recipes["%s_msvc_%s" % (tag, arch)] = _make(
            version, triple, ["msvc_" + arch], "arti_driver.dll",
            "arti_driver.dll",
            _flags(triple + ", dynamic CRT (/MD), native-tls through "
                   "Schannel, link /OPT:NOREF /OPT:NOICF /Brepro "
                   "/INCREMENTAL:NO"),
            "MSVC build (%s) with %s. " % (triple, _RUSTC_RUNNER),
            steps_before=[BuildStep("rustup target add " + triple)],
            env={"RUSTFLAGS": _MSVC_RUSTFLAGS},
            pdb="target/%s/release/arti_driver.pdb" % triple)
    return recipes


RECIPES = {}
for _v in _VERSIONS:
    RECIPES.update(_all(_v))
