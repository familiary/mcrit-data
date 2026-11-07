"""Original DiskCryptor 1.1.846.118 user-mode API and support programs.

CI measurements, SMDA 4.8.0/MCRIT 1.9.0 (functions >=10 instructions):
  x64 dcapi.dll 213+161=374, 127 functions/120 hashes; dccon.exe 96+169=265, 22/22; dcinst.exe 23+145=168, 4/4.
  x86 dcapi.dll 234+170=404, 140/131; dccon.exe 99+175=274, 23/23; dcinst.exe 24+139=163, 5/5.
  Cross-architecture PicHash overlap is 0 for each like component. Within-architecture component overlap is 0 everywhere: the x86 dcapi/dccon share of _snwprintf 0xe7c749284c098840 (20 instructions) is removed by the wide-stdio glue baseline.

The glue baseline removes the printf/wprintf and __scrt_common_main_seh wrappers from the dccon.exe images, so the earlier survivors 0xa487ef4456111551 and 0x01b000030f8b5bfc (x64) and 0xaaa5d2355288b00d (x86) are gone. Named survivors at or above the floor are x64 dcapi.dll StringCchPrintfW 0xa676f9a691935460 (62 instructions), x64 dcinst.exe __scrt_common_main_seh 0x9c6b020cef91b85d (92), x86 dcapi.dll StringCchPrintfW 0x9125a9f03bc5bafa (59), and x86 dcinst.exe __scrt_common_main_seh 0xd5e31daef61b43e7 (110) plus $+0x124 0xb6f9895ed1a726a6 (10). The 16-bit bootloader is not rebuilt; its original resource bytes remain data. The user-mode images are linked and disassembled only.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_PROPS = 'python -c "open(\'corpus-um.props\',\'w\').write(\'<Project><PropertyGroup><WholeProgramOptimization>false</WholeProgramOptimization><LinkIncremental>false</LinkIncremental><IntDir>$(OutDir)obj\\\\$(ProjectName)\\\\</IntDir></PropertyGroup><ItemDefinitionGroup><ClCompile><RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary><Optimization>MaxSpeed</Optimization><WholeProgramOptimization>false</WholeProgramOptimization><DebugInformationFormat>ProgramDatabase</DebugInformationFormat><ProgramDataBaseFileName>$(IntDir)$(ProjectName).compiler.pdb</ProgramDataBaseFileName><TreatWarningAsError>false</TreatWarningAsError><AdditionalOptions>/GL- %(AdditionalOptions)</AdditionalOptions></ClCompile><Link><AdditionalDependencies>advapi32.lib;user32.lib;psapi.lib</AdditionalDependencies><GenerateDebugInformation>true</GenerateDebugInformation><OptimizeReferences>false</OptimizeReferences><EnableCOMDATFolding>false</EnableCOMDATFolding><LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration><ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile><AdditionalOptions>/Brepro /INCREMENTAL:NO %(AdditionalOptions)</AdditionalOptions></Link><Lib><LinkTimeCodeGeneration>false</LinkTimeCodeGeneration></Lib></ItemDefinitionGroup></Project>\')"'

RECIPES = {
 "DiskCryptor_1.1.846.118_msvc": Recipe(
  family="DiskCryptor", version="1.1.846.118", source=Source(url="https://raw.githubusercontent.com/DavidXanatos/DiskCryptor/b9e8463bc73cde0fd906cea8c483e290a7eb53ed/ntldr/1.1.846.118/dcrypt_1.1.846.118_src.zip", sha256="5720eb2725d67803ef585ed5bd155c439489dd606f8b62ff0e89ddfc60da2f32"),
  upstream="https://github.com/DavidXanatos/DiskCryptor/tree/b9e8463bc73cde0fd906cea8c483e290a7eb53ed/ntldr/1.1.846.118", license="GPL-3.0 (original archive license.txt)",
  toolchains=["msvc_x86", "msvc_x64"],
  build=[BuildStep(_PROPS), BuildStep("if not exist out\\obj\\crypto_fast mkdir out\\obj\\crypto_fast"),
   BuildStep('msbuild dcapi\\dcapi.vcxproj /p:Configuration=Release /p:Platform={msbuild_platform} /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0 /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false /p:ForceImportBeforeCppTargets=%CD%\\corpus-um.props /m /v:normal'),
   BuildStep('msbuild dccon\\dccon.vcxproj /p:Configuration=Release /p:Platform={msbuild_platform} /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0 /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false /p:ForceImportBeforeCppTargets=%CD%\\corpus-um.props /m /v:normal'),
   BuildStep('msbuild dcinst\\dcinst.vcxproj /p:Configuration=Release /p:Platform={msbuild_platform} /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0 /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false /p:ForceImportBeforeCppTargets=%CD%\\corpus-um.props /m /v:normal'),
   BuildStep("dir /s out", allow_failure=True)],
  artifacts=[Artifact(path="out/dcapi.dll", component="dcapi.dll", pdb="out/dcapi.pdb"), Artifact(path="out/dccon.exe", component="dccon.exe", pdb="out/dccon.pdb"), Artifact(path="out/dcinst.exe", component="dcinst.exe", pdb="out/dcinst.pdb")],
  build_flags="Original 1.1.846.118 Release /O2 /MD /Zi /GL- v143; /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO; modern dynamic CRT instead of obsolete msvcrt_winxp/win2003 objects",
  notes="Original 2014 source archive preserved by the maintained fork, not modern fork code. dcapi plus dccon/dcinst are collected. The 16-bit bootloader is not built; upstream resource bytes stay data. Forced props replace obsolete CRT compatibility object dependencies with current SDK imports and /MD. Crypto project references are built from the same pinned archive. No encryption, installation or execution is performed.",
 ),
}
