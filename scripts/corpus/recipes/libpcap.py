"""libpcap - the packet-capture core, built for Linux (ELF) and Windows (PE).

Targeted by backlog issue #42: libpcap module-matched inside a traffic
monitoring implant. Nothing in the corpus covered it under any name.

Two axes, both built. The ELF half is the one implants of this kind are
usually built from: libpcap's default configuration, PF_PACKET capture
(pcap-linux.c), which is also what a distribution package contains. The PE
half is the same library against the Windows NPF backend (pcap-npf.c), which
needs the Npcap SDK. Without it the MinGW build stops, with CMake

    CMake Error at CMakeLists.txt:1820 (message):
      No supported packet capture interface was found.
      In order to build a version of libpcap that supports packet capture
      on Windows, you will need to install Npcap and the Npcap SDK, or
      WinPcap and the WinPcap SDK, and run cmake with -DPacket_ROOT=...

and the autotools route, `./configure --host=x86_64-w64-mingw32`, stops at
"configure: error: see the INSTALL for more info" (autotools is not
upstream's Windows path). `-DPCAP_TYPE=null` builds without the SDK
(622 functions on x64, 595 on x86 before the baseline filter) but cannot
capture and is not carried.

The Npcap SDK. npcap-sdk-1.17.zip (the newest on https://npcap.com/dist/ as of
2026-11), sha256 ab7e1a6cb8d07427e0071ec11be380bd9d2bb19ae6ab3f5ede0698c301638258
computed by this recipe's author: npcap.com publishes no checksum or
signature for it. It is a pinned `extra_sources` archive unzipped inside the
source tree at build time. No SDK file is committed; the artefacts contain
only libpcap's own code plus 27 one-instruction import thunks
(PacketOpenAdapter and the rest of Packet.dll's exports) that ld generates
from Packet.lib. Licence: the zip has no licence file. Its headers carry the
UC Berkeley BSD notice for the pcap headers and, in npcap-defs.h, "IMPORTANT
NPCAP LICENSE TERMS": Npcap is "not open source software and may not be
redistributed or used in other software without special permission from the
Nmap Project", the free edition being limited to five installs, with OEM
licences for redistribution. That text is about Npcap (driver and DLLs),
which this build neither contains nor redistributes; whether compiling
against the SDK headers and import library is covered is a question for the
maintainer, and is why the SDK is fetched at build time rather than stored.

How it links. MinGW ld links the SDK's MSVC-format import library
(Lib/Packet.lib, Lib/x64/Packet.lib) directly, so no gendef or dlltool step
is needed; the result imports packet.dll. Two command-line overrides are
needed and no source is patched: `-DPacket_LIBRARY=<path>/Packet.lib` (and
`-DPACKET_LIBRARY` for 1.9.x), because find_library does not find the .lib
under a cross toolchain even with Packet_ROOT set, and
`-DCMAKE_C_FLAGS=-D_Post_invalid_=`, because Packet32.h uses that MSVC SAL
annotation and mingw-w64's sal.h lacks it. 1.9.1 also needs
`-DCMAKE_CXX_COMPILER`, or its project() picks the host g++. This is
upstream libpcap's NPF build, not Npcap's own wpcap.dll (a modified fork):
the DLL is pcap.dll and the function set differs.

Remote capture, which is on in two of the three. Nothing here passes
ENABLE_REMOTE, so each version's own CMake default applies, and that default
changes inside the range built here. 1.9.1 and 1.10.5 set it ON for Windows
(`if(WIN32) option(ENABLE_REMOTE "Enable remote capture" ON)`,
CMakeLists.txt:128 and :492), so the rpcap client is compiled in; 1.11.0
defaults it OFF unconditionally and says why (CMakeLists.txt:506, "This
feature is experimental and is not ready for production use").

The artefacts say the same thing. Counting the recovered names that belong to
the remote sources - `rpcap_*`, `sock_*`, `pcap_remoteact_*`, `pcap_*_rpcap`,
`pcap_startcapture_remote`, `pcap_findalldevs_ex*`, `pcap_createsrcstr`,
`pcap_parsesrcstr`, `pcap_setsampling` and `pcapint_*srcstr_ex` - gives 37 in
1.9.1 and 42 in 1.10.5, the same count on x86 as on x64, covering
pcap-new.c, pcap-rpcap.c and sockutils.c end to end: authentication
(`rpcap_doauth`), the protocol header (`rpcap_process_msg_header`) and the
whole socket layer. 1.11.0 has 6, and they are not remote capture: they are
the `#else` stubs pcap.c and pcap-new.c compile when ENABLE_REMOTE is unset,
which is why the same six names, and no others, are in 1.11.0's ELF
artefacts too - where remote capture is certainly off, the Linux default
being OFF in every version.

Not rpcap over TLS in either case. 1.10.5's remote branch calls
`find_package(OpenSSL)` and takes it if it finds one; under
`CMAKE_FIND_ROOT_PATH=/usr/<host>` it finds none, and no artefact of this
recipe carries an OpenSSL symbol.

Per version. 1.9.1, 1.10.5 and 1.11.0 build for both architectures. 1.8.1
does not: its Windows CMake runs GenVersion.bat to write pcap_version.h
(`GenVersion.bat: Permission denied`, make error 127), and a batch file
cannot run on this host without wine or a patched CMakeLists. It also forces
HAVE_REMOTE and has no FindPacket module (it reads PACKET_DLL_DIR directly).
1.8.1 is therefore ELF only.

Measured on the PE artefacts (kept + removed = image): 1.9.1 x86 482 + 195 =
677, x64 533 + 186 = 719; 1.10.5 x86 517 + 195 = 712, x64 576 + 185 = 761;
1.11.0 x86 469 + 160 = 629, x64 507 + 149 = 656. PicHash overlap of the
10+ instruction functions between a PE artefact and the ELF artefact of the
same version is 9-13 on x86 (about 3%) and 0 on x64: the two containers
share almost no exact function hashes, so the Windows axis is new reference
data rather than a duplicate. Between PE versions it is 26-31%.

The baseline leaves unnamed libgcc emutls helpers in 1.10.5 and 1.11.0
(thread-local storage emulation, static in libgcc so they carry no symbol):
emutls_destroy, 24 instructions on x64 (PicHash 964b047c100ae19f) and 25 on
x86 (cf0d1991e4b23478), and emutls_alloc, 53 on x64 (7250612fb353dc1a) and 54
on x86 (07ebf5f89b023978). Not edited into the baseline; the known unnamed
___chkstk_ms stack probe is also present.

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

Old releases, added for the comment on issue #42 (libpcap 1.1.1 for an x64 set,
libpcap 0.7.x or a 2001-era release for an x86 set; the versions statically
linked into Penquin-family Linux samples). Linux ELF only, x86 and x64:

  * libpcap 0.6.2 (tarball dated 2001-02-06, the 2001-era release), 0.7.2
    (2003-02-26, the newest 0.7.x) and 1.1.1 (2010-04-06). 0.7.2 and 1.1.1
    verified against tcpdump.org's old DSA signing key 464D3CEB89E917F3
    (https://www.tcpdump.org/release/signing-key-DSA-464D3CEB89E917F3.asc;
    "Good signature from tcpdump.org (SIGNING KEY)"). tcpdump.org serves no
    signature for 0.6.2, so it is pinned by the sha256 of the download only.
    0.7.1 (2002-01-23, also unsigned) was built and dropped: 108 of 115 x64
    PicHashes (94%) are the same as 0.7.2's, the same near-duplicate call made
    for 1.10.1 above.
  * Before 0.9 the Makefile has only `all: libpcap.a`, no shared target, so
    libpcap.a is built in the source tree and linked with
    `$CC -shared -o libpcap.so $(ar t libpcap.a)` (the archive's own members).
    1.1.1 does have `make libpcap.so` and uses it out of tree like the later
    versions, with Bluetooth, CAN and libnl off (its only optional switches;
    usbmon capture, pcap-usb-linux.c, is always compiled in).
  * One define is needed on every one of them and no source is patched:
    `make CCOPT='-O2 -fPIC -fvisibility=hidden -DSIOCGSTAMP=0x8906'`. glibc's
    headers no longer provide SIOCGSTAMP, and every release stops at
    pcap-linux.c with

        error: 'SIOCGSTAMP' undeclared (first use in this function); did you
        mean 'SIOCGRARP'?    (1.1.1, pcap-linux.c:1555; 0.7.2 :594; 0.6.2 :435)

    0x8906 is the old x86 value the kernel still answers with the same struct
    timeval these releases pass.
  * These releases predate pcap's export macros, so -fvisibility=hidden hides
    every symbol: `nm -D --defined-only` lists no function in any of the six
    images, glibc is the only NEEDED entry, and the names are in .symtab.
    That is the shape of a statically linked copy.

Measured (kept + removed = total):

                x86                  x64
    0.6.2    269 + 5 = 274        254 + 4 = 258
    0.7.2    279 + 5 = 284        265 + 4 = 269
    1.1.1    464 + 8 = 472        437 + 4 = 441

PicHash overlap of functions with 10 or more instructions between the x64
images (the 32-bit PIC deltas make x86 overlap low everywhere, see the README):
0.6.2 : 0.7.2 80 shared (73% / 70%), 0.7.2 : 1.1.1 49 (43% of 0.7.2, 23% of
1.1.1), 1.1.1 : 1.8.1 26 (12% / 10%), 1.1.1 : 1.9.1 19 (9% / 7%), 0.7.2 : 1.9.1
14. The 1.1.1 image adds pcap-usb-linux.c, pcap-common.c, sf-pcap-ng.c and
fad-getad.c to the 0.7 set of bpf_*, gencode, grammar, optimize, pcap-linux,
pcap, savefile, scanner, inet, etherent and nametoaddr.

Windows axis of the old releases: not built. Their Windows backend is
WinPcap's (pcap-win32.c, fad-win32.c against WinPcap's Packet32.h and
Packet.lib); the tarballs build it from a Visual C++ 6 project
(Win32/Prj/libpcap.dsp), configure has no MinGW path and there is no CMake
build before 1.9, so a MinGW build would be a hand-written one. It was not
attempted; no build error exists to quote.
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
        notes="The Linux build of libpcap's default PF_PACKET configuration; "
              "the Windows NPF build is the sibling libpcap_<version> recipe "
              "(1.8.1 has none: its CMake runs a .bat). Needs flex and bison: "
              "release tarballs do not ship the generated grammar.c or "
              "scanner.c. Pinned by sha256 of tarballs whose GPG signatures "
              "verified (tcpdump.org publishes .sig, not sha256, files).",
    )


# Npcap SDK, the Windows capture backend's import libraries and headers. Pinned
# by a sha256 computed here: npcap.com publishes no checksum or signature for
# it. 1.17 is the newest on https://npcap.com/dist/ as of 2026-11.
_SDK = Source(url="https://npcap.com/dist/npcap-sdk-1.17.zip",
              sha256="ab7e1a6cb8d07427e0071ec11be380bd9d2bb19ae6ab3f5ede0698c301638258")

# The SDK is handed to CMake under both spellings the supported versions use:
# 1.9.x reads PACKET_DLL_DIR / PACKET_LIBRARY (FindPacket.cmake, upper case),
# 1.10 and later read Packet_ROOT / Packet_LIBRARY. A variable a version does
# not read is reported as unused and is harmless. The library is passed
# explicitly because find_library does not pick up the SDK's Packet.lib under
# a MinGW cross toolchain ("Could NOT find Packet (missing: Packet_LIBRARY)"
# with Packet_ROOT alone). MinGW ld links the MSVC-format import library
# directly, so no gendef/dlltool step is needed. The SDK keeps its 32-bit
# library in Lib/ and the 64-bit one in Lib/x64/.
# -D_Post_invalid_= is needed because the SDK's Packet32.h uses that MSVC SAL
# annotation, which mingw-w64's sal.h does not define. CMAKE_CXX_COMPILER is
# set because 1.9.1's project() enables C++ and otherwise picks the host g++,
# which fails its link test against the cross target.
_CMAKE_PE = ("unzip -q -o {npcap_sdk} -d npcap-sdk && "
             "cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
             "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx} "
             "-DCMAKE_RC_COMPILER={windres} "
             "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
             "-DBUILD_SHARED_LIBS=ON "
             "-DPACKET_DLL_DIR=$PWD/npcap-sdk -DPacket_ROOT=$PWD/npcap-sdk "
             "-DPACKET_LIBRARY=$PWD/npcap-sdk/Lib/$([ {bitness} = 64 ] && echo x64/)Packet.lib "
             "-DPacket_LIBRARY=$PWD/npcap-sdk/Lib/$([ {bitness} = 64 ] && echo x64/)Packet.lib "
             "\"-DCMAKE_C_FLAGS=-D_Post_invalid_=\"")


def _libpcap_pe(version, sha256, remote):
    return Recipe(
        family="libpcap",
        version=version,
        upstream="https://www.tcpdump.org/",
        license="BSD-3-Clause",
        source=Source(url="https://www.tcpdump.org/release/libpcap-%s.tar.gz" % version,
                      sha256=sha256),
        extra_sources={"npcap_sdk": _SDK},
        build=[BuildStep(_CMAKE_PE),
               BuildStep("cmake --build build-{arch} -j$(nproc) --target pcap")],
        artifacts=[Artifact(path="build-{arch}/run/pcap.dll", component="pcap.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        requires=["flex", "bison", "unzip"],
        build_flags="-O3 (CMake Release), NPF backend against Npcap SDK 1.17 "
                    "(npcap-sdk-1.17.zip), remote capture %s (this version's "
                    "own ENABLE_REMOTE default; no OpenSSL, so no rpcap over "
                    "TLS)" % remote,
        notes="upstream libpcap's Windows NPF backend (pcap-npf.c), not "
              "Npcap's own wpcap.dll; imports packet.dll. Built against the "
              "Npcap SDK 1.17 import library, fetched at build time and not "
              "stored: see the recipe docstring for the licence terms. "
              "Needs flex, bison and unzip. Pinned by sha256 of tarballs "
              "whose GPG signatures verified.",
    )


# Releases that predate the shared-library target (everything before 0.9 has
# only `all: libpcap.a`) and the out-of-tree configure. Built in the source
# tree (the pipeline unpacks one tree per architecture), compiled with
# -fPIC -fvisibility=hidden through CCOPT, then linked into a shared object
# from the archive's own members. No source is patched.
_CONFIGURE_OLD = "./configure"
# SIOCGSTAMP is gone from <asm/sockios.h> in current glibc/kernel headers
# (moved to <linux/sockios.h> as SIOCGSTAMP_OLD = 0x8906 on x86, with the
# struct timeval these releases pass it), so pcap-linux.c stops with
# "error: 'SIOCGSTAMP' undeclared". The value is supplied on the command line;
# no source is touched.
_CCOPT_OLD = "-O2 -fPIC -fvisibility=hidden -DSIOCGSTAMP=0x8906"
# 1.1.1 has no dbus/rdma/netmap/usb switches (usbmon capture is always
# compiled on Linux); Bluetooth, CAN and libnl are the optional ones it has.
_CONFIGURE_111 = ("mkdir -p build-{arch} && cd build-{arch} && "
                  "{source_root}/configure --disable-bluetooth --disable-can "
                  "--without-libnl")
_LINK_OLD = ("$CC -shared -o libpcap.so $(ar t libpcap.a)")


def _libpcap_old(version, sha256, signed, configure=_CONFIGURE_OLD,
                 shared_target=False):
    sig = ("Pinned by sha256 of a tarball whose GPG signature verified "
           "against tcpdump.org's DSA signing key 464D3CEB89E917F3."
           if signed else
           "tcpdump.org serves no signature for this release; pinned by "
           "sha256 of the download only.")
    if shared_target:
        steps = [BuildStep(_CONFIGURE_111),
                 BuildStep("make -j$(nproc) libpcap.so CCOPT='%s' " % _CCOPT_OLD, cwd="build-{arch}")]
        path = "build-{arch}/libpcap.so.%s" % version
    else:
        steps = [BuildStep(configure),
                 BuildStep("make -j$(nproc) libpcap.a CCOPT='%s'" % _CCOPT_OLD),
                 BuildStep(_LINK_OLD)]
        path = "libpcap.so"
    return Recipe(
        family="libpcap",
        version=version,
        upstream="https://www.tcpdump.org/",
        license="BSD-3-Clause",
        source=Source(url="https://www.tcpdump.org/release/libpcap-%s.tar.gz" % version,
                      sha256=sha256),
        build=steps,
        artifacts=[Artifact(path=path, component="libpcap.so")],
        toolchains=["linux_x86", "linux_x64"],
        requires=["flex", "bison"],
        build_flags="-O2 -fPIC -fvisibility=hidden -DSIOCGSTAMP=0x8906 (CCOPT override), default "
                    "Linux PF_PACKET backend",
        notes="The Linux build of an old libpcap release, as suggested in "
              "issue #42 for the Penquin-era samples. " + sig + " Needs flex "
              "and bison.",
    )



RECIPES = {
    "libpcap_1.1.1_linux": _libpcap_old(
        "1.1.1", "508cca15547e55d1318498b838456a21770c450beb2dc7d7d4a96d90816e5a85",
        signed=True, shared_target=True),
    "libpcap_0.7.2_linux": _libpcap_old(
        "0.7.2", "be38914f9f297e24b89c283390d872bce61c2be08f6fd989cb5acbd20330130d",
        signed=True),
    "libpcap_0.6.2_linux": _libpcap_old(
        "0.6.2", "a551ea7368b1b58e329535e2d4cea9f6a65ed79e1b5bdd8b5c07cb108bbae6e5",
        signed=False),
    "libpcap_1.8.1_linux": _libpcap(
        "1.8.1", "673dbc69fdc3f5a86fb5759ab19899039a8e5e6c631749e48dcd9c6f0c83541e"),
    "libpcap_1.9.1_linux": _libpcap(
        "1.9.1", "635237637c5b619bcceba91900666b64d56ecb7be63f298f601ec786ce087094"),
    "libpcap_1.10.5_linux": _libpcap(
        "1.10.5", "37ced90a19a302a7f32e458224a00c365c117905c2cd35ac544b6880a81488f0"),
    "libpcap_1.11.0_linux": _libpcap(
        "1.11.0", "596389bc8560ea027dff9db8aaf6c173d992366d9aef4baf5d7c6d180b4d49ad"),
    "libpcap_1.9.1": _libpcap_pe(
        "1.9.1", "635237637c5b619bcceba91900666b64d56ecb7be63f298f601ec786ce087094",
        "on"),
    "libpcap_1.10.5": _libpcap_pe(
        "1.10.5", "37ced90a19a302a7f32e458224a00c365c117905c2cd35ac544b6880a81488f0",
        "on"),
    "libpcap_1.11.0": _libpcap_pe(
        "1.11.0", "596389bc8560ea027dff9db8aaf6c173d992366d9aef4baf5d7c6d180b4d49ad",
        "off"),
}
