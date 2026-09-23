"""katursis/StringObfuscator - a three-file C++14 compile-time string encryptor.

A single header, header-only and constexpr, so the reference data comes from
compiling scripts/corpus/exercisers/katursis_str_obfuscator.cpp - a consumer,
not a modification.

Built at -O2, which is the opposite of the other compile-time string
obfuscators in this corpus and is not a choice. Upstream's README lists
"Requirements - O2" and it is literal: at -O0 the constexpr constructor is
not folded, the encryption never happens, and the literals sit in the image
in clear text. Measured on this exerciser with GCC 13, grepping the DLL for
four of the plaintext literals: 26 hits at -O0, 0 at -O1 and 0 at -O2. So an
-O0 build of this library is not an obfuscated build at all, and there would
be nothing worth recording from one.

What survives -O2 is decrypt(), and only decrypt(), because it is the one
member upstream marks __attribute__((noinline)) - under `#ifdef __GNUC__`.
The constructor and detail::encryptor<> are constexpr and always_inline and
disappear into the caller.

The count is driven by distinct string *lengths*, not by the number of
strings: string_encryptor is templated on the buffer size alone and the key
is S % 255. The exerciser sweeps lengths 4 to 63 and gets exactly 60
decrypt() bodies, one per length - 36-41 bytes on x86, 36-63 on x64 - plus
two extra literals at a length already covered which, as expected, add no
function at all.

MSVC is deliberately not covered. The noinline attribute is inside the
__GNUC__ branch, and the _MSC_VER branch defines only `forceinline`, so
under cl decrypt() has nothing stopping it being inlined away entirely and
the artefact could come back empty. That is untested here rather than known;
it is flagged because a reader would otherwise reasonably assume an MSVC
counterpart would work the way the MinGW one does.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# -I. because str_obfuscator.hpp is at the repository root. -shared-libgcc
# rather than -static-libstdc++, which would pull thousands of libstdc++ and
# libgcc functions into the sample under this family's name.
_BUILD = ("{cxx} -std=c++14 -O2 -shared -I. "
          "-o katursis_str_obfuscator.dll "
          "{repo}/scripts/corpus/exercisers/katursis_str_obfuscator.cpp "
          "-shared-libgcc")


RECIPES = {
    # No tags; pinned by full SHA. The repository is three files and has not
    # moved since.
    "StringObfuscator_2021-08-07": Recipe(
        family="StringObfuscator",
        version="2021-08-07",
        upstream="https://github.com/katursis/StringObfuscator",
        license="MIT, Copyright (c) 2016 katursis",
        source=Source(git_url="https://github.com/katursis/StringObfuscator.git",
                      git_ref="9bfc18b4165621807de74e37164b85fa318ceed2"),
        build=[BuildStep(_BUILD)],
        artifacts=[Artifact(path="katursis_str_obfuscator.dll",
                            component="katursis_str_obfuscator.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 -std=c++14 (exerciser; -O2 is required by upstream, "
                    "see notes)",
        notes="Built from an exerciser translation unit, since the library is "
              "header-only and constexpr; the emitted functions are the "
              "library's own. -O2 is mandatory, not preferred: upstream's "
              "README states 'Requirements - O2', and at -O0 the constexpr "
              "constructor is not folded, so the strings are never encrypted "
              "and appear in the image in clear text (measured: 26 plaintext "
              "hits at -O0, 0 at -O1 and -O2). This is the reverse of the "
              "Obfuscate and StringObfuscatorCT families here, which only "
              "emit anything at -O0. string_encryptor is templated on the "
              "buffer size alone, with the key being S % 255, so the number "
              "of functions follows the number of distinct string lengths "
              "rather than the number of strings: the exerciser sweeps "
              "lengths 4-63 and yields exactly 60 decrypt() bodies, 36-41 "
              "bytes on x86 and 36-63 on x64. "
              "decrypt() survives -O2 only because upstream marks it "
              "__attribute__((noinline)) under #ifdef __GNUC__; the MSVC "
              "branch of that #ifdef sets no such attribute, so an MSVC "
              "build may inline it away and emit nothing - untested here, "
              "and specifically at risk. str_obfuscator.hpp is not "
              "self-contained (it names std::size_t and includes nothing), "
              "so the exerciser includes <cstddef> ahead of it.",
    ),
}
