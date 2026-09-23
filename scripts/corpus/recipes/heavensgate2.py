"""Heaven's Gate 2.0 (dadas190) - MSVC only, x86 only.

A fourth WOW64-transition family beside wow64pp, wowGrail and RtlWow64, and
a deliberately different one. wow64pp reaches the 64-bit side through
NtWow64QueryInformationProcess64 and a compiled stub; this one keeps every
64-bit sequence as a ``char inst[]`` byte array, VirtualAllocs an RWX page,
patches the immediates into it at run time and calls it. So the far-call to
selector 0x33 is not in the image as code at all - it is data, and the code
around it is the patcher. That is the shape an analyst meets when this
header has been copied into something, and it is what makes the sample worth
having beside the other three.

It is also the only one of the five Heaven's Gate repositories surveyed for
the wishlist issue that contains no MSVC-only assembly syntax: no .asm file,
no __asm block, no __declspec(naked). It is nevertheless built with MSVC
only, for the reason vxapi.py gives - the single build system the repository
ships is an MSVC solution, and a GCC rendering of a 2017 Visual Studio proof
of concept would be a code shape nobody runs.

x86 only, and upstream agrees twice over. The solution's single
SolutionConfigurationPlatform is ``Release|x86`` and the project's single
ProjectConfiguration is ``Release|Win32``; the Debug and x64
PropertyGroups/ItemDefinitionGroups in HeavensGate.vcxproj are orphans that
no configuration selects. And the code could not be built 64-bit anyway -
HeavensGate.h casts 64-bit pointers down with ``(uint32_t)(peb)`` and
``(uint64_t)(unsigned)(&ptr)`` in roughly twenty places, which is a hard
error on an x64 target rather than a warning. A library that opens a gate
from 32-bit to 64-bit code has nothing to do on x64 in any case.

Eleven functions: the ten in HeavensGate.h - memcpy64, GetPEB64,
GetModuleLDREntry, GetModuleHandle64, X64Call, MyGetProcAddress, MakeUTFStr,
GetKernel32, GetProcAddress64, LoadLibrary64 - plus Source.cpp's main. That
clears config.MIN_USEFUL_FUNCTIONS (8) by three, which is thin enough to be
worth stating: the whole project is one header and one 15-line example, and
nothing can be added without writing code upstream does not have. All eleven
survive because upstream's own Release configuration sets Optimization
Disabled and InlineFunctionExpansion Disabled, and because all ten are
reachable from main by a chain this recipe checked by hand
(main -> LoadLibrary64/GetProcAddress64 -> GetKernel32 -> MakeUTFStr,
MyGetProcAddress, X64Call; main -> GetModuleHandle64 -> GetModuleLDREntry ->
GetPEB64 -> memcpy64). /OPT:REF is nevertheless turned off below rather than
relied upon, because a dropped function here is a refused build.

Read the header, not the README. README.md documents a ``MakeANSIStr`` that
does not exist in the tree, gives MakeUTFStr the signature
``uint64_t MakeUTFStr(char *in)`` where the header has
``void MakeUTFStr(char *str, char *out)``, and describes X64Call as taking
four fixed arguments where the header is variadic
``X64Call(uint64_t proc, unsigned n, ...)``.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Five settings are forced through a props file imported with
# ForceImportBeforeCppTargets, the technique blackbone.py, q3vm_msvc.py and
# wowgrail.py use, so that no upstream file is modified.
#
# GenerateDebugInformation: the project asks for DebugFastLink, i.e.
# /DEBUG:FASTLINK, which leaves the debug information in the .obj files and
# writes a PDB that merely indexes them. That PDB is only meaningful next to
# the object files that produced it, and MSVC keeps symbols in a PDB rather
# than in a COFF symbol table, so a report read with it would name almost
# nothing. Replaced with a full /DEBUG, and DebugInformationFormat stated as
# ProgramDatabase rather than left to the toolset's default.
#
# OptimizeReferences and EnableCOMDATFolding: the project turns both on, i.e.
# /OPT:REF /OPT:ICF. With eleven functions and a floor of eight, folding two
# together or discarding one is the difference between a sample and a refused
# build, so both are turned off here - the same reason vxapi.py passes
# /OPT:NOICF, where folding cost it its StringConcat/StringCopy pair.
#
# /INCREMENTAL:NO: the Release PropertyGroup already sets LinkIncremental
# false, but /DEBUG implies /INCREMENTAL and the /OPT:NO* forms above do not
# suppress it, so it is stated on the link line as well rather than inherited
# from a property this recipe also overrides other parts of. An incremental
# link would put a table of one-instruction jump thunks in front of every
# function and smdaify.assert_not_incrementally_linked refuses that.
#
# /Brepro: without it MSVC stamps the PE with the build time and two runs
# over identical source record different sha256s.
#
# AdditionalDependencies: kernel32.lib, named rather than inherited. The
# project sets IgnoreAllDefaultLibraries, so the /DEFAULTLIB directives the
# objects carry are ignored and only libraries on the link line are used;
# what the code actually references outside itself is VirtualAlloc,
# lstrcmpiW, lstrcmpA and lstrlenA, all four of them kernel32. Relying on
# MSBuild's default list for that would make the link depend on a toolset
# default this recipe cannot check without MSVC.
_PROPS = (
    'python -c "'
    "open('corpus-msvc.props','w').write("
    "'<Project><ItemDefinitionGroup><ClCompile>'"
    "'<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>'"
    "'</ClCompile><Link>'"
    "'<GenerateDebugInformation>true</GenerateDebugInformation>'"
    "'<OptimizeReferences>false</OptimizeReferences>'"
    "'<EnableCOMDATFolding>false</EnableCOMDATFolding>'"
    "'<AdditionalDependencies>kernel32.lib</AdditionalDependencies>'"
    "'<AdditionalOptions>/Brepro /INCREMENTAL:NO</AdditionalOptions>'"
    "'</Link></ItemDefinitionGroup></Project>')"
    '"')

# The solution is built rather than the project, so MSBuild sets SolutionDir
# itself instead of this recipe passing it as blackbone.py has to. Its one
# solution platform is x86, which it maps to the project's Win32 - hence
# /p:Platform=x86 and not Win32, and hardcoded rather than {arch} because
# there is no other leg.
#
# PlatformToolset v140 and WindowsTargetPlatformVersion 8.1 are what the
# project asks for and neither is on the windows-2022 runner image, which
# ships VS2022 and v143 only; WindowsTargetPlatformVersion=10.0 asks MSBuild
# for the newest Windows 10/11 SDK installed.
#
# OutDir and IntDir are pinned rather than inherited, as wowgrail.py pins
# them and for the same two reasons: the Microsoft.Cpp defaults are written
# in terms of $(SolutionDir) and differ between a Win32 and an x64 target, so
# naming them gives this recipe a path to declare with no guesswork; and it
# keeps the compiler PDB (IntDir\\vc143.pdb, by MSBuild's own default) in a
# different directory from the linker PDB, which have to be separate files.
_MSBUILD = ('msbuild HeavensGate.sln '
            '/p:Configuration=Release /p:Platform=x86 '
            '/p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0 '
            '/p:OutDir=%CD%\\out\\ /p:IntDir=%CD%\\obj\\ '
            '/p:ForceImportBeforeCppTargets=%CD%\\corpus-msvc.props '
            '/m /v:minimal')

# Everything up to the semicolon is read out of HeavensGate.vcxproj's
# Release|Win32 ItemDefinitionGroups.
_FLAGS = ("Release|Win32: Optimization Disabled and InlineFunctionExpansion "
          "Disabled, IntrinsicFunctions off, /Gy /Oy /GS- /Gd, "
          "EnableEnhancedInstructionSet NoExtensions, exception handling and "
          "control-flow guard off, /MT, compiled as C (CompileAs "
          "CompileAsC), WIN32;NDEBUG;_CONSOLE, and at link "
          "IgnoreAllDefaultLibraries with EntryPointSymbol main and "
          "SubSystem Console; this recipe retargets v140 to v143 and the 8.1 "
          "SDK to 10.0, replaces DebugFastLink with /Zi and a full /DEBUG, "
          "turns /OPT:REF and /OPT:ICF off, and adds /Brepro "
          "/INCREMENTAL:NO and kernel32.lib")


RECIPES = {
    # No tags; upstream has never released. The pin is the full commit hash
    # of master as of 2017-07-23 and the version string is that date, the
    # same convention wow64pp.py uses.
    "HeavensGate2_2017-07-23": Recipe(
        family="HeavensGate2",
        version="2017-07-23",
        upstream="https://github.com/dadas190/Heavens-Gate-2.0",
        # No LICENSE, COPYING or licence header anywhere in the repository -
        # git ls-files is seven files and a grep for licence or copyright
        # across all of them returns nothing. The only statement of
        # authorship is the comment at HeavensGate.h:1-4, recorded in the
        # notes. "none" is the fact, not a guess, and this field is copied
        # verbatim into provenance.json.
        license="none",
        source=Source(git_url="https://github.com/dadas190/Heavens-Gate-2.0.git",
                      git_ref="bd8a9b08384cdde229eb616789ba921ba2b271c4"),
        build=[
            BuildStep(_PROPS),
            BuildStep(_MSBUILD),
            # build.py reports a missing artefact by the path it expected and
            # nothing else; this puts what the build actually wrote into the
            # log the workflow prints on failure.
            BuildStep("dir out", allow_failure=True),
        ],
        artifacts=[
            Artifact(path="out\\HeavensGate.exe", component="HeavensGate.exe",
                     pdb="out\\HeavensGate.pdb"),
        ],
        # x86 only; see the module docstring. SysWhispers declares only its
        # x64 leg in the same way and needs no special case anywhere.
        toolchains=["msvc_x86"],
        build_flags=_FLAGS,
        # There is no C runtime in this image to mistake for the project's
        # code: the project links IgnoreAllDefaultLibraries with
        # EntryPointSymbol main, so nothing of the CRT - not even its startup
        # - is present, and the imports are the four kernel32 entries the
        # header calls. Running the glue filter over it would have nothing to
        # match and could only cost functions from a sample that has eleven.
        drop_crt_glue=False,
        notes="No licence of any kind: the repository carries no LICENSE or "
              "COPYING file and no per-file notice, and the only statement "
              "of authorship is the comment at the top of HeavensGate.h, "
              "\"Made by David Cernak - Dadas1337\". x86 only - the "
              "solution's single platform is x86, mapped to the project's "
              "only configuration Release|Win32, and the header truncates "
              "64-bit pointers to 32 bits in roughly twenty places, which "
              "does not compile on x64. Eleven functions, against a floor of "
              "eight: the project is one header of ten functions and a "
              "fifteen-line example, and upstream's own Release settings "
              "(Optimization Disabled, InlineFunctionExpansion Disabled) are "
              "what keeps all of them separate. Source.cpp is compiled as C, "
              "not C++, which is upstream's CompileAs setting. No C runtime "
              "is linked at all - IgnoreAllDefaultLibraries with "
              "EntryPointSymbol main - so the image is the eleven functions "
              "and a kernel32 import table and nothing else. None of the "
              "64-bit code is assembled: it is byte arrays in the data of "
              "memcpy64, GetPEB64 and X64Call, copied to an RWX page and "
              "patched with the call's operands before each use, so the gate "
              "itself is data in this artefact and the surrounding code is "
              "the patcher - which also makes this the one repository of the "
              "five surveyed for the wishlist issue that carries no .asm "
              "file, no __asm block and no __declspec(naked). README.md is "
              "stale "
              "and contradicts the header on three of the ten functions; the "
              "header is what was built.",
    ),
}
