"""SoftEther VPN Stable 4.44 built with MSVC, beside the Linux ELF recipes.

Same pinned commit and the same four programs as softether_vpn.py
(vpnserver, vpnbridge, vpnclient, vpncmd), for x86 and x64.

Why not MSBuild: the upstream Windows build is a Visual C++ 2008 solution
(src/SEVPN.sln, Format Version 10.00) of .vcproj projects. On windows-2022
`msbuild src\\SEVPN.sln` fails with `MSB4025: The project file could not be
loaded. Root element is missing.` and `msbuild src\\vpnserver\\vpnserver.vcproj`
with MSB4192 (the .vcproj format cannot be built by MSBuild). Converting the
projects would mean rewriting upstream files, so scripts/corpus/softether_msvc.py
reads the unmodified Release configurations of the same .vcproj files at build
time and runs cl, lib and link with the options, defines, include paths and
source lists they carry. Nothing under the source tree is edited.

What the helper takes from the projects (Mayaqua.vcproj, Cedar.vcproj and the
four program projects, Release|Win32 and Release|x64): /Ox /Ob0 /Oi- /GF- /Gy-
/GS- /Zp4 /W3 /wd4996, /D WIN32 NDEBUG _LIB|_WINDOWS|_CONSOLE VPN_SPEED (CPU_64
on x64), the include list, per-file C++ overrides (Win32Com.cpp and
WinJumpList.cpp as /TP /EHsc), the source lists, the two static libraries
(Mayaqua.lib, Cedar.lib) and the subsystem, stack size and delay-load list of
the programs. Precompiled headers, the .rc/version resource, the manifest and
the BuildUtil post-build steps are not reproduced; none of them contributes
code.

Deviations from a Visual Studio build of the unmodified projects (none edits
upstream source, but the images are NOT byte-identical to a Visual Studio
build of the unmodified solution):

  * /MD in place of the projects' RuntimeLibrary="0" (/MT);
  * /Z7 on the compile and /DEBUG on the link so a PDB is written, with
    /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO;
  * no precompiled header: CedarPch.h is included normally;
  * /ENTRY:mainCRTStartup stated explicitly (the programs define main() but
    two are /SUBSYSTEM:WINDOWS);
  * the vendored static OpenSSL, zlib and intel-aes libraries upstream ships
    under src/BuildFiles/Library are linked as upstream does, with
    /NODEFAULTLIB:LIBCMT and legacy_stdio_definitions.lib because they were
    built against the static CRT; the helper adds the system import
    libraries they and the GUI dialogs need (advapi32, comdlg32, ...) and, if
    the link reports an unresolved __iob_func, a generated one-function shim
    object (the OpenSSL objects were built for a CRT that exported it);
  * two files are compiled with extra command-line switches because the
    sources assume an older Windows SDK: Mayaqua/Network.c with
    /DNTDDI_VERSION=0x06010000 (the old SDK had no NTDDI_WIN7, so the
    "#if (NTDDI_VERSION >= NTDDI_WIN7)" guards in the repository's
    fixed_fwpm*.h copies were true; with the current SDK _WIN32_WINNT 0x0502
    hides FWPM_NET_EVENT1), and Cedar/CM.c with a generated force-included
    header that supplies the EXTENDED_NAME_FORMAT enum (secext.h's
    enumerators) that Mayaqua/Microsoft.h uses there without including
    security.h; /DWINDOWS_IGNORE_PACKING_MISMATCH is passed everywhere so the
    SDK accepts the projects' /Zp4.

Measured on windows-2022 (MSVC 14.44, SDK 10.0.26100.0), scoped dispatches
on scratch/softether-msvc, runs 42409611446, 42410237181, 42410784026 and
42411904117 (the one the data comes from):

  * run 1: /Zp4 against the current SDK stops every file that includes
    windows.h (winnt.h(2597): static_assert failed: 'Windows headers require
    the default packing option ...'), then Network.c (FWPM_NET_EVENT1) and
    CM.c (Microsoft.h(459): C2122 'PULONG': prototype parameter in name list
    illegal) on top;
  * run 2: after the packing define, Network.c and CM.c remain, and the
    link stops on advapi32 symbols (__imp_CryptAcquireContextW, ...);
  * run 3: every Mayaqua and Cedar source compiles and the libraries are
    produced; all four programs fail to link with four unresolved externals,
    Cedar.lib(WinUi.obj) __imp_GetOpenFileNameA/W and __imp_GetSaveFileNameA/W
    (comdlg32.lib missing; the __iob_func one is solved by the shim);
  * run 4: with comdlg32.lib (and a wider system library list) all four
    programs link on x86 and x64.

Vendored code. The images are three times the size of the Linux ELF leg
(about 6,300 functions) because the static OpenSSL 3.x, zlib and intel-aes
objects from src/BuildFiles/Library are linked in. Per x64 vpnserver image
(x86 is within 1%) before anything was excluded: 5,198 functions carry a
name that also occurs in the Linux ELF leg (SoftEther's own code), 6,812 a
name found in data/OpenSSL, 100 a name found in data/libzlib, 2,743 are
other named (ASN1_*_it and further OpenSSL items, intel-aes, delay-load
helpers) and 6,300 are anonymous (nearly all OpenSSL statics).

Recipe.exclude_functions (PR #94) now removes the part of it that can be
shown to be the library's, by exact function name, from the committed
archives (re-derived, not rebuilt): 23,092 functions from the eight images,
3,005 from each x64 image and 2,768 from each x86 image, 5,739 exact names.
recipes/_softether_vendored.py holds the tables and states the evidence,
counted by tier: P (PicHash equal to a same-named function of data/OpenSSL,
data/libzlib or data/libsodium) 17,224 functions, W (same name and
architecture, at least 80% opcode similarity, only where another function of
the identifier is P) 5,332, N (name only, where no family carries the code:
the 58 intel-aes exports and the 60 `ossl_*` functions of OpenSSL's legacy
provider) 536. It also lists what stays and why. In short, kept: the anonymous
statics (6,300 per x64 image, 6,219 per x86 image: a name pattern cannot
reach them; the link map the helper writes could, by source object, but that
needs an address-based exclusion and a rebuild that reproduces the committed
binary, so none was done); about 3,950 (x64) and 4,130 (x86) OpenSSL-named
functions and 87 zlib-named ones that have no P function in the recipe, the
vendored libraries being a different build from every family; import thunks
and inline helpers that merely share a PicHash with the library DLLs; the
delay-load helpers below; and SoftEther's own code.

Coverage (from data/SoftEtherVPN/provenance.json; kept = num_functions,
removed = removed_runtime_functions, excluded = excluded_function_count;
total = kept + removed + excluded, num_functions_before_exclusion = kept +
excluded):

  x64 vpnbridge 18148+271+3005=21424   x86 vpnbridge 18297+303+2768=21368
  x64 vpnclient 18145+271+3005=21421   x86 vpnclient 18296+303+2768=21367
  x64 vpncmd    18143+271+3005=21419   x86 vpncmd    18289+303+2768=21360
  x64 vpnserver 18148+271+3005=21424   x86 vpnserver 18297+303+2768=21368

PicHash overlap (functions of 10+ instructions), before -> after the
exclusion: x64 images carry 12,574 -> 11,952 distinct hashes, x86 about
12,646 -> 12,124 (server). Against the OpenSSL images of data/OpenSSL (main
and claude/corpus-openssl-add: 1.0.2u, 1.1.1w, 3.0.15, 3.5.8, MSVC, MinGW and
GCC) 750 -> 281 x64 and 395 -> 170 x86 hashes match, against data/libzlib 3
-> 2 x64 and 0 x86, against data/libsodium 2 -> 0 x64; what still matches is
the anonymous statics and the OpenSSL-named functions left in. Between the
four programs of one architecture the overlap stays nearly total: x64 server
shares 11,892 with bridge, 11,905 with client and 11,876 with cmd; x86
server shares 12,123, 12,100 and 12,079. x86 and x64 share zero hashes.
Against the Linux ELF leg only 3 x86 hashes match and none on x64. The x64
bridge is kept because it still differs from the server by 60 hashes (the
Linux x64 bridge was identical and was dropped).

Surviving glue: 145 (x86) / 147 (x64) delay-load thunks named
__imp_load_<API> (one PicHash each: x86 9181926168053310126, x64
5404308116032946042), __delayLoadHelper2 (x86 4522973873102832168, x64
6434761726659975131), three __tailMerge_<dll> (x86 875999747887486684, x64
621808072631181165) and, on x86, __except_handler3 (1253497258561142223).
These are generated by /DELAYLOAD and are not in the shared baseline;
reported rather than changing it.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _softether_vendored as _vendored


_COMPONENTS = ("vpnserver", "vpnbridge", "vpnclient", "vpncmd")

RECIPES = {
    "softether_vpn_stable_4.44_msvc": Recipe(
        family="SoftEtherVPN",
        version="4.44-9807-rtm",
        upstream="https://github.com/SoftEtherVPN/SoftEtherVPN_Stable",
        license="Apache-2.0",
        source=Source(
            git_url="https://github.com/SoftEtherVPN/SoftEtherVPN_Stable.git",
            git_ref="ed17437af9719ac66acab30faa29e375d613c35f"),
        build=[
            BuildStep("python {repo}/scripts/corpus/softether_msvc.py "
                      "{source_root} {arch}"),
        ],
        artifacts=[
            Artifact(path="build-{arch}/%s.exe" % name, component=name,
                     is_library=True, pdb="build-{arch}/%s.pdb" % name)
            for name in _COMPONENTS
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        exclude_functions=_vendored.patterns(),
        build_flags="/Ox /Ob0 /Oi- /GF- /Gy- /GS- /Zp4 /W3 /MD /Z7 (from the "
                    "upstream Release .vcproj, /MT replaced by /MD); link "
                    "/DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO",
        notes="Built by driving cl/lib/link from the unmodified Release "
              "configurations of the upstream .vcproj files; see the recipe "
              "module docstring. The statically linked vendored OpenSSL, "
              "zlib, intel-aes and libsodium-derived functions that are "
              "shown to be the library's (PicHash, opcode similarity or "
              "name; tiers in recipes/_softether_vendored.py) are excluded "
              "by exact name and counted in excluded_function_count; "
              "anonymous statics and OpenSSL-named functions without a "
              "matching function in data/OpenSSL stay in the image.",
    ),
}
