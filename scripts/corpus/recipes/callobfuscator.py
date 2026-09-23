"""CallObfuscator (d35ha) - MSVC only, both architectures.

A tool that rewrites a PE's import table so that static and dynamic analysis
see one API where another is called: the thunk that pointed at
VirtualProtect is made to point at Sleep, and a shellcode stub prepended to
the entry point resolves the real symbol at run time and puts it back. What
is recorded here is ``cobf.exe``, the tool, built from its own six
translation units - cli/cli.cpp, cli/ini.c, src/load.cpp, src/obfuscate.cpp,
src/shellcode.cpp and src/utils.cpp - and roughly 59 functions of its own.

The tool's *output* is deliberately not recorded. That output is a modified
copy of somebody else's binary, so its code is not this project's reference
material and filing it under this family would attribute another program's
functions to CallObfuscator. Only cobf.exe is an artefact here.

src/shellcode.cpp is the part worth looking at, and the reason this project
is more than an IAT rewriter. The injected shellcode is not a byte blob: it
is fourteen ordinary C++ static member functions of ``class shellcode`` -
exit, wstr_len, hash_string, str_cpy, str_toi, str_chr, ansi_to_wide,
wstr_cpy, wstr_i_cmp, get_dll_handle, load_dll, resolve_api_set,
get_symbol_ptr, load_syms - followed by a marker function ``funs_end``, and
the tool copies the bytes between the first and the marker out of its own
image at run time. Every one is declared ``no_inline``
(``__declspec(noinline)``, shellcode.hpp) and every one has its address
taken in the static ``shellcodes_funs`` table, so the linker can neither
discard nor fold them and the compiler cannot inline them away. The
extraction depends on MSVC emitting those functions contiguously and in
source order, which is why this artefact contains them as separate
functions and why the recipe leaves them separate.

MSVC only. MinGW comes close - four of the five C++ translation units
compile clean - but include/shellcode.hpp:13 includes ``<Windows.h>`` with a
capital W, which a case-sensitive cross-build cannot resolve, and
src/shellcode.cpp:16 writes ``PVOID shellcode::shellcode_start = exit;``,
which GCC rejects. Both of those are fixable; the layout assumption above is
not. A MinGW build would link and be functionally wrong, which is worse than
one that fails, so no MinGW recipe is written.

Both architectures are built. The tool's bitness has to match the PE it
patches, upstream provides all four Platform x Configuration combinations,
and src/load.cpp:238 and src/obfuscate.cpp:306-346 gate real code on
``_M_IX86``, so the x86 and x64 artefacts are not the same program compiled
twice.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CONFIG = "Release"

# Six settings are forced through a props file imported with
# ForceImportBeforeCppTargets, the technique blackbone.py, q3vm_msvc.py and
# wowgrail.py use, so that no upstream file is modified.
#
# DebugInformationFormat is the one that has to be fixed rather than merely
# tidied. All four configurations set it to None (cobf.vcxproj lines 95, 114,
# 133 and 152), so the objects carry no debug information at all; the link
# does set GenerateDebugInformation, but a PDB built from objects compiled
# without /Zi holds public symbols only - no private symbols and no line
# information - and MSVC keeps symbols in a PDB rather than in a COFF symbol
# table, so SMDA would name very little of a 59-function image. Overridden to
# ProgramDatabase.
#
# RuntimeLibrary: upstream asks for MultiThreaded, i.e. /MT, which links the
# CRT statically. That put 1947 of VX-API's 4219 functions into that artefact
# as MSVC runtime, duplicating data/MSVC, which is this corpus's reference
# for exactly that code. /MD leaves it in ucrtbase and vcruntime140.
#
# OptimizeReferences and EnableCOMDATFolding: upstream's Release turns both
# on, i.e. /OPT:REF /OPT:ICF. Folding merges functions that compiled to
# identical bodies - it cost vxapi its StringConcat/StringCopy pair - and
# this project has several small string helpers in class shellcode that are
# plausible candidates. /OPT:REF would also be the wrong thing next to a
# shellcode region the tool identifies by address arithmetic over a
# contiguous run of functions. Both off.
#
# LinkTimeCodeGeneration is stated as well as WholeProgramOptimization being
# cleared on the command line, because the two reach the link by different
# routes and only the pair of them together guarantees no /LTCG.
#
# /Brepro drops the link timestamp so two runs give identical sha256s.
# /INCREMENTAL:NO because /DEBUG implies /INCREMENTAL and the /OPT:NO* forms
# above do not suppress it; Release already sets LinkIncremental false, but
# this recipe overrides enough of the link that inheriting it would be a
# thing to have to remember. Without it the image reaches every function
# through a table of one-instruction jump thunks and
# smdaify.assert_not_incrementally_linked refuses it.
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

# Release rather than Debug, deliberately. Debug sets LinkIncremental true,
# which assert_not_incrementally_linked refuses and which would have to be
# overridden anyway, and it sets MultiThreadedDebug - and the /MDd runtime is
# not one of the flavours baseline.py probes, so debug CRT glue would be
# mis-attributed to this family rather than dropped. Release needs /MT
# replaced, LTCG and the two /OPT switches turned off, and /Zi restored;
# after that it is an unoptimised, non-folding, fully symbolised build, which
# is what this corpus wants.
#
# /p:WholeProgramOptimization=false is a command-line global property rather
# than a props entry because the project sets WholeProgramOptimization in a
# PropertyGroup evaluated before Microsoft.Cpp.props, which a forced import
# is too late to reach. It is load-bearing here, unlike in heavensgate2.py
# where the project already disables /GL itself: LTCG inlines across
# translation units and would blur exactly the function boundaries
# src/shellcode.cpp depends on.
#
# PlatformToolset v142 is what the project asks for and the windows-2022
# runner image does not carry it - it ships VS2022 and v143 only.
# WindowsTargetPlatformVersion is already 10.0 upstream and is left alone.
#
# The solution's platforms are x86 and x64 and map to the project's Win32 and
# x64, so /p:Platform takes {arch} while the output path takes
# {msbuild_platform}, the same split q3vm_msvc.py makes.
#
# OutDir and IntDir are pinned rather than inherited, as wowgrail.py pins
# them: the Microsoft.Cpp defaults put a Win32 build one directory shallower
# than an x64 one, and pinning also keeps the compiler PDB
# (IntDir\\vc143.pdb, by MSBuild's own default) in a different directory from
# the linker PDB, which have to be separate files.
_MSBUILD = ('msbuild cobf.sln '
            '/p:Configuration=%s /p:Platform={arch} '
            '/p:PlatformToolset=v143 /p:WholeProgramOptimization=false '
            '/p:OutDir=%%CD%%\\out\\{msbuild_platform}\\ '
            '/p:IntDir=%%CD%%\\obj\\{msbuild_platform}\\ '
            '/p:ForceImportBeforeCppTargets=%%CD%%\\corpus-msvc.props '
            '/m /v:minimal' % _CONFIG)

# Everything up to the semicolon is read out of cobf.vcxproj's Release
# ItemDefinitionGroups. The absence of an <Optimization> element is not an
# omission in this description: the project sets none in any of its four
# configurations, so the compile runs at MSBuild's default rather than /O2 -
# which is part of why the tool's ~59 functions survive as separate
# functions.
_FLAGS = ("Release configuration: /Oi /Gy /W3 /GS-, ConformanceMode "
          "(/permissive-), Unicode character set, NDEBUG;_CONSOLE, include\\ "
          "on the include path, and no <Optimization> element in any "
          "configuration so the compile is not /O2; upstream's /MT is "
          "replaced with /MD, DebugInformationFormat None with /Zi and a "
          "full /DEBUG, WholeProgramOptimization (/GL and /LTCG) and "
          "OptimizeReferences/EnableCOMDATFolding (/OPT:REF /OPT:ICF) are "
          "turned off, /Brepro and /INCREMENTAL:NO are added, and the "
          "toolset is retargeted from v142 to v143")


RECIPES = {
    # The tag rather than master. 2.0 is one commit behind HEAD and
    # "git diff --stat 2.0 HEAD" is "README.md | 3 ++-" and nothing else, so
    # the two are source-identical and the tag is the better pin - it names a
    # release rather than a moment. Tag 2.0 is commit
    # 62e938f9840d37df73fe2a5e6722a2407124586e, 2021-02-21.
    "CallObfuscator_2.0": Recipe(
        family="CallObfuscator",
        version="2.0",
        upstream="https://github.com/d35ha/CallObfuscator",
        # No LICENSE or COPYING file, and a grep for licence or copyright
        # across README.md and every source and header returns nothing. The
        # only hits anywhere in the tree are the GPL markers Doxygen writes
        # into its own bundled jquery.js under docs/html/, which say nothing
        # about this project's terms. "none" is the fact; this field is
        # copied verbatim into provenance.json.
        license="none",
        source=Source(git_url="https://github.com/d35ha/CallObfuscator.git",
                      git_ref="2.0"),
        build=[
            BuildStep(_PROPS),
            BuildStep(_MSBUILD),
            # build.py reports a missing artefact by the path it expected and
            # nothing else; this puts what the build actually wrote into the
            # log the workflow prints on failure.
            BuildStep("dir out\\{msbuild_platform}", allow_failure=True),
        ],
        artifacts=[
            Artifact(path="out\\{msbuild_platform}\\cobf.exe",
                     component="cobf.exe",
                     pdb="out\\{msbuild_platform}\\cobf.pdb"),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS,
        notes="No licence of any kind: no LICENSE or COPYING file and no "
              "copyright or licence line in the README or in any source "
              "file. The artefact is cobf.exe, the tool itself, built from "
              "its own six translation units; the patched PE the tool emits "
              "at run time is a modified copy of another program and is "
              "deliberately not recorded here. src/shellcode.cpp is the "
              "distinctive part: the injected shellcode is not a byte blob "
              "but fourteen ordinary C++ static member functions plus a "
              "funs_end marker, each __declspec(noinline) and each "
              "address-taken in a static table, which the tool copies out of "
              "its own image by taking the difference between the first "
              "function's address and the marker's. The linker can therefore "
              "neither discard nor fold them, and this recipe additionally "
              "turns off upstream's /OPT:REF, /OPT:ICF and whole-program "
              "optimization so that nothing reorders or merges them - which "
              "also means this artefact is not byte-comparable with a "
              "release binary built the way upstream configures it. Both "
              "architectures are built because the tool's bitness must match "
              "its target PE's and src/load.cpp and src/obfuscate.cpp gate "
              "code on _M_IX86. Built against the DLL runtime, so the MSVC C "
              "runtime is imported rather than linked in and stays "
              "attributed to data/MSVC. No dependencies: cli/ini.c is a "
              "78-line ini parser written in the same style as the rest of "
              "the project and carrying no attribution to any upstream "
              "parser, so nothing here is vendored from elsewhere.",
    ),
}
