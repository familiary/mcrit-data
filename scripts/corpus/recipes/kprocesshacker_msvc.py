"""Process Hacker v2.39 KProcessHacker driver, not System Informer.

Pinned to upstream v2.39 (commit 4310de8c43f7600e344b789ffabad79b79878f6a).
No upstream source is patched. Obstacles are handled by a forced props file
and msbuild properties on the command line. Each attempt is its own build
step, so the log records every try, and the second attempt runs only when the
first produced no image.

Open risks, in the order they bite:
1. kph.h includes WDK <ntifs.h> before it defines PHNT_MODE. phnt's ntexapi.h
   and ntmmapi.h then redefine enums and structs the WDK already declares:
   C2011 on _FIRMWARE_TYPE, _MEMORY_INFORMATION_CLASS,
   _VIRTUAL_MEMORY_INFORMATION_CLASS, _MEMORY_RANGE_ENTRY and
   _MEMORY_BASIC_INFORMATION, plus C2086/C2365 on SystemMemoryPartitionInformation.
   The forced props define PHNT_MODE=0 and the include guards _NTEXAPI_H and
   _NTMMAPI_H so those two phnt headers are skipped in favour of the WDK copies.
   Other phnt headers may still clash; the log lists every one.
2. The project declares TargetVersion=Windows8. WDK 10.0.26100 rejects it
   ("not a supported OS Version"), and Windows8.1 gives MSB4044 on
   ValidNTTargetVersions. Windows8.1 is tried first, then Windows10.
3. BCrypt* calls in verify.c need the kernel cng.lib. The project names no
   AdditionalDependencies, so an unresolved external here is the open finding.

Driver images are never packaged, signed, installed or loaded. This is a
disassembly reference only.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_PROPS = ('python -c "import base64;'
          "open('corpus-drv.props','wb').write(base64.b64decode('PFByb2plY3Q+PFByb3BlcnR5R3JvdXA+PFdob2xlUHJvZ3JhbU9wdGltaXphdGlvbj5mYWxzZTwvV2hvbGVQcm9ncmFtT3B0aW1pemF0aW9uPjxMaW5rSW5jcmVtZW50YWw+ZmFsc2U8L0xpbmtJbmNyZW1lbnRhbD48SW50RGlyPiQoT3V0RGlyKW9ialwkKFByb2plY3ROYW1lKVw8L0ludERpcj48L1Byb3BlcnR5R3JvdXA+PEl0ZW1EZWZpbml0aW9uR3JvdXA+PENsQ29tcGlsZT48UHJlcHJvY2Vzc29yRGVmaW5pdGlvbnM+UEhOVF9NT0RFPTA7X05URVhBUElfSDtfTlRNTUFQSV9IOyUoUHJlcHJvY2Vzc29yRGVmaW5pdGlvbnMpPC9QcmVwcm9jZXNzb3JEZWZpbml0aW9ucz48UnVudGltZUxpYnJhcnk+TXVsdGlUaHJlYWRlZERMTDwvUnVudGltZUxpYnJhcnk+PE9wdGltaXphdGlvbj5NYXhTcGVlZDwvT3B0aW1pemF0aW9uPjxXaG9sZVByb2dyYW1PcHRpbWl6YXRpb24+ZmFsc2U8L1dob2xlUHJvZ3JhbU9wdGltaXphdGlvbj48RGVidWdJbmZvcm1hdGlvbkZvcm1hdD5Qcm9ncmFtRGF0YWJhc2U8L0RlYnVnSW5mb3JtYXRpb25Gb3JtYXQ+PFByb2dyYW1EYXRhQmFzZUZpbGVOYW1lPiQoSW50RGlyKSQoUHJvamVjdE5hbWUpLmNvbXBpbGVyLnBkYjwvUHJvZ3JhbURhdGFCYXNlRmlsZU5hbWU+PFRyZWF0V2FybmluZ0FzRXJyb3I+ZmFsc2U8L1RyZWF0V2FybmluZ0FzRXJyb3I+PEFkZGl0aW9uYWxPcHRpb25zPi9HTC0gJShBZGRpdGlvbmFsT3B0aW9ucyk8L0FkZGl0aW9uYWxPcHRpb25zPjwvQ2xDb21waWxlPjxMaW5rPjxHZW5lcmF0ZURlYnVnSW5mb3JtYXRpb24+dHJ1ZTwvR2VuZXJhdGVEZWJ1Z0luZm9ybWF0aW9uPjxPcHRpbWl6ZVJlZmVyZW5jZXM+ZmFsc2U8L09wdGltaXplUmVmZXJlbmNlcz48RW5hYmxlQ09NREFURm9sZGluZz5mYWxzZTwvRW5hYmxlQ09NREFURm9sZGluZz48TGlua1RpbWVDb2RlR2VuZXJhdGlvbj5EZWZhdWx0PC9MaW5rVGltZUNvZGVHZW5lcmF0aW9uPjxQcm9ncmFtRGF0YWJhc2VGaWxlPiQoT3V0RGlyKSQoVGFyZ2V0TmFtZSkucGRiPC9Qcm9ncmFtRGF0YWJhc2VGaWxlPjxBZGRpdGlvbmFsT3B0aW9ucz4vQnJlcHJvIC9JTkNSRU1FTlRBTDpOTyAlKEFkZGl0aW9uYWxPcHRpb25zKTwvQWRkaXRpb25hbE9wdGlvbnM+PC9MaW5rPjxMaWI+PExpbmtUaW1lQ29kZUdlbmVyYXRpb24+ZmFsc2U8L0xpbmtUaW1lQ29kZUdlbmVyYXRpb24+PC9MaWI+PC9JdGVtRGVmaW5pdGlvbkdyb3VwPjwvUHJvamVjdD4K'))\"")

_MSBUILD = ('msbuild KProcessHacker\\KProcessHacker.vcxproj /t:Rebuild /p:Configuration="Win8 Release" /p:Platform=x64'
            ' /p:PlatformToolset=WindowsKernelModeDriver10.0 /p:WindowsTargetPlatformVersion=10.0.26100.0'
            ' /p:TargetVersion={target} /p:DriverType=WDM /p:SignMode=Off /p:SkipPackageVerification=true'
            ' /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false'
            ' /p:ForceImportBeforeCppTargets=%CD%\\corpus-drv.props /m /v:normal')

RECIPES = {
 "KProcessHacker_2.39_msvc": Recipe(
  family="KProcessHacker", version="2.39", source=Source(git_url="https://github.com/processhacker/processhacker.git", git_ref="4310de8c43f7600e344b789ffabad79b79878f6a"),
  upstream="https://github.com/processhacker/processhacker/tree/v2.39", license="GPL-3.0-or-later (source headers)", toolchains=["msvc_x64"],
  build=[BuildStep(_PROPS),
   BuildStep(_MSBUILD.format(target="Windows8.1"), allow_failure=True),
   BuildStep("if not exist out\\kprocesshacker.sys " + _MSBUILD.format(target="Windows10"), allow_failure=True),
   BuildStep("dir /s out", allow_failure=True)],
  artifacts=[Artifact(path="out/kprocesshacker.sys", component="kprocesshacker.sys", pdb="out/kprocesshacker.pdb")],
  build_flags="v2.39 Win8 Release x64; WDK 10.0.26100.0 via WindowsKernelModeDriver10.0; TargetVersion Windows8.1 then Windows10; /O2 /MD /Zi /GL- /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO; PHNT_MODE=0 and _NTEXAPI_H/_NTMMAPI_H forced by props; SignMode=Off",
  notes="v2.39 driver as requested by tracker #66, never current System Informer. No x86 kernel target exists in WDK 10.0.26100, so this recipe is x64 only. Kernel runtime/import residue is a measured limitation. No packaging, signing, installation or loading.",
 ),
}
