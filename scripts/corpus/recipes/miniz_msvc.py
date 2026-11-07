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

Flags read back from the build log rather than assumed (CMake 3.31, MSVC
19.44.35229, runner windows-2022). NMake keeps the cl and link lines in
response files, so the recipe prints the files CMake generated them from.
flags.make, both architectures: "/DWIN32 /D_WINDOWS /W3 /W3 /Zi /permissive-
/MD /O2 /Ob2 /DNDEBUG" with -Dminiz_EXPORTS. The link line in build.make:
"/dll /version:3.1 /machine:X86 (x64) /INCREMENTAL:NO /DEBUG /Brepro
/OPT:NOREF /OPT:NOICF". No /GL, no /LTCG, no /MT. The DLL is 88,064 bytes
with an 823,296-byte PDB (x86), and a first-try success on both legs: no
obstacle turned up, and no source was patched.

Counts (smda 5.0.2, mcrit 1.16.0): x86 holds 328 functions in the image, the
glue baseline removes 138 and 190 are kept; x64 holds 334, removes 145 and
keeps 189. Kept plus removed equals the image total. All kept functions are
named. 181 (x86) and 180 (x64) are miniz's own (mz_*, tdefl_*, tinfl_*,
miniz_*); 146 and 140 of the kept carry ten or more instructions, against
130 and 121 in the MinGW artefacts. The removed set is the MSVC runtime
glue: the DLL entry (_DllMainCRTStartup, dllmain_*), __scrt_* start-up and
onexit machinery, __security_*/__GS* cookie code, __castguard_*, and CRT
thunks the probes reach (malloc, free, memcpy, memset, fclose, fflush, fread,
time).

Glue survivors: nine per architecture, all one-instruction import thunks
(jmp through the IAT) to stdio and filesystem functions that the glue probes
do not call, each with PicHash 1165511d87767dcf. x86: __fseeki64, __ftelli64,
__utime64, __wfopen_s, __wfreopen_s, __wstat64, _fwrite, _remove, utime.
x64: _fseeki64, _ftelli64, _utime64, _wfopen_s, _wfreopen_s, _wstat64, fwrite,
remove. x64 utime is the exception: a one-instruction thunk with PicHash
458924a8d07e5d36, the hash mz_free shares. They are not miniz code but carry
no signal and are the same single hash MinGW's _utime thunk has; left in
because the baseline is shared tooling. fflush and _fflush were survivors
until the wide-stdio baseline (PR #80, #86) classified them as CRT glue and
removed them.

MinGW/MSVC overlap by PicHash, functions of ten or more instructions: none.
0 of 127 (x86) and 0 of 119 (x64) distinct MinGW hashes occur in the MSVC
artefact (143 and 138 distinct there). Over all sizes the shared hashes are
four on x86 and five on x64 and all are at most eight instructions: the
one-instruction thunk, mz_version, tdefl_get_adler32,
tdefl_get_prev_return_status and, on x64,
tdefl_write_image_to_png_file_in_memory.
So the pair really is complementary: an MSVC-built sample gets no help from
the MinGW reference and needs this one.
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
            # files CMake generated them into - flags.make for the compile,
            # the inline response file in build.make for the link - and
            # printed to the build log.
            BuildStep("type build-{arch}\\CMakeFiles\\miniz.dir\\flags.make",
                      allow_failure=True),
            BuildStep("type build-{arch}\\CMakeFiles\\miniz.dir\\build.make",
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
