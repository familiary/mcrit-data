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

  * with TightVNC: 88 on x86 and 107 on x64, of 5325 and 5065 UltraVNC
    hashes. That is the RFB code both inherit, plus the zlib and libjpeg
    they both link.
  * with data/libzlib: 5 (x86) and 79 (x64); with data/liblzma 287 and 257;
    with data/libsodium 140 and 113, all from the vcpkg libraries. The zlib
    functions are the ones the deep check fails on: 59 PicHashes share one
    symbol name across TightVNC, UltraVNC and libzlib (`deflate`, `inflate`,
    `_tr_flush_block` and so on). No mechanism in this tooling excludes a
    vendored library from its host family, so they are reported rather than
    hidden; `validate --deep` on a corpus holding these families fails on
    exactly those 59 hashes.
  * with the lzo 2.10 reference data (MinGW and MSVC, the lzo branches): 0
    on x86 and 8 on x64 against the MSVC build, from miniLZO.

Glue that survives the baseline, by name: 6 to 55 kept functions per
artefact carry a name that the baseline removed from another of these
artefacts (their hash differs, so the name-and-PicHash rule keeps them).
They are MSVC STL and CRT inline instantiations - `std::vector<...>`,
`__std_remove_4`, `fprintf`/`sprintf`/`_snwprintf_s`, `ATL::AtlThrowImpl` and
`ATL::CAtlException` in winvnc x86 - not project code. The x86 artefacts
also carry unnamed exception funclets (503 and 853 unnamed of 6268 and 7598).

Forced from the command line, because the projects ask for the opposite:
/MT -> /MD, /GL and /LTCG off (the projects' Link AdditionalOptions carry a
literal /LTCG, which the props file replaces; /DEPENDENTLOADFLAG:0x800, the
other option those lines carried, is put back), LinkIncremental off, /PROFILE
off (it implies /OPT:REF), the post-build signtool step disabled
(PostBuildEventUseInBuild=false; it signs with a certificate this build does
not have), toolset v143 in place of v142, Windows SDK 10.0, and at link /DEBUG
/Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF.
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
}
