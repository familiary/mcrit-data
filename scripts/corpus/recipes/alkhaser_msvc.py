"""al-khaser check suite; measure Release /O2 and /Od separately.

Initial Windows probe: source/project inspection only. No upstream source edits.
Open risks: modern SDK/WDK compatibility; PDB coverage; retained kernel/import
glue and MSVC printf/startup wrappers. Every image is linked and disassembled
only, never run, signed, installed or loaded.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_PROPS_O2 = 'python -c "open(\'corpus-msvc.props\',\'w\').write(\'<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003"><PropertyGroup><WholeProgramOptimization>false</WholeProgramOptimization><LinkIncremental>false</LinkIncremental><IntDir>$(OutDir)obj\\\\$(ProjectName)\\\\</IntDir></PropertyGroup><ItemDefinitionGroup><ClCompile><RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary><Optimization>MaxSpeed</Optimization><WholeProgramOptimization>false</WholeProgramOptimization><DebugInformationFormat>ProgramDatabase</DebugInformationFormat><ProgramDataBaseFileName>$(IntDir)$(ProjectName).compiler.pdb</ProgramDataBaseFileName><TreatWarningAsError>false</TreatWarningAsError><AdditionalOptions>/GL- %(AdditionalOptions)</AdditionalOptions></ClCompile><Link><GenerateDebugInformation>true</GenerateDebugInformation><OptimizeReferences>false</OptimizeReferences><EnableCOMDATFolding>false</EnableCOMDATFolding><LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration><ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile><AdditionalOptions>/Brepro /INCREMENTAL:NO %(AdditionalOptions)</AdditionalOptions></Link><Lib><LinkTimeCodeGeneration>false</LinkTimeCodeGeneration></Lib></ItemDefinitionGroup></Project>\')"'
_PROPS_OD = 'python -c "open(\'corpus-msvc.props\',\'w\').write(\'<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003"><PropertyGroup><WholeProgramOptimization>false</WholeProgramOptimization><LinkIncremental>false</LinkIncremental><IntDir>$(OutDir)obj\\\\$(ProjectName)\\\\</IntDir></PropertyGroup><ItemDefinitionGroup><ClCompile><RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary><Optimization>Disabled</Optimization><InlineFunctionExpansion>Disabled</InlineFunctionExpansion><WholeProgramOptimization>false</WholeProgramOptimization><DebugInformationFormat>ProgramDatabase</DebugInformationFormat><ProgramDataBaseFileName>$(IntDir)$(ProjectName).compiler.pdb</ProgramDataBaseFileName><TreatWarningAsError>false</TreatWarningAsError><AdditionalOptions>/GL- %(AdditionalOptions)</AdditionalOptions></ClCompile><Link><GenerateDebugInformation>true</GenerateDebugInformation><OptimizeReferences>false</OptimizeReferences><EnableCOMDATFolding>false</EnableCOMDATFolding><LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration><ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile><AdditionalOptions>/Brepro /INCREMENTAL:NO %(AdditionalOptions)</AdditionalOptions></Link><Lib><LinkTimeCodeGeneration>false</LinkTimeCodeGeneration></Lib></ItemDefinitionGroup></Project>\')"'

RECIPES = {}
for _label, _props in (("O2", _PROPS_O2), ("Od", _PROPS_OD)):
 RECIPES["al-khaser_2026-07-01_" + _label + "_msvc"] = Recipe(
  family="al-khaser", version="2026-07-01-" + _label,
  source=Source(git_url="https://github.com/LordNoteworthy/al-khaser.git", git_ref="f0e5559073fe02c4f50cc8c3ed8d5b302a6a0659"),
  upstream="https://github.com/LordNoteworthy/al-khaser", license="GPL-2.0 (LICENSE); source credits retained upstream",
  toolchains=["msvc_x86", "msvc_x64"],
  build=[BuildStep("python -m pip install --quiet smda==5.0.2 mcrit==1.16.0"), BuildStep(_props),
   BuildStep('msbuild al-khaser\\al-khaser.vcxproj /p:Configuration=Release /p:Platform={msbuild_platform} /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0 /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false /p:ForceImportBeforeCppTargets=%CD%\\corpus-msvc.props /m /v:normal'), BuildStep("dir /s out", allow_failure=True)],
  artifacts=[Artifact(path="out/al-khaser.exe", component="al-khaser.exe", pdb="out/al-khaser.pdb")],
  build_flags="Release /" + _label + " /MD /Zi /GL- /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO",
  notes="Complete upstream check-suite executable. /O2 models optimized consumers; /Od is a measurement axis for independent check bodies lost to inlining. Its coverage must be justified by measured overlaps after import. No helper DLL is collected. No checks are executed.",
 )
