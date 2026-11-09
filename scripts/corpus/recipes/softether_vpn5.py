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

**Not built: MinGW.** Configuring with x86_64-w64-mingw32-gcc fails in
CMake's own compiler check, because src/CMakeLists.txt appends MSVC linker
switches under if(WIN32) whatever the compiler: "x86_64-w64-mingw32-ld:
cannot find /guard:cf: No such file or directory" (and /DYNAMICBASE,
/CETCOMPAT), then "CMake will not be able to correctly generate this
project" at src/Cedar/CMakeLists.txt:5. The Windows path also requires
vcpkg's unofficial-sodium package (find_package(unofficial-sodium CONFIG
REQUIRED)). Getting past either means editing upstream's CMake files, so it
is recorded in the not-built table rather than patched.
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
}
