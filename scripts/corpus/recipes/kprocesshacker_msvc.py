"""Process Hacker v2.39 KProcessHacker driver, not System Informer.

Pinned to upstream v2.39 (commit 4310de8c43f7600e344b789ffabad79b79878f6a).
No upstream source is patched. Every obstacle is handled by a forced props
file or a msbuild property on the command line, and each attempt is tried in
turn with || so the build log records every failure.

Open risks, in the order they bite:
1. kph.h includes WDK <ntifs.h> before it defines PHNT_MODE, and phnt's
   ntexapi.h, ntmmapi.h and ntobapi.h define enums and objects that the WDK
   also defines (C2011 on _FIRMWARE_TYPE and _MEMORY_INFORMATION_CLASS was
   reported in an earlier round). The forced props define PHNT_MODE=0 so any
   phnt header reached through the WDK's own includes uses kernel mode.
2. The project declares TargetVersion=Windows8. WDK 10.0.26100 rejects
   Windows8, so the attempts retarget to Windows8.1, then Windows10.
3. BCrypt* calls in verify.c need cng.lib on the kernel side; the project
   names no AdditionalDependencies.

Driver images are never packaged, signed, installed or loaded. This is a
disassembly reference only.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_PROPS = ('python -c "import base64;'
          "open('corpus-drv.props','wb').write(base64.b64decode('PFByb2plY3Q+PFByb3BlcnR5R3JvdXA+PFdob2xlUHJvZ3JhbU9wdGltaXphdGlvbj5mYWxzZTwvV2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPjxMaW5rSW5jcmVtZW50YWw+ZmFsc2U8L0xpbmtJbmNyZW1lbnRhbD48SW50RGlyPiQoT3V0RGlyKW9ialwkKFByb2plY3ROYW1lKVw8L0ludERpcj48L1Byb3BlcnR5R3JvdXA+PEl0ZW1EZWZpbml0aW9uR3JvdXA+PENsQ29tcGlsZT48UHJlcHJvY2Vzc29yRGVmaW5pdGlvbnM+UEhOVF9NT0RFPTA7JShQcmVwcm9jZXNzb3JEZWZpbml0aW9ucyk8L1ByZXByb2Nlc3NvckRlZmluaXRpb25zPjxSdW50aW1lTGlicmFyeT5NdWx0aVRocmVhZGVkRExMPC9SdW50aW1lTGlicmFyeT48T3B0aW1pemF0aW9uPk1heFNwZWVkPC9PcHRpbWl6YXRpb24+PFdob2xlUHJvZ3JhbU9wdGltaXphdGlvbj5mYWxzZTwvV2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPjxEZWJ1Z0luZm9ybWF0aW9uRm9ybWF0PlByb2dyYW1EYXRhYmFzZTwvRGVidWdJbmZvcm1hdGlvbkZvcm1hdD48UHJvZ3JhbURhdGFCYXNlRmlsZU5hbWU+JChJbnREaXIpJChQcm9qZWN0TmFtZSkuY29tcGlsZXIucGRiPC9Qcm9ncmFtRGF0YUJhc2VGaWxlTmFtZT48VHJlYXRXYXJuaW5nQXNFcnJvcj5mYWxzZTwvVHJlYXRXYXJuaW5nQXNFcnJvcj48QWRkaXRpb25hbE9wdGlvbnM+L0dMLSAlKEFkZGl0aW9uYWxPcHRpb25zKTwvQWRkaXRpb25hbE9wdGlvbnM+PC9DbENvbXBpbGU+PExpbms+PEdlbmVyYXRlRGVidWdJbmZvcm1hdGlvbj50cnVlPC9HZW5lcmF0ZURlYnVnSW5mb3JtYXRpb24+PE9wdGltaXplUmVmZXJlbmNlcz5mYWxzZTwvT3B0aW1pemVSZWZlcmVuY2VzPjxFbmFibGVDT01EQVRGb2xkaW5nPmZhbHNlPC9FbmFibGVDT01EQVRGb2xkaW5nPjxMaW5rVGltZUNvZGVHZW5lcmF0aW9uPkRlZmF1bHQ8L0xpbmtUaW1lQ29kZUdlbmVyYXRpb24+PFByb2dyYW1EYXRhYmFzZUZpbGU+JChPdXREaXIpJChUYXJnZXROYW1lKS5wZGI8L1Byb2dyYW1EYXRhYmFzZUZpbGU+PEFkZGl0aW9uYWxPcHRpb25zPi9CcmVwcm8gL0lOQ1JFTUVOVEFMOk5PICUoQWRkaXRpb25hbE9wdGlvbnMpPC9BZGRpdGlvbmFsT3B0aW9ucz48L0xpbms+PExpYj48TGlua1RpbWVDb2RlR2VuZXJhdGlvbj5mYWxzZTwvTGlua1RpbWVDb2RlR2VuZXJhdGlvbj48L0xpYj48L0l0ZW1EZWZpbml0aW9uR3JvdXA+PC9Qcm9qZWN0Pgo='));"
          "open('corpus-drv-plain.props','wb').write(base64.b64decode('PFByb2plY3Q+PFByb3BlcnR5R3JvdXA+PFdob2xlUHJvZ3JhbU9wdGltaXphdGlvbj5mYWxzZTwvV2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPjxMaW5rSW5jcmVtZW50YWw+ZmFsc2U8L0xpbmtJbmNyZW1lbnRhbD48SW50RGlyPiQoT3V0RGlyKW9ialwkKFByb2plY3ROYW1lKVw8L0ludERpcj48L1Byb3BlcnR5R3JvdXA+PEl0ZW1EZWZpbml0aW9uR3JvdXA+PENsQ29tcGlsZT48UHJlcHJvY2Vzc29yRGVmaW5pdGlvbnM+JShQcmVwcm9jZXNzb3JEZWZpbml0aW9ucyk8L1ByZXByb2Nlc3NvckRlZmluaXRpb25zPjxSdW50aW1lTGlicmFyeT5NdWx0aVRocmVhZGVkRExMPC9SdW50aW1lTGlicmFyeT48T3B0aW1pemF0aW9uPk1heFNwZWVkPC9PcHRpbWl6YXRpb24+PFdob2xlUHJvZ3JhbU9wdGltaXphdGlvbj5mYWxzZTwvV2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPjxEZWJ1Z0luZm9ybWF0aW9uRm9ybWF0PlByb2dyYW1EYXRhYmFzZTwvRGVidWdJbmZvcm1hdGlvbkZvcm1hdD48UHJvZ3JhbURhdGFCYXNlRmlsZU5hbWU+JChJbnREaXIpJChQcm9qZWN0TmFtZSkuY29tcGlsZXIucGRiPC9Qcm9ncmFtRGF0YUJhc2VGaWxlTmFtZT48VHJlYXRXYXJuaW5nQXNFcnJvcj5mYWxzZTwvVHJlYXRXYXJuaW5nQXNFcnJvcj48QWRkaXRpb25hbE9wdGlvbnM+L0dMLSAlKEFkZGl0aW9uYWxPcHRpb25zKTwvQWRkaXRpb25hbE9wdGlvbnM+PC9DbENvbXBpbGU+PExpbms+PEdlbmVyYXRlRGVidWdJbmZvcm1hdGlvbj50cnVlPC9HZW5lcmF0ZURlYnVnSW5mb3JtYXRpb24+PE9wdGltaXplUmVmZXJlbmNlcz5mYWxzZTwvT3B0aW1pemVSZWZlcmVuY2VzPjxFbmFibGVDT01EQVRGb2xkaW5nPmZhbHNlPC9FbmFibGVDT01EQVRGb2xkaW5nPjxMaW5rVGltZUNvZGVHZW5lcmF0aW9uPkRlZmF1bHQ8L0xpbmtUaW1lQ29kZUdlbmVyYXRpb24+PFByb2dyYW1EYXRhYmFzZUZpbGU+JChPdXREaXIpJChUYXJnZXROYW1lKS5wZGI8L1Byb2dyYW1EYXRhYmFzZUZpbGU+PEFkZGl0aW9uYWxPcHRpb25zPi9CcmVwcm8gL0lOQ1JFTUVOVEFMOk5PICUoQWRkaXRpb25hbE9wdGlvbnMpPC9BZGRpdGlvbmFsT3B0aW9ucz48L0xpbms+PExpYj48TGlua1RpbWVDb2RlR2VuZXJhdGlvbj5mYWxzZTwvTGlua1RpbWVDb2RlR2VuZXJhdGlvbj48L0xpYj48L0l0ZW1EZWZpbml0aW9uR3JvdXA+PC9Qcm9qZWN0Pgo='))\"")

_MSBUILD = ('msbuild KProcessHacker\\KProcessHacker.vcxproj /t:Rebuild /p:Configuration="Win8 Release" /p:Platform=x64'
            ' /p:PlatformToolset=WindowsKernelModeDriver10.0 /p:WindowsTargetPlatformVersion=10.0.26100.0'
            ' /p:TargetVersion={target} /p:DriverType=WDM /p:SignMode=Off /p:SkipPackageVerification=true'
            ' /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false'
            ' /p:ForceImportBeforeCppTargets=%CD%\\{props} /m /v:normal')

_BUILD = ' || '.join([
    _MSBUILD.format(target="Windows8.1", props="corpus-drv.props"),
    _MSBUILD.format(target="Windows10", props="corpus-drv.props"),
    _MSBUILD.format(target="Windows8.1", props="corpus-drv-plain.props"),
])

RECIPES = {
 "KProcessHacker_2.39_msvc": Recipe(
  family="KProcessHacker", version="2.39", source=Source(git_url="https://github.com/processhacker/processhacker.git", git_ref="4310de8c43f7600e344b789ffabad79b79878f6a"),
  upstream="https://github.com/processhacker/processhacker/tree/v2.39", license="GPL-3.0-or-later (source headers)", toolchains=["msvc_x64"],
  build=[BuildStep(_PROPS), BuildStep(_BUILD), BuildStep("dir /s out", allow_failure=True)],
  artifacts=[Artifact(path="out/kprocesshacker.sys", component="kprocesshacker.sys", pdb="out/kprocesshacker.pdb")],
  build_flags="v2.39 Win8 Release x64; WDK 10.0.26100.0 via WindowsKernelModeDriver10.0; TargetVersion attempts Windows8.1, Windows10; /O2 /MD /Zi /GL- /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO; PHNT_MODE=0 forced by props; SignMode=Off",
  notes="v2.39 driver as requested by tracker #66, never current System Informer. No x86 kernel target exists in WDK 10.0.26100, so this recipe is x64 only. Kernel runtime/import residue is a measured limitation. No packaging, signing, installation or loading.",
 ),
}
