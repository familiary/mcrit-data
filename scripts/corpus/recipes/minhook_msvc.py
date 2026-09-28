"""MinHook built with MSVC, beside the MinGW builds of the same two tags.

The MinGW recipe (minhook.py) records what the project's own function count
is and why two releases are pinned; this one builds the same two tags with
cl and link so the corpus carries both code generators. For MinHook that
matters more than the usual "most Windows software is MSVC-built" argument,
because MinHook is vendored as *source*: the five files are dropped into a
consumer's tree and compiled by whatever that consumer uses, which for a
Windows target is overwhelmingly MSVC. A MinGW-only reference would match
the common case weakly.

One part of the tree changes for MSVC and not for GCC, which is worth
recording because it is the opposite of what the diff suggests. Between
v1.3.3 and v1.3.4 both HDE translation units gain ``#include <string.h>``,
lose a cast, gain two ``break`` statements and gain a pair of parentheses.
For GCC all four are semantic no-ops - both ``break``s terminate the final
case of their switch, and ``&`` already binds tighter than ``&&`` - and the
measured artefacts confirm it: ``hde64_disasm`` is the same 665 instructions
with the same PicHash at both tags. But the removed line was inside
``#ifndef _MSC_VER`` / ``#else``, and what the MSVC half lost is
``__stosb((LPBYTE)hs, 0, sizeof(hde32s))`` in favour of ``memset``. So the
length disassembler - one of the two parts a vendored copy freezes hardest -
genuinely differs between these two tags when cl compiles it and does not
when GCC does.

Upstream's own solution is used rather than CMake. CMake is the easier route
and would give /MD and /INCREMENTAL:NO for free, but it only exists from
v1.3.4: v1.3.3 has no CMakeLists.txt at all. Building the two tags through
different build systems would leave them differing in the build system as
well as in the source, which is the one thing a two-release pin is supposed
to isolate, so both go through MSBuild on the solution upstream ships.

The solution has two projects and needs both. MinHook.vcxproj declares no
ClCompile items whatsoever - it is a link-only project whose sources are
``$(SolutionDir)lib\\$(Configuration)\\libMinHook.x{86,64}.lib`` in
AdditionalDependencies - and libMinHook.vcxproj is what actually compiles
the five translation units. The solution records the dependency, so building
the .sln builds the static library first and then wraps it in the DLL. A DLL
is what this pipeline needs in any case: SMDA has no COFF/ar loader, so the
libMinHook.x64.lib half of the same build is not reference data it can read.

Because the DLL is linked from that archive rather than from objects, what
lands in the image is decided by what the linker pulls: MinHook.def exports
the twelve MH_* entry points, hook.obj resolves them, and hook.obj's
references reach buffer.obj, trampoline.obj and one HDE object in turn, so
all four objects are pulled whole. With /OPT:NOREF none of their COMDATs is
then discarded.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Six settings forced through a props file imported with
# ForceImportBeforeCppTargets, the technique callobfuscator.py, blackbone.py,
# q3vm_msvc.py and wowgrail.py use, so that no upstream file is modified.
#
# RuntimeLibrary: both projects ask for MultiThreaded, i.e. /MT, at Release.
# A static CRT put 1947 of VX-API's 4219 functions into that artefact as
# Microsoft's code under the library's name, and data/MSVC is this corpus's
# reference for exactly that code. /MD leaves it in ucrtbase and
# vcruntime140. It costs little here in any case - the only CRT functions
# MinHook references anywhere in its five files are memcpy (9 call sites) and
# memset (4), and /Oi turns both into intrinsics - but the rule is the rule
# and the difference is not measurable in the other direction.
#
# DebugInformationFormat is the one that has to be fixed rather than tidied.
# Every configuration of both projects sets it to None and sets
# GenerateDebugInformation false, so the build emits no PDB at all - and MSVC
# keeps symbols in a PDB rather than in a COFF symbol table the way MinGW
# does. Without one SMDA can name only the twelve exported MH_* functions and
# would leave the other fourteen bodies, the whole trampoline and buffer
# layer, anonymous; smdaify's symbol-coverage gate would refuse the build,
# and correctly. Overridden to ProgramDatabase with a real /DEBUG.
#
# OptimizeReferences and EnableCOMDATFolding: upstream's Release turns both
# on, i.e. /OPT:REF /OPT:ICF. Folding merges functions that compiled to
# identical bodies - it cost vxapi its StringConcat/StringCopy pair - and
# this project is a plausible victim: EnableHook/EnableAllHooksLL and the
# MH_QueueEnableHook/MH_QueueDisableHook pair differ only in a BOOL argument
# passed through, and MH_EnableHook/MH_DisableHook are one-line wrappers that
# differ only in that constant. /OPT:REF would additionally discard the
# COMDATs nothing outside the DLL references, which is most of what this
# artefact is for. Both off.
#
# LinkTimeCodeGeneration is stated as well as WholeProgramOptimization being
# cleared on the command line, because the two reach the link by different
# routes and only the pair of them together guarantees no /LTCG.
#
# /Brepro drops the link timestamp so two runs give identical sha256s.
# /INCREMENTAL:NO because /DEBUG implies /INCREMENTAL and the /OPT:NO* forms
# above do not suppress it - only /OPT:REF, /OPT:ICF and /OPT:ORDER are
# documented to. Release already sets LinkIncremental false, but this recipe
# overrides enough of the link that inheriting it would be a thing to have to
# remember, and without it the image reaches every function through a table
# of one-instruction jump thunks that
# smdaify.assert_not_incrementally_linked refuses.
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


# /p:Platform takes {msbuild_platform} rather than {arch}: these solutions
# spell their platforms Win32 and x64, unlike CallObfuscator's which spells
# them x86 and x64.
#
# /p:WholeProgramOptimization=false is a command-line global property rather
# than a props entry because both projects set WholeProgramOptimization in a
# Configuration PropertyGroup evaluated before Microsoft.Cpp.props, which a
# forced import is too late to reach. It is load-bearing: /LTCG inlines
# across translation units, and the boundaries between hook.c, buffer.c,
# trampoline.c and the HDE unit are the thing this artefact exists to record.
#
# PlatformToolset is retargeted for both tags, and for v1.3.3 it is not
# optional: VC15 asks for v141_xp, the XP-targeting toolset, which the
# windows-2022 image does not carry at all - it ships VS2022 and v143. VC17
# already asks for v143 and is restated only so the two tags are built by one
# command line.
#
# WindowsTargetPlatformVersion likewise. VC17 sets 10.0 itself; the VC15
# projects set nothing, and a v14x toolset with no target platform version
# defaults to the Windows 8.1 SDK, which the runner image does not have.
#
# OutDir and IntDir are deliberately NOT overridden, which is the opposite of
# what callobfuscator.py and wowgrail.py do. MinHook.vcxproj finds the static
# library through the literal path $(SolutionDir)lib\\$(Configuration)\\, so
# moving the libMinHook output would break the DLL link. Upstream's own paths
# are left in place and the artefact is read from them: OutDir is
# $(SolutionDir)bin\\$(Configuration)\\ and TargetName is $(ProjectName).x86
# or .x64, which is why the artefact path below carries {arch}. The compiler
# PDB stays in IntDir as vc143.pdb by MSBuild's default, so it is a different
# file from the linker PDB, which is what those two have to be.
def _msbuild(vc_dir):
    return ('msbuild build\\%s\\MinHook%s.sln '
            '/p:Configuration=Release /p:Platform={msbuild_platform} '
            '/p:PlatformToolset=v143 '
            '/p:WindowsTargetPlatformVersion=10.0 '
            '/p:WholeProgramOptimization=false '
            '/p:ForceImportBeforeCppTargets=%%CD%%\\corpus-msvc.props '
            '/m /v:minimal' % (vc_dir, vc_dir))


# Read out of the two projects' Release ItemDefinitionGroups. Optimization is
# MinSpace, i.e. /O1, and is left alone: it is what MinHook's own release
# configuration has always been, and this recipe's job is to record the shape
# upstream ships rather than to pick a nicer one. /Ob2 comes with it and does
# inline the small statics, which is why the emitted body count is below the
# source count - the MinGW recipe's docstring lists which twelve go.
_FLAGS = ("Release configuration: /O1 (MinSpace) /Ob2 /Oi /Gy /W3, Unicode "
          "character set, WIN32;NDEBUG;_WINDOWS;_USRDLL;MINHOOK_EXPORTS for "
          "the DLL and WIN32;NDEBUG;_LIB;STRICT for the static library, "
          "linked /NOENTRY with dll_resources/MinHook.def and "
          "/MERGE:.CRT=.text; upstream's /MT is replaced with /MD, "
          "DebugInformationFormat None with /Zi and a full /DEBUG, "
          "WholeProgramOptimization (/GL and /LTCG) and "
          "OptimizeReferences/EnableCOMDATFolding (/OPT:REF /OPT:ICF) are "
          "turned off, /Brepro and /INCREMENTAL:NO are added, and the "
          "toolset is retargeted to v143 with the 10.0 SDK")


def _minhook_msvc(version, git_ref, vc_dir):
    return Recipe(
        family="MinHook",
        version=version,
        upstream="https://github.com/TsudaKageyu/minhook",
        license="BSD-2-Clause",
        source=Source(git_url="https://github.com/TsudaKageyu/minhook.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_PROPS),
            BuildStep(_msbuild(vc_dir)),
            # build.py reports a missing artefact by the path it expected and
            # nothing else; this puts what the build actually wrote into the
            # log the workflow prints on failure.
            BuildStep("dir build\\%s\\bin\\Release" % vc_dir,
                      allow_failure=True),
        ],
        artifacts=[
            Artifact(path="build\\%s\\bin\\Release\\MinHook.{arch}.dll" % vc_dir,
                     component="MinHook.dll",
                     pdb="build\\%s\\bin\\Release\\MinHook.{arch}.pdb" % vc_dir),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS,
        notes="The MSVC build of the same two tags the MinGW recipe pins, "
              "from upstream's own solution rather than from CMake because "
              "v1.3.3 ships no CMakeLists.txt and building the two tags "
              "through different build systems would confound the "
              "comparison the two-release pin exists to make. MinHook is "
              "vendored as source and compiled by its consumer, which on "
              "Windows is overwhelmingly MSVC, so this is the build most "
              "sightings will match. The solution's MinHook.vcxproj "
              "compiles nothing - it is a link-only project that wraps "
              "libMinHook.x86.lib/libMinHook.x64.lib, which the sibling "
              "libMinHook.vcxproj builds from the five translation units - "
              "so the .sln is built rather than either project, and the DLL "
              "is the artefact because SMDA cannot read the static archive "
              "the same build also produces. One upstream difference is "
              "MSVC-only and worth knowing: the HDE change between these two "
              "tags sits under #ifndef _MSC_VER/#else, so cl loses "
              "__stosb in favour of memset at v1.3.4 while GCC's "
              "hde64_disasm is byte-identical across the two tags. Built "
              "against the DLL runtime, so the MSVC C runtime is imported "
              "rather than linked in and stays attributed to data/MSVC; "
              "MinHook references only memcpy and memset from it in any "
              "case. Nothing in the tree is prebuilt at either tag, so no "
              "shipped binary is filed under this family.",
    )


RECIPES = {
    # VC15 is the newest project set v1.3.3 ships, and it asks for v141_xp;
    # the recipe retargets it. Tag v1.3.3 is commit
    # 9fbd087432700d73fc571118d6a9697a36443d88, 2017-01-07.
    "MinHook_1.3.3_msvc": _minhook_msvc("1.3.3", "v1.3.3", "VC15"),
    # VC17 is v143 already, which is what the runner has. Tag v1.3.4 is
    # commit c3fcafdc10146beb5919319d0683e44e3c30d537, 2025-03-28.
    "MinHook_1.3.4_msvc": _minhook_msvc("1.3.4", "v1.3.4", "VC17"),
}
