"""tailscale-ipn.exe as Tailscale distributes it: the signed Windows GUI client
from Tailscale's own MSI installers.

The tracker issue for tailscale/tailcat (r0ny123/mcrit-data#44) lists
``tailscale-ipn.exe`` beside ``tailscaled.exe``, ``tailscale.exe`` and
``wintun.dll`` as the files older Tailscale folders in the Kothamine
operators' hands contain. The first two are built from source in the
``tailscale`` family (tailscale.py) and wintun.dll is the ``wintun`` family.
This is the remaining one. Its source is not in tailscale/tailscale (the
Windows GUI lives in Tailscale's closed repository; the binary's own build
info says ``path tailscale.io/win/gui``, ``mod tailscale.io v1.102.4+dirty``),
so the only reference that can exist is the binary Tailscale ships.

**Which version, and why it is not 1.102.5.** The tailscale family is pinned
at v1.102.5. Tailscale published no Windows installer for that release:
``pkgs.tailscale.com/stable/tailscale-setup-1.102.5.exe``, ``-amd64.msi`` and
``-x86.msi`` (and ``tailscale-setup-full-1.102.5.exe``) all answer HTTP 404,
while the same names for 1.102.4 and 1.104.1 answer 200; the stable index
lists 1.102.5 for the Linux packages only. 1.102.4 is the newest Windows
release at or before it, so that is what is harvested. It is one patch
release apart from the tailscaled and tailscale images in this family, not
the same build, and the README row says so. Older Windows installers than
the current stable ones are not kept by pkgs.tailscale.com in general, so
this pin may stop resolving; the digests below are what a copy must match.

    1.102.4 amd64  tailscale-setup-1.102.4-amd64.msi
        https://pkgs.tailscale.com/stable/tailscale-setup-1.102.4-amd64.msi
        sha256 80eb007e39dfebe17299fa1a09c79a8e1d934f76e0246c0817ebe3af675b7ef6
        (38,390,272 bytes; tailscale-ipn.exe 29,748,216 bytes,
        sha256 6aecde62777887a4259a3a08c28a6985cfc9960f15545e68a58fcc54fb556b28)
    1.102.4 x86    tailscale-setup-1.102.4-x86.msi
        https://pkgs.tailscale.com/stable/tailscale-setup-1.102.4-x86.msi
        sha256 a8bda9fb254374bb13d46ebf02b6ffba4ed009a739580be511aa7afa8dddd42d
        (37,450,240 bytes; tailscale-ipn.exe 28,594,168 bytes,
        sha256 6db4a169a16b4214a6eb65b871a937a2c6cc44d89bc0666a1fd18b48e42e9257)

**Signature.** Both tailscale-ipn.exe images carry an Authenticode signature
by "Tailscale Inc." (DigiCert Trusted G4 Code Signing RSA4096 SHA384 2021
CA1, serial 0E072778983CE8A4E170BF6E51E3D225, valid 2026-06-02 to
2027-06-30, signed 2026-09-10). ``osslsigncode verify`` finds the file
digest in the signature equal to the digest it recomputes (SHA256 24470C36...
for x64, 8BB18082... for x86). The certificate chain was not validated
against a trust store on this host; the pin is the sha256 of the installer.

**Harvested, not rebuilt, and nothing is executed.** The MSI is unpacked by
``7z`` (fetch.py reads ``.msi`` as a container) into an empty directory; the
GUI is the MSI stream ``ClientGUIx64`` (amd64) or ``ClientGUI32`` (x86),
which is copied to ``tailscale-ipn.exe``. It is byte-identical to the
``Tailscale/tailscale-ipn.exe`` that ``msiextract`` installs from the same
package (sha256s above).

**What compiled it**, read off the binary: Go 1.26.6 (``go1.26.6`` in its
build info), so ``Artifact.producer`` is ``go1.26.6`` and the README says "as
distributed upstream". The same toolchain version builds the tailscale
family here. Link flags and tags are not published (the build info records
none), so ``build_flags`` says so. The Go runtime and standard library are
removed by symbol name with the Go glue filter (``glue_filter="go"``), as in
tailscale.py; the counts are in the README row and provenance.json.

**Measured**, kept + removed = total (no excluded functions): x64 20,752 +
11,940 = 32,692; x86 21,321 + 12,252 = 33,573. Functions of 10+ instructions:
x64 14,118 (8,556 distinct PicHashes), x86 20,648 (10,978). PicHash overlap
(10+ instructions) with the tailscale family's v1.102.5 images, same
architecture: x64 with tailscaled 2,613 (MinGW build) / 2,205 (Linux build)
and with tailscale 1,840 / 2,982; x86 with tailscaled 1,043 and tailscale 685
(MinGW builds; the Linux x86 images share none with it). The GUI is built from
the same ``tailscale.com`` module the daemon is, so that share is the same
code; it is left in the image, not removed.

**Licence, recorded as a fact.** The sources of tailscale.com are
BSD-3-Clause; the Windows GUI is part of Tailscale's proprietary Windows
client and is distributed under Tailscale's terms, not under the BSD licence.
This corpus commits neither MSI nor the executable; what is committed is the
SMDA report and the MCRIT export derived from it. Whether that is acceptable
is the maintainer's call.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_VERSION = "1.102.4"
_LICENSE = ("Tailscale Inc. proprietary Windows client binary (tailscale.io/"
            "win/gui, not in tailscale/tailscale); the tailscale.com module "
            "it is built from is BSD-3-Clause")
_FLAGS = ("go1.26.6 gc (as distributed by Tailscale Inc.: build info "
          "path tailscale.io/win/gui, mod tailscale.io v1.102.4+dirty); "
          "link flags and tags not published")
_NOTES = (
    "Harvested, not rebuilt: tailscale-ipn.exe, the Windows GUI client, from "
    "Tailscale's signed %(msi)s (%(url)s, sha256 %(sha)s), unpacked with 7z "
    "(MSI stream %(stream)s) and never executed. Authenticode signature by "
    "Tailscale Inc. (DigiCert G4 code signing CA); osslsigncode confirms "
    "the signed digest equals the recomputed one, the chain was not "
    "validated against a trust store. Version 1.102.4, not the 1.102.5 the "
    "rest of the family is pinned at: pkgs.tailscale.com answers 404 for "
    "every 1.102.5 Windows installer, so this is the newest Windows release "
    "at or before it and one patch release apart from the tailscaled and "
    "tailscale images. The source is not in tailscale/tailscale. Compiler "
    "Go 1.26.6 from the binary's build info; the Go runtime and standard "
    "library are removed by the Go glue filter. The tailscale.com packages "
    "it shares with tailscaled stay in the image.")


def _ipn(toolchain, msi, sha256, stream):
    url = "https://pkgs.tailscale.com/stable/" + msi
    return Recipe(
        family="tailscale",
        version=_VERSION,
        upstream="https://pkgs.tailscale.com/",
        license=_LICENSE,
        source=Source(url=url, sha256=sha256),
        build=[BuildStep("cp %s tailscale-ipn.exe && ls -l tailscale-ipn.exe"
                         % stream)],
        artifacts=[Artifact(path="tailscale-ipn.exe",
                            component="tailscale-ipn.exe",
                            producer="go1.26.6")],
        toolchains=[toolchain],
        glue_filter="go",
        build_flags=_FLAGS,
        notes=_NOTES % {"msi": msi, "url": url, "sha": sha256,
                        "stream": stream},
    )


RECIPES = {
    "tailscale_ipn_1.102.4_x64_prebuilt": _ipn(
        "mingw_x64", "tailscale-setup-1.102.4-amd64.msi",
        "80eb007e39dfebe17299fa1a09c79a8e1d934f76e0246c0817ebe3af675b7ef6",
        "ClientGUIx64"),
    "tailscale_ipn_1.102.4_x86_prebuilt": _ipn(
        "mingw_x86", "tailscale-setup-1.102.4-x86.msi",
        "a8bda9fb254374bb13d46ebf02b6ffba4ed009a739580be511aa7afa8dddd42d",
        "ClientGUI32"),
}
