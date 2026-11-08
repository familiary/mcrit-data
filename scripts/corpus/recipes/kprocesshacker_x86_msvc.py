"""Process Hacker v2.39 KProcessHacker driver, x86 build.

The x86 half of ``KProcessHacker_2.39_msvc`` (x64, WDK 10.0.26100.0, which has no
x86 kernel target). Same pinned source (commit 4310de8c43f7600e344b789ffabad79b79878f6a).
It is a recipe of its own for the same reason as ``DiskCryptorDrv_1.1.846.118_msvc_x86``:
``refresh_provenance.py`` separates the two images by the toolchain in the slug.

Route (the one DiskCryptorDrv and WinPmemDrv x86 use):

* ``scripts/corpus/install_wdk_x86.py`` installs WDK 10.0.22621 (stub pinned by
  sha256 f3948d1486f8a7821bcef431487d3893fcd3a053d97ab37a1333a0c26e0bd232)
  beside the runner's 10.0.26100.0; it is the last kit with Lib\\km\\x86.
* Its msbuild toolset rejects Win32 too (WindowsDriver.common.targets(235,5):
  'Win32' is not a valid architecture for Kernel mode drivers or UMDF drivers),
  so KProcessHacker.vcxproj, Win8 Release|Win32, is built with PlatformToolset=v143
  and ConfigurationType=Application (command-line globals override the
  project's WindowsKernelModeDriver8.0 / Driver), TargetExt=.sys, and the forced
  props turn it into a driver: /kernel /Gz /MD /GL-, the 22621 km, km\\crt and
  shared includes, _KERNEL_MODE and the Windows 10 NTDDI/WINNT defines, /DRIVER:WDM
  /SUBSYSTEM:NATIVE /NODEFAULTLIB /ENTRY:GsDriverEntry@8 /SAFESEH:NO, the km\\x86
  library directory, ntoskrnl.lib hal.lib BufferOverflowFastFailK.lib libcntpr.lib
  plus ksecdd.lib (or cng.lib in the last attempt), and /OPT:NOREF /OPT:NOICF
  /Brepro /INCREMENTAL:NO. These are the same settings the x86 kernel-mode probes
  of the glue baseline use, so the baseline matches this image.

Obstacles carried over from the x64 recipe, handled the same way (no upstream
file is edited for them):

1. kph.h includes <ntifs.h> before phnt: the force-included kph_fi_a.h (or the
   smaller kph_fi_b.h with the _NTMMAPI_H define) renames phnt's duplicate
   _FIRMWARE_TYPE (phnt/include/ntexapi.h(2009,14) C2011) and the memory
   information types.
2. util.c and verify.c are not in the vcxproj but are in upstream's sources.inc:
   added as ClCompile items by the props.
3. verify.c calls BCrypt*: ksecdd.lib, then cng.lib.

Patching policy, because the x64 image needed it: nothing is patched unless the
unpatched attempts produce no image. The first three attempts run on the
untouched tree. Only if none produces out\\kprocesshacker.sys, ``patch.py`` runs
and the same three attempts are repeated: it initialises three out-parameter
handles at build time (thread.c:85 ``HANDLE threadHandle;``, process.c:64
``HANDLE processHandle;``, process.c:175 ``HANDLE tokenHandle;`` each become
``= NULL;``, the exact asserted lines of the x64 recipe) and, if the kit's
shared\\warning.h has a ``#pragma warning(error:4703)`` line, copies it without
that line to shadow\\warning.h, first on the include path. The build log says
which attempt produced the image and whether PATCHED / SHADOW lines were printed.
If the image comes from the patched phase it is NOT byte-identical to a build of
unmodified upstream; the provenance notes and README row say which phase it was.

The WDK 10.0.22621 payload is downloaded by the installer stub at build time and
is not pinned beyond the stub's version and sha256. The driver is linked and
disassembled only, never packaged, signed, installed or loaded.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_KIT = "10.0.22621.0"


def _w(name, b64):
    return BuildStep('python -c "import base64;open(\'%s\',\'wb\').write(base64.b64decode(\'%s\'))"' % (name, b64))


_MSBUILD = ('msbuild KProcessHacker\\KProcessHacker.vcxproj /t:Rebuild /p:Configuration="Win8 Release" /p:Platform={msbuild_platform}'
            ' /p:PlatformToolset=v143 /p:ConfigurationType=Application /p:TargetExt=.sys /p:GenerateManifest=false'
            ' /p:WindowsTargetPlatformVersion=' + _KIT + ' /p:KphLibs=@LIBS@ /p:KphFi=@FI@ /p:KphDefs=@DEFS@ /p:KphShadow=%CD%\\shadow'
            ' /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false'
            ' /p:ForceImportBeforeCppTargets=%CD%\\corpus-drv.props /m /v:minimal /flp:logfile=@LOG@;errorsonly')

_TRIES = (("a", "ksecdd.lib", "kph_fi_a.h", "KPH_X"),
          ("b", "ksecdd.lib", "kph_fi_b.h", "_NTMMAPI_H"),
          ("c", "cng.lib", "kph_fi_a.h", "KPH_X"))


def _attempt(phase, tag, libs, fi, defs):
    command = (_MSBUILD.replace("@LIBS@", libs).replace("@FI@", fi).replace("@DEFS@", defs)
               .replace("@LOG@", "msb_%s%s.log" % (phase, tag)))
    return [BuildStep("echo ATTEMPT-%s%s libs=%s fi=%s defs=%s" % (phase, tag, libs, fi, defs)),
            BuildStep("if not exist out\\kprocesshacker.sys " + command, allow_failure=True)]


def _steps():
    steps = [BuildStep('python "{repo}/scripts/corpus/install_wdk_x86.py"'),
             _w("corpus-drv.props", "PFByb2plY3Q+PFByb3BlcnR5R3JvdXA+PFdob2xlUHJvZ3JhbU9wdGltaXphdGlvbj5mYWxzZTwvV2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPjxMaW5rSW5jcmVtZW50YWw+ZmFsc2U8L0xpbmtJbmNyZW1lbnRhbD48SW50RGlyPiQoT3V0RGlyKW9ialwkKFByb2plY3ROYW1lKVw8L0ludERpcj48L1Byb3BlcnR5R3JvdXA+PEl0ZW1Hcm91cD48Q2xDb21waWxlIEluY2x1ZGU9IiQoTVNCdWlsZFByb2plY3REaXJlY3RvcnkpXHV0aWwuYyIgLz48Q2xDb21waWxlIEluY2x1ZGU9IiQoTVNCdWlsZFByb2plY3REaXJlY3RvcnkpXHZlcmlmeS5jIiAvPjwvSXRlbUdyb3VwPjxJdGVtRGVmaW5pdGlvbkdyb3VwPjxDbENvbXBpbGU+PEFkZGl0aW9uYWxJbmNsdWRlRGlyZWN0b3JpZXM+JChLcGhTaGFkb3cpOyQoV2luZG93c1Nka0RpcilJbmNsdWRlXCQoV2luZG93c1RhcmdldFBsYXRmb3JtVmVyc2lvbilca207JChXaW5kb3dzU2RrRGlyKUluY2x1ZGVcJChXaW5kb3dzVGFyZ2V0UGxhdGZvcm1WZXJzaW9uKVxrbVxjcnQ7JChXaW5kb3dzU2RrRGlyKUluY2x1ZGVcJChXaW5kb3dzVGFyZ2V0UGxhdGZvcm1WZXJzaW9uKVxzaGFyZWQ7JShBZGRpdGlvbmFsSW5jbHVkZURpcmVjdG9yaWVzKTwvQWRkaXRpb25hbEluY2x1ZGVEaXJlY3Rvcmllcz48UHJlcHJvY2Vzc29yRGVmaW5pdGlvbnM+JChLcGhEZWZzKTtfS0VSTkVMX01PREU7TlRERElfVkVSU0lPTj0weDBBMDAwMDAwO19XSU4zMl9XSU5OVD0weDBBMDA7V0lOVkVSPTB4MEEwMDslKFByZXByb2Nlc3NvckRlZmluaXRpb25zKTwvUHJlcHJvY2Vzc29yRGVmaW5pdGlvbnM+PEZvcmNlZEluY2x1ZGVGaWxlcz4kKFNvbHV0aW9uRGlyKSQoS3BoRmkpOyUoRm9yY2VkSW5jbHVkZUZpbGVzKTwvRm9yY2VkSW5jbHVkZUZpbGVzPjxSdW50aW1lTGlicmFyeT5NdWx0aVRocmVhZGVkRExMPC9SdW50aW1lTGlicmFyeT48Q2FsbGluZ0NvbnZlbnRpb24+U3RkQ2FsbDwvQ2FsbGluZ0NvbnZlbnRpb24+PE9wdGltaXphdGlvbj5NYXhTcGVlZDwvT3B0aW1pemF0aW9uPjxXaG9sZVByb2dyYW1PcHRpbWl6YXRpb24+ZmFsc2U8L1dob2xlUHJvZ3JhbU9wdGltaXphdGlvbj48RGVidWdJbmZvcm1hdGlvbkZvcm1hdD5Qcm9ncmFtRGF0YWJhc2U8L0RlYnVnSW5mb3JtYXRpb25Gb3JtYXQ+PFByb2dyYW1EYXRhQmFzZUZpbGVOYW1lPiQoSW50RGlyKSQoUHJvamVjdE5hbWUpLmNvbXBpbGVyLnBkYjwvUHJvZ3JhbURhdGFCYXNlRmlsZU5hbWU+PFRyZWF0V2FybmluZ0FzRXJyb3I+ZmFsc2U8L1RyZWF0V2FybmluZ0FzRXJyb3I+PFNETENoZWNrPmZhbHNlPC9TRExDaGVjaz48QWRkaXRpb25hbE9wdGlvbnM+L2tlcm5lbCAvR0wtICUoQWRkaXRpb25hbE9wdGlvbnMpPC9BZGRpdGlvbmFsT3B0aW9ucz48L0NsQ29tcGlsZT48UmVzb3VyY2VDb21waWxlPjxBZGRpdGlvbmFsSW5jbHVkZURpcmVjdG9yaWVzPiQoV2luZG93c1Nka0RpcilJbmNsdWRlXDEwLjAuMjYxMDAuMFx1bTskKFdpbmRvd3NTZGtEaXIpSW5jbHVkZVwxMC4wLjI2MTAwLjBcc2hhcmVkOyUoQWRkaXRpb25hbEluY2x1ZGVEaXJlY3Rvcmllcyk8L0FkZGl0aW9uYWxJbmNsdWRlRGlyZWN0b3JpZXM+PC9SZXNvdXJjZUNvbXBpbGU+PExpbms+PEdlbmVyYXRlRGVidWdJbmZvcm1hdGlvbj50cnVlPC9HZW5lcmF0ZURlYnVnSW5mb3JtYXRpb24+PE9wdGltaXplUmVmZXJlbmNlcz5mYWxzZTwvT3B0aW1pemVSZWZlcmVuY2VzPjxFbmFibGVDT01EQVRGb2xkaW5nPmZhbHNlPC9FbmFibGVDT01EQVRGb2xkaW5nPjxMaW5rVGltZUNvZGVHZW5lcmF0aW9uPkRlZmF1bHQ8L0xpbmtUaW1lQ29kZUdlbmVyYXRpb24+PFRyZWF0TGlua2VyV2FybmluZ0FzRXJyb3JzPmZhbHNlPC9UcmVhdExpbmtlcldhcm5pbmdBc0Vycm9ycz48SW1hZ2VIYXNTYWZlRXhjZXB0aW9uSGFuZGxlcnM+ZmFsc2U8L0ltYWdlSGFzU2FmZUV4Y2VwdGlvbkhhbmRsZXJzPjxTdWJTeXN0ZW0+TmF0aXZlPC9TdWJTeXN0ZW0+PERyaXZlcj5XRE08L0RyaXZlcj48SWdub3JlQWxsRGVmYXVsdExpYnJhcmllcz50cnVlPC9JZ25vcmVBbGxEZWZhdWx0TGlicmFyaWVzPjxFbnRyeVBvaW50U3ltYm9sPkdzRHJpdmVyRW50cnlAODwvRW50cnlQb2ludFN5bWJvbD48QWRkaXRpb25hbExpYnJhcnlEaXJlY3Rvcmllcz4kKFdpbmRvd3NTZGtEaXIpTGliXCQoV2luZG93c1RhcmdldFBsYXRmb3JtVmVyc2lvbilca21ceDg2OyUoQWRkaXRpb25hbExpYnJhcnlEaXJlY3Rvcmllcyk8L0FkZGl0aW9uYWxMaWJyYXJ5RGlyZWN0b3JpZXM+PEFkZGl0aW9uYWxEZXBlbmRlbmNpZXM+bnRvc2tybmwubGliO2hhbC5saWI7QnVmZmVyT3ZlcmZsb3dGYXN0RmFpbEsubGliO2xpYmNudHByLmxpYjskKEtwaExpYnMpOyUoQWRkaXRpb25hbERlcGVuZGVuY2llcyk8L0FkZGl0aW9uYWxEZXBlbmRlbmNpZXM+PFByb2dyYW1EYXRhYmFzZUZpbGU+JChPdXREaXIpJChUYXJnZXROYW1lKS5wZGI8L1Byb2dyYW1EYXRhYmFzZUZpbGU+PEFkZGl0aW9uYWxPcHRpb25zPi9CcmVwcm8gL0lOQ1JFTUVOVEFMOk5PIC9JR05PUkU6NDI2NiAlKEFkZGl0aW9uYWxPcHRpb25zKTwvQWRkaXRpb25hbE9wdGlvbnM+PC9MaW5rPjxMaWI+PExpbmtUaW1lQ29kZUdlbmVyYXRpb24+ZmFsc2U8L0xpbmtUaW1lQ29kZUdlbmVyYXRpb24+PC9MaWI+PC9JdGVtRGVmaW5pdGlvbkdyb3VwPjwvUHJvamVjdD4="), _w("kph_fi_a.h", "I2luY2x1ZGUgPG50aWZzLmg+CiNkZWZpbmUgX0ZJUk1XQVJFX1RZUEUgX1BIX0ZJUk1XQVJFX1RZUEUKI2RlZmluZSBGSVJNV0FSRV9UWVBFIFBIX0ZJUk1XQVJFX1RZUEUKI2RlZmluZSBQRklSTVdBUkVfVFlQRSBQUEhfRklSTVdBUkVfVFlQRQojZGVmaW5lIEZpcm13YXJlVHlwZVVua25vd24gUGhGaXJtd2FyZVR5cGVVbmtub3duCiNkZWZpbmUgRmlybXdhcmVUeXBlQmlvcyBQaEZpcm13YXJlVHlwZUJpb3MKI2RlZmluZSBGaXJtd2FyZVR5cGVVZWZpIFBoRmlybXdhcmVUeXBlVWVmaQojZGVmaW5lIEZpcm13YXJlVHlwZU1heCBQaEZpcm13YXJlVHlwZU1heAojZGVmaW5lIF9NRU1PUllfSU5GT1JNQVRJT05fQ0xBU1MgUGhfTUVNT1JZX0lORk9STUFUSU9OX0NMQVNTCiNkZWZpbmUgTUVNT1JZX0lORk9STUFUSU9OX0NMQVNTIFBoTUVNT1JZX0lORk9STUFUSU9OX0NMQVNTCiNkZWZpbmUgTWVtb3J5QmFzaWNJbmZvcm1hdGlvbiBQaE1lbW9yeUJhc2ljSW5mb3JtYXRpb24KI2RlZmluZSBfVklSVFVBTF9NRU1PUllfSU5GT1JNQVRJT05fQ0xBU1MgUGhfVklSVFVBTF9NRU1PUllfSU5GT1JNQVRJT05fQ0xBU1MKI2RlZmluZSBWSVJUVUFMX01FTU9SWV9JTkZPUk1BVElPTl9DTEFTUyBQaFZJUlRVQUxfTUVNT1JZX0lORk9STUFUSU9OX0NMQVNTCiNkZWZpbmUgVm1QcmVmZXRjaEluZm9ybWF0aW9uIFBoVm1QcmVmZXRjaEluZm9ybWF0aW9uCiNkZWZpbmUgVm1QYWdlUHJpb3JpdHlJbmZvcm1hdGlvbiBQaFZtUGFnZVByaW9yaXR5SW5mb3JtYXRpb24KI2RlZmluZSBWbUNmZ0NhbGxUYXJnZXRJbmZvcm1hdGlvbiBQaFZtQ2ZnQ2FsbFRhcmdldEluZm9ybWF0aW9uCiNkZWZpbmUgX01FTU9SWV9SQU5HRV9FTlRSWSBQaF9NRU1PUllfUkFOR0VfRU5UUlkKI2RlZmluZSBNRU1PUllfUkFOR0VfRU5UUlkgUGhNRU1PUllfUkFOR0VfRU5UUlkKI2RlZmluZSBQTUVNT1JZX1JBTkdFX0VOVFJZIFBoUE1FTU9SWV9SQU5HRV9FTlRSWQojZGVmaW5lIF9NRU1PUllfQkFTSUNfSU5GT1JNQVRJT04gUGhfTUVNT1JZX0JBU0lDX0lORk9STUFUSU9OCiNkZWZpbmUgTUVNT1JZX0JBU0lDX0lORk9STUFUSU9OIFBoTUVNT1JZX0JBU0lDX0lORk9STUFUSU9OCiNkZWZpbmUgUE1FTU9SWV9CQVNJQ19JTkZPUk1BVElPTiBQaFBNRU1PUllfQkFTSUNfSU5GT1JNQVRJT04KI2RlZmluZSBfTUVNT1JZX1BBUlRJVElPTl9JTkZPUk1BVElPTl9DTEFTUyBQaF9NRU1PUllfUEFSVElUSU9OX0lORk9STUFUSU9OX0NMQVNTCiNkZWZpbmUgTUVNT1JZX1BBUlRJVElPTl9JTkZPUk1BVElPTl9DTEFTUyBQaE1FTU9SWV9QQVJUSVRJT05fSU5GT1JNQVRJT05fQ0xBU1MKI2RlZmluZSBTeXN0ZW1NZW1vcnlQYXJ0aXRpb25JbmZvcm1hdGlvbiBQaFN5c3RlbU1lbW9yeVBhcnRpdGlvbkluZm9ybWF0aW9uCiNkZWZpbmUgU3lzdGVtTWVtb3J5UGFydGl0aW9uTW92ZU1lbW9yeSBQaFN5c3RlbU1lbW9yeVBhcnRpdGlvbk1vdmVNZW1vcnkKI2RlZmluZSBTeXN0ZW1NZW1vcnlQYXJ0aXRpb25BZGRQYWdlZmlsZSBQaFN5c3RlbU1lbW9yeVBhcnRpdGlvbkFkZFBhZ2VmaWxlCiNkZWZpbmUgU3lzdGVtTWVtb3J5UGFydGl0aW9uQ29tYmluZU1lbW9yeSBQaFN5c3RlbU1lbW9yeVBhcnRpdGlvbkNvbWJpbmVNZW1vcnkK"), _w("kph_fi_b.h", "I2luY2x1ZGUgPG50aWZzLmg+CiNkZWZpbmUgX0ZJUk1XQVJFX1RZUEUgX1BIX0ZJUk1XQVJFX1RZUEUKI2RlZmluZSBGSVJNV0FSRV9UWVBFIFBIX0ZJUk1XQVJFX1RZUEUKI2RlZmluZSBQRklSTVdBUkVfVFlQRSBQUEhfRklSTVdBUkVfVFlQRQojZGVmaW5lIEZpcm13YXJlVHlwZVVua25vd24gUGhGaXJtd2FyZVR5cGVVbmtub3duCiNkZWZpbmUgRmlybXdhcmVUeXBlQmlvcyBQaEZpcm13YXJlVHlwZUJpb3MKI2RlZmluZSBGaXJtd2FyZVR5cGVVZWZpIFBoRmlybXdhcmVUeXBlVWVmaQojZGVmaW5lIEZpcm13YXJlVHlwZU1heCBQaEZpcm13YXJlVHlwZU1heAojZGVmaW5lIE1FTV9JTUFHRSBTRUNfSU1BR0UKI2RlZmluZSBNZW1vcnlNYXBwZWRGaWxlbmFtZUluZm9ybWF0aW9uIDIK"), _w("patch.py", "CmltcG9ydCBzeXMKRT1bKCdLUHJvY2Vzc0hhY2tlci90aHJlYWQuYycsODUsJ0hBTkRMRSB0aHJlYWRIYW5kbGU7JywnSEFORExFIHRocmVhZEhhbmRsZSA9IE5VTEw7JyksCiAgICgnS1Byb2Nlc3NIYWNrZXIvcHJvY2Vzcy5jJyw2NCwnSEFORExFIHByb2Nlc3NIYW5kbGU7JywnSEFORExFIHByb2Nlc3NIYW5kbGUgPSBOVUxMOycpLAogICAoJ0tQcm9jZXNzSGFja2VyL3Byb2Nlc3MuYycsMTc1LCdIQU5ETEUgdG9rZW5IYW5kbGU7JywnSEFORExFIHRva2VuSGFuZGxlID0gTlVMTDsnKV0KZm9yIHAsbixvLHcgaW4gRToKICAgIGQ9b3BlbihwLCdyYicpLnJlYWQoKS5kZWNvZGUoJ2xhdGluLTEnKS5zcGxpdCgnXG4nKQogICAgdD1kW24tMV0KICAgIGFzc2VydCB0LnN0cmlwKCk9PW8sIChwLG4sdCkKICAgIGRbbi0xXT10LnJlcGxhY2Uobyx3KQogICAgb3BlbihwLCd3YicpLndyaXRlKCdcbicuam9pbihkKS5lbmNvZGUoJ2xhdGluLTEnKSkKICAgIHByaW50KCdQQVRDSEVEJyxwLG4sbywnLT4nLHcpCmltcG9ydCBvcwpzcmM9cidDOlxQcm9ncmFtIEZpbGVzICh4ODYpXFdpbmRvd3MgS2l0c1wxMFxJbmNsdWRlXDEwLjAuMjI2MjEuMFxzaGFyZWRcd2FybmluZy5oJwpMPW9wZW4oc3JjLCdyYicpLnJlYWQoKS5kZWNvZGUoJ2xhdGluLTEnKS5zcGxpdCgnXG4nKQpLPVtpIGZvciBpLGwgaW4gZW51bWVyYXRlKEwpIGlmICd3YXJuaW5nKGVycm9yOjQ3MDMpJyBpbiBsLnJlcGxhY2UoJyAnLCcnKV0KcHJpbnQoJ1NIQURPVyBjYW5kaWRhdGVzJywgSykKaWYgbGVuKEspPT0xOgogICAgcHJpbnQoJ1NIQURPVyBkcm9wcGVkIGxpbmUnLEtbMF0rMSxMW0tbMF1dLnN0cmlwKCkpCiAgICBkZWwgTFtLWzBdXQogICAgb3MubWFrZWRpcnMoJ3NoYWRvdycsZXhpc3Rfb2s9VHJ1ZSkKICAgIG9wZW4oJ3NoYWRvdy93YXJuaW5nLmgnLCd3YicpLndyaXRlKCdcbicuam9pbihMKS5lbmNvZGUoJ2xhdGluLTEnKSkKZWxzZToKICAgIHByaW50KCdTSEFET1cgbm90IG5lZWRlZDogbm8gd2FybmluZyhlcnJvcjo0NzAzKSBsaW5lIGluIHRoaXMga2l0JykK")]
    for tag, libs, fi, defs in _TRIES:
        steps += _attempt("U", tag, libs, fi, defs)
    steps.append(BuildStep("if not exist out\\kprocesshacker.sys python patch.py", allow_failure=True))
    for tag, libs, fi, defs in _TRIES:
        steps += _attempt("P", tag, libs, fi, defs)
    steps.append(BuildStep("dir /b /s out\\*.sys out\\*.pdb", allow_failure=True))
    return steps


RECIPES = {
 "KProcessHacker_2.39_msvc_x86": Recipe(
  family="KProcessHacker", version="2.39", source=Source(git_url="https://github.com/processhacker/processhacker.git", git_ref="4310de8c43f7600e344b789ffabad79b79878f6a"),
  upstream="https://github.com/processhacker/processhacker/tree/v2.39", license="GPL-3.0-or-later (source headers)", toolchains=["msvc_x86"],
  build=_steps(),
  artifacts=[Artifact(path="out/kprocesshacker.sys", component="kprocesshacker.sys", pdb="out/kprocesshacker.pdb")],
  build_flags="v2.39 Win8 Release Win32 with the v143 toolset (the WDK msbuild toolset rejects Win32), WDK 10.0.22621.0 headers and libraries (installed beside 10.0.26100.0), /O2 /MD /Zi /GL- /kernel /Gz /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO /SAFESEH:NO /ENTRY:GsDriverEntry@8; kph_fi.h renames phnt's _FIRMWARE_TYPE; util.c and verify.c added as ClCompile items; ksecdd.lib then cng.lib. NOT byte-identical to unmodified upstream",
  notes="x86 build of the pinned v2.39 driver, separate from the x64 image. WDK 10.0.26100.0 has no x86 kernel target, so WDK 10.0.22621.0 is installed by scripts/corpus/install_wdk_x86.py and the project is built with the v143 toolset turned into a driver by a forced props file (see the recipe docstring). The driver is linked and disassembled only, never loaded or installed.",
 ),
}
