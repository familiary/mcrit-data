"""adamyaxley/Obfuscate - compile-time string literal obfuscation for C++14.

A single header, and one of the two or three string obfuscators that turn up
by name in commodity Windows malware. Header-only and almost entirely
constexpr, so nothing of it exists in a binary until a translation unit
expands AY_OBFUSCATE: there is no upstream artefact to disassemble, and the
reference data comes from compiling
scripts/corpus/exercisers/ay_obfuscate.cpp, which is a consumer of the
library rather than a modification of it.

Built at -O0, which is the whole provenance question for this family and the
reason the level is spelled out in build_flags as well as here. Measured with
GCC 13 on this exerciser:

    -O0   324 of the library's own functions (5 per string plus one shared
          ay::cipher<CHAR_TYPE>)
    -O1    71-74 functions, mostly 21-byte bodies
    -O2    72-75 functions, but every one of them a 5-byte
          `endbr64; ret` destructor stub - the constructor, the decrypt and
          the char* conversion have all been inlined into the caller and
          nothing identifiable is left

So this data describes an -O0 consumer of the library. It will match a debug
build well and an -O2 release build not at all, because at -O2 there is
nothing of the library left in the image to match.

The upstream tests are deliberately not built: CMakeLists.txt FetchContents
googletest at configure time, which needs the network.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# -I. because obfuscate.h sits at the repository root. -shared-libgcc, not
# -static-libstdc++: a static libstdc++ pulls roughly thirteen thousand
# libstdc++ and libgcc functions into the sample under this family's name,
# as recorded on the nlohmann recipe.
_BUILD = ("{cxx} -std=c++14 -O0 -shared -I. "
          "-o ay_obfuscate.dll {repo}/scripts/corpus/exercisers/ay_obfuscate.cpp "
          "-shared-libgcc")


RECIPES = {
    # HEAD, far past the only tag (v1.0.0, 2020): the tag predates the
    # consteval/AY_LINE handling and the char_type deduction that every
    # current checkout carries, so pinning it would describe code nobody
    # fetches today. Pinned by full SHA because there is no tag for this.
    "Obfuscate_2026-06-03": Recipe(
        family="Obfuscate",
        version="2026-06-03",
        upstream="https://github.com/adamyaxley/Obfuscate",
        license="Unlicense (public domain dedication, stated at the foot of "
                "obfuscate.h and in LICENSE)",
        source=Source(git_url="https://github.com/adamyaxley/Obfuscate.git",
                      git_ref="5390a353f4e83ffd596730eab0b0e4ac629dbbbc"),
        build=[BuildStep(_BUILD)],
        artifacts=[Artifact(path="ay_obfuscate.dll",
                            component="ay_obfuscate.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O0 -std=c++14 (exerciser; -O0 chosen deliberately, "
                    "see notes)",
        notes="Built from an exerciser translation unit, since the library is "
              "header-only and constexpr; the emitted functions are the "
              "library's own. -O0 is deliberate and is what this data "
              "describes: at -O2 GCC inlines the constructor, decrypt() and "
              "the char* conversion into the caller and leaves only 5-byte "
              "`endbr64; ret` destructor stubs, so an -O2 consumer of this "
              "library has nothing in it for these functions to match. "
              "obfuscated_data is templated on <N, KEY, CHAR_TYPE> with KEY "
              "defaulting to ay::generate_key(__LINE__), so the exerciser "
              "puts every AY_OBFUSCATE on its own source line; calls sharing "
              "a line and a length collapse into a single instantiation. The "
              "upstream googletest suite is not built - its CMakeLists "
              "FetchContents googletest over the network at configure time.",
    ),
}
