"""CasualX/obfstr, built for Linux and ELF.

The ELF counterpart of obfstr.py: same pinned tag, same driver crate, same
release profile, targeting x86_64-unknown-linux-gnu and
i686-unknown-linux-gnu instead of the *-pc-windows-gnu pair. Those targets
need `rustup target add`; the recipe does not run it, for the same reason no
recipe here installs a compiler.

Everything obfstr.py records about the shape of this data holds unchanged,
because it is a property of the crate rather than of the container: what
lands in the image is obfstr::xref::inner, which upstream marks
`#[inline(never)]` and which is generic over `const SEED: u64`, so there is
exactly one monomorphisation per obfuscated item and each is a different
shape - the seed picks the obfchoice arms and drives the obfstmt!
control-flow flattening around them.

The driver stays `#![no_std]` with `panic = "abort"` and
`crate-type = ["cdylib"]`, and on this side that matters more, not less. A
stock Rust cdylib links the whole of std into the object statically - Rust
has no shared libstd on any stable target - and every one of those functions
would be filed under obfstr's family name, which is the trap the nlohmann
recipe records for -static-libstdc++. obfstr is itself
`#![cfg_attr(not(test), no_std)]` with no dependencies, so nothing is given
up. Rust also gives a cdylib's symbols hidden visibility of its own accord:
measured with `nm -D` on both artefacts, the dynamic symbol table holds
exactly one exported function, the `#[unsafe(no_mangle)] pub extern "C"`
entry point. So this recipe needs no equivalent of the -fvisibility=hidden
the C++ ones pass, and for the same reason it has almost no .plt to show for
itself - 3 unnamed stubs on each architecture.

OBFSTR_SEED is deliberately left unset, which is obfstr's own reproducible
default: it reads the variable through option_env! and falls back to the
literal "FIXED", so setting it would make every seed, and therefore every
function body, depend on an environment variable nothing records.

Measured on the artefacts: 50 functions on x64 and 55 on x86, of which 46 are
obfstr's own on each - one per obfuscated item, the same 46 the PE artefacts
carry. Verified with nm on both .so files: zero _ZN4core, _ZN3std, _ZN5alloc
and compiler_builtins symbols, and zero 64-bit integer helpers. The x86
artefact's five extra functions are _init, _fini, the tm_clones pair and
__do_global_dtors_aux, which the measured baseline cannot match by PicHash
on 32-bit PIC - see obfuscate_linux.py, which records why. Note the contrast
with the PE side, where the x86 report carries 68 functions against x64's 49
because i686 Windows uses DWARF exception machinery this target does not.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# {platform} is the CPU half of the toolchain's triple, "i686" or "x86_64",
# which is also the CPU half of the Rust target triple. The MinGW recipe gets
# it by splitting the cross compiler's prefix; the native compilers have no
# prefix to split, so toolchain.placeholders derives it from the bitness
# there instead - which it has to, or this string would expand to
# "-unknown-linux-gnu" and cargo would report an unknown target.
_TARGET = "{platform}-unknown-linux-gnu"

# rm -rf first so a re-run against a cached checkout copies the driver rather
# than nesting a second copy inside the first.
_COPY = ("rm -rf obfstr_driver && "
         "cp -r {repo}/scripts/corpus/exercisers/obfstr_driver obfstr_driver")

# --offline because the driver's only dependency is the path dependency on
# the pinned checkout: nothing should be resolved from crates.io, and this
# makes that a build failure rather than a silent download.
_BUILD = "cargo build --release --offline --target " + _TARGET


RECIPES = {
    "obfstr_0.4.6_linux": Recipe(
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
            path="obfstr_driver/target/" + _TARGET + "/release/libobfstr_driver.so",
            component="obfstr_driver.so")],
        toolchains=["linux_x86", "linux_x64"],
        requires=["cargo"],
        # Spelled out rather than written with {platform}: provenance strings
        # are copied into the record verbatim and are deliberately not
        # placeholder-expanded (pipeline.py takes build_flags straight off the
        # recipe), so a placeholder here would ship as literal text.
        build_flags="cargo --release (opt-level 3, LTO off) for "
                    "i686-unknown-linux-gnu / x86_64-unknown-linux-gnu, "
                    "driver crate #![no_std] with panic=abort, OBFSTR_SEED "
                    "unset",
        notes="The ELF build of the same tag and the same driver crate as the "
              "MinGW artefacts of this family, so the two are comparable. "
              "Built from a driver crate, since the library is a compiletime "
              "obfuscator and emits nothing until a consumer uses its macros; "
              "the emitted functions are the library's own. Rust edition "
              "2024, so rustc 1.85 or newer is required, and the two targets "
              "need `rustup target add i686-unknown-linux-gnu "
              "x86_64-unknown-linux-gnu`. The artefact is dominated by "
              "obfstr::xref::inner, which upstream marks #[inline(never)] and "
              "which is generic over `const SEED: u64`: one monomorphisation "
              "per obfuscated item, for the 46 strings, byte strings, C "
              "strings, wide strings and xrefs the driver obfuscates. The "
              "driver is #![no_std] with panic=abort so the image contains no "
              "Rust std or core code to be misfiled under this family - which "
              "matters more on this target than on Windows, since Rust has no "
              "shared libstd anywhere and a stock cdylib would link all of it "
              "statically. OBFSTR_SEED is left unset, which is obfstr's own "
              "reproducible default (option_env! falls back to \"FIXED\").",
    ),
}
