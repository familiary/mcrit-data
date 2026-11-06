"""The complete al-khaser check suite, measuring optimized and unoptimized code.

CI measurements, SMDA 4.8.0/MCRIT 1.9.0 (functions >=10 instructions):
  O2 x64 562+1505=2067, 301 functions/260 hashes; O2 x86 607+1482=2089, 319/282.
  Od x64 1152+1469=2621, 618/435; Od x86 1224+1473=2697, 733/465.
  O2 versus Od shares 3 hashes on x64 and 2 on x86; O2 x64/x86 share 1 and Od x64/x86 share 0. The hundreds of unique Od hashes justify that measurement axis.

Runtime survivors include x64 __scrt_common_main_seh 0xd474b2694c31b2d9. The O2 x64 printf/wprintf wrapper is 0x01b000030f8b5bfc; O2 x86 printf/wprintf is 0xaaa5d2355288b00d. Od retains x64 _vfprintf_l/_vfwprintf_l 0xa660e2c3c67aa215 and printf/wprintf 0x824b303376e45f93; x86 _vfprintf_l/_vfwprintf_l 0x78d5e7411c7012b7 and printf/wprintf 0x0b340b9267eabc14. Every image is disassembled only; no check is run.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_PROPS_O2 = 'python -c "open(\'corpus-msvc.props\',\'w\').write(\'<Project><PropertyGroup><WholeProgramOptimization>false</WholeProgramOptimization><LinkIncremental>false</LinkIncremental><IntDir>$(OutDir)obj\\\\$(ProjectName)\\\\</IntDir></PropertyGroup><ItemDefinitionGroup><ClCompile><RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary><Optimization>MaxSpeed</Optimization><WholeProgramOptimization>false</WholeProgramOptimization><DebugInformationFormat>ProgramDatabase</DebugInformationFormat><ProgramDataBaseFileName>$(IntDir)$(ProjectName).compiler.pdb</ProgramDataBaseFileName><TreatWarningAsError>false</TreatWarningAsError><AdditionalOptions>/GL- %(AdditionalOptions)</AdditionalOptions></ClCompile><Link><GenerateDebugInformation>true</GenerateDebugInformation><OptimizeReferences>false</OptimizeReferences><EnableCOMDATFolding>false</EnableCOMDATFolding><LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration><ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile><AdditionalOptions>/Brepro /INCREMENTAL:NO %(AdditionalOptions)</AdditionalOptions></Link><Lib><LinkTimeCodeGeneration>false</LinkTimeCodeGeneration></Lib></ItemDefinitionGroup></Project>\')"'
_PROPS_OD = 'python -c "open(\'corpus-msvc.props\',\'w\').write(\'<Project><PropertyGroup><WholeProgramOptimization>false</WholeProgramOptimization><LinkIncremental>false</LinkIncremental><IntDir>$(OutDir)obj\\\\$(ProjectName)\\\\</IntDir></PropertyGroup><ItemDefinitionGroup><ClCompile><RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary><Optimization>Disabled</Optimization><InlineFunctionExpansion>Disabled</InlineFunctionExpansion><WholeProgramOptimization>false</WholeProgramOptimization><DebugInformationFormat>ProgramDatabase</DebugInformationFormat><ProgramDataBaseFileName>$(IntDir)$(ProjectName).compiler.pdb</ProgramDataBaseFileName><TreatWarningAsError>false</TreatWarningAsError><AdditionalOptions>/GL- %(AdditionalOptions)</AdditionalOptions></ClCompile><Link><GenerateDebugInformation>true</GenerateDebugInformation><OptimizeReferences>false</OptimizeReferences><EnableCOMDATFolding>false</EnableCOMDATFolding><LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration><ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile><AdditionalOptions>/Brepro /INCREMENTAL:NO %(AdditionalOptions)</AdditionalOptions></Link><Lib><LinkTimeCodeGeneration>false</LinkTimeCodeGeneration></Lib></ItemDefinitionGroup></Project>\')"'

RECIPES = {}
for _label, _props in (("O2", _PROPS_O2), ("Od", _PROPS_OD)):
 RECIPES["al-khaser_2026-07-01_" + _label + "_msvc"] = Recipe(
  family="al-khaser", version="2026-07-01-" + _label,
  source=Source(git_url="https://github.com/LordNoteworthy/al-khaser.git", git_ref="f0e5559073fe02c4f50cc8c3ed8d5b302a6a0659"),
  upstream="https://github.com/LordNoteworthy/al-khaser", license="GPL-2.0 (LICENSE); source credits retained upstream",
  toolchains=["msvc_x86", "msvc_x64"],
  build=[BuildStep(_props),
   BuildStep('msbuild al-khaser\\al-khaser.vcxproj /p:Configuration=Release /p:Platform={msbuild_platform} /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0 /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false /p:ForceImportBeforeCppTargets=%CD%\\corpus-msvc.props /m /v:normal'), BuildStep("dir /s out", allow_failure=True)],
  artifacts=[Artifact(path="out/al-khaser.exe", component="al-khaser.exe", pdb="out/al-khaser.pdb")],
  build_flags="Release /" + _label + " /MD /Zi /GL- /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO",
  notes="Complete upstream check-suite executable. /O2 models optimized consumers; /Od is a measurement axis for independent check bodies lost to inlining. Its coverage must be justified by measured overlaps after import. No helper DLL is collected. No checks are executed.",
 )
