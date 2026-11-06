"""Original DiskCryptor 1.1.846.118 filter driver (dcrypt.sys), x64 WDK only.

Built from the pinned 2014 source archive with the runner's WDK 10.0.26100.0
and no upstream source changes. The archive's driver project includes
$(DDK)\\inc\\* directories that a WDK 10 build never defines, and its
shared\\warning.h includes <suppress.h>, which the WDK 10 kit does not ship.
The recipe writes a stub suppress.h into corpus-inc\\ and adds that directory
with /I through the forced props file. The stub defines no macros: the DDK 7.1
header carried PREfast __WARNING_ numbers and _PRAGMA_WARNING_SUPPRESS, and no
DiskCryptor driver source uses either. The project also sets
IgnoreStandardIncludePath, which drops the kit's kernel include directories
(ntifs.h is not found without them), so the props file adds the WDK 10 km,
km\\crt and shared directories explicitly, from $(WindowsSdkDir).

The WDK makes linker warnings errors. The only one the link raised, LNK4266
(no load-config directory for code compiled with /guard:cf), is suppressed by
name with /IGNORE:4266, and TreatLinkerWarningAsErrors is false. It concerns
the load-config directory, not the function bodies.

Open risks:
1. Only the runner's WDK 10.0.26100.0 is tested; other kits may differ.
2. The driver is linked and disassembled only. It is never packaged, signed,
   installed or loaded.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_PROPS = 'python -c "import base64;open(\'corpus-drv.props\',\'wb\').write(base64.b64decode(\'PFByb2plY3Q+PFByb3BlcnR5R3JvdXAgQ29uZGl0aW9uPSInJChNU0J1aWxkUHJvamVjdE5hbWUpJz09J2RyaXZlciciPjxDb25maWd1cmF0aW9uVHlwZT5Ecml2ZXI8L0NvbmZpZ3VyYXRpb25UeXBlPjwvUHJvcGVydHlHcm91cD48UHJvcGVydHlHcm91cD48V2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPmZhbHNlPC9XaG9sZVByb2dyYW1PcHRpbWl6YXRpb24+PExpbmtJbmNyZW1lbnRhbD5mYWxzZTwvTGlua0luY3JlbWVudGFsPjxJbnREaXI+JChPdXREaXIpb2JqXCQoUHJvamVjdE5hbWUpXDwvSW50RGlyPjwvUHJvcGVydHlHcm91cD48SXRlbURlZmluaXRpb25Hcm91cD48Q2xDb21waWxlPjxBZGRpdGlvbmFsSW5jbHVkZURpcmVjdG9yaWVzPiQoU29sdXRpb25EaXIpY29ycHVzLWluYzskKFdpbmRvd3NTZGtEaXIpSW5jbHVkZVwkKFdpbmRvd3NUYXJnZXRQbGF0Zm9ybVZlcnNpb24pXGttOyQoV2luZG93c1Nka0RpcilJbmNsdWRlXCQoV2luZG93c1RhcmdldFBsYXRmb3JtVmVyc2lvbilca21cY3J0OyQoV2luZG93c1Nka0RpcilJbmNsdWRlXCQoV2luZG93c1RhcmdldFBsYXRmb3JtVmVyc2lvbilcc2hhcmVkOyUoQWRkaXRpb25hbEluY2x1ZGVEaXJlY3Rvcmllcyk8L0FkZGl0aW9uYWxJbmNsdWRlRGlyZWN0b3JpZXM+PFJ1bnRpbWVMaWJyYXJ5Pk11bHRpVGhyZWFkZWRETEw8L1J1bnRpbWVMaWJyYXJ5PjxPcHRpbWl6YXRpb24+TWF4U3BlZWQ8L09wdGltaXphdGlvbj48V2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPmZhbHNlPC9XaG9sZVByb2dyYW1PcHRpbWl6YXRpb24+PERlYnVnSW5mb3JtYXRpb25Gb3JtYXQ+UHJvZ3JhbURhdGFiYXNlPC9EZWJ1Z0luZm9ybWF0aW9uRm9ybWF0PjxQcm9ncmFtRGF0YUJhc2VGaWxlTmFtZT4kKEludERpcikkKFByb2plY3ROYW1lKS5jb21waWxlci5wZGI8L1Byb2dyYW1EYXRhQmFzZUZpbGVOYW1lPjxUcmVhdFdhcm5pbmdBc0Vycm9yPmZhbHNlPC9UcmVhdFdhcm5pbmdBc0Vycm9yPjxBZGRpdGlvbmFsT3B0aW9ucz4vR0wtICUoQWRkaXRpb25hbE9wdGlvbnMpPC9BZGRpdGlvbmFsT3B0aW9ucz48L0NsQ29tcGlsZT48TGluaz48VHJlYXRMaW5rZXJXYXJuaW5nQXNFcnJvcnM+ZmFsc2U8L1RyZWF0TGlua2VyV2FybmluZ0FzRXJyb3JzPjxHZW5lcmF0ZURlYnVnSW5mb3JtYXRpb24+dHJ1ZTwvR2VuZXJhdGVEZWJ1Z0luZm9ybWF0aW9uPjxPcHRpbWl6ZVJlZmVyZW5jZXM+ZmFsc2U8L09wdGltaXplUmVmZXJlbmNlcz48RW5hYmxlQ09NREFURm9sZGluZz5mYWxzZTwvRW5hYmxlQ09NREFURm9sZGluZz48TGlua1RpbWVDb2RlR2VuZXJhdGlvbj5EZWZhdWx0PC9MaW5rVGltZUNvZGVHZW5lcmF0aW9uPjxQcm9ncmFtRGF0YWJhc2VGaWxlPiQoT3V0RGlyKSQoVGFyZ2V0TmFtZSkucGRiPC9Qcm9ncmFtRGF0YWJhc2VGaWxlPjxBZGRpdGlvbmFsT3B0aW9ucz4vQnJlcHJvIC9JTkNSRU1FTlRBTDpOTyAvSUdOT1JFOjQyNjYgJShBZGRpdGlvbmFsT3B0aW9ucyk8L0FkZGl0aW9uYWxPcHRpb25zPjwvTGluaz48TGliPjxMaW5rVGltZUNvZGVHZW5lcmF0aW9uPmZhbHNlPC9MaW5rVGltZUNvZGVHZW5lcmF0aW9uPjwvTGliPjwvSXRlbURlZmluaXRpb25Hcm91cD48L1Byb2plY3Q+\'))"'

_SUPPRESS_STUB = ('python -c "import os;os.makedirs(\'corpus-inc\',exist_ok=True);'
                  "open('corpus-inc/suppress.h','w').write('/* corpus stub: the DDK 7.1 suppress.h that shared warning.h includes "
                  "is not in WDK 10.0.26100. It defines no macros. */\\n#pragma once\\n')\"")

RECIPES = {
 "DiskCryptorDrv_1.1.846.118_msvc": Recipe(
  family="DiskCryptorDrv", version="1.1.846.118", source=Source(url="https://raw.githubusercontent.com/DavidXanatos/DiskCryptor/b9e8463bc73cde0fd906cea8c483e290a7eb53ed/ntldr/1.1.846.118/dcrypt_1.1.846.118_src.zip", sha256="5720eb2725d67803ef585ed5bd155c439489dd606f8b62ff0e89ddfc60da2f32"),
  upstream="https://github.com/DavidXanatos/DiskCryptor/tree/b9e8463bc73cde0fd906cea8c483e290a7eb53ed/ntldr/1.1.846.118", license="GPL-3.0 (original archive license.txt)", toolchains=["msvc_x64"],
  build=[BuildStep(_PROPS), BuildStep(_SUPPRESS_STUB), BuildStep("if not exist out\\obj\\crypto_fast mkdir out\\obj\\crypto_fast"),
   BuildStep('msbuild driver\\driver.vcxproj /p:Configuration=Release /p:Platform=x64 /p:PlatformToolset=WindowsKernelModeDriver10.0 /p:WindowsTargetPlatformVersion=10.0.26100.0 /p:DriverType=WDM /p:TargetVersion=Windows10 /p:SignMode=Off /p:SkipPackageVerification=true /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false /p:ForceImportBeforeCppTargets=%CD%\\corpus-drv.props /m /v:normal'), BuildStep("dir /s out", allow_failure=True)],
  artifacts=[Artifact(path="out/dcrypt.sys", component="dcrypt.sys", pdb="out/dcrypt.pdb")],
  build_flags="Original 1.1.846.118 Release x64, WDK 10.0.26100.0, /O2 /MD /Zi /GL- /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO; SignMode=Off; /I corpus-inc (stub suppress.h), WDK 10 km, km\\crt and shared",
  notes="Original driver, separate from user-mode DiskCryptor; no kernel image is rebuilt from modern fork source. WDK 10.0.26100.0 has no x86 kernel target. Kernel glue and import thunks may survive the user-mode baseline. Whole-program optimization and signing disabled. The driver is linked and disassembled only, never loaded or installed. Build-only fix: the generated corpus-inc/suppress.h is not upstream source.",
 ),
}
