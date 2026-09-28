"""RealBlindingEDR (myzxcg) - MSVC, x64 only, five distinct source states.

Reference data for the tool binary itself, so that an analyst who meets a copy
of it - or a copy of its code pasted into something else - can have those
functions named rather than reading them as novel. That is the whole of this
family's purpose here, and it is the same purpose CallObfuscator, VX-API,
BlackBone, SysWhispers, APICallProxy and Hidden already serve in this corpus.

The artefact is ``RealBlindingEDR.exe``, built from the project's own two
files - ``RealBlindingEDR.cpp`` and ``RealBlindingEDR.h``, one translation
unit - and carrying 23 functions of its own at V1.0 and 24 from V1.2.1
onward. The count is small and entirely the project's: there is nothing
vendored in the tree, no submodule and no third-party source file, so unlike
Hidden.sys (a fifth of which is Zydis) every named body above the thunk floor
here belongs to this project.

**The two ``.sys`` files in the repository root are deliberately not
artefacts.** They are third-party signed kernel drivers, carried in the tree
as data rather than built from it; both are PE32+ x86-64 and neither has a
line of source anywhere in the repository. Importing them would file another
vendor's driver code under this project's name, which is the same
misattribution CallObfuscator's recipe refuses when it declines to record the
PE that tool emits. They are also already covered wherever a corpus records
the drivers themselves, which is not this family's job. Only the built
executable is recorded.

x64 only, and measured rather than assumed. The solution offers Win32 as well
and the Win32 configuration may well compile, but every address this program
handles is a 64-bit kernel address in a ``DWORD64``/``INT64``, and the two
drivers it is written around are x86-64 images. A Win32 build would therefore
be a program that cannot do what it is for, and its function bodies would be
shapes no real sample can contain - reference data that can only produce
false confidence. That is the judgement callobfuscator.py makes about a MinGW
build of ``cobf.exe``: one that links and is functionally wrong is worse than
one that fails. If a Win32 artefact is ever wanted it should be argued for on
its own terms, not inherited from the solution file.

MinGW is not attempted either, and here the reason is narrower than usual
rather than a portability claim: nothing in the tree links an import library
by name at link time - ``RtlInitUnicodeString``, ``NtLoadDriver``,
``NtUnloadDriver``, ``RtlAdjustPrivilege`` and ``RtlGetNtVersionNumbers`` all
arrive through ``GetProcAddress``, so the ``#pragma comment(lib,
"ntdll.lib")`` in the header is decorative - which means a cross build is not
obviously blocked and a claim either way would need measuring. It has not
been measured, so no MinGW recipe is written and none is implied.

Five recipes, one per distinct source state, which is what "every version"
means for this project once the duplicates are removed. Measured with
``git diff`` over the two source files:

    V1.0     2023-10-30   961 lines   23 functions
    V1.1     2023-11-01   972 lines   +30/-19 against V1.0
    V1.2     2023-12-14   986 lines   +48/-26 against V1.1
    V1.2.1   2024-01-08  1006 lines   +33/-11 against V1.2, adds
                                      GenerateRandomName -> 24 functions
    V1.5.2   2024-05-24  1006 lines   +2/-2 against V1.2.1

``V1.5`` is **byte-identical to V1.2.1** and ``V1.5.1`` is byte-identical to
``V1.5.2`` - ``git diff`` over the two source files is empty in both cases -
so building them would put two pairs of identical images in the corpus under
different version numbers, which costs a build each and teaches MCRIT that a
match is ambiguous between versions that are in fact the same code. They are
skipped for that reason and the reason is recorded here so the gap in the tag
sequence is not read as an oversight.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Six settings are forced through a props file imported with
# ForceImportBeforeCppTargets, the technique blackbone.py, callobfuscator.py
# and wowgrail.py use, so that no upstream file is modified. This block is
# character-identical to callobfuscator.py's; the three settings that matter
# most here are these.
#
# RuntimeLibrary, and Hidden is why. The x64 configurations ask for /MT,
# which links the CRT statically: HiddenCLI.exe arrived at 952 functions of
# which roughly 130 were the project's, the rest being MSVC's own code
# entering the corpus under the project's name and duplicating data/MSVC.
# /MD took it to 525 with 147 its own. On a 24-function program the same
# mistake would be far worse in proportion: the family would be almost
# entirely Microsoft's code wearing this project's label.
# scripts/corpus/wdk-driver-playbook.md records the lesson; this is the
# first recipe written after it.
#
# WholeProgramOptimization and LinkTimeCodeGeneration off. Release sets /GL
# and /LTCG, and with one translation unit LTCG is free to inline across the
# whole program - the small helpers this project is made of, DellRead,
# DellWrite, IsEDR, AddEDRIntance, are what disappears first. nt_wrapper lost
# essentially its whole library to __forceinline at /O2 and had to be built
# /Od; Obfuscate went from 216 functions to 35 five-byte stubs at -O2.
#
# OptimizeReferences and EnableCOMDATFolding off. Release turns both on.
# Folding merges functions that compiled to identical bodies and cost vxapi
# its StringConcat/StringCopy pair; on a program this size, losing one
# function to folding is losing four percent of the family. /OPT:REF would
# additionally discard any helper that LTCG had finished inlining.
#
# /Brepro drops the link timestamp so two runs give identical sha256s.
# /INCREMENTAL:NO is in there because /DEBUG implies /INCREMENTAL and the
# /OPT:NO* forms do not suppress it - an incrementally linked image reaches
# every function through a table of one-instruction jump thunks that SMDA
# recovers as functions in their own right, which put 4882 thunks into
# libcrypto x86 before it was caught.
_PROPS = (
    'python -c "'
    "open('corpus-msvc.props','w').write("
    "'<Project><ItemDefinitionGroup><ClCompile>'"
    "'<RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary>'"
    "'<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>'"
    "'<WholeProgramOptimization>false</WholeProgramOptimization>'"
    "'</ClCompile><Link>'"
    "'<GenerateDebugInformation>true</GenerateDebugInformation>'"
    "'<OptimizeReferences>false</OptimizeReferences>'"
    "'<EnableCOMDATFolding>false</EnableCOMDATFolding>'"
    "'<LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration>'"
    "'<AdditionalOptions>/Brepro /INCREMENTAL:NO</AdditionalOptions>'"
    "'</Link></ItemDefinitionGroup></Project>')"
    '"')

# Release rather than Debug, for callobfuscator.py's reasons: Debug sets
# MultiThreadedDebug, and /MDd is not one of the flavours baseline.py probes,
# so debug CRT glue would be attributed to this family instead of dropped.
#
# /p:WholeProgramOptimization=false is passed on the command line as well as
# in the props file because the project sets it in a PropertyGroup evaluated
# before Microsoft.Cpp.props, which a forced import is too late to reach.
#
# The project asks for PlatformToolset v143 and WindowsTargetPlatformVersion
# 10.0, both of which the windows-2022 runner image carries, so neither is
# retargeted - unlike callobfuscator.py, which has to move v142 to v143.
# /p:PlatformToolset is stated anyway so a later upstream change to the
# vcxproj cannot silently move the toolchain the corpus records.
#
# The solution's platforms are x86 and x64 and map to the project's Win32 and
# x64, so /p:Platform takes {arch}; the output tree takes
# {msbuild_platform}, matching what MSBuild calls the platform everywhere
# else in the build. Unlike callobfuscator.py's, this command is not a
# %-format expression, so %CD% is spelled once rather than doubled.
#
# OutDir and IntDir are pinned rather than inherited so that the linker PDB
# and the compiler PDB (IntDir\\vc143.pdb by MSBuild's own default) land in
# different directories, which they have to, and so that the artefact path
# does not depend on the Microsoft.Cpp default putting a Win32 build one
# directory shallower than an x64 one.
_MSBUILD = ('msbuild RealBlindingEDR.sln '
            '/p:Configuration=Release /p:Platform={arch} '
            '/p:PlatformToolset=v143 /p:WholeProgramOptimization=false '
            '/p:OutDir=%CD%\\out\\{msbuild_platform}\\ '
            '/p:IntDir=%CD%\\obj\\{msbuild_platform}\\ '
            '/p:ForceImportBeforeCppTargets=%CD%\\corpus-msvc.props '
            '/m /v:minimal')

# Everything up to the semicolon is read out of RealBlindingEDR.vcxproj's
# Release|x64 ItemDefinitionGroup. The absence of an <Optimization> element
# is a fact about the project rather than an omission here: it sets none in
# any of its four configurations, so the compile runs at MSBuild's default
# rather than /O2, which is part of why 24 small functions survive as 24
# functions.
_FLAGS = ("Release|x64: /Oi /Gy /W3, ConformanceMode (/permissive-), "
          "SDLCheck off, Unicode character set, NDEBUG;_CONSOLE, and no "
          "<Optimization> element in any configuration so the compile is not "
          "/O2; upstream's /MT is replaced with /MD, WholeProgramOptimization "
          "(/GL and /LTCG) and OptimizeReferences/EnableCOMDATFolding "
          "(/OPT:REF /OPT:ICF) are turned off, /Zi and a full /DEBUG are "
          "stated, and /Brepro and /INCREMENTAL:NO are added")

_NOTES = (
    "MIT licence, Copyright (c) 2023 myz. The artefact is the tool's own "
    "executable, built from its single translation unit; reference data for "
    "it exists so that these bodies can be named when they are met rather "
    "than read as novel code. Nothing in the tree is vendored - no "
    "submodule, no third-party source file - so every named body above the "
    "import-thunk floor is this project's own, which is unusual in this "
    "corpus and makes the honest count and the reported count much closer "
    "than they are for, say, Hidden.sys. The two .sys files in the "
    "repository root are third-party signed drivers carried in as data with "
    "no source anywhere in the tree, and are deliberately not recorded: "
    "filing another vendor's driver under this family would be exactly the "
    "misattribution that CallObfuscator's recipe avoids by declining to "
    "record the PE that tool writes. x64 only, because every kernel address "
    "this program handles is 64-bit and the drivers it is written around are "
    "x86-64 images, so a Win32 build would be a program that cannot "
    "function and whose bodies no real sample can contain. Built against the "
    "DLL runtime rather than upstream's /MT, so the MSVC C runtime is "
    "imported and stays attributed to data/MSVC instead of entering the "
    "corpus under this name - on a 24-function program the static CRT would "
    "have made the family almost entirely Microsoft's code. Whole-program "
    "optimization, /OPT:REF and /OPT:ICF are turned off so that the small "
    "helpers are not inlined away or folded together, which also means this "
    "artefact is not byte-comparable with a binary built the way upstream "
    "configures it.")


def _recipe(version, git_ref, functions, extra=""):
    return Recipe(
        family="RealBlindingEDR",
        version=version,
        upstream="https://github.com/myzxcg/RealBlindingEDR",
        license="MIT",
        source=Source(git_url="https://github.com/myzxcg/RealBlindingEDR.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_PROPS, cwd="RealBlindingEDR"),
            BuildStep(_MSBUILD, cwd="RealBlindingEDR"),
            # build.py reports a missing artefact by the path it expected and
            # nothing else; this puts what the build actually wrote into the
            # log the workflow prints on failure.
            BuildStep("dir out\\{msbuild_platform}", cwd="RealBlindingEDR",
                      allow_failure=True),
        ],
        artifacts=[
            Artifact(
                path="RealBlindingEDR\\out\\{msbuild_platform}\\RealBlindingEDR.exe",
                component="RealBlindingEDR.exe",
                pdb="RealBlindingEDR\\out\\{msbuild_platform}\\RealBlindingEDR.pdb"),
        ],
        toolchains=["msvc_x64"],
        build_flags=_FLAGS,
        notes="%s %s functions of its own in this state.%s" % (_NOTES, functions, extra),
    )


RECIPES = {
    "RealBlindingEDR_1.0": _recipe("1.0", "V1.0", 23),
    "RealBlindingEDR_1.1": _recipe("1.1", "V1.1", 23),
    "RealBlindingEDR_1.2": _recipe("1.2", "V1.2", 23),
    # V1.5 is byte-identical to V1.2.1 over both source files, so it is not
    # built; this artefact covers both tags.
    "RealBlindingEDR_1.2.1": _recipe(
        "1.2.1", "V1.2.1", 24,
        extra=" Adds GenerateRandomName, taking the count from 23 to 24. Tag "
              "V1.5 is byte-identical to V1.2.1 over both source files and is "
              "not built separately; this artefact covers both."),
    # V1.5.1 is byte-identical to V1.5.2 over both source files, so only the
    # later tag is built.
    "RealBlindingEDR_1.5.2": _recipe(
        "1.5.2", "V1.5.2", 24,
        extra=" Tag V1.5.1 is byte-identical to V1.5.2 over both source files "
              "and is not built separately; this artefact covers both."),
}
