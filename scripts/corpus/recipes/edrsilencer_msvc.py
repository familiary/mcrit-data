"""EDRSilencer built with MSVC for x86 and x64, beside the MinGW builds.

data/EDRSilencer carries only MinGW artefacts, which is the compiler the
upstream README documents. Most Windows software an analyst meets is
MSVC-built, so these recipes add the same two upstream translation units
compiled by cl.exe for both Intel architectures.

Three obstacles, and how each is handled without changing upstream source:

1. C2374 on FWPM_CONDITION_ALE_APP_ID, FWPM_LAYER_ALE_AUTH_CONNECT_V4 and
   FWPM_LAYER_ALE_AUTH_CONNECT_V6. utils.h includes <initguid.h> and then
   <fwpmu.h>, and DEFINEs these three GUIDs. Upstream includes utils.h once
   per translation unit and has no double include (checked: EDRSilencer.c
   and utils.c each include it once, and it has no guards), so the double
   definition is not upstream's doing. The error notes point into the SDK's
   fwpmu.h. Two things were measured. Reading the SDK header a second time
   under INITGUID, or renaming upstream's copies without preventing that
   second read, keeps the error (scratch runs 42212264129 and 42277535747).
   With the generated include-once stub below, the SDK header is read once
   and the error is still reported, so the remaining collision is with
   upstream's own definitions. Renaming upstream's three definitions to
   EDRS_UPSTREAM_* removes that collision, because the SDK header never
   declares the EDRS_ names. The GUID values are upstream's unchanged, and
   the MinGW build uses the same bytes through the same definitions.

2. The harness is generated, not upstream. The recipe writes edrs_inc/fwpmu.h,
   a one-time include guard around the newest real SDK um/fwpmu.h, and
   edrs_guid.h, which windows.h and that stub, then the three renames. Both
   are force-included with /FI or found through /I, so every <fwpmu.h> in
   the build reaches the guarded stub.

3. strcasecmp, called once in EDRSilencer.c, is POSIX. MinGW supplies it;
   MSVC's CRT spells it _stricmp (same ASCII case-insensitive compare). The
   mapping is a command-line /D, so the upstream call site is unchanged.

Measured, SMDA 5.0.2 for MinGW and 4.8.0 for MSVC (functions with 10 or more
instructions, the cross-family floor; kept + removed = total image functions):
  EDRSilencer_2024-11-03_msvc143_x64_EDRSilencer.exe: 49 kept + 168 removed = 217; 18 functions >=10, 18 unique PicHashes.
  EDRSilencer_2024-11-03_msvc143_x86_EDRSilencer.exe: 48 kept + 164 removed = 212; 17 functions >=10, 17 unique PicHashes.
  MinGW (for comparison, from edrsilencer.py): x64 17 unique, x86 19 unique.
  x64 versus x86 (MSVC): 0 shared at the floor.
  MSVC versus MinGW at the floor: x86 0 shared; x64 1 shared, PrintHelp
  0xdd8066c9ae2c617e (upstream's own function, identical code from both
  compilers; not glue).

Glue survivors, named at or above the floor, all MSVC CRT or runtime:
  x64 printf 0x01b000030f8b5bfc (the same hash the al-khaser O2 x64
  printf/wprintf wrapper carries in this corpus);
  x64 __scrt_common_main_seh 0xa487ef4456111551 (as in DiskCryptor's x64 dccon.exe);
  x86 printf 0xcc8ddc54a4d6fac6.
The upstream functions are left alone.

Linked and disassembled only; never executed and never used to change
Windows Filtering Platform.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_SOURCE = Source(git_url="https://github.com/netero1010/EDRSilencer.git",
                 git_ref="0e73a7037ec65c52894d8208e6f605a7da0a34a6")

# Generates edrs_inc/fwpmu.h, a one-time include guard around the newest real
# SDK um/fwpmu.h, and edrs_guid.h, which the compiler force-includes. The
# SDK path is found from WindowsSdkDir, the environment the developer prompt
# exports. Quotes are avoided in the Python text so the cmd.exe quoting holds.
_STUB = ("python -c \"import os,glob;"
         "r=os.environ['WindowsSdkDir'];"
         "c=sorted(glob.glob(os.path.join(r,'Include','*','um','fwpmu.h')));"
         "p=c[-1].replace(chr(92),chr(47));"
         "print('real fwpmu.h:',p);"
         "os.makedirs('edrs_inc',exist_ok=True);"
         "open('edrs_inc/fwpmu.h','w').write('#ifndef EDRS_FWPMU_STUB_ONCE\\n#define EDRS_FWPMU_STUB_ONCE\\n#include '+chr(34)+p+chr(34)+'\\n#endif\\n');"
         "open('edrs_guid.h','w').write('#include <windows.h>\\n#include <fwpmu.h>\\n"
         "#define FWPM_CONDITION_ALE_APP_ID EDRS_UPSTREAM_FWPM_CONDITION_ALE_APP_ID\\n"
         "#define FWPM_LAYER_ALE_AUTH_CONNECT_V4 EDRS_UPSTREAM_FWPM_LAYER_ALE_AUTH_CONNECT_V4\\n"
         "#define FWPM_LAYER_ALE_AUTH_CONNECT_V6 EDRS_UPSTREAM_FWPM_LAYER_ALE_AUTH_CONNECT_V6\\n')\"")

# strcasecmp is POSIX; MSVC's CRT spells it _stricmp (same ASCII compare).
# Mapped on the command line so upstream's call site is unchanged.
_COMPILE = ("cl /nologo /O2 /MD /Zi /D_CRT_SECURE_NO_WARNINGS /I edrs_inc "
            "/Dstrcasecmp=_stricmp /FIedrs_guid.h EDRSilencer.c utils.c "
            "/link fwpuclnt.lib advapi32.lib /DEBUG /OPT:NOREF /OPT:NOICF "
            "/Brepro /INCREMENTAL:NO /OUT:EDRSilencer.exe /PDB:EDRSilencer.pdb")

RECIPES = {
    "EDRSilencer_2024-11-03_msvc": Recipe(
        family="EDRSilencer", version="2024-11-03", source=_SOURCE,
        upstream="https://github.com/netero1010/EDRSilencer", license="MIT",
        build=[BuildStep(_STUB), BuildStep(_COMPILE)],
        artifacts=[Artifact(path="EDRSilencer.exe", component="EDRSilencer.exe", pdb="EDRSilencer.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO; /I edrs_inc (one-time include guard around the SDK fwpmu.h); /FIedrs_guid.h (renames upstream's three GUIDs to EDRS_UPSTREAM_*); /Dstrcasecmp=_stricmp; fwpuclnt.lib advapi32.lib",
        notes="Both upstream translation units with the Windows SDK's WFP "
              "headers and dynamic CRT. Full linker PDB, no LTCG or "
              "incremental link. The only build-side change is generated: an "
              "include-once stub for the SDK's fwpmu.h, a forced-include "
              "harness that renames upstream's three GUID definitions, and a "
              "command-line strcasecmp mapping. No upstream file is changed. Linked and disassembled "
              "only, never executed or used to modify WFP.",
    ),
}
