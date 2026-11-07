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

Coverage (from data/SoftEtherVPN/provenance.json; kept = num_functions,
removed = removed_runtime_functions; total = kept + removed):

  x64 vpnbridge 21153+271=21424   x86 vpnbridge 21065+303=21368
  x64 vpnclient 21150+271=21421   x86 vpnclient 21064+303=21367
  x64 vpncmd    21148+271=21419   x86 vpncmd    21057+303=21360
  x64 vpnserver 21153+271=21424   x86 vpnserver 21065+303=21368

These images are three times the size of the Linux ELF leg (about 6,300
functions) because the static OpenSSL 3.x, zlib and intel-aes objects from
src/BuildFiles/Library are linked in. Nothing was filtered out. Per x64
vpnserver image (x86 is within 1%): 5,198 functions carry a name that also
occurs in the Linux ELF leg (SoftEther's own code), 6,812 carry a name found
in data/OpenSSL, 100 a name found in data/libzlib, 2,743 are other named
(ASN1_*_it and further OpenSSL items, intel-aes, delay-load helpers) and
6,300 are anonymous (nearly all OpenSSL statics). So roughly 75% of each
image is vendored code that would sit under SoftEtherVPN's name. A
Recipe.exclude_functions mechanism is not in this branch's base; the
pattern to exclude them is to drop every function whose object comes from
libeay32.lib, ssleay32.lib, zlib.lib or libintelaes.lib, using the
/MAP file the helper writes (build-<arch>/<program>.map).

PicHash overlap (functions of 10+ instructions): x64 images carry 12,574
distinct hashes (x86 about 12,646). Against data/OpenSSL (all msvc143 and
3.x mingw artefacts) 379 x64 / 123 x86 hashes match, against data/libzlib 3
x64 / 0 x86; the vendored OpenSSL is a different build from every OpenSSL
family here, so hash overlap greatly under-states the duplication that the
names show. Between the four programs of one architecture the overlap is
nearly total: x64 server shares 12,514 with bridge, 12,527 with client and
12,498 with cmd; x86 server shares 12,645, 12,622 and 12,584. x86 and x64
share zero hashes. Against the Linux ELF leg only 3 x86 hashes match and none on
x64. The x64 bridge is kept because it still differs from the server by 60
hashes (the Linux x64 bridge was identical and was dropped).

Surviving glue: 145 (x86) / 147 (x64) delay-load thunks named
__imp_load_<API> (one PicHash each: x86 9181926168053310126, x64
5404308116032946042), __delayLoadHelper2 (x86 4522973873102832168, x64
6434761726659975131), three __tailMerge_<dll> (x86 875999747887486684, x64
621808072631181165) and, on x86, __except_handler3 (1253497258561142223).
These are generated by /DELAYLOAD and are not in the shared baseline;
reported rather than changing it.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


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
        build_flags="/Ox /Ob0 /Oi- /GF- /Gy- /GS- /Zp4 /W3 /MD /Z7 (from the "
                    "upstream Release .vcproj, /MT replaced by /MD); link "
                    "/DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO",
        notes="Built by driving cl/lib/link from the unmodified Release "
              "configurations of the upstream .vcproj files; see the recipe "
              "module docstring.",
    ),
}
