"""libsodium built with MSVC, beside the MinGW builds of the same sources.

data/libsodium carries only MinGW artefacts, and for a ransomware-triage
corpus that is the wrong compiler: a libsodium hit is one of the more
decisive things an analyst can find, and Windows ransomware is MSVC-built.
Upstream ships a full Visual Studio build for exactly this case, so this is
not a hand-rolled command line - it is upstream's own project file with the
three settings the corpus needs forced on top of it.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

What was read rather than assumed, in the pinned trees of both versions:

  * builds/msvc/vs2022/libsodium/libsodium.vcxproj (1.0.20) and
    builds/msvc/vs2019/libsodium/libsodium.vcxproj (1.0.18) derive
    ConfigurationType from the configuration name -
    "$(Configuration.IndexOf('DLL')) != -1" selects DynamicLibrary - so
    ReleaseDLL is the configuration that produces a DLL rather than the
    static lib SMDA cannot read. Both files declare ReleaseDLL for Win32 and
    x64; 1.0.20 adds ARM64, which is not built here.
  * builds/msvc/properties/ReleaseDLL.props sets RuntimeLibrary
    MultiThreadedDLL, i.e. /MD, at both versions. Nothing has to be done
    about the static-CRT trap here; it is already upstream's choice.
  * builds/msvc/properties/Output.props (byte-identical at both versions)
    defines OutDir as
    $(ProjectDir)..\\..\\..\\..\\bin\\$(PlatformName)\\$(DebugOrRelease)\\$(PlatformToolset)\\$(DefaultLinkage)\\
    Release.props sets DebugOrRelease=Release, DLL.props sets
    DefaultLinkage=dynamic, and the project sets neither TargetName nor a
    module definition file, so TargetName falls back to the project name.
    That resolves to bin\\<Platform>\\Release\\v143\\dynamic\\libsodium.dll -
    which is why PlatformToolset is pinned on the command line even for
    1.0.20, where the project already asks for v143: the artefact path
    contains the toolset name, so it must not be left to the runner's
    default.
  * exports come from SODIUM_DLL_EXPORT, which libsodium.props defines when
    ConfigurationType is DynamicLibrary. No .def file, nothing to stage.
  * the pre-build event copies builds/msvc/version.h into
    src/libsodium/include/sodium/. That file is present in both pinned
    trees, so neither the release tarball nor the git checkout needs
    configure to have been run first. It is upstream's own step, not a
    patch.
  * the "'$(Processor)' == 'x86'" group in Release.props, which would set
    EnableEnhancedInstructionSet to SSE2, is dead: nothing in builds/msvc
    ever defines a Processor property. The 32-bit build therefore takes
    v143's own default /arch, and the build_flags string below says so
    rather than repeating upstream's intent.

What has to be forced, and why each one is a build setting rather than a
patch to upstream source:

  * GenerateDebugInformation. Release.props carries
    "<!--<GenerateDebugInformation>true</GenerateDebugInformation>-->" -
    commented out - at both versions, so the link PDB depends on an MSBuild
    default rather than on anything upstream states. build.py fails a build
    whose declared PDB is missing, and without symbols smdaify would reject
    the artefact anyway, so it is stated explicitly here together with
    ProgramDatabaseFile.
  * DebugInformationFormat. 1.0.20's Release.props sets ProgramDatabase;
    1.0.18's has the same line commented out. Forcing it makes the two
    versions comparable and gives the linker something to build a PDB from.
  * /Brepro, so the PE carries no build timestamp and two runs over
    identical source record the same sha256 - the BlackBone x86 DLL did
    exactly that between two green runs.
  * EnableCOMDATFolding and OptimizeReferences off. Release.props turns both
    on. That is what upstream's shipped DLL looks like, but for reference
    data /OPT:ICF merges two routines that happened to compile to identical
    bodies into one entry - it cost VX-API its StringConcat/StringCopy pair -
    and /OPT:REF drops routines nothing references. Both are pure loss here,
    and turning them off yields a superset of the same function bodies. The
    MinGW sibling has no --gc-sections and folds nothing, so this also keeps
    the two comparable.

All five arrive through a props file imported with
ForceImportBeforeCppTargets, which MSBuild imports after the project's own
ItemDefinitionGroups so these values win - the mechanism blackbone.py already
uses for /permissive and /Brepro. Upstream source is untouched.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CONFIG = "ReleaseDLL"

# Written from a step rather than committed, so nothing outside the fetched
# tree is part of the build. No % anywhere in the text: cmd.exe would try to
# expand it, and MSBuild's %(Item) syntax is not needed - nothing else in
# this project sets Link AdditionalOptions, so there is no inherited value to
# preserve.
_PROPS = (
    'python -c "'
    "open('msvcprops.props','w').write("
    "'<Project><ItemDefinitionGroup><ClCompile>'"
    "'<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>'"
    "'</ClCompile><Link>'"
    "'<GenerateDebugInformation>true</GenerateDebugInformation>'"
    "'<ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile>'"
    "'<EnableCOMDATFolding>false</EnableCOMDATFolding>'"
    "'<OptimizeReferences>false</OptimizeReferences>'"
    "'<AdditionalOptions>/Brepro</AdditionalOptions>'"
    "'</Link></ItemDefinitionGroup></Project>')"
    '"')


def _libsodium_msvc(version, vs_dir, source, license="ISC"):
    project = "builds\\msvc\\%s\\libsodium\\libsodium.vcxproj" % vs_dir
    # OutDir interpolates PlatformName and PlatformToolset, so both are named
    # here and repeated in the artefact path below.
    out_dir = "bin\\{msbuild_platform}\\Release\\v143\\dynamic\\"
    return Recipe(
        family="libsodium",
        version=version,
        upstream="https://github.com/jedisct1/libsodium",
        license=license,
        source=source,
        build=[
            BuildStep(_PROPS),
            BuildStep('msbuild %s /p:Configuration=%s '
                      '/p:Platform={msbuild_platform} /p:PlatformToolset=v143 '
                      '/p:ForceImportBeforeCppTargets=%%CD%%\\msvcprops.props '
                      '/m /v:minimal' % (project, _CONFIG)),
            # A missing artefact is reported by build.py with the path it
            # expected and nothing else; this costs a second and puts the
            # names the build actually wrote into the log the workflow
            # prints, so a wrong guess about an output path is one cycle to
            # diagnose rather than two.
            BuildStep("dir " + out_dir, allow_failure=True),
        ],
        artifacts=[Artifact(path=out_dir + "libsodium.dll",
                            component="libsodium.dll",
                            pdb=out_dir + "libsodium.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        # Read out of Common.props / Release.props / DLL.props / ReleaseDLL
        # .props rather than assumed: Optimization MaxSpeed is /O2,
        # InlineFunctionExpansion OnlyExplicitInline is /Ob1 - not /Ob2, which
        # is what CMake's MSVC Release would give and what the other MSVC
        # recipes in this wave use - IntrinsicFunctions is /Oi,
        # FunctionLevelLinking is /Gy, and Release.props appends /Oy- by hand.
        build_flags="ReleaseDLL configuration: /O2 /Ob1 /Oi /Oy- /Gy /MD /Zi "
                    "/W3, NDEBUG and UNICODE defined, SODIUM_DLL_EXPORT; x86 "
                    "takes v143's default /arch because upstream's SSE2 group "
                    "is conditioned on a Processor property nothing defines; "
                    "/DEBUG /Brepro /OPT:NOREF /OPT:NOICF at link, the last "
                    "three forced by this recipe over upstream's /OPT:REF "
                    "/OPT:ICF and commented-out GenerateDebugInformation",
        notes="Built from upstream's own Visual Studio project at the same "
              "source this family's MinGW artefacts come from, so the two "
              "differ in the compiler and in upstream's MSVC-side flags "
              "rather than in the library. No dependencies: libsodium links "
              "only advapi32, the CRT and Win32, and is built against the DLL "
              "runtime so the MSVC C runtime is imported rather than linked "
              "in and stays attributed to data/MSVC. The AMD64 assembly "
              "paths are not built - upstream gates them on an Option-amd64asm "
              "property that defaults to unset in the project file - so the "
              "x64 artefact is the C implementation, as the MinGW one is not "
              "necessarily; read a missing cross-compiler match on the "
              "curve25519 inner loops with that in mind.",
    )


RECIPES = {
    # The vs2022 solution upstream added for this release: PlatformToolset is
    # already v143 in the project file, which makes this the cheapest and
    # lowest-risk of the two.
    "libsodium_1.0.20_msvc": _libsodium_msvc(
        "1.0.20", "vs2022",
        # The same signed release tarball the MinGW recipe pins, and the same
        # digest, so the two artefacts come from identical bytes.
        Source(url="https://download.libsodium.org/libsodium/releases/"
                   "libsodium-1.0.20.tar.gz",
               sha256="ebb65ef6ca439333c2bb41a0c1990587288da07f6c7fd07cb3a18cc1"
                      "8d30ce19")),
    # Enormous installed base, and the version most often found statically
    # linked - which is the case an MSVC reference answers and a MinGW one
    # does not. The git tag is what the MinGW recipe pins; the MSVC path
    # needs none of its autogen.sh dance, because the Visual Studio project
    # does not go through configure. vs2019 is the newest solution this tag
    # ships and it asks for v142, which the windows-2022 image does not
    # carry, so the toolset override is load-bearing here rather than
    # defensive.
    "libsodium_1.0.18_msvc": _libsodium_msvc(
        "1.0.18", "vs2019",
        Source(git_url="https://github.com/jedisct1/libsodium.git",
               git_ref="1.0.18")),
}
