"""Snowapril/String-Obfuscator-In-Compile-Time, built for Linux and ELF.

The ELF counterpart of snowapril_obfuscator.py: same pinned commit, same
exerciser, same -O0, same pinned SOURCE_DATE_EPOCH, different container.

Both of those settings were re-measured on this toolchain rather than carried
over on trust, because both are load-bearing and neither is obviously a
platform-independent property.

-O0 is still the only usable level. GCC 13 on Linux x86_64, same exerciser:

    -O0   125 of the library's own functions (the constructor, the public
          decrypt() and the private encrypt(char)/decrypt(int) pair per
          string, plus the shared snowapril::positive_modulo)
    -O2   8, and all of them constructors - 19 functions in the whole image.
          Every OBFUSCATE builds a temporary that dies at the end of the
          statement, so the optimiser folds decrypt() and the cipher into
          the caller and nothing identifiable is left

SOURCE_DATE_EPOCH is still load-bearing, for the same reason and with the
same value: meta_random.hpp seeds itself from __TIME__, and the resulting
cipher parameters A and B are template arguments, so they are part of every
mangled name. Measured here: two builds a few seconds apart *without* it
share not one of their 124 MetaString names; *with* it set to 1576062057 the
two .so files are byte-identical, sha256 and all. That is a stronger result
than the MinGW side gets - GNU ld stamps a PE with a link timestamp and picks
a randomised image base for every DLL, leaving a 667-byte difference there,
and an ELF shared object has neither.

Measured on the x64 artefact: 131 functions, 125 the library's, 2 the
exerciser's and 4 unnamed .plt/.plt.sec stubs. The x86 artefact is 137, the
extra six being the 32-bit PIC link glue the measured baseline cannot match
by PicHash - see obfuscate_linux.py, which records why.

1576062057 is the pinned commit's own author timestamp
(2019-12-11T11:00:57Z), which yields __TIME__ = "11:00:57" and a seed of
39657. A round midnight epoch would make RandomSeed() evaluate to exactly
zero - the header's arithmetic cancels at "00:00:00" - and the generator
would start from a degenerate state, which is not what a real build of this
library looks like. That is a compiler environment setting, not a patch:
upstream source is untouched.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# -fPIC, {archflag} and -fvisibility=hidden for the reasons recorded at
# length on obfuscate_linux.py. The visibility flag matters most of all here:
# without it the x64 build is 385 functions with 271 of them unnamed .plt
# stubs, and it is *refused*: 113 of the 256 functions above the symbol-check
# floor carry a name, against a 0.5 gate. With it the same source comes out
# at 137 functions with 133 named, 131 once the runtime filter has run. No
# -shared-libgcc: it is already the default when linking with g++ on Linux.
_BUILD = ("{cxx} {archflag} -std=c++14 -O0 -shared -fPIC -fvisibility=hidden "
          "-Iinclude -o snowapril_obfuscator.so "
          "{repo}/scripts/corpus/exercisers/snowapril_obfuscator.cpp")


RECIPES = {
    "StringObfuscatorCT_2019-12-11_linux": Recipe(
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
        artifacts=[Artifact(path="snowapril_obfuscator.so",
                            component="snowapril_obfuscator.so")],
        toolchains=["linux_x86", "linux_x64"],
        build_flags="-O0 -std=c++14 -fPIC -shared -fvisibility=hidden "
                    "SOURCE_DATE_EPOCH=1576062057 (exerciser; every one of "
                    "these is load-bearing, see notes)",
        notes="The ELF build of the same commit and the same exerciser as the "
              "MinGW artefacts of this family, so the two are comparable. "
              "Built from an exerciser translation unit, since the library is "
              "header-only and its cipher runs entirely in the type system; "
              "the emitted functions are the library's own. -O0 is the only "
              "usable level and that was re-measured here rather than "
              "assumed: at -O2 this exerciser emits 8 of the library's "
              "functions, all constructors, against 125 at -O0, because every "
              "OBFUSCATE builds a temporary that dies at the end of the "
              "statement and the optimiser folds it into the caller. "
              "SOURCE_DATE_EPOCH is set because meta_random.hpp seeds "
              "itself from __TIME__ and the "
              "resulting cipher parameters are template arguments: measured "
              "here, two builds seconds apart without it share not one of "
              "their 124 MetaString names. With it the two .so files are "
              "byte-identical - unlike the MinGW artefacts, which still "
              "differ by 667 bytes "
              "of PE link timestamp and randomised image base that an ELF "
              "shared object does not have. obfuscator.hpp is also not "
              "self-contained - it uses an unqualified size_t and includes "
              "only <array> - so the exerciser includes <cstddef> ahead of "
              "it. The 32-bit artefact needs gcc-multilib and g++-multilib "
              "installed.",
    ),
}
