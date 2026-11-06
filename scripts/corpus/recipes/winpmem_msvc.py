"""WinPmem 1.6.2 user-mode acquisition client from Rekall 1.2.0.

Initial Windows probe: source/project inspection only. No upstream source edits.
Open risks: modern SDK/WDK compatibility; PDB coverage; retained kernel/import
glue and MSVC printf/startup wrappers. Every image is linked and disassembled
only, never run, signed, installed or loaded.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

RECIPES = {
 "WinPmem_1.6.2_msvc": Recipe(
  family="WinPmem", version="1.6.2",
  source=Source(url="https://codeload.github.com/google/rekall/tar.gz/cfaf02d7b4f8b9853fec38ea86e7efd22e78bf6f", sha256="e4ea411c282ba9239a3fe65339a500f99eb14cf26d5ff9e2248ea978f0b87e1b", strip_prefix="tools/windows/winpmem"),
  upstream="https://github.com/google/rekall/tree/cfaf02d7b4f8b9853fec38ea86e7efd22e78bf6f/tools/windows/winpmem; https://github.com/Velocidex/WinPmem",
  license="Apache-2.0 (source headers and LICENSE)", toolchains=["msvc_x86", "msvc_x64"],
  build=[BuildStep("python -m pip install --quiet smda==5.0.2 mcrit==1.16.0"),
   BuildStep("cl /nologo /O2 /MD /Zi /EHsc /DUNICODE /D_UNICODE /D_CRT_SECURE_NO_WARNINGS /D_INC_VARARGS executable/winpmem.cpp /link /DLL /NOENTRY advapi32.lib /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO /OUT:winpmem.dll /PDB:winpmem.pdb")],
  artifacts=[Artifact(path="winpmem.dll", component="winpmem.dll", pdb="winpmem.pdb")],
  build_flags="/O2 /MD /Zi /EHsc /DUNICODE /D_UNICODE /D_INC_VARARGS /DLL /NOENTRY /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO",
  notes="Historical 1.6.2 client pin located in Rekall 1.2.0 (2014-12-21), confirmed by PMEM_VERSION in executable/winpmem.h. Only the client translation unit is linked; no CLI, resources, fcat executable or embedded prebuilt drivers. No modern WinPmem substitution. No acquisition is performed; linked and disassembled only. _INC_VARARGS attempts to suppress the obsolete redundant varargs include, after standard stdarg is included by upstream.",
 ),
}
