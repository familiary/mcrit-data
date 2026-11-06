"""Process Hacker v2.39 KProcessHacker driver, not System Informer.

Initial Windows probe. Open risks: legacy headers versus WDK 10.0.26100;
old project assumptions; link/PDB paths; kernel glue surviving the user-mode
baseline. No upstream source is patched. Driver images are never packaged,
signed, installed or loaded; all output is for disassembly only.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_PROPS = 'python -c "open(\'corpus-drv.props\',\'w\').write(\'<Project><PropertyGroup><WholeProgramOptimization>false</WholeProgramOptimization><LinkIncremental>false</LinkIncremental><IntDir>$(OutDir)obj\\\\$(ProjectName)\\\\</IntDir></PropertyGroup><ItemDefinitionGroup><ClCompile><RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary><Optimization>MaxSpeed</Optimization><WholeProgramOptimization>false</WholeProgramOptimization><DebugInformationFormat>ProgramDatabase</DebugInformationFormat><ProgramDataBaseFileName>$(IntDir)$(ProjectName).compiler.pdb</ProgramDataBaseFileName><TreatWarningAsError>false</TreatWarningAsError><AdditionalOptions>/GL- %(AdditionalOptions)</AdditionalOptions></ClCompile><Link><GenerateDebugInformation>true</GenerateDebugInformation><OptimizeReferences>false</OptimizeReferences><EnableCOMDATFolding>false</EnableCOMDATFolding><LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration><ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile><AdditionalOptions>/Brepro /INCREMENTAL:NO %(AdditionalOptions)</AdditionalOptions></Link><Lib><LinkTimeCodeGeneration>false</LinkTimeCodeGeneration></Lib></ItemDefinitionGroup></Project>\')"'

RECIPES = {
 "KProcessHacker_2.39_msvc": Recipe(
  family="KProcessHacker", version="2.39", source=Source(git_url="https://github.com/processhacker/processhacker.git", git_ref="4310de8c43f7600e344b789ffabad79b79878f6a"),
  upstream="https://github.com/processhacker/processhacker/tree/v2.39", license="GPL-3.0-or-later (source headers)", toolchains=["msvc_x64"],
  build=[BuildStep(_PROPS),
   BuildStep('msbuild KProcessHacker\\KProcessHacker.vcxproj /p:Configuration="Win8 Release" /p:Platform=x64 /p:PlatformToolset=WindowsKernelModeDriver10.0 /p:WindowsTargetPlatformVersion=10.0.26100.0 /p:TargetVersion=Windows10 /p:DriverType=WDM /p:SignMode=Off /p:SkipPackageVerification=true /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false /p:ForceImportBeforeCppTargets=%CD%\\corpus-drv.props /m /v:normal'), BuildStep("dir /s out", allow_failure=True)],
  artifacts=[Artifact(path="out/kprocesshacker.sys", component="kprocesshacker.sys", pdb="out/kprocesshacker.pdb")],
  build_flags="v2.39 Win8 Release x64, WDK 10.0.26100.0 retarget from 8.0; /O2 /MD /Zi /GL- /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO; SignMode=Off",
  notes="v2.39 driver as requested by tracker #66, never current System Informer. WDK 10.0.26100.0 replaces the unavailable 8.0 toolset through properties only. No x86 kernel target in this WDK. Kernel runtime/import residue is a measured limitation. No packaging, signing, installation or loading.",
 ),
}
