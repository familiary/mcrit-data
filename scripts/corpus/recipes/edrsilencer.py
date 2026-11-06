"""EDRSilencer's two upstream C files; linked and disassembled, never run.

The upstream README documents MinGW x64. Both Intel architectures produce
separate useful code sets. The Windows 10.0.26100 SDK MSVC attempt failed
because the SDK already initializes three GUIDs that upstream initializes
again in utils.h. See scripts/corpus/README.md for the exact C2374 errors.

CI measurements, SMDA 4.8.0/MCRIT 1.9.0 (functions >=10 instructions):
  EDRSilencer_2024-11-03_mingw13_x64_EDRSilencer.exe: 69 kept + 143 removed = 212; 17 functions >=10, 17 unique PicHashes.
  EDRSilencer_2024-11-03_mingw13_x86_EDRSilencer.exe: 38 kept + 152 removed = 190; 19 functions >=10, 19 unique PicHashes.
  x64 versus x86: 0 shared; 17/19 unique to each.

Named runtime survivor: EDRSilencer_2024-11-03_mingw13_x86_EDRSilencer.exe
  _swprintf.constprop.0 0x798993e50037fa94 (11 instructions).
The x64 swprintf.constprop.0 (0xd0892c9781e77af5, 8 instructions) is below
the comparison floor. All images are disassembled only; WFP is never changed.
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

}
