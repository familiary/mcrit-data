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

Second pass (PR #69, the three versions that first did not build). The
maintainer authorised recipe-applied workarounds for them; none edits an
upstream file, and each image is therefore NOT byte-identical to a build of
unmodified upstream. Every change, with its reason:

  * 1.8.3.2 (c757708e, the head of upstream's default branch; the commit
    message is "1.8.3.2").
    The fetch step failed on `git submodule update`: `fatal: remote error:
    upload-pack: not our ref b493d9bbb599fa4d9a0e5ea4bde957dd812384e7`, the
    3rdparty/noVNC pin of 1.8.3.0 and every later commit, which noVNC does
    not serve. noVNC contributes no code to either executable: the vcxproj
    lists its files as `<None Include>` and winvnc.rc embeds 55 of its .js
    files as `JS` resources for the web viewer. So (a) Source(submodules=False)
    skips the submodule fetch (a new, off-by-default Source option; the
    provenance still records the pin, uninitialised, as `-b493d9bb...`), and
    (b) noVNC commit 7c36fabe599e053c5a81e98e091ac636f6c1e174, the pin of
    1.8.2.9 and a commit noVNC serves, is fetched through extra_sources and
    copied to 3rdparty\\noVNC so the 55 resource files exist (all 55 are in
    that commit; v1.7.0 lacks core/clipboard.js, master has all 55). The
    resource section of winvnc.exe therefore carries the web viewer scripts
    of that older noVNC, not of b493d9bb. Code is unaffected.
  * 1.2.1.5 (9761329e). `zipunzip_src\\zip20\\windll\\visualc\\lib\\zip32.vcxproj`
    failed with 240 errors from winnt.h, `error C2143: syntax error: missing
    ':' before 'constant'`. Cause, found by reading winnt.h of SDK
    10.0.26100: the ARM64 unwind-data struct declares a bit-field
    `DWORD CR : 2;`, and Info-ZIP's zip.h has `#define CR 13` (and `LF 10`),
    which every .c of the project includes before <windows.h> is parsed, so
    the field becomes `DWORD 13 : 2;`. Fix: the generated props file adds
    `<ForcedIncludeFiles>windows.h</ForcedIncludeFiles>` for the project named
    zip32 only, so windows.h is parsed first and its include guard makes the
    later include a no-op. No source line changes; the preprocessed Info-ZIP
    code is the same except that CR/LF are defined after windows.h.
  * 1.2.1.4 (b4034d51). `libjpeg-turbo-win\\jdcoefct.c(23,10): error C1083:
    Cannot open include file: 'jdcoefct.h'`. The tree's decompressor sources
    come from libjpeg-turbo 1.5.1 (jdcoefct.c, jdmaster.c and jdsample.c are
    byte-identical to the 1.5.1 tag; 1.5.0 differs in two of them) though
    jconfig.h says 1.4.2, and the four private headers jdcoefct.h, jdmainct.h,
    jdmaster.h and jdsample.h were never committed (1.2.1.5 adds them,
    byte-identical to the 1.5.0-1.5.3 tags). They are taken from libjpeg-turbo
    commit cb88e5da8003afcdc443b787fdcb77285e5a8a02 (tag 1.5.1) through
    extra_sources, copied to a corpusinc directory beside the tree and put on
    the include path by the generated props file (AdditionalIncludeDirectories),
    not into libjpeg-turbo-win.
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


# --- second pass: 1.2.1.4, 1.2.1.5 and 1.8.3.2 (see the docstring) ---------

# The generated props file of the 1.2.1.x builds. Same switches as _PROPS
# (without /DEPENDENTLOADFLAG, which 1.2.x never had), plus two additions that
# the docstring explains: windows.h force-included for the zip32 project only,
# and an optional extra include directory beside the props file. \x27 is a
# single quote, because the whole script sits inside a cmd double-quoted
# string and python single-quoted literals.
def _props_1_2(include_dir=None):
    include = ""
    if include_dir:
        include = ("'<AdditionalIncludeDirectories>$(MSBuildThisFileDirectory)"
                   + include_dir + r";%(AdditionalIncludeDirectories)"
                   "</AdditionalIncludeDirectories>'")
    return (
        'python -c "'
        "open('msvcprops.props','w').write("
        "'<Project><ItemDefinitionGroup><ClCompile>'"
        "'<RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary>'"
        "'<WholeProgramOptimization>false</WholeProgramOptimization>'"
        "'<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>'"
        + include +
        "'</ClCompile><Link>'"
        "'<GenerateDebugInformation>true</GenerateDebugInformation>'"
        "'<ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile>'"
        "'<LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration>'"
        "'<EnableCOMDATFolding>false</EnableCOMDATFolding>'"
        "'<OptimizeReferences>false</OptimizeReferences>'"
        "'<Profile>false</Profile>'"
        "'<AdditionalOptions>/Brepro /INCREMENTAL:NO</AdditionalOptions>'"
        "'</Link></ItemDefinitionGroup>'"
        r"'<ItemDefinitionGroup Condition=\x22\x27$(MSBuildProjectName)\x27==\x27zip32\x27\x22>'"
        "'<ClCompile><ForcedIncludeFiles>windows.h</ForcedIncludeFiles></ClCompile>'"
        "'</ItemDefinitionGroup></Project>')"
        '"')


# winvnc.sln of the 1.2.1.x trees lists two installer projects both named
# "UltraVnc" (.vdproj), which MSBuild refuses (MSB5004); the solution filter
# does not help because the check runs first. A copy without the .vdproj
# entries is generated beside it and upstream's file is left alone.
_SLN = (
    'python -c "'
    r"import re;"
    r"L=open('winvnc/winvnc.sln',encoding='utf-8-sig').read().splitlines();"
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

_MSBUILD_1_2 = ('msbuild %s /t:%s /p:Configuration=Release '
                '/p:Platform={msbuild_platform} /p:PlatformToolset=v143 '
                '/p:WindowsTargetPlatformVersion=10.0 '
                '/p:WholeProgramOptimization=false /p:LinkIncremental=false '
                '/p:PostBuildEventUseInBuild=false '
                '/p:ForceImportBeforeCppTargets=%%CD%%\\msvcprops.props '
                '/m /v:minimal')

# The four private headers of libjpeg-turbo, from the pinned checkout, into a
# directory beside the tree.
_COPY_JPEG_HEADERS = (
    'python -c "'
    "import shutil,sys,os;"
    "os.makedirs('corpusinc',exist_ok=True);"
    "[shutil.copy(sys.argv[1]+'/'+h,'corpusinc') "
    "for h in ['jdcoefct.h','jdmainct.h','jdmaster.h','jdsample.h']]"
    '" {libjpeg_turbo}')

# noVNC files into 3rdparty\noVNC, where winvnc.rc names them.
_COPY_NOVNC = (
    'python -c "'
    "import shutil,sys;"
    "shutil.copytree(sys.argv[1],'3rdparty/noVNC',dirs_exist_ok=True,"
    "ignore=shutil.ignore_patterns('.git'))"
    '" {novnc}')

_OLD_FLAGS = ("Release configuration of the 1.2.1.x vcxproj files: "
              "/Ox /Ob2 /Oi /Ot per project, platform toolset v143 in "
              "place of v100, Windows SDK 10.0; /MT replaced by /MD, /GL and "
              "/LTCG off; /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF "
              "at link, forced by this recipe over upstream's /OPT:REF; "
              "/PROFILE off; post-build signing disabled; windows.h "
              "force-included (/FI) for the zip32 project only, because "
              "Info-ZIP's #define CR 13 breaks winnt.h's ARM64 bit-field "
              "`DWORD CR : 2`")

_OLD_NOTES = ("Commit %s, FILEVERSION %s: the nearest buildable state to the "
              "1.2.13 viewer FOSSIL used, which has no commit of its own. "
              "vncviewer.exe is the component the evidence points at; "
              "winvnc.exe, the server, is the second target. Both statically "
              "link the in-tree zlib, libjpeg-turbo, miniLZO and the "
              "Info-ZIP sources, so those functions are present here under "
              "the UltraVNC family. The CRT is imported (/MD) and stays "
              "attributed to data/MSVC. %s")

_COMMON_STEPS = [
    BuildStep(_NASM, allow_failure=True),
    BuildStep(_SLN),
    BuildStep(_MSBUILD_1_2 % ("vncviewer\\vncviewer.sln", "vncviewer"),
              allow_failure=True),
    BuildStep(_MSBUILD_1_2 % ("winvnc\\winvnc_build.sln", "winvnc"),
              allow_failure=True),
    BuildStep(_LOCATE),
]

_ARTIFACTS = [
    Artifact(path="corpusout\\vncviewer.exe", component="vncviewer.exe",
             pdb="corpusout\\vncviewer.pdb"),
    Artifact(path="corpusout\\winvnc.exe", component="winvnc.exe",
             pdb="corpusout\\winvnc.pdb"),
]

_JPEG_ONLY = ("NOT byte-identical to a build of unmodified upstream: the "
              "windows.h force-include for zip32 (see the recipe docstring). ")


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
        build=[BuildStep(_props_1_2())] + _COMMON_STEPS,
        artifacts=_ARTIFACTS,
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_OLD_FLAGS,
        notes=_OLD_NOTES % ("9761329e (2017-06-10)", "1.2.1.5", _JPEG_ONLY),
    ),
    "UltraVNC_1.2.1.4_msvc": Recipe(
        family="UltraVNC",
        version="1.2.1.4",
        upstream="https://github.com/ultravnc/UltraVNC",
        license="GPL-2.0-or-later",
        source=Source(git_url="https://github.com/ultravnc/UltraVNC.git",
                      git_ref="b4034d51163fefd9935691a11ec4d3597d5c571f"),
        extra_sources={
            "libjpeg_turbo": Source(
                git_url="https://github.com/libjpeg-turbo/libjpeg-turbo.git",
                git_ref="cb88e5da8003afcdc443b787fdcb77285e5a8a02"),
        },
        build=([BuildStep(_props_1_2("corpusinc")),
                BuildStep(_COPY_JPEG_HEADERS)] + _COMMON_STEPS),
        artifacts=_ARTIFACTS,
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_OLD_FLAGS + "; libjpeg-turbo's four private headers "
                    "(jdcoefct.h, jdmainct.h, jdmaster.h, jdsample.h) on the "
                    "include path from libjpeg-turbo 1.5.1",
        notes=_OLD_NOTES % (
            "b4034d51 (2017)", "1.2.1.4",
            "NOT byte-identical to a build of unmodified upstream: the tree "
            "lacks four libjpeg-turbo private headers, supplied from "
            "libjpeg-turbo commit cb88e5da (tag 1.5.1) as a build-side "
            "include directory, and windows.h is force-included for zip32 "
            "(see the recipe docstring). "),
    ),
    "UltraVNC_1.8.3.2_msvc": Recipe(
        family="UltraVNC",
        version="1.8.3.2",
        upstream="https://github.com/ultravnc/UltraVNC",
        license="GPL-3.0-or-later",
        source=Source(git_url="https://github.com/ultravnc/UltraVNC.git",
                      git_ref="c757708e83b6c8249a1cdc9b9c0427c4e72f1c21",
                      submodules=False),
        extra_sources={
            "novnc": Source(git_url="https://github.com/novnc/noVNC.git",
                            git_ref="7c36fabe599e053c5a81e98e091ac636f6c1e174"),
        },
        build=[
            BuildStep(_PROPS),
            BuildStep(_COPY_NOVNC),
            BuildStep(_VCPKG_INTEGRATE, allow_failure=True),
            BuildStep(_MSBUILD % ("vncviewer\\vncviewer.sln", "vncviewer"),
                      allow_failure=True),
            BuildStep(_MSBUILD % ("winvnc\\winvnc.sln", "winvnc"),
                      allow_failure=True),
            BuildStep(_LOCATE),
        ],
        artifacts=_ARTIFACTS,
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS + "; noVNC submodule not fetched, files for "
                    "winvnc.rc's web-viewer resources taken from noVNC "
                    "7c36fabe",
        notes="Commit c757708e (2026-11-02), version 1.8.3.2, the head of "
              "upstream's default branch. NOT byte-identical to a build of "
              "unmodified upstream: the 3rdparty/noVNC submodule pin "
              "b493d9bb is not served by noVNC, so it is left uninitialised "
              "and noVNC 7c36fabe (the pin of 1.8.2.9) supplies the 55 .js "
              "files winvnc.rc embeds as resources; no code is affected "
              "(see the recipe docstring). Dependencies come from vcpkg per "
              "vcpkg.json, statically linked into the exes, so those "
              "libraries' functions are present here under the UltraVNC "
              "family; miniLZO is compiled from lzo\\minilzo.c. The CRT is "
              "imported (/MD) and stays attributed to data/MSVC.",
    ),
}
