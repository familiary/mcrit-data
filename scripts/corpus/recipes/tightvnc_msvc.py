"""TightVNC 2.x (mcrit-data issue #70) - MSVC only.

The issue is the weakest evidence in the queue and says so: an AhnLab ASEC
article reports that Kimsuky customises TightVNC's tvnserver, and names no
version, no function, no string and no upstream-against-sample comparison.
It is built for the one thing it can settle, which is #27: UltraVNC and
TightVNC share RFB ancestry, FOSSIL's UltraVNC attribution for Zeus and
Citadel rests on that paper alone, and a TightVNC reference beside the
UltraVNC one is what lets a later comparison separate the two.

No version is evidenced, so the pin is a judgement and recorded as one. Two
releases of the 2.8 line are built, both source zips served by tightvnc.com
(sha256 below, computed from the downloaded bytes; upstream publishes none):
2.8.85, dated 2024-06-17 in the archive, and 2.8.90, the newest source zip the
download page lists. The reported Kimsuky sample is not tied to either.

Components. tvnserver.exe is the binary the issue names (service
installation and connection direction are the reported customisations).
tvnviewer.exe is built beside it because the viewer shares most of the
protocol code and the issue's own scenario has the attacker's tvnviewer on the
other end. Both come from the 2.8.x Visual Studio projects.

Build. The tree ships tightvnc.sln (VS2008 .vcproj) and tightvnc2017.sln
(.vcxproj, toolset v141_xp). The vcxproj files are built directly, one
msbuild per application, which builds their ProjectReferences; SolutionDir is
passed because OutDir is defined relative to it. PlatformToolset is
overridden to v143, since v141_xp is not on the runner. All vendored
dependencies are in-tree projects built as static libraries and linked into
the exes (zlib, libjpeg); there is no external dependency and no DirectX SDK
reference in the vcxproj files. No source patch.

Flags forced from the command line, because the projects ask for the
opposite: /MT -> /MD (the CRT is imported rather than linked, so it stays
attributed to data/MSVC), /GL and /LTCG off (WholeProgramOptimization), and
at link /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF. They arrive
through a props file imported with ForceImportBeforeCppTargets plus
/p:WholeProgramOptimization=false, which also reaches the project-reference
libraries. No MFC and no ATL: UseOfMfc is not set anywhere in the 2.8 tree, so
there is no static/dynamic MFC choice to record.
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
    "'<AdditionalOptions>/Brepro /INCREMENTAL:NO</AdditionalOptions>'"
    "'</Link></ItemDefinitionGroup></Project>')"
    '"')

# Copies each built exe and its PDB to corpusout\ so the artefact paths do not
# depend on where OutDir resolves for Win32 against x64. Newest match wins.
_NAMES = ("tvnserver", "tvnviewer")
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

_MSBUILD = ('msbuild %s\\%s.vcxproj /p:Configuration=Release '
            '/p:Platform={msbuild_platform} /p:PlatformToolset=v143 '
            '/p:SolutionDir=%%CD%%\\ /p:WholeProgramOptimization=false '
            '/p:LinkIncremental=false '
            '/p:ForceImportBeforeCppTargets=%%CD%%\\msvcprops.props '
            '/m /v:minimal')

_FLAGS = ("Release configuration of the 2.8 vcxproj files: /O2 (MaxSpeed) "
          "/Oi /Ot /Gy, platform toolset v143 in place of v141_xp; /MT "
          "replaced by /MD, WholeProgramOptimization off (no /GL, no "
          "/LTCG); /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at "
          "link, forced by this recipe over upstream's /OPT:REF /OPT:ICF")


def _tightvnc(version, sha256):
    return Recipe(
        family="TightVNC",
        version=version,
        upstream="https://www.tightvnc.com/",
        license="GPL-2.0-or-later",
        source=Source(
            url="https://www.tightvnc.com/download/%s/tightvnc-%s-src-gpl.zip"
                % (version, version),
            sha256=sha256),
        build=[
            BuildStep(_PROPS),
            BuildStep(_MSBUILD % ("tvnserver", "tvnserver"), allow_failure=True),
            BuildStep(_MSBUILD % ("tvnviewer", "tvnviewer"), allow_failure=True),
            BuildStep(_LOCATE),
        ],
        artifacts=[
            Artifact(path="corpusout\\tvnserver.exe", component="tvnserver.exe",
                     pdb="corpusout\\tvnserver.pdb"),
            Artifact(path="corpusout\\tvnviewer.exe", component="tvnviewer.exe",
                     pdb="corpusout\\tvnviewer.pdb"),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS,
        notes="No version is evidenced for the Kimsuky sample (issue #70); "
              "this is one of two 2.8 releases pinned by judgement. The "
              "exes statically link the in-tree zlib and libjpeg projects, "
              "so functions from those libraries are present here under "
              "the TightVNC family; the CRT is imported (/MD) and stays "
              "attributed to data/MSVC. tvnserver.exe is the service-capable "
              "server the issue names; tvnviewer.exe shares its RFB code.",
    )


RECIPES = {
    "TightVNC_2.8.85_msvc": _tightvnc(
        "2.8.85",
        "13d22e5843f1727fc7ee927a097820b4e68fd3e5f439a8c07fa0d57c6e24308c"),
    "TightVNC_2.8.90_msvc": _tightvnc(
        "2.8.90",
        "f3f76393a5865e1f1919c78c3eb43b9c937cf738927c2bfc920ecbd3913b061c"),
}
