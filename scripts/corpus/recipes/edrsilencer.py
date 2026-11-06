"""EDRSilencer's two upstream C files; linked and disassembled, never run.

The upstream README actually documents a MinGW x64 command. Both Intel
architectures are tested here, and MSVC uses dynamic CRT with full PDBs.
Only code reference data is retained; no filters are installed or exercised.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_SOURCE = Source(git_url="https://github.com/netero1010/EDRSilencer.git",
                 git_ref="0e73a7037ec65c52894d8208e6f605a7da0a34a6")
RECIPES = {
    "EDRSilencer_2024-11-03_mingw": Recipe(
        family="EDRSilencer", version="2024-11-03", source=_SOURCE,
        upstream="https://github.com/netero1010/EDRSilencer", license="MIT",
        build=[BuildStep("{cc} -O2 -g EDRSilencer.c utils.c -o EDRSilencer.exe -lfwpuclnt -ladvapi32 -Wl,--no-insert-timestamp")],
        artifacts=[Artifact(path="EDRSilencer.exe", component="EDRSilencer.exe")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 -g -lfwpuclnt -ladvapi32 -Wl,--no-insert-timestamp",
        notes="Both upstream translation units, compiled with the upstream "
              "MinGW command plus symbols, -O2 and deterministic PE timestamp. "
              "Windows SDK APIs are imported. Linked and disassembled only; "
              "never executed or used to modify Windows Filtering Platform.",
    ),
    "EDRSilencer_2024-11-03_msvc": Recipe(
        family="EDRSilencer", version="2024-11-03", source=_SOURCE,
        upstream="https://github.com/netero1010/EDRSilencer", license="MIT",
        build=[BuildStep("cl /nologo /O2 /MD /Zi /D_CRT_SECURE_NO_WARNINGS EDRSilencer.c utils.c /link fwpuclnt.lib advapi32.lib /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO /OUT:EDRSilencer.exe /PDB:EDRSilencer.pdb")],
        artifacts=[Artifact(path="EDRSilencer.exe", component="EDRSilencer.exe", pdb="EDRSilencer.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO; fwpuclnt.lib advapi32.lib",
        notes="Both upstream translation units; Windows SDK APIs and CRT are "
              "dynamic. Full linker PDB, no LTCG or incremental link. Linked "
              "and disassembled only, never executed or used to modify WFP.",
    ),
}
