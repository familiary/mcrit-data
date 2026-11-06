"""WinPmem 1.6.2 driver from Rekall 1.2.0; x64 WDK probe.

The seven C files are exactly the upstream SOURCES list. Its generated api.h
is already shipped in the pinned archive; no obfuscation key is regenerated.
Open risks: /kernel with the requested /MD, and 2014 headers against WDK
10.0.26100.0. No source patch, ignored relocation or missing-symbol override.
The image is never signed, installed, loaded or used for acquisition.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

RECIPES = {
 "WinPmemDrv_1.6.2_msvc": Recipe(
  family="WinPmemDrv", version="1.6.2",
  source=Source(url="https://codeload.github.com/google/rekall/tar.gz/cfaf02d7b4f8b9853fec38ea86e7efd22e78bf6f", sha256="e4ea411c282ba9239a3fe65339a500f99eb14cf26d5ff9e2248ea978f0b87e1b", strip_prefix="tools/windows/winpmem"),
  upstream="https://github.com/google/rekall/tree/cfaf02d7b4f8b9853fec38ea86e7efd22e78bf6f/tools/windows/winpmem", license="Apache-2.0", toolchains=["msvc_x64"],
  build=[   BuildStep('cl /nologo /c /O2 /MD /Zi /GL- /kernel /Zl /GS /D_AMD64_ /DWIN64 /D_WIN64 /D_KERNEL_MODE /Dtry=__try /Dexcept=__except /DNTDDI_VERSION=0x06020000 /D_WIN32_WINNT=0x0602 /I"%WindowsSdkDir%Include/10.0.26100.0/km" /I"%WindowsSdkDir%Include/10.0.26100.0/shared" winpmem.c read.c api.c kd.c pte_mmap.c pte_mmap_windows.c pci.c /Fdwinpmem.compiler.pdb'),
   BuildStep('link /DRIVER /SUBSYSTEM:NATIVE /ENTRY:DriverEntry /NODEFAULTLIB /MACHINE:X64 /DEBUG /OPT:NOREF /OPT:NOICF /INCREMENTAL:NO /Brepro /OUT:winpmem.sys /PDB:winpmem.pdb *.obj /LIBPATH:"%WindowsSdkDir%Lib/10.0.26100.0/km/x64" ntoskrnl.lib hal.lib wdmsec.lib BufferOverflowK.lib')],
  artifacts=[Artifact(path="winpmem.sys", component="winpmem.sys", pdb="winpmem.pdb")],
  build_flags="Upstream SOURCES list, WDK 10.0.26100.0; /O2 /MD /Zi /GL- /kernel /Zl /GS /Dtry=__try /Dexcept=__except /DRIVER /NODEFAULTLIB /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO",
  notes="Original 1.6.2-era driver from the same historical pin as the client. Only upstream's seven C units are compiled; its generated api.h is preserved. WDK has no x86 kernel target. Kernel runtime/import residue is retained when the user-mode baseline cannot match it. Never packaged, signed, installed, loaded or executed.",
 ),
}
