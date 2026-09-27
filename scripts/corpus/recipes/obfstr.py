"""CasualX/obfstr - compiletime string constant obfuscation for Rust.

The first Rust family this tooling generates. data/Rust exists already, but
it is legacy IDA-derived data with no provenance.json behind it; this one is
built from pinned source like every other recipe here.

obfstr is a compiletime obfuscator, so the encoding runs in `const` context
and nothing of the crate exists in a binary until something uses the macros.
The reference data therefore comes from a driver crate,
scripts/corpus/exercisers/obfstr_driver, which is a consumer of the library
rather than a modification of it - the same arrangement as the C++ exercisers
here, in the shape cargo needs. The recipe copies it into the fetched
checkout so its `obfstr = { path = ".." }` dependency resolves to the pinned
source; upstream's own files are untouched.

What lands in the image is obfstr::xref::inner, which upstream marks
`#[inline(never)]` and which is generic over `const SEED: u64`. That gives
exactly one monomorphisation per obfuscated item, and each is a different
shape, because the seed picks the obfchoice arms and drives the obfstmt!
control-flow flattening wrapped around them. Measured on this driver at
release: 46 distinct obfstr functions on both x86 and x64, one for each of
the 46 obfuscated strings, byte strings, C strings, wide strings and xrefs.

Two things this recipe is careful about.

The driver is #![no_std] with panic = "abort" and crate-type = ["cdylib"].
A stock Rust cdylib drags thousands of std and core functions into the image
and every one of them would be filed under obfstr's family name - the trap
the nlohmann recipe records for -static-libstdc++. obfstr is itself
`#![cfg_attr(not(test), no_std)]` with no dependencies, so nothing is given
up. Measured on the built DLLs: zero symbols matching _ZN4core, _ZN3std or
_ZN5alloc on either architecture. What is in the image besides obfstr is the
driver's three functions and the mingw-w64 C runtime, which drop_crt_glue
removes.

OBFSTR_SEED is deliberately left unset. obfstr reads it through option_env!
and falls back to the literal "FIXED", so an unset variable is the
reproducible case; setting it would make every seed, and therefore every
function body, depend on an environment variable nothing records. Verified:
two release builds of the x64 DLL three seconds apart differ in exactly
three bytes - the COFF timestamp at offset 136, the checksum, and the export
directory's timestamp - and are otherwise byte-identical, code included.

Targets are x86_64-pc-windows-gnu and i686-pc-windows-gnu, which link
through the mingw-w64 toolchain this corpus already uses, so the artefacts
sit alongside the GCC-built ones rather than in a toolchain of their own.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# {platform} is the CPU half of the mingw triple, "i686" or "x86_64", which
# is also the CPU half of the Rust target triple.
_TARGET = "{platform}-pc-windows-gnu"

# rm -rf first so a re-run against a cached checkout copies the driver rather
# than nesting a second copy inside the first.
_COPY = ("rm -rf obfstr_driver && "
         "cp -r {repo}/scripts/corpus/exercisers/obfstr_driver obfstr_driver")

# --offline because the driver's only dependency is the path dependency on
# the pinned checkout: nothing should be resolved from crates.io, and this
# makes that a build failure rather than a silent download.
_BUILD = "cargo build --release --offline --target " + _TARGET


RECIPES = {
    # v0.4.6 is both the newest crates.io release and HEAD of the repository,
    # so the tag is the right pin - 9e56c1938dfd3bd65fe305fbafcb57394c701356.
    "obfstr_0.4.6": Recipe(
        family="obfstr",
        version="0.4.6",
        upstream="https://github.com/CasualX/obfstr",
        license="MIT, Copyright (c) 2019-2020 Casper "
                "<CasualX@users.noreply.github.com>",
        source=Source(git_url="https://github.com/CasualX/obfstr.git",
                      git_ref="v0.4.6"),
        build=[BuildStep(_COPY),
               BuildStep(_BUILD, cwd="obfstr_driver")],
        artifacts=[Artifact(
            path="obfstr_driver/target/" + _TARGET + "/release/obfstr_driver.dll",
            component="obfstr_driver.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        requires=["cargo"],
        # Spelled out rather than written with {platform}: provenance strings
        # are copied into the record verbatim and are deliberately not
        # placeholder-expanded (pipeline.py takes build_flags straight off the
        # recipe), so a placeholder here would ship as literal text.
        build_flags="cargo --release (opt-level 3, LTO off) for "
                    "i686-pc-windows-gnu / x86_64-pc-windows-gnu, driver "
                    "crate #![no_std] with panic=abort, OBFSTR_SEED unset",
        notes="Built from a driver crate, since the library is a compiletime "
              "obfuscator and emits nothing until a consumer uses its "
              "macros; the emitted functions are the library's own. Rust "
              "edition 2024, so rustc 1.85 or newer is required. The "
              "artefact is dominated by obfstr::xref::inner, which upstream "
              "marks #[inline(never)] and which is generic over "
              "`const SEED: u64`: one monomorphisation per obfuscated item, "
              "measured at 46 on both architectures for the 46 strings, byte "
              "strings, C strings, wide strings and xrefs the driver "
              "obfuscates. Unlike the C++ string obfuscators in this corpus, "
              "this one emits the same one-per-string shape in debug and in "
              "release, so the optimisation level is not the provenance "
              "hazard it is for those; release is recorded here. The driver "
              "is #![no_std] with panic=abort so the image contains no Rust "
              "std or core code to be misfiled under this family - measured: "
              "zero _ZN4core, _ZN3std or _ZN5alloc symbols in either "
              "artefact. OBFSTR_SEED is left unset, which is obfstr's own "
              "reproducible default (option_env! falls back to \"FIXED\"); "
              "two rebuilds differ only in the PE timestamps and checksum, "
              "three bytes, with identical code. Targeted at "
              "*-pc-windows-gnu, which links through the same mingw-w64 "
              "toolchain as the rest of the corpus. The x86 report carries 68 "
              "functions against x64's 49 for the same 46 obfstr "
              "monomorphisations: the extra 19 are i686's DWARF exception "
              "machinery, which x86_64 does not use - libgcc's "
              "unwind-dw2-fde.o, whose fifteen file-static helpers carry no "
              "symbol in the shipped libgcc_eh.a and so come back unnamed "
              "(they sit exactly 0x1b60 below __Unwind_Find_FDE in the "
              "image, which is that member's own .text layout), plus Rust's "
              "rsbegin::eh_frames::init/uninit and one further mingw CRT "
              "body. None of it is Rust std or compiler_builtins: measured "
              "zero _ZN4core, _ZN3std, _ZN5alloc and compiler_builtins "
              "symbols, and zero 64-bit integer helpers (__udivdi3 and "
              "friends), in either artefact.",
    ),
}
