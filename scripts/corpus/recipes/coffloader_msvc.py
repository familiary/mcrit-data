"""trustedsec/COFFLoader built with MSVC, beside the MinGW build.

The project is aimed at the Windows toolchains people write BOFs with, and
the source anticipates MSVC: COFFLoader.c has an ``_MSC_VER`` branch that
casts the entry point as ``void(__cdecl*)(char*, unsigned long)`` with the
comment "VS 2017 doesn't like this". Upstream ships no MSVC project, only the
MinGW Makefile, so this is a direct ``cl`` of the two translation units the
Makefile compiles, with the same ``-DCOFF_STANDALONE``. See coffloader.py for
the pin, the function inventory and the reason Linux is out of scope.

Flags from the corpus mandates: /O2 (the Makefile builds at -O0, as in
coffloader.py), /MD, /Zi, no /GL and no /LTCG; at link /DEBUG /Brepro
/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF. /D_CRT_SECURE_NO_WARNINGS silences
the deprecation warnings for fopen, strncpy and friends and changes no code.
advapi32.lib is named because BeaconIsAdmin reaches the token APIs.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


RECIPES = {
    "COFFLoader_2026-09-28_msvc": Recipe(
        family="COFFLoader",
        version="2026-09-28",
        upstream="https://github.com/trustedsec/COFFLoader",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/trustedsec/COFFLoader.git",
                      git_ref="edfa7639a137bee639e535732a1aa67cc2b33549"),
        build=[
            BuildStep("cl /nologo /c /O2 /MD /Zi /Fdcoffloader_cl.pdb "
                      "/DCOFF_STANDALONE /D_CRT_SECURE_NO_WARNINGS "
                      "beacon_compatibility.c COFFLoader.c"),
            BuildStep("link /nologo /DEBUG /Brepro /INCREMENTAL:NO "
                      "/OPT:NOREF /OPT:NOICF /PDB:COFFLoader.pdb "
                      "/OUT:COFFLoader.exe beacon_compatibility.obj "
                      "COFFLoader.obj kernel32.lib advapi32.lib"),
            BuildStep("dir", allow_failure=True),
        ],
        artifacts=[Artifact(path="COFFLoader.exe", component="COFFLoader.exe",
                            is_library=False, pdb="COFFLoader.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="cl /O2 /MD /Zi -DCOFF_STANDALONE (no /GL); /DEBUG "
                    "/Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link",
        notes="COFFLoader.c plus beacon_compatibility.c, as upstream's "
              "Makefile links them, built against the DLL runtime so the "
              "C runtime stays attributed to data/MSVC.",
    ),
}
