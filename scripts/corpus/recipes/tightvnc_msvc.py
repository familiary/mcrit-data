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

Overlaps, measured by PicHash over functions of ten instructions or more:
83 (x86) and 48 (x64) hashes shared with UltraVNC 1.8.2.9, of 4010 and 3890
here (84 and 107, of 4083 and 3961, before the zlib functions were excluded);
none with data/libzlib, liblzma or libsodium (73 and 63 with libzlib before).
The zlib 1.2.13 the exes link statically was what `validate --deep` failed on
(TightVNC, UltraVNC and libzlib shared one symbol name for each of 80
PicHashes); it is now removed by name, see below and ultravnc_msvc.py.
Kept functions per artefact whose name another artefact's baseline removed:
8 on x64 and 23 on x86, STL and CRT inline instantiations. The x86 server
has 3505 unnamed functions of 8059 (exception funclets).

zlib (PR #69, which depends on PR #94 for Recipe.exclude_functions). The
exclude_functions pattern is anchored on 85 exact zlib identifiers
(_ZLIB_FUNCTIONS, built by _vendored_zlib.py). Every function the pattern
removes is zlib's: of the 250 removed from the eight images, 194 have a
PicHash of 10 or more instructions that is in data/libzlib, 48 have fewer
than 10 instructions and the PicHash of a libzlib function of the same name,
and 8 (x64 `_tr_tally`, `compress_block`, `crc32_z` twice, `deflate_fast`,
`deflate_slow` and `inflate` twice, whose hash differs from every libzlib
build) match the libzlib function of that name and architecture in opcode
sequence at 100% (frame-pointer set-up ignored). Every zlib-named function in
the images matches the pattern; none is left in. The images were re-derived from their
archives, not rebuilt. Kept / removed / excluded / total, 2.8.85: tvnserver
8059 / 1501 / 84 / 9644 (x86), 6845 / 1513 / 83 / 8441 (x64); tvnviewer 5553 /
1547 / 42 / 7142 (x86), 4834 / 1554 / 41 / 6429 (x64). 2.8.90: tvnserver 8071
/ 1501 / 84 / 9656 (x86), 6849 / 1513 / 83 / 8445 (x64); tvnviewer 5545 /
1548 / 42 / 7135 (x86), 4829 / 1555 / 41 / 6425 (x64).

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
from ._vendored_zlib import zlib_functions


# The zlib 1.2.13 the exes link statically: exact identifiers, every function
# of each name in the four images of a version is zlib's (see
# _vendored_zlib.py for the test and the docstring above for the counts).
_ZLIB_FUNCTIONS = (
    '_tr_align', '_tr_flush_bits', '_tr_flush_block', '_tr_init',
    '_tr_stored_block', '_tr_tally', 'adler32', 'adler32_combine',
    'adler32_combine64', 'adler32_combine_', 'adler32_z', 'bi_flush',
    'bi_windup', 'build_tree', 'compress_block', 'crc32', 'crc32_combine',
    'crc32_combine64', 'crc32_combine_gen', 'crc32_combine_gen64',
    'crc32_combine_op', 'crc32_z', 'deflate', 'deflateBound', 'deflateCopy',
    'deflateEnd', 'deflateGetDictionary', 'deflateInit2_', 'deflateInit_',
    'deflateParams', 'deflatePending', 'deflatePrime', 'deflateReset',
    'deflateResetKeep', 'deflateSetDictionary', 'deflateSetHeader',
    'deflateTune', 'deflate_fast', 'deflate_huff', 'deflate_rle',
    'deflate_slow', 'deflate_stored', 'fill_window', 'flush_pending',
    'gen_bitlen', 'gen_codes', 'get_crc_table', 'inflate', 'inflateCodesUsed',
    'inflateCopy', 'inflateEnd', 'inflateGetDictionary', 'inflateGetHeader',
    'inflateInit2_', 'inflateInit_', 'inflateMark', 'inflatePrime',
    'inflateReset', 'inflateReset2', 'inflateResetKeep',
    'inflateSetDictionary', 'inflateSync', 'inflateSyncPoint',
    'inflateUndermine', 'inflateValidate', 'inflate_fast', 'inflate_table',
    'init_block', 'longest_match', 'multmodp', 'pqdownheap', 'putShortMSB',
    'read_buf', 'scan_tree', 'send_all_trees', 'send_tree', 'slide_hash',
    'syncsearch', 'updatewindow', 'x2nmodp', 'zError', 'zcalloc', 'zcfree',
    'zlibCompileFlags', 'zlibVersion',
)


_PROPS = (
    'python -c "'
    "open('msvcprops.props','w').write(("
    "'<Project><ItemDefinitionGroup><ClCompile>'"
    "'<RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary>'"
    "'<WholeProgramOptimization>false</WholeProgramOptimization>'"
    "'<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>'"
    "'<PreprocessorDefinitions>_CRT_RAND_S;@p(PreprocessorDefinitions)</PreprocessorDefinitions>'"
    "'</ClCompile><Link>'"
    "'<GenerateDebugInformation>true</GenerateDebugInformation>'"
    "'<ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile>'"
    "'<LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration>'"
    "'<EnableCOMDATFolding>false</EnableCOMDATFolding>'"
    "'<OptimizeReferences>false</OptimizeReferences>'"
    "'<AdditionalOptions>/Brepro /INCREMENTAL:NO</AdditionalOptions>'"
    "'</Link></ItemDefinitionGroup>'"
    # rfb/RfbKeySym.h uses std::wstring without including <string>, which
    # older toolsets supplied transitively and v143 does not (34 x C2039/C2061
    # in the first x86 run, all in rfb.vcxproj, nothing else failed). Forced
    # inclusion of <string> for C++ translation units only, because the
    # zlib and libjpeg projects are C. The text is built with placeholder
    # tokens so no quote or percent sign reaches cmd.exe. _CRT_RAND_S goes
    # with it: 2.8.90 calls rand_s (win-system, desktop, log-server,
    # rfb-sconn), which stdlib.h declares only when the macro is defined
    # first, and the forced <string> now pulls stdlib.h in ahead of the
    # sources' own #define. 2.8.85 does not call it.
    "'<Target Name=@dForceStringInclude@d BeforeTargets=@dClCompile@d>'"
    "'<ItemGroup><ClCompile Condition=@d@s@p(Extension)@s==@s.cpp@s@d>'"
    "'<ForcedIncludeFiles>string</ForcedIncludeFiles></ClCompile>'"
    "'</ItemGroup></Target></Project>').replace('@d',chr(34)).replace('@s',chr(39))"
    ".replace('@p',chr(37)))"
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
            '/p:WindowsTargetPlatformVersion=10.0 /p:SolutionDir=%%CD%%\\ /p:WholeProgramOptimization=false '
            '/p:LinkIncremental=false '
            '/p:ForceImportBeforeCppTargets=%%CD%%\\msvcprops.props '
            '/m /v:minimal')

_FLAGS = ("Release configuration of the 2.8 vcxproj files: /O2 (MaxSpeed) "
          "/Oi /Ot /Gy, platform toolset v143 in place of v141_xp and Windows SDK 10.0 in place of 8.1; /MT "
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
        exclude_functions=[zlib_functions(_ZLIB_FUNCTIONS)],
        notes="No version is evidenced for the Kimsuky sample (issue #70); "
              "this is one of two 2.8 releases pinned by judgement. The "
              "exes statically link the in-tree zlib and libjpeg projects, "
              "so libjpeg's functions are present here under the TightVNC "
              "family; zlib's are removed by name (exclude_functions: 85 exact "
              "zlib identifiers, see the recipe docstring); the CRT is "
              "imported (/MD) and stays attributed to data/MSVC. "
              "tvnserver.exe is the service-capable server the issue names; "
              "tvnviewer.exe shares its RFB code.",
    )


RECIPES = {
    "TightVNC_2.8.85_msvc": _tightvnc(
        "2.8.85",
        "13d22e5843f1727fc7ee927a097820b4e68fd3e5f439a8c07fa0d57c6e24308c"),
    "TightVNC_2.8.90_msvc": _tightvnc(
        "2.8.90",
        "f3f76393a5865e1f1919c78c3eb43b9c937cf738927c2bfc920ecbd3913b061c"),
}
