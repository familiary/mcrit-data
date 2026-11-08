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
images (overlap is measured in the README, not removed), except zlib: its
functions are removed by name, see "zlib" below.

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

Further patches for the addon projects of the same CMake tree (scripts/corpus/
exercisers/ultravnc_mingw_patch.py again; each was measured to apply at all
three pinned commits). None of them touches the viewer or the seven tools:

 8. Case-folded include names. The sources were written on Windows and the
    git tree holds ldapAuth.h, ldapAuth9x.h, ldapAuthnt4.h, Resource.h,
    dsmplugin.h and winvnc/winvnc/Localization.h while they include
    `ldapauth.h`, `ldapauth9x.h`, `ldapauthnt4.h`, `resource.h`, `DSMPlugin.h`
    and `../../../winvnc/winvnc/localization.h`. For every quoted include in
    addon/ms-logon, uvnckeyboardhelper and uvnc_settings that does not resolve
    but resolves ignoring case, the patch script creates a symbolic link with
    the spelled name next to the real file (six links; no file is edited).
    `fatal error: ldapauth.h: No such file or directory` and the
    `resource.h` / `localization.h` errors go away.
 9. Stand-in forwarding headers, generated into <source root>/casefold-inc
    (put on CPATH): `Dsgetdc.h` containing `#include <dsgetdc.h>` and
    `SDKDDKVer.h` containing `#include <sdkddkver.h>` (the sources include
    `<Dsgetdc.h>` and, through targetver.h, `<SDKDDKVer.h>`; mingw-w64 ships
    both in lower case: `fatal error: Dsgetdc.h: No such file or directory`,
    `fatal error: SDKDDKVer.h: No such file or directory`).
10. addon/eventMessageLogger/messages.mc: `MessageID=` becomes `MessageId=`
    (three places). windmc's keywords are case-sensitive; `In messages.mc at
    line 13: parser: syntax error.` was this keyword, not the file structure.
11. try/finally. authSSP (authSSP.cpp, GenClientServerContext.cpp,
    vncAccessControl.cpp), MSLogonACL (vncExportACL.cpp, vncImportACL.cpp) and
    workgrpdomnt4 use `__try { ... __leave; ... } __finally { cleanup }` with
    no `__except`. exercisers/ultravnc_mingw_seh.h, force-included into those
    three targets only (target_compile_options appended to their CMakeLists),
    defines `__try` as `do`, `__leave` as `break` and `__finally` as
    `while (0);`, so the block becomes `do { ... break; ... } while (0);
    { cleanup }`, which runs the cleanup on the normal path and after
    `__leave`. The ten protected blocks (authSSP.cpp 2,
    GenClientServerContext.cpp 1, vncAccessControl.cpp 2, vncExportACL.cpp 1,
    vncImportACL.cpp 2, workgrpdomnt4.cpp 2) contain no `return`, no
    loop or switch around a `__leave` and no goto, so `break` always leaves
    the do-while; only a hardware exception inside a block, which these
    blocks do not handle either, would behave differently. This is a macro
    form of the scope-guard rewrite of patch 4, chosen because it is the same
    text change at every site.
12. goto over initialisations (as patch 6; GCC rejects these even under
    -fpermissive, so no flag is used): repeater\\socket_functions.cpp, the
    four declarations `DWORD start=0; DWORD stop=0; int measure_counter=0;
    long temp_bytes=0;` become declaration plus assignment (`error: jump to
    label 'error'` ... `crosses initialization of 'DWORD start'`);
    uvnckeyboardhelper.cpp, `DWORD dwEvent = WaitForMultipleObjects(...)` and
    `int counter=0;` likewise.
13. repeater, 32-bit only: the i686 import library for msvcrt.dll has no
    `_ltoa_s` (`undefined reference to `_imp___ltoa_s'`); repeater.cpp:61
    calls `_ltoa_s(value, buf, 10)`. exercisers/ultravnc_mingw_repeater_x86.h,
    force-included into repeater when UVNC_REPEATER_X86 is set (x86 only),
    includes <stdlib.h> and defines `_ltoa_s(v, b, r)` as `(_ltoa(v, b, r), 0)`.
    The x64 image calls msvcrt's own `_ltoa_s`.

The addon images built from these patches (and the compiler warning that
remains in MSLogonACL: `vncImportACL.cpp:27:35: warning: deleting 'PSID' {aka
'void*'} is undefined [-Wdelete-incomplete]`, three places, which is upstream's
code and is compiled as written) are NOT byte-identical to a build of
unmodified upstream.

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

Not built from this CMake tree (winvnc is now built, see patches 14-20), with the exact errors (all identical at the
three pinned commits; the cmake directory does not change between 1.8.2.9 and
1.8.3.2):
  * uvnc_settings: `fatal error: natupnp.h: No such file or directory`
    (upnp.h:28). mingw-w64 has no natupnp.h; a stand-in would have to declare
    the IUPnPNAT, IStaticPortMappingCollection and IStaticPortMapping COM
    interfaces from memory, and a wrong vtable layout would be a wrong image,
    so none was written.
  * logmessages x86 (all three versions): built, but the DLL has 3 functions
    after the MinGW glue is removed, below the floor of 8 (`logmessages.dll
    yielded only 3 functions, which is too little to be useful reference data
    (this recipe requires 8)`); it is reported as excluded by the floor, not
    forced in. The x64 DLL has 10 functions and is kept.
winvnc.exe (patches 14-20; ultravnc_mingw_winvnc_patch.py, run after the one
above; each pattern must match the stated number of times, and all of them
match at the three pinned commits). Upstream comments winvnc out of its CMake
tree and the CMake project is stale against winvnc.vcxproj, which MSVC builds.
The image is NOT byte-identical to a build of unmodified upstream, and it is
not the MSVC build either: the changes below were measured to be what
compiles and links with MinGW-w64 GCC 13, not what upstream's maintainers
build.

14. cmake\\CMakeLists.txt: `#add_subdirectory(winvnc)` becomes
    `add_subdirectory(winvnc)`.
15. cmake\\winvnc\\CMakeLists.txt, the dropped cloud code: `    libudtcloud`
    and `    CloudDialog.cpp` are deleted. Reason: libudtcloud's sources
    (UdtCloudlib/proxy/Cloudthread.cpp, proxy.cpp, ringbuffer.cpp) and the
    udt4 library it links are not in the UltraVNC repository or a submodule
    (`CMake Error at libudtcloud/CMakeLists.txt:23 (target_sources): Cannot
    find source file: .../UdtCloudlib/proxy/Cloudthread.cpp`; the sibling
    repository is not reachable from the build host: git ls-remote needs a
    login, https returns 403, raw.githubusercontent.com 404). The code is
    compiled out upstream as well: CloudDialog.cpp wraps everything in
    `#ifdef _CLOUD`, no project defines _CLOUD, and winvnc.vcxproj neither
    lists CloudDialog.cpp nor links UdtCloudlib, so the MSVC winvnc.exe has
    no cloud code either. No stand-in for UdtCloudlib was written.
16. cmake\\winvnc\\CMakeLists.txt, source list brought in line with
    winvnc.vcxproj: `    inifile.cpp` and `    initipp.cpp` are deleted (the
    files are not in winvnc\\winvnc; `Cannot find source file:
    .../winvnc/winvnc/inifile.cpp`), and ../../common/inifile.cpp,
    ../loadmemory/MemoryModule.c, ../loadmemory/loadDllFromMemory.cpp,
    DlgChangePassword.cpp, RulesListView.cpp, ScSelect.cpp and
    SchannelTLS.cpp (the vcxproj's other ClCompile items; the three
    table*template.cpp items are #included by translate.cpp) are added;
    `    libzip32` and `    libzipunzip` are deleted from the link list
    (as patch 1; `cannot find -llibzip32`).
17. cmake\\winvnc\\CMakeLists.txt, appended:
        target_compile_definitions(winvnc PRIVATE _CRT_SECURE_NO_WARNINGS SODIUM_STATIC)
        target_compile_options(winvnc PRIVATE -fpermissive -std=gnu++17
            "SHELL:-include ${UVNC_COMPAT}" "SHELL:-include ${UVNC_WINVNC_COMPAT}"
            "SHELL:-include ${UVNC_SEH}")
        target_link_directories(winvnc PRIVATE ${UVNC_DEPS_LIB})
        target_link_libraries(winvnc PRIVATE ${UVNC_DEPS_LIB}/libminizip-ng.a
            winmm d3d11 dxgi bcrypt ncrypt crypt32 secur32)
    (the vcxproj's Release definitions, C++17 and libraries; -fpermissive for
    vnclog.h:54 `extra qualification 'VNCLog::' on member 'Print'`; the
    SEH header is the one of patch 11). ultravnc_mingw_winvnc_compat.h adds
    the MSVC array overload `wcsncat_s(wchar_t (&)[N], const wchar_t*, size_t)`
    (vncmenu.cpp:445: `too few arguments to function 'errno_t wcsncat_s'`).
    The force-included header of the viewer is reused.
18. Source edits: (a) the macro `VNCLOG(s)` is `(__FUNCTION__ " : " s)` in
    stdhdrs.h, benchmark.cpp and DSMPlugin.cpp; GCC's __FUNCTION__ is a
    variable, not a literal (`expected ')' before string constant`, ~400
    sites), so it becomes `(s)`: the log strings lose their function-name
    prefix. (b) Dtwinver.cpp: the integer suffix `ui64` becomes `ULL` (four
    places; `unable to find numeric literal operator 'operator""ui64'`).
    (c) vncclient.cpp: the `__try { bUnzipOk = m_pZipUnZip->UnZipDirectory(
    szPathW, szFileNameW); } __except(EXCEPTION_EXECUTE_HANDLER) { bUnzipOk
    = false; }` becomes the bare call, so a hardware exception inside the
    unzip is no longer swallowed (`expected 'catch' before '__except'`).
    (d) SchannelTLS.cpp: `#include <algorithm>` and `using std::min;` after
    `#include "vnclog.h"` (`'min' was not declared in this scope`).
19. Case folding, as patch 8/9 (links next to the real file, no file edited;
    forwarding headers in casefold-inc): quoted includes in winvnc\\winvnc,
    winvnc\\loadmemory, DSMPlugin, common and rfb (vncEncoder.h, vncServer.h,
    and in DSMPlugin\\MSRC4Plugin and TestPlugin REGISTRY.h / stdafx.h, which
    are not compiled) and the system headers CommCtrl.h, VersionHelpers.h,
    WinSock2.h, Windows.h and WtsApi32.h that mingw-w64 has in lower case
    (`fatal error: WtsApi32.h: No such file or directory`).
20. unofficial-sodium. cmake\\winvnc\\CMakeLists.txt does find_package(
    unofficial-sodium CONFIG REQUIRED) (`Could not find a package
    configuration file provided by "unofficial-sodium"`), vcpkg's package.
    The recipe copies ultravnc_mingw_sodium_config.cmake into the dependency
    prefix as share/unofficial-sodium/unofficial-sodiumConfig.cmake: it
    declares the imported static target unofficial-sodium::sodium on the
    libsodium.a and include directory that this recipe built (SODIUM_STATIC),
    nothing more. noVNC: winvnc.rc embeds 55 noVNC .js files from
    3rdparty\\noVNC, whose submodule pin (b493d9bb) is not served and stays
    uninitialised (Source.submodules is False); noVNC commit 7c36fabe
    (the pin of 1.8.2.9, as in ultravnc_msvc.py) is fetched as an extra
    source and copied there. The resource section therefore carries that
    noVNC's scripts, not those of b493d9bb; code is unaffected.
The binary imports libgcc_s_seh-1.dll and libstdc++-6.dll, as upstream's
cmake installs them next to the programs.

Data (winvnc.exe; kept + removed + excluded = total, from provenance.json; the
74 excluded are zlib functions removed by name as for the viewer):
  x64  1.8.2.9  5019 + 204 + 74 = 5297   x86  1.8.2.9  5328 + 210 + 74 = 5612
  x64  1.8.3.0  5018 + 204 + 74 = 5296   x86  1.8.3.0  5330 + 210 + 74 = 5614
  x64  1.8.3.1  5019 + 204 + 74 = 5297   x86  1.8.3.1  5331 + 210 + 74 = 5615
Every version now has 35 images: the 33 above plus winvnc.exe x86 and x64.

Built by patches 8-13 (the earlier list of failures, now resolved): ldapauth,
ldapauth9x, ldapauthnt4 (patch 8, 9), uvnckeyboardhelper (8, 9, 12), authSSP
(8, 9, 11), MSLogonACL (11), repeater (12, 13 on x86), logmessages (10) and,
because logmessages was its stated blocker, workgrpdomnt4 (11).

Data. UltraVNC 1.8.3.1 (92bb19b9) has 33 images: the first 16 (eight
components, x86 and x64) are in the table below, the other 17 (addon projects)
follow the 1.8.2.9 / 1.8.3.0 text; 1.8.2.9 and 1.8.3.0 are described after this table. Counts, kept +
removed + excluded = total, read from data/UltraVNC/provenance.json (kept =
num_functions, removed = removed_runtime_functions, excluded =
excluded_function_count, the zlib functions removed by name, see below):

  x86  vncviewer.exe        4258 +  189 + 74 =  4521
  x86  createpassword.exe     30 +   62 +  0 =    92
  x86  setpasswd.exe          30 +  127 +  0 =   157
  x86  setcad.exe              8 +   59 +  0 =    67
  x86  testauth.exe            9 +  127 +  0 =   136
  x86  authadmin.dll           9 +  114 +  0 =   123
  x86  logging.dll            58 +  115 +  0 =   173
  x86  vnchooks.dll           28 +   49 +  0 =    77
  x64  vncviewer.exe        4044 +  182 + 74 =  4300
  x64  createpassword.exe     53 +   64 +  0 =   117
  x64  setpasswd.exe          53 +  123 +  0 =   176
  x64  setcad.exe             21 +   61 +  0 =    82
  x64  testauth.exe           28 +  124 +  0 =   152
  x64  authadmin.dll          26 +  109 +  0 =   135
  x64  logging.dll            52 +  110 +  0 =   162
  x64  vnchooks.dll           69 +   50 +  0 =   119

  Total over the 16 images: 8776 kept + 1665 removed + 148 excluded = 10589.

Overlap with the MSVC images of the same version, 1.8.3.1 (distinct PicHashes of
functions of 10+ instructions): the MinGW viewer has 2792 (x86) and 2509 (x64),
the MSVC viewer 3466 and 3220, and they share 84 and 47. All eight MinGW
components together (2857 / 2569) share 84 / 49 with the MSVC viewer plus
server; nothing beyond the viewer adds more than 2. A different compiler
and standard library mostly changes the hashes, so this is a different axis
rather than a duplicate. (Before the zlib functions were excluded the viewers
had 2854 / 2570 and 3534 / 3288 and the eight components 2919 / 2630; the
shared counts did not change, since zlib's hashes are not shared between the
two compilers.)

UltraVNC 1.8.2.9 (97a077cc) and 1.8.3.0 (36c2389f) were built through the same
pipeline with the same patches (patch 5 applies at both; every pattern matched
the stated number of times) and have the same 16 images each. kept + removed +
excluded = total per image, from data/UltraVNC/provenance.json (the 1.8.2.9 and
1.8.3.0 numbers equal the 1.8.3.1 ones except for the viewer):

  version  x86 vncviewer.exe       x64 vncviewer.exe       seven tools (x86 / x64)
  1.8.2.9  4263 + 189 + 74 = 4526  4041 + 182 + 74 = 4297  as 1.8.3.1 above
  1.8.3.0  4263 + 189 + 74 = 4526  4041 + 182 + 74 = 4297  as 1.8.3.1 above

  Totals over the 16 images: 8778 kept + 1665 removed + 148 excluded = 10591 at
  both versions. 1.8.3.1 (above): 8776 + 1665 + 148 = 10589.

Addon images (patches 8-13). Each of the three versions has 17 more images
besides the 16 above (33 per version; the per-image numbers are identical at
1.8.2.9, 1.8.3.0 and 1.8.3.1, because these projects did not change). kept +
removed + excluded = total, excluded 0 (they contain no zlib), from
data/UltraVNC/provenance.json:

  x86  ldapauth.dll         16 + 111 + 0 = 127   x64  ldapauth.dll         36 + 106 + 0 = 142
  x86  ldapauth9x.dll       16 + 111 + 0 = 127   x64  ldapauth9x.dll       35 + 106 + 0 = 141
  x86  ldapauthnt4.dll      16 + 111 + 0 = 127   x64  ldapauthnt4.dll      36 + 106 + 0 = 142
  x86  uvnckeyboardhelper   33 +  62 + 0 =  95   x64  uvnckeyboardhelper   65 +  64 + 0 = 129
  x86  authSSP.dll          66 + 120 + 0 = 186   x64  authSSP.dll         126 + 116 + 0 = 242
  x86  MSLogonACL.exe       76 + 150 + 0 = 226   x64  MSLogonACL.exe      109 + 144 + 0 = 253
  x86  repeater.exe        174 + 154 + 0 = 328   x64  repeater.exe        289 + 147 + 0 = 436
  x86  workgrpdomnt4.dll    15 + 133 + 0 = 148   x64  workgrpdomnt4.dll    42 + 128 + 0 = 170
  x86  logmessages.dll      3 functions: below the floor, no image           x64  logmessages.dll      10 +  50 + 0 =  60

  Per version: 1160 kept + 1919 removed + 0 excluded = 3079 over the 17 new
  images. All 33 images of a version: 1.8.3.1 9936 + 3584 + 148 = 13668;
  1.8.2.9 and 1.8.3.0 9938 + 3584 + 148 = 13670. Most of what the small DLLs
  contain is the MinGW C runtime (removed by the baseline) and the functions
  of their own few source files, so the kept counts are small; the
  workgrpdomnt4 and ldapauth families of DLLs are near copies of each other
  within a version.

zlib (PR #69; Recipe.exclude_functions comes from PR #94, so #69 depends on
#94). The viewer links zlib 1.3.1 statically, and its functions are PicHash-
identical to data/libzlib, which `validate --deep` reported as leakage (one
symbol name under TightVNC, UltraVNC and libzlib). The recipe now sets
exclude_functions to one anchored pattern over 74 exact zlib identifiers
(_ZLIB_FUNCTIONS; _vendored_zlib.py builds the pattern and states the test an
identifier must pass). Per version, the 74 + 74 = 148 functions removed from the
x86 and x64 viewers are, by evidence: 117 with a PicHash of 10 or more
instructions in data/libzlib, 18 with fewer than 10 instructions and the
PicHash of a libzlib function of the same name, and 13 (x86 only) whose hash
differs from every libzlib build but whose opcode sequence is at least 80%
similar to libzlib's function of that name. One zlib-named identifier is left
in: `copy_block`, a 13-instruction function that does not match libzlib's. The
tools contain no zlib: the recipe's pattern removes nothing from their images,
so their kept counts are unchanged and only their provenance gains
`excluded_function_count` 0. The images were re-derived from their archives,
not rebuilt.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._vendored_zlib import zlib_functions

# zlib 1.3.1, built statically into the viewer: exact identifiers whose every
# function in the three recipes' viewers is zlib's (see _vendored_zlib.py).
_ZLIB_FUNCTIONS = (
    '_tr_align', '_tr_flush_bits', '_tr_flush_block', '_tr_init',
    '_tr_stored_block', '_tr_tally', 'adler32', 'adler32_combine',
    'adler32_combine64', 'adler32_z', 'build_tree', 'compress', 'compress2',
    'compressBound', 'compress_block', 'crc32', 'crc32_combine',
    'crc32_combine64', 'crc32_combine_gen', 'crc32_combine_gen64',
    'crc32_combine_op', 'crc32_z', 'deflate', 'deflateBound', 'deflateCopy',
    'deflateEnd', 'deflateGetDictionary', 'deflateInit2_', 'deflateInit_',
    'deflateParams', 'deflatePending', 'deflatePrime', 'deflateReset',
    'deflateResetKeep', 'deflateSetDictionary', 'deflateSetHeader',
    'deflateTune', 'deflate_fast', 'deflate_slow', 'deflate_stored',
    'fill_window', 'get_crc_table', 'inflate', 'inflateCodesUsed',
    'inflateCopy', 'inflateEnd', 'inflateGetDictionary', 'inflateGetHeader',
    'inflateInit2_', 'inflateInit_', 'inflateMark', 'inflatePrime',
    'inflateReset', 'inflateReset2', 'inflateResetKeep',
    'inflateSetDictionary', 'inflateSync', 'inflateSyncPoint',
    'inflateUndermine', 'inflateValidate', 'inflate_fast', 'inflate_table',
    'longest_match', 'pqdownheap', 'scan_tree', 'send_tree', 'uncompress',
    'uncompress2', 'updatewindow', 'zError', 'zcalloc', 'zcfree',
    'zlibCompileFlags', 'zlibVersion',
)

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

# The dependency prefix, then the recipe-generated forwarding headers.
_CPATH = ("{source_root}/deps-{arch}/prefix/include:"
          "{source_root}/casefold-inc")

_PATCH = BuildStep("python3 -I {repo}/scripts/corpus/exercisers/ultravnc_mingw_patch.py .")

# Patches 14-20: winvnc.exe. noVNC's files (winvnc.rc embeds 55 of them) are
# copied to 3rdparty/noVNC, the sodium find-config shim into the dependency
# prefix, then the CMake/source patches are applied.
_WINVNC = [
    BuildStep("python3 -c \"import shutil,sys;shutil.copytree(sys.argv[1],"
              "'3rdparty/noVNC',dirs_exist_ok=True,"
              "ignore=shutil.ignore_patterns('.git'))\" {novnc}"),
    BuildStep("mkdir -p deps-{arch}/prefix/share/unofficial-sodium && "
              "cp {repo}/scripts/corpus/exercisers/ultravnc_mingw_sodium_config.cmake "
              "deps-{arch}/prefix/share/unofficial-sodium/unofficial-sodiumConfig.cmake"),
    BuildStep("python3 -I {repo}/scripts/corpus/exercisers/ultravnc_mingw_winvnc_patch.py ."),
]

_CONFIGURE = BuildStep(
    "cmake -S cmake -B bld-{arch} -DCMAKE_SYSTEM_NAME=Windows "
    "-DCMAKE_SYSTEM_PROCESSOR={platform} -DCMAKE_C_COMPILER={cc} "
    "-DCMAKE_CXX_COMPILER={cxx} -DCMAKE_RC_COMPILER={windres} "
    "-DCMAKE_AR=$(command -v {ar}) -DCMAKE_RANLIB=$(command -v {ranlib}) "
    "-DCMAKE_FIND_ROOT_PATH=\"/usr/{host};$PWD/deps-{arch}/prefix\" "
    "-DCMAKE_PREFIX_PATH=$PWD/deps-{arch}/prefix -DCMAKE_BUILD_TYPE=Release "
    "-DUVNC_COMPAT={repo}/scripts/corpus/exercisers/ultravnc_mingw_compat.h "
    "-DUVNC_SEH={repo}/scripts/corpus/exercisers/ultravnc_mingw_seh.h "
    "-DUVNC_WINVNC_COMPAT={repo}/scripts/corpus/exercisers/ultravnc_mingw_winvnc_compat.h "
    "$(if [ {bitness} = 32 ]; then echo -DUVNC_REPEATER_X86={repo}/scripts/corpus/exercisers/ultravnc_mingw_repeater_x86.h; fi) "
    "-DUVNC_DEPS_LIB=$PWD/deps-{arch}/prefix/lib",
    env=dict(_ENV, CPATH=_CPATH))

# `-k`: the CMake tree builds a dozen projects and several of them cannot
# build (see the docstring); the artefacts below are checked by the pipeline.
_BUILD = BuildStep("cmake --build bld-{arch} -j$(nproc) -- -k",
                   env=dict(_ENV, CPATH=_CPATH),
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
    # Added by the case-fold / try-finally / goto patches (docstring 8-12).
    ("ldapauth/ldapauth.dll", "ldapauth.dll"),
    ("ldapauth9x/ldapauth9x.dll", "ldapauth9x.dll"),
    ("ldapauthnt4/ldapauthnt4.dll", "ldapauthnt4.dll"),
    ("uvnckeyboardhelper/uvnckeyboardhelper.exe", "uvnckeyboardhelper.exe"),
    ("authSSP/authSSP.dll", "authSSP.dll"),
    ("MSLogonACL/MSLogonACL.exe", "MSLogonACL.exe"),
    ("repeater/repeater.exe", "repeater.exe"),
    ("workgrpdomnt4/workgrpdomnt4.dll", "workgrpdomnt4.dll"),
    ("logmessages/logmessages.dll", "logmessages.dll"),
    ("winvnc/winvnc.exe", "winvnc.exe"),
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
    # noVNC's pin in the UltraVNC repo (b493d9bb) is not served any more, the
    # submodule stays uninitialised; the commit ultravnc_msvc.py uses (the pin
    # of 1.8.2.9) supplies the files winvnc.rc embeds.
    "novnc": Source(git_url="https://github.com/novnc/noVNC.git",
                    git_ref="7c36fabe599e053c5a81e98e091ac636f6c1e174"),
}

_FLAGS = ("-O3 -DNDEBUG (CMake Release, MinGW branch of cmake/CMakeLists.txt); "
          "dependencies static from pinned source; build tree patched by the "
          "recipe (see the recipe docstring): Info-ZIP projects removed, "
          "CredentialManager.cpp added, vncviewer built as UNICODE with "
          "-fpermissive -municode and a force-included compat header, "
          "__try/__finally and goto-over-initialisation rewritten, .rc paths; "
          "addon projects (ldapauth*, authSSP, MSLogonACL, repeater, "
          "uvnckeyboardhelper, logmessages, workgrpdomnt4): case-folded "
          "include links, <Dsgetdc.h>/<SDKDDKVer.h> forwarding headers, "
          "MessageID->MessageId in messages.mc, try/finally macros "
          "force-included into authSSP/MSLogonACL/workgrpdomnt4, goto "
          "declarations split in repeater and uvnckeyboardhelper, _ltoa_s "
          "shim for 32-bit repeater; winvnc: CMake target enabled, "
          "libudtcloud/CloudDialog.cpp dropped, source list per vcxproj, "
          "VNCLOG function-name prefix dropped, ui64->ULL, __try/__except "
          "removed, unofficial-sodium find-config for the built libsodium")


def _ultravnc(version, commit, patch_note):
    return Recipe(
        family="UltraVNC",
        version=version,
        upstream="https://github.com/ultravnc/UltraVNC",
        license="GPL-3.0-or-later",
        source=Source(git_url="https://github.com/ultravnc/UltraVNC.git",
                      git_ref=commit, submodules=False),
        extra_sources=dict(_EXTRA),
        build=_DEPS + [_PATCH] + _WINVNC + [_CONFIGURE, _BUILD],
        artifacts=[Artifact(path="bld-{arch}/%s" % path, component=component)
                   for path, component in _COMPONENTS],
        toolchains=["mingw_x86", "mingw_x64"],
        requires=["cmake", "make", "python3"],
        build_flags=_FLAGS,
        exclude_functions=[zlib_functions(_ZLIB_FUNCTIONS)],
        notes="NOT byte-identical to a build of unmodified upstream: "
              "recipe-applied build-tree patches, see the recipe docstring. "
              "Commit %s; the 3rdparty/noVNC submodule is left uninitialised "
              "(the viewer does not use it). %sDependencies (zlib 1.3.1, zstd "
              "1.5.7, xz 5.8.1, libjpeg-turbo 3.1.1, minizip-ng 4.0.10, "
              "libsodium 1.0.20) are built from pinned source as static "
              "libraries, so their functions are present under the UltraVNC "
              "family, except zlib's, which are removed by name "
              "(exclude_functions: 74 exact zlib identifiers, see the recipe "
              "docstring). The MinGW C runtime glue is removed by the "
              "baseline. "
              "Addon images (ldapauth*, authSSP, MSLogonACL, repeater, "
              "uvnckeyboardhelper, logmessages, workgrpdomnt4) additionally "
              "rely on the case-fold, forwarding-header, try/finally and "
              "goto patches 8-13 of the docstring; logmessages.dll x86 has 3 "
              "functions and is below the floor, so it has no image. "
              "winvnc.exe additionally relies on patches 14-20 of the docstring "
              "(CMake target enabled and its source list corrected, "
              "libudtcloud and CloudDialog.cpp dropped as upstream's MSVC "
              "build does, VNCLOG/ui64/__except edits, forwarding headers, "
              "a find-config for the built libsodium, noVNC files from "
              "7c36fabe for the .rc); uvnc_settings fails on the missing "
              "natupnp.h."
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
