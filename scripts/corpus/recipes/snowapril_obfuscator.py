"""Snowapril/String-Obfuscator-In-Compile-Time - a C++14 compile-time XOR-free
string obfuscator built out of template metaprogramming.

Two headers, no build system of any kind, and the whole affine cipher
(`(A * c + B) % 127`, inverted with a compile-time extended Euclid) lives in
the type system. Nothing of it exists in a binary until a translation unit
expands OBFUSCATE, so the reference data comes from compiling
scripts/corpus/exercisers/snowapril_obfuscator.cpp, a consumer.

Built at -O0, and here that is not a preference but the only choice.
Measured with GCC 13 on this exerciser:

    -O0   251 of the library's own functions (4 per string - the constructor,
          the public decrypt(), and the private encrypt(char)/decrypt(int)
          pair - plus a shared snowapril::positive_modulo)
    -O1    15 functions
    -O2    15-17 functions

Everything the library does is a loop over a compile-time-sized buffer inside
a temporary that dies at the end of the statement, so any optimiser folds it
into the caller. This data describes an -O0 consumer; an optimised one has
almost nothing left to match.

SOURCE_DATE_EPOCH is set, and that is the interesting part of this recipe.
meta_random.hpp derives its seed from __TIME__, so the cipher parameters A
and B - which are template arguments, and therefore part of every mangled
name - change on every build. Two builds a minute apart produced 496
differing symbol lines out of 248 symbols, i.e. not one function kept its
name, and the object file differed from byte 9. GCC honours SOURCE_DATE_EPOCH
by freezing __DATE__ and __TIME__, and with it set the object file is
byte-identical across rebuilds and every symbol matches. That is a compiler
environment setting, not a patch: upstream source is untouched.

The value used is the pinned commit's own author timestamp, 1576062057
(2019-12-11T11:00:57Z), which yields __TIME__ = "11:00:57" and a seed of
39657. A round midnight epoch would make RandomSeed() evaluate to exactly
zero - the header's arithmetic is built to cancel at "00:00:00" - and the
generator would then start from a degenerate state, which is not what a real
build of this library looks like.

What SOURCE_DATE_EPOCH does *not* fix is the PE image itself: two runs still
differ in 667 bytes. That is not this project's doing. GNU ld stamps a link
timestamp into the COFF header and picks a fresh randomised image base for
every DLL, so every MinGW artefact in this corpus has the same property - a
one-line trivial DLL rebuilt twice differs in 1000 bytes the same way.
Pinning both with -Wl,--no-insert-timestamp -Wl,--image-base brings the
difference down to 2 bytes, which confirms where it comes from; those flags
are deliberately not used here, so this artefact is linked exactly like every
other MinGW artefact in the corpus.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_BUILD = ("{cxx} -std=c++14 -O0 -shared -Iinclude "
          "-o snowapril_obfuscator.dll "
          "{repo}/scripts/corpus/exercisers/snowapril_obfuscator.cpp "
          "-shared-libgcc")


RECIPES = {
    # No tags have ever been cut, so this is pinned by full SHA: the merge
    # that is HEAD as of writing.
    "StringObfuscatorCT_2019-12-11": Recipe(
        family="StringObfuscatorCT",
        version="2019-12-11",
        upstream="https://github.com/Snowapril/String-Obfuscator-In-Compile-Time",
        # Recorded as it stands rather than as it was presumably meant: the
        # LICENSE file is the MIT text with "Copyright (c) 2018 " and no
        # holder after the year.
        license="MIT (LICENSE carries the MIT text with the copyright line "
                "left as 'Copyright (c) 2018 ' - no holder is named)",
        source=Source(
            git_url="https://github.com/Snowapril/String-Obfuscator-In-Compile-Time.git",
            git_ref="93718ba36c1e1f22289a85354ca6849931968d48"),
        build=[BuildStep(_BUILD, env={"SOURCE_DATE_EPOCH": "1576062057"})],
        artifacts=[Artifact(path="snowapril_obfuscator.dll",
                            component="snowapril_obfuscator.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O0 -std=c++14 SOURCE_DATE_EPOCH=1576062057 "
                    "(exerciser; both settings are load-bearing, see notes)",
        notes="Built from an exerciser translation unit, since the library is "
              "header-only and its cipher runs entirely in the type system; "
              "the emitted functions are the library's own. -O0 is the only "
              "usable level: at -O1 the same exerciser leaves 15 of the "
              "library's functions against 251 at -O0, because every "
              "OBFUSCATE builds a temporary that dies at the end of the "
              "statement and the optimiser folds it into the caller. "
              "SOURCE_DATE_EPOCH is set because meta_random.hpp seeds itself "
              "from __TIME__ and the resulting cipher parameters are template "
              "arguments: without it no two builds share a single mangled "
              "name (measured: 496 differing symbol lines over 248 symbols "
              "between builds a minute apart). With it the object file is "
              "byte-identical across rebuilds. The linked DLL still is not, "
              "by 667 bytes, but that is GNU ld's link timestamp and "
              "randomised image base and is true of every MinGW artefact "
              "here. obfuscator.hpp is also not self-contained - it uses an "
              "unqualified size_t and includes only <array> - so the "
              "exerciser includes <cstddef> ahead of it.",
    ),
}
