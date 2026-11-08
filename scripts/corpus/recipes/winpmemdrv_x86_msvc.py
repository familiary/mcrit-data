"""WinPmem 1.6.2 driver (winpmem.sys) from the pinned Rekall 1.2.0 archive, x86.

The x86 half of ``WinPmemDrv_1.6.2_msvc``, a recipe of its own for the reason
``diskcryptordrv_x86_msvc.py`` gives: the runner's WDK 10.0.26100.0 cannot build
an x86 driver, and Microsoft.Windows.WDK.x86 (10.0.26100.1, 10.0.26100.6584 and
10.0.28000.1839 inspected) ships no Lib\\<ver>\\km directory, so there is no
x86 ntoskrnl.lib in it. The recipe therefore installs WDK 10.0.22621
(``scripts/install_wdk_x86.py``: installer stub pinned by sha256
f3948d1486f8a7821bcef431487d3893fcd3a053d97ab37a1333a0c26e0bd232, falling back
to the Chocolatey package of the same kit) and drives cl and link directly, the
way the x64 recipe does, against its Lib\\10.0.22621.0\\km\\x86.

The x86 command lines differ from the x64 ones only where the architecture
does: /Gz and /D_X86_ /DWIN32 /D_WIN32 instead of /D_AMD64_ /DWIN64 /D_WIN64,
/MACHINE:X86, the km\\x86 library directory, and /ENTRY:GsDriverEntry@8 (the
entry the WDK itself gives an x86 driver built with /GS; it is defined in
BufferOverflowK.lib and calls DriverEntry). Upstream's source is not changed.
The image is NOT byte-identical to a build of unmodified upstream because it is
built with the WDK 10.0.22621 toolchain and the corpus link flags (/OPT:NOREF
/OPT:NOICF /Brepro /INCREMENTAL:NO, no /GL).

Open risks:
1. The WDK 10.0.22621 payload is downloaded by the installer stub at build
   time and is not pinned beyond the stub's own version and sha256.
2. Upstream compiles seven C units under a 2016 DDK; only the units its SOURCES
   file names are built, and none of them is x64-only (winpmem.c and kd.c have
   _WIN64 branches that are simply not taken).
3. The x86 kernel-mode glue baseline is measured on the runner from the same
   10.0.22621 libraries.
4. The image is never signed, installed or loaded.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_KIT = "10.0.22621.0"

RECIPES = {
 "WinPmemDrv_1.6.2_msvc_x86": Recipe(
  family="WinPmemDrv", version="1.6.2",
  source=Source(url="https://codeload.github.com/google/rekall/tar.gz/cfaf02d7b4f8b9853fec38ea86e7efd22e78bf6f", sha256="e4ea411c282ba9239a3fe65339a500f99eb14cf26d5ff9e2248ea978f0b87e1b", strip_prefix="tools/windows/winpmem"),
  upstream="https://github.com/google/rekall/tree/cfaf02d7b4f8b9853fec38ea86e7efd22e78bf6f/tools/windows/winpmem", license="Apache-2.0", toolchains=["msvc_x86"],
  build=[BuildStep('python "{repo}/scripts/install_wdk_x86.py"'),
   BuildStep('cl /nologo /c /O2 /MD /Zi /GL- /kernel /Zl /GS /Gz /D_X86_ /DWIN32 /D_WIN32 /D_KERNEL_MODE /Dtry=__try /Dexcept=__except /DNTDDI_VERSION=0x06020000 /D_WIN32_WINNT=0x0602 /I"%WindowsSdkDir%Include/' + _KIT + '/km" /I"%WindowsSdkDir%Include/' + _KIT + '/shared" winpmem.c read.c api.c kd.c pte_mmap.c pte_mmap_windows.c pci.c /Fdwinpmem.compiler.pdb'),
   BuildStep('link /DRIVER /SUBSYSTEM:NATIVE /ENTRY:GsDriverEntry@8 /NODEFAULTLIB /MACHINE:X86 /DEBUG /OPT:NOREF /OPT:NOICF /INCREMENTAL:NO /Brepro /OUT:winpmem.sys /PDB:winpmem.pdb *.obj /LIBPATH:"%WindowsSdkDir%Lib/' + _KIT + '/km/x86" ntoskrnl.lib hal.lib wdmsec.lib BufferOverflowK.lib')],
  artifacts=[Artifact(path="winpmem.sys", component="winpmem.sys", pdb="winpmem.pdb")],
  build_flags="Upstream SOURCES list, WDK 10.0.22621.0 (installed beside 10.0.26100.0), x86; /O2 /MD /Zi /GL- /kernel /Zl /GS /Gz /Dtry=__try /Dexcept=__except /DRIVER /ENTRY:GsDriverEntry@8 /NODEFAULTLIB /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO. NOT byte-identical to unmodified upstream",
  notes="Original 1.6.2-era driver from the same historical pin as the client, x86 build. WDK 10.0.26100.0 has no x86 kernel target and Microsoft.Windows.WDK.x86 carries no km libraries, so WDK 10.0.22621.0 is installed by scripts/install_wdk_x86.py (installer stub pinned by sha256 f3948d14...d232) and cl/link are driven directly against its km\\x86 libraries. Only upstream's seven C units are compiled; its generated api.h is preserved. Recipe-applied, NOT byte-identical to unmodified upstream: the WDK 10.0.22621 toolchain and the corpus compile/link flags. Never packaged, signed, installed, loaded or executed.",
 ),
}
