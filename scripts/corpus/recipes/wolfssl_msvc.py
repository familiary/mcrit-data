"""wolfSSL built with MSVC, beside the MinGW build of the same tag.

data/wolfSSL carries only MinGW artefacts. wolfSSL is the least common of the
Windows TLS stacks in malware - its own MinGW recipe says so - but where it
does turn up it is inside an MSVC-built binary, and the whole point of this
family is to be able to tell it apart from mbedTLS and OpenSSL rather than to
match it often.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

Upstream's own CMake is used rather than the in-tree wolfssl.vcxproj /
wolfssl64.sln, and that is a deliberate choice against the usual "prefer the
shipped solution" rule:

  * the MinGW artefact is a CMake build. The vcxproj compiles against
    IDE/WIN/user_settings.h, which is a different feature set, so an artefact
    built from it would differ from its MinGW sibling in *what wolfSSL was
    compiled*, not just in who compiled it. Using CMake on both sides keeps
    the only variable the compiler.
  * the vcxproj asks for PlatformToolset v110, which the windows-2022 image
    does not carry, so it would need the same override anyway.

What was read rather than assumed, in CMakeLists.txt at v5.9.2-stable:

  * BUILD_SHARED_LIBS is upstream's own option (default ON) and selects
    "add_library(wolfssl SHARED ...)"; it is passed explicitly rather than
    relied on. Without it the build is a static wolfssl.lib, which SMDA
    cannot read.
  * "wolfssl" is the target name, so --target wolfssl builds the library
    alone.
  * exports are real, not a .def trick: the build sets BUILDING_WOLFSSL
    PRIVATE and, under BUILD_SHARED_LIBS, WOLFSSL_DLL PUBLIC, and
    wolfssl/wolfcrypt/visibility.h turns that pair into
    "#define WOLFSSL_API __declspec(dllexport)" for _MSC_VER. So no
    CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS is needed here, unlike mbedTLS.
  * no OUTPUT_NAME or PREFIX is set on the target - only VERSION and
    SOVERSION, which do not reach the file name on a platform without
    sonames. MSVC's empty library prefix therefore makes the file
    wolfssl.dll, where MinGW's "lib" prefix makes it libwolfssl.dll. The
    component is recorded as the name this build produces.
  * add_library is called from the top-level CMakeLists.txt, so with a
    single-configuration generator the DLL and its PDB land in the build
    root.
  * the /Zi-to-/Z7 rewrite in the MSVC branch of the sccache block cannot
    fire: ENABLE_SCCACHE is an add_option defaulting to "no". (It would not
    have broken the PDB either way - link /DEBUG writes one from /Z7 objects
    too - but it is worth knowing which of the two is in the artefact.)
  * the WIN32 branch of the compiler-flag block prepends "-Wall" to
    CMAKE_C_FLAGS unconditionally. cl reads that as /Wall, i.e. every
    warning MSVC has, including the ones its own headers trip; over ~500
    translation units that is a build log measured in tens of megabytes. It
    cannot be removed through a cache variable because the line appends to
    whatever CMAKE_C_FLAGS holds, so /W0 is put at the end of
    CMAKE_C_FLAGS_RELEASE instead, which CMake emits after CMAKE_C_FLAGS and
    which cl resolves last-wins. This changes no code, only the log; expect
    one D9025 "overriding '/Wall' with '/W0'" line per file.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# See xz_msvc.py for why the per-configuration variables and not
# CMAKE_C_FLAGS / CMAKE_SHARED_LINKER_FLAGS: CMake's MSVC Release default
# carries neither /Zi nor /DEBUG, so the artefact would come back with no PDB
# and no names, and overriding the per-configuration variables leaves CMake's
# own initialisation - /machine on the 32-bit leg among it - in place.
#
# /MD is spelled out rather than inherited. wolfSSL's CMakeLists declares
# cmake_minimum_required(VERSION 3.16), so CMP0091 is NEW and the runtime
# would normally come from CMAKE_MSVC_RUNTIME_LIBRARY - but setting
# CMAKE_C_FLAGS_RELEASE by hand is the same string either way, and under a
# project old enough for CMP0091 OLD an omitted /MD silently becomes cl's
# default /MT, which put 1947 of VX-API's 4219 functions into that artefact
# as MSVC C runtime.
_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi /W0"'
# /DEBUG so a PDB is written at all, /Brepro so the PE carries no build
# timestamp, /OPT:NOREF /OPT:NOICF so unreferenced and identically-compiled
# routines both survive as separate reference samples. /INCREMENTAL:NO is
# CMake's own Release default and is restated because setting the variable
# replaces it.
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

# NMake Makefiles: nmake ships with MSVC itself, the generator is
# single-configuration so the DLL lands in the build root, and the target
# architecture comes from the developer environment the workflow sets up.
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON '
          '-DWOLFSSL_EXAMPLES=no -DWOLFSSL_CRYPT_TESTS=no %s %s'
          % (_CFLAGS, _LDFLAGS))


RECIPES = {
    "wolfSSL_5.9.2_msvc": Recipe(
        family="wolfSSL",
        version="5.9.2",
        upstream="https://github.com/wolfSSL/wolfssl",
        # Same reading as the MinGW recipe: COPYING at v5.9.2-stable is GPLv3
        # and every source header offers "version 3 ... or any later
        # version". The GPLv2 fallback in LICENSING applies only to the named
        # Exception Software projects, which this build is not.
        license="GPL-3.0-or-later",
        source=Source(git_url="https://github.com/wolfSSL/wolfssl.git",
                      git_ref="v5.9.2-stable"),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} --target wolfssl"),
            # Cheap insurance, as in xz_msvc.py: puts the names the build
            # actually wrote into the log the workflow prints on failure.
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/wolfssl.dll",
                            component="wolfssl.dll",
                            pdb="build-{arch}/wolfssl.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi /W0 (CMake Release, /Zi added, /W0 "
                    "overriding the /Wall upstream prepends on WIN32); "
                    "/DEBUG /Brepro /OPT:NOREF /OPT:NOICF at link",
        notes="Same tag and the same upstream CMake configuration as the "
              "MinGW artefacts of this family, so the two differ only in the "
              "compiler. No dependencies: wolfSSL links ws2_32, crypt32 and "
              "advapi32 from Win32 and nothing else, and is built against "
              "the DLL runtime so the MSVC C runtime is imported rather than "
              "linked in and stays attributed to data/MSVC. Named wolfssl.dll "
              "rather than the MinGW build's libwolfssl.dll because MSVC has "
              "no library prefix; it is the same library and the same tag. "
              "wolfSSL and mbedTLS implement the same primitives and both "
              "appear in this corpus - a cross-family PicHash hit between "
              "them is two independent implementations of one algorithm, not "
              "code leaking from one family into the other, and neither "
              "vendors the other.",
    ),
}
