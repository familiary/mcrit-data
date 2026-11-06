"""Original DiskCryptor 1.1.846.118 filter driver, x64 WDK only.

Initial Windows probe. Open risks: legacy headers versus WDK 10.0.26100;
old project assumptions; link/PDB paths; kernel glue surviving the user-mode
baseline. No upstream source is patched. Driver images are never packaged,
signed, installed or loaded; all output is for disassembly only.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_PROPS = 'python -c "import base64;open(\'corpus-drv.props\',\'wb\').write(base64.b64decode(\'PFByb2plY3Q+PFByb3BlcnR5R3JvdXAgQ29uZGl0aW9uPSInJChNU0J1aWxkUHJvamVjdE5hbWUpJz09J2RyaXZlciciPjxDb25maWd1cmF0aW9uVHlwZT5Ecml2ZXI8L0NvbmZpZ3VyYXRpb25UeXBlPjwvUHJvcGVydHlHcm91cD48UHJvcGVydHlHcm91cD48V2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPmZhbHNlPC9XaG9sZVByb2dyYW1PcHRpbWl6YXRpb24+PExpbmtJbmNyZW1lbnRhbD5mYWxzZTwvTGlua0luY3JlbWVudGFsPjxJbnREaXI+JChPdXREaXIpb2JqXCQoUHJvamVjdE5hbWUpXDwvSW50RGlyPjwvUHJvcGVydHlHcm91cD48SXRlbURlZmluaXRpb25Hcm91cD48Q2xDb21waWxlPjxSdW50aW1lTGlicmFyeT5NdWx0aVRocmVhZGVkRExMPC9SdW50aW1lTGlicmFyeT48T3B0aW1pemF0aW9uPk1heFNwZWVkPC9PcHRpbWl6YXRpb24+PFdob2xlUHJvZ3JhbU9wdGltaXphdGlvbj5mYWxzZTwvV2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPjxEZWJ1Z0luZm9ybWF0aW9uRm9ybWF0PlByb2dyYW1EYXRhYmFzZTwvRGVidWdJbmZvcm1hdGlvbkZvcm1hdD48UHJvZ3JhbURhdGFCYXNlRmlsZU5hbWU+JChJbnREaXIpJChQcm9qZWN0TmFtZSkuY29tcGlsZXIucGRiPC9Qcm9ncmFtRGF0YUJhc2VGaWxlTmFtZT48VHJlYXRXYXJuaW5nQXNFcnJvcj5mYWxzZTwvVHJlYXRXYXJuaW5nQXNFcnJvcj48QWRkaXRpb25hbE9wdGlvbnM+L0dMLSAlKEFkZGl0aW9uYWxPcHRpb25zKTwvQWRkaXRpb25hbE9wdGlvbnM+PC9DbENvbXBpbGU+PExpbms+PEdlbmVyYXRlRGVidWdJbmZvcm1hdGlvbj50cnVlPC9HZW5lcmF0ZURlYnVnSW5mb3JtYXRpb24+PE9wdGltaXplUmVmZXJlbmNlcz5mYWxzZTwvT3B0aW1pemVSZWZlcmVuY2VzPjxFbmFibGVDT01EQVRGb2xkaW5nPmZhbHNlPC9FbmFibGVDT01EQVRGb2xkaW5nPjxMaW5rVGltZUNvZGVHZW5lcmF0aW9uPkRlZmF1bHQ8L0xpbmtUaW1lQ29kZUdlbmVyYXRpb24+PFByb2dyYW1EYXRhYmFzZUZpbGU+JChPdXREaXIpJChUYXJnZXROYW1lKS5wZGI8L1Byb2dyYW1EYXRhYmFzZUZpbGU+PEFkZGl0aW9uYWxPcHRpb25zPi9CcmVwcm8gL0lOQ1JFTUVOVEFMOk5PICUoQWRkaXRpb25hbE9wdGlvbnMpPC9BZGRpdGlvbmFsT3B0aW9ucz48L0xpbms+PExpYj48TGlua1RpbWVDb2RlR2VuZXJhdGlvbj5mYWxzZTwvTGlua1RpbWVDb2RlR2VuZXJhdGlvbj48L0xpYj48L0l0ZW1EZWZpbml0aW9uR3JvdXA+PC9Qcm9qZWN0Pg==\'))"'

RECIPES = {
 "DiskCryptorDrv_1.1.846.118_msvc": Recipe(
  family="DiskCryptorDrv", version="1.1.846.118", source=Source(url="https://raw.githubusercontent.com/DavidXanatos/DiskCryptor/b9e8463bc73cde0fd906cea8c483e290a7eb53ed/ntldr/1.1.846.118/dcrypt_1.1.846.118_src.zip", sha256="5720eb2725d67803ef585ed5bd155c439489dd606f8b62ff0e89ddfc60da2f32"),
  upstream="https://github.com/DavidXanatos/DiskCryptor/tree/b9e8463bc73cde0fd906cea8c483e290a7eb53ed/ntldr/1.1.846.118", license="GPL-3.0 (original archive license.txt)", toolchains=["msvc_x64"],
  build=[BuildStep(_PROPS), BuildStep("if not exist out\\obj\\crypto_fast mkdir out\\obj\\crypto_fast"),
   BuildStep('msbuild driver\\driver.vcxproj /p:Configuration=Release /p:Platform=x64 /p:PlatformToolset=WindowsKernelModeDriver10.0 /p:WindowsTargetPlatformVersion=10.0.26100.0 /p:DriverType=WDM /p:TargetVersion=Windows10 /p:SignMode=Off /p:SkipPackageVerification=true /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false /p:ForceIncludeFiles= /p:ForceImportBeforeCppTargets=%CD%\\corpus-drv.props /m /v:normal'), BuildStep("dir /s out", allow_failure=True)],
  artifacts=[Artifact(path="out/dcrypt.sys", component="dcrypt.sys", pdb="out/dcrypt.pdb")],
  build_flags="Original 1.1.846.118 Release x64, WDK 10.0.26100.0, /O2 /MD /Zi /GL- /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO; SignMode=Off",
  notes="Original driver, separate from user-mode DiskCryptor; no kernel image is rebuilt from modern fork source. WDK 10.0.26100.0 has no x86 kernel target. Kernel glue and import thunks may survive the user-mode baseline. Whole-program optimization and signing disabled. The driver is linked and disassembled only, never loaded or installed.",
 ),
}
