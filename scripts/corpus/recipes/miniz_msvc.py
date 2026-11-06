"""miniz built with MSVC, beside the MinGW build of the same tag.

miniz is what small agents and loaders vendor when they want zlib's API
without zlib's build, and on Windows a vendored copy is compiled by cl far
more often than by gcc. data/miniz carries only the MinGW artefacts of
3.1.0, so an MSVC-built sample would be matched against GCC code.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

Pinned to the same tag as miniz.py (3.1.0), so the pair differs by compiler
and optimiser settings only.

What was read rather than assumed, in CMakeLists.txt at 3.1.0:
  * the library target is "miniz" (project(miniz C)), built from miniz.c,
    miniz_zip.c, miniz_tinfl.c and miniz_tdef.c. BUILD_SHARED_LIBS defaults
    to OFF - without it the build is a static miniz.lib, which SMDA cannot
    read - so it is turned on. MSVC has no library prefix, so the file is
    miniz.dll where MinGW's is libminiz.dll.
  * generate_export_header(miniz) supplies MINIZ_EXPORT, and CMake defines
    miniz_EXPORTS for a shared target, so the DLL exports the whole API
    (mz_*, tdefl_*, tinfl_*, mz_zip_*) without CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS.
  * set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/bin) puts
    the DLL in <source>/bin, not under the build directory. The PDB is
    written next to it: PDB_OUTPUT_DIRECTORY is unset, and CMake then uses
    the runtime output directory. The artefact paths are bin/miniz.dll and
    bin/miniz.pdb, as the MinGW recipe's bin/libminiz.dll.
  * for MSVC upstream appends "/W3 /Zi /permissive-" to CMAKE_C_FLAGS itself,
    so /Zi is upstream's own and is not restated; CMAKE_C_STANDARD 90 has no
    effect under cl.
  * cmake_minimum_required(VERSION 3.5...3.12): the upper bound is below
    3.15, so CMP0091 is OLD and the C runtime flag lives in
    CMAKE_C_FLAGS_RELEASE itself (default "/MD /O2 /Ob2 /DNDEBUG"), not in
    CMAKE_MSVC_RUNTIME_LIBRARY. 3.5 is the floor CMake 4 still accepts, so no
    CMAKE_POLICY_VERSION_MINIMUM is needed.
  * BUILD_EXAMPLES, BUILD_TESTS and INSTALL_PROJECT default to ON for a
    standalone project; all three are turned off, as in the MinGW recipe, to
    keep the build to the library (the tests would enable C++20).

/MD is upstream's own Release default and is restated in the variable below
so a runner CMake that changed the default could not hand the build /MT and
file the static CRT under miniz. No /GL, no /LTCG. Upstream's default link
for a CMake Release DLL has neither /DEBUG nor /Brepro, so there would be no
PDB and a timestamped PE; the per-configuration linker variable restates
CMake's own /INCREMENTAL:NO and adds /DEBUG /Brepro /OPT:NOREF /OPT:NOICF.
See cjson_msvc.py for why the per-configuration variables are overridden
rather than CMAKE_SHARED_LINKER_FLAGS.

Measured counts, the MinGW/MSVC PicHash overlap and the runtime glue that
survived are recorded below once the CI artefacts have been imported.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG"'
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON '
          '-DBUILD_EXAMPLES=OFF -DBUILD_TESTS=OFF -DINSTALL_PROJECT=OFF '
          '%s %s' % (_CFLAGS, _LDFLAGS))


def _miniz_msvc(version, git_ref):
    return Recipe(
        family="miniz",
        version=version,
        upstream="https://github.com/richgel999/miniz",
        license="MIT",
        source=Source(git_url="https://github.com/richgel999/miniz.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} --target miniz"),
            # NMake hides the cl and link command lines in response files,
            # so the flags that were actually used are read back from the
            # files CMake generated them into and printed to the build log.
            BuildStep("type build-{arch}\\CMakeFiles\\miniz.dir\\flags.make",
                      allow_failure=True),
            BuildStep("type build-{arch}\\CMakeFiles\\miniz.dir\\link.txt",
                      allow_failure=True),
            BuildStep("dir bin", allow_failure=True),
        ],
        artifacts=[Artifact(path="bin/miniz.dll", component="miniz.dll",
                            pdb="bin/miniz.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi /W3 /permissive- (CMake Release, /Zi "
                    "from upstream); /DEBUG /Brepro /OPT:NOREF /OPT:NOICF "
                    "at link",
        notes="Shared build of upstream CMake, same tag as the MinGW recipe: "
              "miniz.c, miniz_zip.c, miniz_tinfl.c and miniz_tdef.c, whole "
              "API exported. Named miniz.dll rather than libminiz.dll "
              "because MSVC has no library prefix. Built against the DLL "
              "runtime, so the MSVC C runtime is imported rather than "
              "linked in. The MinGW build is -O3 -std=gnu90, this one /O2 "
              "/Ob2, so the pair differs by compiler and optimiser.",
    )


RECIPES = {
    "miniz_3.1.0_msvc": _miniz_msvc("3.1.0", "3.1.0"),
}
