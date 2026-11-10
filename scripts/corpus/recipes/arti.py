"""Arti - the Tor project's Rust Tor client, two releases, six axes each.

**Why this family exists.** Tracker issue #36 records a Tor-backed npm
supply-chain worm published 2026-05-11 (CloudSEK, 2026-05-14), described by
the vendor as using a "modified Arti 1.1.x". That is a vendor assessment,
not a build string. The issue asked for `cargo build --release -p
arti-client` on x86_64-pc-windows-msvc, i686-pc-windows-msvc and
x86_64-unknown-linux-gnu (the sample was a Linux ELF).

**Which releases.** Arti is released as the `arti` crate; its library half
is `arti-client` and the `tor-*` crates, versioned together (arti 2.3.0 is
arti-client 0.42.0, arti 1.1.13 is arti-client 0.14.0). Checked against
crates.io (non-yanked):

  * **2.3.0** (2026-05-07) - the newest release before the worm.
    arti-client 0.42.0, crates.io sha256
    16739ee6ad4ee11073a8d12c34a911ea72977c5ce4abbb21a1f7cf5955f22a01
    (the arti 2.3.0 crate itself: 937670cb...cd714).
  * **1.1.13** (2024-02-05) - the newest 1.1.x patch release, the series
    the vendor names. arti-client 0.14.0, crates.io sha256
    7ffd8cfa3b2bdbeefd4a8d8656a3763b53275fdd61e5aaf77821e3fec05f11b4
    (the arti 1.1.13 crate: 614ac83e...a0971).

The newest overall release (2.8.0 at the time of writing) is deliberately
not built. Each arti-client tarball is fetched and checksummed by the
pipeline (Source.sha256 is crates.io's own checksum) and compiled through a
`--config patch.crates-io.arti-client.path='.'` override, so the compiled
arti-client is exactly the pinned source. Every other crate is pinned by
crates.io checksum in the driver's Cargo.lock and built `--locked`. Each
Cargo.lock started as the Cargo.lock that crates.io ships inside the
matching `arti` release crate, so versions and checksums are the release's
own; cargo pruned it to the 495 (2.3.0) and 388 (1.1.13) packages the
driver reaches (checked: every one is in the release lock with the same
checksum). One deliberate deviation: on 1.1.13 `time` is raised from 0.3.31
to 0.3.36 (and time-macros 0.2.16 to 0.2.18, plus num-conv 0.1.0 which they
need), a lockfile edit only, because time 0.3.31 does not compile on
rustc 1.97 (`error[E0282]: type annotations needed for Box<_>` in
time-0.3.31/src/format_description/parse/mod.rs:83, the well-known
break fixed in 0.3.35). No upstream source is touched.

**Scope decision.** The driver is a std cdylib, because arti-client needs
std, tokio and a TLS stack and has no no_std mode. A Rust cdylib links all
of std statically, and with the corpus linker policy (no section folding, no
unreferenced-code elimination on PE) it also keeps every third-party
dependency body: tokio, the RustCrypto and dalek crates, native-tls,
SQLite, zstd, flate2, serde, std/core/alloc. Filing 10,000 to 40,000 such
functions under "arti" would misattribute them, and much of it is shared
with other families (data/Rust holds lib.rust.* families for several of the
same crates). So the family keeps **only the Arti workspace's own code** and
counts the rest as excluded, using `Recipe.exclude_functions`, with a
negative lookahead on the project's own namespaces, the way orion does:

    ^(?!<?(?:arti_client|tor_[a-z0-9_]+|safelog|fs_mistrust|caret|
              retry_error|slotmap_careful|oneshot_fused_workaround|
              web_time_compat|pwd_grp)::  | _{1,2}ZN\\d+(?:...) | _{1,2}ZN\\d+_\\$LT\\$(?:...))

(the full pattern, with the legacy-mangled spellings, is `_EXCLUDE` below
and is recorded in every provenance entry.) The kept crates are the ones
cargo resolves from the Arti repository (gitlab.torproject.org/tpo/core/arti):
arti-client, the tor-* crates the default features reach (tor-proto,
tor-netdoc, tor-netdir, tor-circmgr, tor-guardmgr, tor-dirmgr,
tor-cell, tor-llcrypto, ...), safelog, fs-mistrust, caret, retry-error,
slotmap-careful, oneshot-fused-workaround, web-time-compat and pwd-grp.
Excluded and counted: std, core, alloc, compiler_builtins, the C runtime,
the driver's own `arti_x_*` exports, and every third-party crate. Trait
impls of Arti types for core traits (`<tor_proto::T as core::fmt::Debug>`)
stay; blanket impls of core/tokio types over Arti types
(`core::ptr::drop_in_place<tor_proto::T>`, `<&tor_proto::T as ...>`) do not.
Measured on all twelve artefacts: every kept function sits in one of the
own namespaces (39 crates in 2.3.0, 29-30 in 1.1.13), and no function with
a foreign namespace survives.

**Driver and features.** scripts/corpus/exercisers/arti_driver exports two
`#[no_mangle] extern "C"` functions, `arti_x_fetch` (bootstrap a client,
open a stream to host:port, write a request, read the reply) and
`arti_x_resolve`, which call arti-client's public API
(`TorClient::create_bootstrapped`, `connect`, `resolve`) on a current-thread
tokio runtime so the linker keeps the client, circuit, directory, channel
and protocol code behind them. Features are arti-client's defaults (tokio,
native-tls, compression) plus `static-sqlite`, arti-client's own feature that
bundles SQLite (there is no system SQLite on the Windows targets and no
32-bit one on the Linux host). Not covered: onion-service client and
service, bridges and pluggable transports, the RPC server, the `arti` CLI
and SOCKS/DNS proxy crate; those are non-default features of arti-client or
the separate `arti` binary crate. The ELF builds link the system OpenSSL for
native-tls (libssl-dev, with the i386 multiarch copy for x86); the PE
builds use Schannel through the OS and need nothing.

**Measured** (kept + removed-as-glue + excluded-by-name = image total; ELF
and MinGW built in the container with rustc 1.97.0 (2d8144b78 2026-07-07),
LLVM 22.1.6; MSVC on the windows-2022 runner, runs 42407223773 (2.3.0) and
42409508551 (1.1.13), rustc as shipped on the runner image, version not
captured in the log):

    artefact                  x86 kept/glue/excl = total     x64 kept/glue/excl = total
    2.3.0  ELF (gcc13)        4179 /   5 / 12702 = 16886     4190 /   6 / 12410 = 16606
    2.3.0  MinGW (mingw13)    7141 /  93 / 34486 = 41720     6392 /  85 / 27080 = 33557
    2.3.0  MSVC (msvc143)     4169 / 225 / 39782 = 44176     4146 / 207 / 35468 = 39821
    1.1.13 ELF (gcc13)        3027 /   5 / 10054 = 13086     3054 /   6 /  9758 = 12818
    1.1.13 MinGW (mingw13)    4688 /  91 / 28294 = 33073     4237 /  82 / 21416 = 25735
    1.1.13 MSVC (msvc143)     2280 / 221 / 31987 = 34488     2346 / 202 / 28329 = 30877

No unnamed function is kept, and none of the kept functions is C runtime
glue: the glue column is the measured C-runtime baseline, the excluded
column everything outside the Arti namespaces.

**PicHash overlap** (distinct PicHashes of functions with 10 or more
instructions; kept functions only):

  * ELF against MinGW or MSVC on one architecture: 0 on x64 in both
    versions, 0 against MinGW and 5 (1.1.13) / 9 (2.3.0) against MSVC on x86.
    MinGW against MSVC: x64 625 of 1577/1566 (1.1.13) and 1113 of 2682/2699
    (2.3.0); x86 99 of 1823/1559 and 219 of 3136/2705. Both are LLVM-built
    PE images from the same code generator.
  * x64 against x86: 0 for every pair.
  * 1.1.13 against 2.3.0 on the same axis: ELF x64 362 of 1093/1710, x86 17
    of 2210/3160; MinGW x64 539 of 1577/2682, x86 787 of 1823/3136; MSVC x64
    640 of 1566/2699, x86 665 of 1559/2705.
  * against the existing Rust data (all eight files of data/Rust, 106,219
    distinct PicHashes of 10-or-more-instruction functions): 0 for every ELF
    artefact; 2.3.0 MinGW x64 16 (lib.rust.http 10, textwrap 7, aho-corasick
    3, mio 3), MSVC x64 6; 1.1.13 MinGW x64 11, MSVC x64 4, MSVC x86 1 and
    2.3.0 MSVC x86 1 (lib.rust.url); the rest 0. The origin of these
    hashes was not examined further.
  * against data/orion (the twelve orion artefacts of PR #95, 2,701 distinct
    PicHashes): 0 for every ELF artefact; 2 to 4 for each PE artefact.

The same counts are in each recipe's notes.
"""
from ..recipe import Artifact, BuildStep, Recipe, Source


# arti 2.3.0 (crates.io sha256 937670cbf2189f02070a50275609a6d4057865bb6124b678e3aa2d5c3adcd714)
# ships Cargo.lock naming arti-client 0.42.0, whose crates.io checksum is the
# pin below.
_VERSIONS = {
    "2.3.0": ("arti-client", "0.42.0",
              "16739ee6ad4ee11073a8d12c34a911ea72977c5ce4abbb21a1f7cf5955f22a01"),
    "1.1.13": ("arti-client", "0.14.0",
               "7ffd8cfa3b2bdbeefd4a8d8656a3763b53275fdd61e5aaf77821e3fec05f11b4"),
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

_LOCK_NOTE = ("The 1.1.13 driver lockfile is the release's own Cargo.lock "
              "pruned to the driver, except that time is raised 0.3.31 -> "
              "0.3.36 (with time-macros 0.2.18 and num-conv 0.1.0) because "
              "0.3.31 does not compile on current rustc (E0282); no source is "
              "patched. ")

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
          "workspace's own code is kept; see the recipe module docstring. ")


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
        notes=_NOTES + (_LOCK_NOTE if version == "1.1.13" else "") + notes,
    )


def _flags(extra):
    return ("cargo --release (opt-level 3, LTO off, codegen-units 16, "
            "panic=abort, debug info off) --locked; " + extra)


# (kept, glue removed, excluded by name) per version, kind and architecture;
# kept + glue + excluded is the image total.
_COUNTS = {
    ("2.3.0", "elf"): {"x86": (4179, 5, 12702), "x64": (4190, 6, 12410)},
    ("2.3.0", "mingw"): {"x86": (7141, 93, 34486), "x64": (6392, 85, 27080)},
    ("2.3.0", "msvc"): {"x86": (4169, 225, 39782), "x64": (4146, 207, 35468)},
    ("1.1.13", "elf"): {"x86": (3027, 5, 10054), "x64": (3054, 6, 9758)},
    ("1.1.13", "mingw"): {"x86": (4688, 91, 28294), "x64": (4237, 82, 21416)},
    ("1.1.13", "msvc"): {"x86": (2280, 221, 31987), "x64": (2346, 202, 28329)},
}


def _measured(version, kind, arches=("x86", "x64")):
    parts = []
    for arch in arches:
        kept, glue, excluded = _COUNTS[(version, kind)][arch]
        parts.append("%s: %d kept + %d glue + %d excluded = %d" %
                     (arch, kept, glue, excluded, kept + glue + excluded))
    return "Measured " + "; ".join(parts) + ". "


_RUSTC_LOCAL = ("rustc 1.97.0 (2d8144b78 2026-07-07), LLVM 22.1.6, the stable "
                "toolchain of the build container")


_RUSTC_RUNNER = ("rustc of the windows-2022 runner image's stable toolchain "
                 "(its version was not captured in the retained job log)")


def _all(version):
    tag = "arti_" + version
    recipes = {
        tag + "_linux": _make(
            version, "{platform}-unknown-linux-gnu", ["linux_x86", "linux_x64"],
            "libarti_driver.so", "arti_driver.so",
            _flags("i686-unknown-linux-gnu / x86_64-unknown-linux-gnu, "
                   "system OpenSSL for native-tls"),
            "ELF build with " + _RUSTC_LOCAL + ". " + _measured(version, "elf"),
            prefix=_ELF32),
        tag: _make(
            version, "{platform}-pc-windows-gnu", ["mingw_x86", "mingw_x64"],
            "arti_driver.dll", "arti_driver.dll",
            _flags("i686-pc-windows-gnu / x86_64-pc-windows-gnu, "
                   "native-tls through Schannel"),
            "MinGW (windows-gnu) build with " + _RUSTC_LOCAL + ". "
            + _measured(version, "mingw")),
    }
    for arch, triple in (("x86", "i686-pc-windows-msvc"),
                         ("x64", "x86_64-pc-windows-msvc")):
        recipes["%s_msvc_%s" % (tag, arch)] = _make(
            version, triple, ["msvc_" + arch], "arti_driver.dll",
            "arti_driver.dll",
            _flags(triple + ", dynamic CRT (/MD), native-tls through "
                   "Schannel, link /OPT:NOREF /OPT:NOICF /Brepro "
                   "/INCREMENTAL:NO"),
            "MSVC build (%s) with %s. %s" % (triple, _RUSTC_RUNNER,
                                              _measured(version, "msvc", (arch,))),
            steps_before=[BuildStep("rustup target add " + triple)],
            env={"RUSTFLAGS": _MSVC_RUSTFLAGS},
            pdb="target/%s/release/arti_driver.pdb" % triple)
    return recipes


RECIPES = {}
for _v in _VERSIONS:
    RECIPES.update(_all(_v))


# ---------------------------------------------------------------------------
# The variants added after the first two releases (see "Further variants" in
# the module docstring). Each pins its rustc with rustup instead of taking the
# host's or the runner's stable, so the same toolchain builds every axis.

_SRC = "https://static.crates.io/crates/%s/%s-%s.crate"

# version slug -> (crate fetched, its version, crates.io sha256, driver
# directory or None for the arti binary crate itself, rustc, features)
_VARIANTS = {
    "2.8.0": ("arti-client", "0.48.0",
              "5bb17a5096e30f2b2bf9f7493ff7577ac66ed7059b8e435658a2884546afe70c",
              "2.8.0", "1.97.0", "default + static-sqlite"),
    "2.3.0-full": ("arti-client", "0.42.0",
                   "16739ee6ad4ee11073a8d12c34a911ea72977c5ce4abbb21a1f7cf5955f22a01",
                   "2.3.0-full", "1.97.0", "full + static-sqlite"),
    "1.1.13-rust1.75": ("arti-client", "0.14.0",
                        "7ffd8cfa3b2bdbeefd4a8d8656a3763b53275fdd61e5aaf77821e3fec05f11b4",
                        "1.1.13-rust1.75", "1.75.0", "default + static-sqlite"),
    "2.3.0-cli": ("arti", "2.3.0",
                  "937670cbf2189f02070a50275609a6d4057865bb6124b678e3aa2d5c3adcd714",
                  None, "1.97.0", "default + static-sqlite"),
    "1.1.13-cli": ("arti", "1.1.13",
                   "614ac83e08192637fd9e1a1a1ba9261c06b958c1a124461dd85a74e973ca0971",
                   None, "1.75.0", "default + static-sqlite"),
}

# The arti binary crate adds its own namespace (arti::) and, with its default
# features, the arti-* workspace crates it links; everything else is excluded
# exactly as for the driver.
_OWN_CLI = _OWN + r"|arti|arti_[a-z0-9_]+"
_EXCLUDE_CLI = [r"^(?!<?(?:%s)::|_{1,2}ZN\d+(?:%s)|_{1,2}ZN\d+_\$LT\$(?:%s))"
                % (_OWN_CLI, _OWN_CLI, _OWN_CLI)]

_VARIANT_NOTES = {
    "2.8.0": ("Arti 2.8.0 (2026-11-04, the newest release; arti-client "
              "0.48.0), built from the std cdylib driver crate "
              "(scripts/corpus/exercisers/arti_driver/2.8.0) with "
              "arti-client's default features plus static-sqlite. The "
              "driver's Cargo.lock is the arti 2.8.0 release crate's own "
              "(sha256 34f021b3ac0b757e0c60710fd15df3b5157d41327289ebb0ab493bce1050b0d4) "
              "pruned by cargo to 508 packages, every one at the release's "
              "version and checksum. "),
    "2.3.0-full": ("Arti 2.3.0 (arti-client 0.42.0) with arti-client's "
                   "\"full\" feature: every non-experimental feature "
                   "(onion-service client and service, bridge-client, "
                   "pt-client, vanguards, async-std, memquota, rpc, keymgr) "
                   "on top of the defaults, plus static-sqlite; driver "
                   "scripts/corpus/exercisers/arti_driver/2.3.0-full, whose "
                   "Cargo.lock is the arti 2.3.0 release crate's pruned by "
                   "cargo to 553 packages, every one at the release's "
                   "version and checksum. "),
    "1.1.13-rust1.75": ("Arti 1.1.13 (arti-client 0.14.0) with the release "
                        "Cargo.lock unchanged (time 0.3.31, which does not "
                        "compile on rustc 1.80 or later), built with rustc "
                        "1.75.0, the stable release current when 1.1.13 "
                        "shipped (2024-02-05). Driver "
                        "scripts/corpus/exercisers/arti_driver/1.1.13-rust1.75: "
                        "the arti 1.1.13 release crate's Cargo.lock pruned by "
                        "cargo to 388 packages with no version changed, and "
                        "src_legacy/lib.rs, the same driver source with "
                        "#[no_mangle] for rustc 1.75. "),
    "2.3.0-cli": ("The arti binary crate itself (the arti 2.3.0 release crate "
                  "from crates.io), the Tor client and SOCKS/DNS proxy, built "
                  "with its own shipped Cargo.lock --locked, its default "
                  "features (tokio, native-tls, dns-proxy, harden, "
                  "compression, bridge-client, pt-client, "
                  "onion-service-client, vanguards) plus static-sqlite, "
                  "cargo's default release profile (the crate publishes "
                  "none), i.e. what `cargo install arti --locked --features "
                  "static-sqlite` builds. Kept: the Arti namespaces of the "
                  "driver plus arti:: and arti_*::. "),
    "1.1.13-cli": ("The arti binary crate itself (the arti 1.1.13 release "
                   "crate from crates.io) built with its own shipped "
                   "Cargo.lock --locked and rustc 1.75.0 (time 0.3.31 needs "
                   "a rustc older than 1.80), its default features plus "
                   "static-sqlite, cargo's default release profile; what "
                   "`cargo install arti@1.1.13 --locked --features "
                   "static-sqlite` builds with that rustc. Kept: the Arti "
                   "namespaces of the driver plus arti:: and arti_*::. "),
}


def _variant(slug, target, toolchains, kind, triple_note, steps_before=(),
             env=None, msvc=False, prefix=""):
    crate, crate_ver, sha, driver, rustc, features = _VARIANTS[slug]
    env = dict(env or {}, RUSTUP_TOOLCHAIN=rustc)
    install = BuildStep("rustup toolchain install %s --profile minimal "
                        "--target %s" % (rustc, target), env=dict(env))
    if driver is None:
        cargo = ("cargo build --release --locked --target-dir target "
                 "--features static-sqlite --target %s" % target)
        binary = "arti.exe" if kind != "elf" else "arti"
        pdb = "target/%s/release/arti.pdb" % target if msvc else None
        exclude = list(_EXCLUDE_CLI)
        profile = ("cargo default release profile (opt-level 3, LTO off, "
                   "codegen-units 16, panic=unwind, debug info off)")
    else:
        cargo = _CARGO % (driver, target)
        binary = ("libarti_driver.so" if kind == "elf"
                  else "arti_driver.dll")
        pdb = "target/%s/release/arti_driver.pdb" % target if msvc else None
        exclude = list(_EXCLUDE)
        profile = ("cargo --release (opt-level 3, LTO off, codegen-units 16, "
                   "panic=abort, debug info off)")
    return Recipe(
        family="arti",
        version=slug,
        upstream=_UPSTREAM,
        license=_LICENSE,
        source=Source(url=_SRC % (crate, crate, crate_ver), sha256=sha),
        build=list(steps_before) + [
            install,
            BuildStep("rustc -vV", env=dict(env)),
            BuildStep(prefix + cargo, env=dict(env)),
        ],
        artifacts=[Artifact(path="target/%s/release/%s" % (target, binary),
                            component=binary, pdb=pdb)],
        toolchains=toolchains,
        requires=["cargo"],
        exclude_functions=exclude,
        # The arti binary on MSVC, built with cargo's default profile (no
        # debug info), names only its public symbols in the PDB: measured
        # 38% (2.3.0 x64), 36% (2.3.0 x86), 44% (1.1.13 x64) and 40% (1.1.13
        # x86) of functions of 3+ instructions in run 42776062997, against
        # the 0.5 default. Not a stripped build; turning on debug info would
        # change the code (orion's debug = true MSVC images differ from the
        # release ones), so the floor is lowered for these four only.
        min_named_ratio=0.3 if (driver is None and msvc) else 0.5,
        build_flags="%s --locked, rustc %s (rustup), features %s; %s"
                    % (profile, rustc, features, triple_note),
        notes=_VARIANT_NOTES[slug] + "Only the Arti workspace's own code is "
              "kept; see the recipe module docstring.",
    )


for _slug in _VARIANTS:
    _tag = "arti_" + _slug
    RECIPES[_tag + "_linux"] = _variant(
        _slug, "{platform}-unknown-linux-gnu", ["linux_x86", "linux_x64"],
        "elf", "i686-unknown-linux-gnu / x86_64-unknown-linux-gnu, system "
        "OpenSSL for native-tls", prefix=_ELF32)
    RECIPES[_tag] = _variant(
        _slug, "{platform}-pc-windows-gnu", ["mingw_x86", "mingw_x64"],
        "mingw", "i686-pc-windows-gnu / x86_64-pc-windows-gnu, native-tls "
        "through Schannel")
    for _arch, _triple in (("x86", "i686-pc-windows-msvc"),
                           ("x64", "x86_64-pc-windows-msvc")):
        RECIPES["%s_msvc_%s" % (_tag, _arch)] = _variant(
            _slug, _triple, ["msvc_" + _arch], "msvc",
            _triple + ", dynamic CRT (/MD), native-tls through Schannel, "
            "link /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO",
            env={"RUSTFLAGS": _MSVC_RUSTFLAGS}, msvc=True)
