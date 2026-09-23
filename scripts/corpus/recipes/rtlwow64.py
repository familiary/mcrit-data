"""RtlWow64 - a WOW64-transition DLL with an Rtl-shaped API. MSVC only.

A 32-bit process on 64-bit Windows keeps a second, 64-bit ntdll mapped that
its own loader will not show it. RtlWow64 reaches that side and wraps it in
the shape of the native API: RtlGetModuleHandleWow64,
RtlGetProcAddressWow64, RtlLoadLibraryWow64, RtlLoadKernel32X64 and
RtlInvokeX64, backed by RtlpGetModuleHandleWow64 and
RtlpGetProcAddressWow64, which walk the 64-bit PEB loader list and parse the
x64 export directory by hand. Underneath them RtlpWow64Execute64 copies a
small "Heaven's Gate" thunk - the Wow64Execute byte array at
RtlWow64/RtlWow64.cpp:325 - into an executable heap and far-calls through
it. That is the sequence an analyst is looking for, and the reason this
project is worth a reference sample.

MSVC only, and not a preference. The sources use every Microsoft extension
at once, and each one alone is enough to stop GCC:

  * RtlWow64/RtlWow64.cpp:791 is "__asm int 3;", MSVC inline assembly.
  * RtlWow64/RtlWow64.cpp:21-24 is __try/__except with an exception filter,
    structured exception handling, which mingw's GCC does not implement.
  * RtlWow64/RtlNative.h declares its 64-bit structures with __ptr64
    pointer qualifiers throughout.
  * RtlWow64/RtlNative.h:21 is "#pragma comment(lib,\"ntdll.lib\")".

x86 only, and that is upstream's own conclusion: RtlWow64.sln maps only
Debug|x86 and Release|x86 onto the project's Win32 configurations, even
though RtlWow64.vcxproj carries x64 groups. It could not do otherwise. The
__asm above is rejected outright by a 64-bit MSVC front end, and the
NtWow64QueryInformationProcess64, NtWow64ReadVirtualMemory64 and
NtWow64WriteVirtualMemory64 that RtlNative.cpp resolves by name exist only in
the WOW64 ntdll - there is no gate to open from a native 64-bit process.

Upstream never tagged a release, so the pin is the full commit hash of
master as of 2021-02-12 and the version string is that date.

The project is built directly rather than through RtlWow64.sln. The solution
also carries test\\test.vcxproj, an executable that links against this DLL
and is no part of the reference data; building the one project keeps the
build to what is being collected.

No upstream file is modified. Four settings the project does not state, or
states in a way this corpus cannot use, arrive through an ItemDefinitionGroup
imported with ForceImportBeforeCppTargets - the mechanism blackbone.py
established here - and MSBuild imports it after the project's own groups, so
they win.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# RuntimeLibrary: Release|Win32 asks for MultiThreaded, i.e. /MT. That is the
# one compile setting this recipe overrides, for the reason cryptopp_msvc.py
# records - under /MT the MSVC C runtime is linked into the artefact and filed
# under this family, which is what put 1947 of VX-API's 4219 functions into
# that sample, duplicating data/MSVC. MultiThreadedDLL leaves it in
# ucrtbase.dll and vcruntime140.dll with only import thunks here.
#
# DebugInformationFormat: the Release|Win32 ClCompile group sets none, so
# whether the compiler emits debug info at all depends on an MSBuild default.
# MSVC keeps symbols in a PDB rather than in a COFF symbol table, so without
# one SMDA can name only the eleven functions m.def exports and smdaify
# rejects the build; build.py turns a declared-but-missing PDB into a hard
# failure, which is what makes this worth forcing rather than hoping for.
# GenerateDebugInformation is already true in the project and is left alone.
#
# /Brepro: without it MSVC stamps the PE with the build time, so two runs over
# identical source record different sha256s - which the BlackBone x86 DLL did
# between two green runs.
#
# /INCREMENTAL:NO: /DEBUG implies /INCREMENTAL, an incrementally linked image
# reaches every function through a table of one-instruction jump thunks, and
# SMDA recovers each of those as a function of its own - 2936 of
# nlohmann_json 3.12.0 x86's 5205, before
# smdaify.assert_not_incrementally_linked began refusing it. The project's
# own Release|Win32 PropertyGroup already sets LinkIncremental false and its
# OptimizeReferences would suppress it as well, so this is belt and braces
# on a sample small enough that a thunk table would be most of it.
_PROPS = (
    'python -c "'
    "open('corpus-msvc.props','w').write("
    "'<Project><ItemDefinitionGroup><ClCompile>'"
    "'<RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary>'"
    "'<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>'"
    "'</ClCompile><Link>'"
    "'<AdditionalOptions>/Brepro /INCREMENTAL:NO</AdditionalOptions>'"
    "'</Link></ItemDefinitionGroup></Project>')"
    '"')

# PlatformToolset has to be overridden: the project asks for v142, which the
# windows-2022 runner image does not carry - it ships VS2022 and v143 only.
# The same override blackbone.py needs, for the same reason.
#
# OutDir and IntDir are pinned rather than inherited. The project states
# neither, so both would come from the Microsoft.Cpp defaults, which for a
# Win32 target are written in terms of $(SolutionDir) - and this build does
# not go through a solution. Naming them puts the DLL and its linker PDB at a
# path this recipe can declare with no guesswork, and keeps the compiler PDB
# (IntDir\\vc143.pdb, by MSBuild's own default) in a different directory from
# the linker PDB, which is the separation nlohmann_msvc.py spells out.
_MSBUILD = ('msbuild RtlWow64\\RtlWow64.vcxproj '
            '/p:Configuration=Release /p:Platform={msbuild_platform} '
            '/p:PlatformToolset=v143 '
            '/p:OutDir=%CD%\\out\\ /p:IntDir=%CD%\\obj\\ '
            '/p:ForceImportBeforeCppTargets=%CD%\\corpus-msvc.props '
            '/m /v:minimal')

_FLAGS = ("Release|Win32 as upstream defines it: /Gy /Oi /sdl /W3 "
          "/permissive- (ConformanceMode), WIN32, NDEBUG, RTLWOW64_EXPORTS, "
          "_WINDOWS and _USRDLL defined, WholeProgramOptimization (/GL, and "
          "/LTCG at link), and /OPT:REF /OPT:ICF at link; the project states "
          "no Optimization element for this configuration, so no /O switch "
          "is passed. Exports come from RtlWow64\\m.def. /MD replaces "
          "upstream's /MT, /Zi replaces its unstated debug format, and "
          "/Brepro /INCREMENTAL:NO are appended at link, all by this recipe; "
          "the toolset is retargeted from v142 to v143.")


RECIPES = {
    "RtlWow64_2021-02-12": Recipe(
        family="RtlWow64",
        version="2021-02-12",
        upstream="https://github.com/bb107/RtlWow64",
        # LICENSE is the full Apache 2.0 text and every source file carries
        # the "Copyright 2020 Boring" Apache header.
        license="Apache-2.0",
        source=Source(git_url="https://github.com/bb107/RtlWow64.git",
                      git_ref="a7b5d0bef14db397e722ec2558db1169c1f14bb4"),
        build=[
            BuildStep(_PROPS),
            BuildStep(_MSBUILD),
            # build.py reports a missing artefact by the path it expected and
            # nothing else; this puts what the build actually wrote into the
            # log the workflow prints on failure, as q3vm_msvc.py does.
            BuildStep("dir out", allow_failure=True),
        ],
        artifacts=[Artifact(path="out\\RtlWow64.dll", component="RtlWow64.dll",
                            pdb="out\\RtlWow64.pdb")],
        # x86 only; see the module docstring. SysWhispers declares one
        # architecture in the other direction and needs no special case.
        toolchains=["msvc_x86"],
        build_flags=_FLAGS,
        notes="A small sample by design. The project is three translation "
              "units holding eighteen functions of its own - thirteen in "
              "RtlWow64.cpp, the three NtWow64* forwarders in RtlNative.cpp "
              "and RtlpInitialize plus DllMain in dllmain.cpp - of which "
              "RtlWow64\\m.def exports eleven, so the artefact clears "
              "config.MIN_USEFUL_FUNCTIONS on the exports alone whatever "
              "upstream's /OPT:REF and /OPT:ICF decide about the rest. "
              "Folding is left on because it is upstream's own Release "
              "setting, the same call blackbone.py makes, and there is "
              "little for it to fold: the closest pair, "
              "RtlGetModuleHandleWow64 and RtlLoadLibraryWow64, have the "
              "same shape but load different globals (LdrGetDllHandle "
              "against LdrLoadDll) and call different string initialisers, "
              "so their bodies are not identical. Built against the DLL "
              "runtime, so the MSVC C "
              "runtime is imported rather than linked in and stays "
              "attributed to data/MSVC. No dependencies: the project links "
              "only ntdll.lib, through a #pragma comment in RtlNative.h, and "
              "the Windows import libraries. The test executable in the "
              "solution is not built.",
    ),
}
