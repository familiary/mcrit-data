"""EDRSilencer built with MSVC for x86 and x64, beside the MinGW builds.

data/EDRSilencer carries only MinGW artefacts, which is the compiler the
upstream README documents. Most Windows software an analyst meets is
MSVC-built, so these recipes add the same two upstream translation units
compiled by cl.exe for both Intel architectures.

The problem. Upstream utils.h includes <initguid.h> and then <fwpmu.h>, and
DEFINE_GUIDs three filter-engine GUIDs: FWPM_CONDITION_ALE_APP_ID,
FWPM_LAYER_ALE_AUTH_CONNECT_V4 and FWPM_LAYER_ALE_AUTH_CONNECT_V6. Each
translation unit includes utils.h exactly once; upstream has no double
include. Under cl the same names come out initialized twice, which is
C2374 "redefinition; multiple initialization". Renaming upstream's copies
did not remove the second initializer, so the second one comes from the
SDK's fwpmu.h being processed again while INITGUID is defined.

The fix is generated, not upstream. The recipe writes a one-line include
guard around the real SDK header, as a stub named fwpmu.h in a build
directory on the include path. Every <fwpmu.h> then reaches the stub first,
the real header is read once, and that happens before utils.h turns on
INITGUID. Upstream's three GUIDs are defined once. A harness header is
forced into every compilation with /FI and includes windows.h and fwpmu.h
first.

The harness also renames upstream's three GUIDs to EDRS_UPSTREAM_*, after
the SDK header has been read. The SDK header declares the FWPM_ names with
an initializer in the same translation unit, so upstream's FWPM_ definitions
collide with it; the EDRS_ names have no earlier declaration. Upstream's
references are rewritten to match through the macro.

Probe output (/showIncludes and /P, with allow_failure) is in the log, so a
failing build still shows the include chain.

The GUID values are upstream's, unchanged. Both upstream translation units
are compiled with /MD, /O2 and full symbols, then linked with
fwpuclnt.lib and advapi32.lib, the same libraries the MinGW command passes.
Linked and disassembled only; never executed and never used to change
Windows Filtering Platform.

No measurements are recorded here yet. Overlap figures and glue survivors
are measured after the first CI import and will be added.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_SOURCE = Source(git_url="https://github.com/netero1010/EDRSilencer.git",
                 git_ref="0e73a7037ec65c52894d8208e6f605a7da0a34a6")

# Generates edrs_inc/fwpmu.h, a one-time include guard around the newest real
# SDK um\fwpmu.h, and edrs_guid.h, which the compiler force-includes. The
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

# Diagnostics, allowed to fail. Upstream's own include lines, then the
# include chain of the plain (no harness) compile, then the preprocessed
# SDK-name occurrences with the harness.
_PROBE_SOURCE = "findstr /n /c:#include EDRSilencer.c utils.c utils.h"
_PROBE_PLAIN = "cl /nologo /c /showIncludes EDRSilencer.c /Foprobe_plain.obj"
_PROBE_HARNESS_PP = ("cl /nologo /P /I edrs_inc /FIedrs_guid.h EDRSilencer.c "
                     "&& findstr /n /c:FWPM_CONDITION_ALE_APP_ID EDRSilencer.i")

RECIPES = {
    "EDRSilencer_2024-11-03_msvc": Recipe(
        family="EDRSilencer", version="2024-11-03", source=_SOURCE,
        upstream="https://github.com/netero1010/EDRSilencer", license="MIT",
        build=[BuildStep(_PROBE_SOURCE, allow_failure=True),
               BuildStep(_PROBE_PLAIN, allow_failure=True),
               BuildStep(_STUB),
               BuildStep(_PROBE_HARNESS_PP, allow_failure=True),
               BuildStep(_COMPILE)],
        artifacts=[Artifact(path="EDRSilencer.exe", component="EDRSilencer.exe", pdb="EDRSilencer.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO; /I edrs_inc (one-time guard around SDK fwpmu.h); /FIedrs_guid.h; fwpuclnt.lib advapi32.lib",
        notes="Both upstream translation units with the Windows SDK's WFP "
              "headers and dynamic CRT. Full linker PDB, no LTCG or "
              "incremental link. The only build-side change is generated: an "
              "include-once stub for the SDK's fwpmu.h and a forced-include "
              "harness. No upstream file is changed. Linked and disassembled "
              "only, never executed or used to modify WFP.",
    ),
}
