"""Phantom DLL hollowing built with MSVC, beside the MinGW build of the same
commit.

``phantomdllhollower.py`` records the family and ends by saying an MSVC
artefact is worth adding later. This is that artefact, and for this project it
is the more representative of the two: upstream is a Visual Studio 2019
solution with two ``Application`` projects, ``PlatformToolset`` v142,
``Release|Win32`` and ``Release|x64``, ``Optimization`` MaxSpeed,
``RuntimeLibrary`` MultiThreaded and ``WholeProgramOptimization`` true. There
is no makefile, no CMakeLists and nothing in the tree that cross-builds, so a
real copy of this PoC is an MSVC build and the committed MinGW artefacts are
the unusual shape. ``cronos_msvc.py`` states the same rationale for recording
both compilers of one commit; ``minhook_msvc.py`` is the other precedent.

The two ``.vcxproj`` files are identical apart from the GUID, the
``RootNamespace`` and the one ``ClCompile`` item, so everything below applies
to both.

What is overridden, and why each one
------------------------------------

Six settings through ``corpus-msvc.props``, force-imported with
``ForceImportBeforeCppTargets``. No file in the fetched tree is touched, which
is the line this corpus does not cross.

``RuntimeLibrary`` MultiThreaded -> MultiThreadedDLL is the one that matters
most here. These are five- and seven-function programs; a statically linked
CRT would make the family almost entirely Microsoft's code filed under Forrest
Orr's name, which is the VX-API lesson - 1947 of 4219 functions -
``callobfuscator.py`` records and ``scripts/corpus/wdk-driver-playbook.md``
restates, and ``data/MSVC`` is this corpus's reference for exactly that code.
Measured, ``/MD`` leaves four MSVC CRT bodies in each of the four artefacts and
nothing else of Microsoft's C runtime; ``dumpbin /dependents`` lists
VCRUNTIME140.dll and six ``api-ms-win-crt-*`` sets for the hollower, plus
MSVCP140.dll, ``api-ms-win-crt-convert`` and - on x64 only -
VCRUNTIME140_1.dll for MemSweep.

``OptimizeReferences`` and ``EnableCOMDATFolding`` both true -> false, i.e.
``/OPT:NOREF /OPT:NOICF``. Folding was a real risk in the hollower:
``GetContainerSectHdr`` and ``GetPAFromRVA`` are 29- and 38-instruction PE
helpers and ICF cost VX-API its StringConcat/StringCopy pair. ``/OPT:REF``
would additionally discard anything the entry point does not reach.

``WholeProgramOptimization`` -> false in the props file *and*
``/p:WholeProgramOptimization=false`` on the command line, plus
``LinkTimeCodeGeneration`` Default, because the three reach the build by
different routes and only all of them together guarantee no ``/GL`` and no
``/LTCG``. The command-line global is the load-bearing one: both projects set
``WholeProgramOptimization`` in a ``PropertyGroup Label="Configuration"``
evaluated before ``Microsoft.Cpp.props``, which a forced import cannot reach.
``phantomdllhollower.py`` argues that ``/GL`` has nothing to do in either
project because each is a single translation unit; that argument is about
cross-TU inlining and says nothing about what LTCG does within one unit, so it
is not a reason to leave it on.

``DebugInformationFormat`` -> ProgramDatabase, with
``GenerateDebugInformation`` true, ``ProgramDataBaseFileName`` under
``$(IntDir)`` and ``ProgramDatabaseFile`` at ``$(OutDir)$(TargetName).pdb``.
No configuration of either project sets ``DebugInformationFormat`` at all, so
it would otherwise take MSBuild's default; it is forced rather than trusted
because MSVC keeps symbols in a PDB rather than in a COFF symbol table and
these two EXEs export nothing, so without one SMDA could name no function
whatsoever and the symbol-coverage gate would refuse both builds, correctly.
``minhook_msvc.py`` had to override an explicit ``None`` for the same reason.
The compiler PDB and the linker PDB have to be separate files - pointing both
at one path has link.exe write the file it is reading type information from -
and the compiler PDB is named ``$(ProjectName).compiler.pdb`` rather than a
fixed stem because one props file serves two projects, as in ``hidden.py``.

``/Brepro`` so two runs over the same source record the same sha256, and
``/INCREMENTAL:NO`` because ``/DEBUG`` implies ``/INCREMENTAL`` and the
``/OPT:NO*`` forms do not suppress it; an incrementally linked image reaches
every function through a one-instruction jump thunk and
``smdaify.assert_not_incrementally_linked`` refuses it.

``PlatformToolset`` is retargeted v142 -> v143. v142 is VS2019 and the
windows-2022 image carries VS2022 and v143 only.
``WindowsTargetPlatformVersion`` is already ``10.0`` in both ``Globals``
groups, so unlike in ``minhook_msvc.py`` it is left alone.

The two ``.vcxproj`` files are built individually rather than the ``.sln``.
The solution spells its platforms ``x86`` and ``x64`` where the projects spell
them ``Win32`` and ``x64``, which is survivable either way, but ``OutDir`` and
``IntDir`` are pinned here - the ``Microsoft.Cpp`` defaults put a Win32 build
one directory shallower than an x64 one - and one pinned ``IntDir`` shared by
two projects would have them writing over each other's tracker logs and
compiler PDB. So each project gets its own ``IntDir`` and both land in one
``OutDir``.

What the compiler and linker were actually given
------------------------------------------------

Read out of MSBuild's tracker logs rather than inferred from the project
files, the way ``jemalloc_msvc.py`` established its flag list, and it is worth
doing because the two disagree: MSBuild adds ``/D _MBCS`` from
``CharacterSet``, ``/EHsc``, ``/Gd /TP /FC`` and a twelve-library default link
line that neither project mentions. Both ``CL.command.1.tlog`` files on x64:

    /c /Zi /nologo /W3 /WX- /diagnostics:column /sdl /O2 /Oi /D _MBCS
    /Gm- /EHsc /MD /GS /Gy /fp:precise /Zc:wchar_t /Zc:forScope /Zc:inline
    /permissive- /Fo... /Fd... /external:W3 /Gd /TP /FC

x86 is the same plus ``/Oy-`` and ``/analyze-``. ``link.command.1.tlog``:

    /OUT:... /NOLOGO KERNEL32.LIB USER32.LIB GDI32.LIB WINSPOOL.LIB
    COMDLG32.LIB ADVAPI32.LIB SHELL32.LIB OLE32.LIB OLEAUT32.LIB UUID.LIB
    ODBC32.LIB ODBCCP32.LIB /MANIFEST
    /MANIFESTUAC:"level='asInvoker' uiAccess='false'" /manifest:embed
    /DEBUG /PDB:... /SUBSYSTEM:CONSOLE /OPT:NOREF /OPT:NOICF /LTCGOUT:...
    /TLBID:1 /DYNAMICBASE /NXCOMPAT /IMPLIB:... /MACHINE:X64 /Brepro
    /INCREMENTAL:NO

x86 adds ``/SAFESEH`` and says ``/MACHINE:X86``.

Three things in those lines. ``/O2`` is present and ``/GL`` is not, so the
clearing works and the optimisation level is upstream's own. ``/MD`` is there
where the project asks for ``/MT``. And ``/LTCGOUT`` appears although
``/LTCG`` does not - it names an ``.iobj`` path that is never written;
``jemalloc_msvc.py`` records the same and it is not evidence of LTCG.

Two warnings, neither fatal and neither introduced here: C4244 at
``PhantomDllHollower.cpp(268,21)``, a ``uint64_t`` to ``uint32_t``
initialisation, on both architectures, and C4477 at ``MemSweep.cpp(53,5)``,
``printf("%d")`` against a ``SIZE_T``, on x64 only. ``/sdl`` is on, as
upstream sets it, and promoted neither.

Function counts
---------------

Measured through ``corpus.smdaify`` with the glue filter on. Every partition
adds up to the report total exactly, and the vendored-third-party bucket is
zero in all four because there is no vendored code in the tree.

``PhantomDllHollower.exe`` x64, 21 functions:

    5   this project's: HollowDLL 420, wmain 124, CheckRelocRange 51,
        GetPAFromRVA 38, GetContainerSectHdr 29
    12  one-instruction import thunks, all named from the PDB - six kernel32
        (FindFirstFileW, GetFileSize, SetFilePointer, GetSystemDirectoryW,
        LoadLibraryW, CreateFileTransactedW) and six UCRT (wcscat_s,
        _stricmp, _configure_wide_argv, _initialize_wide_environment,
        _get_initial_wide_environment, __p___wargv)
    4   MSVC CRT bodies the name-keyed glue filter does not reach:
        __scrt_common_main_seh 99, printf 25, wmainCRTStartup 4 and a
        one-instruction __scrt_wide_environment_policy::initialize_environment

``PhantomDllHollower.exe`` x86, 21 functions:

    5   this project's: HollowDLL 481, wmain 155, GetPAFromRVA 57,
        GetContainerSectHdr 55, CheckRelocRange 44
    12  the same twelve thunks, stdcall-decorated
    4   MSVC CRT bodies: printf 20, __scrt_wide_argv_policy::configure_argv 5,
        wmainCRTStartup 2, initialize_environment 1. No
        __scrt_common_main_seh - see below

``MemSweep.exe`` x64, 56 functions:

    6   this project's bodies: MemoryPermissionRecord::UpdateMap 289,
        wmain 243, ::ShowRecords 157, EnumProcessMem 103, QueryProcessMem 87,
        and MemoryPermissionRecord::MemoryPermissionRecord 56
    14  this project's EH unwind funclets: `QueryProcessMem'::`1'::dtor$0 13,
        the constructor's dtor$1 9, wmain$dtor$1 9, wmain$dtor$4 9, and ten
        two-instruction funclets of UpdateMap, wmain, QueryProcessMem and the
        constructor
    22  Microsoft STL template instantiations compiled in from the headers,
        from two 173-instruction std::_Tree_val::_Insert_node bodies down to
        three two-instruction std::list funclets
    10  one-instruction import thunks - five kernel32 (OpenProcess,
        VirtualQueryEx, CreateToolhelp32Snapshot, Process32FirstW,
        Process32NextW) and five UCRT
    4   MSVC CRT bodies: __scrt_common_main_seh 99, printf 25,
        wmainCRTStartup 4, initialize_environment 1

``MemSweep.exe`` x86, 47 functions:

    6   this project's bodies: ::ShowRecords 296, ::UpdateMap 288, wmain 279,
        EnumProcessMem 113, QueryProcessMem 103, the constructor 74
    1   one split region of one of them, which SMDA names
        MemoryPermissionRecord::ShowRecords$+0x435, 63 instructions
    26  Microsoft STL instantiations, from two 182-instruction _Insert_node
        bodies down to a one-instruction std::map destructor, and including
        the std::bad_alloc / std::exception machinery that the x64 artefact
        does not carry
    10  the same ten thunks, decorated
    4   MSVC CRT bodies: printf 20, configure_argv 5, wmainCRTStartup 2,
        initialize_environment 1

There are no unnamed functions in any of the four: the forced PDB names every
body, where the MinGW artefacts carry three to nine anonymous compiler-glue
fragments each.

``min_functions`` is deliberately not set, for the reason the MinGW recipe
gives: all four artefacts clear ``config.MIN_USEFUL_FUNCTIONS`` on their own -
21 is the smallest - and the field is for a project that genuinely contains
fewer functions than the floor, not for restating a count a docstring states.

The MemSweep asymmetry, and what it actually was
------------------------------------------------

The MinGW artefacts report 5 of this project's functions in MemSweep x64 and
13 in MemSweep x86, and the obvious reading of that - that GCC inlined eight
bodies away on x64 - is wrong. Read off the committed MinGW exports, x86 has
the same five named bodies as x64 plus eight extra entries, and all eight are
fragments rather than functions: ``_wmain.cold`` (5 instructions),
``QueryProcessMem (.cold)`` (4), ``EnumProcessMem (.cold)`` (4) and five
unnamed pieces of 16, 14, 3, 2 and 2 instructions that SMDA splits out of
those cold regions and out of the two enumerators. GCC moved the
throw/terminate paths of three functions into ``.text.unlikely`` on x86 and
did not on x64. Nothing was inlined away; the same five functions are in both.

MSVC has an asymmetry of its own, larger and pointing the other way: 20 of
this project's entries on x64 against 7 on x86. Same cause, different
mechanism. The x64 exception model puts each destructor call that has to run
during unwinding in its own funclet with its own unwind data, which the PDB
names ``wmain$dtor$1`` or ``` `MemoryPermissionRecord::UpdateMap'::`1'::dtor$2
```, and there are fourteen of them; x86 uses the ``FS:[0]`` frame-based
model, where the same destructor calls stay inside the parent body and only
one region of ``ShowRecords`` gets separated at all. So on both compilers the
architecture difference is about where cold and unwinding code is *placed*,
not about how much code exists, and on neither is it inlining. Worth stating
because the funclets and the ``.cold`` clones are two to thirteen instructions
and match nothing useful; the number to judge this family's coverage on is six
bodies on either architecture.

The one genuine difference in what the compilers emit is the opposite of
inlining as well. MSVC keeps ``MemoryPermissionRecord``'s constructor, 56
instructions on x64 and 74 on x86, which GCC emits nowhere: it is defined
in-class, takes its ``std::list`` argument by value, ``new``s the map and
calls ``UpdateMap``, and ``-O2`` inlines all of that into ``wmain`` while
``/O2 /Ob2`` does not. The destructor is empty and neither compiler emits it.
So this project's own function count is 6 under MSVC against 5 under GCC.

Whether the MSVC bodies differ from the MinGW ones
--------------------------------------------------

All of them, which is the whole reason for recording a second compiler.
Compared by PicHash against the committed MinGW artefacts, per architecture
and per source-level name:

    hollower x64   5 of 5 named bodies differ
    hollower x86   5 of 5
    MemSweep x64   5 of 5 comparable
    MemSweep x86   5 of 5 comparable

Twenty of twenty, no shared hash anywhere. The constructor has no MinGW
counterpart to compare with, and neither has any of the 22 and 26 Microsoft
STL bodies - those are libstdc++'s on the MinGW side, so they are different
code rather than a failed comparison. That is a stronger result than
``minhook_msvc.py``'s ("7 of 29 named bodies differ on MinGW x86"), and it is
what one should expect: MinHook is C with a hand-rolled length disassembler
that compiles to nearly the same thing either way, and nothing in these two
files does. Instruction counts move in both directions rather than one -
``HollowDLL`` 428 -> 420 on x64 and 491 -> 481 on x86, ``GetContainerSectHdr``
26 -> 29 and 47 -> 55, ``MemSweep``'s ``wmain`` 397 -> 243 and 439 -> 279,
``ShowRecords`` 134 -> 296 on x86 - so this is not one compiler optimising
harder but two code generators.

``__scrt_common_main_seh``, and ``printf``
------------------------------------------

Both x64 artefacts carry ``__scrt_common_main_seh`` at 99 instructions, and
that PicHash is the corpus's one standing leakage finding. Swept over every
committed ``.mcrit`` rather than assumed, the hash currently appears in four
families - bzip2, Lua (5.1.5 and 5.4.8), MemoryModule and Hidden - all on x64
and all naming it ``__scrt_common_main_seh``, and, tellingly, **not** in
``data/MSVC``, which is the corpus's reference for exactly this code and is
what would have let the filter drop it. These two artefacts are two more
sightings of that hash, not a new finding: the leakage count counts hashes and
the hash has not moved. The x86 pair does not carry it at all, which confirms
again what ``scripts/corpus/README.md`` records - it is x64 only, absent from
every x86 EXE; what the x86 pair has in its place is
``__scrt_wide_argv_policy::configure_argv`` at 5 instructions. No build flag
here was chosen to suppress any of it.

``printf`` survives the filter in all four, and for the MSVC reason rather
than the MinGW one. In the MinGW artefacts it is a filter gap: the baseline
holds that exact PicHash under the name ``printf`` and g++ emits the body as
``_Z6printfPKcz``, so the name-keyed lookup misses. Here the name is plainly
``printf`` and the baseline simply does not hold the body - the UCRT headers
define it as an inline wrapper over ``__stdio_common_vfprintf``, compiled into
every translation unit that calls it. ``cronos_msvc.py`` records the same case.
The same sweep says these two hashes are well established in the corpus
already, and classify differently from the wrapper above: the 25-instruction
x64 body is in LuaJIT, MSVC, MemoryModule, libxml2, mbedTLS, protobuf and
q3vm, and the 20-instruction x86 body in MSVC and q3vm - and because
``data/MSVC`` carries it under ``printf`` and ``wprintf`` while LuaJIT's PDB
names the identical body ``printf``, ``printf_s``, ``wprintf``, ``wprintf_s``,
``_printf_p`` and ``_wprintf_p``, the set of names is not one name repeated
and so it is a differing-names collision rather than leakage. Either way,
these artefacts join an existing shared hash and introduce nothing.

Reproducibility, measured
-------------------------

``/Brepro`` does what it is there for. The four binaries were built twice, in
runs 36560200508 and 36562628973 on separate runner instances, and all four
sha256s are identical across the two - 74570fd5 and 9a2e383b on x64, acd0838c
and c0f94538 on x86. That is the MSVC half of the claim
``scripts/corpus/README.md`` makes, and it is worth having a second
measurement of it beside the MinGW counter-example the sibling recipe found:
two MinGW builds of this very commit differ in two bytes, both the COFF
``TimeDateStamp`` GNU ld writes.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CONFIG = "Release"

# Six settings forced through a props file imported with
# ForceImportBeforeCppTargets, the technique callobfuscator.py,
# minhook_msvc.py, hidden.py and wowgrail.py use, so that no upstream file is
# modified. The docstring gives the reason for each; the two mechanical notes
# are here.
#
# ProgramDataBaseFileName is $(IntDir)$(ProjectName).compiler.pdb rather than a
# fixed stem because one props file serves both projects, which hidden.py hit
# first. Each msbuild step below also gets its own IntDir, so the two cannot
# collide even by name.
#
# ProgramDatabaseFile is stated rather than inherited so the linker PDB lands
# at a path the Artifact entries below can name: OutDir is pinned on the
# command line and TargetName is the project name, which is what these
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
# reach. Measured: the CL tracker log carries /O2 and no /GL.
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


# Read out of the tracker logs of the green run rather than out of the
# .vcxproj, because the two disagree: MSBuild supplies /D _MBCS from
# CharacterSet, /EHsc, /Gd /TP /FC and the twelve-library default link line
# that neither project mentions.
_FLAGS = ("Release configuration as upstream declares it, read back from "
          "MSBuild's tracker logs: /O2 /Oi /Gy /GS /sdl /permissive- /EHsc "
          "/W3 /Zi /D _MBCS /Gm- /fp:precise /TP, and /Oy- /analyze- on x86; "
          "linked /DEBUG /SUBSYSTEM:CONSOLE /DYNAMICBASE /NXCOMPAT "
          "(/SAFESEH on x86) against MSBuild's default library list - "
          "kernel32, user32, gdi32 and the rest of the Windows set, since "
          "neither project names a library of its own. Upstream's /MT is "
          "replaced with /MD so the MSVC runtime is imported rather than "
          "linked in; WholeProgramOptimization (/GL and /LTCG) is turned off "
          "in the props file and again as a command-line global because both "
          "projects set it in a PropertyGroup evaluated before "
          "Microsoft.Cpp.props; OptimizeReferences and EnableCOMDATFolding "
          "(/OPT:REF /OPT:ICF) are turned off, giving /OPT:NOREF /OPT:NOICF; "
          "DebugInformationFormat is forced to ProgramDatabase with a full "
          "/DEBUG, because no configuration of either project sets it and "
          "MSVC keeps symbols in a PDB; /Brepro and /INCREMENTAL:NO are "
          "added; and the toolset is retargeted from v142 to v143, the "
          "windows-2022 image carrying no v142. /LTCGOUT appears in the link "
          "line without /LTCG and names an intermediate that is never "
          "written. No upstream file is modified")


_NOTES = (
    "The MSVC build of the same commit phantomdllhollower.py pins, which that "
    "recipe flagged as worth adding: upstream is a Visual Studio 2019 "
    "solution - two Application projects, PlatformToolset v142, Release for "
    "Win32 and x64, Optimization MaxSpeed, RuntimeLibrary MultiThreaded, "
    "WholeProgramOptimization true - with no makefile and nothing that "
    "cross-builds, so a real copy of this PoC is an MSVC build and the MinGW "
    "artefacts are the unusual shape. The two now differ in the compiler and "
    "nothing else. What the family is and what in it is matchable are "
    "unchanged and stated in the MinGW recipe: HollowDLL is the technique and "
    "the only function that is, what identifies the technique is its API "
    "sequence rather than its body, the other three functions in the hollower "
    "are generic PE-parsing furniture, and MemSweep.exe is the repository's "
    "defensive scanner, recorded to name that binary rather than any "
    "technique. Built against the DLL runtime, so the MSVC C runtime is "
    "imported rather than linked in and stays attributed to data/MSVC - which "
    "matters more here than usual, because these are five- and seven-function "
    "programs and /MT would have made the family almost entirely Microsoft's "
    "code under Forrest Orr's name, the effect that put 1947 of VX-API's 4219 "
    "functions into that artefact. /GL and /LTCG are turned off in the props "
    "file and again as a command-line global, because both projects set "
    "WholeProgramOptimization in a PropertyGroup evaluated before "
    "Microsoft.Cpp.props; /OPT:REF and /OPT:ICF, which upstream's Release "
    "turns on, are turned off because ICF could fold the 29- and "
    "38-instruction PE helpers together and /OPT:REF would discard whatever "
    "the entry point does not reach. DebugInformationFormat is forced to "
    "ProgramDatabase because no configuration of either project sets it, these "
    "EXEs export nothing, and without a PDB SMDA would name no function at "
    "all. The two .vcxproj files are built individually rather than the .sln, "
    "so each gets its own IntDir and their tracker logs and compiler PDBs "
    "cannot collide. Function partitions, which add up exactly: the hollower "
    "is 5 own functions of 21 on both architectures, the rest being 12 "
    "one-instruction import thunks and 4 MSVC CRT bodies; MemSweep is 6 own "
    "bodies of 56 on x64 (plus 14 of its own x64 EH unwind funclets, 22 "
    "Microsoft STL instantiations, 10 thunks, 4 CRT bodies) and 6 of 47 on "
    "x86 (plus one 63-instruction split region of ShowRecords, 26 STL "
    "instantiations, 10 thunks, 4 CRT bodies). No function is unnamed in any "
    "of the four, the forced PDB naming every body, where the MinGW artefacts "
    "carry anonymous compiler glue. This project's own function count is 6 "
    "under MSVC against 5 under GCC: MemoryPermissionRecord's constructor is "
    "defined in-class, takes its std::list argument by value and news a map, "
    "and /O2 /Ob2 emits it out of line at 56 and 74 instructions where -O2 "
    "inlines it into wmain; the destructor is empty and neither compiler "
    "emits it. The MinGW side's 13-vs-5 MemSweep asymmetry does not exist here "
    "and was never inlining - the extra eight entries on MinGW x86 are three "
    ".cold clones and five unnamed fragments that GCC split out of "
    "throw/terminate paths - and MSVC has the opposite asymmetry for the same "
    "kind of reason: the x64 exception model emits each unwinding destructor "
    "call as its own $dtor$N funclet of 2 to 13 instructions, while x86's "
    "frame-based model keeps them inside the parent body. Every own body "
    "differs from its MinGW counterpart by PicHash - 20 of 20 comparable "
    "bodies across the four artefacts, no shared hash anywhere - with counts "
    "moving in both directions (HollowDLL 428 to 420 on x64, "
    "GetContainerSectHdr 47 to 55 on x86, MemSweep's wmain 397 to 243, "
    "ShowRecords 134 to 296 on x86), which is what recording a second "
    "compiler is for. Two runtime bodies survive the glue filter in all four "
    "artefacts and, swept against every committed export, neither hash is new "
    "to the corpus: printf, a UCRT header inline wrapper over "
    "__stdio_common_vfprintf compiled into every translation unit that calls "
    "it, at 25 instructions on x64 - a hash LuaJIT, MSVC, MemoryModule, "
    "libxml2, mbedTLS, protobuf and q3vm already carry, under six different "
    "names in LuaJIT alone, so it classifies as a differing-names collision "
    "rather than leakage - and 20 on x86, in MSVC and q3vm; and, in the two "
    "x64 artefacts only, __scrt_common_main_seh at 99 instructions, which is "
    "the corpus's one standing leakage finding, present in bzip2, Lua, "
    "MemoryModule and Hidden on x64, absent from every x86 EXE and absent from "
    "data/MSVC itself, which is why the filter cannot reach it. These are "
    "further sightings of the same unresolved hashes rather than new findings. "
    "/Brepro holds: the four binaries were built twice on separate runners and "
    "all four sha256s are identical across the two runs. Nothing in the tree "
    "is prebuilt and nothing is vendored, so the vendored-third-party bucket "
    "is zero in all four."
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
