"""Zydis and Zycore built with MSVC - the compiler behind Hidden.sys.

What it is. Zydis (zyantific/zydis) is a fast, allocation-free x86 and x86-64
instruction decoder and formatter in C; Zycore is the C support library it
sits on - ZyanString, ZyanVector, ZyanList, ZyanBitset, the allocator and the
argument parser - and Zydis's only dependency. Zycore is a git submodule that
each Zydis tag pins by commit, and the pipeline's fetch stage initialises it,
so its commit is recorded in provenance beside Zydis's own.

Why it is here. Issue 45 of the tracker. data/Hidden vendors Zydis 3.1.0 and
Zycore 1.0.0 under Hidden/Disasm and compiles them into Hidden.sys with
ZYCORE_STATIC_DEFINE, ZYDIS_STATIC_DEFINE and ZYAN_NO_LIBC, so 103 of the
507 functions the Hidden family reports for Hidden.sys are Zydis or Zycore
under the wrong name (the committed notes say 101; 103 carry a Zydis, Zyan or
Zycore name, 91 of them ten instructions or more). This is a
de-duplication and attribution family, not a new sighting: the chain is
ValleyRAT to Hidden, which Check Point Research publishes at roughly 175 of
about 200 driver functions, and Hidden to Zydis, which this corpus measures.
No published function-level match between Zydis and a ValleyRAT sample
exists, and none is claimed.

Measured against the Hidden family, on the x64 artefacts (Hidden is x64 only,
because the WDK has no x86 kernel libraries): every one of those 103 symbol
names is present in the MSVC build of Zydis 3.1.0 (103 of 103, with and
without ZYAN_NO_LIBC), against 83 in the MinGW and ELF builds and 95 in
4.1.1 MSVC, so the vendored copy is confirmed as 3.1.0 by name. Exact PicHash
agreement is much thinner: 3 of the 91 substantial ones
(ZydisFormatterBufferGetString, ZydisFormatterTokenNext and
ZydisIsFeatureEnabled, same name and same hash) with the 3.1.0 MSVC builds, 2
with 4.1.1 MSVC and none with MinGW or ELF. The driver is compiled by the
WDK's kernel-mode toolset with its own flags, which is a different code
generator configuration from the user-mode cl line used here, and the other 88
differ in encoding, not in what they are. So Hidden.sys's copy is not an
exact duplicate of this one, and fuzzy matching, not PicHash, is what will
link them. The functions are still carried inside data/Hidden/x64 under the
Hidden name: moving them out would rewrite committed Hidden data, which needs
a name-based removal this tooling does not have (refilter removes by baseline
symbol and PicHash only), so that is left as a decision and recorded in
hidden.py.

Zycore is not a family of its own. It cannot be built into a PE by itself
without becoming a second copy of the same functions: a Zycore DLL and a Zydis
DLL that links it statically both carry ZyanString and ZyanVector under two
family names, which is what validate --deep fails on. It is part of the Zydis
image here, and its functions are the Zyan* names (144 to 176 of an x64
image).

How it is built. Zydis's CMake builds libZydis and libZycore as static
archives, and SMDA cannot read an archive, so one DLL is linked from both with
the whole of each archive included (--whole-archive, /WHOLEARCHIVE), the route
cryptopp and the MSVC mbedTLS take. The two together are the library: Zydis's
decoder tables, decoder, formatters (Intel, AT&T), and the whole of Zycore.
Zydis's own CMake builds a shared library with ZYDIS_BUILD_SHARED_LIB, and
that path is not used because on Windows it unconditionally adds
resources/VersionInfo.rc, which is UTF-16 and which windres refuses
("syntax error" on the first line), so no MinGW DLL would link; the static
route needs no change to upstream. Examples and tools are switched off, and
-DCMAKE_POLICY_VERSION_MINIMUM=3.5 lets CMake 4 configure the 3.x projects'
old minimum.

Two versions. 3.1.0 is what Hidden vendors and the issue's first priority.
4.1.1 is the current release (4.x adds an encoder and has 194 Zydis* functions
in the MSVC x64 image against 3.1.0's 132). The
PicHash overlap at the ten-instruction floor between them on one toolchain is
110 of 198 distinct hashes (MinGW x64), 115 of 236 (MSVC x64), 113 of 205
(ELF x64) and under a third on x86, so each is a reference of its own.

MSVC specifics. Three builds: 3.1.0 and 4.1.1 as the project's CMake configures
them, and 3.1.0 again with -DZYAN_NO_LIBC=ON, the configuration Hidden uses.
ZYAN_NO_LIBC changes what is compiled, which is the measured difference: the
build without it has 38 function names the other lacks - the default allocator,
the critical-section, thread-local-storage, memory-protection and terminal
wrappers, ZyanArgParse, and the Init, Duplicate and Concat forms of ZyanString
and ZyanVector that take the default allocator - and the nolibc build has six
the other lacks, Zycore's own ZYAN_MEMCPY, ZYAN_MEMMOVE, ZYAN_MEMSET,
ZYAN_MEMCMP, ZYAN_STRLEN and ZYAN_STRCMP. The PicHash overlap between the
3.1.0 build with it and without it is 132 of 226 distinct x64 hashes (179 of
244 on x86), so it is a different set of functions, not a relabel, and the
3.1.0-nolibc version string keeps the two apart.

Counts, kept + removed = total, ten instructions or more in brackets, every
kept function named from the PDB: 3.1.0 x86 328 + 160 = 488 (259), x64 316 +
150 = 466 (239); 4.1.1 x86 401 + 147 = 548 (311), x64 381 + 150 = 531 (291);
3.1.0-nolibc x86 295 + 140 = 435 (250), x64 284 + 129 = 413 (228). The
removed functions are MSVC runtime that /MD still links statically.

Glue survivors, by name and PicHash: _fileno, _get_osfhandle and _isatty
(__fileno, __get_osfhandle, __isatty on x86) are one-instruction import
thunks, PicHash 1253497258561142223, in the libc builds of both versions.

Build. NMake Makefiles so the target architecture is the developer
environment's, Release with /MD /O2 /Ob2 /Z7 (the /Z7 is deliberate: the
archives are built by one step and linked by another, and C7 debug information
travels inside the objects), and a one-line anchor translation unit written by
a step because link needs an object of its own beside /WHOLEARCHIVE. The link
is /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF so the PE is
reproducible and nothing is folded or reached through a thunk table. /MD keeps
the MSVC C runtime imported so it stays attributed to data/MSVC.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Z7"'
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
          '-DZYDIS_BUILD_EXAMPLES=OFF -DZYDIS_BUILD_TOOLS=OFF %s ' % _CFLAGS)
_ANCHOR_SRC = ('python -c "'
               "open('anchor.c','w').write("
               "'int zydis_msvc_anchor(void){return 0;}')"
               '"')
_ANCHOR = "cl /nologo /c /O2 /MD /Z7 /Foanchor.obj anchor.c"
_LINK = ('link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO '
         '/OPT:NOREF /OPT:NOICF '
         '/WHOLEARCHIVE:build-{arch}\\Zydis.lib '
         '/WHOLEARCHIVE:build-{arch}\\zycore\\Zycore.lib '
         '/PDB:zydis.pdb /OUT:zydis.dll anchor.obj kernel32.lib')

_COMMON = ("Zydis and its Zycore submodule built as static archives and "
           "linked into one DLL with /WHOLEARCHIVE, so the whole of Zycore is "
           "in the image under the Zydis name. Hidden vendors Zydis 3.1.0 "
           "and compiles it into Hidden.sys, 103 of whose functions carry "
           "Zydis or Zycore names: all 103 are present here by name at "
           "3.1.0, with exact PicHash agreement on only 3 of the 91 "
           "substantial ones because Hidden is compiled by the WDK. ")


def _zydis(version, tag, extra="", notes=""):
    return Recipe(
        family="Zydis",
        version=version,
        upstream="https://github.com/zyantific/zydis",
        license="MIT, Copyright (c) Florian Bernd, Joel Hoener",
        source=Source(git_url="https://github.com/zyantific/zydis.git",
                      git_ref=tag),
        build=[BuildStep(_CMAKE + extra),
               BuildStep("cmake --build build-{arch}"),
               BuildStep(_ANCHOR_SRC),
               BuildStep(_ANCHOR),
               BuildStep(_LINK),
               BuildStep("dir build-{arch} build-{arch}\\zycore",
                         allow_failure=True)],
        artifacts=[Artifact(path="zydis.dll", component="zydis.dll",
                            pdb="zydis.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Z7 (CMake Release, /Z7 added)%s; /DEBUG "
                    "/Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF /WHOLEARCHIVE "
                    "at link" % (", -DZYAN_NO_LIBC=ON" if extra else ""),
        notes=_COMMON + notes,
    )


RECIPES = {
    "Zydis_3.1.0_msvc": _zydis(
        "3.1.0", "v3.1.0",
        notes="Tag v3.1.0 with the Zycore commit it pins, 3435866, built as "
              "the project configures itself. Measured: x86 328 functions "
              "kept of 488, x64 316 of 466, 259 and 239 of them ten "
              "instructions or more, all named."),
    "Zydis_4.1.1_msvc": _zydis(
        "4.1.1", "v4.1.1",
        notes="Tag v4.1.1 with the Zycore commit it pins, 0b2432c. Measured: "
              "x86 401 functions kept of 548, x64 381 of 531, 311 and 291 of "
              "them ten instructions or more, all named. 115 of 236 "
              "distinct x64 hashes of the 3.1.0 build are also in this one."),
    "Zydis_3.1.0-nolibc_msvc": _zydis(
        "3.1.0-nolibc", "v3.1.0", extra="-DZYAN_NO_LIBC=ON",
        notes="Tag v3.1.0 built with ZYAN_NO_LIBC, the configuration Hidden "
              "uses; the ordinary build is the 3.1.0 row. The default "
              "allocator, critical-section, TLS and terminal wrappers drop "
              "out and Zycore's own ZYAN_MEMCPY and friends come in. Measured: x86 295 functions kept "
              "of 435, x64 284 of 413, 250 and 228 of them ten "
              "instructions or more, all named. 132 of its 226 distinct x64 "
              "hashes are shared with the ordinary 3.1.0 build, so it is a "
              "different set of functions rather than a relabel. This is the "
              "build whose names match Hidden.sys's 103 Zydis and Zycore "
              "functions."),
}


# Hidden's vendored copy: master at 6a17c48 with its Zycore pin 4f3746f (see
# the "Hidden's commit" paragraph above). Built twice the way the 3.1.0 rows
# are, and once more with the WDK, below.
_HIDDEN_COMMIT = "6a17c48576e1b016ce098c4bdbd001a1403b6a0a"
_HIDDEN_NOTE = ("Master at commit 6a17c48 (2021-07-29) with the Zycore commit "
                "it pins, 4f3746f: the sources Hidden/Disasm vendors, "
                "identified by content (its ZYDIS_VERSION still reads "
                "3.1.0, 130 commits after the v3.1.0 tag). ")
RECIPES["Zydis_3.1.0-6a17c48_msvc"] = _zydis(
    "3.1.0-6a17c48", _HIDDEN_COMMIT,
    notes=_HIDDEN_NOTE + "MEASURED_PLAIN")
RECIPES["Zydis_3.1.0-6a17c48-nolibc_msvc"] = _zydis(
    "3.1.0-6a17c48-nolibc", _HIDDEN_COMMIT, extra="-DZYAN_NO_LIBC=ON",
    notes=_HIDDEN_NOTE + "Built with ZYAN_NO_LIBC, Hidden's configuration. "
    "MEASURED_NOLIBC")

# The WDK build. CMake is run for its configure step only, because that is
# what writes the two export headers (ZydisExportConfig.h,
# ZycoreExportConfig.h) the sources include; nothing it would compile is
# used. The 14 translation units of src/ are then compiled by a generated
# kernel-mode driver project that carries Hidden.vcxproj's Release|x64
# settings and nothing else - the WindowsKernelModeDriver10.0 toolset,
# ConfigurationType Driver, DriverType WDM, the three defines - and is
# built with the same msbuild properties and the same forced props file as
# hidden.py's driver step, so the compiler and linker see Hidden.sys's
# command lines. corpus_entry.c is a DriverEntry that returns
# STATUS_SUCCESS; a Driver project will not link without one.
_WDK_PROPS = (
    'python -c "'
    "c='<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>"
    "<ProgramDataBaseFileName>$(IntDir)$(ProjectName).compiler.pdb"
    "</ProgramDataBaseFileName>"
    "<WholeProgramOptimization>false</WholeProgramOptimization>"
    "<TreatWarningAsError>false</TreatWarningAsError>';"
    "l='<GenerateDebugInformation>true</GenerateDebugInformation>"
    "<ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile>"
    "<OptimizeReferences>false</OptimizeReferences>"
    "<EnableCOMDATFolding>false</EnableCOMDATFolding>"
    "<LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration>"
    "<AdditionalOptions>%(AdditionalOptions) /Brepro /INCREMENTAL:NO"
    "</AdditionalOptions>';"
    "open('corpus-drv.props','w').write("
    "'<Project><ItemDefinitionGroup><ClCompile>'+c+'</ClCompile><Link>'"
    "+l+'</Link></ItemDefinitionGroup></Project>')"
    '"')
_WDK_PROJECT = (
    'python -c "'
    "q=chr(39);"
    "i=lambda p: '<Import Project='+q+'$(VCTargetsPath)'+chr(92)+p+q+' />';"
    "open('zydis.vcxproj','w').write("
    "'<Project DefaultTargets='+q+'Build'+q+'>'"
    "'<ItemGroup><ProjectConfiguration Include='+q+'Release|x64'+q+'>'"
    "'<Configuration>Release</Configuration><Platform>x64</Platform>'"
    "'</ProjectConfiguration></ItemGroup>'"
    "'<PropertyGroup><ProjectGuid>{6A17C485-76E1-4B01-8CE0-98C4BDBD0014}'"
    "'</ProjectGuid><RootNamespace>zydis</RootNamespace></PropertyGroup>'"
    "+i('Microsoft.Cpp.Default.props')+"
    "'<PropertyGroup><TargetVersion>Windows7</TargetVersion>'"
    "'<UseDebugLibraries>false</UseDebugLibraries>'"
    "'<PlatformToolset>WindowsKernelModeDriver10.0</PlatformToolset>'"
    "'<ConfigurationType>Driver</ConfigurationType>'"
    "'<DriverType>WDM</DriverType></PropertyGroup>'"
    "+i('Microsoft.Cpp.props')+"
    "'<ItemDefinitionGroup><ClCompile><PreprocessorDefinitions>'"
    "'ZYCORE_STATIC_DEFINE;ZYDIS_STATIC_DEFINE;ZYAN_NO_LIBC;'"
    "'%(PreprocessorDefinitions)</PreprocessorDefinitions>'"
    "'<AdditionalIncludeDirectories>include;src;dependencies/zycore/include;'"
    "'build-x64;build-x64/zycore;%(AdditionalIncludeDirectories)'"
    "'</AdditionalIncludeDirectories></ClCompile></ItemDefinitionGroup>'"
    "'<ItemGroup><ClCompile Include='+q+'src/*.c'+q+' />'"
    "'<ClCompile Include='+q+'corpus_entry.c'+q+' /></ItemGroup>'"
    "+i('Microsoft.Cpp.targets')+'</Project>');"
    "open('corpus_entry.c','w').write('#include <wdm.h>'+chr(10)+"
    "'DRIVER_INITIALIZE DriverEntry;'+chr(10)+"
    "'NTSTATUS DriverEntry(PDRIVER_OBJECT d, PUNICODE_STRING r)'"
    "'{ UNREFERENCED_PARAMETER(d); UNREFERENCED_PARAMETER(r); '"
    "'return STATUS_SUCCESS; }'+chr(10))"
    '"')
_WDK_MSBUILD = ('msbuild zydis.vcxproj '
                '/p:Configuration=Release /p:Platform={msbuild_platform} '
                '/p:TargetVersion=Windows10 /p:SignMode=Off '
                '/p:SkipPackageVerification=true '
                '/p:WholeProgramOptimization=false '
                '/p:OutDir=%CD%\\out\\ /p:IntDir=%CD%\\obj\\drv\\ '
                '/p:ForceImportBeforeCppTargets=%CD%\\corpus-drv.props '
                '/m /v:normal')

RECIPES["Zydis_3.1.0-6a17c48-wdk"] = Recipe(
    family="Zydis",
    version="3.1.0-6a17c48-wdk",
    upstream="https://github.com/zyantific/zydis",
    license="MIT, Copyright (c) Florian Bernd, Joel Hoener",
    source=Source(git_url="https://github.com/zyantific/zydis.git",
                  git_ref=_HIDDEN_COMMIT),
    build=[BuildStep(_CMAKE + "-DZYAN_NO_LIBC=ON"),
           BuildStep(_WDK_PROPS),
           BuildStep(_WDK_PROJECT),
           BuildStep(_WDK_MSBUILD),
           BuildStep("dir /s out", allow_failure=True)],
    artifacts=[Artifact(path="out\\zydis.sys", component="zydis.sys",
                        pdb="out\\zydis.pdb")],
    # The WDK has no x86 kernel libraries; see hidden.py.
    toolchains=["msvc_x64"],
    build_flags="Release|x64 of a generated WDM driver project on the "
                "WindowsKernelModeDriver10.0 toolset with "
                "ZYCORE_STATIC_DEFINE, ZYDIS_STATIC_DEFINE and ZYAN_NO_LIBC - "
                "Hidden.vcxproj's own settings - built with hidden.py's "
                "msbuild properties (TargetVersion=Windows10, SignMode=Off, "
                "SkipPackageVerification=true, WholeProgramOptimization=false) "
                "and its forced props file (/Zi with separate compiler and "
                "linker PDBs, /DEBUG, /OPT:NOREF /OPT:NOICF, no LTCG, /Brepro, "
                "/INCREMENTAL:NO, TreatWarningAsError false); the code "
                "generation flags are the WDK's defaults, as for Hidden.sys. "
                "CMake configures only, to write the export headers",
    notes=_HIDDEN_NOTE + "Compiled the way Hidden.sys compiles it: the "
          "WDK's kernel-mode toolset and Hidden.vcxproj's defines, in a "
          "generated driver project whose only other code is a DriverEntry "
          "returning STATUS_SUCCESS. MEASURED_WDK",
)
