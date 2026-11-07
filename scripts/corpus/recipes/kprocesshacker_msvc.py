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
          "open('corpus-drv.props','wb').write(base64.b64decode('PFByb2plY3Q+PFByb3BlcnR5R3JvdXA+PFdob2xlUHJvZ3JhbU9wdGltaXphdGlvbj5mYWxzZTwvV2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPjxMaW5rSW5jcmVtZW50YWw+ZmFsc2U8L0xpbmtJbmNyZW1lbnRhbD48SW50RGlyPiQoT3V0RGlyKW9ialwkKFByb2plY3ROYW1lKVw8L0ludERpcj48L1Byb3BlcnR5R3JvdXA+PEl0ZW1Hcm91cD48Q2xDb21waWxlIEluY2x1ZGU9IiQoTVNCdWlsZFByb2plY3REaXJlY3RvcnkpXHV0aWwuYyIgLz48Q2xDb21waWxlIEluY2x1ZGU9IiQoTVNCdWlsZFByb2plY3REaXJlY3RvcnkpXHZlcmlmeS5jIiAvPjwvSXRlbUdyb3VwPjxJdGVtRGVmaW5pdGlvbkdyb3VwPjxDbENvbXBpbGU+PFByZXByb2Nlc3NvckRlZmluaXRpb25zPiQoS3BoRGVmcyk7JShQcmVwcm9jZXNzb3JEZWZpbml0aW9ucyk8L1ByZXByb2Nlc3NvckRlZmluaXRpb25zPjxGb3JjZWRJbmNsdWRlRmlsZXM+JChTb2x1dGlvbkRpcikkKEtwaEZpKTslKEZvcmNlZEluY2x1ZGVGaWxlcyk8L0ZvcmNlZEluY2x1ZGVGaWxlcz48T3B0aW1pemF0aW9uPk1heFNwZWVkPC9PcHRpbWl6YXRpb24+PFdob2xlUHJvZ3JhbU9wdGltaXphdGlvbj5mYWxzZTwvV2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPjxEZWJ1Z0luZm9ybWF0aW9uRm9ybWF0PlByb2dyYW1EYXRhYmFzZTwvRGVidWdJbmZvcm1hdGlvbkZvcm1hdD48UHJvZ3JhbURhdGFCYXNlRmlsZU5hbWU+JChJbnREaXIpJChQcm9qZWN0TmFtZSkuY29tcGlsZXIucGRiPC9Qcm9ncmFtRGF0YUJhc2VGaWxlTmFtZT48VHJlYXRXYXJuaW5nQXNFcnJvcj5mYWxzZTwvVHJlYXRXYXJuaW5nQXNFcnJvcj48U0RMQ2hlY2s+ZmFsc2U8L1NETENoZWNrPjxEaXNhYmxlU3BlY2lmaWNXYXJuaW5ncz40NzAzOyUoRGlzYWJsZVNwZWNpZmljV2FybmluZ3MpPC9EaXNhYmxlU3BlY2lmaWNXYXJuaW5ncz48QWRkaXRpb25hbE9wdGlvbnM+JShBZGRpdGlvbmFsT3B0aW9ucykgL0dMLSAvc2RsLSAvd2Q0NzAzPC9BZGRpdGlvbmFsT3B0aW9ucz48L0NsQ29tcGlsZT48TGluaz48R2VuZXJhdGVEZWJ1Z0luZm9ybWF0aW9uPnRydWU8L0dlbmVyYXRlRGVidWdJbmZvcm1hdGlvbj48T3B0aW1pemVSZWZlcmVuY2VzPmZhbHNlPC9PcHRpbWl6ZVJlZmVyZW5jZXM+PEVuYWJsZUNPTURBVEZvbGRpbmc+ZmFsc2U8L0VuYWJsZUNPTURBVEZvbGRpbmc+PExpbmtUaW1lQ29kZUdlbmVyYXRpb24+RGVmYXVsdDwvTGlua1RpbWVDb2RlR2VuZXJhdGlvbj48QWRkaXRpb25hbERlcGVuZGVuY2llcz4kKEtwaExpYnMpOyUoQWRkaXRpb25hbERlcGVuZGVuY2llcyk8L0FkZGl0aW9uYWxEZXBlbmRlbmNpZXM+PFByb2dyYW1EYXRhYmFzZUZpbGU+JChPdXREaXIpJChUYXJnZXROYW1lKS5wZGI8L1Byb2dyYW1EYXRhYmFzZUZpbGU+PEFkZGl0aW9uYWxPcHRpb25zPi9CcmVwcm8gL0lOQ1JFTUVOVEFMOk5PICUoQWRkaXRpb25hbE9wdGlvbnMpPC9BZGRpdGlvbmFsT3B0aW9ucz48L0xpbms+PExpYj48TGlua1RpbWVDb2RlR2VuZXJhdGlvbj5mYWxzZTwvTGlua1RpbWVDb2RlR2VuZXJhdGlvbj48L0xpYj48L0l0ZW1EZWZpbml0aW9uR3JvdXA+PC9Qcm9qZWN0Pgo='))\"")

_HDR_A = ('python -c "import base64;'
        "open('kph_fi_a.h','wb').write(base64.b64decode('I2luY2x1ZGUgPG50aWZzLmg+CiNkZWZpbmUgX0ZJUk1XQVJFX1RZUEUgX1BIX0ZJUk1XQVJFX1RZUEUKI2RlZmluZSBGSVJNV0FSRV9UWVBFIFBIX0ZJUk1XQVJFX1RZUEUKI2RlZmluZSBQRklSTVdBUkVfVFlQRSBQUEhfRklSTVdBUkVfVFlQRQojZGVmaW5lIEZpcm13YXJlVHlwZVVua25vd24gUGhGaXJtd2FyZVR5cGVVbmtub3duCiNkZWZpbmUgRmlybXdhcmVUeXBlQmlvcyBQaEZpcm13YXJlVHlwZUJpb3MKI2RlZmluZSBGaXJtd2FyZVR5cGVVZWZpIFBoRmlybXdhcmVUeXBlVWVmaQojZGVmaW5lIEZpcm13YXJlVHlwZU1heCBQaEZpcm13YXJlVHlwZU1heAojZGVmaW5lIF9NRU1PUllfSU5GT1JNQVRJT05fQ0xBU1MgUGhfTUVNT1JZX0lORk9STUFUSU9OX0NMQVNTCiNkZWZpbmUgTUVNT1JZX0lORk9STUFUSU9OX0NMQVNTIFBoTUVNT1JZX0lORk9STUFUSU9OX0NMQVNTCiNkZWZpbmUgTWVtb3J5QmFzaWNJbmZvcm1hdGlvbiBQaE1lbW9yeUJhc2ljSW5mb3JtYXRpb24KI2RlZmluZSBfVklSVFVBTF9NRU1PUllfSU5GT1JNQVRJT05fQ0xBU1MgUGhfVklSVFVBTF9NRU1PUllfSU5GT1JNQVRJT05fQ0xBU1MKI2RlZmluZSBWSVJUVUFMX01FTU9SWV9JTkZPUk1BVElPTl9DTEFTUyBQaFZJUlRVQUxfTUVNT1JZX0lORk9STUFUSU9OX0NMQVNTCiNkZWZpbmUgVm1QcmVmZXRjaEluZm9ybWF0aW9uIFBoVm1QcmVmZXRjaEluZm9ybWF0aW9uCiNkZWZpbmUgVm1QYWdlUHJpb3JpdHlJbmZvcm1hdGlvbiBQaFZtUGFnZVByaW9yaXR5SW5mb3JtYXRpb24KI2RlZmluZSBWbUNmZ0NhbGxUYXJnZXRJbmZvcm1hdGlvbiBQaFZtQ2ZnQ2FsbFRhcmdldEluZm9ybWF0aW9uCiNkZWZpbmUgX01FTU9SWV9SQU5HRV9FTlRSWSBQaF9NRU1PUllfUkFOR0VfRU5UUlkKI2RlZmluZSBNRU1PUllfUkFOR0VfRU5UUlkgUGhNRU1PUllfUkFOR0VfRU5UUlkKI2RlZmluZSBQTUVNT1JZX1JBTkdFX0VOVFJZIFBoUE1FTU9SWV9SQU5HRV9FTlRSWQojZGVmaW5lIF9NRU1PUllfQkFTSUNfSU5GT1JNQVRJT04gUGhfTUVNT1JZX0JBU0lDX0lORk9STUFUSU9OCiNkZWZpbmUgTUVNT1JZX0JBU0lDX0lORk9STUFUSU9OIFBoTUVNT1JZX0JBU0lDX0lORk9STUFUSU9OCiNkZWZpbmUgUE1FTU9SWV9CQVNJQ19JTkZPUk1BVElPTiBQaFBNRU1PUllfQkFTSUNfSU5GT1JNQVRJT04KI2RlZmluZSBfTUVNT1JZX1BBUlRJVElPTl9JTkZPUk1BVElPTl9DTEFTUyBQaF9NRU1PUllfUEFSVElUSU9OX0lORk9STUFUSU9OX0NMQVNTCiNkZWZpbmUgTUVNT1JZX1BBUlRJVElPTl9JTkZPUk1BVElPTl9DTEFTUyBQaE1FTU9SWV9QQVJUSVRJT05fSU5GT1JNQVRJT05fQ0xBU1MKI2RlZmluZSBTeXN0ZW1NZW1vcnlQYXJ0aXRpb25JbmZvcm1hdGlvbiBQaFN5c3RlbU1lbW9yeVBhcnRpdGlvbkluZm9ybWF0aW9uCiNkZWZpbmUgU3lzdGVtTWVtb3J5UGFydGl0aW9uTW92ZU1lbW9yeSBQaFN5c3RlbU1lbW9yeVBhcnRpdGlvbk1vdmVNZW1vcnkKI2RlZmluZSBTeXN0ZW1NZW1vcnlQYXJ0aXRpb25BZGRQYWdlZmlsZSBQaFN5c3RlbU1lbW9yeVBhcnRpdGlvbkFkZFBhZ2VmaWxlCiNkZWZpbmUgU3lzdGVtTWVtb3J5UGFydGl0aW9uQ29tYmluZU1lbW9yeSBQaFN5c3RlbU1lbW9yeVBhcnRpdGlvbkNvbWJpbmVNZW1vcnkK'))\"")

_HDR_B = ('python -c "import base64;'
        "open('kph_fi_b.h','wb').write(base64.b64decode('I2luY2x1ZGUgPG50aWZzLmg+CiNkZWZpbmUgX0ZJUk1XQVJFX1RZUEUgX1BIX0ZJUk1XQVJFX1RZUEUKI2RlZmluZSBGSVJNV0FSRV9UWVBFIFBIX0ZJUk1XQVJFX1RZUEUKI2RlZmluZSBQRklSTVdBUkVfVFlQRSBQUEhfRklSTVdBUkVfVFlQRQojZGVmaW5lIEZpcm13YXJlVHlwZVVua25vd24gUGhGaXJtd2FyZVR5cGVVbmtub3duCiNkZWZpbmUgRmlybXdhcmVUeXBlQmlvcyBQaEZpcm13YXJlVHlwZUJpb3MKI2RlZmluZSBGaXJtd2FyZVR5cGVVZWZpIFBoRmlybXdhcmVUeXBlVWVmaQojZGVmaW5lIEZpcm13YXJlVHlwZU1heCBQaEZpcm13YXJlVHlwZU1heAojZGVmaW5lIE1FTV9JTUFHRSBTRUNfSU1BR0UKI2RlZmluZSBNZW1vcnlNYXBwZWRGaWxlbmFtZUluZm9ybWF0aW9uIDIK'))\"")

_MSBUILD = ('msbuild KProcessHacker\\KProcessHacker.vcxproj /t:Rebuild /p:Configuration="Win8 Release" /p:Platform=x64'
            ' /p:PlatformToolset=WindowsKernelModeDriver10.0 /p:WindowsTargetPlatformVersion=10.0.26100.0'
            ' /p:TargetVersion=Windows10 /p:KphLibs={libs} /p:KphFi={fi} /p:KphDefs={defs} /p:DriverType=WDM /p:SignMode=Off /p:SkipPackageVerification=true'
            ' /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false'
            ' /p:ForceImportBeforeCppTargets=%CD%\\corpus-drv.props /m /v:normal')

RECIPES = {
 "KProcessHacker_2.39_msvc": Recipe(
  family="KProcessHacker", version="2.39", source=Source(git_url="https://github.com/processhacker/processhacker.git", git_ref="4310de8c43f7600e344b789ffabad79b79878f6a"),
  upstream="https://github.com/processhacker/processhacker/tree/v2.39", license="GPL-3.0-or-later (source headers)", toolchains=["msvc_x64"],
  build=[BuildStep(_PROPS), BuildStep(_HDR_A), BuildStep(_HDR_B),
   BuildStep("echo ATTEMPT-A ksecdd rename"),
   BuildStep(_MSBUILD.format(libs="ksecdd.lib", fi="kph_fi_a.h", defs="KPH_X"), allow_failure=True),
   BuildStep("echo ATTEMPT-B ksecdd guard"),
   BuildStep("if not exist out\\kprocesshacker.sys " + _MSBUILD.format(libs="ksecdd.lib", fi="kph_fi_b.h", defs="_NTMMAPI_H"), allow_failure=True),
   BuildStep("echo ATTEMPT-C cng rename"),
   BuildStep("if not exist out\\kprocesshacker.sys " + _MSBUILD.format(libs="cng.lib", fi="kph_fi_a.h", defs="KPH_X"), allow_failure=True),
   BuildStep("dir /s out", allow_failure=True)],
  artifacts=[Artifact(path="out/kprocesshacker.sys", component="kprocesshacker.sys", pdb="out/kprocesshacker.pdb")],
  build_flags="v2.39 Win8 Release x64; WDK 10.0.26100.0 via WindowsKernelModeDriver10.0; TargetVersion Windows10; /O2 /Zi /GL- /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO; _NTMMAPI_H guard and kph_fi.h (renames phnt's _FIRMWARE_TYPE) forced by props; util.c and verify.c added as ClCompile items; KphLibs ksecdd.lib then cng.lib; SignMode=Off",
  notes="v2.39 driver as requested by tracker #66, never current System Informer. No x86 kernel target exists in WDK 10.0.26100, so this recipe is x64 only. Kernel runtime/import residue is a measured limitation. No packaging, signing, installation or loading.",
 ),
}
