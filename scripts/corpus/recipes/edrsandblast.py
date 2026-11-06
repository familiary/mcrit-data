"""EDRSandblast reusable core and static API, built as an x64 DLL.

CI measurement, SMDA 4.8.0/MCRIT 1.9.0: 378 kept + 89 removed = 467 image functions; 240 have >=10 instructions with 227 unique PicHashes. The x64 reference complements its MinGW-free upstream MSVC build. Runtime printf/wprintf wrapper survives at 0x01b000030f8b5bfc. Vendored SysWhispers2 stubs are included as shipped. DLL is linked and disassembled only.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_PROPS = 'python -c "open(\'corpus-msvc.props\',\'w\').write(\'<Project><PropertyGroup><WholeProgramOptimization>false</WholeProgramOptimization><LinkIncremental>false</LinkIncremental><IntDir>$(OutDir)obj\\\\$(ProjectName)\\\\</IntDir></PropertyGroup><ItemDefinitionGroup><ClCompile><RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary><Optimization>MaxSpeed</Optimization><WholeProgramOptimization>false</WholeProgramOptimization><DebugInformationFormat>ProgramDatabase</DebugInformationFormat><ProgramDataBaseFileName>$(IntDir)$(ProjectName).compiler.pdb</ProgramDataBaseFileName><TreatWarningAsError>false</TreatWarningAsError><AdditionalOptions>/GL- %(AdditionalOptions)</AdditionalOptions></ClCompile><Link><GenerateDebugInformation>true</GenerateDebugInformation><OptimizeReferences>false</OptimizeReferences><EnableCOMDATFolding>false</EnableCOMDATFolding><LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration><ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile><AdditionalOptions>/Brepro /INCREMENTAL:NO %(AdditionalOptions)</AdditionalOptions></Link><Lib><LinkTimeCodeGeneration>false</LinkTimeCodeGeneration></Lib></ItemDefinitionGroup></Project>\')"'

RECIPES = {
 "EDRSandblast_2024-08-30_msvc": Recipe(
  family="EDRSandblast", version="2024-08-30",
  source=Source(git_url="https://github.com/wavestone-cdt/EDRSandblast.git", git_ref="0710fad92dbcdf373ed30c536b99012fcd46dbcc"),
  upstream="https://github.com/wavestone-cdt/EDRSandblast", license="CC-BY-4.0 (README); vendored SysWhispers2 stubs",
  toolchains=["msvc_x64"],
  build=[BuildStep(_PROPS),
   BuildStep('msbuild EDRSandblast\\EDRSandblast.vcxproj /p:Configuration=Release /p:Platform=x64 /p:PlatformToolset=v143 /p:TargetName=EDRSandblast_Core /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false /p:ForceImportBeforeCppTargets=%CD%\\corpus-msvc.props /m /v:normal'),
   BuildStep('msbuild EDRSandblast_StaticLibrary\\EDRSandblast_StaticLibrary.vcxproj /p:Configuration=Release /p:Platform=x64 /p:PlatformToolset=v143 /p:TargetName=EDRSandblast_API /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false /p:ForceImportBeforeCppTargets=%CD%\\corpus-msvc.props /m /v:normal'),
   BuildStep('link /DLL /NOENTRY /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO /OUT:out\\EDRSandblast.dll /PDB:out\\EDRSandblast.pdb /WHOLEARCHIVE:out\\EDRSandblast_Core.lib /WHOLEARCHIVE:out\\EDRSandblast_API.lib kernel32.lib user32.lib gdi32.lib shlwapi.lib winhttp.lib pathcch.lib advapi32.lib dbghelp.lib version.lib shell32.lib ole32.lib oleaut32.lib uuid.lib netapi32.lib ntdll.lib crypt32.lib psapi.lib ucrt.lib vcruntime.lib msvcrt.lib msvcprt.lib'), BuildStep("dir /s out", allow_failure=True)],
  artifacts=[Artifact(path="out/EDRSandblast.dll", component="EDRSandblast.dll", pdb="out/EDRSandblast.pdb")],
  build_flags="Release x64 /O2 /MD /Zi /GL-; whole core + API archives; /DLL /NOENTRY /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO",
  notes="Complete upstream core and static API archives, linked whole into a corpus DLL. x64 only per upstream. SysWhispers2 code is vendored and recorded separately from the corpus SysWhispers v1 family. System dependencies are dynamic. No CLI or LSASS example is collected. Linked and disassembled only; never executed or used with a driver.",
 ),
}
