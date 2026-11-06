"""llhttp built with MSVC, beside the MinGW build of the same tag.

llhttp is vendored into Windows software that is built with cl at least as
often as with gcc, and data/llhttp held MinGW artefacts only. Same pin as
llhttp.py (release/v9.3.0, the tag that ships the generated C sources, so no
npm and no llparse), so the MinGW/MSVC pair differs by compiler only.

A separate registry entry rather than a second toolchain on the MinGW recipe:
one Recipe has one build list and these steps are cmd.exe.

Built with upstream's CMake and the NMake Makefiles generator (as cjson_msvc
and lz4_msvc), target llhttp_shared. Nothing is patched. Read from
CMakeLists.txt at the tag rather than assumed:
  * BUILD_SHARED_LIBS defaults ON and the target is llhttp_shared with
    OUTPUT_NAME llhttp, so the DLL is llhttp.dll where MinGW writes
    libllhttp.dll, in the build directory itself (no bin/ subdirectory).
  * the API is exported by LLHTTP_EXPORT (__declspec(dllexport) under
    _WIN32), so no .def file or CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS is needed.
  * the default build type is RelWithDebInfo, which the MinGW recipe keeps;
    kept here too. For cl that is /MD /Zi /O2 /Ob1 /DNDEBUG. The runtime is
    /MD (cmake_minimum_required is 3.25, so CMP0091 is NEW and the default
    MSVC_RUNTIME_LIBRARY selects the DLL runtime), no /GL.
  * CMake's RelWithDebInfo linker default is `/debug /INCREMENTAL`, so the
    shared linker flags for that configuration are overridden to
    /INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF. Only the linker
    flags are touched; the compile flags are upstream's.
  * CMAKE_VERBOSE_MAKEFILE=ON so the link line is readable from the log
    (nmake does not echo the compile line either way).
  * configure_file writes libllhttp.pc into the source tree, as in MinGW.

Component name llhttp.dll (the name this build writes).

Read back from the runner's logs (windows-2022, MSVC 19.44.35229, v143), not
assumed: the link line at both archs is, verbatim apart from paths,
`/out:llhttp.dll /dll /version:9.3 /machine:<x64|X86> /INCREMENTAL:NO /DEBUG
/Brepro /OPT:NOREF /OPT:NOICF` plus CMake's default libraries and
/MANIFEST:EMBED; no /GL and no /LTCG anywhere. The compile line goes through
a response file nmake does not echo, so the compile flags are CMake's
RelWithDebInfo defaults, not read back. The DLL is 56,320 bytes (x64) and the
build directory holds llhttp.dll and llhttp.pdb.

Counted on the runner, kept + removed = image total (removed is the
baseline's compiler-runtime filter, "dropped N compiler runtime functions"):

               kept    removed    image
    x86         125      128       253
    x64         125      122       247

The removed functions are MSVC runtime glue (DllMain, _DllMainCRTStartup,
_CRT_INIT, __scrt_* and __castguard_* families, kernel32 import thunks).
Glue survivors: none. The three non-llhttp names that remain are llhttp's own
generated helpers, llparse__match_sequence_id, llparse__match_sequence_to_lower
and llparse__match_sequence_to_lower_unsafe (PicHashes x86
4122063763036958151, 2954676877279366605, 6934423368462920082; x64
16863769406257931593, 2664413443017959462, 8404370493517813254; 42 to 54
instructions each). The other 122 functions are llhttp__internal__* and
llhttp_* by name; no unnamed function in either artefact.

MinGW against MSVC, PicHash overlap over functions of 10+ instructions (same
tag, same arch):

                  mingw / msvc     shared
    x86              44 / 56          0
    x64              30 / 31          0

No exact function body is shared at that floor (13 x86 and 15 x64 PicHashes
are shared across all sizes, i.e. trivial functions), so the MSVC axis is
needed for a cl-built sample.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELWITHDEBINFO='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=RelWithDebInfo '
          '-DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
          '-DCMAKE_VERBOSE_MAKEFILE=ON -DBUILD_SHARED_LIBS=ON %s' % _LDFLAGS)


def _llhttp_msvc(version, git_ref):
    return Recipe(
        family="llhttp",
        version=version,
        upstream="https://github.com/nodejs/llhttp",
        license="MIT",
        source=Source(git_url="https://github.com/nodejs/llhttp.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} --target llhttp_shared"),
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/llhttp.dll",
                            component="llhttp.dll",
                            pdb="build-{arch}/llhttp.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /Zi /O2 /Ob1 /DNDEBUG (CMake RelWithDebInfo, "
                    "upstream default); /DEBUG /Brepro /INCREMENTAL:NO "
                    "/OPT:NOREF /OPT:NOICF at link",
        notes="Pre-generated C from the release/v%s tag (llhttp.c, api.c, "
              "http.c); the llparse toolchain is not run. Named llhttp.dll "
              "rather than libllhttp.dll because MSVC has no library prefix."
              % version,
    )


RECIPES = {
    "llhttp_9.3.0_msvc": _llhttp_msvc("9.3.0", "release/v9.3.0"),
}
