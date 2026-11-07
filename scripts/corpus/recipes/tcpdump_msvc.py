"""tcpdump 4.99.x built with MSVC, beside the Linux ELF and MinGW builds.

The MinGW recipe (tcpdump.py) says it plainly: tcpdump's Windows port is
written for MSVC first, and the MinGW images are the follow-up's stand-in. This
is the MSVC build, from upstream's own CMake project, with no patch: the
4.99.7 MinGW leg needs a recipe-applied sed on cmake/Modules/FindPCAP.cmake
(GNU ld rejects the MSVC link option /delayload:wpcap.dll and delayimp.lib);
link.exe accepts both, so here FindPCAP.cmake is used as shipped and wpcap.dll
is delay-loaded, as upstream intends. Nothing is patched, and these images are
byte-faithful builds of the unmodified tarballs.

Versions: 4.99.7, 4.99.5 and 4.99.3, the same tarballs (same sha256) as the
MinGW and ELF legs. 4.99.0 is 88% of 4.99.3 on PicHash overlap (see tcpdump.py)
and is not built here.

libpcap is not in the image. As in the MinGW leg the build links the Npcap SDK
1.17's wpcap.lib, the import library of Npcap's own wpcap.dll, so the PE
imports wpcap.dll and none of libpcap's code is in it. The SDK is the same zip
(sha256 pinned in _NPCAP_SDK, computed by tcpdump.py's author because
npcap.com publishes none); it is fetched at build time and not stored, for the
licence reason spelled out in tcpdump.py. WITH_CRYPTO=OFF as in the MinGW leg
(there is no libcrypto on the runner, and OpenSSL is a separate family).

How the SDK is found. cmake/Modules/FindPCAP.cmake on Windows does
find_path(PCAP_INCLUDE_DIR pcap.h) and, for a 64-bit target, sets
CMAKE_LIBRARY_ARCHITECTURE to x64 before find_library(PCAP_LIBRARY NAMES pcap
wpcap), which is exactly the SDK layout (Lib/ is 32-bit, Lib/x64 is 64-bit).
The recipe unpacks the zip into npcap-sdk/ and passes it as CMAKE_PREFIX_PATH,
so one command serves both architectures and the 32-bit leg cannot pick up the
64-bit library.

Flags. /MD (tcpdump's CMakeLists adds /MD again itself unless USE_STATIC_RT is
set; the repeat is harmless), /O2 /Ob2 /Zi, no /GL and no /LTCG; link
/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF. The per-configuration
variables are overridden, not CMAKE_C_FLAGS / CMAKE_EXE_LINKER_FLAGS, so CMake's
own initialisation (/machine on the 32-bit leg) stays in place; upstream's
LINK_FLAGS (/delayload:wpcap.dll) is appended to those at link time.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from .tcpdump import _NPCAP_SDK

_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_LDFLAGS = ('-DCMAKE_EXE_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DWITH_CRYPTO=OFF '
          '-DCMAKE_PREFIX_PATH={source_root}/npcap-sdk %s %s'
          % (_CFLAGS, _LDFLAGS))


def _tcpdump_msvc(version, sha256):
    return Recipe(
        family="tcpdump",
        version=version,
        upstream="https://www.tcpdump.org/",
        license="BSD-3-Clause",
        source=Source(url="https://www.tcpdump.org/release/tcpdump-%s.tar.gz" % version,
                      sha256=sha256),
        extra_sources={"npcap_sdk": _NPCAP_SDK},
        build=[
            BuildStep("cmake -E make_directory npcap-sdk"),
            BuildStep("cmake -E tar xf {npcap_sdk}", cwd="npcap-sdk"),
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} --target tcpdump"),
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/tcpdump.exe",
                            component="tcpdump.exe",
                            pdb="build-{arch}/tcpdump.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release, /Zi added), "
                    "WITH_CRYPTO=OFF, linked against the Npcap SDK 1.17 "
                    "wpcap.lib; /DEBUG /Brepro /OPT:NOREF /OPT:NOICF "
                    "/INCREMENTAL:NO at link, upstream's /delayload:wpcap.dll",
        notes="MSVC build of tcpdump's Windows port from upstream's CMake "
              "project, unpatched: imports (delay-loaded, as upstream "
              "intends) Npcap's wpcap.dll, libpcap is not in the image. "
              "Built against the Npcap SDK 1.17 import library, fetched at "
              "build time and not stored (licence terms in tcpdump.py). Same "
              "tarball as the MinGW and ELF recipes of this version. Built "
              "against the DLL runtime, so the MSVC C runtime is imported "
              "and stays attributed to data/MSVC.",
    )


RECIPES = {
    "tcpdump_4.99.7_msvc": _tcpdump_msvc(
        "4.99.7", "8be364e28d3b745ef1459b385cd2f4bc0e1ebad7a5d2ebdf70071d6c9b5b9a54"),
    "tcpdump_4.99.5_msvc": _tcpdump_msvc(
        "4.99.5", "8c75856e00addeeadf70dad67c9ff3dd368536b2b8563abf6854d7c764cd3adb"),
    "tcpdump_4.99.3_msvc": _tcpdump_msvc(
        "4.99.3", "ad75a6ed3dc0d9732945b2e5483cb41dc8b4b528a169315e499c6861952e73b3"),
}
