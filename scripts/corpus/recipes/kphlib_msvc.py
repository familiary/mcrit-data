"""Process Hacker v2.39 kph.c client, with only link-reached phlib support.

Pinned to upstream v2.39 (commit 4310de8c43f7600e344b789ffabad79b79878f6a).
No upstream source is patched. The phlib and kph.c compiles add
_NO_CRT_STDIO_INLINE, so the stdio wrappers are real calls rather than inline
headers. The link line is otherwise unchanged.

Open risks, in the order they bite:
1. phlib\\format.c declares and calls the UCRT-internal __acrt_fp_format
   itself (under #if _MSC_VER >= 1900; the older branch calls the equally
   internal _cfltcvt_l), so no define or header choice avoids the reference.
   ucrt.lib does not export it. The static libucrt.lib defines it, but
   linking that beside the /MD import libraries gives LNK2005 duplicates for
   wcslen, _create_locale and _ui64tow and LNK1169; legacy_stdio_float_rounding.lib
   is not in this SDK (LNK1181). The recipe therefore generates one small
   object, fpshim.c, defining __acrt_fp_format with the exported
   _snprintf_s_l, compiled /MD. It is generated, not upstream, and it enters
   the image as one extra function named __acrt_fp_format that is not the
   UCRT's code; the notes say so.
2. kph.c is compiled as a plain object and the phlib archive is pulled by
   reference, so only reached support code enters the image.

No driver interaction is exercised; the DLL is linked and disassembled only.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_SHIM = ('python -c "import base64;'
        "open('fpshim.c','wb').write(base64.b64decode('I2luY2x1ZGUgPHN0ZGlvLmg+CiNpbmNsdWRlIDxsb2NhbGUuaD4KZXJybm9fdCBfX2NkZWNsIF9fYWNydF9mcF9mb3JtYXQoZG91YmxlIGNvbnN0KiB2YWx1ZSwgY2hhciogcmVzdWx0LCBzaXplX3QgY291bnQsIGNoYXIqIHNjcmF0Y2gsIHNpemVfdCBzY3JhdGNoX2NvdW50LCBpbnQgZm9ybWF0LCBpbnQgcHJlY2lzaW9uLCB1bnNpZ25lZCBfX2ludDY0IG9wdGlvbnMsIF9sb2NhbGVfdCBsb2NhbGUpCnsKICAgIGNoYXIgZls4XTsKICAgICh2b2lkKXNjcmF0Y2g7ICh2b2lkKXNjcmF0Y2hfY291bnQ7ICh2b2lkKW9wdGlvbnM7CiAgICBmWzBdID0gJyUnOyBmWzFdID0gJy4nOyBmWzJdID0gJyonOyBmWzNdID0gKGNoYXIpZm9ybWF0OyBmWzRdID0gMDsKICAgIHJldHVybiBfc25wcmludGZfc19sKHJlc3VsdCwgY291bnQsIF9UUlVOQ0FURSwgZiwgbG9jYWxlLCBwcmVjaXNpb24sICp2YWx1ZSkgPCAwID8gMzQgOiAwOwp9Cg=='))\"")

_PROPS = ('python -c "import base64;'
          "open('corpus-um.props','wb').write(base64.b64decode('PFByb2plY3Q+PFByb3BlcnR5R3JvdXA+PFdob2xlUHJvZ3JhbU9wdGltaXphdGlvbj5mYWxzZTwvV2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPjxMaW5rSW5jcmVtZW50YWw+ZmFsc2U8L0xpbmtJbmNyZW1lbnRhbD48SW50RGlyPiQoT3V0RGlyKW9ialwkKFByb2plY3ROYW1lKVw8L0ludERpcj48L1Byb3BlcnR5R3JvdXA+PEl0ZW1EZWZpbml0aW9uR3JvdXA+PENsQ29tcGlsZT48UHJlcHJvY2Vzc29yRGVmaW5pdGlvbnM+X05PX0NSVF9TVERJT19JTkxJTkU7JShQcmVwcm9jZXNzb3JEZWZpbml0aW9ucyk8L1ByZXByb2Nlc3NvckRlZmluaXRpb25zPjxSdW50aW1lTGlicmFyeT5NdWx0aVRocmVhZGVkRExMPC9SdW50aW1lTGlicmFyeT48T3B0aW1pemF0aW9uPk1heFNwZWVkPC9PcHRpbWl6YXRpb24+PFdob2xlUHJvZ3JhbU9wdGltaXphdGlvbj5mYWxzZTwvV2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPjxEZWJ1Z0luZm9ybWF0aW9uRm9ybWF0PlByb2dyYW1EYXRhYmFzZTwvRGVidWdJbmZvcm1hdGlvbkZvcm1hdD48UHJvZ3JhbURhdGFCYXNlRmlsZU5hbWU+JChJbnREaXIpJChQcm9qZWN0TmFtZSkuY29tcGlsZXIucGRiPC9Qcm9ncmFtRGF0YUJhc2VGaWxlTmFtZT48VHJlYXRXYXJuaW5nQXNFcnJvcj5mYWxzZTwvVHJlYXRXYXJuaW5nQXNFcnJvcj48QWRkaXRpb25hbE9wdGlvbnM+L0dMLSAlKEFkZGl0aW9uYWxPcHRpb25zKTwvQWRkaXRpb25hbE9wdGlvbnM+PC9DbENvbXBpbGU+PExpbms+PEdlbmVyYXRlRGVidWdJbmZvcm1hdGlvbj50cnVlPC9HZW5lcmF0ZURlYnVnSW5mb3JtYXRpb24+PE9wdGltaXplUmVmZXJlbmNlcz5mYWxzZTwvT3B0aW1pemVSZWZlcmVuY2VzPjxFbmFibGVDT01EQVRGb2xkaW5nPmZhbHNlPC9FbmFibGVDT01EQVRGb2xkaW5nPjxMaW5rVGltZUNvZGVHZW5lcmF0aW9uPkRlZmF1bHQ8L0xpbmtUaW1lQ29kZUdlbmVyYXRpb24+PFByb2dyYW1EYXRhYmFzZUZpbGU+JChPdXREaXIpJChUYXJnZXROYW1lKS5wZGI8L1Byb2dyYW1EYXRhYmFzZUZpbGU+PEFkZGl0aW9uYWxPcHRpb25zPi9CcmVwcm8gL0lOQ1JFTUVOVEFMOk5PICUoQWRkaXRpb25hbE9wdGlvbnMpPC9BZGRpdGlvbmFsT3B0aW9ucz48L0xpbms+PExpYj48TGlua1RpbWVDb2RlR2VuZXJhdGlvbj5mYWxzZTwvTGlua1RpbWVDb2RlR2VuZXJhdGlvbj48L0xpYj48L0l0ZW1EZWZpbml0aW9uR3JvdXA+PC9Qcm9qZWN0Pgo='))\"")

LINK_BASE = r'/DLL /NOENTRY /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO /OUT:out\kphlib.dll /PDB:out\kphlib.pdb out\kph.obj out\fpshim.obj out\phlib.lib ntdll.lib kernel32.lib advapi32.lib user32.lib gdi32.lib comctl32.lib shell32.lib shlwapi.lib ole32.lib oleaut32.lib uuid.lib version.lib winmm.lib crypt32.lib wintrust.lib uxtheme.lib psapi.lib setupapi.lib netapi32.lib ws2_32.lib iphlpapi.lib comdlg32.lib ucrt.lib vcruntime.lib msvcrt.lib msvcprt.lib legacy_stdio_definitions.lib'

RECIPES = {
 "kphlib_2.39_msvc": Recipe(
  family="kphlib", version="2.39", source=Source(git_url="https://github.com/processhacker/processhacker.git", git_ref="4310de8c43f7600e344b789ffabad79b79878f6a"),
  upstream="https://github.com/processhacker/processhacker/tree/v2.39", license="GPL-3.0-or-later (source headers)", toolchains=["msvc_x86", "msvc_x64"],
  build=[BuildStep(_PROPS),
   BuildStep(r'msbuild phlib\phlib.vcxproj /p:Configuration=Release /p:Platform={msbuild_platform} /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0 /p:SolutionDir=%CD%\ /p:OutDir=%CD%\out\ /p:TargetName=phlib /p:WholeProgramOptimization=false /p:ForceImportBeforeCppTargets=%CD%\corpus-um.props /m /v:normal'),
   BuildStep(_SHIM),
   BuildStep(r'cl /nologo /c /O2 /MD /Zi /D_CRT_SECURE_NO_WARNINGS fpshim.c /Foout\fpshim.obj'),
   BuildStep(r'cl /nologo /c /O2 /MD /Zi /Gz /D_PHLIB_ /D_NO_CRT_STDIO_INLINE /DUNICODE /D_UNICODE /DNDEBUG /Iphlib\include /Iphnt\include phlib\kph.c /Foout\kph.obj'),
   BuildStep('link ' + LINK_BASE), BuildStep("dir /s out", allow_failure=True)],
  artifacts=[Artifact(path="out/kphlib.dll", component="kphlib.dll", pdb="out/kphlib.pdb")],
  build_flags="v2.39 Release /O2 /MD /Zi /Gz /GL- /D_NO_CRT_STDIO_INLINE; direct kph.obj + generated fpshim.obj (__acrt_fp_format via _snprintf_s_l) + archive-selected phlib support; /DLL /NOENTRY /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO",
  notes="The reusable kph.c client is linked directly, and only phlib archive objects it reaches are pulled in; phlib is not whole-archived. No ProcessHacker GUI executable is built. The generated fpshim.c supplies the UCRT-internal __acrt_fp_format that phlib's format.c calls, as one extra function that is not the UCRT's code. Necessary Ph support functions are recorded as part of this client image. No driver interaction is exercised; linked and disassembled only.",
 ),
}
