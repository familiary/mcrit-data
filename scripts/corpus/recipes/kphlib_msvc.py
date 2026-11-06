"""Process Hacker v2.39 kph.c client, with only link-reached phlib support.

Initial Windows probe. Open risks: legacy headers versus WDK 10.0.26100;
old project assumptions; link/PDB paths; kernel glue surviving the user-mode
baseline. No upstream source is patched. Driver images are never packaged,
signed, installed or loaded; all output is for disassembly only.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_PROPS = 'python -c "open(\'corpus-um.props\',\'w\').write(\'<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003"><PropertyGroup><WholeProgramOptimization>false</WholeProgramOptimization><LinkIncremental>false</LinkIncremental><IntDir>$(OutDir)obj\\\\$(ProjectName)\\\\</IntDir></PropertyGroup><ItemDefinitionGroup><ClCompile><RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary><Optimization>MaxSpeed</Optimization><WholeProgramOptimization>false</WholeProgramOptimization><DebugInformationFormat>ProgramDatabase</DebugInformationFormat><ProgramDataBaseFileName>$(IntDir)$(ProjectName).compiler.pdb</ProgramDataBaseFileName><TreatWarningAsError>false</TreatWarningAsError><AdditionalOptions>/GL- %(AdditionalOptions)</AdditionalOptions></ClCompile><Link><GenerateDebugInformation>true</GenerateDebugInformation><OptimizeReferences>false</OptimizeReferences><EnableCOMDATFolding>false</EnableCOMDATFolding><LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration><ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile><AdditionalOptions>/Brepro /INCREMENTAL:NO %(AdditionalOptions)</AdditionalOptions></Link><Lib><LinkTimeCodeGeneration>false</LinkTimeCodeGeneration></Lib></ItemDefinitionGroup></Project>\')"'

RECIPES = {
 "kphlib_2.39_msvc": Recipe(
  family="kphlib", version="2.39", source=Source(git_url="https://github.com/processhacker/processhacker.git", git_ref="4310de8c43f7600e344b789ffabad79b79878f6a"),
  upstream="https://github.com/processhacker/processhacker/tree/v2.39", license="GPL-3.0-or-later (source headers)", toolchains=["msvc_x86", "msvc_x64"],
  build=[BuildStep("python -m pip install --quiet smda==5.0.2 mcrit==1.16.0"), BuildStep(_PROPS),
   BuildStep('msbuild phlib\\phlib.vcxproj /p:Configuration=Release /p:Platform={msbuild_platform} /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0 /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:TargetName=phlib /p:WholeProgramOptimization=false /p:ForceImportBeforeCppTargets=%CD%\\corpus-um.props /m /v:normal'),
   BuildStep('cl /nologo /c /O2 /MD /Zi /Gz /D_PHLIB_ /DUNICODE /D_UNICODE /DNDEBUG /Iphlib\\include /Iphnt\\include phlib\\kph.c /Foout\\kph.obj'),
   BuildStep('link /DLL /NOENTRY /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO /OUT:out\\kphlib.dll /PDB:out\\kphlib.pdb out\\kph.obj out\\phlib.lib ntdll.lib kernel32.lib advapi32.lib user32.lib gdi32.lib comctl32.lib shell32.lib shlwapi.lib ole32.lib oleaut32.lib uuid.lib version.lib winmm.lib crypt32.lib wintrust.lib uxtheme.lib psapi.lib setupapi.lib netapi32.lib ws2_32.lib iphlpapi.lib'), BuildStep("dir /s out", allow_failure=True)],
  artifacts=[Artifact(path="out/kphlib.dll", component="kphlib.dll", pdb="out/kphlib.pdb")],
  build_flags="v2.39 Release /O2 /MD /Zi /Gz /GL-; direct kph.obj + archive-selected phlib support; /DLL /NOENTRY /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO",
  notes="The reusable kph.c client is linked directly, and only phlib archive objects it reaches are pulled in; phlib is not whole-archived. No ProcessHacker GUI executable is built. Necessary Ph support functions are recorded as part of this client image. No driver interaction is exercised; linked and disassembled only.",
 ),
}
