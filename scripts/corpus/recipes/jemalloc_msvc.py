"""jemalloc built with MSVC, beside the MinGW builds of the same tags.

PROVISIONAL DOCSTRING - rewritten from the CI logs once a run has answered it.

jemalloc.py explains why this was deferred: ``msvc/ReadMe.txt`` step 5 wants
``sh -c "CC=cl ./autogen.sh"`` before the solution opens, and
``include/jemalloc/`` holds only ``.h.in`` templates until autoconf and
configure have run. The workflow now has autoconf (see "Install autoconf" in
windows-reference-data.yml), kept off PATH and reached through
``%AUTOTOOLS_BASH%``.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Fails with a sentence rather than with cmd.exe's complaint about an empty
# command, for whoever runs this recipe somewhere the workflow step has not.
_CHECK_BASH = (
    'python -c "'
    "import os,sys;"
    "p=os.environ.get('AUTOTOOLS_BASH');"
    "sys.exit(0 if p and os.path.isfile(p) else "
    "'AUTOTOOLS_BASH is not set to an MSYS2 bash; the Install autoconf step "
    "of windows-reference-data.yml sets it')"
    '"')

# One MSYS login shell per step, with the Windows PATH appended
# (MSYS2_PATH_TYPE=inherit) so that cl is found, and CHERE_INVOKING so that it
# stays in the source root instead of going to $HOME. The directory of cl.exe
# goes first inside this process only: the MSYS /usr/bin is ahead of the
# inherited Windows PATH and holds coreutils' link.exe, which cl would
# otherwise run in place of MSVC's linker.
_ENV = {"MSYS2_PATH_TYPE": "inherit", "CHERE_INVOKING": "1", "MSYSTEM": "MSYS"}
_SH = ('"%AUTOTOOLS_BASH%" -lc '
       '"PATH=$(command -v cl | sed \'s,/[^/]*$,,\'):$PATH; ')

# Cygwin's triple, which is what the documented route yields. MSYS2's
# config.guess says x86_64-pc-msys, which configure.ac's
# `*-*-mingw* | *-*-cygwin*` case does not match: it falls through to
# "Unsupported operating system" and abi=elf. Both --build and --host, so that
# autoconf does not decide it is cross compiling and skip the tests that run a
# program. Pointer width does not come from the triple with cl, only from
# LG_SIZEOF_PTR_WIN, so the same string serves the x86 leg.
_TRIPLE = "--build=x86_64-pc-cygwin --host=x86_64-pc-cygwin"


def _autogen(cxx, version, commit):
    # --with-version because configure asks git, and cannot: under MSYS2's
    # bash 5.3 its `test ! "${srcroot}" && cd "${srcroot}"` is an error
    # ("./configure: line 8977: cd: null directory") where it is a no-op
    # elsewhere, so it falls through to "Missing VERSION file, and unable to
    # generate it; creating bogus VERSION" and the DLL would say
    # 0.0.0-0-g000000missing_version_try_git_fetch_tags. This is what
    # `git describe --long --abbrev=40` prints on the tagged commit.
    return BuildStep(
        _SH + 'CC=cl sh ./autogen.sh %s%s --with-version=%s-0-g%s"'
        % ("--disable-cxx " if cxx else "", _TRIPLE, version, commit),
        env=_ENV, allow_failure=True)


# The checks that make an autogen failure readable: the tail of config.log is
# what says why, and the build log the workflow prints holds only its last
# sixty lines.
_TAIL = BuildStep(_SH + 'tail -n 25 config.log"', env=_ENV, allow_failure=True)

_CHECK_HEADERS = (
    'python -c "'
    "import os,sys;"
    "f='include/jemalloc/internal/jemalloc_internal_defs.h';"
    "sys.exit(0 if os.path.isfile(f) else "
    "'autogen.sh produced no ' + f + ' - see the config.log tail above')"
    '"')

# Written from a step, not committed, and not part of upstream's tree beyond
# being dropped next to the solution. See the docstring.
def _props(private_namespace_on_win32):
    # The 5.x Release|x64 project defines JEMALLOC_NO_PRIVATE_NAMESPACE and
    # Release|Win32 does not, so jemalloc_preamble.h includes
    # jemalloc/internal/private_namespace.h on x86 only - a header make
    # generates from the built objects, which this build never runs. Giving
    # Win32 the define its x64 sibling already has is the smallest change.
    # /D rather than PreprocessorDefinitions because that would need
    # %(PreprocessorDefinitions), and cmd.exe reads a % as its own.
    extra = (
        "'<ItemDefinitionGroup Condition=\\x22$(Platform)==Win32\\x22>'"
        "'<ClCompile><AdditionalOptions>/DJEMALLOC_NO_PRIVATE_NAMESPACE'"
        "'</AdditionalOptions></ClCompile></ItemDefinitionGroup>'"
        if private_namespace_on_win32 else "''")
    return (
        'python -c "'
        "open('jemalloc-corpus.props','w').write("
        "'<Project><PropertyGroup><LinkIncremental>false</LinkIncremental>'"
        "'</PropertyGroup><ItemDefinitionGroup><ClCompile>'"
        "'<RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary>'"
        "'<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>'"
        "'<WholeProgramOptimization>false</WholeProgramOptimization>'"
        "'</ClCompile><Link>'"
        "'<GenerateDebugInformation>true</GenerateDebugInformation>'"
        "'<ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile>'"
        "'<EnableCOMDATFolding>false</EnableCOMDATFolding>'"
        "'<OptimizeReferences>false</OptimizeReferences>'"
        "'<LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration>'"
        "'<AdditionalOptions>/Brepro</AdditionalOptions>'"
        "'</Link></ItemDefinitionGroup>'" + extra +
        "'</Project>')"
        '"')


_MSBUILD = ('msbuild msvc\\%s /t:jemalloc /p:Configuration=Release '
            '/p:Platform={arch} /p:PlatformToolset=v143 '
            '/p:WindowsTargetPlatformVersion=10.0 '
            '/p:WholeProgramOptimization=false '
            '/p:ForceImportBeforeCppTargets=%%CD%%\\jemalloc-corpus.props '
            '/m /v:minimal')

# What the compiler and linker were actually given, out of MSBuild's tracker
# logs, so that the flags claimed in build_flags are read off the build.
_TLOGS = (
    'python -c "'
    "import glob;"
    "[print(f+chr(10)+open(f,'rb').read().decode('utf-16','replace')"
    ".encode('ascii','replace').decode()) "
    "for f in sorted(glob.glob('msvc/projects/*/jemalloc/*/*/jemalloc.tlog/"
    "*.command.*.tlog'))]"
    '"')

_OUT = "msvc\\{msbuild_platform}\\Release\\"

_FLAGS = ("/O2 /Oi /Gy /W3 /Zi (upstream Release); /MD, /Brepro, /INCREMENTAL:NO "
          "added; /GL, /LTCG, /OPT:REF and /OPT:ICF turned off; toolset "
          "retargeted to v143")


def _jemalloc_msvc(version, commit, sln, is_5x, notes):
    return Recipe(
        family="jemalloc",
        version=version,
        upstream="https://github.com/jemalloc/jemalloc",
        license="BSD-2-Clause",
        # The same tags the MinGW recipe pins.
        source=Source(git_url="https://github.com/jemalloc/jemalloc.git",
                      git_ref=version),
        build=[
            BuildStep(_CHECK_BASH),
            _autogen(is_5x, version, commit),
            _TAIL,
            BuildStep(_CHECK_HEADERS),
            BuildStep(_props(is_5x)),
            BuildStep(_MSBUILD % sln),
            BuildStep(_TLOGS, allow_failure=True),
            BuildStep("dumpbin /dependents " + _OUT + "jemalloc.dll",
                      allow_failure=True),
            BuildStep("dir " + _OUT, allow_failure=True),
        ],
        artifacts=[Artifact(path=_OUT + "jemalloc.dll",
                            component="jemalloc.dll",
                            pdb=_OUT + "jemalloc.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS,
        notes=notes,
    )


RECIPES = {
    "jemalloc_4.5.0_msvc": _jemalloc_msvc(
        "4.5.0", "04380e79f1e2428bd0ad000bbc6e3d2dfc6b66a5",
        "jemalloc_vc2015.sln", False, "4.x extent generation."),
    "jemalloc_5.2.1_msvc": _jemalloc_msvc(
        "5.2.1", "ea6b3e973b477b8061e0076bb257dbd7f3faa756",
        "jemalloc_vc2017.sln", True, "Pre-HPA 5.x."),
    "jemalloc_5.3.0_msvc": _jemalloc_msvc(
        "5.3.0", "54eaed1d8b56b1aa528be3bdd1877e59c56fa90c",
        "jemalloc_vc2017.sln", True, "What most binaries carry."),
    "jemalloc_5.4.0_msvc": _jemalloc_msvc(
        "5.4.0", "7a34f18502e7b222724097cdcd499b437d189acc",
        "jemalloc_vc2022.sln", True, "Current release."),
}
