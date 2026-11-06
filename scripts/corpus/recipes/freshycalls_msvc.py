"""FreshyCalls (crummie5), MSVC - the same exerciser, the other code generator.

The MSVC counterpart of freshycalls.py, built from the same
``exercisers/freshycalls.cpp`` so the two artefacts differ in the code
generator and nothing else. That is most of the signal for this project
rather than a refinement of it: it is C++ with ``std::map``,
``std::unordered_map`` and ``std::string_view`` throughout, and the README's
MSVC section is explicit that for C++ the gap between a MinGW and an MSVC
reference is name mangling, exception tables, vtable shapes and template
instantiation - that is, most of the binary.

Two of the three command-line workarounds the MinGW side needs do not apply
here: ``<intrin.h>`` is the branch syscall.hpp takes when ``__GNUC__`` is
undefined and it declares what it uses, and ``Windows.h`` resolves on a
case-insensitive filesystem.

The third one does apply, which was an assumption this docstring got wrong
until a Windows runner corrected it. UNICODE is *not* defined by default by
cl - it is defined by the project templates Visual Studio generates, and
this project has no project file - so ``utils.cpp`` passing a wide literal
to ``GetModuleHandle`` failed with
``utils.cpp(15): error C2664: 'HMODULE GetModuleHandleA(LPCSTR)': cannot
convert argument 1 from 'const wchar_t [10]' to 'LPCSTR'``. ``/DUNICODE
/D_UNICODE`` is therefore passed on both sides, for the same reason.

**x64 only**: syscall.hpp ``#error``s on anything that is not ``__x86_64``
or ``_M_AMD64``.

``/MD`` not ``/MT``, no ``/GL``, and ``/Zi`` with a declared PDB because
MSVC writes no COFF symbol table and the exerciser exports one function.
``/EHsc`` because the project throws. Nothing is run.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_EX = "{repo}/scripts/corpus/exercisers"
_STEPS = (
    BuildStep("cl /nologo /c /O2 /MD /Zi /EHsc /std:c++17 /DUNICODE /D_UNICODE /I. "
              "/Fdfc.pdb /Foexer.obj %s/freshycalls.cpp" % _EX),
    BuildStep("cl /nologo /c /O2 /MD /Zi /EHsc /std:c++17 /DUNICODE /D_UNICODE /I. "
              "/Fdfc.pdb /Fosyscall.obj syscall.cpp"),
    BuildStep("cl /nologo /c /O2 /MD /Zi /EHsc /std:c++17 /DUNICODE /D_UNICODE /I. "
              "/Fdfc.pdb /Foutils.obj utils.cpp"),
    BuildStep("link /nologo /DLL /DEBUG /Brepro /OPT:NOREF /OPT:NOICF "
              "/INCREMENTAL:NO /PDB:fc.pdb /OUT:freshycalls.dll "
              "exer.obj syscall.obj utils.obj"),
)


RECIPES = {
    "FreshyCalls_2022-09-01_msvc": Recipe(
        family="FreshyCalls",
        version="2022-09-01",
        upstream="https://github.com/crummie5/FreshyCalls",
        license="MPL-2.0",
        source=Source(git_url="https://github.com/crummie5/FreshyCalls.git",
                      git_ref="112bdf0db63a5f7104ba5243af6a672bc098a1ad"),
        build=list(_STEPS),
        artifacts=[Artifact(path="freshycalls.dll",
                            component="freshycalls.dll",
                            pdb="fc.pdb")],
        toolchains=["msvc_x64"],
        build_flags="cl /O2 /MD /Zi /EHsc /std:c++17 /DUNICODE /D_UNICODE, "
                    "linked /DLL /DEBUG "
                    "/Brepro /OPT:NOREF /OPT:NOICF /INCREMENTAL:NO",
        notes="Built from the same exerciser as the MinGW artefact, so the "
              "two differ in the code generator alone. The project has no "
              "build system of any kind, so this compile line is the "
              "recipe's; its callers are variadic templates and are "
              "instantiated by the exerciser at three arities each.",
    ),
}
