"""SoftEther VPN Developer Edition 5.x, built from unmodified source for Linux.

Tracker issue #51 names both lines of SoftEther: Stable 4.x
(SoftEtherVPN_Stable, which softether_vpn.py and softether_vpn_msvc.py
build) and the Developer Edition 5.x at SoftEtherVPN/SoftEtherVPN, the one
whose CMake/vcpkg build the issue lists. This is the 5.x half, pinned at tag
5.2.5189 (commit 4db1b36b102e35e01369e02f46a4044a740deab4), the newest tag;
its submodules (cpu_features, tinydir, BLAKE2, libhamcore, liboqs and
oqs-provider) are fetched at the commits the tag records and listed in
provenance.

**The artefacts are the two libraries.** 5.x builds Cedar and Mayaqua as
shared objects, libcedar.so and libmayaqua.so, and vpnserver, vpnbridge,
vpnclient and vpncmd are each a 46-line main() that calls into libcedar, so
the libraries are where the code is and the four programs are not taken.
Upstream's ./configure is ``cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo``, which
is used here (-O2 -g -DNDEBUG, plus src/CMakeLists.txt's -fsigned-char).
OpenSSL 3.0, zlib, readline and ncurses are the host's (Ubuntu 24.04) and
libsodium the matching Ubuntu package, staged and pinned by sha256; all are
linked dynamically, so none of their code is in the images.

**Vendored code, excluded by name** (_softether5_vendored.py): with an
OpenSSL 3.x host upstream's OQS_ENABLE defaults on, so liboqs and the OQS
provider are statically linked into libmayaqua.so, beside google/
cpu_features; libcedar.so compiles BLAKE2's blake2s. Every function name
defined in those archives and objects of this build, and in none of
SoftEther's own objects, is excluded - the membership test the musl XMRig
recipes use - and counted in provenance. data/BLAKE2 carries BLAKE2; there
is no liboqs, oqs-provider or cpu_features family to file the rest under.

**Measured**, kept + removed as runtime glue + excluded = total:

    x64 libcedar.so     5179 + 4 +    7 = 5190   (2900 of 10+ instructions)
    x64 libmayaqua.so   2615 + 4 + 1226 = 3845   (1624 of 10+ instructions)
    x86 libcedar.so     5173 + 7 +    7 = 5187   (3123 of 10+ instructions)
    x86 libmayaqua.so   3024 + 9 +  873 = 3906   (1842 of 10+ instructions)

The glue removed is the ELF start-up set (_init, frame_dummy,
register_tm_clones, deregister_tm_clones, __do_global_dtors_aux). The
x64 excluded functions are liboqs 860 (844 names), oqs-provider 261,
cpu_features 105 and blake2s 7. Unnamed functions stay: 1852 of
libcedar.so's 1854 and 475 of libmayaqua.so's 543 are three instructions or
fewer (PLT stubs into the shared libraries).

**PicHash overlap** (10+ instructions): libcedar.so and libmayaqua.so share
25; against the Stable 4.44 x64 ELF programs (GCC 14) libcedar.so shares 3
and libmayaqua.so 1, and against the 4.44 MSVC and x86 images nothing, so
5.x is a reference of its own rather than a re-run of 4.x.
On x86 the two libraries share 4, x86 and x64 share none, and against
the Stable 4.44 x86 ELF programs libcedar.so shares 42 and libmayaqua.so
31 (none against the 4.44 MSVC images). The x86 build adds -msse2, which
libcedar's 3rdparty/BLAKE2/sse/blake2s.c needs on GCC's i686 default, and
uses liboqs's own .CMake/toolchain_x86.cmake so liboqs selects its 32-bit
code; 30 liboqs Keccak names occur only in the x86 archive and are in the
exclusion table with the rest. x86 glue removed also includes libgcc's
64-bit division helpers and __x86.get_pc_thunk.*.

**MinGW x86 and x64: built, from a patched build tree.** The images are
NOT byte-identical to a build of unmodified upstream. Configuring with
x86_64-w64-mingw32-gcc first failed in CMake's own compiler check, because
src/CMakeLists.txt appends MSVC switches under if(WIN32) whatever the
compiler: "x86_64-w64-mingw32-ld: cannot find /guard:cf: No such file or
directory" (and /DYNAMICBASE, /CETCOMPAT), then "CMake will not be able to
correctly generate this project" at src/Cedar/CMakeLists.txt:5. Before
configuring, the recipe runs scripts/corpus/softether5_mingw.py on the
cloned tree, which (its docstring has every line of it):

  - deletes those four lines from src/CMakeLists.txt:
        set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} /Qspectre")
        set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} /guard:cf")
        set(CMAKE_EXE_LINKER_FLAGS  "${CMAKE_EXE_LINKER_FLAGS} /guard:cf /DYNAMICBASE")
        set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} /CETCOMPAT")
  - adds src/PenCore/pencore.c and pencore.rc as symlinks to PenCore.c and
    PenCore.rc (CMake's generate step: "Cannot find source file:
    pencore.c");
  - writes a header directory, first on the include path: case aliases for
    the SDK headers upstream spells in mixed case (WinSock2.h, DbgHelp.h,
    ShlObj.h, ...; cfg.h resolves to Mayaqua's Cfg.h, as on NTFS); prsht.h
    and fwpmu.h wrappers adding the SDK names mingw-w64 11 lacks
    (PSWIZBF_ELEVATIONREQUIRED, PSTMSG, PROPSHEETHEADER[AW]_V2,
    FWPM_SESSION_FLAG_DYNAMIC, FWPM_FILTER_FLAG_PERMIT_IF_CALLOUT_UNREGISTERED,
    FWPM_LAYER_INBOUND_IPPACKET_V4/V6); a natupnp.h, which mingw-w64 does not
    ship, declaring IUPnPNAT and the static port-mapping interfaces in the
    type library's method order; and in the WinSock2.h alias __forceinline
    without mingw's extern, __try/__except as if (1)/else if (0) (GCC has
    no SEH in C, so Win32.c's MsSetThreadName raises its exception without
    a handler) and, for C++ only, Key.h's three-value CRYPTO_KEY_TYPE enum
    ahead of Types.h's forward typedef;
  - writes libDbgHelp.Lib.a, libPsapi.Lib.a, libSecur32.Lib.a and
    libWtsApi32.Lib.a symlinks to mingw's import libraries ("cannot find
    -lDbgHelp.Lib").

No upstream .c or .h file is changed. Beyond that, by flag: -D_WIN32_WINNT=
0x0600 (the Vista value MayaType.h sets when nothing has; mingw predefines
0x0A00, which with MayaType.h's NTDDI_VISTA left "unknown type name
'IKEEXT_EM_POLICY1'"), -DSKIP_CPU_FEATURES (upstream's own switch;
cpu_features is only added under if(UNIX)), CMAKE_SYSTEM_PROCESSOR AMD64 or
x86 for liboqs, -msse2 on x86 as on Linux, and -lstdc++ -lshlwapi in front
of CMake's default C standard libraries (Cedar's two .cpp files end up in
C-linked programs: "undefined reference to `__gxx_personality_seh0'";
"undefined reference to `__imp_SHStrDupW'" from mingw's inline
InitPropVariantFromString). The vcpkg path's unofficial-sodium is never
reached: without VCPKG_TARGET_TRIPLET, src/Cedar/CMakeLists.txt finds
libsodium through pkg-config. OpenSSL 3.0.15, zlib 1.3.1 and libsodium
1.0.20 are built inside the recipe from pinned tarballs as DLLs and only
imported (vpnserver.exe imports libcrypto-3-x64.dll, libssl-3-x64.dll,
zlib1.dll, libsodium-26.dll and libstdc++-6.dll), so none of their code is
in the images.

Cedar and Mayaqua are static libraries on Windows, so the program is the
image, and only vpnserver.exe is taken: on x64 vpnbridge, vpnclient and
vpncmd were linked too and define exactly vpnserver's function symbols,
except that vpncmd has main/SetConsoleTitleA where the others have
WinMain, StartProcess and StopProcess. liboqs, the OQS provider and blake2s
are statically linked and excluded by exact name with the same membership
test on that build's liboqs.a, liboqsprovider.a and blake2s.c.obj
(_softether5_vendored.py; seven MinGW-only names, GCC .part.0/.constprop.0
clones, are kept apart in MINGW_NAMES; x86 matches them behind i686's
leading underscore). Measured, kept + removed as runtime glue + excluded =
total:

    mingw13 x64 vpnserver.exe  8092 + 156 + 748 = 8996  (5808 of 10+ instructions, 5380 distinct PicHashes)
    mingw13 x86 vpnserver.exe  7725 + 162 + 747 = 8634  (6118 of 10+ instructions, 5607 distinct PicHashes)

PicHash overlap (10+ instructions): x86 and x64 share none. The x64 image
shares nothing with the 5.x x64 ELF libraries or the 4.44 x64 ELF programs
and 3 hashes with each 4.44 MSVC x64 program; the x86 image shares 68 with
x86 libcedar.so, 44 with x86 libmayaqua.so, 111 with each 4.44 x86 ELF
program and nothing with the 4.44 MSVC x86 programs. Unnamed functions:
399 on x64 (29 of 10+ instructions), 6 on x86 (1). Named survivors that are
runtime rather than SoftEther: the libstdc++ import thunks __cxa_begin_catch,
__cxa_end_catch and __gxx_personality_seh0/_v0 (one instruction each,
PicHash 1253497258561142223), the mingwex __mingw_aligned_malloc family
(x64 __mingw_aligned_malloc 1432033393685044057, x86
___mingw_aligned_malloc 16357674226355305341), mingw's inline stdio as
twelve printf.constprop.0 copies (x64 63033854732689302, x86
5331446925571218161) and one C++ printf(char const*, ...) (x64
680774687785349816, x86 9440566005262149013), and on x86 __configthreadlocale
and __exit; none of them is in the shared MinGW glue baseline.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _softether5_vendored as _vendored


_UBUNTU = "http://archive.ubuntu.com/ubuntu/pool/main"

# libsodium is the one build dependency the host does not carry as a -dev
# package. It is staged from the Ubuntu 24.04 packages that match the host's
# own runtime, pinned by sha256, and found through pkg-config with a sysroot
# so nothing is installed. It is linked dynamically, like OpenSSL, zlib,
# readline and ncurses, so none of its code enters the images.
_DEPS_X64 = {
    "sodium_dev": Source(
        url=_UBUNTU + "/libs/libsodium/libsodium-dev_1.0.18-1ubuntu0.24.04.1_amd64.deb",
        sha256="bd3e8cd6ab8cf731d8a8a15333831b9081a94ebefe22236fc8713975fe7a6d3a"),
    "sodium_rt": Source(
        url=_UBUNTU + "/libs/libsodium/libsodium23_1.0.18-1ubuntu0.24.04.1_amd64.deb",
        sha256="74d6f8fbd65f7f71b6f4f4223bef5fb57c1c14cd4e9ce788ead2b88e8c3ee236"),
}
_DEPS_X86 = {
    "sodium_dev": Source(
        url=_UBUNTU + "/libs/libsodium/libsodium-dev_1.0.18-1ubuntu0.24.04.1_i386.deb",
        sha256="46db1461d7365c8f73456987bcd915e4b46d384c8d0b64226b4d224dcf958e0e"),
    "sodium_rt": Source(
        url=_UBUNTU + "/libs/libsodium/libsodium23_1.0.18-1ubuntu0.24.04.1_i386.deb",
        sha256="3e555827d1b6afe96fdf5b46413a5ff9d390428ac403bd021ef5323d8e1183e8"),
    "readline_dev": Source(
        url=_UBUNTU + "/r/readline/libreadline-dev_8.2-4build1_i386.deb",
        sha256="195fd50dee863995a29a0ac26aab9268ccc82dc7764a5b8f41a424162453228b"),
    "readline_rt": Source(
        url=_UBUNTU + "/r/readline/libreadline8t64_8.2-4build1_i386.deb",
        sha256="d34dd34bf9ba9fa5fac457b48935b32cc21667b82109dbd634d93b82e9a4a913"),
    "ncurses_dev": Source(
        url=_UBUNTU + "/n/ncurses/libncurses-dev_6.4+20240113-1ubuntu2_i386.deb",
        sha256="66e7047726e01cf5e12115c9011fc5c96e7975f245d39bc7fafd28730b5f41fb"),
    "ncurses_rt": Source(
        url=_UBUNTU + "/n/ncurses/libncurses6_6.4+20240113-1ubuntu2_i386.deb",
        sha256="56b1b4c0254a5eb02e8ccc03b323f4092cbd75ac3d80d11540f89ef40c91c91f"),
    "ncursesw_rt": Source(
        url=_UBUNTU + "/n/ncurses/libncursesw6_6.4+20240113-1ubuntu2_i386.deb",
        sha256="6393ad9d4eca8dcec8aa28eec9881dbabbd241eb910099abeafab33056eb7d71"),
    "tinfo_rt": Source(
        url=_UBUNTU + "/n/ncurses/libtinfo6_6.4+20240113-1ubuntu2_i386.deb",
        sha256="66af73bb26395ccc8a8b9f7b4f7854ba38ae6d00602ab8a70dda30af77910057"),
}


def _stage(deps):
    return BuildStep("mkdir -p deps && " + " && ".join(
        "dpkg-deb -x {%s} deps" % key for key in sorted(deps)))


# upstream's ./configure is `cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo ..`
# from build/, i.e. -O2 -g -DNDEBUG (src/CMakeLists.txt adds -fsigned-char).
# It is invoked directly so the build directory and the extra settings below
# can be given; the build type is upstream's.
#
# One linker flag is added: -Wl,-Bsymbolic-functions. libcedar.so and
# libmayaqua.so export every function, so without it each call between two
# of a library's own functions goes through an unnamed .plt stub, and the
# first build failed the symbol gate on exactly that ("only 3299 of 6717
# functions of at least 3 instructions carry symbols (49%)" for
# libcedar.so). -fvisibility=hidden, which the other ELF recipes use, is not
# available here because vpnserver and the other programs link against the
# libraries' exports. -Bsymbolic-functions binds those calls inside the
# library instead; it changes symbol interposition, not the code.
_CONFIGURE_X64 = ("cmake -S . -B build -G 'Unix Makefiles' "
                  "-DCMAKE_BUILD_TYPE=RelWithDebInfo "
                  "-DCMAKE_SHARED_LINKER_FLAGS=-Wl,-Bsymbolic-functions")
# i386: liboqs picks its implementations from CMAKE_SYSTEM_PROCESSOR, which a
# plain -m32 build leaves at the host's x86_64, so it would compile the
# x86_64 AVX2 code into a 32-bit object. liboqs ships a toolchain file for
# exactly this case, .CMake/toolchain_x86.cmake (CMAKE_SYSTEM_NAME Linux,
# CMAKE_SYSTEM_PROCESSOR i586, CMAKE_CROSSCOMPILING OFF), and it is used as it
# is. The i386 readline and ncurses come from the staged packages, found
# through CMAKE_PREFIX_PATH, and -rpath-link lets the linker follow their
# own dependencies (libtinfo) inside the staging directory. -msse2 because
# libcedar compiles 3rdparty/BLAKE2/sse/blake2s.c, which stops with
# 'blake2-config.h:69:2: error: #error "This code requires at least SSE2."'
# on GCC's i686 default; it is a code-generation flag, not a source change.
_I386_LIB = "{source_root}/deps/usr/lib/i386-linux-gnu"
_CONFIGURE_X86 = ("cmake -S . -B build -G 'Unix Makefiles' "
                  "-DCMAKE_BUILD_TYPE=RelWithDebInfo "
                  "-DCMAKE_TOOLCHAIN_FILE="
                  "src/Mayaqua/3rdparty/liboqs/.CMake/toolchain_x86.cmake "
                  "-DCMAKE_PREFIX_PATH={source_root}/deps/usr "
                  "-DCMAKE_C_FLAGS=-msse2 "
                  "'-DCMAKE_SHARED_LINKER_FLAGS=-Wl,-Bsymbolic-functions "
                  "-Wl,-rpath-link," + _I386_LIB + "' "
                  "'-DCMAKE_EXE_LINKER_FLAGS=-Wl,-rpath-link," + _I386_LIB + "'")
_BUILD = "cmake --build build -j2"


def _pkgconfig(triple):
    return {
        "PKG_CONFIG_SYSROOT_DIR": "{source_root}/deps",
        "PKG_CONFIG_PATH": "{source_root}/deps/usr/lib/%s/pkgconfig" % triple,
    }


_ARTIFACTS = [
    Artifact(path="build/libcedar.so", component="libcedar.so"),
    Artifact(path="build/libmayaqua.so", component="libmayaqua.so"),
]

_SOURCE = Source(git_url="https://github.com/SoftEtherVPN/SoftEtherVPN.git",
                 git_ref="5.2.5189")


# MinGW: the three libraries the Windows build looks for (vcpkg's on
# upstream's MSVC path) are built here from pinned release tarballs, as DLLs
# with import libraries, so none of their code enters the images - the same
# position as the dynamic OpenSSL, zlib and libsodium of the Linux leg.
# OpenSSL and zlib use the pins of recipes/openssl.py and recipes/libpng.py.
_ZLIB = "1.3.1"
_SODIUM = "1.0.20"
_OPENSSL = "3.0.15"
_DEPS_MINGW = {
    "zlib_archive": Source(
        url="https://zlib.net/fossils/zlib-%s.tar.gz" % _ZLIB,
        sha256="9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23"),
    "sodium_archive": Source(
        url="https://download.libsodium.org/libsodium/releases/libsodium-%s.tar.gz" % _SODIUM,
        sha256="ebb65ef6ca439333c2bb41a0c1990587288da07f6c7fd07cb3a18cc18d30ce19"),
    "openssl_archive": Source(
        url="https://github.com/openssl/openssl/releases/download/openssl-%s/openssl-%s.tar.gz"
            % (_OPENSSL, _OPENSSL),
        sha256="23c666d0edf20f14249b3d8f0368acaee9ab585b09e1de82107c66e1f3ec9533"),
}

# The build-tree preparation of scripts/corpus/softether5_mingw.py: four
# MSVC-only lines deleted from src/CMakeLists.txt, two case symlinks in
# src/PenCore, a header directory and an import-library alias directory. Its
# docstring lists every byte of it.
_MINGW_PREPARE = ("python {repo}/scripts/corpus/softether5_mingw.py "
                  "{source_root} {source_root}/mingw-shim /usr/{host}/lib")
_MINGW_ZLIB = ("mkdir -p deps-src deps/include deps/lib deps/bin && "
               "tar xf {zlib_archive} -C deps-src && "
               "make -C deps-src/zlib-%s -f win32/Makefile.gcc PREFIX={prefix} "
               "STRIP=true -j$(nproc) zlib1.dll && "
               "cp deps-src/zlib-%s/zlib.h deps-src/zlib-%s/zconf.h deps/include/ && "
               "cp deps-src/zlib-%s/libz.dll.a deps/lib/" % ((_ZLIB,) * 4))
_MINGW_SODIUM = ("tar xf {sodium_archive} -C deps-src && cd deps-src/libsodium-%s && "
                 "./configure --host={host} --prefix={source_root}/deps "
                 "--disable-static --enable-shared && make -j$(nproc) && make install"
                 % _SODIUM)
# --cross-compile-prefix prepends the triple itself (see recipes/openssl.py).
# The static libcrypto.a/libssl.a that install_dev also installs are deleted
# so nothing can link OpenSSL statically.
_MINGW_OPENSSL = ("tar xf {openssl_archive} -C deps-src && cd deps-src/openssl-%s && "
                  "./Configure {openssl_target} --cross-compile-prefix={prefix} "
                  "shared no-tests --prefix={source_root}/deps --libdir=lib && "
                  "(make -j$(nproc) build_libs || make -j$(nproc) build_libs) && "
                  "make install_dev && rm -f {source_root}/deps/lib/libcrypto.a "
                  "{source_root}/deps/lib/libssl.a" % _OPENSSL)
_OPENSSL_ENV = {"CC": "gcc", "CXX": "g++", "AR": "ar", "RANLIB": "ranlib",
                "WINDRES": "windres"}
# Upstream's RelWithDebInfo, as on Linux. CMAKE_SYSTEM_PROCESSOR is what
# liboqs picks its implementations by (AMD64 is what its own
# toolchain_windows-amd64.cmake sets, x86 what toolchain_windows_x86.cmake
# sets). Two defines: _WIN32_WINNT=0x0600 is the Vista value
# Mayaqua/MayaType.h sets when nothing else has (mingw's _mingw.h defines
# 0x0A00 first, which with MayaType.h's NTDDI_VISTA leaves ipsectypes.h using
# IKEEXT_EM_POLICY1 that iketypes.h never declares: "unknown type name
# 'IKEEXT_EM_POLICY1'"); SKIP_CPU_FEATURES is upstream's own switch for
# builds without google/cpu_features, which src/Mayaqua/CMakeLists.txt only
# adds under if(UNIX) - MSVC skips the include through _MSC_VER instead, so
# without it Encrypt.c stops with "cpu_features_macros.h: No such file or
# directory".
_MINGW_FLAGS = ("-I{source_root}/mingw-shim/include -D_WIN32_WINNT=0x0600 "
                "-DSKIP_CPU_FEATURES")


def _mingw_configure(processor, extra_cflags=""):
    flags = (_MINGW_FLAGS + " " + extra_cflags).strip()
    return ("cmake -S . -B build -G 'Unix Makefiles' "
            "-DCMAKE_BUILD_TYPE=RelWithDebInfo "
            "-DCMAKE_SYSTEM_NAME=Windows -DCMAKE_SYSTEM_PROCESSOR=%s "
            "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx} "
            "-DCMAKE_RC_COMPILER={windres} "
            "'-DCMAKE_FIND_ROOT_PATH={source_root}/deps;/usr/{host}' "
            "-DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER "
            "-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY "
            "-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY "
            "-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY "
            "-DOPENSSL_ROOT_DIR={source_root}/deps "
            "-DZLIB_INCLUDE_DIR={source_root}/deps/include "
            "-DZLIB_LIBRARY={source_root}/deps/lib/libz.dll.a "
            "'-DCMAKE_C_FLAGS=%s' '-DCMAKE_CXX_FLAGS=%s' "
            "'-DCMAKE_EXE_LINKER_FLAGS=-L{source_root}/mingw-shim/lib'"
            % (processor, flags, flags))


_MINGW_ENV = {
    "PKG_CONFIG_LIBDIR": "{source_root}/deps/lib/pkgconfig",
    "PKG_CONFIG_PATH": "",
}
# Cedar's two C++ files (Win32Com.cpp, WinJumpList.cpp) end up in programs
# whose only source is C, so CMake links them with gcc and nothing pulls in
# the C++ runtime ("undefined reference to `__gxx_personality_seh0'",
# "`__cxa_end_catch'", "`vtable for __cxxabiv1::__class_type_info'" from
# libcedar.a(Win32Com.cpp.obj)); MSVC's single runtime hides this.
# InitPropVariantFromString, inline in mingw's propvarutil.h, needs
# shlwapi's SHStrDupW, which the SDK build gets without naming it
# ("undefined reference to `__imp_SHStrDupW'"). Both libraries go in front of
# CMake's own default list for Windows-GNU, which is otherwise kept as it is;
# libstdc++ is the import library, so its code stays in libstdc++-6.dll.
_MINGW_STDLIBS = ("'-DCMAKE_C_STANDARD_LIBRARIES=-lstdc++ -lshlwapi -lkernel32 "
                  "-luser32 -lgdi32 -lwinspool -lshell32 -lole32 -loleaut32 "
                  "-luuid -lcomdlg32 -ladvapi32'")
# Only vpnserver is built and taken: Cedar and Mayaqua are static libraries
# on Windows, and vpnbridge, vpnclient and vpncmd link the same members of
# them - on x64 their function symbols are vpnserver's exactly, except that
# vpncmd has main/SetConsoleTitleA where the others have WinMain,
# StartProcess and StopProcess.
_MINGW_BUILD = "cmake --build build -j$(nproc) --target vpnserver"
_MINGW_CLEAN = "rm -rf deps-src"


_MINGW_BUILD_FLAGS = (
    "upstream RelWithDebInfo (-O2 -g -DNDEBUG) cross-compiled with CMake for "
    "Windows; BUILD TREE PATCHED by scripts/corpus/softether5_mingw.py (4 "
    "MSVC-only lines deleted from src/CMakeLists.txt, case aliases, SDK "
    "shim headers, __forceinline/__try shims); -D_WIN32_WINNT=0x0600 "
    "-DSKIP_CPU_FEATURES; -lstdc++ -lshlwapi added to the C standard "
    "libraries; OpenSSL %s, zlib %s and libsodium %s built from pinned "
    "tarballs as DLLs" % (_OPENSSL, _ZLIB, _SODIUM))
_MINGW_NOTES = (
    "The Developer Edition 5.x (tag 5.2.5189) cross-compiled with MinGW-w64. "
    "NOT byte-identical to a build of unmodified upstream: the recipe edits "
    "the cloned build tree before configuring (scripts/corpus/softether5_mingw.py "
    "lists every change: four MSVC-only switch lines (/Qspectre, /guard:cf, "
    "/guard:cf /DYNAMICBASE, /CETCOMPAT) deleted from src/CMakeLists.txt; "
    "symlinks pencore.c/pencore.rc in src/PenCore; a header directory of "
    "case aliases and Windows SDK definitions mingw-w64 11 lacks (prsht.h, "
    "fwpmu.h, natupnp.h); __forceinline redefined without extern, __try/"
    "__except turned into if/else, and for C++ the CRYPTO_KEY_TYPE enum "
    "declared ahead of its forward typedef; mixed-case import-library "
    "aliases). No upstream .c or .h file is modified. OpenSSL, zlib and "
    "libsodium are built from pinned tarballs as DLLs and imported, so "
    "none of their code is in the image. Cedar and Mayaqua are static on "
    "Windows, so the program is the image; only vpnserver.exe is taken "
    "because vpnbridge, vpnclient and vpncmd link the same functions. "
    "liboqs, the OQS provider and blake2s are linked statically and "
    "excluded by exact name (_softether5_vendored.py, MinGW additions "
    "included). ")
_MINGW_NOTES_X64 = _MINGW_NOTES + (
    "Measured x64: vpnserver.exe 8092 kept + 156 glue + 748 excluded = 8996.")
_MINGW_NOTES_X86 = _MINGW_NOTES + (
    "x86 adds -msse2 (blake2s.c requires SSE2) and matches the excluded "
    "names behind i686's leading underscore. Measured x86: vpnserver.exe "
    "7725 kept + 162 glue + 747 excluded = 8634.")


def _mingw_recipe(arch, processor, extra_cflags, build_flags, notes, prefix=""):
    return Recipe(
        family="SoftEtherVPN",
        version="5.2.5189",
        upstream="https://github.com/SoftEtherVPN/SoftEtherVPN",
        license="Apache-2.0",
        source=_SOURCE,
        extra_sources=_DEPS_MINGW,
        build=[
            BuildStep(_MINGW_PREPARE),
            BuildStep(_MINGW_ZLIB),
            BuildStep(_MINGW_SODIUM),
            BuildStep(_MINGW_OPENSSL, env=_OPENSSL_ENV),
            BuildStep(_MINGW_CLEAN),
            BuildStep(_mingw_configure(processor, extra_cflags) + " " + _MINGW_STDLIBS,
                      env=_MINGW_ENV),
            BuildStep(_MINGW_BUILD),
        ],
        artifacts=[Artifact(path="build/vpnserver.exe", component="vpnserver")],
        toolchains=["mingw_%s" % arch],
        requires=["cmake", "make", "perl", "pkg-config", "python"],
        exclude_functions=_vendored.patterns(mingw=True, prefix=prefix),
        build_flags=build_flags,
        notes=notes,
    )


# MSVC: upstream's own Windows route, CMake with vcpkg (src/BUILD_WINDOWS.md),
# on the windows-2022 runner. vcpkg is pinned to the 2026.01.16 release tag
# (the commit below), which fixes the port versions for the manifest at the
# source root (vcpkg.json lists libsodium, openssl and zlib and carries no
# baseline of its own): OpenSSL 3.6.0#3, libsodium 1.0.21 and zlib 1.3.1, as
# DLLs through an overlay triplet. Nothing in the source tree is edited:
# scripts/corpus/softether5_msvc.py writes the overlay triplet and a
# CMAKE_PROJECT_INCLUDE file that restores /MD (upstream's CMakeLists.txt
# shadows the cache variable with its own static-CRT setting), and the rest
# is on the command line.
_VCPKG = Source(git_url="https://github.com/microsoft/vcpkg.git",
                git_ref="66c0373dc7fca549e5803087b9487edfe3aca0a1")
# vcpkg's build trees and packages go to C:/vb and C:/vp: under the corpus
# work directory (build/sources/<recipe>-vcpkg/buildtrees/...) the first run's
# libsodium port stopped on its longest file name, "error C1083: Cannot open
# source file: '..\\..\\..\\..\\src\\libsodium\\crypto_pwhash\\scryptsalsa208sha256\\
# nosse\\pwhash_scryptsalsa208sha256_nosse.c'", because the relative path cl
# resolves is exactly 260 characters (MAX_PATH).
# OQS_ENABLE=OFF is upstream's own switch (src/Mayaqua/CMakeLists.txt:
# "By setting this to OFF, Open Quantum Safe algorithms will not be built
# in", which defines SKIP_OQS_PROVIDER). It defaults to ON for OpenSSL 3.x and
# the second run stopped on it: cl 19.44 (14.44.35207) dies compiling the
# OQS provider, "src/Mayaqua/3rdparty/oqs-provider/oqsprov/
# oqsprov_capabilities.c(683): warning C4034: sizeof returns 0" and then
# "fatal error C1001: Internal compiler error. (compiler file
# 'D:\\a\\_work\\1\\s\\src\\vctools\\Compiler\\Utc\\src\\p2\\main.cpp', line 258)",
# on x86 and x64 alike; SoftEther switches every other KEM and signature
# family off, which leaves that file with zero-length tables. Upstream's own
# Windows builds use clang-cl (CMakeSettings.json, .github/workflows/
# windows.yml), never cl. So the MSVC images carry neither liboqs nor the OQS
# provider. "-- -k 0" keeps Ninja going past a failed compile so one run
# reports every error.
# /Z7 rather than RelWithDebInfo's /Zi so no shared compiler PDB is needed
# (Ninja compiles in parallel); /MD stated because liboqs and oqs-provider
# declare an older cmake_minimum_required, under which the runtime comes from
# the flags and not from CMAKE_MSVC_RUNTIME_LIBRARY. The link line is the
# corpus mandate: no /GL, no /LTCG, /OPT:NOREF /OPT:NOICF /Brepro
# /INCREMENTAL:NO. Upstream's own /Qspectre, /guard:cf, /DYNAMICBASE and
# /CETCOMPAT are kept.
_MSVC_C = '"/MD /O2 /Ob1 /DNDEBUG /Z7"'
_MSVC_CONFIGURE = (
    "cmake -S . -B build-{arch} -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo "
    "-DCMAKE_TOOLCHAIN_FILE={vcpkg}\\scripts\\buildsystems\\vcpkg.cmake "
    "-DVCPKG_TARGET_TRIPLET=se-{arch}-windows-release "
    "-DVCPKG_OVERLAY_TRIPLETS={source_root}\\vcpkg-triplets "
    "-DVCPKG_APPLOCAL_DEPS=OFF -DOQS_ENABLE=OFF "
    '"-DVCPKG_INSTALL_OPTIONS=--x-buildtrees-root=C:/vb;--x-packages-root=C:/vp" '
    "-DCMAKE_PROJECT_INCLUDE={source_root}\\se-msvc-runtime.cmake "
    "-DCMAKE_C_FLAGS_RELWITHDEBINFO=" + _MSVC_C + " "
    "-DCMAKE_CXX_FLAGS_RELWITHDEBINFO=" + _MSVC_C + " "
    '-DCMAKE_EXE_LINKER_FLAGS_RELWITHDEBINFO="/DEBUG /INCREMENTAL:NO '
    '/OPT:NOREF /OPT:NOICF /Brepro"')

_MSVC_BUILD_FLAGS = (
    "upstream's CMake + vcpkg route, RelWithDebInfo with /MD /O2 /Ob1 /Z7 "
    "(upstream's /Qspectre /guard:cf kept, no /GL or /LTCG); link /DEBUG "
    "/DYNAMICBASE /CETCOMPAT (upstream) /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF "
    "/Brepro; /MD instead of upstream's /MT through CMAKE_PROJECT_INCLUDE; "
    "vcpkg 2026.01.16 dynamic release triplet (OpenSSL 3.6.0, libsodium "
    "1.0.21, zlib 1.3.1 as DLLs)")
_MSVC_NOTES = (
    "The Developer Edition 5.x (tag 5.2.5189) built with MSVC v143 through "
    "upstream's own CMake + vcpkg route on the GitHub windows-2022 runner. "
    "No upstream source or CMake file is edited, so no build-tree patch is "
    "applied; the build differs from upstream's own Windows release in "
    "settings only: /MD (upstream: /MT), cl and /Z7 (CMakeSettings.json: "
    "clang-cl, RelWithDebInfo /Zi), the corpus link flags, and dynamic vcpkg "
    "ports pinned to the vcpkg 2026.01.16 release (upstream: x64-windows-"
    "static, unpinned). OpenSSL, zlib and libsodium are DLLs, so none of their "
    "code is in the image. Cedar and Mayaqua are static on Windows, so the "
    "program is the image and only vpnserver.exe is taken. liboqs, the OQS "
    "provider and blake2s are linked statically and excluded by exact name "
    "(_softether5_vendored.py). ")


def _msvc_recipe():
    return Recipe(
        family="SoftEtherVPN",
        version="5.2.5189",
        upstream="https://github.com/SoftEtherVPN/SoftEtherVPN",
        license="Apache-2.0",
        source=_SOURCE,
        extra_sources={"vcpkg": _VCPKG},
        build=[
            BuildStep("call {vcpkg}\\bootstrap-vcpkg.bat -disableMetrics"),
            BuildStep("python {repo}/scripts/corpus/softether5_msvc.py prepare "
                      "{source_root} {arch}"),
            BuildStep(_MSVC_CONFIGURE),
            BuildStep("cmake --build build-{arch} --target vpnserver -- -k 0"),
            # Evidence for the exclusion table, read from this build's own
            # static libraries; see softether5_msvc.py. Never fails the build.
            BuildStep("python {repo}/scripts/corpus/softether5_msvc.py names "
                      "build-{arch}", allow_failure=True),
            BuildStep("dumpbin /nologo /dependents build-{arch}\\vpnserver.exe",
                      allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/vpnserver.exe",
                            component="vpnserver",
                            pdb="build-{arch}/vpnserver.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        requires=["cmake", "ninja", "python"],
        # i686 COFF decorates C names with a leading underscore (the x86
        # images name blake2s "_blake2s"); x64 names carry none.
        exclude_functions=_vendored.patterns(optional_prefix="_",
                                             libraries=("BLAKE2",)),
        build_flags=_MSVC_BUILD_FLAGS,
        notes=_MSVC_NOTES,
    )


RECIPES = {
    "softether_vpn_5.2.5189_linux": Recipe(
        family="SoftEtherVPN",
        version="5.2.5189",
        upstream="https://github.com/SoftEtherVPN/SoftEtherVPN",
        license="Apache-2.0",
        source=_SOURCE,
        extra_sources=_DEPS_X64,
        build=[
            _stage(_DEPS_X64),
            BuildStep(_CONFIGURE_X64, env=_pkgconfig("x86_64-linux-gnu")),
            BuildStep(_BUILD),
        ],
        artifacts=_ARTIFACTS,
        toolchains=["linux_x64"],
        requires=["cmake", "make", "dpkg-deb", "pkg-config"],
        exclude_functions=_vendored.patterns(),
        build_flags="upstream RelWithDebInfo (-O2 -g -DNDEBUG -fsigned-char); linked with -Wl,-Bsymbolic-functions",
        notes=("The Developer Edition 5.x (SoftEtherVPN/SoftEtherVPN, tag 5.2.5189), "
              "built with upstream's RelWithDebInfo CMake configuration; the "
              "artefacts are libcedar.so and libmayaqua.so, which hold the "
              "code - vpnserver, vpnbridge, vpnclient and vpncmd are 46-line "
              "mains calling into libcedar. OpenSSL, zlib, readline, ncurses "
              "and libsodium are linked dynamically. liboqs, the OQS "
              "provider and cpu_features (static, in libmayaqua.so) and "
              "BLAKE2's blake2s (in libcedar.so) are excluded by exact name: "
              "every function defined in their archives or objects of this "
              "build and in none of SoftEther's (_softether5_vendored.py). "
              "-Wl,-Bsymbolic-functions keeps calls inside each library off "
              "unnamed PLT stubs. "
               "Measured x64: libcedar.so 5179 kept + 4 glue + 7 excluded = "
               "5190, libmayaqua.so 2615 + 4 + 1226 = 3845 (liboqs 860, OQS "
               "provider 261, cpu_features 105)."),
    ),
    "softether_vpn_5.2.5189_linux_x86": Recipe(
        family="SoftEtherVPN",
        version="5.2.5189",
        upstream="https://github.com/SoftEtherVPN/SoftEtherVPN",
        license="Apache-2.0",
        source=_SOURCE,
        extra_sources=_DEPS_X86,
        build=[
            _stage(_DEPS_X86),
            BuildStep(_CONFIGURE_X86, env=_pkgconfig("i386-linux-gnu")),
            BuildStep(_BUILD),
        ],
        artifacts=_ARTIFACTS,
        toolchains=["linux_x86"],
        requires=["cmake", "make", "dpkg-deb", "pkg-config"],
        exclude_functions=_vendored.patterns(),
        build_flags="upstream RelWithDebInfo (-O2 -g -DNDEBUG -fsigned-char), "
                    "-m32 -msse2 with liboqs's own .CMake/toolchain_x86.cmake; linked "
                    "with -Wl,-Bsymbolic-functions",
        notes=("The Developer Edition 5.x (SoftEtherVPN/SoftEtherVPN, tag 5.2.5189), "
              "built with upstream's RelWithDebInfo CMake configuration; the "
              "artefacts are libcedar.so and libmayaqua.so, which hold the "
              "code - vpnserver, vpnbridge, vpnclient and vpncmd are 46-line "
              "mains calling into libcedar. OpenSSL, zlib, readline, ncurses "
              "and libsodium are linked dynamically. liboqs, the OQS "
              "provider and cpu_features (static, in libmayaqua.so) and "
              "BLAKE2's blake2s (in libcedar.so) are excluded by exact name: "
              "every function defined in their archives or objects of this "
              "build and in none of SoftEther's (_softether5_vendored.py). "
              "-Wl,-Bsymbolic-functions keeps calls inside each library off "
              "unnamed PLT stubs. "
               "x86 adds -msse2 (blake2s.c requires SSE2) and liboqs's own "
               ".CMake/toolchain_x86.cmake. Measured x86: libcedar.so 5173 "
               "kept + 7 glue + 7 excluded = 5187, libmayaqua.so 3024 + 9 + "
               "873 = 3906."),
    ),
    "softether_vpn_5.2.5189_mingw_x64": _mingw_recipe(
        "x64", "AMD64", "", _MINGW_BUILD_FLAGS, _MINGW_NOTES_X64),
    "softether_vpn_5.2.5189_mingw_x86": _mingw_recipe(
        "x86", "x86", "-msse2", _MINGW_BUILD_FLAGS + "; x86 adds -msse2",
        _MINGW_NOTES_X86, prefix="_"),
    "softether_vpn_5.2.5189_msvc": _msvc_recipe(),
}
