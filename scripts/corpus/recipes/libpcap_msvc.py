"""libpcap built with MSVC (wpcap.dll), beside the MinGW pcap.dll builds.

libpcap is linked into Windows software built with cl at least as often as
with gcc, and data/libpcap held MinGW and Linux artefacts only. The same
source compiles to different machine code under cl (measured below), so this
is the axis that answers an MSVC-built sample. Same four tarballs, same
sha256 pins and the same Npcap SDK 1.17 pin as libpcap.py (imported from it,
so the two cannot drift); see that docstring for the SDK licence terms. A
separate registry entry because these steps are cmd.exe.

Unlike the MinGW recipe nothing is cross-linked: cl links the SDK's
Packet.lib natively, so the 1.8.1 problem there (GenVersion.bat cannot run
under a Linux host) does not exist, and 1.8.1 is built here: four versions,
both architectures. 1.8.1 is the only version with no MinGW twin.

Decisions, each read from the CMakeLists of the pinned tarballs.
  * The artefact is wpcap.dll, the Windows library name. 1.8.1 hardcodes it;
    1.9.1 and later default LIBRARY_NAME to pcap on Windows and document it
    as overridable, so -DLIBRARY_NAME=wpcap is passed (the target is then
    called wpcap, and DEFINE_SYMBOL pcap_EXPORTS keeps the dllexport
    working). The MinGW build is pcap.dll.
  * USE_STATIC_RT defaults to ON on MSVC in all four versions; it is turned
    OFF, because the mandate is /MD (the compile line read back from a log:
    /MD /O2 /Ob2 /DNDEBUG /Zi). The link line carries /INCREMENTAL:NO
    /DEBUG /Brepro /OPT:NOREF /OPT:NOICF and no /GL or /LTCG.
  * No .def file: the API is declspec(dllexport) in every version.
  * flex and bison are not on the windows-2022 image and the tarballs do not
    ship the generated parser. The first build step runs
    `choco install winflexbison3` (the package upstream's appveyor.yml uses;
    CMake finds win_flex and win_bison by name), so the workflow is
    untouched. `requires` is not used: it is checked before any step runs.
  * The SDK's 64-bit library is in Lib/x64. The 1.10 and later FindPacket
    module took Lib/Packet.lib on the x64 runner (LNK4272, 24 unresolved
    externals in the first dispatch), so the matching Packet.lib is copied to
    Packet-<arch>.lib and handed to CMake explicitly.
  * CMAKE_DISABLE_FIND_PACKAGE_OpenSSL=ON. 1.10 and later use OpenSSL if
    find_package finds one; the x64 runner has C:\\Program Files\\OpenSSL and
    pcap-new.c then fails on off_t, while the x86 leg found none. Switching
    it off makes both legs the same configuration (ENABLE_REMOTE stays at
    each version's default, as in the MinGW recipe).
  * Remote capture follows each version's own default, as in the MinGW
    recipe: ON for 1.8.1, which forces HAVE_REMOTE and has no option at
    all, and for 1.9.1 and 1.10.5, which set ENABLE_REMOTE ON under
    if(WIN32) (CMakeLists.txt:128 and :492); OFF for 1.11.0, which defaults
    it OFF unconditionally as experimental (CMakeLists.txt:506). The
    artefacts agree, counted by the recovered names belonging to the remote
    sources: 34 in 1.8.1 on both architectures, 48/49 in 1.9.1 and 55/58 in
    1.10.5 (x64/x86), and 6 in 1.11.0 - which are the `#else` stubs, the
    same six the MinGW and ELF 1.11.0 artefacts carry. The MinGW recipe's
    docstring used to say remote capture was off for all three of its
    versions; it is corrected to the above and the pair matches.

Measured on the artefacts (kept + removed = image):
    1.8.1   x86 606 + 164 = 770     x64 604 + 171 = 775
    1.9.1   x86 675 + 165 = 840     x64 672 + 171 = 843
    1.10.5  x86 715 + 168 = 883     x64 714 + 174 = 888
    1.11.0  x86 671 + 160 = 831     x64 664 + 165 = 829
(Removed are the MSVC runtime, Win32 and stdio functions the baseline
recognises; 160-174 per image, the CRT startup code a /MD DLL carries.)

Exported API against the MinGW build: identical. The exported name sets of
wpcap.dll and pcap.dll are the same for 1.9.1 (115), 1.10.5 (117) and
1.11.0 (112), on both architectures, so the difference between the two
families is code generation, not interface. 1.8.1 exports 112.

PicHash overlap of the 10+ instruction functions between the MinGW and MSVC
artefact of the same version and architecture is 0 in all twelve pairs
(1.9.1 x86 0 of 419 MSVC / 326 MinGW, x64 0 of 416 / 301; 1.10.5 x86 0 of
447 / 351, x64 0 of 444 / 326; 1.11.0 x86 0 of 433 / 317, x64 0 of 425 /
293), the same result as every earlier MSVC pass: the MSVC data is new
reference data, not a duplicate of the MinGW data.

Glue that survives the baseline, by name. Each kept artefact still holds
about 73-106 one-instruction import thunks (a `jmp [IAT slot]`) that the
linker emits for imported functions: the Npcap Packet* family (32 names,
PacketOpenAdapter, PacketGetNetInfoEx, ... PacketSetTimestampMode), and CRT,
Win32 and Winsock imports (_strdup, _fdopen, _fileno, _setmode, _close,
_open_osfhandle, _wfopen, _ftelli64, _wcserror_s, __intrinsic_setjmp/_setjmp3,
longjmp, clearerr, feof, ferror, fwrite, getc, rewind,
setvbuf, isspace, strtoul, strncpy_s, strerror_s, LoadLibraryA, GetVersion,
SetEvent, FormatMessageW, GetSystemDirectoryA, WSAStartup, WSACleanup,
getaddrinfo, freeaddrinfo, gethostbyname, getprotobyname, inet_pton, htonl,
ntohl, ntohs). fflush and puts (_fflush and _puts on x86) are no longer kept:
the wide-stdio baseline removes them from every image of this pass. Their
PicHash is 1165511d87767dcf on both architectures (70 of the 73
one-instruction functions on 1.11.0 x86, 65 of 76 on x64; the x64 ones that
are not it, 458924a8d07e5d36 x8 and d38af1f639c8eb6d x3, are libpcap's own
one-line functions such as pcap_free_datalinks). They are not removed because
the baseline is shared tooling this pass does not edit.
Names with a `$+0x...` suffix (6-14 on x86, 0-1 on x64, e.g. gen_scode$+0x749)
are SMDA entries inside a libpcap function and are libpcap code.

Sources: tcpdump.org tarballs by sha256, GPG-verified when libpcap.py was
written; the SDK as libpcap.py pins it.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from .libpcap import _SDK


# Flex and bison are not on the windows-2022 image and the tarballs carry
# only grammar.y and scanner.l. upstream's own appveyor.yml installs the same
# package, and libpcap's CMake looks for win_flex / win_bison by name.
_TOOLS = ("(where win_flex >nul 2>&1 && where win_bison >nul 2>&1) || "
          "choco install winflexbison3 -y --no-progress")

_UNPACK_SDK = "cmake -E tar xf {npcap_sdk}"

# The SDK keeps the 32-bit import library in Lib and the 64-bit one in
# Lib/x64. 1.10 and later FindPacket modules did not pick Lib/x64 on the
# runner (the x64 link took Lib/Packet.lib, LNK4272, 24 unresolved), so the
# right one is staged under a per-arch name and passed explicitly.
_STAGE_LIB = ('if "{bitness}"=="64" (copy /Y Lib\\x64\\Packet.lib Packet-{arch}.lib) '
              'else (copy /Y Lib\\Packet.lib Packet-{arch}.lib)')

_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

# USE_STATIC_RT defaults to ON on MSVC in all four versions and would put
# /MT in the flags (1.9.1 and later rewrite /MD to /MT; 1.8.1 appends it).
# PACKET_DLL_DIR (1.8.1, 1.9.x) and Packet_ROOT (1.10 and later) both point
# at the SDK and Packet_LIBRARY / PACKET_LIBRARY at the staged library.
# CMAKE_DISABLE_FIND_PACKAGE_OpenSSL keeps the runner's own OpenSSL out: 1.10
# and later optionally use it, the x64 runner has one in Program Files
# (pcap-new.c then fails on off_t) and the x86 one does not, so the two
# legs would otherwise not be the same build.
# LIBRARY_NAME=wpcap is the documented Windows override (1.8.1 hardcodes it).
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
          '-DCMAKE_VERBOSE_MAKEFILE=ON -DBUILD_SHARED_LIBS=ON '
          '-DUSE_STATIC_RT=OFF -DLIBRARY_NAME=wpcap '
          '-DPACKET_DLL_DIR={source_root}/npcap-sdk '
          '-DPacket_ROOT={source_root}/npcap-sdk '
          '-DPacket_LIBRARY={source_root}/npcap-sdk/Packet-{arch}.lib '
          '-DPACKET_LIBRARY={source_root}/npcap-sdk/Packet-{arch}.lib '
          '-DCMAKE_DISABLE_FIND_PACKAGE_OpenSSL=ON %s %s' % (_CFLAGS, _LDFLAGS))


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
            BuildStep(_STAGE_LIB, cwd="npcap-sdk"),
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
