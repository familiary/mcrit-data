"""libpcap - the packet-capture core, built for Linux and ELF.

Targeted by backlog issue #42: libpcap module-matched inside a traffic
monitoring implant. Nothing in the corpus covered it under any name.

Which axis, and why. The MinGW axis was tried first and does not work as
upstream ships it. Configuring the release tarball with CMake for either
cross compiler stops at

    CMake Error at CMakeLists.txt:1820 (message):
      No supported packet capture interface was found.
      In order to build a version of libpcap that supports packet capture
      on Windows, you will need to install Npcap and the Npcap SDK, or
      WinPcap and the WinPcap SDK, and run cmake with -DPacket_ROOT=...

and the autotools route, `./configure --host=x86_64-w64-mingw32`, stops at
"configure: error: see the INSTALL for more info" (it finds none of the BSD
or Linux capture mechanisms; autotools is not upstream's Windows path). The
Npcap SDK is a proprietary-licence download and is not on this host. Upstream
does document `-DPCAP_TYPE=null`, which configures and builds cleanly with no
SDK and no patching (pcap.dll, 622 functions on x64 and 595 on x86 before the
baseline filter) - but that is a library that cannot capture: it has no
pcap-npf backend, which is the half of libpcap that differs most from
the Linux one. That variant is a maintainer decision rather than something to
slip in under this family's name, so it is not built here. Implants of this
kind are overwhelmingly Linux, and the ELF build uses libpcap's *default*
configuration (PF_PACKET capture, pcap-linux.c), which is what a distribution
package, and so most statically linked copies, actually contain.

Sources. www.tcpdump.org publishes a detached GPG signature
(libpcap-X.tar.gz.sig) per release, not a sha256 file; the signatures of all
four tarballs below verified against the Tcpdump Group's package signing key
(RSA 1F166A5742ABB9E0249A8D30E089DEF1D9C15D0D, fetched from the same site, so
this checks integrity against the signer rather than independently of the
site). The pinned sha256 values are of those verified tarballs. The tarballs
do NOT ship generated parser sources: they carry grammar.y (grammar.y.in from
1.10) and scanner.l only, so building needs bison and flex on the host (git
tags need them too). Both are listed in `requires`; neither goes into the
image, since only their generated C does.

Build. Upstream's own configure, no source patch. Optional capture backends
that configure would otherwise enable if the host happens to have the library
(libnl, D-Bus, Bluetooth, RDMA, netmap, usbmon) are switched off, so the
artefact does not depend on what the build host has installed; libnl is the
one a distribution build normally has, which adds nl80211 monitor-mode code
this reference does not contain. Out of tree, one build directory per
architecture, shared object only (`make libpcap.so`): the same reasoning as
the rest of the Linux half, glibc is NEEDED rather than linked in, so no libc
body is filed under this family. configure already adds -fvisibility=hidden
itself (aclocal.m4 AC_LBL_CHECK_COMPILER_OPT), so unlike the header-only C++
recipes nothing has to be added, and measured 96 exported symbols either way.

Versions. Measured by PicHash overlap of functions with 10 or more
instructions between the x64 builds of the five candidates:

    1.8.1 vs 1.9.1 21-24%   1.9.1 vs 1.10.1 35%    1.10.1 vs 1.10.5 77-80%
    1.9.1 vs 1.10.5 31%     1.10.5 vs 1.11.0 49-53%  1.8.1 vs 1.11.0 11-13%

1.10.1 is a near duplicate of 1.10.5 and was dropped; 1.8.1 (Ubuntu 18.04),
1.9.1 (Ubuntu 20.04), 1.10.5 (the last 1.10 line, which is what 1.10.2-1.10.4
distributions are closest to) and 1.11.0 (new BPF/pcapng work) are each at
most about half shared with their neighbour. On x86 the overlap between any
two versions is lower still (3-16%) because 32-bit PIC bodies reach the GOT
through a per-image delta - see README, "The Linux half".
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_CONFIGURE = ("mkdir -p build-{arch} && cd build-{arch} && "
              "{source_root}/configure --disable-dbus --disable-bluetooth "
              "--disable-rdma --disable-netmap --disable-usb --without-libnl")


def _libpcap(version, sha256):
    return Recipe(
        family="libpcap",
        version=version,
        upstream="https://www.tcpdump.org/",
        license="BSD-3-Clause",
        source=Source(url="https://www.tcpdump.org/release/libpcap-%s.tar.gz" % version,
                      sha256=sha256),
        build=[BuildStep(_CONFIGURE),
               BuildStep("make -j$(nproc) libpcap.so", cwd="build-{arch}")],
        artifacts=[Artifact(path="build-{arch}/libpcap.so.%s" % version,
                            component="libpcap.so")],
        toolchains=["linux_x86", "linux_x64"],
        requires=["flex", "bison"],
        build_flags="-O2 -fPIC -fvisibility=hidden (set by upstream configure), "
                    "default Linux PF_PACKET backend; libnl, D-Bus, Bluetooth, "
                    "RDMA, netmap and usbmon disabled",
        notes="The ELF build only. A MinGW build needs the Npcap/WinPcap SDK "
              "(CMake stops with 'No supported packet capture interface was "
              "found'); `-DPCAP_TYPE=null` builds without it but cannot "
              "capture, so no PE artefact is carried. Needs flex and bison: "
              "release tarballs do not ship the generated grammar.c or "
              "scanner.c. Pinned by sha256 of tarballs whose GPG signatures "
              "verified (tcpdump.org publishes .sig, not sha256, files).",
    )


RECIPES = {
    "libpcap_1.8.1_linux": _libpcap(
        "1.8.1", "673dbc69fdc3f5a86fb5759ab19899039a8e5e6c631749e48dcd9c6f0c83541e"),
    "libpcap_1.9.1_linux": _libpcap(
        "1.9.1", "635237637c5b619bcceba91900666b64d56ecb7be63f298f601ec786ce087094"),
    "libpcap_1.10.5_linux": _libpcap(
        "1.10.5", "37ced90a19a302a7f32e458224a00c365c117905c2cd35ac544b6880a81488f0"),
    "libpcap_1.11.0_linux": _libpcap(
        "1.11.0", "596389bc8560ea027dff9db8aaf6c173d992366d9aef4baf5d7c6d180b4d49ad"),
}
