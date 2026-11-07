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

Measured on the committed artefacts (MSVC 19.44, kept + removed = image):
x64 4.99.3 2114 + 193 = 2307, 4.99.5 1962 + 193 = 2155, 4.99.7 2056 + 198 =
2254; x86 4.99.3 2113 + 204 = 2317, 4.99.5 1952 + 204 = 2156, 4.99.7 2054 + 210
= 2264. Of the kept functions 1583-1609 have 10 or more instructions (999-1029
distinct PicHashes), and 328-390 on x64 and 104-163 on x86 have one or two:
import thunks (jmp through the IAT) and, at 4.99.7, the `__imp_load_*`
delay-load thunks. PicHash overlap (10+ instructions) with the MinGW and ELF
image of the same version is 0 on both architectures, and of MSVC against the
MinGW images of other versions too, so the MSVC axis is new reference data.
Between MSVC versions on x64: 4.99.3/4.99.5 786 (78% of the smaller),
4.99.3/4.99.7 576 (57%), 4.99.5/4.99.7 619 (62%); on x86 769 (77%), 112 (11%)
and 119 (12%).

Glue that survives the baseline: no CRT- or SDK-named function of three to
nine instructions other than, on x86 4.99.7, ReadAcquire and ReadPointerAcquire (7 instructions,
PicHash 1188053738595351258) and _InlineInterlockedCompareExchangePointer (9,
2389241439520967849); the rest are the import thunks (1 instruction, PicHash
1253497258561142223) and the 4.99.7 delay-load thunks (2 instructions, PicHash
5404308116032946042 on x64, 9181926168053310126 on x86).
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
