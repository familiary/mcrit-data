"""UltraVNC built with MinGW-w64, x86 and x64 (mcrit-data issue #27).

ultravnc_msvc.py says what UltraVNC is and why the viewer is the component the
evidence (FOSSIL) points at. This file is the non-MSVC axis. It is NOT
byte-identical to a build of unmodified upstream: the build tree is patched by
the recipe, every patch is listed here, and the pinned checkout is never
modified or committed.

What upstream offers. Upstream's only non-MSVC path is cmake\\CMakeLists.txt
with its MinGW branch (cmake\\readme.txt: Debian, vcpkg `x64-mingw-static`).
vcpkg is not used here. The six libraries of vcpkg.json are built from pinned
sources as static libraries into deps-<arch>\\prefix (see _DEPS); the exe links
them statically, as the vcpkg static triplet does, so those libraries'
functions are in the image under the UltraVNC family exactly as in the MSVC
images (overlap is measured in the README, not removed).

Pinned dependencies (all CMake Release, static, no shared objects):
  zlib 1.3.1 (tarball, sha256 9a93b2b7...df23), zstd v1.5.7 (f8745da6),
  xz v5.8.1 (a522a226; liblzma), libjpeg-turbo 3.1.1 (7723f50f),
  minizip-ng 4.0.10 (f3ed731e; MZ_COMPAT=OFF so the headers install as
  <minizip-ng/mz.h>, which MiniZipNG.cpp includes; MZ_BZIP2=OFF,
  MZ_OPENSSL=OFF), libsodium 1.0.20 (tarball, sha256 ebb65ef6...ce19).
vcpkg's own versions at the pinned baseline were not used; these are the
newest releases at the time and are recorded, not claimed to equal vcpkg's.

Patches applied by the recipe to the build tree (all by
scripts/corpus/exercisers/ultravnc_mingw_patch.py, which stops if a pattern
does not occur the stated number of times):

 1. cmake\\CMakeLists.txt: the lines `add_subdirectory(libzip32)` and
    `add_subdirectory(libzipunzip)` are deleted, and `    libzip32` and
    `    libzipunzip` are deleted from cmake\\vncviewer\\CMakeLists.txt.
    Reason: those two CMake projects compile zipunzip_src\\zip20 and
    zipunzip_src\\unzip, which no longer exist in the tree (MiniZipNG.cpp
    replaced them); configure stops with `CMake Error at
    libzip32/CMakeLists.txt:32 (target_sources): Cannot find source file:
    .../zipunzip_src/zip20/api.c`. minizip-ng is linked instead, as the
    vcxproj does through vcpkg.
 2. cmake\\vncviewer\\CMakeLists.txt: `    CredentialManager.cpp` is added to
    the source list. Reason: it is in vncviewer.vcxproj and missing from the
    list; the link fails with `undefined reference to
    CredentialManager::ReadVncPassword(...)`.
 3. cmake\\vncviewer\\CMakeLists.txt: appended
        target_compile_definitions(vncviewer PRIVATE UNICODE _UNICODE SODIUM_STATIC)
        target_compile_options(vncviewer PRIVATE -fpermissive "SHELL:-include ${UVNC_COMPAT}")
        target_link_options(vncviewer PRIVATE -municode)
        target_link_directories(vncviewer PRIVATE ${UVNC_DEPS_LIB})
        target_link_libraries(vncviewer PRIVATE ${UVNC_DEPS_LIB}/libminizip-ng.a
                              ${UVNC_DEPS_LIB}/libsodium.a bcrypt crypt32)
    Reason: vncviewer.vcxproj is a Unicode program (CharacterSet Unicode,
    _UNICODE;UNICODE); the CMake target is ANSI and fails with 100+ errors
    such as `no matching function for call to 'strcpy_s(wchar_t [250],
    long long unsigned int, TCHAR*&)'`. -municode selects wWinMain (`undefined
    reference to 'WinMain'` otherwise). -fpermissive downgrades the
    MSVC-accepted `invalid conversion from 'const char*' to 'char*'`
    (ClientConnectionTLS.cpp:219, :403) to warnings. sodium.h is included by
    ClientConnection.cpp and the CMake target does not link libsodium.
    The other CMake projects (ANSI programs) keep their upstream flags.
 4. vncviewer\\ClientConnection.cpp, WriteExact(): the SEH block
        __try { EnterCriticalSection(&crit); WriteTransformed(...); }
        __finally { LeaveCriticalSection(&crit); }
    becomes EnterCriticalSection(&crit), a local struct whose destructor
    calls LeaveCriticalSection(&crit), then WriteTransformed(...) (GCC has no
    __try/__finally: `error: expected 'catch' before '__finally'`).
 5. vncviewer\\ClientConnectionTLS.cpp (1.8.2.9 and 1.8.3.0 only; 1.8.3.1 no
    longer has the call): `Handshake(DynBuffer(), outbuf)` becomes
    `Handshake(uvnc_lvalue(DynBuffer()), outbuf)` (`error: cannot bind
    non-const lvalue reference of type 'DynBuffer&' to an rvalue of type
    'DynBuffer'`); uvnc_lvalue is in the force-included header.
 6. vncviewer\\FileTransfer.cpp: five declarations that a `goto` jumps over
    are split into declaration plus assignment (`char szSavedParentPath[
    MAX_PATH] = {0}` -> declaration + memset; `bool bDirectPath = false` (two
    places); `WCHAR ofDirStrippedW[MAX_PATH] = {0}` -> declaration + memset;
    `int nIndex = SendDlgItemMessage(...)` (two places) -> declaration +
    assignment). Reason: `error: jump to label 'populate_folder'` /
    `'send_request'` ... `crosses initialization`, which MSVC accepts and
    GCC does not even under -fpermissive. The values are the same.
 7. vncviewer\\res\\vncviewer.rc: `"stat\\\\chat.bmp"` and `"stat\\\\FT.bmp"`
    become `"stat/chat.bmp"` and `"stat/FT.bmp"` (windres on Linux:
    `can't open bitmap file 'stat\\chat.bmp': No such file or directory`).

Force-included header (scripts/corpus/exercisers/ultravnc_mingw_compat.h, C++
only, -include): <cstring> (AboutBox.cpp uses std::strstr without including
it), the uvnc_lvalue helper of patch 5, and the `_strdate_s(char (&)[N])` /
`_strtime_s(char (&)[N])` array overloads that MSVC's CRT provides and
mingw-w64 does not (FileTransfer.cpp:2573: `too few arguments to function
'errno_t _strdate_s(char*, size_t)'`).

Build environment, not source: CPATH names the dependency prefix's include
directory (the project's own CMakeLists replaces CMAKE_C_FLAGS/CMAKE_CXX_FLAGS
for MinGW, which discards any -I given there).

x86 only: i686 mingw-w64 ships no libcryptui.a (the x86_64 package has it) and
ClientConnectionTLS.cpp calls CryptUIDlgViewCertificate; the recipe generates
an import library for the one function used with dlltool from a two-line .def
(`CryptUIDlgViewCertificateW@8`, --kill-at), so the exe imports cryptui.dll
as MSVC's does. No Windows binary is involved, only the import record.

Not built from this CMake tree, with the exact errors (all identical at the
three pinned commits; the cmake directory does not change between 1.8.2.9 and
1.8.3.2):
  * winvnc (the server): `#add_subdirectory(winvnc)` is commented out
    upstream. Enabling it needs libudtcloud, whose sources are gone
    (`CMake Error at libudtcloud/CMakeLists.txt:23 (target_sources): Cannot
    find source file: .../UdtCloudlib/proxy/Cloudthread.cpp`), and
    cmake\\winvnc\\CMakeLists.txt needs vcpkg's `unofficial-sodium` package
    (`Could not find a package configuration file provided by
    "unofficial-sodium"`).
  * authSSP, MSLogonACL: SEH (`error: '__try' was not declared in this
    scope`, `'__finally' was not declared in this scope`) in
    authSSP.cpp, vncAccessControl.cpp, GenClientServerContext.cpp,
    vncExportACL.cpp, vncImportACL.cpp; authSSP also `fatal error:
    ../../../winvnc/winvnc/localization.h: No such file or directory`.
  * ldapauth, ldapauth9x, ldapauthnt4: `fatal error: ldapauth.h: No such
    file or directory` (and ldapauth9x.h, ldapauthnt4.h).
  * repeater: `socket_functions.cpp:523:1: error: jump to label 'error'`
    (crosses initialization) and the ANSI/UNICODE errors do not apply (it is
    an ANSI program); only the goto fails.
  * uvnc_settings: `fatal error: natupnp.h: No such file or directory`.
  * uvnckeyboardhelper: `fatal error: SDKDDKVer.h: No such file or
    directory` and `resource.h: No such file or directory` (the .rc).
  * workgrpdomnt4, logmessages: logmessages: `In messages.mc at line 13:
    parser: syntax error.`; workgrpdomnt4 depends on it.

Data. UltraVNC 1.8.3.1 (92bb19b9) has images (16: eight components, x86 and
x64); 1.8.2.9 and 1.8.3.0 are described after this table. Counts, kept + removed = total,
read from data/UltraVNC/provenance.json (kept = num_functions, removed =
removed_runtime_functions):

  x86  vncviewer.exe        4332 +  189 =  4521
  x86  createpassword.exe     30 +   62 =    92
  x86  setpasswd.exe          30 +  127 =   157
  x86  setcad.exe              8 +   59 =    67
  x86  testauth.exe            9 +  127 =   136
  x86  authadmin.dll           9 +  114 =   123
  x86  logging.dll            58 +  115 =   173
  x86  vnchooks.dll           28 +   49 =    77
  x64  vncviewer.exe        4118 +  182 =  4300
  x64  createpassword.exe     53 +   64 =   117
  x64  setpasswd.exe          53 +  123 =   176
  x64  setcad.exe             21 +   61 =    82
  x64  testauth.exe           28 +  124 =   152
  x64  authadmin.dll          26 +  109 =   135
  x64  logging.dll            52 +  110 =   162
  x64  vnchooks.dll           69 +   50 =   119

  Total over the 16 images: 8924 kept + 1665 removed = 10589.

Overlap with the MSVC images of the same version, 1.8.3.1 (distinct PicHashes of
functions of 10+ instructions): the MinGW viewer has 2854 (x86) and 2570 (x64),
the MSVC viewer 3534 and 3288, and they share 84 and 47. All eight MinGW
components together (2919 / 2630) share 84 / 49 with the MSVC viewer plus
server; nothing beyond the viewer adds more than 2. A different compiler
and standard library mostly changes the hashes, so this is a different axis
rather than a duplicate.

UltraVNC 1.8.2.9 (97a077cc) and 1.8.3.0 (36c2389f) were built through the same
pipeline with the same patches (patch 5 applies at both; every pattern matched
the stated number of times) and have the same 16 images each. kept + removed =
total per image, from data/UltraVNC/provenance.json (the 1.8.2.9 and 1.8.3.0
numbers equal the 1.8.3.1 ones except for the viewer):

  version  x86 vncviewer.exe  x64 vncviewer.exe  seven tools (x86 / x64)
  1.8.2.9  4337 + 189 = 4526  4115 + 182 = 4297  as 1.8.3.1 above
  1.8.3.0  4337 + 189 = 4526  4115 + 182 = 4297  as 1.8.3.1 above

  Totals over the 16 images: 8926 kept + 1665 removed = 10591 at both
  versions. 1.8.3.1 (above): 8924 + 1665 = 10589.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_ENV = {"CFLAGS": "", "CXXFLAGS": ""}

# The cmake options every dependency shares. {cxx} and friends come from the
# toolchain; the prefix is deps-<arch>\\prefix under the source root.
_TC = ("-DCMAKE_SYSTEM_NAME=Windows -DCMAKE_SYSTEM_PROCESSOR={platform} "
       "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx} "
       "-DCMAKE_RC_COMPILER={windres} -DCMAKE_AR=$(command -v {ar}) "
       "-DCMAKE_RANLIB=$(command -v {ranlib}) "
       "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
       "-DCMAKE_INSTALL_PREFIX=$PWD/deps-{arch}/prefix")


def _cmake_dep(name, src, extra=""):
    return BuildStep(
        "cmake -S %s -B deps-{arch}/b-%s %s %s && "
        "cmake --build deps-{arch}/b-%s -j$(nproc) && "
        "cmake --install deps-{arch}/b-%s" % (src, name, _TC, extra, name, name),
        env=_ENV)


_DEPS = [
    # The two tarballs are unpacked; the git sources are checkouts already.
    BuildStep("rm -rf deps-{arch} && mkdir -p deps-{arch}/prefix deps-{arch}/zlib "
              "deps-{arch}/sodium && tar xf {zlib} -C deps-{arch}/zlib --strip-components=1 "
              "&& tar xf {sodium} -C deps-{arch}/sodium --strip-components=1"),
    _cmake_dep("zlib", "deps-{arch}/zlib", "-DZLIB_BUILD_EXAMPLES=OFF"),
    # zlib installs libzlibstatic.a next to an import library for its DLL;
    # FindZLIB must find the static one, so the import library goes and the
    # static one gets the libz.a name FindZLIB and -lz look for.
    BuildStep("rm -f deps-{arch}/prefix/lib/libzlib.dll.a "
              "deps-{arch}/prefix/bin/libzlib.dll && "
              "cp deps-{arch}/prefix/lib/libzlibstatic.a deps-{arch}/prefix/lib/libz.a"),
    _cmake_dep("zstd", "{zstd}/build/cmake",
               "-DZSTD_BUILD_PROGRAMS=OFF -DZSTD_BUILD_TESTS=OFF "
               "-DZSTD_BUILD_SHARED=OFF -DZSTD_BUILD_STATIC=ON"),
    _cmake_dep("xz", "{xz}",
               "-DBUILD_SHARED_LIBS=OFF -DXZ_TOOL_XZ=OFF -DXZ_TOOL_XZDEC=OFF "
               "-DXZ_TOOL_LZMADEC=OFF -DXZ_TOOL_LZMAINFO=OFF "
               "-DXZ_TOOL_SCRIPTS=OFF -DXZ_NLS=OFF"),
    _cmake_dep("jpeg", "{jpeg}",
               "-DENABLE_SHARED=OFF -DENABLE_STATIC=ON -DWITH_TURBOJPEG=ON"),
    _cmake_dep("mz", "{mz}",
               "-DCMAKE_PREFIX_PATH=$PWD/deps-{arch}/prefix -DBUILD_SHARED_LIBS=OFF "
               "-DMZ_COMPAT=OFF -DMZ_BZIP2=OFF -DMZ_LZMA=ON -DMZ_ZSTD=ON "
               "-DMZ_ZLIB=ON -DMZ_OPENSSL=OFF -DMZ_LIBBSD=OFF -DMZ_ICONV=OFF "
               "-DMZ_FETCH_LIBS=OFF -DMZ_FORCE_FETCH_LIBS=OFF"),
    BuildStep("S=$PWD && mkdir -p deps-{arch}/b-sodium && cd deps-{arch}/b-sodium && "
              "$S/deps-{arch}/sodium/configure --host={host} --prefix=$S/deps-{arch}/prefix "
              "--enable-static --disable-shared && make -j$(nproc) && make install",
              env=_ENV),
    # i686 mingw-w64 has no libcryptui.a (see the docstring).
    BuildStep("if [ {bitness} = 32 ]; then printf 'LIBRARY cryptui.dll\\nEXPORTS\\n"
              "CryptUIDlgViewCertificateW@8\\n' > deps-{arch}/cryptui.def && "
              "{prefix}dlltool -d deps-{arch}/cryptui.def "
              "-l deps-{arch}/prefix/lib/libcryptui.a -k -m i386; fi"),
]

_PATCH = BuildStep("python3 -I {repo}/scripts/corpus/exercisers/ultravnc_mingw_patch.py .")

_CONFIGURE = BuildStep(
    "cmake -S cmake -B bld-{arch} -DCMAKE_SYSTEM_NAME=Windows "
    "-DCMAKE_SYSTEM_PROCESSOR={platform} -DCMAKE_C_COMPILER={cc} "
    "-DCMAKE_CXX_COMPILER={cxx} -DCMAKE_RC_COMPILER={windres} "
    "-DCMAKE_AR=$(command -v {ar}) -DCMAKE_RANLIB=$(command -v {ranlib}) "
    "-DCMAKE_FIND_ROOT_PATH=\"/usr/{host};$PWD/deps-{arch}/prefix\" "
    "-DCMAKE_PREFIX_PATH=$PWD/deps-{arch}/prefix -DCMAKE_BUILD_TYPE=Release "
    "-DUVNC_COMPAT={repo}/scripts/corpus/exercisers/ultravnc_mingw_compat.h "
    "-DUVNC_DEPS_LIB=$PWD/deps-{arch}/prefix/lib",
    env=dict(_ENV, CPATH="{source_root}/deps-{arch}/prefix/include"))

# `-k`: the CMake tree builds a dozen projects and several of them cannot
# build (see the docstring); the artefacts below are checked by the pipeline.
_BUILD = BuildStep("cmake --build bld-{arch} -j$(nproc) -- -k",
                   env=dict(_ENV, CPATH="{source_root}/deps-{arch}/prefix/include"),
                   allow_failure=True)

_COMPONENTS = [
    ("vncviewer/vncviewer.exe", "vncviewer.exe"),
    ("createpassword/createpassword.exe", "createpassword.exe"),
    ("setpasswd/setpasswd.exe", "setpasswd.exe"),
    ("setcad/setcad.exe", "setcad.exe"),
    ("testauth/testauth.exe", "testauth.exe"),
    ("authadmin/authadmin.dll", "authadmin.dll"),
    ("logging/logging.dll", "logging.dll"),
    ("vnchooks/vnchooks.dll", "vnchooks.dll"),
]

_EXTRA = {
    "zlib": Source(url="https://zlib.net/fossils/zlib-1.3.1.tar.gz",
                   sha256="9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23"),
    "zstd": Source(git_url="https://github.com/facebook/zstd.git", git_ref="v1.5.7"),
    "xz": Source(git_url="https://github.com/tukaani-project/xz.git", git_ref="v5.8.1"),
    "jpeg": Source(git_url="https://github.com/libjpeg-turbo/libjpeg-turbo.git",
                   git_ref="3.1.1"),
    "mz": Source(git_url="https://github.com/zlib-ng/minizip-ng.git", git_ref="4.0.10"),
    "sodium": Source(
        url="https://download.libsodium.org/libsodium/releases/libsodium-1.0.20.tar.gz",
        sha256="ebb65ef6ca439333c2bb41a0c1990587288da07f6c7fd07cb3a18cc18d30ce19"),
}

_FLAGS = ("-O3 -DNDEBUG (CMake Release, MinGW branch of cmake/CMakeLists.txt); "
          "dependencies static from pinned source; build tree patched by the "
          "recipe (see the recipe docstring): Info-ZIP projects removed, "
          "CredentialManager.cpp added, vncviewer built as UNICODE with "
          "-fpermissive -municode and a force-included compat header, "
          "__try/__finally and goto-over-initialisation rewritten, .rc paths")


def _ultravnc(version, commit, patch_note):
    return Recipe(
        family="UltraVNC",
        version=version,
        upstream="https://github.com/ultravnc/UltraVNC",
        license="GPL-3.0-or-later",
        source=Source(git_url="https://github.com/ultravnc/UltraVNC.git",
                      git_ref=commit, submodules=False),
        extra_sources=dict(_EXTRA),
        build=_DEPS + [_PATCH, _CONFIGURE, _BUILD],
        artifacts=[Artifact(path="bld-{arch}/%s" % path, component=component)
                   for path, component in _COMPONENTS],
        toolchains=["mingw_x86", "mingw_x64"],
        requires=["cmake", "make", "python3"],
        build_flags=_FLAGS,
        notes="NOT byte-identical to a build of unmodified upstream: "
              "recipe-applied build-tree patches, see the recipe docstring. "
              "Commit %s; the 3rdparty/noVNC submodule is left uninitialised "
              "(the viewer does not use it). %sDependencies (zlib 1.3.1, zstd "
              "1.5.7, xz 5.8.1, libjpeg-turbo 3.1.1, minizip-ng 4.0.10, "
              "libsodium 1.0.20) are built from pinned source as static "
              "libraries, so their functions are present under the UltraVNC "
              "family. The MinGW C runtime glue is removed by the baseline. "
              "winvnc.exe is not built: upstream's CMake does not offer it."
              % (commit[:8], patch_note),
    )


RECIPES = {
    "UltraVNC_1.8.2.9_mingw": _ultravnc(
        "1.8.2.9", "97a077cc5b069c6b2ff87f3131d7d10b9a9d7122",
        "Same commit as the MSVC image of this version. "),
    "UltraVNC_1.8.3.0_mingw": _ultravnc(
        "1.8.3.0", "36c2389f681c9c939d5276323cf6242d26bb00fb",
        "Same commit as the MSVC image of this version. "),
    "UltraVNC_1.8.3.1_mingw": _ultravnc(
        "1.8.3.1", "92bb19b9eb01b043bf84172dfa493cd7b9341076",
        "Same commit as the MSVC image of this version; patch 5 does not "
        "apply (the call is gone). "),
}
