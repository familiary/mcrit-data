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
    jdsample.h; error C1083).
  * 1.2.1.5 has them and its viewer and server solutions are otherwise
    buildable (nasm installed, Windows SDK 10.0 selected, winvnc.sln copied
    without its duplicate-named installer projects), but the in-tree Info-ZIP
    project zipunzip_src\\zip20\\windll\\visualc\\lib\\zip32.vcxproj fails with
    240 errors from the Windows SDK's own winnt.h, under SDK 10.0.26100.0 and
    again under 10.0.19041.0, on x86 and x64 alike, and nothing else in the
    tree fails. Both UltraVNC executables reference that project, so neither
    is produced. It is in the README's not-built table.
  * 1.8.3.0 and later cannot be fetched by this pipeline: eab6d20a moved the
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

Vendored libraries are not split out. They are statically linked into the exe
by upstream's own project files, so their functions are in the image under the
UltraVNC family exactly as a sample in the wild carries them; the overlap with
the zlib, liblzma, libsodium and lzo families is measured and listed in the
README, not removed. That is how BlackBone's AsmJit and rewolf-wow64ext are
handled in this corpus.

Overlaps, measured by PicHash over functions of ten instructions or more
(counts of distinct hashes; the artefacts are the four built here):

  * with TightVNC: 84 on x86 and 107 on x64, of 5314 and 5059 UltraVNC
    hashes. That is the RFB code both inherit, plus the zlib and libjpeg
    they both link.
  * with data/libzlib: 4 (x86) and 79 (x64); with data/liblzma 287 and 257;
    with data/libsodium 140 and 113, all from the vcpkg libraries. The zlib
    functions are the ones the deep check fails on: 59 PicHashes share one
    symbol name across TightVNC, UltraVNC and libzlib (`deflate`, `inflate`,
    `_tr_flush_block` and so on). No mechanism in this tooling excludes a
    vendored library from its host family, so they are reported rather than
    hidden; `validate --deep` on a corpus holding these families fails on
    exactly those 59 hashes.
  * with the lzo 2.10 reference data (MinGW and MSVC, the lzo branches): 0
    on x86 and 8 on x64 against the MSVC build, from miniLZO.

Glue that survives the baseline, by name: 6 to 47 kept functions per
artefact carry a name that the baseline removed from another of these
artefacts (their hash differs, so the name-and-PicHash rule keeps them).
They are MSVC STL and CRT inline instantiations - `std::vector<...>`,
`__std_remove_4`, `wmemchr`/`wmemcmp` in vncviewer x86, `ATL::AtlThrowImpl` and
`ATL::CAtlException` in winvnc x86 - not project code. The x86 artefacts
also carry unnamed exception funclets (503 and 853 unnamed of 6252 and 7582).

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
  * 1.8.3.2 (c757708e, the head of upstream's default branch) builds winvnc.exe
    but not vncviewer.exe: `ClientConnectionUltra2.cpp(18,10): error C1083:
    Cannot open include file: 'ViewerBounds.h'`. 6c44cfc ("harden code against
    buffer overruns") added `#include "ViewerBounds.h"` to ClientConnectionCursor,
    ClientConnectionUltra2 and FileTransfer and never committed the header; it is
    in none of upstream's four branches (main, 1.9.0.0, 1.8.4.0_feature_requests,
    feature/VeNCryptTLS). Nothing is invented to stand in for it:
    1.8.3.2 is built with its server only, and the viewer is taken from 1.8.3.1
    (92bb19b9), the last release before that commit, which builds both.
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
  * 1.2.1.4 (b4034d51) is not built. The `jdcoefct.h` error (C1083) is
    resolvable: the tree's jdcoefct.c, jdmaster.c and jdsample.c are
    byte-identical to libjpeg-turbo 1.5.1 (1.5.0 differs in two) though
    jconfig.h says 1.4.2, and the four private headers jdcoefct.h, jdmainct.h,
    jdmaster.h and jdsample.h were never committed (1.2.1.5 adds them,
    byte-identical to the 1.5.0-1.5.3 tags); supplied from commit cb88e5da
    (tag 1.5.1) as a build-side include directory, that error went away. The
    tree is nonetheless a half-committed state: the winvnc link failed with 13
    unresolved externals (zlib: `_compress`, `_uncompress`, `_adler32`,
    `_deflate`, `_deflateEnd`, `_deflateParams`, `_deflateInit2_`, ... because
    zlib-1.2.11\\contrib\\vstudio\\vc10\\x86\\ZlibStatRelease\\zlibstat.lib is not
    produced by its sln) and the jpeg SIMD asm files of 1.2.1.5 are absent.
    1.2.1.5 is the buildable neighbour, so 1.2.1.4 is not carried.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


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
              "family; miniLZO is compiled from lzo\\minilzo.c. The CRT is "
              "imported (/MD) and stays attributed to data/MSVC.")


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
        notes="Commit 97a077cc (2026-09-06), version 1.8.2.9, the newest "
              "release whose submodule can be fetched; FOSSIL's 1.2.13 "
              "viewer has no buildable source state (see the recipe "
              "docstring and the README). vncviewer.exe is the component "
              "the evidence points at; winvnc.exe is the server. "
              "Dependencies come from vcpkg per vcpkg.json: zlib, zstd, "
              "libjpeg-turbo, liblzma, libsodium and minizip-ng, statically "
              "linked into the exes, so those libraries' functions are "
              "present here under the UltraVNC family; miniLZO is compiled "
              "from lzo\\minilzo.c. The CRT is imported (/MD) and stays "
              "attributed to data/MSVC.",
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
              "present here under the UltraVNC family. The CRT is imported "
              "(/MD) and stays attributed to data/MSVC.",
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
              "miniLZO and the Info-ZIP sources. The CRT is imported (/MD) "
              "and stays attributed to data/MSVC.",
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
        build=([s for s in _NEW_STEPS if "vncviewer.sln" not in s.command]
               + [BuildStep(_LOCATE.replace("('vncviewer', 'winvnc')",
                                            "('winvnc',)"))]),
        artifacts=_ARTIFACTS[1:],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_NEW_FLAGS,
        notes=_NEW_NOTES % (
            "c757708e (2026-11-02)", "1.8.3.2",
            "winvnc.exe only: vncviewer.exe does not build at this commit "
            "because upstream never committed ViewerBounds.h (which "
            "ClientConnectionCursor.cpp, ClientConnectionUltra2.cpp and "
            "FileTransfer.cpp include); the viewer is in 1.8.3.1. "),
    ),
}
