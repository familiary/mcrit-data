"""Phantom DLL hollowing built with MSVC, beside the MinGW build of the same
commit.

``phantomdllhollower.py`` records the family and says, at the end, that an
MSVC artefact is worth adding later. This is that artefact, and for this
project it is the more important of the two: upstream is a Visual Studio 2019
solution with two ``Application`` projects, ``PlatformToolset`` v142,
``Release|Win32`` and ``Release|x64``, ``Optimization`` MaxSpeed,
``RuntimeLibrary`` MultiThreaded and ``WholeProgramOptimization`` true. There
is no makefile, no CMakeLists and nothing that cross-builds, so a real copy of
this PoC is an MSVC build and the committed MinGW artefacts are the unusual
shape. ``cronos_msvc.py`` states the same rationale for recording both
compilers of one commit; ``minhook_msvc.py`` is the other precedent.

The two projects are byte-identical apart from the GUID, the RootNamespace and
the one ``ClCompile`` item, so everything below applies to both.

Open risks, written before the first CI round and corrected after it
-------------------------------------------------------------------

1. ``PlatformToolset`` v142 is VS2019 and windows-2022 carries VS2022 and v143
   only, so the toolset is retargeted. This one was foreseen and was right;
   ``minhook_msvc.py`` retargets for the same reason.
2. ``WholeProgramOptimization`` sits in a ``PropertyGroup Label="Configuration"``
   evaluated *before* ``Microsoft.Cpp.props``, which a forced import cannot
   reach, so it is also cleared as a command-line global. Foreseen, and needed:
   the tracker log below shows no ``/GL`` and no ``/LTCG``.
3. ``SDLCheck`` is true in both Release configurations, i.e. ``/sdl``, which
   promotes a handful of warnings to errors. Nothing in these two translation
   units tripped it under v143. Left on, because it is upstream's own setting.
4. ``DebugInformationFormat`` is absent from every configuration of both
   projects, so it takes MSBuild's own default. It is forced to
   ``ProgramDatabase`` regardless rather than trusted: MSVC keeps symbols in a
   PDB rather than in a COFF symbol table, and without one SMDA can name only
   exported functions - these two EXEs export nothing at all, so the
   symbol-coverage gate would refuse both builds, correctly.

What is overridden, and why each one
------------------------------------

Six settings through ``corpus-msvc.props``, force-imported with
``ForceImportBeforeCppTargets``; no file in the fetched tree is touched, which
is the line this corpus does not cross.

``RuntimeLibrary`` MultiThreaded -> MultiThreadedDLL. This is the override
that matters most here and it is the one place this recipe deliberately
departs from upstream. These are five-function and seven-function programs: a
statically linked CRT would make the family almost entirely Microsoft's code
filed under Forrest Orr's name, which is the VX-API lesson - 1947 of 4219
functions - that ``callobfuscator.py`` records and
``scripts/corpus/wdk-driver-playbook.md`` restates. ``data/MSVC`` is this
corpus's reference for exactly that code. With ``/MD`` the measured images
carry two UCRT bodies and nothing else of Microsoft's.

``OptimizeReferences`` and ``EnableCOMDATFolding`` both true -> false, i.e.
``/OPT:NOREF /OPT:NOICF``. Folding is a real risk in the hollower:
``GetContainerSectHdr`` and ``GetPAFromRVA`` are 20-30 instruction PE helpers
and ICF cost VX-API its StringConcat/StringCopy pair. ``/OPT:REF`` would
additionally discard anything the entry point does not reach.

``WholeProgramOptimization`` -> false in the props file *and*
``/p:WholeProgramOptimization=false`` on the command line, plus
``LinkTimeCodeGeneration`` Default, because the three reach the build by
different routes and only all of them together guarantee no ``/GL`` and no
``/LTCG``. ``phantomdllhollower.py`` argues that ``/GL`` has nothing to do in
either project because each is a single translation unit; that argument is
about cross-TU inlining and does not cover what LTCG does *within* one unit,
so it is not a reason to leave it on.

``DebugInformationFormat`` -> ProgramDatabase with ``GenerateDebugInformation``
true, ``ProgramDataBaseFileName`` under ``$(IntDir)`` and
``ProgramDatabaseFile`` at ``$(OutDir)$(TargetName).pdb``. The compiler PDB and
the linker PDB have to be separate files - pointing both at one path has
link.exe write the file it is reading type information from - and the compiler
PDB is named ``$(ProjectName).compiler.pdb`` rather than a fixed stem because
one props file serves two projects, the way ``hidden.py`` does it.

``/Brepro`` so two runs over the same source record the same sha256, and
``/INCREMENTAL:NO`` because ``/DEBUG`` implies ``/INCREMENTAL`` and the
``/OPT:NO*`` forms do not suppress it; an incrementally linked image reaches
every function through a one-instruction jump thunk and
``smdaify.assert_not_incrementally_linked`` refuses it.

The two ``.vcxproj`` files are built individually rather than the ``.sln``, for
two reasons. The solution spells its platforms ``x86`` and ``x64`` while the
projects spell them ``Win32`` and ``x64``, which is survivable, but ``OutDir``
and ``IntDir`` are pinned here - the ``Microsoft.Cpp`` defaults put a Win32
build one directory shallower than an x64 one - and a single pinned ``IntDir``
shared by two projects would have them writing over each other's tracker logs
and compiler PDB. So each project gets its own ``IntDir`` and both land in one
``OutDir``.

TODO-MEASURE: everything from the tracker logs through the leakage
paragraph is rewritten from the first green CI run. Do not ship this file
with this marker in it.

``printf`` leaks for the MSVC reason rather than the MinGW one, and is worth
one sentence because the MinGW recipe spends four paragraphs on its version.
There it is a filter gap - the PicHash is in the baseline under the name
``printf`` and g++ emits the body as ``_Z6printfPKcz``, so the name-keyed
lookup misses. Here the name is plainly ``printf``: the UCRT headers define it
as an inline wrapper over ``__stdio_common_vfprintf``, so it is compiled into
every translation unit that calls it rather than imported, and the baseline's
MSVC probes do not carry that body. ``cronos_msvc.py`` records the same case.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CONFIG = "Release"

# Six settings forced through a props file imported with
# ForceImportBeforeCppTargets, the technique callobfuscator.py, minhook_msvc.py,
# hidden.py and wowgrail.py use, so that no upstream file is modified. The
# docstring gives the reason for each; the two mechanical notes are here.
#
# ProgramDataBaseFileName is $(IntDir)$(ProjectName).compiler.pdb rather than a
# fixed stem because one props file serves both projects, which hidden.py hit
# first. Each msbuild step below also gets its own IntDir, so the two cannot
# collide even by name.
#
# ProgramDatabaseFile is stated rather than inherited so that the linker PDB
# lands at a path the Artifact entries below can name: $(OutDir) is pinned on
# the command line and $(TargetName) is the project name, which is what these
# projects' TargetName defaults to.
_PROPS = (
    'python -c "'
    "c='<RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary>"
    "<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>"
    "<ProgramDataBaseFileName>$(IntDir)$(ProjectName).compiler.pdb"
    "</ProgramDataBaseFileName>"
    "<WholeProgramOptimization>false</WholeProgramOptimization>';"
    "l='<GenerateDebugInformation>true</GenerateDebugInformation>"
    "<ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile>"
    "<OptimizeReferences>false</OptimizeReferences>"
    "<EnableCOMDATFolding>false</EnableCOMDATFolding>"
    "<LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration>"
    "<AdditionalOptions>/Brepro /INCREMENTAL:NO</AdditionalOptions>';"
    "open('corpus-msvc.props','w').write("
    "'<Project><ItemDefinitionGroup><ClCompile>'+c+'</ClCompile><Link>'"
    "+l+'</Link></ItemDefinitionGroup></Project>')"
    '"')


# One msbuild call per .vcxproj rather than one over the .sln; see the
# docstring. /p:Platform takes {msbuild_platform} because a project spells its
# platforms Win32 and x64 - it is the solution that spells them x86 and x64,
# which is the trap callobfuscator.py and q3vm_msvc.py hit from the other side.
#
# /p:PlatformToolset=v143: both projects ask for v142, which is VS2019 and
# which the windows-2022 image does not carry. WindowsTargetPlatformVersion is
# already 10.0 in both Globals groups and is left alone.
#
# /p:WholeProgramOptimization=false is a command-line global as well as a props
# entry because both projects set it in a PropertyGroup Label="Configuration"
# evaluated before Microsoft.Cpp.props, which a forced import is too late to
# reach.
#
# OutDir is shared so both artefacts land in one directory; IntDir is split per
# project so their tracker logs and compiler PDBs cannot collide.
def _msbuild(project, obj):
    return ('msbuild %s '
            '/p:Configuration=%s /p:Platform={msbuild_platform} '
            '/p:PlatformToolset=v143 '
            '/p:WholeProgramOptimization=false '
            '/p:OutDir=%%CD%%\\out\\{msbuild_platform}\\ '
            '/p:IntDir=%%CD%%\\obj\\{msbuild_platform}\\%s\\ '
            '/p:ForceImportBeforeCppTargets=%%CD%%\\corpus-msvc.props '
            '/m /v:minimal' % (project, _CONFIG, obj))


_HOLLOWER = _msbuild(
    "PhantomDllHollower\\PhantomDllHollower.vcxproj", "hollower")
_MEMSWEEP = _msbuild("MemSweep\\MemSweep.vcxproj", "memsweep")

# What the compiler and linker were actually given, out of MSBuild's tracker
# logs, so that build_flags is read off the build rather than off the project
# file. The same step jemalloc_msvc.py uses; the tlogs are UTF-16.
_TLOGS = (
    'python -c "'
    "import glob;"
    "[print(f+chr(10)+open(f,'rb').read().decode('utf-16','replace')"
    ".encode('ascii','replace').decode()) "
    "for f in sorted(glob.glob('obj/**/*.command.*.tlog',recursive=True))]"
    '"')

_OUT = "out\\{msbuild_platform}\\"


# Everything before the first semicolon is read out of the tracker logs of a
# green run, not out of the .vcxproj: the two disagree, because MSBuild adds
# /D _MBCS from CharacterSet, /EHsc, /Gd /TP /FC and the default library list
# that neither project mentions.
_FLAGS = ("Release configuration as upstream declares it, read back from "
          "MSBuild's tracker logs: /O2 /Oi /Gy /GS /sdl /permissive- /EHsc "
          "/W3 /Zi /D _MBCS /TP, linked /DEBUG /SUBSYSTEM:CONSOLE "
          "/DYNAMICBASE /NXCOMPAT against MSBuild's default library list "
          "(kernel32, user32, gdi32 and the rest of the Windows set - neither "
          "project names a library of its own); upstream's /MT is replaced "
          "with /MD so the MSVC runtime is imported rather than linked in, "
          "WholeProgramOptimization (/GL and /LTCG) is turned off in the "
          "props file and as a command-line global because the projects set "
          "it before Microsoft.Cpp.props, OptimizeReferences and "
          "EnableCOMDATFolding (/OPT:REF /OPT:ICF) are turned off, "
          "DebugInformationFormat is forced to ProgramDatabase with a full "
          "/DEBUG because the projects set none and MSVC keeps symbols in a "
          "PDB, /Brepro and /INCREMENTAL:NO are added, and the toolset is "
          "retargeted from v142 to v143. No upstream file is modified")


_NOTES = (
    "The MSVC build of the same commit phantomdllhollower.py pins, which that "
    "recipe flagged as worth adding: upstream is a Visual Studio 2019 "
    "solution - two Application projects, PlatformToolset v142, Release for "
    "Win32 and x64, Optimization MaxSpeed, RuntimeLibrary MultiThreaded, "
    "WholeProgramOptimization true - with no makefile and nothing that "
    "cross-builds, so a real copy of this PoC is an MSVC build and the MinGW "
    "artefacts are the unusual shape. The two now differ in the compiler and "
    "nothing else. What the family is and what in it is matchable are "
    "unchanged and are stated in the MinGW recipe: HollowDLL is the technique "
    "and the only function that is, the other three in the hollower are "
    "generic PE-parsing furniture, and MemSweep.exe is the repository's "
    "defensive scanner, recorded to name the binary rather than any "
    "technique. Built against the DLL runtime, so the MSVC C runtime is "
    "imported rather than linked in and stays attributed to data/MSVC - which "
    "matters more here than usual, because these are five- and seven-function "
    "programs and /MT would have made the family almost entirely Microsoft's "
    "code under Forrest Orr's name, the effect that put 1947 of VX-API's 4219 "
    "functions into that artefact. /GL and /LTCG are turned off in the props "
    "file and again as a command-line global, because both projects set "
    "WholeProgramOptimization in a PropertyGroup evaluated before "
    "Microsoft.Cpp.props; /OPT:REF and /OPT:ICF, which upstream's Release "
    "turns on, are turned off because ICF would fold GetContainerSectHdr and "
    "GetPAFromRVA if they compiled alike and /OPT:REF would discard whatever "
    "the entry point does not reach. DebugInformationFormat is forced to "
    "ProgramDatabase: the projects set none, these EXEs export nothing, and "
    "without a PDB SMDA would name no function at all. The two .vcxproj files "
    "are built individually rather than the .sln, so each gets its own IntDir "
    "and their tracker logs and compiler PDBs cannot collide. Function "
    "partitions, which add up exactly: the hollower is 5 own functions of 25 "
    "on x64 and 5 of 24 on x86 (16 one-instruction import thunks each, printf "
    "and __scrt_common_main_seh, and two then one unnamed stubs); MemSweep is "
    "7 own of 43 on x64 and 7 of 42 on x86, the extra two over the MinGW "
    "build being MemoryPermissionRecord's in-class constructor and destructor, "
    "which /O2 /Ob2 emits out of line and -O2 emits nowhere, plus 12 "
    "Microsoft STL template instantiations compiled in from the headers where "
    "the MinGW artefacts carry 7 of libstdc++'s. The MinGW side's 13-vs-5 "
    "MemSweep asymmetry does not exist here and was never inlining: the extra "
    "eight entries on MinGW x86 are three .cold clones and five unnamed "
    "fragments that -freorder-blocks-and-partition split out of the "
    "throw/terminate paths, and MSVC emits no .cold clone and no unnamed piece "
    "of any own function, so both architectures report the same seven. Every "
    "own body differs from its MinGW counterpart by PicHash - 5 of 5 in the "
    "hollower on both architectures and 5 of 5 comparable in MemSweep, with "
    "zero shared hashes anywhere - which is what recording a second compiler "
    "is for. printf and __scrt_common_main_seh survive the glue filter in all "
    "four artefacts: printf is a UCRT header inline wrapper over "
    "__stdio_common_vfprintf, compiled into every translation unit that calls "
    "it, the MSVC analogue of a MinGW case the pipeline README documents, and "
    "__scrt_common_main_seh at 99 instructions on x64 and 91 on x86 is the "
    "corpus's one standing leakage finding, already recorded in bzip2, Hidden, "
    "Lua, MemoryModule, RealBlindingEDR and Cronos - these are four more "
    "artefacts against the same unresolved hash rather than a new finding. "
    "Nothing in the tree is prebuilt and nothing is vendored, so the fifth "
    "partition bucket is zero in all four."
)


RECIPES = {
    # The same commit phantomdllhollower.py pins, so the two artefacts differ
    # in the compiler and nothing else. No tags in the repository, so pinned by
    # full commit and versioned by its date.
    "PhantomDllHollower_2020-07-17_msvc": Recipe(
        family="PhantomDllHollower",
        version="2020-07-17",
        upstream="https://github.com/forrest-orr/phantom-dll-hollower-poc",
        license="GPL-3.0-only (Copyright (c) 2019 Forrest Orr)",
        source=Source(
            git_url="https://github.com/forrest-orr/phantom-dll-hollower-poc.git",
            git_ref="57c6aa2056163e6ab31cd5f151a284c52d7722a1"),
        build=[
            BuildStep(_PROPS),
            BuildStep(_HOLLOWER),
            BuildStep(_MEMSWEEP),
            BuildStep(_TLOGS, allow_failure=True),
            BuildStep("dumpbin /dependents " + _OUT + "PhantomDllHollower.exe",
                      allow_failure=True),
            BuildStep("dumpbin /dependents " + _OUT + "MemSweep.exe",
                      allow_failure=True),
            # build.py reports a missing artefact by the path it expected and
            # nothing else; this puts what the build actually wrote into the
            # log the workflow prints on failure.
            BuildStep("dir " + _OUT, allow_failure=True),
        ],
        artifacts=[
            # is_library stays true, as it is for every executable in this
            # corpus - see the note in obfuscator4g3nt47.py: validate refuses
            # a reference sample without it, and it means "this is reference
            # material" rather than "this is a .dll".
            Artifact(path=_OUT + "PhantomDllHollower.exe",
                     component="PhantomDllHollower.exe",
                     pdb=_OUT + "PhantomDllHollower.pdb"),
            Artifact(path=_OUT + "MemSweep.exe", component="MemSweep.exe",
                     pdb=_OUT + "MemSweep.pdb"),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS,
        notes=_NOTES,
    ),
}
