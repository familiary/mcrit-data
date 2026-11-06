"""Process Hacker v2.39 KProcessHacker driver, not System Informer.

Initial Windows probe. Open risks: legacy headers versus WDK 10.0.26100;
old project assumptions; link/PDB paths; kernel glue surviving the user-mode
baseline. No upstream source is patched. Driver images are never packaged,
signed, installed or loaded; all output is for disassembly only.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_PROPS = 'python -c "import base64;open(\'corpus-drv.props\',\'wb\').write(base64.b64decode(\'PFByb2plY3Q+PFByb3BlcnR5R3JvdXA+PFdob2xlUHJvZ3JhbU9wdGltaXphdGlvbj5mYWxzZTwvV2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPjxMaW5rSW5jcmVtZW50YWw+ZmFsc2U8L0xpbmtJbmNyZW1lbnRhbD48SW50RGlyPiQoT3V0RGlyKW9ialwkKFByb2plY3ROYW1lKVw8L0ludERpcj48L1Byb3BlcnR5R3JvdXA+PEl0ZW1EZWZpbml0aW9uR3JvdXA+PENsQ29tcGlsZT48UHJlcHJvY2Vzc29yRGVmaW5pdGlvbnM+X1BITlRfSDslKFByZXByb2Nlc3NvckRlZmluaXRpb25zKTwvUHJlcHJvY2Vzc29yRGVmaW5pdGlvbnM+PFJ1bnRpbWVMaWJyYXJ5Pk11bHRpVGhyZWFkZWRETEw8L1J1bnRpbWVMaWJyYXJ5PjxPcHRpbWl6YXRpb24+TWF4U3BlZWQ8L09wdGltaXphdGlvbj48V2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPmZhbHNlPC9XaG9sZVByb2dyYW1PcHRpbWl6YXRpb24+PERlYnVnSW5mb3JtYXRpb25Gb3JtYXQ+UHJvZ3JhbURhdGFiYXNlPC9EZWJ1Z0luZm9ybWF0aW9uRm9ybWF0PjxQcm9ncmFtRGF0YUJhc2VGaWxlTmFtZT4kKEludERpcikkKFByb2plY3ROYW1lKS5jb21waWxlci5wZGI8L1Byb2dyYW1EYXRhQmFzZUZpbGVOYW1lPjxUcmVhdFdhcm5pbmdBc0Vycm9yPmZhbHNlPC9UcmVhdFdhcm5pbmdBc0Vycm9yPjxBZGRpdGlvbmFsT3B0aW9ucz4vR0wtICUoQWRkaXRpb25hbE9wdGlvbnMpPC9BZGRpdGlvbmFsT3B0aW9ucz48L0NsQ29tcGlsZT48TGluaz48R2VuZXJhdGVEZWJ1Z0luZm9ybWF0aW9uPnRydWU8L0dlbmVyYXRlRGVidWdJbmZvcm1hdGlvbj48T3B0aW1pemVSZWZlcmVuY2VzPmZhbHNlPC9PcHRpbWl6ZVJlZmVyZW5jZXM+PEVuYWJsZUNPTURBVEZvbGRpbmc+ZmFsc2U8L0VuYWJsZUNPTURBVEZvbGRpbmc+PExpbmtUaW1lQ29kZUdlbmVyYXRpb24+RGVmYXVsdDwvTGlua1RpbWVDb2RlR2VuZXJhdGlvbj48UHJvZ3JhbURhdGFiYXNlRmlsZT4kKE91dERpcikkKFRhcmdldE5hbWUpLnBkYjwvUHJvZ3JhbURhdGFiYXNlRmlsZT48QWRkaXRpb25hbE9wdGlvbnM+L0JyZXBybyAvSU5DUkVNRU5UQUw6Tk8gJShBZGRpdGlvbmFsT3B0aW9ucyk8L0FkZGl0aW9uYWxPcHRpb25zPjwvTGluaz48TGliPjxMaW5rVGltZUNvZGVHZW5lcmF0aW9uPmZhbHNlPC9MaW5rVGltZUNvZGVHZW5lcmF0aW9uPjwvTGliPjwvSXRlbURlZmluaXRpb25Hcm91cD48L1Byb2plY3Q+\'))"'

RECIPES = {
 "KProcessHacker_2.39_msvc": Recipe(
  family="KProcessHacker", version="2.39", source=Source(git_url="https://github.com/processhacker/processhacker.git", git_ref="4310de8c43f7600e344b789ffabad79b79878f6a"),
  upstream="https://github.com/processhacker/processhacker/tree/v2.39", license="GPL-3.0-or-later (source headers)", toolchains=["msvc_x64"],
  build=[BuildStep(_PROPS),
   BuildStep('msbuild KProcessHacker\\KProcessHacker.vcxproj /p:Configuration="Win8 Release" /p:Platform=x64 /p:PlatformToolset=WindowsKernelModeDriver10.0 /p:WindowsTargetPlatformVersion=10.0.26100.0 /p:TargetVersion=Windows10 /p:DriverType=WDM /p:SignMode=Off /p:SkipPackageVerification=true /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false /p:ForceImportBeforeCppTargets=%CD%\\corpus-drv.props /m /v:normal'), BuildStep("dir /s out", allow_failure=True)],
  artifacts=[Artifact(path="out/kprocesshacker.sys", component="kprocesshacker.sys", pdb="out/kprocesshacker.pdb")],
  build_flags="v2.39 Win8 Release x64, WDK 10.0.26100.0 retarget from 8.0; /O2 /MD /Zi /GL- /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO; SignMode=Off",
  notes="v2.39 driver as requested by tracker #66, never current System Informer. WDK 10.0.26100.0 replaces the unavailable 8.0 toolset through properties only. No x86 kernel target in this WDK. Kernel runtime/import residue is a measured limitation. No packaging, signing, installation or loading.",
 ),
}
