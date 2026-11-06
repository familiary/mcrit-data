"""Original DiskCryptor 1.1.846.118 user-mode API and console/support programs.

Initial Windows probe. Open risks: legacy headers versus WDK 10.0.26100;
old project assumptions; link/PDB paths; kernel glue surviving the user-mode
baseline. No upstream source is patched. Driver images are never packaged,
signed, installed or loaded; all output is for disassembly only.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_PROPS = 'python -c "open(\'corpus-um.props\',\'w\').write(\'<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003"><PropertyGroup><WholeProgramOptimization>false</WholeProgramOptimization><LinkIncremental>false</LinkIncremental><IntDir>$(OutDir)obj\\\\$(ProjectName)\\\\</IntDir></PropertyGroup><ItemDefinitionGroup><ClCompile><RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary><Optimization>MaxSpeed</Optimization><WholeProgramOptimization>false</WholeProgramOptimization><DebugInformationFormat>ProgramDatabase</DebugInformationFormat><ProgramDataBaseFileName>$(IntDir)$(ProjectName).compiler.pdb</ProgramDataBaseFileName><TreatWarningAsError>false</TreatWarningAsError><AdditionalOptions>/GL- %(AdditionalOptions)</AdditionalOptions></ClCompile><Link><AdditionalDependencies>advapi32.lib;user32.lib;psapi.lib</AdditionalDependencies><GenerateDebugInformation>true</GenerateDebugInformation><OptimizeReferences>false</OptimizeReferences><EnableCOMDATFolding>false</EnableCOMDATFolding><LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration><ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile><AdditionalOptions>/Brepro /INCREMENTAL:NO %(AdditionalOptions)</AdditionalOptions></Link><Lib><LinkTimeCodeGeneration>false</LinkTimeCodeGeneration></Lib></ItemDefinitionGroup></Project>\')"'

RECIPES = {
 "DiskCryptor_1.1.846.118_msvc": Recipe(
  family="DiskCryptor", version="1.1.846.118", source=Source(url="https://raw.githubusercontent.com/DavidXanatos/DiskCryptor/b9e8463bc73cde0fd906cea8c483e290a7eb53ed/ntldr/1.1.846.118/dcrypt_1.1.846.118_src.zip", sha256="5720eb2725d67803ef585ed5bd155c439489dd606f8b62ff0e89ddfc60da2f32"),
  upstream="https://github.com/DavidXanatos/DiskCryptor/tree/b9e8463bc73cde0fd906cea8c483e290a7eb53ed/ntldr/1.1.846.118", license="GPL-3.0 (original archive license.txt)",
  toolchains=["msvc_x86", "msvc_x64"],
  build=[BuildStep("python -m pip install --quiet smda==5.0.2 mcrit==1.16.0"), BuildStep(_PROPS), BuildStep("if not exist out\\obj\\crypto_fast mkdir out\\obj\\crypto_fast"),
   BuildStep('msbuild dcapi\\dcapi.vcxproj /p:Configuration=Release /p:Platform={msbuild_platform} /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0 /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false /p:ForceImportBeforeCppTargets=%CD%\\corpus-um.props /m /v:normal'),
   BuildStep('msbuild dccon\\dccon.vcxproj /p:Configuration=Release /p:Platform={msbuild_platform} /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0 /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false /p:ForceImportBeforeCppTargets=%CD%\\corpus-um.props /m /v:normal'),
   BuildStep('msbuild dcinst\\dcinst.vcxproj /p:Configuration=Release /p:Platform={msbuild_platform} /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0 /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false /p:ForceImportBeforeCppTargets=%CD%\\corpus-um.props /m /v:normal'),
   BuildStep("dir /s out", allow_failure=True)],
  artifacts=[Artifact(path="out/dcapi.dll", component="dcapi.dll", pdb="out/dcapi.pdb"), Artifact(path="out/dccon.exe", component="dccon.exe", pdb="out/dccon.pdb"), Artifact(path="out/dcinst.exe", component="dcinst.exe", pdb="out/dcinst.pdb")],
  build_flags="Original 1.1.846.118 Release /O2 /MD /Zi /GL- v143; /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO; modern dynamic CRT instead of obsolete msvcrt_winxp/win2003 objects",
  notes="Original 2014 source archive preserved by the maintained fork, not modern fork code. dcapi plus dccon/dcinst are collected. The 16-bit bootloader is not built; upstream resource bytes stay data. Forced props replace obsolete CRT compatibility object dependencies with current SDK imports and /MD. Crypto project references are built from the same pinned archive. No encryption, installation or execution is performed.",
 ),
}
