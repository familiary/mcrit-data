"""wow64pp - a header-only Heaven's Gate implementation, built with MinGW.

A WOW64 process runs 32-bit code under a 64-bit kernel and keeps a second,
64-bit ntdll mapped that its own loader cannot see. wow64pp reaches that
side: it reads the 64-bit PEB through NtWow64QueryInformationProcess64, walks
the 64-bit loader list to find a module, parses the x64 export directory to
locate LdrGetProcedureAddress, and then far-calls into 64-bit code through a
hand-assembled stub that pushes the 0x33 code selector and retf's. That
far-call sequence is the "Heaven's Gate" an analyst is looking for, and it is
the one piece of a WOW64 transition that a malware author is most likely to
have copied rather than written.

Header-only: CMakeLists.txt declares "add_library(wow64pp INTERFACE)" and
target_sources lists the one header, so nothing of the library exists in a
binary until a translation unit uses it and there is no upstream artefact to
disassemble. scripts/corpus/exercisers/wow64pp.cpp is the driver; the
functions that land in the DLL are wow64pp's, and the exerciser only selects
which. Upstream's own consumer cannot serve: test/CMakeLists.txt includes
"${PROJECT_SOURCE_DIR}/test/Catch/contrib/ParseAndAddCatchTests.cmake" and
test/Catch is a submodule the repository references but does not contain, so
cmake configure fails before anything is compiled.

x86 only, and not by choice. wow64pp.hpp:779 passes
"reinterpret_cast<std::uint32_t>(&ret)" to the stub, which is a hard error on
a 64-bit target rather than a warning - measured with
x86_64-w64-mingw32-g++ 13, "cast from 'uint32_t*' to 'uint32_t' loses
precision", four times from that one line. Upstream agrees: its CMakeLists.txt
appends "/machine:X86" to CMAKE_EXE_LINKER_FLAGS unconditionally. The library
is also meaningless on x64, where there is no gate to open.

MinGW is covered here *and* MSVC in wow64pp_msvc.py, which is worth the
duplication for this one library: upstream's README says it is "based on
wow64ext ... however not using inline assembly allowing it to work on other
compilers like MinGW", so a GCC build is a configuration the author
specifically supports and expects to be used, not an approximation of an
MSVC-only project. Verified rather than assumed: i686-w64-mingw32-g++ 13
compiles and links the exerciser with no warnings beyond one about the
exported array. C++ is also where the two compilers diverge most - name
mangling, exception tables and template instantiation all differ - so the
pair is two genuinely different renderings of the same source.

No pinned tag exists; upstream has never tagged a release, so the pin is the
full commit hash of master as of 2020-09-19 and the version string is that
date.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# -std=c++14 is upstream's own: CMakeLists.txt sets CMAKE_CXX_STANDARD 14 with
# CMAKE_CXX_STANDARD_REQUIRED ON. The MSVC recipe passes /std:c++14 for the
# same reason, so the two artefacts differ in the compiler and nothing else.
#
# A DLL, not an EXE: the exerciser exports two entry points and defines no
# main, so an executable link has no entry point and mingw's startup object
# asks for WinMain instead - the same reason libstdcxx.py gives.
#
# -shared-libgcc rather than the static default, for the reason nlohmann.py
# records: -static-libstdc++ would pull roughly thirteen thousand libstdc++
# and libgcc functions into a sample that is supposed to be wow64pp. The
# library does use std::string, std::error_code and std::make_unique, so some
# standard-library instantiation is unavoidable and is what the glue filter
# is for.
_BUILD = ("{cxx} -std=c++14 -O2 -shared -Iinclude "
          "-o wow64pp.dll {repo}/scripts/corpus/exercisers/wow64pp.cpp "
          "-shared-libgcc")


RECIPES = {
    "wow64pp_2020-09-19": Recipe(
        family="wow64pp",
        version="2020-09-19",
        upstream="https://github.com/JustasMasiulis/wow64pp",
        license="Apache-2.0",
        source=Source(git_url="https://github.com/JustasMasiulis/wow64pp.git",
                      git_ref="4573048c41657cf66555a87a736720ab8712cbdd"),
        build=[BuildStep(_BUILD)],
        artifacts=[Artifact(path="wow64pp.dll", component="wow64pp.dll")],
        # x86 only; see the module docstring. SysWhispers does the same thing
        # in the other direction and needs no special case anywhere.
        toolchains=["mingw_x86"],
        build_flags="-O2 -std=c++14 -shared -shared-libgcc",
        notes="Built from an exerciser translation unit, since the library is "
              "header-only; the emitted functions are the library's own and "
              "the exerciser only selects which. Coverage is every entry "
              "point the header has - module_handle, import and "
              "call_function in both their throwing and error_code forms, "
              "and the detail:: layer they are built from - because all of "
              "them are `inline` and an optimiser that swallowed a call site "
              "would leave nothing in the image, so the exerciser takes each "
              "function's address as well as calling it. Both call_function "
              "arities are present: four arguments or fewer never reaches "
              "the loop that pushes overflow arguments onto the 64-bit "
              "stack, so the two are different code. The MSVC counterpart of "
              "this artefact is built from the same exerciser by "
              "wow64pp_msvc.py.",
    ),
}
