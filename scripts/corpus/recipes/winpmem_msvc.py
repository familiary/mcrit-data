"""WinPmem 1.6.2 client image from the pinned Rekall 1.2.0 source.

CI measurements, SMDA 4.8.0/MCRIT 1.9.0: x64 58 kept + 95 removed = 153; x86 58 + 85 = 143. Both retain 31 functions >=10 instructions and 31 unique PicHashes; cross-architecture overlap is 0.

Named formatting/runtime survivors are x64 asprintf 0x3a5fd25ec0fe4cc8, aswprintf 0xc6f0ed3de3fb8d13, vwprintf 0x30c7edbbfc938177 and wprintf 0x01b000030f8b5bfc; x86 asprintf 0x639bfc2bc221685f, aswprintf 0x013adc10373d10ee, vwprintf 0x6c593a236b25c531 and wprintf 0xcc8ddc54a4d6fac6. Only the client translation unit is linked; no CLI, resources or embedded drivers are included. No acquisition is performed.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

RECIPES = {
 "WinPmem_1.6.2_msvc": Recipe(
  family="WinPmem", version="1.6.2",
  source=Source(url="https://codeload.github.com/google/rekall/tar.gz/cfaf02d7b4f8b9853fec38ea86e7efd22e78bf6f", sha256="e4ea411c282ba9239a3fe65339a500f99eb14cf26d5ff9e2248ea978f0b87e1b", strip_prefix="tools/windows/winpmem"),
  upstream="https://github.com/google/rekall/tree/cfaf02d7b4f8b9853fec38ea86e7efd22e78bf6f/tools/windows/winpmem; https://github.com/Velocidex/WinPmem",
  license="Apache-2.0 (source headers and LICENSE)", toolchains=["msvc_x86", "msvc_x64"],
  build=[   BuildStep("cl /nologo /O2 /MD /Zi /EHsc /DUNICODE /D_UNICODE /D_CRT_SECURE_NO_WARNINGS /D_INC_VARARGS executable/winpmem.cpp /link /DLL /NOENTRY advapi32.lib kernel32.lib ucrt.lib vcruntime.lib msvcrt.lib msvcprt.lib /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO /OUT:winpmem.dll /PDB:winpmem.pdb")],
  artifacts=[Artifact(path="winpmem.dll", component="winpmem.dll", pdb="winpmem.pdb")],
  build_flags="/O2 /MD /Zi /EHsc /DUNICODE /D_UNICODE /D_INC_VARARGS /DLL /NOENTRY /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO",
  notes="Historical 1.6.2 client pin located in Rekall 1.2.0 (2014-12-21), confirmed by PMEM_VERSION in executable/winpmem.h. Only the client translation unit is linked; no CLI, resources, fcat executable or embedded prebuilt drivers. No modern WinPmem substitution. No acquisition is performed; linked and disassembled only. _INC_VARARGS attempts to suppress the obsolete redundant varargs include, after standard stdarg is included by upstream.",
 ),
}
