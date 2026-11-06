"""EDRSilencer built with MSVC for x86 and x64, beside the MinGW builds.

data/EDRSilencer carries only MinGW artefacts, which is the compiler the
upstream README documents. Most Windows software an analyst meets is
MSVC-built, so these recipes add the same two upstream translation units
compiled by cl.exe for both Intel architectures.

Why a generated harness header is needed. Upstream utils.h includes
<initguid.h> and then DEFINE_GUIDs three filter-engine GUIDs,
FWPM_CONDITION_ALE_APP_ID, FWPM_LAYER_ALE_AUTH_CONNECT_V4 and
FWPM_LAYER_ALE_AUTH_CONNECT_V6. The current Windows SDK (10.0.26100)
fwpmu.h initializes those same objects itself, so the translation unit
gets two initializers for each name:

  error C2374: 'FWPM_CONDITION_ALE_APP_ID': redefinition; multiple initialization

Force-including <windows.h> and <fwpmu.h> before utils.h does not help: the
same C2374 is reported, with the "see declaration" note pointing into
fwpmu.h, so the SDK copy is an initializer as well. The failing build is
scratch branch scratch/codex-windows-tools-probe, run 42212264129. So the
harness does not reorder includes. It is written into the source tree by
the recipe, forced into every compilation with /FI, and renames upstream's
three copies to EDRS_UPSTREAM_<name> after the SDK header has been read.
Upstream then defines its GUIDs under the new names, with the same bytes
as before, and each reference in EDRSilencer.c and utils.c is rewritten
to match through the macro. The SDK's own copies are no longer referenced
and are dropped by /OPT:REF. Upstream source is not changed.

The GUIDs themselves are unchanged. The same three values are what the
MinGW build uses through upstream utils.h, so the filter-layer and
condition keys match what EDRSilencer sends to WFP in both builds.

Both upstream translation units are compiled with /MD, /O2 and full symbols,
then linked with fwpuclnt.lib and advapi32.lib, the same libraries the
MinGW command passes as -lfwpuclnt -ladvapi32. Linked and disassembled
only; never executed and never used to change Windows Filtering Platform.

Notes on this data:
  * The compiler produces full PDB symbols, so names survive the import.
  * No measurements are recorded here yet. The overlap figures and glue
    survivors are measured after the first CI import and will be added.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_SOURCE = Source(git_url="https://github.com/netero1010/EDRSilencer.git",
                 git_ref="0e73a7037ec65c52894d8208e6f605a7da0a34a6")

# Written before cl runs, in the source root. Upstream's copies of the three
# GUIDs are renamed to EDRS_UPSTREAM_*; the SDK's copies are read first, so
# the renaming applies to upstream's definitions and to nothing the SDK
# declares. Each line has no quotes, percent signs or cmd metacharacters.
_HARNESS = ("python -c \"open('edrs_msvc_guid.h','w').write('"
            "#include <windows.h>\\n"
            "#include <fwpmu.h>\\n"
            "#define FWPM_CONDITION_ALE_APP_ID EDRS_UPSTREAM_FWPM_CONDITION_ALE_APP_ID\\n"
            "#define FWPM_LAYER_ALE_AUTH_CONNECT_V4 EDRS_UPSTREAM_FWPM_LAYER_ALE_AUTH_CONNECT_V4\\n"
            "#define FWPM_LAYER_ALE_AUTH_CONNECT_V6 EDRS_UPSTREAM_FWPM_LAYER_ALE_AUTH_CONNECT_V6\\n"
            "')\"")

_COMPILE = ("cl /nologo /O2 /MD /Zi /D_CRT_SECURE_NO_WARNINGS "
            "/FIedrs_msvc_guid.h EDRSilencer.c utils.c "
            "/link fwpuclnt.lib advapi32.lib /DEBUG /OPT:NOREF /OPT:NOICF "
            "/Brepro /INCREMENTAL:NO /OUT:EDRSilencer.exe /PDB:EDRSilencer.pdb")

RECIPES = {
    "EDRSilencer_2024-11-03_msvc": Recipe(
        family="EDRSilencer", version="2024-11-03", source=_SOURCE,
        upstream="https://github.com/netero1010/EDRSilencer", license="MIT",
        build=[BuildStep(_HARNESS), BuildStep(_COMPILE)],
        artifacts=[Artifact(path="EDRSilencer.exe", component="EDRSilencer.exe", pdb="EDRSilencer.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO; /FIedrs_msvc_guid.h (renames upstream's three GUIDs to EDRS_UPSTREAM_*); fwpuclnt.lib advapi32.lib",
        notes="Both upstream translation units with the Windows SDK's WFP "
              "headers and dynamic CRT. Full linker PDB, no LTCG or "
              "incremental link. The only source change is the generated "
              "harness, which renames upstream's copies of three GUIDs so "
              "they no longer collide with the SDK's. Linked and "
              "disassembled only, never executed or used to modify WFP.",
    ),
}
