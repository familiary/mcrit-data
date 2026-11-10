"""tcpdump 4.99.x - the packet-capture CLI, built for Linux (ELF) and Windows (PE).

Targeted by backlog issue #88: a tcpdump renamed `dsstatmond` and run as a
credential sniffer on compromised Ivanti Connect Secure appliances (Volexity).
The evidence is naming only, from one report, with no version, hash or stated
origin, and Ivanti ships its own tcpdump, so the binary may be the appliance's
stock build and not something the actor compiled. A match against this
family would show an unmodified tcpdump, not an actor's change. The build the
appliance ships is a distribution build whose compiler is unknown, so the
match is structural (the same source), not byte-exact. Related: #42 (libpcap).

Versions. The issue asks for a 4.99.x tag (master reads 5.0.0-PRE-GIT). All
eight 4.99 releases were built for x64 and compared by PicHash overlap of
functions with 10 or more instructions (libpcap 1.10.5 shared, libcrypto off):

    4.99.0 vs 4.99.1 95%   4.99.2 vs 4.99.3 100%  4.99.3 vs 4.99.4 97%
    4.99.0 vs 4.99.3 88%   4.99.3 vs 4.99.5 70%   4.99.5 vs 4.99.7 65%
    4.99.0 vs 4.99.5 64%   4.99.0 vs 4.99.7 46%   4.99.6 vs 4.99.7 98%

so 4.99.0-4.99.4 are one cluster (85-100%), 4.99.5 is a step (63-72% against
it) and 4.99.6/4.99.7 are another (50% against 4.99.0-4.99.4, 98% with each
other). 4.99.0 (the first release), 4.99.3 (Debian 12), 4.99.5 and 4.99.7 (the
latest 4.99) are built; 4.99.1, 4.99.2, 4.99.4 and 4.99.6 are each 95% or more
of a built neighbour and are not. On the committed ELF x64 artefacts the same
comparison gives 87% (4.99.0/4.99.3), 64% (4.99.0/4.99.5), 46% (4.99.0/4.99.7),
70% (4.99.3/4.99.5), 50% (4.99.3/4.99.7) and 65% (4.99.5/4.99.7). On x86 it is
1-4% between any two versions, because 32-bit PIC bodies embed the image's GOT
delta (see the corpus README, "The Linux half"), so on x86 every version is
separate reference data.

How libpcap is separated from tcpdump's own code. tcpdump links libpcap, and
data/libpcap (issue #42) already describes it, so the ELF build links libpcap
1.10.5 (the 1.10 line tcpdump 4.99 is released against) as a shared library
and it is NEEDED, not part of the image, which holds tcpdump's own code
(libnetdissect, tcpdump.c, fptype.c) and nothing of libpcap's. This was
measured on 4.99.5 x64 against the alternative: linked statically the image is
1329 functions against 943 dynamically (+386, 29% of it libpcap), and 281 of the
288 libpcap.so 1.10.5 functions of 10 or more instructions (98%) reappear in
it under tcpdump's name, a duplicate of data/libpcap; the dynamic image shares 1
of 627 PicHashes with libpcap.so. A distribution tcpdump is dynamic. A
statically linked sample then matches this family on tcpdump's code and
data/libpcap on libpcap's. libcrypto (OpenSSL 3.0.15, ESP decryption in
print-esp.c, which configure enables when it finds one) is dynamic for the
same reason; it adds 47 functions (12 of 10 or more instructions) to 4.99.5 x64.

Build (Linux). Both libraries are built from pinned tarballs into a private
prefix per architecture (see _elf_deps.py: libpcap 1.10.5, GPG-verified against
the Tcpdump Group package signing key 1F16 6A57 42AB B9E0 249A 8D30 E089 DEF1
D9C1 5D0D, and OpenSSL 3.0.15, the version data/OpenSSL carries), because the
x86 half has no 32-bit -dev packages on this host. tcpdump's own configure,
unpatched: --with-crypto --without-smi --without-cap-ng so the artefact does
not depend on which of libsmi and libcap-ng the host has. -O2 PIE, dynamic
glibc. All eight tarballs (4.99.0-4.99.7) verified against the same key; the
four built are pinned by the sha256 of the verified file. tcpdump's tarball
ships a generated configure, so no autotools are needed; libpcap's needs
flex and bison (see `requires`).

Windows (MinGW). tcpdump 4.99 has a Windows port: CMake against the Npcap SDK,
and the code is written for MSVC first. The MinGW build links the SDK's
wpcap.lib (the import library of Npcap's own wpcap.dll; libpcap is not built
and none of it is in the image, which imports wpcap.dll) and needs three
command-line settings, no source patch: -DPCAP_INCLUDE_DIR/-DPCAP_LIBRARY for
the SDK, -DSUITABLE_SNPRINTF_EXITCODE=0 (CMake cannot run the try_run test
when cross-compiling, and mingw-w64's snprintf is C99), and
-Dour_fstat=_fstati64 -D"our_statb=struct _stati64", because
netdissect-stdinc.h defines those two names only for _MSC_VER and for UN*X,
so MinGW stops at tcpdump.c:1105 without them. The SDK is
npcap-sdk-1.17.zip (sha256 as libpcap.py pins it, computed by the recipe's
author: npcap.com publishes none); no SDK file is committed. The zip has no
licence file; its Include/npcap-defs.h carries an "IMPORTANT NPCAP LICENSE
TERMS" notice saying Npcap is not open source software and may not be
redistributed or used in other software without special permission from the
Nmap Project. That text is about Npcap (driver and DLLs), which this build
neither contains nor redistributes; whether compiling against the SDK headers
and import library is covered is a question for the maintainer, and is why the
SDK is fetched at build time and not stored. 4.99.0, 4.99.3 and 4.99.5 build
unmodified. 4.99.6 was not tried.

4.99.7 needs a recipe-applied patch. Its cmake/Modules/FindPCAP.cmake sets, on
Windows, the MSVC link.exe option `/delayload:wpcap.dll` as PCAP_LINK_FLAGS
(a normal variable the module sets itself, so it cannot be overridden from
the command line; tcpdump's CMakeLists.txt passes it to LINK_FLAGS) and adds
`delayimp.lib` to PCAP_LIBRARIES; GNU ld stops with "cannot find
/delayload:wpcap.dll". The recipe edits the unpacked source before cmake runs
(sed on cmake/Modules/FindPCAP.cmake, nothing committed):

    -    set(PCAP_LINK_FLAGS /delayload:wpcap.dll)
    +    set(PCAP_LINK_FLAGS "")
    -    set(PCAP_LIBRARIES ${PCAP_LIBRARIES} delayimp.lib)
    +    # delayimp.lib dropped

Effect: wpcap.dll is an ordinary load-time import of the PE and not
delay-loaded, so the import table differs from an MSVC build; no tcpdump code
is changed (the SetDllDirectory call in main() is source and still compiled).
The 4.99.7 MinGW images are therefore NOT byte-identical to a build of
unmodified upstream, which does not build with MinGW at all.
PicHash overlap between the PE and ELF artefacts of the same version is 0 on
x64 and 5-7 hashes (about 1%) on x86; between PE versions 4.99.0/4.99.3 81-84%
and 4.99.5 against either 50-59% on x64 and 20-22% on x86, so the PE axis is
new reference data and four versions are kept. The 4.99.7 PE against the
other PE versions (functions of 10 or more instructions): x64 36% (4.99.0),
39% (4.99.3), 56% (4.99.5); x86 9%, 9%, 10%. Against the 4.99.7 ELF: 0 on x64
and 7 hashes on x86.

MSVC is built by tcpdump_msvc.py (4.99.3, 4.99.5, 4.99.7), unpatched, against
the same Npcap SDK import library.

Measured on the artefacts (kept + removed = image): ELF x64 4.99.0 1101 + 7 =
1108, 4.99.3 1106 + 7, 4.99.5 990 + 7, 4.99.7 992 + 7; ELF x86 4.99.0 1061 + 5,
4.99.3 1066 + 5, 4.99.5 998 + 5, 4.99.7 1002 + 7; PE x64 4.99.0 694 + 187,
4.99.3 669 + 188, 4.99.5 604 + 191, 4.99.7 608 + 191; PE x86 4.99.0 772 + 187,
4.99.3 748 + 188, 4.99.5 684 + 191, 4.99.7 683 + 193. About three quarters of an ELF artefact's functions carry a symbol (the rest are
PLT stubs and anonymous pieces), well above the 50% gate.

Glue that survives the baseline, by name and PicHash: on the four ELF x86
artefacts _init (11 instructions), deregister_tm_clones (18),
register_tm_clones (26), __do_global_dtors_aux (21) and __stack_chk_fail_local
(5), each with a different PicHash per image (the GOT delta), plus the
two-instruction __x86.get_pc_thunk.bp/.cx/.si and, on one of them, _start (16).
The x64 artefacts have none. The PE artefacts keep `_main`/`main`, which is
tcpdump's own entry point, and the 1-3 instruction `___p___argv`/`__p___argv`.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _elf_deps as deps


_NPCAP_SDK = Source(
    url="https://npcap.com/dist/npcap-sdk-1.17.zip",
    sha256="ab7e1a6cb8d07427e0071ec11be380bd9d2bb19ae6ab3f5ede0698c301638258")

# PKG_CONFIG_LIBDIR (not _PATH) so the host's own .pc files cannot be found:
# the x86 build must not pick up a 64-bit libpcap or libcrypto.
_TCPDUMP_CONFIGURE = (
    "mkdir -p build-{arch} && cd build-{arch} && "
    "PKG_CONFIG_LIBDIR=%s/lib/pkgconfig:%s/lib/pkgconfig "
    "{source_root}/configure --with-crypto --without-smi --without-cap-ng"
    % (deps.prefix("libpcap-1.10.5"), deps.prefix("openssl-3.0.15")))


def _tcpdump(version, sha256):
    return Recipe(
        family="tcpdump",
        version=version,
        upstream="https://www.tcpdump.org/",
        license="BSD-3-Clause",
        source=Source(url="https://www.tcpdump.org/release/tcpdump-%s.tar.gz" % version,
                      sha256=sha256),
        extra_sources={"libpcap_src": deps.LIBPCAP,
                       "openssl_src": deps.OPENSSL["3.0.15"]},
        build=[BuildStep(deps.openssl_step("3.0.15")),
               BuildStep(deps.libpcap_step()),
               BuildStep(_TCPDUMP_CONFIGURE),
               BuildStep("make -j$(nproc) tcpdump", cwd="build-{arch}")],
        artifacts=[Artifact(path="build-{arch}/tcpdump", component="tcpdump")],
        toolchains=["linux_x86", "linux_x64"],
        requires=["flex", "bison", "pkg-config", "perl"],
        build_flags="-O2 (upstream configure default), PIE, dynamic libpcap "
                    "1.10.5, libcrypto 3.0.15 and glibc",
        notes="tcpdump's own code only: libpcap 1.10.5 and OpenSSL 3.0.15 are "
              "built from pinned tarballs and linked as shared libraries, so "
              "none of their code is in the image (see data/libpcap, "
              "data/OpenSSL). Default PF_PACKET backend. Pinned by sha256 of "
              "a tarball whose GPG signature verified.",
    )


# 4.99.7 only. Recipe-applied patch to cmake/Modules/FindPCAP.cmake (see the
# docstring): drop the MSVC link.exe option and the delayimp.lib import library.
_FINDPCAP_SED = (
    "sed -i -e 's|^\\( *\\)set(PCAP_LINK_FLAGS /delayload:wpcap.dll)|"
    "\\1set(PCAP_LINK_FLAGS \"\")|' "
    "-e 's|^\\( *\\)set(PCAP_LIBRARIES .*delayimp.lib)|\\1# delayimp.lib dropped|' "
    "cmake/Modules/FindPCAP.cmake && "
    "test $(grep -c 'delayimp.lib dropped\\|PCAP_LINK_FLAGS \"\"' "
    "cmake/Modules/FindPCAP.cmake) = 2")


def _tcpdump_pe(version, sha256, patch_findpcap=False):
    patched = ("; %s only: cmake/Modules/FindPCAP.cmake patched by the " % version +
               "recipe (sed: PCAP_LINK_FLAGS /delayload:wpcap.dll -> empty, "
               "delayimp.lib dropped from PCAP_LIBRARIES), so wpcap.dll is "
               "load-time and not delay-loaded") if patch_findpcap else ""
    return Recipe(
        family="tcpdump",
        version=version,
        upstream="https://www.tcpdump.org/",
        license="BSD-3-Clause",
        source=Source(url="https://www.tcpdump.org/release/tcpdump-%s.tar.gz" % version,
                      sha256=sha256),
        extra_sources={"npcap_sdk": _NPCAP_SDK},
        build=[
            BuildStep("unzip -q -o {npcap_sdk} -d npcap-sdk"),
        ] + ([BuildStep(_FINDPCAP_SED)] if patch_findpcap else []) + [
            BuildStep(
                "cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
                "-DCMAKE_C_COMPILER={cc} -DCMAKE_RC_COMPILER={windres} "
                "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
                "-DPCAP_INCLUDE_DIR=$PWD/npcap-sdk/Include "
                "-DPCAP_LIBRARY=$PWD/npcap-sdk/Lib/$([ {bitness} = 64 ] && echo x64/)wpcap.lib "
                "-DWITH_CRYPTO=OFF -DSUITABLE_SNPRINTF_EXITCODE=0 "
                "\"-DCMAKE_C_FLAGS=-Dour_fstat=_fstati64 -D'our_statb=struct _stati64'\"",
                env={"CFLAGS": ""}),
            BuildStep("cmake --build build-{arch} -j$(nproc) --target tcpdump"),
        ],
        artifacts=[Artifact(path="build-{arch}/tcpdump.exe", component="tcpdump.exe")],
        toolchains=["mingw_x86", "mingw_x64"],
        requires=["unzip", "perl"],
        build_flags="-O3 (CMake Release), WITH_CRYPTO=OFF, linked against the "
                    "Npcap SDK 1.17 wpcap.lib" + patched,
        notes="MinGW build of the Windows port: imports Npcap's wpcap.dll, "
              "libpcap is not in the image. Built against the Npcap SDK "
              "1.17 import library, fetched at build time and not stored "
              "(licence terms in the recipe docstring). Not the MSVC "
              "build tcpdump's Windows port is written for."
              + ((" %s only: built from upstream source modified by " % version) +
                 "a recipe-applied sed on cmake/Modules/FindPCAP.cmake "
                 "(MSVC /delayload:wpcap.dll link option and delayimp.lib "
                 "removed, which GNU ld rejects); the image is NOT "
                 "byte-identical to a build of unmodified upstream."
                 if patch_findpcap else ""),
    )


RECIPES = {
    "tcpdump_4.99.0_linux": _tcpdump(
        "4.99.0", "8cf2f17a9528774a7b41060323be8b73f76024f7778f59c34efa65d49d80b842"),
    "tcpdump_4.99.3_linux": _tcpdump(
        "4.99.3", "ad75a6ed3dc0d9732945b2e5483cb41dc8b4b528a169315e499c6861952e73b3"),
    "tcpdump_4.99.5_linux": _tcpdump(
        "4.99.5", "8c75856e00addeeadf70dad67c9ff3dd368536b2b8563abf6854d7c764cd3adb"),
    "tcpdump_4.99.7_linux": _tcpdump(
        "4.99.7", "8be364e28d3b745ef1459b385cd2f4bc0e1ebad7a5d2ebdf70071d6c9b5b9a54"),
}

for _name, _version in (("4.99.0", "8cf2f17a9528774a7b41060323be8b73f76024f7778f59c34efa65d49d80b842"),
                        ("4.99.3", "ad75a6ed3dc0d9732945b2e5483cb41dc8b4b528a169315e499c6861952e73b3"),
                        ("4.99.5", "8c75856e00addeeadf70dad67c9ff3dd368536b2b8563abf6854d7c764cd3adb")):
    RECIPES["tcpdump_%s" % _name] = _tcpdump_pe(_name, _version)

# Added in the final sweep: the four 4.99 releases that were first measured
# and skipped as 95% or more of a built neighbour. Built now because a near
# duplicate is still committed with its overlap stated (see the docstring).
# Tarballs verified against the Tcpdump Group signing key (RSA
# 1F166A5742ABB9E0249A8D30E089DEF1D9C15D0D, good signature on all four).
_SWEEP = (("4.99.1", "79b36985fb2703146618d87c4acde3e068b91c553fb93f021a337f175fd10ebe"),
          ("4.99.2", "f4304357d34b79d46f4e17e654f1f91f9ce4e3d5608a1badbd53295a26fb44d5"),
          ("4.99.4", "0232231bb2f29d6bf2426e70a08a7e0c63a0d59a9b44863b7f5e2357a6e49fea"),
          ("4.99.6", "5839921a0f67d7d8fa3dacd9cd41e44c89ccb867e8a6db216d62628c7fd14b09"))
for _name, _version in _SWEEP:
    RECIPES["tcpdump_%s_linux" % _name] = _tcpdump(_name, _version)
    # 4.99.6 is the first release whose FindPCAP.cmake carries the MSVC
    # /delayload:wpcap.dll option, so it needs the same sed as 4.99.7.
    RECIPES["tcpdump_%s" % _name] = _tcpdump_pe(
        _name, _version, patch_findpcap=(_name == "4.99.6"))

RECIPES["tcpdump_4.99.7"] = _tcpdump_pe(
    "4.99.7", "8be364e28d3b745ef1459b385cd2f4bc0e1ebad7a5d2ebdf70071d6c9b5b9a54",
    patch_findpcap=True)
