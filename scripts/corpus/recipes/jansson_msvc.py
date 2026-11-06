"""Jansson built with MSVC, beside the MinGW builds of the same tags.

jansson is vendored and linked into Windows software that is built with cl far
more often than with gcc, and data/Jansson held MinGW artefacts only, so a
cl-built sample was answered by GCC code. The MinGW and MSVC compilers lay out
the same source differently (different PicHashes), hence this axis.

Same two pins as jansson.py (v2.13.1 and v2.15.1), so each MinGW/MSVC pair
differs by compiler and nothing else on the source side. A separate registry
entry rather than another toolchain on the MinGW recipe, for the reason in
sqlite3_msvc.py: one Recipe has one build list and these steps are cmd.exe.

What was read rather than assumed, in CMakeLists.txt at both tags:
  * the target is called "jansson" and has no MSVC library prefix, so the DLL
    is jansson.dll where MinGW writes libjansson.dll. JANSSON_BUILD_SHARED_LIBS
    (default OFF) selects SHARED; off it is a static archive SMDA cannot read.
    The component is recorded as the name this build writes.
  * CMAKE_RUNTIME_OUTPUT_DIRECTORY is <build>/bin at both tags, so the DLL and
    its PDB land in build-<arch>/bin.
  * the shared target is linked with src/jansson.def, so the API is exported
    without CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS.
  * JANSSON_STATIC_CRT (MSVC only, default OFF) is the only thing that would
    add /MT; it is left at its default, and the runtime flag in CMake's own
    Release string is /MD. cmake_minimum_required is 3.1 at 2.13.1 and 3.10
    at 2.15.1, so CMP0091 is OLD at the first and the runtime lives in
    CMAKE_C_FLAGS_RELEASE; overriding that variable therefore has to restate
    /MD, as cjson_msvc.py explains.
  * upstream's own MSVC additions are /W3 /D_CRT_SECURE_NO_WARNINGS /wd4005
    /wd4996 /nologo; they stay. -Wno-format-truncation is behind
    check_c_compiler_flag and is rejected by cl, so it does not apply.
  * the options set on the command line are the MinGW recipe's: DOCS off (no
    sphinx), EXAMPLES off, WITHOUT_TESTS on. USE_DTOA is left at its default
    (ON from 2.15.0), so 2.15.1 carries its vendored dtoa here as in MinGW.

Overrides go through the per-configuration CMake variables, as in
cjson_msvc.py and lz4_msvc.py, not an MSBuild props file: this is an NMake
Makefiles build and there is no ForceImportBeforeCppTargets to import. They
give /MD /O2 /Ob2 /Zi, and at link /INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF
/OPT:NOICF (no /GL, no /LTCG). CMAKE_POLICY_VERSION_MINIMUM=3.5 is insurance
against a CMake 4 runner for the 3.1 declared at 2.13.1; an unused cache entry
elsewhere.

Flags read back from the tracker logs: PENDING (filled after the runner build).
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
          '-DCMAKE_VERBOSE_MAKEFILE=ON '
          '-DJANSSON_BUILD_SHARED_LIBS=ON -DJANSSON_BUILD_DOCS=OFF '
          '-DJANSSON_EXAMPLES=OFF -DJANSSON_WITHOUT_TESTS=ON %s %s'
          % (_CFLAGS, _LDFLAGS))


def _jansson_msvc(version, git_ref):
    return Recipe(
        family="Jansson",
        version=version,
        upstream="https://github.com/akheron/jansson",
        license="MIT",
        source=Source(git_url="https://github.com/akheron/jansson.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} --target jansson"),
            BuildStep("dir build-{arch}\\bin", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/bin/jansson.dll",
                            component="jansson.dll",
                            pdb="build-{arch}/bin/jansson.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release, /Zi added), plus "
                    "upstream's /W3 /D_CRT_SECURE_NO_WARNINGS /wd4005 "
                    "/wd4996; /DEBUG /Brepro /OPT:NOREF /OPT:NOICF at link",
        notes="Same tag as the MinGW recipe. Built against the DLL runtime, "
              "so the MSVC C runtime is imported and stays attributed to "
              "data/MSVC. Named jansson.dll rather than libjansson.dll "
              "because MSVC has no library prefix.",
    )


RECIPES = {
    "Jansson_2.13.1_msvc": _jansson_msvc("2.13.1", "v2.13.1"),
    "Jansson_2.15.1_msvc": _jansson_msvc("2.15.1", "v2.15.1"),
}
