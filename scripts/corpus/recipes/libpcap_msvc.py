"""libpcap built with MSVC (wpcap.dll), beside the MinGW pcap.dll builds.

Work-in-progress docstring; measurements are added once the runner has
produced the artefacts.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from .libpcap import _SDK


# Flex and bison are not on the windows-2022 image and the tarballs carry
# only grammar.y and scanner.l. upstream's own appveyor.yml installs the same
# package, and libpcap's CMake looks for win_flex / win_bison by name.
_TOOLS = ("(where win_flex >nul 2>&1 && where win_bison >nul 2>&1) || "
          "choco install winflexbison3 -y --no-progress")

_UNPACK_SDK = "cmake -E tar xf {npcap_sdk}"

_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

# USE_STATIC_RT defaults to ON on MSVC in all four versions and would put
# /MT in the flags (1.9.1 and later rewrite /MD to /MT; 1.8.1 appends it).
# PACKET_DLL_DIR (1.8.1, 1.9.x) and Packet_ROOT (1.10 and later) both point
# at the SDK; the Find module picks Lib or Lib/x64 by pointer size.
# LIBRARY_NAME=wpcap is the documented Windows override (1.8.1 hardcodes it).
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
          '-DCMAKE_VERBOSE_MAKEFILE=ON -DBUILD_SHARED_LIBS=ON '
          '-DUSE_STATIC_RT=OFF -DLIBRARY_NAME=wpcap '
          '-DPACKET_DLL_DIR={source_root}/npcap-sdk '
          '-DPacket_ROOT={source_root}/npcap-sdk %s %s' % (_CFLAGS, _LDFLAGS))


def _libpcap_msvc(version, sha256, out_dir):
    return Recipe(
        family="libpcap",
        version=version,
        upstream="https://www.tcpdump.org/",
        license="BSD-3-Clause",
        source=Source(url="https://www.tcpdump.org/release/libpcap-%s.tar.gz" % version,
                      sha256=sha256),
        extra_sources={"npcap_sdk": _SDK},
        build=[
            BuildStep(_TOOLS),
            BuildStep("cmake -E make_directory npcap-sdk"),
            BuildStep(_UNPACK_SDK, cwd="npcap-sdk"),
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} --target wpcap"),
            BuildStep("dir build-{arch}%s" % out_dir.replace("/", "\\"),
                      allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}%s/wpcap.dll" % out_dir,
                            component="wpcap.dll",
                            pdb="build-{arch}%s/wpcap.pdb" % out_dir)],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release, /Zi added), NPF backend "
                    "against Npcap SDK 1.17; /DEBUG /Brepro /OPT:NOREF "
                    "/OPT:NOICF at link",
        notes="Same tarball as the MinGW recipe, built with cl against the "
              "Npcap SDK 1.17 import library (fetched at build time, not "
              "stored). Named wpcap.dll, the Windows library name, where "
              "the MinGW build is pcap.dll. Needs flex and bison "
              "(winflexbison3 is installed by the first build step).",
    )


RECIPES = {
    "libpcap_1.8.1_msvc": _libpcap_msvc(
        "1.8.1", "673dbc69fdc3f5a86fb5759ab19899039a8e5e6c631749e48dcd9c6f0c83541e", ""),
    "libpcap_1.9.1_msvc": _libpcap_msvc(
        "1.9.1", "635237637c5b619bcceba91900666b64d56ecb7be63f298f601ec786ce087094", "/run"),
    "libpcap_1.10.5_msvc": _libpcap_msvc(
        "1.10.5", "37ced90a19a302a7f32e458224a00c365c117905c2cd35ac544b6880a81488f0", "/run"),
    "libpcap_1.11.0_msvc": _libpcap_msvc(
        "1.11.0", "596389bc8560ea027dff9db8aaf6c173d992366d9aef4baf5d7c6d180b4d49ad", "/run"),
}
