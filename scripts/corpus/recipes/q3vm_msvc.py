"""q3vm built with MSVC, beside the MinGW builds of the same commits.

This is not a second rendering of code the corpus already has. q3vm's
interpreter selects its dispatch at compile time:

    #ifdef __GNUC__
    #ifndef DEBUG_VM           /* can't use computed gotos in debug mode */
    #define USE_COMPUTED_GOTOS

[read, src/vm/vm.c at both pinned commits]. GCC therefore compiles the opcode
loop as a computed-goto threaded interpreter and MSVC compiles it as a
switch, and that loop is the recognisable part of q3vm. The existing recipe's
own note says the switch-based version "is not covered here"; this covers it.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

What was read rather than assumed, in msvc/q3vm/q3vm.sln and
msvc/q3vm/q3vm/q3vm.vcxproj (byte-identical at v1.3.1 and at the 2026
commit - the whole msvc/ directory is unchanged between them):

  * the solution's platforms are ``x86`` and ``x64`` and they map to the
    project's ``Win32`` and ``x64``, so /p:Platform takes {arch} while the
    output path takes {msbuild_platform}.
  * the project is ``ConfigurationType Application``, i.e. q3vm.exe - the
    same component the MinGW recipe files - and its only sources are
    ``..\\..\\..\\src\\main.c`` and ``..\\..\\..\\src\\vm\\vm.c``, compiled
    with ``CompileAs CompileAsC``. LCC and the bytecode tools that the GNU
    default target also builds are not in this project, so nothing has to be
    excluded the way the MinGW recipe excludes them by naming a target.
  * Release is ``Optimization MaxSpeed`` (/O2), ``IntrinsicFunctions`` (/Oi),
    ``FunctionLevelLinking`` (/Gy), ``SDLCheck`` (/sdl), ``WarningLevel
    Level3``, ``WholeProgramOptimization`` (/GL and /LTCG), and at link
    ``OptimizeReferences`` and ``EnableCOMDATFolding`` (/OPT:REF /OPT:ICF).
  * ``OutDir`` is ``$(SolutionDir)..\\bin\\$(Platform)\\$(Configuration)\\``,
    which is why the solution is built rather than the project: building the
    .vcxproj alone would resolve SolutionDir to the project directory and
    move the output. Building the solution also lets MSBuild set SolutionDir
    itself instead of this recipe passing it, as blackbone.py has to.
  * ``PlatformToolset`` is v140 for Win32 and v141 for x64, and
    ``WindowsTargetPlatformVersion`` is 8.1. Neither exists on the
    windows-2022 runner image, so both are overridden on the command line.
  * ``VISUAL_STUDIO_PATCHES`` is in the project's PreprocessorDefinitions but
    nothing under src/ tests it at either commit, so it changes no code.

Three settings the project leaves unstated are forced through a props file
imported with ForceImportBeforeCppTargets, exactly as blackbone.py does for
/permissive and /Brepro - no upstream file is modified. Upstream's own
optimisation, standard and link settings are left alone.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# RuntimeLibrary: the project sets none, so the artefact would depend on
# MSBuild's default. /MT is what that costs when it goes wrong - the first
# VX-API build linked the CRT in and came back 46% MSVC C runtime by function
# count, duplicating data/MSVC - so it is stated rather than inherited.
#
# DebugInformationFormat and GenerateDebugInformation: the project sets
# neither for Release. MSVC keeps symbols in a PDB rather than in a COFF
# symbol table, so without one SMDA recovers anonymous functions and smdaify
# rejects the build; build.py turns a declared-but-missing PDB into a hard
# failure, which is what makes this worth forcing rather than hoping for.
#
# /Brepro: without it MSVC stamps the PE with the build time, so two runs over
# identical source record different sha256s - which the BlackBone x86 DLL did
# between two green runs. It is appended to the link's AdditionalOptions,
# which MSBuild emits last.
#
# Nothing here touches /OPT:REF or /OPT:ICF. Folding is upstream's own
# Release setting, as it is in BlackBone's project, and the MinGW build of
# this family passes -Wl,--gc-sections, so leaving both alone keeps the pair
# comparable rather than making one side more complete than the other.
_PROPS = (
    'python -c "'
    "open('corpus-msvc.props','w').write("
    "'<Project><ItemDefinitionGroup><ClCompile>'"
    "'<RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary>'"
    "'<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>'"
    "'</ClCompile><Link>'"
    "'<GenerateDebugInformation>true</GenerateDebugInformation>'"
    "'<AdditionalOptions>/Brepro</AdditionalOptions>'"
    "'</Link></ItemDefinitionGroup></Project>')"
    '"')

# WindowsTargetPlatformVersion=10.0 asks MSBuild for the newest Windows 10/11
# SDK installed, which is how a project pinned to the retired 8.1 SDK is
# retargeted without editing it.
_MSBUILD = ('msbuild msvc\\q3vm\\q3vm.sln '
            '/p:Configuration=Release /p:Platform={arch} '
            '/p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0 '
            '/p:ForceImportBeforeCppTargets=%CD%\\corpus-msvc.props '
            '/m /v:minimal')

_FLAGS = ("Release configuration: /O2 /Oi /Gy /sdl /W3 /GL, compiled as C "
          "with _CRT_SECURE_NO_WARNINGS and VISUAL_STUDIO_PATCHES defined; "
          "/LTCG /OPT:REF /OPT:ICF at link (all upstream's own); /MD, /Zi, "
          "/DEBUG and /Brepro added by this recipe, and the toolset "
          "retargeted from v140/v141 to v143")


def _q3vm_msvc(version, git_ref):
    return Recipe(
        family="q3vm",
        version=version,
        upstream="https://github.com/jnz/q3vm",
        license="GPL-2.0 (inherited from the Quake III Arena source release)",
        # The same refs the MinGW recipe pins.
        source=Source(git_url="https://github.com/jnz/q3vm.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_PROPS),
            BuildStep(_MSBUILD),
            # build.py reports a missing artefact by the path it expected and
            # nothing else; this puts what the build actually wrote into the
            # log the workflow prints on failure.
            BuildStep("dir msvc\\bin\\{msbuild_platform}\\Release",
                      allow_failure=True),
        ],
        artifacts=[
            Artifact(path="msvc\\bin\\{msbuild_platform}\\Release\\q3vm.exe",
                     component="q3vm.exe",
                     pdb="msvc\\bin\\{msbuild_platform}\\Release\\q3vm.pdb"),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS,
        notes="Switch-based opcode dispatch, where the MinGW artefact of the "
              "same commit has computed-goto dispatch: vm.c selects on "
              "__GNUC__, so the interpreter loop - the part of q3vm worth "
              "recognising - is structurally different code here rather than "
              "the same code from another compiler. Whole-program "
              "optimization is upstream's own Release setting and inlines "
              "across main.c and vm.c, so the function count is not "
              "comparable with the MinGW one function for function. Built "
              "against the DLL runtime, so the MSVC C runtime is imported "
              "rather than linked in and stays attributed to data/MSVC. No "
              "dependencies.",
    )


RECIPES = {
    # The only released version, and what any tarball grab since 2018 carries.
    "q3vm_1.3.1_msvc": _q3vm_msvc("1.3.1", "v1.3.1"),
    # 31 commits and ~140 changed lines of vm.c/vm.h past v1.3.1, including
    # opcode handling changes. Its msvc/ directory is identical to v1.3.1's,
    # so the same command line serves both and only the interpreter differs.
    "q3vm_2026-03-06_msvc": _q3vm_msvc(
        "2026-03-06", "df042e22febcd2851ff26db570f89d04899ca111"),
}
