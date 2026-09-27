"""wow64pp built with MSVC, beside the MinGW build of the same commit.

The library is header-only, so none of it exists in a binary until a
translation unit uses it. The MinGW recipe solves that by compiling
scripts/corpus/exercisers/wow64pp.cpp into a DLL; this one compiles the same
exerciser with cl, so the two artefacts differ in the compiler and nothing
else. The functions that land in the binary are wow64pp's; the exerciser
only selects which.

Both compilers are worth having for this library rather than only the
likelier one. Upstream's README is explicit that avoiding inline assembly is
the point - it is "based on wow64ext ... however not using inline assembly
allowing it to work on other compilers like MinGW" - so GCC is a supported
configuration a user may actually have shipped. MSVC is still the likelier
sighting in Windows malware, and the two renderings are far apart: this is
C++ with std::string, std::error_code, std::unique_ptr and a variadic
template, and MSVC's name mangling, exception tables and template
instantiation all differ from GCC's, so the MinGW artefact matches an MSVC
build of this header weakly at best.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

x86 only, as the MinGW recipe is. wow64pp.hpp:779 passes
"reinterpret_cast<std::uint32_t>(&ret)" into the far-call stub, which on a
64-bit target is a hard error rather than a warning - verified with
x86_64-w64-mingw32-g++ 13, "cast from 'uint32_t*' to 'uint32_t' loses
precision", and cl's C2440 is the same refusal. Upstream's CMakeLists.txt
appends "/machine:X86" to CMAKE_EXE_LINKER_FLAGS unconditionally, so this is
upstream's own conclusion as well.

Upstream's own tests are not the driver here and could not be: upstream
never tagged a release either, so both recipes pin the full commit hash of
master as of 2020-09-19.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# /std:c++14 is upstream's own - CMakeLists.txt sets CMAKE_CXX_STANDARD 14
# with CMAKE_CXX_STANDARD_REQUIRED ON - and it is what the MinGW recipe
# passes as -std=c++14, so the pair really does differ only in the compiler.
# It also keeps std::aligned_storage, which detail::read_memory<T> is built
# on, out of deprecation territory.
#
# /MD rather than cl's default: /LD implies /MT, and a static CRT put 1947 of
# VX-API's 4219 functions into that artefact as MSVC C runtime, duplicating
# data/MSVC. /EHsc because the throwing half of this library's API is half of
# its API - module_handle, import and the detail:: functions behind them all
# raise std::system_error, and the exerciser catches it.
#
# The compiler PDB and the linker PDB are given different names on purpose.
# MSVC keeps symbols in a PDB rather than in a COFF symbol table, and it is
# the linker's PDB - the one with final addresses - that SMDA needs, so that
# is the file declared on the Artifact. Pointing /Fd and /PDB: at one path
# would have link.exe write the file it is reading its type information from.
_COMPILE = ('cl /nologo /c /O2 /MD /Zi /EHsc /std:c++14 /Iinclude '
            '/Fdwow64pp.compiler.pdb /Fowow64pp.obj '
            '{repo}/scripts/corpus/exercisers/wow64pp.cpp')

# A DLL, not a .lib: SMDA cannot read a static library. The exerciser's entry
# points are already extern "C" __declspec(dllexport), so the image has a real
# export table without a .def file.
#
# kernel32.lib is named explicitly. link.exe invoked from the command line
# adds only the defaultlibs the objects ask for, and the five Win32 functions
# wow64pp declares for itself - GetLastError, GetCurrentProcess,
# DuplicateHandle, GetModuleHandleA, GetProcAddress - plus the VirtualAlloc
# and CloseHandle it uses without declaring are all kernel32's.
#
# /Brepro drops the build timestamp MSVC stamps into the PE header, without
# which two runs over identical source record different sha256s. /OPT:NOREF
# keeps routines nothing references, which is most of what this exerciser
# emits, and /OPT:NOICF keeps two routines that compiled to identical bodies
# apart - the throwing and error_code halves of this header are near-twins by
# construction, which is exactly the shape folding destroys, and it cost
# VX-API its StringConcat/StringCopy pair.
#
# /INCREMENTAL:NO because /DEBUG implies /INCREMENTAL and the /OPT:NO* forms
# above do not suppress it - only /OPT:REF, /OPT:ICF and /OPT:ORDER are
# documented to. An incrementally linked image reaches each function through a
# jump table, and SMDA recovers every one of those one-instruction thunks as a
# function of its own, unnamed: 2936 of nlohmann_json 3.12.0 x86's 5205
# functions, before smdaify.assert_not_incrementally_linked began refusing it.
_LINK = ('link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO '
         '/OPT:NOREF /OPT:NOICF '
         '/PDB:wow64pp.pdb /OUT:wow64pp.dll wow64pp.obj kernel32.lib')

_FLAGS = ("/O2 /MD /Zi /EHsc /std:c++14; "
          "/DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link")


RECIPES = {
    "wow64pp_2020-09-19_msvc": Recipe(
        family="wow64pp",
        version="2020-09-19",
        upstream="https://github.com/JustasMasiulis/wow64pp",
        license="Apache-2.0",
        source=Source(git_url="https://github.com/JustasMasiulis/wow64pp.git",
                      git_ref="4573048c41657cf66555a87a736720ab8712cbdd"),
        build=[BuildStep(_COMPILE), BuildStep(_LINK)],
        artifacts=[Artifact(path="wow64pp.dll", component="wow64pp.dll",
                            pdb="wow64pp.pdb")],
        toolchains=["msvc_x86"],
        build_flags=_FLAGS,
        notes="Built from the same exerciser translation unit as the MinGW "
              "recipe for this commit, so the emitted functions are the same "
              "library code selected the same way and the two artefacts "
              "differ in the compiler alone. What that exerciser produced "
              "under i686-w64-mingw32-g++ 13 is the yardstick for this one: "
              "83 functions, of which 23 are wow64pp's own, including both "
              "call_function arities and all four detail::read_memory forms. "
              "Expect the MSVC sample to carry a larger share of standard "
              "library instantiation, the usual property of a header-only "
              "C++ library compiled by cl, and whatever the MSVC C++ probe "
              "in baseline.py does not reach survives the glue filter under "
              "this family name - a property of the baseline rather than of "
              "this build, and the reason to read this sample alongside "
              "data/MSVC. No dependencies: the library is header-only and "
              "the DLL is built against the DLL runtime, so the MSVC C "
              "runtime is imported rather than linked in.",
    ),
}
