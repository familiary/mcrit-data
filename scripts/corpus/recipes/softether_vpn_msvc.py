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
    built against the static CRT.
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
