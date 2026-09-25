"""nlohmann/json built with MSVC, beside the MinGW builds of the same tags.

The library is header-only, so none of it exists in a binary until a
translation unit uses it, and there is no upstream artefact to disassemble.
The MinGW recipe solves that by compiling
scripts/corpus/exercisers/nlohmann_json.cpp into a DLL; this one compiles
the same exerciser with cl, so the two artefacts differ in the compiler and
nothing else. The functions that land in the binary are nlohmann's; the
exerciser only selects which.

That matters more here than for a compiled library. MSVC instantiates C++
templates into a completely different shape from GCC, so the existing MinGW
artefacts match an MSVC sighting of this library barely at all - and
nlohmann/json in Windows software is overwhelmingly an MSVC sighting.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

What was read rather than assumed, in the pinned trees:
  * include/nlohmann/json.hpp is the include root at both tags, so /Iinclude
    is the same include path the MinGW recipe passes.
  * detail/macro_scope.hpp selects JSON_HAS_CPP_17 from
    "(defined(__cplusplus) && __cplusplus > 201703L) || (defined(_MSVC_LANG)
    && _MSVC_LANG > 201703L)" - it reads _MSVC_LANG explicitly, so /std:c++17
    alone puts the library in the same mode /Zc:__cplusplus would, and that
    switch is deliberately not passed.
  * upstream's own tests/CMakeLists.txt adds
    "$<$<CXX_COMPILER_ID:MSVC>:/bigobj>", which is why /bigobj is here: this
    exerciser instantiates the whole serialiser plus the CBOR, MessagePack,
    BSON and UBJSON writers in one translation unit, and MSVC's 65279-section
    object limit is a real ceiling for that, not a theoretical one.
  * neither include tree contains a non-ASCII byte, so /utf-8 would change
    nothing and is not passed.

Two of the three MinGW versions are covered. 3.12.0 is current and the
counterpart of the newest MinGW artefact; 3.11.3 is the release actually
vendored almost everywhere and is post-3.11's inline-namespace and
serialiser rework. 3.10.5 is left out on purpose: it is pre-3.11 code whose
own macro_scope.hpp carries the "_MSC_VER < 1940" filesystem guard that
3.11.3 corrected to 1914, so on a current toolset it takes a different
JSON_HAS_FILESYSTEM branch from the one its MinGW sibling takes, and it is
the version least likely to have been built against a 19.4x front end
upstream. Covering it is a separate decision from proving the toolchain.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# /MD rather than cl's default: /LD implies /MT, and a static CRT put 1947 of
# VX-API's 4219 functions into that artefact as MSVC C runtime, duplicating
# data/MSVC. /EHsc because the exerciser catches json::exception and
# json::parse_error and the standard library wants real unwind semantics;
# CMake passes it by default for MSVC C++ for the same reason.
#
# The compiler PDB and the linker PDB are given different names on purpose.
# MSVC keeps symbols in a PDB rather than in a COFF symbol table, and it is
# the linker's PDB - the one with final addresses - that SMDA needs, so that
# is the file declared on the Artifact. Pointing /Fd and /PDB: at one path
# would have link.exe write the file it is reading its type information from;
# CMake avoids that by naming the compile PDB separately and this does the
# same.
_COMPILE = ('cl /nologo /c /O2 /MD /Zi /EHsc /bigobj /std:c++17 /Iinclude '
            '/Fdnlohmann_json.compiler.pdb /Fonlohmann_json.obj '
            '{repo}/scripts/corpus/exercisers/nlohmann_json.cpp')

# A DLL, not a .lib: SMDA cannot read a static library. The exerciser's
# entry point is already extern "C" __declspec(dllexport), so the image has a
# real export table without CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS or a .def.
#
# /Brepro drops the build timestamp MSVC stamps into the PE header, without
# which two runs over identical source record different sha256s. /OPT:NOREF
# keeps routines nothing references - which is most of what an exerciser
# instantiates - and /OPT:NOICF keeps two routines that compiled to identical
# bodies apart; template instantiation over related types produces a great
# many such pairs, and folding them cost VX-API its StringConcat/StringCopy
# pair. link /DEBUG is documented to imply both, but the corpus says what it
# wants rather than relying on that.
#
# /INCREMENTAL:NO because /DEBUG implies /INCREMENTAL and the /OPT:NO* forms
# above do not suppress it - only /OPT:REF, /OPT:ICF and /OPT:ORDER are
# documented to. An incrementally linked image reaches each function through a
# jump table, and SMDA recovers every one of those one-instruction thunks as a
# function of its own, unnamed. That was measured on the artefacts this
# omission produced: 2936 of nlohmann_json 3.12.0 x86's 5205 functions. It is
# not what a released binary looks like, and it inflates the function count of
# the family it is filed under.
_LINK = ('link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO '
         '/OPT:NOREF /OPT:NOICF '
         '/PDB:nlohmann_json.pdb /OUT:nlohmann_json.dll nlohmann_json.obj')

_FLAGS = ("/O2 /MD /Zi /EHsc /bigobj /std:c++17; "
          "/DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link")


def _nlohmann_msvc(version, git_ref):
    return Recipe(
        family="nlohmann_json",
        version=version,
        upstream="https://github.com/nlohmann/json",
        license="MIT",
        source=Source(git_url="https://github.com/nlohmann/json.git",
                      git_ref=git_ref),
        build=[BuildStep(_COMPILE), BuildStep(_LINK)],
        artifacts=[Artifact(path="nlohmann_json.dll",
                            component="nlohmann_json.dll",
                            pdb="nlohmann_json.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS,
        notes="Built from the same exerciser translation unit as the MinGW "
              "recipe for this tag, so the emitted functions are the same "
              "library code selected the same way and the two artefacts "
              "differ in the compiler alone. Expect a large share of the "
              "sample to be MSVC STL instantiations rather than nlohmann's "
              "own template code: a header-only C++ library compiled by cl "
              "is mostly std:: by function count, and whatever the MSVC C++ "
              "probe in baseline.py does not reach survives the glue filter "
              "under this family name. That is a property of the baseline, "
              "not of this build - refilter is the lever for it - and it is "
              "the reason to read these two samples alongside data/MSVC. "
              "This family is the one most exposed to it. No dependencies: the "
              "library is header-only and the DLL is built against the DLL "
              "runtime, so the MSVC C runtime is imported rather than linked "
              "in.",
    )


RECIPES = {
    # The release vendored almost everywhere, and the first of the post-3.11
    # serialiser rework.
    "nlohmann_json_3.11.3_msvc": _nlohmann_msvc("3.11.3", "v3.11.3"),
    # Current, and the direct counterpart of the newest MinGW artefact.
    "nlohmann_json_3.12.0_msvc": _nlohmann_msvc("3.12.0", "v3.12.0"),
}
