"""Wintun as Tailscale ships it: the signed wintun.dll from wintun.net.

The tracker issue for tailscale/tailcat (r0ny123/mcrit-data#44) names
wintun.dll as a sibling harvest: older Tailscale deployments the Kothamine
operators carried hold tailscaled.exe, tailscale.exe, tailscale-ipn.exe and
wintun.dll side by side. Wintun is WireGuard LLC's layer-3 TUN driver for
Windows; the DLL is its user-mode API and carries the kernel driver inside
its resources.

**Which version, and from where.** Not chosen here: tailscale pins it. The
v1.102.5 tree this branch builds (tsconst/wintun/wintun.go) says

    Version = "0.14.1"
    URL     = "https://www.wintun.net/builds/wintun-" + Version + ".zip"
    SHA256  = "07c256185d6ee3652e09fa55c0b673e2624b565e02c4b9091c79ca7d2f24ef51"

and that is the digest this recipe pins, so the image filed here is the one
Tailscale's own Windows build is made and tested against. 0.14.1 is also the
newest Wintun release. The download was checked against that digest.

**Harvested, not rebuilt.** Wintun's source (git.zx2c4.com/wintun, GPLv2) is
an MSBuild solution whose DLL embeds a driver signed by WireGuard LLC; a
rebuild cannot reproduce that signature or the embedded driver, and what a
sample carries is the wintun.net prebuilt, byte for byte. ``wintun/bin/amd64``
and ``wintun/bin/x86`` are taken; the arm and arm64 builds in the same zip
are not, because SMDA here reads x86 and x64 only.

**What compiled it**, read off the PE headers rather than the Linux host
that unpacks it: linker 14.29, Rich-header build 30136, i.e. MSVC v142
(Visual Studio 2019 16.11), so ``Artifact.producer`` is ``msvc142`` and the
README row says "as distributed upstream". Both DLLs name a PDB
(``...\\wintun\\Release\\{amd64,x86}\\wintun.pdb``) that is not published, so
only the fourteen exported ``Wintun*`` functions are named and
``min_named_ratio`` is 0. The C runtime is linked statically - the only
imports are kernel32 and ntdll - so the image carries MSVC CRT code that,
unnamed, no name-and-PicHash glue filter can remove; it is filed under this
family and is not Wintun's.

**Measured**, kept + removed = total: x86 811 + 0 = 811, x64 654 + 0 =
654; 606 and 459 of ten instructions or more (583 and 440 distinct
PicHashes), 15 named on each (the fourteen exports and the entry point).
Nothing is removed as runtime because the statically linked CRT is unnamed.
The two architectures share no PicHash at that floor, and the image shares
none with the tailscale family's Windows images, which are Go and load
wintun.dll rather than containing it.

**Not built: tailscale-ipn.exe.** The issue lists it beside wintun.dll. It
is Tailscale's Windows GUI, and its source is not in tailscale/tailscale:
v1.102.5 has no cmd/tailscale-ipn (its cmd/ holds tailscale, tailscaled,
systray and the server tools), so there is nothing to build from the open
tree. Only the signed binary in Tailscale's MSI installer exists, and that
is a harvest decision for the maintainer, not attempted here.

**Licence, recorded as a fact.** The prebuilt binaries are not under the
source's GPLv2: the zip's LICENSE.txt is WireGuard LLC's "Prebuilt Binaries
License", which grants use and forbids, among other things, reverse
engineering, disassembly and redistribution of the DLLs. This corpus commits
neither DLL; what is committed is the SMDA report and the MCRIT export
derived from it. Whether that is acceptable is the maintainer's call and is
flagged in the provenance licence field.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# The zip unpacks to wintun/, which the fetch makes the source root, and
# its bin/ names the 64-bit directory amd64 rather than x64, so the leg's
# DLL is copied to a fixed name first; the architecture in the stem comes
# from the PE header either way.
_PICK = ('d=x86; [ "{arch}" = x64 ] && d=amd64; '
         'cp "bin/$d/wintun.dll" wintun.dll && ls -l wintun.dll')

RECIPES = {
    "wintun_0.14.1_prebuilt": Recipe(
        family="wintun",
        version="0.14.1",
        upstream="https://git.zx2c4.com/wintun",
        license="Prebuilt Binaries License (WireGuard LLC), the LICENSE.txt "
                "inside wintun-0.14.1.zip: a non-exclusive right to use, "
                "with reverse engineering, decompiling, disassembling and "
                "redistributing the DLLs prohibited. The Wintun source is "
                "GPLv2, Copyright (c) 2018-2021 WireGuard LLC; the prebuilt "
                "binaries are not under it",
        source=Source(
            url="https://www.wintun.net/builds/wintun-0.14.1.zip",
            sha256="07c256185d6ee3652e09fa55c0b673e2624b565e02c4b9091c79ca7d2f24ef51"),
        build=[BuildStep(_PICK)],
        artifacts=[Artifact(path="wintun.dll", component="wintun.dll",
                            producer="msvc142")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="MSVC v142 (as distributed by WireGuard LLC: PE linker "
                    "14.29, Rich build 30136, static CRT); exact flags not "
                    "published",
        min_named_ratio=0,
        notes="Harvested, not rebuilt: the wintun.dll that wintun.net "
              "publishes in wintun-0.14.1.zip, pinned by the sha256 that "
              "tailscale v1.102.5 itself pins in tsconst/wintun/wintun.go, "
              "so this is the Wintun the Tailscale Windows client is built "
              "and tested against (tracker issue #44 names wintun.dll as a "
              "sibling harvest of the tailscale family). The producer is "
              "read off the PE headers (linker 14.29, Rich build 30136: "
              "MSVC v142), not inferred from the Linux host that unpacked "
              "it. The PDB the DLLs name is not published, so only the "
              "fourteen exported Wintun* functions are named; the MSVC C "
              "runtime is linked statically and its unnamed bodies stay in "
              "the image. The kernel driver embedded in the DLL's resources "
              "is data to SMDA and is not disassembled. The arm and arm64 "
              "DLLs of the same zip are not taken. Measured: x86 811 kept + "
              "0 removed = 811, x64 654 + 0 = 654, 606 and 459 of ten "
              "instructions or more; no PicHash shared between the two "
              "architectures or with the tailscale family.",
    ),
}
