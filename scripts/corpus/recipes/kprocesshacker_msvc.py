"""Process Hacker v2.39 KProcessHacker driver, not System Informer.

Pinned to upstream v2.39 (commit 4310de8c43f7600e344b789ffabad79b79878f6a).
No upstream source is patched. Obstacles are handled by a forced props file
and msbuild properties on the command line. Each attempt is its own build
step, so the log records every try, and the second attempt (cng.lib) runs only when the
first produced no image.

Open risks, in the order they bite:
1. kph.h includes WDK <ntifs.h> before it defines PHNT_MODE (as
   PHNT_MODE_KERNEL, which is 0). phnt's ntmmapi.h then redefines enums and
   structs the WDK already declares; the props define _NTMMAPI_H, phnt's own
   include guard, so that header is skipped in favour of the WDK copies.
   Guarding ntexapi.h as well removes SYSTEM_INFORMATION_CLASS, which only
   phnt provides (ntfill.h(65,35) C2059), so ntexapi.h stays.
2. phnt/include/ntexapi.h(2009,14) redefines _FIRMWARE_TYPE inside its
   PHNT_MODE_KERNEL block (C2011), the one clash left. The generated header
   kph_fi.h is force-included (ForcedIncludeFiles in the props): it reads
   <ntifs.h> first, then renames the tag, the typedefs and the four
   enumerators (FirmwareTypeUnknown/Bios/Uefi/Max) so phnt's later copy no
   longer collides. Only phnt's copy is renamed; the WDK's keep their names.
3. KProcessHacker.vcxproj lists nine sources but not util.c or verify.c,
   which upstream's sources.inc builds. Without them the driver cannot link
   (KphCaptureUnicodeString and others). The props add them as ClCompile
   items; the vcxproj is untouched.
4. verify.c calls BCrypt* in kernel mode. sources.inc names ksecdd.lib; the
   vcxproj names no library. The first msbuild passes ksecdd.lib, the second
   (only if no image) cng.lib, through the KphLibs property.
5. The project declares TargetVersion=Windows8; WDK 10.0.26100 rejects it and
   Windows8.1 gives MSB4044 on ValidNTTargetVersions, so Windows10 is passed.

Driver images are never packaged, signed, installed or loaded. This is a
disassembly reference only.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_PROPS = ('python -c "import base64;'
          "open('corpus-drv.props','wb').write(base64.b64decode('PFByb2plY3Q+PFByb3BlcnR5R3JvdXA+PFdob2xlUHJvZ3JhbU9wdGltaXphdGlvbj5mYWxzZTwvV2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPjxMaW5rSW5jcmVtZW50YWw+ZmFsc2U8L0xpbmtJbmNyZW1lbnRhbD48SW50RGlyPiQoT3V0RGlyKW9ialwkKFByb2plY3ROYW1lKVw8L0ludERpcj48L1Byb3BlcnR5R3JvdXA+PEl0ZW1Hcm91cD48Q2xDb21waWxlIEluY2x1ZGU9IiQoTVNCdWlsZFByb2plY3REaXJlY3RvcnkpXHV0aWwuYyIgLz48Q2xDb21waWxlIEluY2x1ZGU9IiQoTVNCdWlsZFByb2plY3REaXJlY3RvcnkpXHZlcmlmeS5jIiAvPjwvSXRlbUdyb3VwPjxJdGVtRGVmaW5pdGlvbkdyb3VwPjxDbENvbXBpbGU+PFByZXByb2Nlc3NvckRlZmluaXRpb25zPl9OVE1NQVBJX0g7JShQcmVwcm9jZXNzb3JEZWZpbml0aW9ucyk8L1ByZXByb2Nlc3NvckRlZmluaXRpb25zPjxGb3JjZWRJbmNsdWRlRmlsZXM+JChTb2x1dGlvbkRpcilrcGhfZmkuaDslKEZvcmNlZEluY2x1ZGVGaWxlcyk8L0ZvcmNlZEluY2x1ZGVGaWxlcz48T3B0aW1pemF0aW9uPk1heFNwZWVkPC9PcHRpbWl6YXRpb24+PFdob2xlUHJvZ3JhbU9wdGltaXphdGlvbj5mYWxzZTwvV2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPjxEZWJ1Z0luZm9ybWF0aW9uRm9ybWF0PlByb2dyYW1EYXRhYmFzZTwvRGVidWdJbmZvcm1hdGlvbkZvcm1hdD48UHJvZ3JhbURhdGFCYXNlRmlsZU5hbWU+JChJbnREaXIpJChQcm9qZWN0TmFtZSkuY29tcGlsZXIucGRiPC9Qcm9ncmFtRGF0YUJhc2VGaWxlTmFtZT48VHJlYXRXYXJuaW5nQXNFcnJvcj5mYWxzZTwvVHJlYXRXYXJuaW5nQXNFcnJvcj48QWRkaXRpb25hbE9wdGlvbnM+L0dMLSAlKEFkZGl0aW9uYWxPcHRpb25zKTwvQWRkaXRpb25hbE9wdGlvbnM+PC9DbENvbXBpbGU+PExpbms+PEdlbmVyYXRlRGVidWdJbmZvcm1hdGlvbj50cnVlPC9HZW5lcmF0ZURlYnVnSW5mb3JtYXRpb24+PE9wdGltaXplUmVmZXJlbmNlcz5mYWxzZTwvT3B0aW1pemVSZWZlcmVuY2VzPjxFbmFibGVDT01EQVRGb2xkaW5nPmZhbHNlPC9FbmFibGVDT01EQVRGb2xkaW5nPjxMaW5rVGltZUNvZGVHZW5lcmF0aW9uPkRlZmF1bHQ8L0xpbmtUaW1lQ29kZUdlbmVyYXRpb24+PEFkZGl0aW9uYWxEZXBlbmRlbmNpZXM+JChLcGhMaWJzKTslKEFkZGl0aW9uYWxEZXBlbmRlbmNpZXMpPC9BZGRpdGlvbmFsRGVwZW5kZW5jaWVzPjxQcm9ncmFtRGF0YWJhc2VGaWxlPiQoT3V0RGlyKSQoVGFyZ2V0TmFtZSkucGRiPC9Qcm9ncmFtRGF0YWJhc2VGaWxlPjxBZGRpdGlvbmFsT3B0aW9ucz4vQnJlcHJvIC9JTkNSRU1FTlRBTDpOTyAlKEFkZGl0aW9uYWxPcHRpb25zKTwvQWRkaXRpb25hbE9wdGlvbnM+PC9MaW5rPjxMaWI+PExpbmtUaW1lQ29kZUdlbmVyYXRpb24+ZmFsc2U8L0xpbmtUaW1lQ29kZUdlbmVyYXRpb24+PC9MaWI+PC9JdGVtRGVmaW5pdGlvbkdyb3VwPjwvUHJvamVjdD4K'))\"")

_HDR = ('python -c "import base64;'
        "open('kph_fi.h','wb').write(base64.b64decode('I2luY2x1ZGUgPG50aWZzLmg+CiNkZWZpbmUgX0ZJUk1XQVJFX1RZUEUgX1BIX0ZJUk1XQVJFX1RZUEUKI2RlZmluZSBGSVJNV0FSRV9UWVBFIFBIX0ZJUk1XQVJFX1RZUEUKI2RlZmluZSBQRklSTVdBUkVfVFlQRSBQUEhfRklSTVdBUkVfVFlQRQojZGVmaW5lIEZpcm13YXJlVHlwZVVua25vd24gUGhGaXJtd2FyZVR5cGVVbmtub3duCiNkZWZpbmUgRmlybXdhcmVUeXBlQmlvcyBQaEZpcm13YXJlVHlwZUJpb3MKI2RlZmluZSBGaXJtd2FyZVR5cGVVZWZpIFBoRmlybXdhcmVUeXBlVWVmaQojZGVmaW5lIEZpcm13YXJlVHlwZU1heCBQaEZpcm13YXJlVHlwZU1heAo='))\"")

_MSBUILD = ('msbuild KProcessHacker\\KProcessHacker.vcxproj /t:Rebuild /p:Configuration="Win8 Release" /p:Platform=x64'
            ' /p:PlatformToolset=WindowsKernelModeDriver10.0 /p:WindowsTargetPlatformVersion=10.0.26100.0'
            ' /p:TargetVersion=Windows10 /p:KphLibs={libs} /p:DriverType=WDM /p:SignMode=Off /p:SkipPackageVerification=true'
            ' /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false'
            ' /p:ForceImportBeforeCppTargets=%CD%\\corpus-drv.props /m /v:normal')

RECIPES = {
 "KProcessHacker_2.39_msvc": Recipe(
  family="KProcessHacker", version="2.39", source=Source(git_url="https://github.com/processhacker/processhacker.git", git_ref="4310de8c43f7600e344b789ffabad79b79878f6a"),
  upstream="https://github.com/processhacker/processhacker/tree/v2.39", license="GPL-3.0-or-later (source headers)", toolchains=["msvc_x64"],
  build=[BuildStep(_PROPS), BuildStep(_HDR),
   BuildStep(_MSBUILD.format(libs="ksecdd.lib"), allow_failure=True),
   BuildStep("if not exist out\\kprocesshacker.sys " + _MSBUILD.format(libs="cng.lib"), allow_failure=True),
   BuildStep("dir /s out", allow_failure=True)],
  artifacts=[Artifact(path="out/kprocesshacker.sys", component="kprocesshacker.sys", pdb="out/kprocesshacker.pdb")],
  build_flags="v2.39 Win8 Release x64; WDK 10.0.26100.0 via WindowsKernelModeDriver10.0; TargetVersion Windows10; /O2 /Zi /GL- /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO; _NTMMAPI_H guard and kph_fi.h (renames phnt's _FIRMWARE_TYPE) forced by props; util.c and verify.c added as ClCompile items; KphLibs ksecdd.lib then cng.lib; SignMode=Off",
  notes="v2.39 driver as requested by tracker #66, never current System Informer. No x86 kernel target exists in WDK 10.0.26100, so this recipe is x64 only. Kernel runtime/import residue is a measured limitation. No packaging, signing, installation or loading.",
 ),
}
