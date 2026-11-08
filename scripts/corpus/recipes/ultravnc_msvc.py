"""UltraVNC (mcrit-data issue #27) - MSVC only.

The evidence is FOSSIL (ACM TOPS 2018): 86 UltraVNC functions matched in Zeus
and 125 in Citadel. Two things in the issue decide what is built.

  * FOSSIL's reference binary was the *viewer*, vncviewer 1.2.13, not the
    server. vncviewer.exe is therefore the component the evidence points at;
    winvnc.exe, the server, is built from the same commit as the second
    component and recorded as such.
  * The attribution to UltraVNC rather than TightVNC or RealVNC rests on
    FOSSIL alone; the families share RFB ancestry. TightVNC is built as its
    own family (issue #70) so the two can be compared.

Version. 1.8.2.9 (97a077cc, 2026-09-06), not the 1.2.x line FOSSIL used. The
1.2.x line was tried first and could not be built here; what was found is
recorded so it is not repeated:

  * "1.2.13" is not a commit. The upstream history (git-svn import, 1862
    commits) carries FILEVERSION 1.2.1.2 from 2016-09-19 until b4034d51
    ("1214", 1.2.1.4), reverts to 1.2.1.2, then reaches 1.2.1.5 (9761329e,
    2017-06-10). No commit carries 1.2.1.3.
  * 1.2.1.4 (and 1.2.1.2) do not build: libjpeg-turbo-win\\ lacks the private
    headers its own .c files include (jdcoefct.h, jdmainct.h, jdmaster.h,
    jdsample.h; error C1083). (Superseded: see the second pass; it builds.)
  * 1.2.1.5 has them and its viewer and server solutions are otherwise
    buildable (nasm installed, Windows SDK 10.0 selected, winvnc.sln copied
    without its duplicate-named installer projects), but the in-tree Info-ZIP
    project zipunzip_src\\zip20\\windll\\visualc\\lib\\zip32.vcxproj fails with
    240 errors from the Windows SDK's own winnt.h, under SDK 10.0.26100.0 and
    again under 10.0.19041.0, on x86 and x64 alike, and nothing else in the
    tree fails. Both UltraVNC executables reference that project, so neither
    is produced. It is in the README's not-built table.
  * (Superseded: see the second pass.) 1.8.3.0 and later cannot be
    fetched by this pipeline: eab6d20a moved the
    3rdparty/noVNC submodule to commit b493d9bb, which noVNC no longer serves,
    and fetch.py updates submodules. 1.8.2.9 is the newest release that can
    be.

1.8.2.9 build. vncviewer\\vncviewer.sln and winvnc\\winvnc.sln, built with
/t:<project> so the installer .vdproj entries of winvnc.sln are never built.
Dependencies come from vcpkg in manifest mode per vcpkg.json (zlib, zstd,
libjpeg-turbo, liblzma, libsodium, minizip-ng), as upstream's
cmake\\VCPKG_README.txt describes for Windows; VcpkgTriplet is forced to the
-md variant vcpkg ships (static libraries, dynamic CRT), because the project's
own VcpkgUseStatic picks x64-windows-static, whose overlay triplet in
triplets\\ sets VCPKG_CRT_LINKAGE static and would put /MT objects into an /MD
link. miniLZO is compiled straight from lzo\\minilzo.c. Nothing is MFC or ATL:
UseOfMfc is false in every project (the .rc files include afxres.h, so the MFC
headers must exist, which the windows-2022 image provides), so there is no
static/dynamic MFC choice to record.

Vendored libraries are mostly not split out. They are statically linked into
the exe by upstream's own project files, so their functions are in the image
under the UltraVNC family exactly as a sample in the wild carries them; the
overlap with the liblzma, libsodium and lzo families is measured and listed in
the README, not removed. That is how BlackBone's AsmJit and rewolf-wow64ext are
handled in this corpus. zlib is the exception (see "zlib" below): it is the one
vendored library whose functions `validate --deep` reports as leakage, and
Recipe.exclude_functions (PR #94, which this change therefore depends on)
removes them.

Overlaps, measured by PicHash over functions of ten instructions or more
(counts of distinct hashes; the artefacts are the four built here):

  * with TightVNC: 83 on x86 and 48 on x64, of 5228 and 4973 UltraVNC
    hashes (84 and 107, of 5314 and 5059, before the zlib functions were
    excluded). That is the RFB code both inherit, plus the libjpeg they both
    link.
  * with data/libzlib: 2 (x86) and 11 (x64) (4 and 79 before the exclusion);
    with data/liblzma 287 and 257; with data/libsodium 140 and 113, all from
    the vcpkg libraries. The zlib functions were the ones the deep check
    failed on: with a sparse checkout of UltraVNC, TightVNC, libzlib, liblzma
    and libsodium it reported 80 PicHashes sharing one symbol name across
    TightVNC, UltraVNC and libzlib (`deflate`, `inflate`, `_tr_flush_block` and
    so on); a further hash, `adler32` against `adler32_z`, was listed as
    differently named. They are now removed by name, see "zlib" below, and the
    same check reports 0 leakage. The 2 and 11 hashes that remain are
    zlib-named functions the exclusion leaves in the image on purpose, and
    libsodium's `crypto_generichash_*` thunk.
  * with the lzo 2.10 reference data (MinGW and MSVC, the lzo branches): 0
    on x86 and 8 on x64 against the MSVC build, from miniLZO.

Glue that survives the baseline, by name: 6 to 47 kept functions per
artefact carry a name that the baseline removed from another of these
artefacts (their hash differs, so the name-and-PicHash rule keeps them).
They are MSVC STL and CRT inline instantiations - `std::vector<...>`,
`__std_remove_4`, `wmemchr`/`wmemcmp` in vncviewer x86, `ATL::AtlThrowImpl` and
`ATL::CAtlException` in winvnc x86 - not project code. The x86 artefacts
also carry unnamed exception funclets (503 and 853 unnamed of 6172 and 7503).

zlib (PR #69; Recipe.exclude_functions comes from PR #94, so #69 depends on
#94). Every image links zlib statically: vcpkg's 1.3.1 in 1.8.x, the in-tree
1.2.11 (zlibstatv12) in 1.2.1.x. Each recipe now sets exclude_functions to one
anchored pattern over exact zlib identifiers (the _ZLIB_* tuples below;
_vendored_zlib.py states the test an identifier has to pass and builds the
pattern). The committed images were re-derived from their own archives, not
rebuilt: the removal the pipeline performs after the glue baseline was applied
to each .7z and .mcrit, and provenance records `exclude_functions`,
`excluded_function_count` and `num_functions_before_exclusion`, so kept +
removed + excluded = total.

  * Removed, per recipe (functions over its four images; identifiers):
    1.2.1.4 154 (41), 1.2.1.5 60 (16), 1.8.2.9 / 1.8.3.0 / 1.8.3.1 318 (80)
    each, 1.8.3.2 372 (93). By evidence, in that order: PicHash of 10 or more
    instructions found in data/libzlib 90 / 28 / 122 / 162; fewer than 10
    instructions and the PicHash of a libzlib function of the same name 40 /
    24 / 43 / 54; neither, but the same exact name and architecture and an
    opcode sequence at least 80% similar to libzlib's function of that name
    24 / 8 / 153 / 156. The last group is zlib built with other flags: the
    libzlib x86 images keep frame pointers and vcpkg's do not, so PicHash
    cannot confirm them (of the 80 functions removed from an x86 1.8.x image
    only 2 have a libzlib PicHash). Every such identifier has a
    PicHash-confirmed function in the same recipe, usually the x64 one.
  * Left in although the name is zlib's: an identifier is dropped from the
    pattern if any function of that name in the recipe fails the test, since
    a name pattern cannot tell two functions apart. 1.8.2.9 to 1.8.3.1 leave
    20 identifiers and 1.8.3.2 leaves 7. Six (`_tr_tally`, `compress_block`,
    `crc32_z`, `deflate_fast`, `deflate_slow`, `inflate`) have no
    PicHash-confirmed function in the recipe. The others share their name
    with a function that is not libzlib's: winvnc.exe also contains a
    differently built zlib-compatible implementation, whose `compress`,
    `compress2`, `compressBound`, `uncompress`, `uncompress2`,
    `deflateBound`, `crc32_combine*`, `adler32_combine` and `_tr_stored_block`
    do not match libzlib (its `deflateBound` is 10 instructions where zlib's
    is 78 or more), and liblzma has its own `fill_window` (PicHash in
    data/liblzma). Functions of those names that are PicHash-identical to
    libzlib therefore stay under UltraVNC: 12 in the four images of a 1.8.2.9,
    1.8.3.0 or 1.8.3.1 recipe, 2 in 1.8.3.2 (`fill_window`), 30 in 1.2.1.4 and
    16 in 1.2.1.5. Only two families hold those hashes, so the deep check does
    not report them. 1.2.1.4 leaves 50 identifiers and 1.2.1.5 leaves 62: 22
    and 27 without a PicHash-confirmed function, 28 and 35 that also name a
    function which is not zlib's (`crc32`, `get_crc_table`, `copy_block` and
    a second `fill_window`, `build_tree`, `compress_block`, `gen_bitlen`,
    `send_tree` and others per image). Those 1.2.1.x functions are probably
    the in-tree Info-ZIP zip sources, which name their deflate, trees and crc
    routines the same way; that was not checked against the source.
  * Not reachable by name: unnamed functions (a few share a PicHash with a
    library family; the check counts them as "no symbol", none is a leakage
    hit), and libsodium's `crypto_generichash_blake2b_update` /
    `crypto_generichash_update`, whose 10-instruction body is PicHash-identical
    to zlib's `adler32_combine64` thunk. Result of the deep check on the
    sparse checkout described above: 80 leakage hashes before (an earlier
    version of this docstring said 59), 0 after.

Forced from the command line, because the projects ask for the opposite:
/MT -> /MD, /GL and /LTCG off (the projects' Link AdditionalOptions carry a
literal /LTCG, which the props file replaces; /DEPENDENTLOADFLAG:0x800, the
other option those lines carried, is put back), LinkIncremental off, /PROFILE
off (it implies /OPT:REF), the post-build signtool step disabled
(PostBuildEventUseInBuild=false; it signs with a certificate this build does
not have), toolset v143 in place of v142, Windows SDK 10.0, and at link /DEBUG
/Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF.

Second pass (PR #69: the versions that first did not build). The
maintainer authorised recipe-applied workarounds for them; none edits an
upstream file, and each image is therefore NOT byte-identical to a build of
unmodified upstream. Every change, with its reason:

  * 1.8.3.0 and later: the fetch failed on `git submodule update`: `fatal:
    remote error: upload-pack: not our ref b493d9bbb599fa4d9a0e5ea4bde957dd812384e7`,
    the 3rdparty/noVNC pin that noVNC does not serve. noVNC contributes no
    code to either executable: the vcxproj lists its files as `<None Include>`
    and winvnc.rc embeds 55 of its .js files as `JS` resources for the web
    viewer. So (a) Source(submodules=False) skips the submodule fetch (a new,
    off-by-default Source option; the provenance still records the pin,
    uninitialised, as `-b493d9bb...`), and (b) noVNC commit
    7c36fabe599e053c5a81e98e091ac636f6c1e174, the pin of 1.8.2.9 and a commit
    noVNC serves, is fetched through extra_sources and copied to
    3rdparty\\noVNC so the 55 resource files exist (all 55 are in that commit;
    v1.7.0 lacks core/clipboard.js). The resource section of winvnc.exe
    therefore carries the web viewer scripts of that older noVNC, not of
    b493d9bb. Code is unaffected.
  * 1.8.3.2 (c757708e, the head of upstream's default branch) builds both
    executables, x86 and x64 (run 42440991418), only with two headers the
    recipe writes into the build tree: this vncviewer.exe is NOT byte-identical
    to unmodified upstream, and neither header is upstream's. Commit 6c44cfc
    ("harden code against buffer overruns") added `#include "ViewerBounds.h"`
    to ClientConnection, ClientConnectionCursor, ClientConnectionUltra2 and
    FileTransfer (.cpp) and `#include "ViewerJpegSource.h"` to
    ClientConnectionTight and ClientConnectionUltra2, and committed neither
    header; they are in none of upstream's four branches (main, 1.9.0.0,
    1.8.4.0_feature_requests, feature/VeNCryptTLS; upstream has no tags) and
    GitHub code search finds no file of either name. Run 42440127604 (before
    any stand-in) failed at the first one:
        ClientConnectionUltra2.cpp(18,10): error C1083: Cannot open include
        file: 'ViewerBounds.h': No such file or directory
    and, with ViewerBounds.h supplied, at the second:
        ClientConnectionUltra2.cpp(25,10): error C1083: Cannot open include
        file: 'ViewerJpegSource.h': No such file or directory
    A scan of every quoted and angle-bracket include in vncviewer\\ and rfb\\
    found no other header absent from the tree (the rest are system, vcpkg or
    sibling-directory headers that the 1.8.3.1 viewer resolves the same way).
    scripts/corpus/exercisers/ultravnc_standin_headers.py writes both files
    into vncviewer\\ of the build tree before msbuild runs; nothing is added to
    a source tree. Both are RECONSTRUCTIONS from the 24 + 6 call sites and
    from the code 6c44cfc deleted at them. What is known and what is chosen:
      ViewerBounds (namespace of function templates, any integer types):
      - clipAxis(position, length, limit, offset): in-out ints and an out
        offset; the per-axis clipping that 6c44cfc removed from
        SoftCursorToScreen, copied in behaviour.
      - rectangle(x, y, w, h, fbW, fbH): the removed body of
        Check_Rectangle_borders (x, y >= 0, x + w <= fbW, y + h <= fbH, no
        wrap-around), written without overflowing additions. Also the new test
        in Copyto0buffer, where the removed test was weaker.
      - framebuffer(w, h, bytesPerPixel): the removed ReadNewFBSize test
        ("a screensize > 20 000 is not possible with current OS"): 0 <= each
        side <= 20000. The bytes-per-pixel argument is accepted and only
        required to be non-negative. CHOSEN, not known: whether upstream also
        caps the byte total.
      - payload(n): 0 <= n <= 104857600. CHOSEN from the literal 104857600 that
        ReadCursorShape and DecompressJpegRect pass as a buffer limit and the
        104857596 (= that - 4) cap ReadScreenUpdate puts on compressed sizes
        before asking for size + 4 bytes.
      - range(offset, length, size): [offset, offset + length) inside
        [0, size], all non-negative, overflow-free. Replaces `m_nCSOffset <
        m_nCSBufferSize` (now with length 4) and `nIndex < nLen - 3`.
      - pixels(w, h, bytesPerPixel, limit): w * h * bytesPerPixel <= limit,
        all non-negative, overflow-free (zero sizes pass: ReadCursorShape
        returns early on an empty cursor after calling it).
      ViewerJpeg (three functions forwarded to by the JpegInitSource,
      JpegFillInputBuffer and JpegSkipInputData callbacks):
      - their bodies are the callbacks' removed bodies (error flag set, input
        window reset, or the skip performed). The error flag is reached through
        cinfo->client_data, which both callers set to &jpegError.
      - RECONSTRUCTED: the removed code reset the window from file-scope
        jpegBufferPtr / jpegBufferLen, which 6c44cfc turned into caller locals
        a callback cannot see. initSource therefore records
        cinfo->src->next_input_byte / bytes_in_buffer, which the callers have
        set when libjpeg calls it from jpeg_read_header, per thread.
    Verified here only with g++ (-std=c++11/14): the six ViewerBounds shapes
    with every argument type the callers pass, and ViewerJpeg round-tripped
    through libjpeg (a full image decodes with the flag clear; a truncated one
    sets it). The MSVC build is the run above. winvnc.exe includes neither
    header. Kept / removed / excluded / total: 6250 / 1588 / 93 / 7931 (x86
    viewer), 6014 / 1617 / 93 / 7724 (x64 viewer) (6343 and 6107 kept before
    the zlib exclusion). PicHash overlap (functions of 10+ instructions,
    distinct hashes) against the 1.8.3.1 viewer: 3158 of 3497 (90.3%) x86,
    2771 of 3243 (85.4%) x64; the hardening commit changed much of the viewer.
    Surviving glue names (kept functions whose name is in another UltraVNC
    msvc143 image's removed list, same architecture): x86 4 (std::bad_alloc,
    std::bad_array_new_length, std::bad_cast, std::exception constructors),
    x64 0. The same run also rebuilt winvnc.exe, which was not adopted: the
    committed images (run before this one) stay, because the rebuild differs
    (x64 7245 functions against 7258, x86 7658 against 7670, both before the
    zlib exclusion; same compiler 19.44.35229) and the cause was not isolated.
    Kept / removed / excluded / total of the committed winvnc: 7165 / 1716 /
    93 / 8974 (x64), 7577 / 1648 / 93 / 9318 (x86).
  * 1.2.1.5 (9761329e) needed six things.
    (1) zip32 failed with 240 errors from winnt.h, `error C2143: syntax error:
    missing ':' before 'constant'`. Cause, found by reading winnt.h of SDK
    10.0.26100: the ARM64 unwind-data struct declares a bit-field `DWORD CR : 2;`
    and Info-ZIP's zip.h has `#define CR 13`, which every .c of the project
    sees before <windows.h> is parsed, so the field becomes `DWORD 13 : 2;`.
    Fix: the generated props file force-includes windows.h for projects named
    zip32* only, so it is parsed first and its include guard makes the later
    include a no-op. (Verified: no zip32 error in run 42410253107.)
    (2) The plain libjpeg-turbo-win.vcxproj that vncviewer.sln and winvnc.sln
    reference does not assemble simd\\jchuffsse2.asm (x86) or
    simd\\jchuff-sse2-64.asm (x64) though jsimd_i386.c / jsimd_x86_64.c call
    them: `libjpeg-turbo-win-static.lib(jsimd_i386.obj) : error LNK2019:
    unresolved external symbol _jsimd_huff_encode_one_block_sse2` and
    `LNK2001 _jconst_huff_encode_one_block`. libjpeg-turbo-winv12.vcxproj does
    list them, so the build uses upstream's own VS2013 solutions
    (vncviewer\\vncviewer_vs2013.sln and winvnc\\winvncv12.sln, which reference
    the *v12.vcxproj files); PlatformToolset is forced to v143 as before.
    (3) FileTransfer.h uses std::string without including <string>
    (`error C2039: 'string': is not a member of 'std'`, `C2061`), which older
    toolsets supplied transitively: <string> is force-included for .cpp items,
    the technique of the TightVNC recipe.
    (4) directxviewer.h includes <d3dx9.h>, which the vcxproj looks for in
    "C:\\Program Files (x86)\\Microsoft DirectX SDK (June 2010)" and the runner
    does not have (`C1083: Cannot open include file: 'd3dx9.h'`). The headers
    come from the Microsoft.DXSDK.D3DX 9.29.952.8 NuGet package, fetched by
    sha256 through extra_sources and put on the include path; the viewer loads
    d3d9 dynamically and needs none of its libraries.
    (5) x64 only: winvnc's PreBuildEvent runs `cl /nologo /MT /Fo..\\Release\\ ...
    /c buildtime.cpp`, an /MT compile into a directory the x64 build never
    creates (`C1083: Cannot open compiler generated file ...\\winvnc\\Release\\
    buildtime.obj`); its output is not linked (buildtime.cpp is also a normal
    ClCompile item). PreBuildEventUseInBuild=false drops it, as the post-build
    signing step is dropped.
    (6) x64 only: the Release|x64 configuration of winvncv12.vcxproj omits
    the `_WIN32_WINNT=0x501;_WIN32_IE=0x0600` that Release|Win32 defines, and
    stdhdrs.h then sets WINVER 0x0500 without _WIN32_WINNT, so HideDesktop.cpp
    reaches ATL with a newer default _WIN32_WINNT than WINVER: `atlwinverapi.h(714,9):
    error C3861: 'LCMapStringEx': identifier not found` (run 42411877665, the
    only error of that project). The generated props file defines the same two
    macros as Release|Win32 does for winvnc* projects on x64.
  * 1.8.3.0 (36c2389f, "1.8.3.0") builds like 1.8.3.1: same noVNC pin, same
    two workarounds, both executables, x86 and x64 (run 42417689317). Its
    images are carried although they are almost the same code as versions
    already carried: PicHash overlap (functions of 10+ instructions,
    distinct hashes) is 99.97% against 1.8.2.9 for the x86 viewer (3460 of
    3461), 96.9% for the x64 viewer, 98.8% / 95.3% for the x86 / x64 server
    against 1.8.2.9 and 99.8% / 98.2% against 1.8.3.1. Kept / removed /
    excluded / total: 6172 / 1587 / 80 / 7839 (x86 viewer), 5943 / 1611 / 80 /
    7634 (x64 viewer), 7511 / 1662 / 79 / 9252 (x86 server), 7110 / 1722 / 79 /
    8911 (x64 server).
  * 1.2.1.4 (b4034d51) builds, both executables, x86 and x64 (run
    42419034988), with three more things the tree does not supply, on top of
    the 1.2.1.5 workarounds (1)-(6) above (which remove the d3dx9.h,
    std::string and buildtime.obj errors recorded earlier for this commit):
    (a) the four private libjpeg headers jdcoefct.h, jdmainct.h, jdmaster.h and
    jdsample.h (`C1083`) were never committed (the tree's jdcoefct.c, jdmaster.c
    and jdsample.c are byte-identical to libjpeg-turbo 1.5.1; jconfig.h says
    1.4.2): copied into libjpeg-turbo-win\\ from commit cb88e5da (tag 1.5.1);
    (b) the same holds for the SIMD Huffman sources that
    libjpeg-turbo-winv12.vcxproj lists as CustomBuild items and jsimd_i386.c /
    jsimd_x86_64.c call (jchuffsse2.asm, jchuff-sse2-64.asm and
    jpeg_nbits_table.inc): copied from the same tag; all seven files are
    byte-identical to what 1.2.1.5 commits (jchuff-sse2.asm is named
    jchuffsse2.asm there; tags 1.5.2 and 1.5.3 differ in that one file);
    (c) winvncv12.vcxproj imports ..\\packages\\Libjpeg-Turbo.1.5.15\\build\\
    native\\Libjpeg-Turbo.targets and raises `error : This project references
    NuGet package(s) that are missing on this computer` (no packages.config or
    restore exists in the tree; 1.2.1.5 drops the import): the package
    (libjpeg-turbo.1.5.15.nupkg, sha256 e6ba0d68...e2e9, nuget.org) is fetched
    by hash and its build\\ directory unpacked there. Under v143 its targets add
    one include directory and link nothing (they link only for v120 and v140).
    The "13 unresolved externals" (zlib `_compress`, `_deflate`, ...) of the
    earlier diagnostic (run 42410253107) did not recur: winvncv12.vcxproj of
    this commit has a ProjectReference to
    zlib-1.2.11\\contrib\\vstudio\\vc10\\zlibstatv12.vcxproj, which the solution
    builds and links, so no zlib workaround is applied; I cannot say why that
    run lacked the library. Kept / removed / excluded / total: 2535 / 1513 /
    42 / 4090 (x86 viewer), 2300 / 1521 / 35 / 3856 (x64 viewer), 3832 / 1560 /
    42 / 5434 (x86 server), 3527 / 1584 / 35 / 5146 (x64 server). Carried
    although redundant: against 1.2.1.5 the PicHash overlap is 96.4% / 89.9%
    (x86 / x64 viewer, of 1403 and 1221 hashes) and 97.7% / 93.8% (server, of
    1967 and 1766), 94.8% over the four images together (6028 of 6357
    hashes). Surviving glue names (kept
    functions named like something the baseline removed from another UltraVNC
    image): 1.2.1.4 has 25 (x86 viewer), 25 (x86 server) and 5 / 5 (x64), the
    same as 1.2.1.5; 1.8.3.0 has 34, 45 and 5 / 5, the same as 1.8.3.1; they
    are MSVC STL and ATL inline instantiations.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._vendored_zlib import zlib_functions


_PROPS = (
    'python -c "'
    "open('msvcprops.props','w').write("
    "'<Project><ItemDefinitionGroup><ClCompile>'"
    "'<RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary>'"
    "'<WholeProgramOptimization>false</WholeProgramOptimization>'"
    "'<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>'"
    "'</ClCompile><Link>'"
    "'<GenerateDebugInformation>true</GenerateDebugInformation>'"
    "'<ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile>'"
    "'<LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration>'"
    "'<EnableCOMDATFolding>false</EnableCOMDATFolding>'"
    "'<OptimizeReferences>false</OptimizeReferences>'"
    "'<Profile>false</Profile>'"
    "'<AdditionalOptions>/Brepro /INCREMENTAL:NO /DEPENDENTLOADFLAG:0x800"
    "</AdditionalOptions>'"
    "'</Link></ItemDefinitionGroup></Project>')"
    '"')

# zlib as each version links it (vcpkg's 1.3.1 for 1.8.x, the in-tree 1.2.11 for
# 1.2.1.x): exact identifiers whose every function in the recipe's four images
# is zlib's. See _vendored_zlib.py for the test and the docstring for the
# identifiers that are left in.
_ZLIB_1_2_1_4 = (
    '_tr_align', '_tr_flush_bits', '_tr_init', 'adler32', 'adler32_combine',
    'adler32_combine64', 'adler32_combine_', 'adler32_z', 'bi_flush',
    'bi_reverse', 'build_bl_tree', 'compress', 'compress2', 'compressBound',
    'deflateInit_', 'deflateStateCheck', 'detect_data_type', 'fixedtables',
    'flush_pending', 'inflateCopy', 'inflateGetDictionary', 'inflateInit_',
    'inflateMark', 'inflatePrime', 'inflateSetDictionary',
    'inflateStateCheck', 'match_init', 'putShortMSB', 'read_buf', 'scan_tree',
    'send_all_trees', 'slide_hash', 'syncsearch', 'uncompress', 'uncompress2',
    'updatewindow', 'zError', 'zcalloc', 'zcfree', 'zlibCompileFlags',
    'zlibVersion',
)
_ZLIB_1_2_1_5 = (
    'bi_flush', 'bi_reverse', 'build_bl_tree', 'compressBound',
    'deflateInit_', 'detect_data_type', 'inflateUndermine', 'match_init',
    'putShortMSB', 'scan_tree', 'syncsearch', 'zError', 'zcalloc', 'zcfree',
    'zlibCompileFlags', 'zlibVersion',
)
_ZLIB_1_8_X = (
    '_tr_align', '_tr_flush_bits', '_tr_flush_block', '_tr_init', 'adler32',
    'adler32_combine64', 'adler32_combine_', 'adler32_z', 'bi_flush',
    'bi_reverse', 'bi_windup', 'build_bl_tree', 'build_tree', 'crc32',
    'crc_word', 'crc_word_big', 'deflate', 'deflateCopy', 'deflateEnd',
    'deflateGetDictionary', 'deflateInit2_', 'deflateInit_', 'deflateParams',
    'deflatePending', 'deflatePrime', 'deflateReset', 'deflateResetKeep',
    'deflateSetDictionary', 'deflateSetHeader', 'deflateStateCheck',
    'deflateTune', 'deflate_huff', 'deflate_rle', 'deflate_stored',
    'detect_data_type', 'fixedtables', 'flush_pending', 'gen_bitlen',
    'gen_codes', 'get_crc_table', 'inflateCodesUsed', 'inflateCopy',
    'inflateEnd', 'inflateGetDictionary', 'inflateGetHeader', 'inflateInit2_',
    'inflateInit_', 'inflateMark', 'inflatePrime', 'inflateReset',
    'inflateReset2', 'inflateResetKeep', 'inflateSetDictionary',
    'inflateStateCheck', 'inflateSync', 'inflateSyncPoint',
    'inflateUndermine', 'inflateValidate', 'inflate_fast', 'inflate_table',
    'init_block', 'lm_init', 'longest_match', 'multmodp', 'pqdownheap',
    'putShortMSB', 'read_buf', 'scan_tree', 'send_all_trees', 'send_tree',
    'slide_hash', 'syncsearch', 'tr_static_init', 'updatewindow', 'x2nmodp',
    'zError', 'zcalloc', 'zcfree', 'zlibCompileFlags', 'zlibVersion',
)
_ZLIB_1_8_3_2 = (
    '_tr_align', '_tr_flush_bits', '_tr_flush_block', '_tr_init',
    '_tr_stored_block', 'adler32', 'adler32_combine', 'adler32_combine64',
    'adler32_combine_', 'adler32_z', 'bi_flush', 'bi_reverse', 'bi_windup',
    'build_bl_tree', 'build_tree', 'compress', 'compress2', 'compressBound',
    'crc32', 'crc32_combine', 'crc32_combine64', 'crc32_combine_gen',
    'crc32_combine_gen64', 'crc32_combine_op', 'crc_word', 'crc_word_big',
    'deflate', 'deflateBound', 'deflateCopy', 'deflateEnd',
    'deflateGetDictionary', 'deflateInit2_', 'deflateInit_', 'deflateParams',
    'deflatePending', 'deflatePrime', 'deflateReset', 'deflateResetKeep',
    'deflateSetDictionary', 'deflateSetHeader', 'deflateStateCheck',
    'deflateTune', 'deflate_huff', 'deflate_rle', 'deflate_stored',
    'detect_data_type', 'fixedtables', 'flush_pending', 'gen_bitlen',
    'gen_codes', 'get_crc_table', 'inflateCodesUsed', 'inflateCopy',
    'inflateEnd', 'inflateGetDictionary', 'inflateGetHeader', 'inflateInit2_',
    'inflateInit_', 'inflateMark', 'inflatePrime', 'inflateReset',
    'inflateReset2', 'inflateResetKeep', 'inflateSetDictionary',
    'inflateStateCheck', 'inflateSync', 'inflateSyncPoint',
    'inflateUndermine', 'inflateValidate', 'inflate_fast', 'inflate_table',
    'init_block', 'lm_init', 'longest_match', 'multmodp', 'pqdownheap',
    'putShortMSB', 'read_buf', 'scan_tree', 'send_all_trees', 'send_tree',
    'slide_hash', 'syncsearch', 'tr_static_init', 'uncompress', 'uncompress2',
    'updatewindow', 'x2nmodp', 'zError', 'zcalloc', 'zcfree',
    'zlibCompileFlags', 'zlibVersion',
)

# Copies each built exe and its PDB to corpusout\ so the artefact paths do not
# depend on where OutDir resolves for Win32 against x64. Newest match wins.
_NAMES = ("vncviewer", "winvnc")
_LOCATE = (
    'python -c "'
    "import glob,os,shutil;"
    "os.makedirs('corpusout',exist_ok=True);"
    "c=lambda n:[g for g in glob.glob('**/'+n+'.exe',recursive=True) "
    "if 'Release' in g and not g.startswith('corpusout')];"
    "f=lambda n:sorted(c(n),key=os.path.getmtime)[-1];"
    "[(print(f(n)),shutil.copy(f(n),'corpusout'),"
    "shutil.copy(f(n)[:-4]+'.pdb','corpusout')) for n in %r]"
    '"' % (_NAMES,))

_MSBUILD = ('msbuild %s /t:%s /p:Configuration=Release '
            '/p:Platform={msbuild_platform} /p:PlatformToolset=v143 '
            '/p:WindowsTargetPlatformVersion=10.0 '
            '/p:WholeProgramOptimization=false /p:LinkIncremental=false '
            '/p:PostBuildEventUseInBuild=false '
            '/p:VcpkgTriplet={asm_arch}-windows-static-md '
            '/p:ForceImportBeforeCppTargets=%%CD%%\\msvcprops.props '
            '/m /v:minimal')

_VCPKG_INTEGRATE = '"%VCPKG_INSTALLATION_ROOT%\\vcpkg.exe" integrate install'

_FLAGS = ("Release configuration of the 1.8.2.9 vcxproj files, platform "
          "toolset v143 in place of v142, Windows SDK 10.0; dependencies "
          "from vcpkg (manifest mode) as the static-library, dynamic-CRT "
          "triplet; /MT replaced by /MD, /GL and /LTCG off; /DEBUG /Brepro "
          "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF /DEPENDENTLOADFLAG:0x800 at "
          "link; post-build signing disabled")


# --- second pass: 1.2.1.5, 1.8.3.1 and 1.8.3.2 (see the docstring) ---------

# Generated props file of the 1.2.1.5 build. Same switches as _PROPS (without
# /DEPENDENTLOADFLAG, which 1.2.x never had), plus: the DirectX headers on the
# include path, windows.h force-included for zip32* projects, and <string>
# force-included for .cpp items. The text is built with placeholder tokens so
# no quote or percent sign reaches cmd.exe: @d is a double quote, @s a single
# quote, @p a percent sign.
_PROPS_1_2 = (
    'python -c "'
    "open('msvcprops.props','w').write(("
    "'<Project><ItemDefinitionGroup><ClCompile>'"
    "'<RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary>'"
    "'<WholeProgramOptimization>false</WholeProgramOptimization>'"
    "'<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>'"
    "'<AdditionalIncludeDirectories>$(MSBuildThisFileDirectory)corpusdx"
    "/build/native/include;@p(AdditionalIncludeDirectories)"
    "</AdditionalIncludeDirectories>'"
    "'</ClCompile><Link>'"
    "'<GenerateDebugInformation>true</GenerateDebugInformation>'"
    "'<ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile>'"
    "'<LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration>'"
    "'<EnableCOMDATFolding>false</EnableCOMDATFolding>'"
    "'<OptimizeReferences>false</OptimizeReferences>'"
    "'<Profile>false</Profile>'"
    "'<AdditionalOptions>/Brepro /INCREMENTAL:NO</AdditionalOptions>'"
    "'</Link></ItemDefinitionGroup>'"
    "'<ItemDefinitionGroup Condition=@d$(MSBuildProjectName.StartsWith(@szip32@s))@d>'"
    "'<ClCompile><ForcedIncludeFiles>windows.h</ForcedIncludeFiles></ClCompile>'"
    "'</ItemDefinitionGroup>'"
    "'<ItemDefinitionGroup Condition=@d@s$(Platform)@s==@sx64@s And "
    "$(MSBuildProjectName.StartsWith(@swinvnc@s))@d>'"
    "'<ClCompile><PreprocessorDefinitions>_WIN32_WINNT=0x501;_WIN32_IE=0x0600;"
    "@p(PreprocessorDefinitions)</PreprocessorDefinitions></ClCompile>'"
    "'</ItemDefinitionGroup>'"
    "'<Target Name=@dForceStringInclude@d BeforeTargets=@dClCompile@d>'"
    "'<ItemGroup><ClCompile Condition=@d@s@p(Extension)@s==@s.cpp@s@d>'"
    "'<ForcedIncludeFiles>string</ForcedIncludeFiles></ClCompile>'"
    "'</ItemGroup></Target></Project>').replace('@d',chr(34)).replace('@s',chr(39))"
    ".replace('@p',chr(37)))"
    '"')


# The two installer projects of winvncv12.sln (.vdproj) cannot be built by
# MSBuild and the solution filter does not help (MSB5004 is raised first). A
# copy of the solution without the .vdproj entries is generated beside it and
# upstream's file is left alone.
_SLN_1_2 = (
    'python -c "'
    r"import re;"
    r"L=open('winvnc/winvncv12.sln',encoding='utf-8-sig').read().splitlines();"
    r"I=[i for i,l in enumerate(L) if l.startswith('Project(') and 'vdproj' in l];"
    r"G=[re.findall(r'\x7b([0-9A-Fa-f-]+)\x7d',L[i])[-1] for i in I];"
    r"D=set([j for i in I for j in range(i,L.index('EndProject',i)+1)]);"
    r"O=[l for j,l in enumerate(L) if j not in D and not any([x in l for x in G])];"
    r"open('winvnc/winvnc_build.sln','w').write(chr(10).join(O)+chr(10));"
    r"print(len(I),'installer projects dropped')"
    '"')

# libjpeg-turbo-win's SIMD sources are assembled with nasm (the project adds
# C:\Program Files\nasm to ExecutablePath); the runner has none (exit 9009).
_NASM = 'choco install nasm -y --no-progress'

# The D3DX9 headers from the pinned NuGet package.
_UNPACK_DXSDK = (
    'python -c "'
    "import zipfile,sys;"
    "zipfile.ZipFile(sys.argv[1]).extractall('corpusdx')"
    '" {dxsdk}')

_MSBUILD_1_2 = ('msbuild %s /t:%s /p:Configuration=Release '
                '/p:Platform={msbuild_platform} /p:PlatformToolset=v143 '
                '/p:WindowsTargetPlatformVersion=10.0 '
                '/p:WholeProgramOptimization=false /p:LinkIncremental=false '
                '/p:PostBuildEventUseInBuild=false '
                '/p:PreBuildEventUseInBuild=false '
                '/p:ForceImportBeforeCppTargets=%%CD%%\\msvcprops.props '
                '/m /v:minimal')

# noVNC files into 3rdparty\noVNC, where winvnc.rc names them.
_COPY_NOVNC = (
    'python -c "'
    "import shutil,sys;"
    "shutil.copytree(sys.argv[1],'3rdparty/noVNC',dirs_exist_ok=True,"
    "ignore=shutil.ignore_patterns('.git'))"
    '" {novnc}')

# --- 1.2.1.4 (see the docstring) --------------------------------------------

# winvncv12.vcxproj imports the NuGet package Libjpeg-Turbo 1.5.15 from
# ..\packages\ and raises an error when it is missing (no packages.config or
# restore is in the tree). Its targets only add an include directory and, for
# the v120 and v140 toolsets, link its own libs; under v143 nothing is linked.
# The package is fetched by sha256 and its build\ directory unpacked where the
# project looks for it.
_UNPACK_LJNUGET = (
    'python -c "'
    "import zipfile,sys;z=zipfile.ZipFile(sys.argv[1]);"
    "z.extractall('winvnc/packages/Libjpeg-Turbo.1.5.15',"
    "[n for n in z.namelist() if n.startswith('build/')])"
    '" {ljnuget}')

# The files libjpeg-turbo-win\ includes or assembles and that 1.2.1.4 never
# committed (1.2.1.5 adds them): four private headers and the SIMD Huffman
# sources, taken from libjpeg-turbo tag 1.5.1 (cb88e5da). Byte-identical to
# the copies in 1.2.1.5 (jchuff-sse2.asm is named jchuffsse2.asm there).
_COPY_JPEG = (
    'python -c "'
    "import shutil,sys;"
    "[shutil.copy(sys.argv[1]+'/'+a,'libjpeg-turbo-win/'+b) for a,b in ["
    "('jdcoefct.h','jdcoefct.h'),('jdmainct.h','jdmainct.h'),"
    "('jdmaster.h','jdmaster.h'),('jdsample.h','jdsample.h'),"
    "('simd/jchuff-sse2.asm','simd/jchuffsse2.asm'),"
    "('simd/jchuff-sse2-64.asm','simd/jchuff-sse2-64.asm'),"
    "('simd/jpeg_nbits_table.inc','simd/jpeg_nbits_table.inc')]]"
    '" {libjpeg}')

_ARTIFACTS = [
    Artifact(path="corpusout\\vncviewer.exe", component="vncviewer.exe",
             pdb="corpusout\\vncviewer.pdb"),
    Artifact(path="corpusout\\winvnc.exe", component="winvnc.exe",
             pdb="corpusout\\winvnc.pdb"),
]

_NOVNC_SOURCE = Source(git_url="https://github.com/novnc/noVNC.git",
                       git_ref="7c36fabe599e053c5a81e98e091ac636f6c1e174")

_NEW_STEPS = [
    BuildStep(_PROPS),
    BuildStep(_COPY_NOVNC),
    BuildStep(_VCPKG_INTEGRATE, allow_failure=True),
    BuildStep(_MSBUILD % ("vncviewer\\vncviewer.sln", "vncviewer"),
              allow_failure=True),
    BuildStep(_MSBUILD % ("winvnc\\winvnc.sln", "winvnc"),
              allow_failure=True),
]

_NEW_FLAGS = (_FLAGS + "; noVNC submodule not fetched, the files for "
              "winvnc.rc's web-viewer resources taken from noVNC 7c36fabe")

_NEW_NOTES = ("Commit %s, version %s. NOT byte-identical to a build of "
              "unmodified upstream: the 3rdparty/noVNC submodule pin "
              "b493d9bb is not served by noVNC, so it is left uninitialised "
              "and noVNC 7c36fabe (the pin of 1.8.2.9) supplies the 55 .js "
              "files winvnc.rc embeds as resources; no code is affected "
              "(see the recipe docstring). %sDependencies come from vcpkg per "
              "vcpkg.json, statically linked into the exes, so those "
              "libraries' functions are present here under the UltraVNC "
              "family, except zlib's, which are removed by name "
              "(exclude_functions, see the recipe docstring); miniLZO is "
              "compiled from lzo\\minilzo.c. The CRT is imported (/MD) and "
              "stays attributed to data/MSVC.")


# 1.8.3.2 only: the two headers upstream never committed, written into the
# build tree (vncviewer\\ViewerBounds.h and vncviewer\\ViewerJpegSource.h, beside
# the sources that include them) by a script that ships with this tooling. See
# the docstring.
_STANDIN = ('python {repo}/scripts/corpus/exercisers/ultravnc_standin_headers.py '
            'vncviewer')

_VB_FLAGS = ("; vncviewer\\ViewerBounds.h and vncviewer\\ViewerJpegSource.h, "
             "which upstream never committed, generated by the recipe as "
             "stand-ins (scripts/corpus/exercisers/ultravnc_standin_headers.py)")

_VB_NOTES = ("The viewer additionally needs two stand-in headers: commit "
             "6c44cfc added #include \"ViewerBounds.h\" (ClientConnection.cpp, "
             "ClientConnectionCursor.cpp, ClientConnectionUltra2.cpp, "
             "FileTransfer.cpp) and #include \"ViewerJpegSource.h\" "
             "(ClientConnectionTight.cpp, ClientConnectionUltra2.cpp) and never "
             "committed either (`ClientConnectionUltra2.cpp(18,10): error C1083: "
             "Cannot open include file: 'ViewerBounds.h': No such file or "
             "directory`, then `ClientConnectionUltra2.cpp(25,10): error C1083: "
             "Cannot open include file: 'ViewerJpegSource.h': No such file or "
             "directory`; neither is in any of upstream's four branches). The "
             "recipe writes both into the build tree: ViewerBounds::framebuffer, "
             "payload, range, pixels, rectangle and clipAxis, and "
             "ViewerJpeg::initSource, fillInputBuffer and skipInputData, "
             "reconstructed from the call sites and from the code 6c44cfc "
             "removed, so vncviewer.exe is NOT byte-identical to unmodified "
             "upstream and its bounds checks and JPEG source-manager state "
             "handling may differ from upstream's own headers; winvnc.exe does "
             "not include them. ")


RECIPES = {
    "UltraVNC_1.8.2.9_msvc": Recipe(
        family="UltraVNC",
        version="1.8.2.9",
        upstream="https://github.com/ultravnc/UltraVNC",
        license="GPL-3.0-or-later",
        source=Source(git_url="https://github.com/ultravnc/UltraVNC.git",
                      git_ref="97a077cc5b069c6b2ff87f3131d7d10b9a9d7122"),
        build=[
            BuildStep(_PROPS),
            BuildStep(_VCPKG_INTEGRATE, allow_failure=True),
            BuildStep(_MSBUILD % ("vncviewer\\vncviewer.sln", "vncviewer"),
                      allow_failure=True),
            BuildStep(_MSBUILD % ("winvnc\\winvnc.sln", "winvnc"),
                      allow_failure=True),
            BuildStep(_LOCATE),
        ],
        artifacts=[
            Artifact(path="corpusout\\vncviewer.exe", component="vncviewer.exe",
                     pdb="corpusout\\vncviewer.pdb"),
            Artifact(path="corpusout\\winvnc.exe", component="winvnc.exe",
                     pdb="corpusout\\winvnc.pdb"),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS,
        exclude_functions=[zlib_functions(_ZLIB_1_8_X)],
        notes="Commit 97a077cc (2026-09-06), version 1.8.2.9, the newest "
              "release whose submodule can be fetched; FOSSIL's 1.2.13 "
              "viewer has no buildable source state (see the recipe "
              "docstring and the README). vncviewer.exe is the component "
              "the evidence points at; winvnc.exe is the server. "
              "Dependencies come from vcpkg per vcpkg.json: zlib, zstd, "
              "libjpeg-turbo, liblzma, libsodium and minizip-ng, statically "
              "linked into the exes, so those libraries' functions are "
              "present here under the UltraVNC family, except zlib's, which "
              "are removed by name (exclude_functions, see the recipe "
              "docstring); miniLZO is compiled from lzo\\minilzo.c. The CRT "
              "is imported (/MD) and stays attributed to data/MSVC.",
    ),
    "UltraVNC_1.2.1.5_msvc": Recipe(
        family="UltraVNC",
        version="1.2.1.5",
        upstream="https://github.com/ultravnc/UltraVNC",
        license="GPL-2.0-or-later",
        source=Source(git_url="https://github.com/ultravnc/UltraVNC.git",
                      git_ref="9761329ece79ab416bd6f17b3d68cbca21c9737c"),
        extra_sources={
            "dxsdk": Source(
                url="https://api.nuget.org/v3-flatcontainer/"
                    "microsoft.dxsdk.d3dx/9.29.952.8/"
                    "microsoft.dxsdk.d3dx.9.29.952.8.nupkg",
                sha256="ead0906ae8a26c18a7525da7490127a2110f7c58f18293738283e30e97c6ea4b"),
        },
        build=[
            BuildStep(_PROPS_1_2),
            BuildStep(_UNPACK_DXSDK),
            BuildStep(_NASM, allow_failure=True),
            BuildStep(_SLN_1_2),
            BuildStep(_MSBUILD_1_2 % ("vncviewer\\vncviewer_vs2013.sln",
                                      "vncviewer"), allow_failure=True),
            BuildStep(_MSBUILD_1_2 % ("winvnc\\winvnc_build.sln", "winvnc"),
                      allow_failure=True),
            BuildStep(_LOCATE),
        ],
        artifacts=_ARTIFACTS,
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="Release configuration of upstream's VS2013 solutions "
                    "(vncviewer_vs2013.sln, winvncv12.sln): /Ox /Ob2 /Oi /Ot "
                    "per project, platform toolset v143 in place of "
                    "v141_xp, Windows SDK 10.0; /MT replaced by /MD, /GL and "
                    "/LTCG off; /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF "
                    "/OPT:NOICF at link, forced by this recipe over "
                    "upstream's /OPT:REF; /PROFILE off; post-build signing "
                    "and winvnc's /MT pre-build compile of buildtime.cpp "
                    "disabled; windows.h force-included for zip32 and <string> "
                    "for C++ items, _WIN32_WINNT/_WIN32_IE as in Release|Win32 for winvnc x64; D3DX9 headers from the Microsoft.DXSDK.D3DX "
                    "9.29.952.8 NuGet package",
        exclude_functions=[zlib_functions(_ZLIB_1_2_1_5)],
        notes="Commit 9761329e (2017-06-10), FILEVERSION 1.2.1.5: the "
              "nearest buildable state to the 1.2.13 viewer FOSSIL used, "
              "which has no commit of its own. NOT byte-identical to a build "
              "of unmodified upstream: windows.h is force-included for the "
              "Info-ZIP project (its #define CR 13 breaks winnt.h's ARM64 "
              "bit-field), <string> for C++ items, D3DX9 headers come from a "
              "NuGet package, and the solutions are upstream's VS2013 ones "
              "so the SIMD Huffman assembly is part of libjpeg-turbo (see "
              "the recipe docstring). vncviewer.exe is the component the "
              "evidence points at; winvnc.exe, the server, is the second "
              "target. Both statically link the in-tree zlib, libjpeg-turbo, "
              "miniLZO and the Info-ZIP sources, so those functions are "
              "present here under the UltraVNC family, except the zlib "
              "functions the recipe removes by name (exclude_functions: 16 "
              "exact identifiers, see the recipe docstring). The CRT is "
              "imported (/MD) and stays attributed to data/MSVC.",
    ),
    "UltraVNC_1.2.1.4_msvc": Recipe(
        family="UltraVNC",
        version="1.2.1.4",
        upstream="https://github.com/ultravnc/UltraVNC",
        license="GPL-2.0-or-later",
        source=Source(git_url="https://github.com/ultravnc/UltraVNC.git",
                      git_ref="b4034d51163fefd9935691a11ec4d3597d5c571f"),
        extra_sources={
            "dxsdk": Source(
                url="https://api.nuget.org/v3-flatcontainer/"
                    "microsoft.dxsdk.d3dx/9.29.952.8/"
                    "microsoft.dxsdk.d3dx.9.29.952.8.nupkg",
                sha256="ead0906ae8a26c18a7525da7490127a2110f7c58f18293738283e30e97c6ea4b"),
            "libjpeg": Source(
                git_url="https://github.com/libjpeg-turbo/libjpeg-turbo.git",
                git_ref="cb88e5da8003afcdc443b787fdcb77285e5a8a02"),
            "ljnuget": Source(
                url="https://api.nuget.org/v3-flatcontainer/libjpeg-turbo/"
                    "1.5.15/libjpeg-turbo.1.5.15.nupkg",
                sha256="e6ba0d683c7048867fb21ba65e1cd40c96e02144d2721095347b24b523d6e2e9"),
        },
        build=[
            BuildStep(_PROPS_1_2),
            BuildStep(_UNPACK_DXSDK),
            BuildStep(_COPY_JPEG),
            BuildStep(_UNPACK_LJNUGET),
            BuildStep(_NASM, allow_failure=True),
            BuildStep(_SLN_1_2),
            BuildStep(_MSBUILD_1_2 % ("vncviewer\\vncviewer_vs2013.sln",
                                      "vncviewer"), allow_failure=True),
            BuildStep(_MSBUILD_1_2 % ("winvnc\\winvnc_build.sln", "winvnc"),
                      allow_failure=True),
            BuildStep(_LOCATE),
        ],
        artifacts=_ARTIFACTS,
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="As UltraVNC_1.2.1.5_msvc (upstream's VS2013 solutions, "
                    "v143, SDK 10.0, /MD, no /GL or /LTCG, /DEBUG /Brepro "
                    "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF, signing and "
                    "buildtime pre-build step disabled, windows.h for zip32, "
                    "<string> for C++ items, _WIN32_WINNT/_WIN32_IE for "
                    "winvnc x64, D3DX9 headers from the NuGet package), plus: "
                    "jdcoefct.h, jdmainct.h, jdmaster.h, jdsample.h and the "
                    "SIMD Huffman sources (jchuffsse2.asm, jchuff-sse2-64.asm, "
                    "jpeg_nbits_table.inc) added to libjpeg-turbo-win from "
                    "libjpeg-turbo 1.5.1 (cb88e5da); the NuGet package "
                    "Libjpeg-Turbo 1.5.15 that winvncv12.vcxproj imports "
                    "unpacked under winvnc\\packages (headers only under v143)",
        exclude_functions=[zlib_functions(_ZLIB_1_2_1_4)],
        notes="Commit b4034d51 (FILEVERSION 1.2.1.4), the half-committed "
              "state before 1.2.1.5. NOT byte-identical to a build of "
              "unmodified upstream: the tree lacks four libjpeg private "
              "headers and the SIMD Huffman assembly its own project lists "
              "(supplied from libjpeg-turbo 1.5.1, identical to what 1.2.1.5 "
              "commits), winvncv12.vcxproj needs the NuGet package "
              "Libjpeg-Turbo 1.5.15 that is not in the tree (fetched by "
              "sha256), and the 1.2.1.5 workarounds apply (windows.h for the "
              "Info-ZIP project, <string> for C++ items, D3DX9 headers from "
              "a NuGet package). See the recipe docstring. Both executables "
              "statically link the in-tree zlib 1.2.11, libjpeg-turbo, "
              "miniLZO and the Info-ZIP sources; 41 exact zlib identifiers "
              "are removed by name (exclude_functions, see the recipe "
              "docstring), the rest is present under the UltraVNC family. "
              "The CRT is imported (/MD) and stays attributed to data/MSVC.",
    ),
    "UltraVNC_1.8.3.0_msvc": Recipe(
        family="UltraVNC",
        version="1.8.3.0",
        upstream="https://github.com/ultravnc/UltraVNC",
        license="GPL-3.0-or-later",
        source=Source(git_url="https://github.com/ultravnc/UltraVNC.git",
                      git_ref="36c2389f681c9c939d5276323cf6242d26bb00fb",
                      submodules=False),
        extra_sources={"novnc": _NOVNC_SOURCE},
        build=_NEW_STEPS + [BuildStep(_LOCATE)],
        artifacts=_ARTIFACTS,
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_NEW_FLAGS,
        exclude_functions=[zlib_functions(_ZLIB_1_8_X)],
        notes=_NEW_NOTES % ("36c2389f (2026-09-12)", "1.8.3.0", ""),
    ),
    "UltraVNC_1.8.3.1_msvc": Recipe(
        family="UltraVNC",
        version="1.8.3.1",
        upstream="https://github.com/ultravnc/UltraVNC",
        license="GPL-3.0-or-later",
        source=Source(git_url="https://github.com/ultravnc/UltraVNC.git",
                      git_ref="92bb19b9eb01b043bf84172dfa493cd7b9341076",
                      submodules=False),
        extra_sources={"novnc": _NOVNC_SOURCE},
        build=_NEW_STEPS + [BuildStep(_LOCATE)],
        artifacts=_ARTIFACTS,
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_NEW_FLAGS,
        exclude_functions=[zlib_functions(_ZLIB_1_8_X)],
        notes=_NEW_NOTES % ("92bb19b9 (2026-10-18)", "1.8.3.1", ""),
    ),
    "UltraVNC_1.8.3.2_msvc": Recipe(
        family="UltraVNC",
        version="1.8.3.2",
        upstream="https://github.com/ultravnc/UltraVNC",
        license="GPL-3.0-or-later",
        source=Source(git_url="https://github.com/ultravnc/UltraVNC.git",
                      git_ref="c757708e83b6c8249a1cdc9b9c0427c4e72f1c21",
                      submodules=False),
        extra_sources={"novnc": _NOVNC_SOURCE},
        build=_NEW_STEPS[:2] + [BuildStep(_STANDIN)] + _NEW_STEPS[2:]
              + [BuildStep(_LOCATE)],
        artifacts=_ARTIFACTS,
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_NEW_FLAGS + _VB_FLAGS,
        exclude_functions=[zlib_functions(_ZLIB_1_8_3_2)],
        notes=_NEW_NOTES % (
            "c757708e (2026-11-02)", "1.8.3.2", _VB_NOTES),
    ),
}
