"""Crypto++ built with MSVC, beside the MinGW build of the same tag.

Crypto++ in malware is essentially always MSVC-built - it is a C++ toolkit
with a Visual Studio solution in the tree, and the projects that embed it are
Visual Studio projects - so data/cryptopp's MinGW-only coverage answers the
likeliest sighting with the wrong code generator. C++ is also where the two
compilers diverge most: name mangling, exception tables, vtable and thunk
shapes and template instantiation all differ, so the MinGW artefact matches
an MSVC Crypto++ far more weakly than it would for a C library.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

The shape of this build mirrors the MinGW one exactly, because upstream
forces it to. Crypto++ ships cryptlib.vcxproj (a static library) and
cryptdll.vcxproj (the FIPS-subset DLL, a fraction of the library - the same
trap the GNUmakefile has). SMDA cannot read a static .lib, and the FIPS DLL
is not the library anyone is trying to match, so cryptlib.lib is built first
and then linked whole into a DLL - /WHOLEARCHIVE being link.exe's
--whole-archive, and for the same reason: to force every object in rather
than only what an anchor happens to reference.

What was read rather than assumed, in cryptlib.vcxproj at CRYPTOPP_8_9_0:

  * ConfigurationType is StaticLibrary, TargetName is cryptlib, TargetExt is
    .lib, and the Release/Debug OutDir is "$(Platform)\\Output\\$(Configuration)\\".
    So the archive is <Platform>\\Output\\Release\\cryptlib.lib. (The
    DLL-Import configurations use a different directory and define
    CRYPTOPP_IMPORTS; they are for building *against* cryptopp.dll and are
    not used here.)
  * PlatformToolset is "$(DefaultPlatformToolset)", which the project itself
    falls back to v100 when empty. MSBuild global properties beat a project
    PropertyGroup, so /p:PlatformToolset=v143 pins it to the only toolset the
    windows-2022 image carries.
  * the Release ItemDefinitionGroup sets RuntimeLibrary MultiThreaded, i.e.
    /MT. That is the one setting in this recipe that has to change: under
    /MT the MSVC C runtime is linked into the artefact and filed under the
    cryptopp name, which is what put 1947 of VX-API's 4219 functions into
    that artefact. It is overridden to MultiThreadedDLL.
  * the Release group sets no DebugInformationFormat at all, so whether a
    PDB exists depends on an MSBuild default. It is forced to OldStyle
    (/Z7) rather than ProgramDatabase (/Zi): /Z7 puts the debug info in the
    .obj files themselves, which is what survives being packed into a .lib
    and unpacked again by a separate link step. With /Zi the objects would
    instead carry a path to a compiler PDB that the wrapper link has to find.
  * the "All Configurations" group sets WholeProgramOptimization true, i.e.
    /GL. A /GL archive holds IL rather than machine code and makes the
    wrapper link an implicit LTCG link, whose whole-program dead-code
    elimination is exactly what /WHOLEARCHIVE is here to prevent. It is
    turned off both ways: as a global property, which is where the project
    declares it, and as ClCompile metadata in the props file.
  * the per-file ISA settings are intact and are deliberately left alone -
    chacha_avx.cpp carries EnableEnhancedInstructionSet
    AdvancedVectorExtensions2 and its neighbours carry their own, which is
    why the MinGW recipe pins CXXFLAGS on the command line rather than
    flattening CRYPTOPP_CXXFLAGS. Flattening them here would emit code no
    real Crypto++ binary contains.
  * rdrand.asm, rdseed.asm, x64masm.asm and x64dll.asm are CustomBuild items
    assembled with ml/ml64 straight out of the project file, so the MASM
    fast paths are in this artefact. Both assemblers are in the developer
    environment the workflow sets up.
  * osrng.h carries "#pragma comment(lib, \"advapi32.lib\")" and
    "bcrypt.lib", so those arrive through the objects; ws2_32 is what
    upstream's GNUmakefile adds for winpipes.cpp. All three are named on the
    link line anyway rather than relied on.

Only 8.9.0 is covered. 7.0.0's cryptlib.vcxproj was read too and is the same
file in every respect this recipe depends on - same configurations, same
OutDir, same TargetName, same v100 default toolset, same /MT Release - so it
is a one-line addition once this pattern is green; it is held back only
because the static-lib-to-DLL wrap is new here and a second version doubles
the cost of getting it wrong. 5.6.5 is deliberately not covered: it hardcodes
PlatformToolset v100 rather than defaulting to it, and it is 2016 C++03 that
the MinGW recipe already had to pin to -std=c++11 to keep GCC 13 happy, so
v143 is a real risk rather than a theoretical one.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_LIB = "{msbuild_platform}\\Output\\Release\\cryptlib.lib"

# The props file and the anchor translation unit, written from a step so that
# nothing outside the fetched tree is part of the build. No % anywhere: cmd
# .exe would try to expand it.
#
# ForceImportBeforeCppTargets is imported after the project's own
# ItemDefinitionGroups, so these three win over the Release configuration -
# the mechanism blackbone.py already uses. Upstream source is untouched.
_PREPARE = (
    'python -c "'
    "open('msvcprops.props','w').write("
    "'<Project><ItemDefinitionGroup><ClCompile>'"
    "'<RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary>'"
    "'<DebugInformationFormat>OldStyle</DebugInformationFormat>'"
    "'<WholeProgramOptimization>false</WholeProgramOptimization>'"
    "'</ClCompile></ItemDefinitionGroup></Project>');"
    "open('anchor.c','w').write('int cryptopp_anchor(void){return 0;}')"
    '"')

_MSBUILD = ('msbuild cryptlib.vcxproj /p:Configuration=Release '
            '/p:Platform={msbuild_platform} /p:PlatformToolset=v143 '
            '/p:WholeProgramOptimization=false '
            '/p:ForceImportBeforeCppTargets=%CD%\\msvcprops.props '
            '/m /v:minimal')

# link needs at least one object of its own; /WHOLEARCHIVE supplies the rest.
# /MD here too, or this single object would drag the static CRT in.
_ANCHOR = "cl /nologo /c /O2 /MD /Z7 /Foanchor.obj anchor.c"

# A DLL, not the .lib MSBuild just produced: SMDA cannot read a static
# library. /WHOLEARCHIVE forces every object in, including the ones nothing
# references, which is the whole point - the FIPS DLL upstream ships is the
# alternative and it is a fraction of the library.
#
# /Brepro drops the build timestamp MSVC stamps into the PE header, without
# which two runs over identical source record different sha256s. /OPT:NOREF
# keeps routines nothing references and /OPT:NOICF keeps two routines that
# compiled to identical bodies apart - folding them cost VX-API its
# StringConcat/StringCopy pair, and a crypto library is full of near-twin
# bodies. link /DEBUG is documented to imply both, but the corpus says what
# it wants rather than relying on that.
#
# /INCREMENTAL:NO because /DEBUG implies /INCREMENTAL and the /OPT:NO* forms do
# not suppress it - only /OPT:REF, /OPT:ICF and /OPT:ORDER are documented to.
# An incrementally linked image reaches each function through a jump table, and
# SMDA recovers every one of those one-instruction thunks as a function of its
# own, unnamed. That was measured on the artefacts this omission produced: 5815
# of cryptopp 8.9.0 x64's 17,244 functions. It is not what a released binary
# looks like, and it inflates the function count of the family it is filed
# under.
#
# The DLL exports nothing. That is fine and is not the MinGW build's
# situation reversed: nothing here needs an import library, and the PDB - not
# the export table - is what names the functions for SMDA.
_LINK = ('link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO '
         '/OPT:NOREF /OPT:NOICF '
         '/WHOLEARCHIVE:%s /PDB:cryptopp.pdb /OUT:cryptopp.dll '
         'anchor.obj ws2_32.lib advapi32.lib bcrypt.lib' % _LIB)


RECIPES = {
    "cryptopp_8.9.0_msvc": Recipe(
        family="cryptopp",
        version="8.9.0",
        upstream="https://github.com/weidai11/cryptopp",
        # Same reading as the MinGW recipe: License.txt places the
        # compilation under Boost 1.0 while the individual files are put in
        # the public domain by their authors.
        license="Boost-1.0 (compilation); individual files public domain",
        source=Source(git_url="https://github.com/weidai11/cryptopp.git",
                      git_ref="CRYPTOPP_8_9_0"),
        build=[
            BuildStep(_PREPARE),
            BuildStep(_MSBUILD),
            BuildStep(_ANCHOR),
            BuildStep(_LINK),
            # Cheap insurance, as in xz_msvc.py: puts the names the build
            # actually wrote into the log the workflow prints on failure.
            BuildStep("dir {msbuild_platform}\\Output\\Release",
                      allow_failure=True),
        ],
        artifacts=[Artifact(path="cryptopp.dll", component="cryptopp.dll",
                            pdb="cryptopp.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="cryptlib.vcxproj Release: /O2 /Ob2 /Oi /Oy /Gy /GF /W4 "
                    "/MD /Z7, NDEBUG and USE_PRECOMPILED_HEADERS defined, "
                    "plus the per-file ISA settings upstream assigns "
                    "(AdvancedVectorExtensions2 for chacha_avx.cpp and so "
                    "on); x86 additionally /arch:SSE2 from the project's "
                    "Win32 group. /MD and /Z7 replace upstream's /MT and its "
                    "unstated debug format, and /GL is turned off, all three "
                    "by this recipe. Whole archive linked into a DLL with "
                    "/DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF.",
        notes="Whole library, not upstream's FIPS DLL subset - the same "
              "choice the MinGW recipe makes, by the same mechanism "
              "(/WHOLEARCHIVE here, --whole-archive there). Crypto++ carries "
              "third-party code that lands in this sample under the cryptopp "
              "name: TweetNaCl (tweetnacl.cpp), Andrew Moon's "
              "curve25519-donna (donna_*.cpp), Botan's ChaCha SSE2/AVX, and "
              "Crypto++'s own DEFLATE implementation in zdeflate/zinflate/"
              "zlib.cpp, which is not zlib's code and must not be confused "
              "with data/libzlib if a deep validate round flags it. That is "
              "upstream's arrangement, not this recipe's: there is no "
              "configuration that leaves them out. Built against the DLL "
              "runtime, so the MSVC C runtime is imported rather than linked "
              "in - but note this is a C++ artefact, so MSVC STL "
              "instantiations compiled into it are attributed here and the "
              "C++ side of the glue baseline is the narrowest part of it.",
    ),
}
