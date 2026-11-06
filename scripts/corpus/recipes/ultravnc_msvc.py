"""UltraVNC (mcrit-data issue #27) - MSVC only.

The evidence is FOSSIL (ACM TOPS 2018): 86 UltraVNC functions matched in Zeus
and 125 in Citadel. Two things in the issue decide what is built.

  * FOSSIL's reference binary was the *viewer*, vncviewer 1.2.13, not the
    server. The viewer is therefore the first target, at or near that
    version, and the server (winvnc) is built from the same commit as a
    second component, recorded as such.
  * The attribution to UltraVNC rather than TightVNC or RealVNC rests on
    FOSSIL alone; the families share RFB ancestry. TightVNC is built as its
    own family (issue #70) so the two can be compared.

Versions. "1.2.13" cannot be resolved to a commit: the upstream history
(git-svn import, 1862 commits) carries FILEVERSION 1.2.1.2 from 2016-09-19
until commit b4034d51 ("1214", 2017-05-13), which is 1.2.1.4. No commit
carries 1.2.1.3, so the read is "1.2.1.3, which has no source state of its
own" and the nearest labelled state is pinned: 1.2.1.4. That is a judgement,
not an evidenced match. The 1.8.2.9 release (1.8.3.0 and later cannot be
fetched by this pipeline: eab6d20a moved the 3rdparty/noVNC submodule to
commit b493d9bb, which noVNC no longer serves, and fetch.py updates
submodules) (a different build system
altogether) is built as well, because it is what an analyst meets today; its
shape is in the second recipe below.

1.2.1.4 build. The tree is self-contained: vncviewer\\vncviewer.sln and
winvnc\\winvnc.sln build the exe and its dependencies from in-tree projects -
zlib 1.2.11, libjpeg-turbo 1.4.2 (libjpeg-turbo-win), the Info-ZIP
zip/unzip sources, miniLZO (compiled straight from lzo\\minilzo.c) and
omnithread/rdr. Nothing comes from vcpkg and nothing is MFC or ATL
(UseOfMfc is false in every project; the .rc files include afxres.h, so the
MFC headers must exist, which the windows-2022 image provides). The vcxproj
files ask for toolset v100 and a static CRT; both are overridden on the
command line (v143, /MD). Each solution is built with /t:<project>, so the
installer .vdproj entries in winvnc.sln are never built.

Vendored libraries are not split out. They are statically linked into the exe
by upstream's own project files, so their functions are in the image under the
UltraVNC family exactly as a sample in the wild carries them; the overlap with
data/libzlib, data/lzo and data/liblzma is measured and listed in the
README, not removed. That is how BlackBone's AsmJit and rewolf-wow64ext are
handled in this corpus.

Forced from the command line, because the projects ask for the opposite:
/MT -> /MD, /GL and /LTCG off (the projects' Link AdditionalOptions carry a
literal /LTCG, which the props file replaces), LinkIncremental off,
/PROFILE off (it implies /OPT:REF), the post-build signtool step disabled
(PostBuildEventUseInBuild=false; it signs with a certificate this build does
not have), and at link /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


def _props(extra_link=""):
    return (
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
        "'<AdditionalOptions>/Brepro /INCREMENTAL:NO" + extra_link + "</AdditionalOptions>'"
        "'</Link></ItemDefinitionGroup></Project>')"
        '"')


# winvnc.sln lists two installer projects both named "UltraVnc" (.vdproj),
# which MSBuild refuses (MSB5004). A solution filter naming only the .vcxproj
# entries of the solution avoids loading them; it is generated, not edited in.
_SLNF = (
    'python -c "'
    r"import re,json;"
    r"s=open('winvnc/winvnc.sln').read();"
    r"p=re.findall(r'[\w\\.\-]+\.vcxproj',s);"
    r"json.dump(dict(solution=dict(path='winvnc\\winvnc.sln',projects=p)),"
    r"open('winvnc/winvnc.slnf','w'))"
    '"')

# libjpeg-turbo-win's SIMD sources are assembled with nasm (the project adds
# C:\Program Files\nasm to ExecutablePath); the runner has none (exit 9009).
_NASM = 'choco install nasm -y --no-progress'

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
            '/p:WindowsTargetPlatformVersion=10.0 /p:WholeProgramOptimization=false /p:LinkIncremental=false '
            '/p:PostBuildEventUseInBuild=false %s'
            '/p:ForceImportBeforeCppTargets=%%CD%%\\msvcprops.props '
            '/m /v:minimal')

# vcpkg manifest mode, as upstream's cmake/VCPKG_README.txt describes for
# Windows. VcpkgTriplet is forced to the -md variant, which vcpkg ships:
# libraries static, CRT dynamic. The project's own VcpkgUseStatic would pick
# x64-windows-static, whose overlay triplet in triplets\\ sets
# VCPKG_CRT_LINKAGE static and would put /MT objects into an /MD link.
_VCPKG_INTEGRATE = '"%VCPKG_INSTALLATION_ROOT%\\vcpkg.exe" integrate install'

_OLD_FLAGS = ("Release configuration of the 1.2.1.4 vcxproj files: "
              "/Ox /Ob2 /Oi /Ot /GS- per project, platform toolset v143 in "
              "place of v100; /MT replaced by /MD, /GL and /LTCG off; /DEBUG "
              "/Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link, "
              "forced by this recipe over upstream's /OPT:REF; /PROFILE off; "
              "post-build signing disabled")

_NEW_FLAGS = ("Release configuration of the 1.8.2.9 vcxproj files, platform "
              "toolset v143 in place of v142; dependencies from vcpkg "
              "(manifest mode) as the static-library, dynamic-CRT triplet; "
              "/MT replaced by /MD, /GL and /LTCG off; /DEBUG /Brepro "
              "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF /DEPENDENTLOADFLAG:0x800 "
              "at link; post-build signing disabled")


RECIPES = {
    "UltraVNC_1.2.1.4_msvc": Recipe(
        family="UltraVNC",
        version="1.2.1.4",
        upstream="https://github.com/ultravnc/UltraVNC",
        license="GPL-2.0-or-later",
        source=Source(git_url="https://github.com/ultravnc/UltraVNC.git",
                      git_ref="b4034d51163fefd9935691a11ec4d3597d5c571f"),
        build=[
            BuildStep(_props()),
            BuildStep(_NASM, allow_failure=True),
            BuildStep(_SLNF),
            BuildStep(_MSBUILD % ("vncviewer\\vncviewer.sln", "vncviewer", ""),
                      allow_failure=True),
            BuildStep(_MSBUILD % ("winvnc\\winvnc.slnf", "winvnc", ""),
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
        build_flags=_OLD_FLAGS,
        notes="Commit b4034d51 (git-svn r1079, 2017-05-13), FILEVERSION "
              "1.2.1.4: the nearest labelled state to the 1.2.13 viewer "
              "FOSSIL used, which has no commit of its own. vncviewer.exe is "
              "the component the evidence points at; winvnc.exe, the "
              "server, is the second target. Both statically link the "
              "in-tree zlib 1.2.11, libjpeg-turbo 1.4.2, miniLZO and the "
              "Info-ZIP sources, so those functions are present here under "
              "the UltraVNC family. The CRT is imported (/MD) and stays "
              "attributed to data/MSVC.",
    ),
    "UltraVNC_1.8.2.9_msvc": Recipe(
        family="UltraVNC",
        version="1.8.2.9",
        upstream="https://github.com/ultravnc/UltraVNC",
        license="GPL-3.0-or-later",
        source=Source(git_url="https://github.com/ultravnc/UltraVNC.git",
                      git_ref="97a077cc5b069c6b2ff87f3131d7d10b9a9d7122"),
        build=[
            BuildStep(_props(" /DEPENDENTLOADFLAG:0x800")),
            BuildStep(_VCPKG_INTEGRATE, allow_failure=True),
            BuildStep(_MSBUILD % (
                "vncviewer\\vncviewer.sln", "vncviewer",
                "/p:VcpkgTriplet={asm_arch}-windows-static-md "),
                allow_failure=True),
            BuildStep(_MSBUILD % (
                "winvnc\\winvnc.sln", "winvnc",
                "/p:VcpkgTriplet={asm_arch}-windows-static-md "),
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
        build_flags=_NEW_FLAGS,
        notes="Commit 97a077cc (2026-09-06), version 1.8.2.9. "
              "Dependencies come from vcpkg per vcpkg.json: zlib, zstd, "
              "libjpeg-turbo, liblzma, libsodium and minizip-ng, statically "
              "linked into the exes, so those libraries' functions are "
              "present here under the UltraVNC family; miniLZO is compiled "
              "from lzo\\minilzo.c. vncviewer.exe and winvnc.exe as in "
              "1.2.1.4.",
    ),
}
