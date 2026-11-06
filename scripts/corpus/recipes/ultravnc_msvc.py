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
until commit b4034d51 ("1214", 2017-05-13), which is 1.2.1.4, then reverts to
1.2.1.2 and goes to 1.2.1.5 (9761329e, 2017-06-10). No commit carries
1.2.1.3. 1.2.1.4 was the first pin tried and does not build: its
libjpeg-turbo-win directory lacks the private headers (jdcoefct.h,
jdmainct.h, jdmaster.h, jdsample.h) that its own .c files include, and the
1.2.1.2 tree lacks them too. 1.2.1.5, the next state, carries them and is
pinned. That is a judgement about the nearest buildable state, not an
evidenced match. The second recipe is 1.8.2.9, the newest release a source
checkout can be taken of: 1.8.3.0 and later cannot be fetched by this
pipeline, because eab6d20a moved the 3rdparty/noVNC submodule to commit
b493d9bb, which noVNC no longer serves, and fetch.py updates submodules. It
is a different build system altogether (vcpkg dependencies) and is what an
analyst meets today.

1.2.1.5 build. The tree is self-contained: vncviewer\\vncviewer.sln and
winvnc\\winvnc.sln build the exe and its dependencies from in-tree projects -
zlib (1.2.5 on the viewer's path, per vncviewer.sln), libjpeg-turbo-win, the Info-ZIP
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
# which MSBuild refuses (MSB5004) - a solution filter did not help, the check
# runs before the filter is applied. A copy of the solution without the
# .vdproj entries (and the lines naming their GUIDs) is generated beside it;
# upstream's file is not edited.
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

# The 1.2.1.5 zip32 project (Info-ZIP) does not compile against the newest
# SDK on the runner (winnt.h 10.0.26100.0, 120 syntax errors, nothing else in
# the tree). The era's own SDK range is preferred when it is installed; this
# writes the choice to sdkver.txt for the msbuild line to read.
_SDK = (
    'python -c "'
    "import os;"
    "d='C:/Program Files (x86)/Windows Kits/10/Include';"
    "v=os.listdir(d);"
    "w=[x for x in ['10.0.19041.0','10.0.22621.0','10.0.20348.0','10.0.17763.0'] if x in v];"
    "c=(w+sorted(v)[::-1])[0];"
    "open('sdkver.txt','w').write(c);"
    "print('sdk',c,'of',sorted(v))"
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

# Same line with the SDK read from sdkver.txt; delayed expansion because the
# variable is set and used in one command.
_MSBUILD_OLD = ('cmd /v:on /c "set /p SDK=<sdkver.txt && msbuild %s /t:%s '
                '/p:Configuration=Release /p:Platform={msbuild_platform} '
                '/p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=!SDK! '
                '/p:WholeProgramOptimization=false /p:LinkIncremental=false '
                '/p:PostBuildEventUseInBuild=false '
                '/p:ForceImportBeforeCppTargets=%%CD%%\\msvcprops.props '
                '/m /v:minimal"')

# vcpkg manifest mode, as upstream's cmake/VCPKG_README.txt describes for
# Windows. VcpkgTriplet is forced to the -md variant, which vcpkg ships:
# libraries static, CRT dynamic. The project's own VcpkgUseStatic would pick
# x64-windows-static, whose overlay triplet in triplets\\ sets
# VCPKG_CRT_LINKAGE static and would put /MT objects into an /MD link.
_VCPKG_INTEGRATE = '"%VCPKG_INSTALLATION_ROOT%\\vcpkg.exe" integrate install'

_OLD_FLAGS = ("Release configuration of the 1.2.1.5 vcxproj files: "
              "/Ox /Ob2 /Oi /Ot per project, platform toolset v143 in "
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
    "UltraVNC_1.2.1.5_msvc": Recipe(
        family="UltraVNC",
        version="1.2.1.5",
        upstream="https://github.com/ultravnc/UltraVNC",
        license="GPL-2.0-or-later",
        source=Source(git_url="https://github.com/ultravnc/UltraVNC.git",
                      git_ref="9761329ece79ab416bd6f17b3d68cbca21c9737c"),
        build=[
            BuildStep(_props()),
            BuildStep(_NASM, allow_failure=True),
            BuildStep(_SDK),
            BuildStep(_SLN),
            BuildStep(_MSBUILD_OLD % ("vncviewer\\vncviewer.sln", "vncviewer"),
                      allow_failure=True),
            BuildStep(_MSBUILD_OLD % ("winvnc\\winvnc_build.sln", "winvnc"),
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
        notes="Commit 9761329e (2017-06-10), FILEVERSION 1.2.1.5: the "
              "nearest buildable state to the 1.2.13 viewer FOSSIL used, "
              "which has no commit of its own. vncviewer.exe is "
              "the component the evidence points at; winvnc.exe, the "
              "server, is the second target. Both statically link the "
              "in-tree zlib, libjpeg-turbo, miniLZO and the "
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
              "1.2.1.5.",
    ),
}
