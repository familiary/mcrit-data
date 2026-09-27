"""katursis/StringObfuscator, built for Linux and ELF.

The ELF counterpart of katursis_obfuscator.py: same pinned commit, same
exerciser, same -O2, different container.

-O2 is as mandatory here as it is on the PE side, and for the same reason -
upstream's README says "Requirements - O2" and means it. Re-measured on this
toolchain by grepping the built .so for three of the exerciser's plaintext
literals: 22 hits at -O0, 0 at -O1 and 0 at -O2. At -O0 the constexpr
constructor is not folded, the encryption never happens, and the literals sit
in the image in clear text; an -O0 build of this library is not an obfuscated
build at all and there would be nothing worth recording from one. That makes
this family the exact opposite of Obfuscate and StringObfuscatorCT, which
only emit anything at -O0 - on both platforms.

The function count does not move with the level once the obfuscation happens
at all: measured here, 60 of the library's own functions at -O1 and 60 at
-O2 (against 180 at -O0, which are the unobfuscated ones). -O2 is recorded
because that is what upstream asks for.

What survives -O2 is decrypt(), and only decrypt(), because it is the one
member upstream marks __attribute__((noinline)) under `#ifdef __GNUC__` - a
branch the native GCC takes just as the mingw-w64 one does. The count follows
the number of distinct string *lengths* rather than the number of strings,
since string_encryptor is templated on the buffer size alone with the key
being S % 255: the exerciser sweeps lengths 4 to 63 and yields exactly 60
decrypt() bodies, and the two extra literals at a length already covered add
none.

A ``.so`` linking glibc dynamically, for the reason recorded on
obfuscate_linux.py: nothing of the C runtime is then in the image to be
misfiled under this family's name. Measured on the x64 artefact: 65
functions, 60 the library's decrypt() bodies, 1 the exerciser's and 4
unnamed .plt/.plt.sec stubs. The x86 artefact is 71, the extra six being the
32-bit PIC link glue the measured baseline cannot match by PicHash - see
obfuscate_linux.py, which records why.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# -I. because str_obfuscator.hpp is at the repository root. -fPIC,
# {archflag} and -fvisibility=hidden for the reasons recorded on
# obfuscate_linux.py; no -shared-libgcc, which is already the default when
# linking with g++ on Linux.
_BUILD = ("{cxx} {archflag} -std=c++14 -O2 -shared -fPIC -fvisibility=hidden "
          "-I. -o katursis_str_obfuscator.so "
          "{repo}/scripts/corpus/exercisers/katursis_str_obfuscator.cpp")


RECIPES = {
    "StringObfuscator_2021-08-07_linux": Recipe(
        family="StringObfuscator",
        version="2021-08-07",
        upstream="https://github.com/katursis/StringObfuscator",
        license="MIT, Copyright (c) 2016 katursis",
        source=Source(git_url="https://github.com/katursis/StringObfuscator.git",
                      git_ref="9bfc18b4165621807de74e37164b85fa318ceed2"),
        build=[BuildStep(_BUILD)],
        artifacts=[Artifact(path="katursis_str_obfuscator.so",
                            component="katursis_str_obfuscator.so")],
        toolchains=["linux_x86", "linux_x64"],
        build_flags="-O2 -std=c++14 -fPIC -shared -fvisibility=hidden "
                    "(exerciser; -O2 is required by upstream, see notes)",
        notes="The ELF build of the same commit and the same exerciser as the "
              "MinGW artefacts of this family, so the two are comparable. "
              "Built from an exerciser translation unit, since the library is "
              "header-only and constexpr; the emitted functions are the "
              "library's own. -O2 is mandatory, not preferred: upstream's "
              "README states 'Requirements - O2', and at -O0 the constexpr "
              "constructor is not folded, so the strings are never encrypted "
              "and appear in the image in clear text - re-measured on this "
              "toolchain at 22 plaintext hits at -O0 and 0 at -O1 and -O2. "
              "This is the reverse of the Obfuscate and StringObfuscatorCT "
              "families "
              "here, which only emit anything at -O0. string_encryptor is "
              "templated on the buffer size alone, with the key being "
              "S % 255, so the number of functions follows the number of "
              "distinct string lengths rather than the number of strings: the "
              "exerciser sweeps lengths 4-63 and yields exactly 60 decrypt() "
              "bodies. decrypt() survives -O2 only because upstream marks it "
              "__attribute__((noinline)) under #ifdef __GNUC__, which the "
              "native GCC takes as the mingw-w64 one does. Built -shared so "
              "glibc stays out of the image, and -fvisibility=hidden so the "
              "object exports only the exerciser's entry point and calls its "
              "own functions directly, which is what the MinGW DLL does. The "
              "32-bit artefact needs gcc-multilib and g++-multilib installed.",
    ),
}
