"""liblzma built with MSVC, beside the MinGW builds of the same tags.

liblzma in the wild on Windows - installers, droppers, anything that carries
an .xz or LZMA2 payload and is not 7-Zip - is MSVC-built, and data/liblzma
carries only MinGW artefacts. Upstream's CMake support exists for precisely
this: the header comment of v5.4.7's CMakeLists.txt says it is "intended to
be useful to build static or shared liblzma on Windows with MSVC (to avoid
the need to maintain Visual Studio project files)", and v5.8.1 goes further
and rejects MSVC older than 1900.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

What was read rather than assumed, at both pinned tags:
  * BUILD_SHARED_LIBS is upstream's own option, and it is what turns the
    static lzma.lib - which SMDA cannot read - into a DLL.
  * the DLL is liblzma.dll under MSVC at both versions, but by two different
    routes. 5.4.7 sets PREFIX "" on a target called liblzma; 5.8.1 sets
    OUTPUT_NAME "lzma" and then RUNTIME_OUTPUT_NAME "liblzma" under
    "if(WIN32 AND NOT MINGW)", with a comment explaining that it keeps
    liblzma.dll while naming the import library lzma.lib for pkgconf.
  * the .rc is compiled by CMake's implicitly enabled RC language; nothing
    here needs an explicit enable_language. It carries no manifest for a DLL
    - common_w32res.rc emits one only for VFT_APP - so it cannot collide
    with the manifest CMake embeds itself.
  * the PDB is liblzma.pdb next to the DLL. CMake's MSVC shared-library rule
    passes /pdb:<TARGET_PDB> (Modules/Platform/Windows-MSVC.cmake),
    GetPDBName builds that name from the runtime artefact's own prefix and
    base name, and the PDB directory falls back to the runtime output
    directory when PDB_OUTPUT_DIRECTORY is unset (Source/cmGeneratorTarget
    .cxx). The base name is RUNTIME_OUTPUT_NAME where that is set, which a
    generator-expression probe of a target shaped like 5.8.1's confirms.
  * "liblzma" is upstream's own target name, so --target liblzma builds the
    library alone and leaves xz.exe, xzdec and lzmainfo unbuilt.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# CMake's MSVC Release default is "/MD /O2 /Ob2 /DNDEBUG" with no /Zi, and no
# /DEBUG at link, which would produce an artefact whose functions SMDA cannot
# name. RelWithDebInfo would supply both but drops to /Ob1, which is not what
# a shipped Release binary looks like, so Release is kept and /Zi added to
# it. Only the per-configuration variables are overridden: CMAKE_C_FLAGS and
# CMAKE_SHARED_LINKER_FLAGS keep the values CMake initialises them with,
# among them /machine on the 32-bit leg.
#
# The linker flags are the same set sqlite3_msvc.py explains: /DEBUG so a PDB
# is written at all, /Brepro so the PE carries no build timestamp and two
# runs of identical source record the same sha256, and /OPT:NOREF /OPT:NOICF
# so unreferenced and identically-compiled routines both survive as separate
# reference samples. /INCREMENTAL:NO is CMake's own Release default and is
# restated because setting the variable replaces it.
#
# This also settles the one thing the MinGW recipe warns about: upstream's
# string(REPLACE -O3 -O2 ...) only fires when CMAKE_C_FLAGS_RELEASE is not
# already defined, and it rewrites a GCC spelling that MSVC never emits. Both
# MSVC versions are therefore /O2 /Ob2, where the MinGW pair is -O3 for 5.4.7
# and -O2 for 5.8.1.
_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

# NMake Makefiles rather than Ninja or the Visual Studio generator: nmake
# ships with MSVC itself, so it is present wherever cl is, it is
# single-configuration (so CMAKE_BUILD_TYPE means what it says and the
# artefacts land in the build root rather than under a Release/ subdirectory)
# and it inherits the architecture from the developer environment the
# workflow set up, instead of naming it a second time.
#
# XZ_NLS=OFF is insurance, not a requirement: 5.8.1 turns translations on by
# itself only when find_package(Intl) and find_package(Gettext) both succeed,
# which they should not under MSVC, but if they did the configure would stop
# with a FATAL_ERROR about UCRT and gettext-runtime versions. Nothing in
# liblzma itself uses NLS - only the command line tools do - so switching it
# off cannot change this artefact. 5.4.7's CMake build has no translations at
# all and prints the variable back as unused, which is a warning and not a
# failure.
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DXZ_NLS=OFF '
          '%s %s' % (_CFLAGS, _LDFLAGS))


def _xz_msvc(version, git_ref, license):
    return Recipe(
        family="liblzma",
        version=version,
        upstream="https://github.com/tukaani-project/xz",
        license=license,
        source=Source(git_url="https://github.com/tukaani-project/xz.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} --target liblzma"),
            # A missing artefact is reported by build.py with the path it
            # expected and nothing else. This costs a second and puts the
            # names the build actually produced in the log the workflow
            # prints on failure, so a wrong guess about an output name is one
            # cycle to diagnose rather than two.
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/liblzma.dll",
                            component="liblzma.dll",
                            pdb="build-{arch}/liblzma.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release, /Zi added); "
                    "/DEBUG /Brepro /OPT:NOREF /OPT:NOICF at link",
        notes="Built from upstream's own CMake support, which exists to build "
              "liblzma with MSVC. Only the liblzma target is built, so xz.exe "
              "and the other tools are not in this run. No dependencies: "
              "liblzma links only the CRT and Win32, and is built against the "
              "DLL runtime so the MSVC C runtime stays attributed to "
              "data/MSVC. Unlike the MinGW pair, both versions here are /O2: "
              "upstream's -O3-to-O2 rewrite is a GCC spelling and does not "
              "fire under MSVC, and these builds set the Release flags "
              "explicitly in any case.",
    )


RECIPES = {
    # Same two tags as the MinGW recipe, for a like-for-like comparison. The
    # licence changed between them - COPYING at v5.4.7 still places liblzma
    # in the public domain, the 0BSD relicensing lands in the 5.8 series - so
    # it is stated per version there and here.
    "liblzma_5.4.7_msvc": _xz_msvc("5.4.7", "v5.4.7",
                                   license="public domain (liblzma)"),
    "liblzma_5.8.1_msvc": _xz_msvc("5.8.1", "v5.8.1",
                                   license="0BSD (liblzma)"),
}
