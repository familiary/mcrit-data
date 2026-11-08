"""Original DiskCryptor 1.1.846.118 filter driver (dcrypt.sys), x86 build.

The x86 half of ``DiskCryptorDrv_1.1.846.118_msvc``. It is a recipe of its own
because the x64 one declares ``msvc_x64`` and builds against the runner's WDK
10.0.26100.0, which cannot produce an x86 driver; (family, version) is shared
and ``refresh_provenance.py`` separates the two by the toolchain in the slug.

How the x86 image is built, in the order the options were tried:

1. NuGet Microsoft.Windows.WDK.x86 / Microsoft.Windows.SDK.CPP.x86, inspected
   directly. Microsoft.Windows.WDK.x86 10.0.26100.1 (sha256
   4a3f6cff29720c632d605f9e6901c020f314e23669fec076c4679e764cf56516),
   10.0.26100.6584 (dfa6cf4884fc7b88d59e2d40afad876bc6b3f4954bdf449d5c0ded9e3db22db1)
   and 10.0.28000.1839 ship the km headers and the msbuild targets but no
   Lib\\<ver>\\km directory at all: the only .lib files in them are KMDF's
   wdfldr.lib and wdfdriverentry.lib and four um stubs, so there is no
   ntoskrnl.lib, hal.lib or fltmgr.lib for x86. The package has no version
   older than 10.0.26090 and Microsoft.Windows.SDK.CPP.x86 ships user-mode
   libraries only. Option 1 cannot link a driver.
2. An older WDK installed beside the runner's: WDK 10.0.22621 (Windows 11 22H2),
   the last kit that carries Lib\\10.0.22621.0\\km\\x86. ``scripts/corpus/install_wdk_x86.py``
   downloads the installer stub, checks its sha256
   (f3948d1486f8a7821bcef431487d3893fcd3a053d97ab37a1333a0c26e0bd232, version
   10.1.22621.382), installs the kit with /quiet and falls back to the
   Chocolatey package of the same kit. The kits do not overlap (Include, Lib and
   build are per-version directories), so the x64 recipes are unaffected.
   Run 42440504687 showed that kit's msbuild integration rejects Win32 too:
   C:\\Program Files (x86)\\Windows Kits\\10\\build\\10.0.22621.0\\WindowsDriver.common.targets(235,5):
   error :  'Win32' is not a valid architecture for Kernel mode drivers or UMDF drivers
   (reported for crypto_fast.vcxproj, the ProjectReference of driver.vcxproj).
   So the WindowsKernelModeDriver10.0 toolset cannot be used for x86 at all; only
   the kit's headers and x86 libraries are usable.
3. Driving the compiler and linker with those headers and libraries. The
   project's own Release|Win32 configuration is still built with msbuild, but
   with the ordinary v143 toolset (/p:PlatformToolset=v143,
   /p:WindowsTargetPlatformVersion=10.0.22621.0) and the forced props turn it
   into a driver: /kernel, _KERNEL_MODE and Windows 10 NTDDI/WINNT defines, the
   22621 km, km\\crt and shared include directories, the km\\x86 library
   directory and libcntpr.lib (the kernel C runtime subset the WDK toolset adds
   to a driver link). The project itself already supplies /Gz, /DRIVER:WDM,
   /SUBSYSTEM:NATIVE, /NODEFAULTLIB and entry DriverEntry.

Recipe-applied changes, each of them NOT in upstream, so the image is NOT
byte-identical to a build of unmodified upstream (it is not byte-identical to an
upstream release anyway: those were built with the DDK 7.1 and /GL):

* The WDK 10.0.22621 install above (a different toolchain from the 2014
  upstream one).
* corpus-inc\\suppress.h, a generated stub with no macros: the DDK 7.1
  suppress.h that shared\\warning.h includes is not in WDK 10. Nothing in the
  driver sources uses the macros it defined.
* corpus-drv.props, force-imported (it no longer sets ConfigurationType=Driver: the v143 project stays an application target whose output the project names .sys): adds the WDK 10.0.22621 km, km\\crt and
  shared include directories (the project sets IgnoreStandardIncludePath and
  names $(DDK)\\inc\\*, which WDK 10 never defines), /MD, /O2-equivalent
  MaxSpeed, no /GL, /DEBUG with a linker PDB, /OPT:NOREF /OPT:NOICF /Brepro
  /INCREMENTAL:NO, /IGNORE:4266, TreatLinkerWarningAsErrors false, and for x86
  ImageHasSafeExceptionHandlers=false (/SAFESEH:NO: the yasm-assembled objects
  of crypto_fast carry no safe-handler table). It is the x64 props file plus
  that one property.

The project's own Win32 settings are untouched: /Gz (StdCall), _X86_;IS_DRIVER,
BufferSecurityCheck off, entry DriverEntry, base address 0x10000, yasm -f win32
for crypto_fast\\i386\\*.asm.

Open risks:
1. The WDK 10.0.22621 payload is downloaded by the installer stub at build
   time and is not pinned beyond the stub's own version and sha256.
2. The x86 kernel-mode glue baseline is measured on the runner from the same
   10.0.22621 libraries (baseline.kernel_glue for an x86 toolchain); an x86
   image filtered before that baseline existed would keep the runtime.
3. The driver is linked and disassembled only. It is never packaged, signed,
   installed or loaded.
"""

import base64

from ..recipe import Artifact, BuildStep, Recipe, Source

_KIT = "10.0.22621.0"

_PROPS_XML = (
    "<Project>"
    "<PropertyGroup><WholeProgramOptimization>false</WholeProgramOptimization>"
    "<LinkIncremental>false</LinkIncremental>"
    "<IntDir>$(OutDir)obj\\$(ProjectName)\\</IntDir></PropertyGroup>"
    "<ItemDefinitionGroup><ClCompile>"
    "<AdditionalIncludeDirectories>$(SolutionDir)corpus-inc;"
    "$(WindowsSdkDir)Include\\$(WindowsTargetPlatformVersion)\\km;"
    "$(WindowsSdkDir)Include\\$(WindowsTargetPlatformVersion)\\km\\crt;"
    "$(WindowsSdkDir)Include\\$(WindowsTargetPlatformVersion)\\shared;"
    "%(AdditionalIncludeDirectories)</AdditionalIncludeDirectories>"
    "<PreprocessorDefinitions>_KERNEL_MODE;NTDDI_VERSION=0x0A000000;"
    "_WIN32_WINNT=0x0A00;WINVER=0x0A00;%(PreprocessorDefinitions)</PreprocessorDefinitions>"
    "<RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary>"
    "<Optimization>MaxSpeed</Optimization>"
    "<WholeProgramOptimization>false</WholeProgramOptimization>"
    "<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>"
    "<ProgramDataBaseFileName>$(IntDir)$(ProjectName).compiler.pdb</ProgramDataBaseFileName>"
    "<TreatWarningAsError>false</TreatWarningAsError>"
    "<AdditionalOptions>/kernel /GL- %(AdditionalOptions)</AdditionalOptions>"
    "</ClCompile><Link>"
    "<TreatLinkerWarningAsErrors>false</TreatLinkerWarningAsErrors>"
    "<GenerateDebugInformation>true</GenerateDebugInformation>"
    "<ImageHasSafeExceptionHandlers>false</ImageHasSafeExceptionHandlers>"
    "<AdditionalLibraryDirectories>$(WindowsSdkDir)Lib\\$(WindowsTargetPlatformVersion)\\km\\x86;"
    "%(AdditionalLibraryDirectories)</AdditionalLibraryDirectories>"
    "<AdditionalDependencies>%(AdditionalDependencies);libcntpr.lib</AdditionalDependencies>"
    "<OptimizeReferences>false</OptimizeReferences>"
    "<EnableCOMDATFolding>false</EnableCOMDATFolding>"
    "<LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration>"
    "<ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile>"
    "<AdditionalOptions>/Brepro /INCREMENTAL:NO /IGNORE:4266 %(AdditionalOptions)</AdditionalOptions>"
    "</Link><Lib><LinkTimeCodeGeneration>false</LinkTimeCodeGeneration></Lib>"
    "</ItemDefinitionGroup></Project>")

_PROPS = ('python -c "import base64;open(\'corpus-drv.props\',\'wb\').write('
          "base64.b64decode('%s'))\"" % base64.b64encode(_PROPS_XML.encode()).decode())

_SUPPRESS_STUB = ('python -c "import os;os.makedirs(\'corpus-inc\',exist_ok=True);'
                  "open('corpus-inc/suppress.h','w').write('/* corpus stub: the DDK 7.1 suppress.h that shared warning.h includes "
                  "is not in WDK 10. It defines no macros. */\\n#pragma once\\n')\"")

RECIPES = {
 "DiskCryptorDrv_1.1.846.118_msvc_x86": Recipe(
  family="DiskCryptorDrv", version="1.1.846.118", source=Source(url="https://raw.githubusercontent.com/DavidXanatos/DiskCryptor/b9e8463bc73cde0fd906cea8c483e290a7eb53ed/ntldr/1.1.846.118/dcrypt_1.1.846.118_src.zip", sha256="5720eb2725d67803ef585ed5bd155c439489dd606f8b62ff0e89ddfc60da2f32"),
  upstream="https://github.com/DavidXanatos/DiskCryptor/tree/b9e8463bc73cde0fd906cea8c483e290a7eb53ed/ntldr/1.1.846.118", license="GPL-3.0 (original archive license.txt)", toolchains=["msvc_x86"],
  build=[BuildStep('python "{repo}/scripts/corpus/install_wdk_x86.py"'), BuildStep(_PROPS), BuildStep(_SUPPRESS_STUB), BuildStep("if not exist out\\obj\\crypto_fast mkdir out\\obj\\crypto_fast"),
   BuildStep('msbuild driver\\driver.vcxproj /p:Configuration=Release /p:Platform={msbuild_platform} /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=' + _KIT + ' /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false /p:ForceImportBeforeCppTargets=%CD%\\corpus-drv.props /m /v:normal'), BuildStep("dir /s out", allow_failure=True)],
  artifacts=[Artifact(path="out/dcrypt.sys", component="dcrypt.sys", pdb="out/dcrypt.pdb")],
  build_flags="Original 1.1.846.118 Release Win32 with the v143 toolset (the WDK msbuild toolset rejects Win32), WDK 10.0.22621.0 headers and libraries (installed beside 10.0.26100.0), /O2 /MD /Zi /GL- /kernel /Gz /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO /SAFESEH:NO; SignMode=Off; /I corpus-inc (stub suppress.h), WDK 10.0.22621.0 km, km\\crt and shared. NOT byte-identical to unmodified upstream",
  notes="Original driver, separate from user-mode DiskCryptor; x86 build of the same pinned source as the x64 image. WDK 10.0.26100.0 has no x86 kernel target and Microsoft.Windows.WDK.x86 carries no km libraries, so WDK 10.0.22621.0 is installed by scripts/corpus/install_wdk_x86.py (installer stub pinned by sha256 f3948d14...d232); its msbuild toolset also rejects Win32 ('Win32' is not a valid architecture for Kernel mode drivers or UMDF drivers), so driver.vcxproj is built with the v143 toolset and the props make it a kernel-mode driver. Recipe-applied, NOT byte-identical to unmodified upstream: the v143 toolset with WDK 10.0.22621 headers/libraries instead of the WDK msbuild toolset, a generated corpus-inc/suppress.h stub, and a forced props file (WDK 10 km include directories, /kernel, /MD, no /GL, libcntpr.lib, /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO, /IGNORE:4266, /SAFESEH:NO). The driver is linked and disassembled only, never loaded or installed.",
 ),
}
