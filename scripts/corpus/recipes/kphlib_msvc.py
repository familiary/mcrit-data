"""Process Hacker v2.39 kph.c client, with only link-reached phlib support.

Pinned to upstream v2.39 (commit 4310de8c43f7600e344b789ffabad79b79878f6a).
No upstream source is patched. The link line is retried with the static UCRT
and the float-rounding legacy library added, one at a time, with ``||``, so
the build log records each attempt.

Open risks, in the order they bite:
1. phlib\\format.obj references __acrt_fp_format, which the import library
   ucrt.lib does not export. A static-UCRT library or a legacy float helper may
   supply it. If neither does, the link error text is the open finding.
2. kph.c is compiled as a plain object and the phlib archive is pulled by
   reference, so only reached support code enters the image.

No driver interaction is exercised; the DLL is linked and disassembled only.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_PROPS = 'python -c "open(\'corpus-um.props\',\'w\').write(\'<Project><PropertyGroup><WholeProgramOptimization>false</WholeProgramOptimization><LinkIncremental>false</LinkIncremental><IntDir>$(OutDir)obj\\\\$(ProjectName)\\\\</IntDir></PropertyGroup><ItemDefinitionGroup><ClCompile><RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary><Optimization>MaxSpeed</Optimization><WholeProgramOptimization>false</WholeProgramOptimization><DebugInformationFormat>ProgramDatabase</DebugInformationFormat><ProgramDataBaseFileName>$(IntDir)$(ProjectName).compiler.pdb</ProgramDataBaseFileName><TreatWarningAsError>false</TreatWarningAsError><AdditionalOptions>/GL- %(AdditionalOptions)</AdditionalOptions></ClCompile><Link><GenerateDebugInformation>true</GenerateDebugInformation><OptimizeReferences>false</OptimizeReferences><EnableCOMDATFolding>false</EnableCOMDATFolding><LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration><ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile><AdditionalOptions>/Brepro /INCREMENTAL:NO %(AdditionalOptions)</AdditionalOptions></Link><Lib><LinkTimeCodeGeneration>false</LinkTimeCodeGeneration></Lib></ItemDefinitionGroup></Project>\')"'

LINK_BASE = r'/DLL /NOENTRY /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO /OUT:out\kphlib.dll /PDB:out\kphlib.pdb out\kph.obj out\phlib.lib ntdll.lib kernel32.lib advapi32.lib user32.lib gdi32.lib comctl32.lib shell32.lib shlwapi.lib ole32.lib oleaut32.lib uuid.lib version.lib winmm.lib crypt32.lib wintrust.lib uxtheme.lib psapi.lib setupapi.lib netapi32.lib ws2_32.lib iphlpapi.lib comdlg32.lib ucrt.lib vcruntime.lib msvcrt.lib msvcprt.lib legacy_stdio_definitions.lib'
_LINK = 'link %s'
_LINK_ATTEMPTS = ' || '.join([
    _LINK % (LINK_BASE + ' libucrt.lib'),
    _LINK % (LINK_BASE + ' legacy_stdio_float_rounding.lib'),
    _LINK % (LINK_BASE + ' libucrt.lib legacy_stdio_float_rounding.lib'),
])

RECIPES = {
 "kphlib_2.39_msvc": Recipe(
  family="kphlib", version="2.39", source=Source(git_url="https://github.com/processhacker/processhacker.git", git_ref="4310de8c43f7600e344b789ffabad79b79878f6a"),
  upstream="https://github.com/processhacker/processhacker/tree/v2.39", license="GPL-3.0-or-later (source headers)", toolchains=["msvc_x86", "msvc_x64"],
  build=[BuildStep(_PROPS),
   BuildStep(r'msbuild phlib\phlib.vcxproj /p:Configuration=Release /p:Platform={msbuild_platform} /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0 /p:SolutionDir=%CD%\ /p:OutDir=%CD%\out\ /p:TargetName=phlib /p:WholeProgramOptimization=false /p:ForceImportBeforeCppTargets=%CD%\corpus-um.props /m /v:normal'),
   BuildStep(r'cl /nologo /c /O2 /MD /Zi /Gz /D_PHLIB_ /DUNICODE /D_UNICODE /DNDEBUG /Iphlib\include /Iphnt\include phlib\kph.c /Foout\kph.obj'),
   BuildStep(_LINK_ATTEMPTS), BuildStep("dir /s out", allow_failure=True)],
  artifacts=[Artifact(path="out/kphlib.dll", component="kphlib.dll", pdb="out/kphlib.pdb")],
  build_flags="v2.39 Release /O2 /MD /Zi /Gz /GL-; direct kph.obj + archive-selected phlib support; /DLL /NOENTRY /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO; link retried with libucrt.lib and/or legacy_stdio_float_rounding.lib",
  notes="The reusable kph.c client is linked directly, and only phlib archive objects it reaches are pulled in; phlib is not whole-archived. No ProcessHacker GUI executable is built. Necessary Ph support functions are recorded as part of this client image. No driver interaction is exercised; linked and disassembled only.",
 ),
}
