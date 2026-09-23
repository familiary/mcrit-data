"""wowGrail - HITB 2021 Heaven's Gate process hollowing. MSVC only.

aaaddress1's proof of concept for the HITB 2021 talk "Rebuild The Heaven's
Gate": instead of carrying its own 64-bit syscall stubs, it locates
wow64!Wow64SystemServiceEx by walking the 64-bit loader list to wow64.dll and
parsing its export directory from 32-bit code, then JITs a five-instruction
trampoline that enters 64-bit mode, calls through that pointer and returns.
On top of that it runs a RunPE: CreateProcessA suspended, then
NtWriteVirtualMemory, NtSetContextThread and NtResumeThread issued through
the trampoline rather than through the 32-bit ntdll an EDR has hooked. The
recognisable parts are the far-call byte arrays - the memcpy64 thunk built
out of a string literal at wowGrail/wowGrail.cpp:14 and the stub_template at
:155 - and the export-directory walk that finds the translator.

MSVC only. wowGrail.cpp:14 writes "(void(cdecl*)(ULONG64, ULONG64, ULONG64))"
with the bare, un-underscored "cdecl" keyword, a Microsoft extension GCC does
not have at all; :141 calls stricmp under its MSVC spelling; and the whole
memcpy64 idea is to execute a string literal, which lives in .rdata and needs
the /NXCOMPAT:NO that the project's own DataExecutionPrevention false asks
for.

x86 only, and structurally so. wowGrail.cpp:230 reads CTX->Ebx and :233
assigns CTX->Eax; the 64-bit CONTEXT has no Ebx or Eax member, so the x64
configurations the project file carries cannot compile this source. Nor
should they: a 64-bit process has no gate to open.

There is no solution file in the repository, so msbuild is pointed at
wowGrail\\wowGrail.vcxproj directly.

Release|Win32, not Debug, and not because Release is the default choice.
Upstream's README is emphatic - "**HIGHLY RECOMMEND** Compile It in Release
mode, if you're using MSVC toolchain. Due to MSVC's performance
instrumentation in Debug mode, there'll be an unexpected memory layout" - and
the configuration is tuned for it rather than merely faster: Release|Win32
sets Optimization Disabled and InlineFunctionExpansion OnlyExplicitInline so
the layout stays predictable, BufferSecurityCheck false so no stack cookie is
inserted around the JIT buffers, and DataExecutionPrevention false so the
string-literal thunks are executable. Those four are exactly what the
technique depends on, and none of them is touched here.

Upstream never tagged a release, so the pin is the full commit hash of
master as of 2021-05-27 and the version string is that date.

The artefact is never executed. wowGrail.cpp:113 opens
"C:/Windows/SysWoW64/ntdll.dll", :193 hardcodes
"C:\\Windows\\SysWOW64\\calc.exe" and main() maps a "picaball.exe" that is
not in the repository. It is disassembled and nothing else.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# RuntimeLibrary: Release|Win32 asks for MultiThreaded, i.e. /MT, and that is
# the one compile setting this recipe overrides. Under /MT the MSVC C runtime
# is linked into the artefact and filed under this family - what put 1947 of
# VX-API's 4219 functions into that sample, duplicating data/MSVC - and this
# is a console C++ executable using std::string, std::wstring and printf, so
# a static CRT would be most of the image. MultiThreadedDLL leaves it in
# ucrtbase.dll and vcruntime140.dll. cryptopp_msvc.py and q3vm_msvc.py make
# the same call. The four settings the technique depends on - Optimization,
# InlineFunctionExpansion, BufferSecurityCheck, DataExecutionPrevention - are
# not among them and stay exactly as upstream sets them.
#
# DebugInformationFormat: the Release|Win32 ClCompile group sets none, so
# whether the compiler emits debug info depends on an MSBuild default. MSVC
# keeps symbols in a PDB rather than in a COFF symbol table, so without one
# SMDA recovers anonymous functions - and this executable exports nothing, so
# there would not even be an export table to fall back on. The project's
# GenerateDebugInformation is already true and is left alone.
#
# /Brepro: without it MSVC stamps the PE with the build time and two runs over
# identical source record different sha256s, as the BlackBone x86 DLL did.
#
# /INCREMENTAL:NO: /DEBUG implies /INCREMENTAL, and an incrementally linked
# image reaches every function through a table of one-instruction jump thunks
# that SMDA recovers as functions in their own right - 2936 of nlohmann_json
# 3.12.0 x86's 5205, before smdaify.assert_not_incrementally_linked began
# refusing such a build. The project's Release|Win32 PropertyGroup already
# sets LinkIncremental false; this states it where nothing can override it,
# on a sample of roughly ten own functions where a thunk table would dwarf
# the subject.
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
#
# OutDir and IntDir are pinned rather than inherited. The project states
# neither and there is no solution, so both would come from the
# Microsoft.Cpp defaults, which for a Win32 target are written in terms of
# $(SolutionDir). Naming them puts the executable and its linker PDB at a
# path this recipe can declare with no guesswork, and keeps the compiler PDB
# (IntDir\\vc143.pdb, by MSBuild's own default) in a different directory from
# the linker PDB - the separation nlohmann_msvc.py spells out.
_MSBUILD = ('msbuild wowGrail\\wowGrail.vcxproj '
            '/p:Configuration=Release /p:Platform={msbuild_platform} '
            '/p:PlatformToolset=v143 '
            '/p:OutDir=%CD%\\out\\ /p:IntDir=%CD%\\obj\\ '
            '/p:ForceImportBeforeCppTargets=%CD%\\corpus-msvc.props '
            '/m /v:minimal')

_FLAGS = ("Release|Win32 as upstream defines it: /Od (Optimization "
          "Disabled), /Ob1 (InlineFunctionExpansion OnlyExplicitInline), "
          "/GS- (BufferSecurityCheck false), /Oi- (IntrinsicFunctions "
          "false), /Gy /sdl /W3 /permissive- "
          "(ConformanceMode), Unicode character set, WIN32, NDEBUG and "
          "_CONSOLE defined, WholeProgramOptimization off; at link Console "
          "subsystem, /OPT:REF /OPT:ICF and /NXCOMPAT:NO "
          "(DataExecutionPrevention false). /MD replaces upstream's /MT, /Zi "
          "replaces its unstated debug format, and /Brepro /INCREMENTAL:NO "
          "are appended at link, all by this recipe; the toolset is "
          "retargeted from v142 to v143.")


RECIPES = {
    "wowGrail_2021-05-27": Recipe(
        family="wowGrail",
        version="2021-05-27",
        upstream="https://github.com/aaaddress1/wowGrail",
        # LICENSE is the full GPL 3.0 text with no "or later" wording, and
        # wowGrail/wow64ext.h is ReWolf's wow64ext header carried into the
        # tree under its own, different terms - its banner says LGPL "version
        # 3 of the License, or (at your option) any later version". Both are
        # recorded, the way sevenzip.py records the unRAR and LZFSE terms
        # alongside 7-Zip's own.
        license="GPL-3.0; wowGrail/wow64ext.h LGPL-3.0-or-later "
                "(vendored ReWolf wow64ext header)",
        source=Source(git_url="https://github.com/aaaddress1/wowGrail.git",
                      git_ref="b6b9a1e4afd9c9d8e1a28edc700c452dadfa8a10"),
        build=[
            BuildStep(_PROPS),
            BuildStep(_MSBUILD),
            # build.py reports a missing artefact by the path it expected and
            # nothing else; this puts what the build actually wrote into the
            # log the workflow prints on failure, as q3vm_msvc.py does.
            BuildStep("dir out", allow_failure=True),
        ],
        artifacts=[Artifact(path="out\\wowGrail.exe", component="wowGrail.exe",
                            pdb="out\\wowGrail.pdb")],
        # x86 only; see the module docstring.
        toolchains=["msvc_x86"],
        build_flags=_FLAGS,
        notes="A small sample: one translation unit with ten functions of "
              "its own - getPtr_Peb64, get64b_CSTR, get64b_WSTR, "
              "getPtr_Module64, getPtr_Wow64SystemServiceEx, "
              "getBytecodeOfNtAPI, NtAPI, RunPortableExecutable, "
              "MapFileToMemory and main - plus the std::string and "
              "std::wstring instantiations they force and the initialiser "
              "for the memcpy64 thunk. The vendored ReWolf header is in the "
              "tree but not in the artefact: wowGrail.cpp uses only its "
              "PEB64, PEB_LDR_DATA64 and LDR_DATA_TABLE_ENTRY64 typedefs and "
              "calls none of the twelve wow64ext functions it declares, so "
              "there is no wow64ext code here to misattribute and no "
              "unresolved external either - the declarations are dllimport "
              "and nothing references them. Built against the DLL runtime, "
              "so the MSVC C runtime is imported rather than linked in and "
              "stays attributed to data/MSVC. The binary must not be run: it "
              "opens hardcoded paths under C:\\Windows\\SysWOW64 and maps a "
              "picaball.exe that upstream does not ship. It is reference "
              "data, not a tool.",
    ),
}
