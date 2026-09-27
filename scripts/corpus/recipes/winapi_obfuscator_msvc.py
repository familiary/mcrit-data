"""SaulBerrenson/WinApiObfuscator - hash-resolved WinAPI imports, MSVC only.

One of the WinAPI-obfuscation projects from the lib2smda wishlist. The whole
project is a single 278-line header, winapi_import.hpp, with no build system of
any kind: no CMake, no .sln, no Makefile. It resolves an export by walking the
PEB's loader list for kernel32, hashing every name in the target module's
export directory with MurmurHash2A and comparing against a hash computed at the
call site - the import-hiding shape that shows up in loaders and packers, and
the reason it is worth having in the corpus.

Header-only, so nothing of it exists in a binary until a translation unit uses
it and there is no upstream artefact to disassemble;
scripts/corpus/exercisers/winapi_obfuscator.cpp is the consumer that decides
which instantiations get emitted. The functions that land in the DLL are the
library's own.

MSVC only, and both architectures. get_modules() branches on _WIN64 between
__readgsqword(0x60) and __readfsdword(0x30), so the two legs disassemble to
genuinely different code rather than the same code twice. There is no MinGW
counterpart and there cannot be one; that was established by compiling rather
than by reading:

  * the header opens with "#include <Windows.h>", capital W, which does not
    resolve against mingw-w64's case-sensitive include directory;
  * "using t_load_library = HMODULE(WINAPI *)(__in LPCSTR file_name);" is a
    parse error under g++ - the SAL annotation is inside the parameter list of
    a function-pointer type alias.

Building it would need upstream source to be patched, which this corpus does
not do.

The exerciser has to stay a single translation unit. detail::murmur_hash2_a and
detail::parse_export_table are plain non-inline, non-static free functions in
the header, so a second translation unit that includes it is LNK2005 on both.
That is an upstream property and it is recorded here because it constrains any
future recipe over this project, not only this one.

Pinned by the annotated tag 2.0.0.0, which peels to
01fb7ffdd6c890cbdd2028ea98ba60a5ad37d1da and is also the repository HEAD, so
"the tag" and "current" are the same tree and there is no second version worth
covering.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# /Od, not the corpus default of /O2, and this is the one place in this recipe
# where the reference data deliberately does not describe what a release build
# of a consumer looks like.
#
# NEITHER LEVEL HAS BEEN MEASURED. MSVC does not exist in the container this
# recipe was written in, so both of the numbers below are reasoning about the
# code, not counts taken off an artefact, and nothing here should be read as
# though they were:
#
#   * Everything this library emits beyond two free functions is a template
#     instantiation, and most of it is win_api_import<T>::function_holder - a
#     two-pointer struct whose members are a constructor, a destructor, a move
#     constructor, a move assignment operator, cleanup(), operator() and
#     operator bool. At /O2 cl is expected to inline nearly all of that into
#     its callers. How much survives is exactly what has not been measured,
#     and the risk is that it lands under MIN_USEFUL_FUNCTIONS = 8.
#   * At /Od, which implies /Ob0, every called instantiation is emitted as its
#     own COMDAT. Twelve distinct T at roughly twelve functions each should be
#     about 145 functions - also an estimate.
#
# /Od is therefore the cautious choice rather than the demonstrated one: it is
# the level that cannot plausibly fall under the floor. The first CI run
# produces the real /Od count, and that is the point at which to decide
# whether /O2 would have cleared the floor after all and would be the better
# reference. Until then this recipe claims only that /Od is safe.
#
# The consequence either way, stated here and in the notes because it goes
# into provenance.json: this sample matches an unoptimised consumer of this
# header and will match an /O2 consumer of the same header much less well. The
# alternative was to lower a gate to let an /O2 build through, which this
# corpus does not do.
#
# /MD rather than cl's default: /LD implies /MT, and a static CRT put 1947 of
# VX-API's 4219 functions into that artefact as MSVC C runtime, duplicating
# data/MSVC. /EHsc because win_api_import<T>::get_function() wraps its body in
# try/catch. /std:c++17 for the structured binding in get_function() and for
# std::string_view. /I. because the header sits at the repository root and the
# exerciser includes it by name.
_COMPILE = ('cl /nologo /c /Od /MD /Zi /EHsc /std:c++17 /I. '
            '/Fdwinapi_obfuscator.compiler.pdb /Fowinapi_obfuscator.obj '
            '{repo}/scripts/corpus/exercisers/winapi_obfuscator.cpp')

# A DLL, not a .lib: SMDA cannot read a static library. The exerciser's entry
# point is already extern "C" __declspec(dllexport), so the image has a real
# export table without a .def file.
#
# kernel32.lib is named explicitly rather than left to the default library
# list, because function_holder::cleanup() calls FreeLibrary and
# get_modules() calls lstrcmpiW, and an unresolved external here would cost a
# CI round to discover.
#
# /Brepro drops the build timestamp, without which two runs over identical
# source record different sha256s. /OPT:NOREF keeps routines nothing
# references, which at /Od is most of what the exerciser instantiates, and
# /OPT:NOICF keeps apart the many instantiations that compile to identical
# bodies - function_holder over two pointer-shaped T is exactly that case, and
# folding cost VX-API its StringConcat/StringCopy pair.
#
# /INCREMENTAL:NO because /DEBUG implies /INCREMENTAL and the /OPT:NO* forms
# above do not suppress it - only /OPT:REF, /OPT:ICF and /OPT:ORDER are
# documented to. An incrementally linked image reaches each function through a
# table of one-instruction jump thunks and SMDA recovers every one as an
# unnamed function; smdaify.assert_not_incrementally_linked refuses a build
# with a run of more than MAX_INCREMENTAL_THUNK_RUN of them.
_LINK = ('link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO '
         '/OPT:NOREF /OPT:NOICF '
         '/PDB:winapi_obfuscator.pdb /OUT:winapi_obfuscator.dll '
         'winapi_obfuscator.obj kernel32.lib')


RECIPES = {
    "WinApiObfuscator_2.0.0.0_msvc": Recipe(
        family="WinApiObfuscator",
        version="2.0.0.0",
        upstream="https://github.com/SaulBerrenson/WinApiObfuscator",
        license="MIT",
        source=Source(
            git_url="https://github.com/SaulBerrenson/WinApiObfuscator.git",
            # The annotated tag, which peels to
            # 01fb7ffdd6c890cbdd2028ea98ba60a5ad37d1da and is HEAD.
            git_ref="2.0.0.0"),
        build=[BuildStep(_COMPILE), BuildStep(_LINK)],
        artifacts=[Artifact(path="winapi_obfuscator.dll",
                            component="winapi_obfuscator.dll",
                            pdb="winapi_obfuscator.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/Od /MD /Zi /EHsc /std:c++17; /DEBUG /Brepro "
                    "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF and kernel32.lib "
                    "at link. /Od rather than the corpus default /O2 as a "
                    "cautious choice, not a measured one: at /O2 cl is "
                    "expected to inline almost all of "
                    "win_api_import<T>::function_holder into its callers, and "
                    "how much would survive was not measured, so /Od was "
                    "taken as the level that cannot fall under the "
                    "eight-function floor. This sample therefore describes an "
                    "unoptimised consumer of the header.",
        notes="Built from an exerciser translation unit, since the project is "
              "a single header with no build system at all; the emitted "
              "functions are the library's own and the exerciser only selects "
              "which ones. It must stay one translation unit: "
              "detail::murmur_hash2_a and detail::parse_export_table are "
              "non-inline free functions in the header, so a second including "
              "translation unit is LNK2005 on both. MSVC only - the header "
              "spells its Windows include with a capital W and puts a SAL "
              "__in annotation inside a function-pointer type alias, neither "
              "of which survives mingw-w64, and this corpus does not patch "
              "upstream. Both architectures, because get_modules() reaches the "
              "PEB through __readgsqword(0x60) on x64 and __readfsdword(0x30) "
              "on x86 and the two legs are different code. Compiled at /Od as "
              "a cautious choice rather than a measured one - see build_flags "
              "- so read the sample as reference for an unoptimised consumer "
              "rather than for an /O2 one, and revisit the level once a run "
              "has produced a real function count. No "
              "dependencies beyond kernel32; built against the DLL runtime, so "
              "the MSVC C runtime is imported rather than linked in and stays "
              "attributed to data/MSVC.",
    ),
}
