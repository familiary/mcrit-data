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

6. ROOT CAUSE of C4703 (thread.c(148), process.c(132), process.c(238)):
   the WDK header shared\warning.h line 28 is `#pragma warning(error:4703)`
   (found by the diagnostic step, run 42401510808). It is not /WX, /sdl or a
   /we switch: the cl.exe line of run 42401145014 carried /WX- /sdl- /wd4703
   (and /wd4703 again through _CL_) and the error remained, and
   WindowsDriver.Shared.Props:75 TreatWarningAsError=true is overridden by the
   props. warning.h is re-included by WDK headers, so a pragma in the forced
   include (kph_fi_*.h, after <ntifs.h>) is overridden again afterwards:
   run 42401510808 with that pragma still failed. Not yet tried: put a
   shadow shared\warning.h without that line first on the include path (a
   build-environment override, no upstream source touched), or a forced
   include that predefines warning.h's own guard if it has one. C4703 is the
   only warning at issue; the three sites are out-parameter handles assigned
   on the success path.

Driver images are never packaged, signed, installed or loaded. This is a
disassembly reference only.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_PROPS = ('python -c "import base64;'
          "open('corpus-drv.props','wb').write(base64.b64decode('PFByb2plY3Q+PFByb3BlcnR5R3JvdXA+PFdob2xlUHJvZ3JhbU9wdGltaXphdGlvbj5mYWxzZTwvV2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPjxMaW5rSW5jcmVtZW50YWw+ZmFsc2U8L0xpbmtJbmNyZW1lbnRhbD48SW50RGlyPiQoT3V0RGlyKW9ialwkKFByb2plY3ROYW1lKVw8L0ludERpcj48L1Byb3BlcnR5R3JvdXA+PEl0ZW1Hcm91cD48Q2xDb21waWxlIEluY2x1ZGU9IiQoTVNCdWlsZFByb2plY3REaXJlY3RvcnkpXHV0aWwuYyIgLz48Q2xDb21waWxlIEluY2x1ZGU9IiQoTVNCdWlsZFByb2plY3REaXJlY3RvcnkpXHZlcmlmeS5jIiAvPjwvSXRlbUdyb3VwPjxJdGVtRGVmaW5pdGlvbkdyb3VwPjxDbENvbXBpbGU+PFByZXByb2Nlc3NvckRlZmluaXRpb25zPiQoS3BoRGVmcyk7JShQcmVwcm9jZXNzb3JEZWZpbml0aW9ucyk8L1ByZXByb2Nlc3NvckRlZmluaXRpb25zPjxGb3JjZWRJbmNsdWRlRmlsZXM+JChTb2x1dGlvbkRpcikkKEtwaEZpKTslKEZvcmNlZEluY2x1ZGVGaWxlcyk8L0ZvcmNlZEluY2x1ZGVGaWxlcz48T3B0aW1pemF0aW9uPk1heFNwZWVkPC9PcHRpbWl6YXRpb24+PFdob2xlUHJvZ3JhbU9wdGltaXphdGlvbj5mYWxzZTwvV2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPjxEZWJ1Z0luZm9ybWF0aW9uRm9ybWF0PlByb2dyYW1EYXRhYmFzZTwvRGVidWdJbmZvcm1hdGlvbkZvcm1hdD48UHJvZ3JhbURhdGFCYXNlRmlsZU5hbWU+JChJbnREaXIpJChQcm9qZWN0TmFtZSkuY29tcGlsZXIucGRiPC9Qcm9ncmFtRGF0YUJhc2VGaWxlTmFtZT48VHJlYXRXYXJuaW5nQXNFcnJvcj5mYWxzZTwvVHJlYXRXYXJuaW5nQXNFcnJvcj48U0RMQ2hlY2s+ZmFsc2U8L1NETENoZWNrPjxBZGRpdGlvbmFsT3B0aW9ucz4lKEFkZGl0aW9uYWxPcHRpb25zKSAvR0wtPC9BZGRpdGlvbmFsT3B0aW9ucz48L0NsQ29tcGlsZT48TGluaz48R2VuZXJhdGVEZWJ1Z0luZm9ybWF0aW9uPnRydWU8L0dlbmVyYXRlRGVidWdJbmZvcm1hdGlvbj48T3B0aW1pemVSZWZlcmVuY2VzPmZhbHNlPC9PcHRpbWl6ZVJlZmVyZW5jZXM+PEVuYWJsZUNPTURBVEZvbGRpbmc+ZmFsc2U8L0VuYWJsZUNPTURBVEZvbGRpbmc+PExpbmtUaW1lQ29kZUdlbmVyYXRpb24+RGVmYXVsdDwvTGlua1RpbWVDb2RlR2VuZXJhdGlvbj48QWRkaXRpb25hbERlcGVuZGVuY2llcz4kKEtwaExpYnMpOyUoQWRkaXRpb25hbERlcGVuZGVuY2llcyk8L0FkZGl0aW9uYWxEZXBlbmRlbmNpZXM+PFByb2dyYW1EYXRhYmFzZUZpbGU+JChPdXREaXIpJChUYXJnZXROYW1lKS5wZGI8L1Byb2dyYW1EYXRhYmFzZUZpbGU+PEFkZGl0aW9uYWxPcHRpb25zPi9CcmVwcm8gL0lOQ1JFTUVOVEFMOk5PICUoQWRkaXRpb25hbE9wdGlvbnMpPC9BZGRpdGlvbmFsT3B0aW9ucz48L0xpbms+PExpYj48TGlua1RpbWVDb2RlR2VuZXJhdGlvbj5mYWxzZTwvTGlua1RpbWVDb2RlR2VuZXJhdGlvbj48L0xpYj48L0l0ZW1EZWZpbml0aW9uR3JvdXA+PC9Qcm9qZWN0Pgo='))\"")

_HDR_A = ('python -c "import base64;'
        "open('kph_fi_a.h','wb').write(base64.b64decode('I2luY2x1ZGUgPG50aWZzLmg+CiNkZWZpbmUgX0ZJUk1XQVJFX1RZUEUgX1BIX0ZJUk1XQVJFX1RZUEUKI2RlZmluZSBGSVJNV0FSRV9UWVBFIFBIX0ZJUk1XQVJFX1RZUEUKI2RlZmluZSBQRklSTVdBUkVfVFlQRSBQUEhfRklSTVdBUkVfVFlQRQojZGVmaW5lIEZpcm13YXJlVHlwZVVua25vd24gUGhGaXJtd2FyZVR5cGVVbmtub3duCiNkZWZpbmUgRmlybXdhcmVUeXBlQmlvcyBQaEZpcm13YXJlVHlwZUJpb3MKI2RlZmluZSBGaXJtd2FyZVR5cGVVZWZpIFBoRmlybXdhcmVUeXBlVWVmaQojZGVmaW5lIEZpcm13YXJlVHlwZU1heCBQaEZpcm13YXJlVHlwZU1heAojZGVmaW5lIF9NRU1PUllfSU5GT1JNQVRJT05fQ0xBU1MgUGhfTUVNT1JZX0lORk9STUFUSU9OX0NMQVNTCiNkZWZpbmUgTUVNT1JZX0lORk9STUFUSU9OX0NMQVNTIFBoTUVNT1JZX0lORk9STUFUSU9OX0NMQVNTCiNkZWZpbmUgTWVtb3J5QmFzaWNJbmZvcm1hdGlvbiBQaE1lbW9yeUJhc2ljSW5mb3JtYXRpb24KI2RlZmluZSBfVklSVFVBTF9NRU1PUllfSU5GT1JNQVRJT05fQ0xBU1MgUGhfVklSVFVBTF9NRU1PUllfSU5GT1JNQVRJT05fQ0xBU1MKI2RlZmluZSBWSVJUVUFMX01FTU9SWV9JTkZPUk1BVElPTl9DTEFTUyBQaFZJUlRVQUxfTUVNT1JZX0lORk9STUFUSU9OX0NMQVNTCiNkZWZpbmUgVm1QcmVmZXRjaEluZm9ybWF0aW9uIFBoVm1QcmVmZXRjaEluZm9ybWF0aW9uCiNkZWZpbmUgVm1QYWdlUHJpb3JpdHlJbmZvcm1hdGlvbiBQaFZtUGFnZVByaW9yaXR5SW5mb3JtYXRpb24KI2RlZmluZSBWbUNmZ0NhbGxUYXJnZXRJbmZvcm1hdGlvbiBQaFZtQ2ZnQ2FsbFRhcmdldEluZm9ybWF0aW9uCiNkZWZpbmUgX01FTU9SWV9SQU5HRV9FTlRSWSBQaF9NRU1PUllfUkFOR0VfRU5UUlkKI2RlZmluZSBNRU1PUllfUkFOR0VfRU5UUlkgUGhNRU1PUllfUkFOR0VfRU5UUlkKI2RlZmluZSBQTUVNT1JZX1JBTkdFX0VOVFJZIFBoUE1FTU9SWV9SQU5HRV9FTlRSWQojZGVmaW5lIF9NRU1PUllfQkFTSUNfSU5GT1JNQVRJT04gUGhfTUVNT1JZX0JBU0lDX0lORk9STUFUSU9OCiNkZWZpbmUgTUVNT1JZX0JBU0lDX0lORk9STUFUSU9OIFBoTUVNT1JZX0JBU0lDX0lORk9STUFUSU9OCiNkZWZpbmUgUE1FTU9SWV9CQVNJQ19JTkZPUk1BVElPTiBQaFBNRU1PUllfQkFTSUNfSU5GT1JNQVRJT04KI2RlZmluZSBfTUVNT1JZX1BBUlRJVElPTl9JTkZPUk1BVElPTl9DTEFTUyBQaF9NRU1PUllfUEFSVElUSU9OX0lORk9STUFUSU9OX0NMQVNTCiNkZWZpbmUgTUVNT1JZX1BBUlRJVElPTl9JTkZPUk1BVElPTl9DTEFTUyBQaE1FTU9SWV9QQVJUSVRJT05fSU5GT1JNQVRJT05fQ0xBU1MKI2RlZmluZSBTeXN0ZW1NZW1vcnlQYXJ0aXRpb25JbmZvcm1hdGlvbiBQaFN5c3RlbU1lbW9yeVBhcnRpdGlvbkluZm9ybWF0aW9uCiNkZWZpbmUgU3lzdGVtTWVtb3J5UGFydGl0aW9uTW92ZU1lbW9yeSBQaFN5c3RlbU1lbW9yeVBhcnRpdGlvbk1vdmVNZW1vcnkKI2RlZmluZSBTeXN0ZW1NZW1vcnlQYXJ0aXRpb25BZGRQYWdlZmlsZSBQaFN5c3RlbU1lbW9yeVBhcnRpdGlvbkFkZFBhZ2VmaWxlCiNkZWZpbmUgU3lzdGVtTWVtb3J5UGFydGl0aW9uQ29tYmluZU1lbW9yeSBQaFN5c3RlbU1lbW9yeVBhcnRpdGlvbkNvbWJpbmVNZW1vcnkKI3ByYWdtYSB3YXJuaW5nKGRpc2FibGU6NDcwMykK'))\"")

_HDR_B = ('python -c "import base64;'
        "open('kph_fi_b.h','wb').write(base64.b64decode('I2luY2x1ZGUgPG50aWZzLmg+CiNkZWZpbmUgX0ZJUk1XQVJFX1RZUEUgX1BIX0ZJUk1XQVJFX1RZUEUKI2RlZmluZSBGSVJNV0FSRV9UWVBFIFBIX0ZJUk1XQVJFX1RZUEUKI2RlZmluZSBQRklSTVdBUkVfVFlQRSBQUEhfRklSTVdBUkVfVFlQRQojZGVmaW5lIEZpcm13YXJlVHlwZVVua25vd24gUGhGaXJtd2FyZVR5cGVVbmtub3duCiNkZWZpbmUgRmlybXdhcmVUeXBlQmlvcyBQaEZpcm13YXJlVHlwZUJpb3MKI2RlZmluZSBGaXJtd2FyZVR5cGVVZWZpIFBoRmlybXdhcmVUeXBlVWVmaQojZGVmaW5lIEZpcm13YXJlVHlwZU1heCBQaEZpcm13YXJlVHlwZU1heAojZGVmaW5lIE1FTV9JTUFHRSBTRUNfSU1BR0UKI2RlZmluZSBNZW1vcnlNYXBwZWRGaWxlbmFtZUluZm9ybWF0aW9uIDIKI3ByYWdtYSB3YXJuaW5nKGRpc2FibGU6NDcwMykK'))\"")

_DIAG = ('python -c "import base64;'
        "open('diag.py','wb').write(base64.b64decode('CmltcG9ydCByZSxvcyx0ZXh0d3JhcApkZWYgUChzKToKICAgIHByaW50KHNbOjMwMF0pCmRlZiB0YWlsKHBhdGgscGF0LG4pOgogICAgaWYgbm90IG9zLnBhdGguZXhpc3RzKHBhdGgpOgogICAgICAgIFAoJ05PRklMRSAnK3BhdGgpOyByZXR1cm4KICAgIGs9MAogICAgZm9yIGwgaW4gb3BlbihwYXRoLGVycm9ycz0ncmVwbGFjZScpLnJlYWQoKS5zcGxpdGxpbmVzKCk6CiAgICAgICAgaWYgcmUuc2VhcmNoKHBhdCxsKToKICAgICAgICAgICAgUChwYXRoKyc6ICcrbC5zdHJpcCgpKTsgays9MQogICAgICAgICAgICBpZiBrPj1uOiBicmVhawogICAgaWYgaz09MDogUChwYXRoKyc6IG5vIG1hdGNoJykKZm9yIGYgaW4gKCdtc2JfYS5sb2cnLCdtc2JfYi5sb2cnLCdtc2JfYy5sb2cnLCdtc2JfZC5sb2cnKToKICAgIHRhaWwoZixyJ2Vycm9yIFtBLVpdK1xkKycsMykKaWYgb3MucGF0aC5leGlzdHMoJ21zYl9hLmxvZycpOgogICAgZm9yIGwgaW4gb3BlbignbXNiX2EubG9nJyxlcnJvcnM9J3JlcGxhY2UnKS5yZWFkKCkuc3BsaXRsaW5lcygpOgogICAgICAgIGlmICdDTC5leGUnIGluIGwgYW5kICcvRm8nIGluIGw6CiAgICAgICAgICAgIHQ9W3ggZm9yIHggaW4gbC5zcGxpdCgpIGlmIHJlLm1hdGNoKHInXlsvLV0oc2RsLT98d2VcZCt8d2RcZCt8V1gtP3xXXGR8d1xkK3xrZXJuZWx8T1xTKnxHTC0/fEdTLT98Z3VhcmRcUyp8ZFxkXFMqfFpcUyp8TUR8TVR8Y2JzdHJpbmd8YW5hbHl6ZVxTKikkJyx4KV0KICAgICAgICAgICAgZm9yIGxuIGluIHRleHR3cmFwLndyYXAoJ0NMRkxBR1MgJysnICcuam9pbih0KSwyODApOiBQKGxuKQogICAgICAgICAgICBicmVhawpyb290cz1bcidDOlxQcm9ncmFtIEZpbGVzICh4ODYpXFdpbmRvd3MgS2l0c1wxMFxidWlsZFwxMC4wLjI2MTAwLjAnLHInQzpcUHJvZ3JhbSBGaWxlc1xNaWNyb3NvZnQgVmlzdWFsIFN0dWRpb1wyMDIyXEVudGVycHJpc2VcTVNCdWlsZFxNaWNyb3NvZnRcVkNcdjE3MFxQbGF0Zm9ybXNceDY0XFBsYXRmb3JtVG9vbHNldHNcV2luZG93c0tlcm5lbE1vZGVEcml2ZXIxMC4wJ10Kaz0wCmZvciByIGluIHJvb3RzOgogICAgZm9yIGQsXyxmcyBpbiBvcy53YWxrKHIpOgogICAgICAgIGZvciBmIGluIGZzOgogICAgICAgICAgICBpZiBmLmxvd2VyKCkuZW5kc3dpdGgoKCcucHJvcHMnLCcudGFyZ2V0cycpKToKICAgICAgICAgICAgICAgIHA9b3MucGF0aC5qb2luKGQsZikKICAgICAgICAgICAgICAgIGZvciBpLGwgaW4gZW51bWVyYXRlKG9wZW4ocCxlcnJvcnM9J3JlcGxhY2UnKS5yZWFkKCkuc3BsaXRsaW5lcygpKToKICAgICAgICAgICAgICAgICAgICBpZiByZS5zZWFyY2gocic0NzAzfFRyZWF0U3BlY2lmaWNXYXJuaW5nc0FzRXJyb3JzfC9zZGx8U0RMQ2hlY2t8L1dYfFRyZWF0V2FybmluZ0FzRXJyb3J8L3dlXGQnLGwpOgogICAgICAgICAgICAgICAgICAgICAgICBpZiBrPDMwOiBQKCdXREsgJytwLnNwbGl0KCcxMC4wLjI2MTAwLjAnKVstMV0uc3BsaXQoJ1dpbmRvd3NLZXJuZWxNb2RlRHJpdmVyMTAuMCcpWy0xXSsnOicrc3RyKGkrMSkrJzogJytsLnN0cmlwKCkpOyBrKz0xCgprPTAKZm9yIHIgaW4gKHInQzpcUHJvZ3JhbSBGaWxlcyAoeDg2KVxXaW5kb3dzIEtpdHNcMTBcSW5jbHVkZVwxMC4wLjI2MTAwLjBca20nLHInQzpcUHJvZ3JhbSBGaWxlcyAoeDg2KVxXaW5kb3dzIEtpdHNcMTBcSW5jbHVkZVwxMC4wLjI2MTAwLjBcc2hhcmVkJyk6CiAgICBmb3IgZCxfLGZzIGluIG9zLndhbGsocik6CiAgICAgICAgZm9yIGYgaW4gZnM6CiAgICAgICAgICAgIGlmIGYubG93ZXIoKS5lbmRzd2l0aCgnLmgnKToKICAgICAgICAgICAgICAgIHA9b3MucGF0aC5qb2luKGQsZikKICAgICAgICAgICAgICAgIGZvciBpLGwgaW4gZW51bWVyYXRlKG9wZW4ocCxlcnJvcnM9J3JlcGxhY2UnKS5yZWFkKCkuc3BsaXRsaW5lcygpKToKICAgICAgICAgICAgICAgICAgICBpZiAnNDcwMycgaW4gbCBhbmQgazwyMDoKICAgICAgICAgICAgICAgICAgICAgICAgUCgnSU5DICcrcC5zcGxpdCgnMTAuMC4yNjEwMC4wJylbLTFdKyc6JytzdHIoaSsxKSsnOiAnK2wuc3RyaXAoKSk7IGsrPTEK'))\"")

_MSBUILD = ('msbuild KProcessHacker\\KProcessHacker.vcxproj /t:Rebuild /p:Configuration="Win8 Release" /p:Platform=x64'
            ' /p:PlatformToolset=WindowsKernelModeDriver10.0 /p:WindowsTargetPlatformVersion=10.0.26100.0'
            ' /p:TargetVersion=Windows10 /p:KphLibs={libs} /p:KphFi={fi} /p:KphDefs={defs} /p:DriverType=WDM /p:SignMode=Off /p:SkipPackageVerification=true'
            ' /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false'
            ' /p:ForceImportBeforeCppTargets=%CD%\\corpus-drv.props /m /v:normal /flp:logfile={log};{lv}')

RECIPES = {
 "KProcessHacker_2.39_msvc": Recipe(
  family="KProcessHacker", version="2.39", source=Source(git_url="https://github.com/processhacker/processhacker.git", git_ref="4310de8c43f7600e344b789ffabad79b79878f6a"),
  upstream="https://github.com/processhacker/processhacker/tree/v2.39", license="GPL-3.0-or-later (source headers)", toolchains=["msvc_x64"],
  build=[BuildStep(_PROPS), BuildStep(_HDR_A), BuildStep(_HDR_B), BuildStep(_DIAG),
   BuildStep("echo ATTEMPT-A ksecdd rename, pragma only"),
   BuildStep(_MSBUILD.format(libs="ksecdd.lib", fi="kph_fi_a.h", defs="KPH_X", log="msb_a.log", lv="verbosity=detailed"), allow_failure=True),
   BuildStep("echo ATTEMPT-B ksecdd rename, pragma only"),
   BuildStep("if not exist out\\kprocesshacker.sys " + _MSBUILD.format(libs="ksecdd.lib", fi="kph_fi_a.h", defs="KPH_X", log="msb_b.log", lv="errorsonly;verbosity=quiet"), allow_failure=True),
   BuildStep("echo ATTEMPT-C ksecdd guard, pragma only"),
   BuildStep("if not exist out\\kprocesshacker.sys " + _MSBUILD.format(libs="ksecdd.lib", fi="kph_fi_b.h", defs="_NTMMAPI_H", log="msb_c.log", lv="errorsonly;verbosity=quiet"), allow_failure=True),
   BuildStep("echo ATTEMPT-D cng rename, pragma only"),
   BuildStep("if not exist out\\kprocesshacker.sys " + _MSBUILD.format(libs="cng.lib", fi="kph_fi_a.h", defs="KPH_X", log="msb_d.log", lv="errorsonly;verbosity=quiet"), allow_failure=True),
   BuildStep("python diag.py", allow_failure=True),
   BuildStep("dir /b /s out\\*.sys out\\*.pdb", allow_failure=True)],
  artifacts=[Artifact(path="out/kprocesshacker.sys", component="kprocesshacker.sys", pdb="out/kprocesshacker.pdb")],
  build_flags="v2.39 Win8 Release x64; WDK 10.0.26100.0 via WindowsKernelModeDriver10.0; TargetVersion Windows10; /O2 /Zi /GL- /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO; _NTMMAPI_H guard and kph_fi.h (renames phnt's _FIRMWARE_TYPE) forced by props; util.c and verify.c added as ClCompile items; KphLibs ksecdd.lib then cng.lib; SignMode=Off; warning C4703 only downgraded, by #pragma warning(disable:4703) appended to the forced-include kph_fi_*.h after <ntifs.h>",
  notes="v2.39 driver as requested by tracker #66, never current System Informer. No x86 kernel target exists in WDK 10.0.26100, so this recipe is x64 only. Kernel runtime/import residue is a measured limitation. No packaging, signing, installation or loading.",
 ),
}
