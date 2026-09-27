"""lz4 built with MSVC, beside the MinGW build of the same tag.

lz4 turns up in modern loaders, packers and installers, and those are
MSVC-built; data/lz4 carries only MinGW artefacts. Upstream keeps a CMake
project in build/cmake for exactly this, alongside a VS2022 solution - the
CMake path is used here because it is the one that needs no MSBuild property
overrides to produce a DLL with a PDB.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

What was read rather than assumed, in build/cmake/CMakeLists.txt at v1.10.0:
  * BUILD_SHARED_LIBS is a CMAKE_DEPENDENT_OPTION defaulting to ON outside
    bundled mode, and it selects the lz4_shared target; without it the build
    is a static lz4.lib, which SMDA cannot read.
  * lz4_shared carries OUTPUT_NAME "lz4" and, under "if(MSVC)",
    LZ4_DLL_EXPORT=1 - so the DLL exports its API and MSVC's empty library
    prefix makes the file lz4.dll, where MinGW's "lib" prefix makes it
    liblz4.dll. The component is recorded as the name this build produces
    rather than the MinGW one's.
  * the VERSION/SOVERSION properties on the target do not reach the file
    name: CMake drops both where the platform has no soname, which a
    cross-built MinGW configure of this same file confirms by linking
    "-o liblz4.dll" with no version in it.
  * LZ4_BUILD_CLI is upstream's option, and turning it off keeps the build
    to the library.
  * the PDB is lz4.pdb next to the DLL: CMake's MSVC shared-library rule
    passes /pdb:<TARGET_PDB>, that name is the runtime artefact's own prefix
    and base name with a .pdb suffix, and its directory falls back to the
    runtime output directory, which no target here overrides.

Only 1.10.0 is covered. 1.9.4's build/cmake/CMakeLists.txt declares
cmake_minimum_required(VERSION 2.8.12), which CMake 4 refuses outright
unless CMAKE_POLICY_VERSION_MINIMUM is passed; that is a cache variable and
so would be legitimate here, but it makes the build's success depend on
which CMake the runner image happens to carry, and this first wave is meant
to prove the pattern rather than to test that.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# See xz_msvc.py for why these two variables and not CMAKE_C_FLAGS /
# CMAKE_SHARED_LINKER_FLAGS: CMake's MSVC Release default carries neither
# /Zi nor /DEBUG, so the artefact would come back with no PDB and no names,
# and overriding the per-configuration variables leaves CMake's own
# initialisation - /machine on the 32-bit leg among it - in place.
_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

# NMake Makefiles: nmake ships with MSVC itself, the generator is
# single-configuration so the DLL lands in the build root, and the target
# architecture comes from the developer environment the workflow sets up.
_CMAKE = ('cmake -S build/cmake -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON '
          '-DLZ4_BUILD_CLI=OFF %s %s' % (_CFLAGS, _LDFLAGS))


RECIPES = {
    "lz4_1.10.0_msvc": Recipe(
        family="lz4",
        version="1.10.0",
        upstream="https://github.com/lz4/lz4",
        license="BSD-2-Clause (library), GPL-2.0 (programs)",
        # The same immutable tag the MinGW recipe pins, and for the same
        # reason: upstream publishes no checksums for the release tarballs
        # and re-uploaded the 1.10.0 asset after publication.
        source=Source(git_url="https://github.com/lz4/lz4.git",
                      git_ref="v1.10.0"),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} --target lz4_shared"),
            # Cheap insurance, as in xz_msvc.py: build.py reports a missing
            # artefact by the path it expected, and this puts the names the
            # build actually wrote into the log the workflow prints.
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/lz4.dll", component="lz4.dll",
                            pdb="build-{arch}/lz4.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release, /Zi added); "
                    "/DEBUG /Brepro /OPT:NOREF /OPT:NOICF at link",
        notes="The DLL carries lz4.c, lz4hc.c, lz4frame.c, lz4file.c and "
              "xxhash.c, as the MinGW artefact does - upstream compiles "
              "xxHash into liblz4 and there is no xxHash family here to "
              "attribute it to. Built against the DLL runtime, so the MSVC C "
              "runtime is imported rather than linked in. Named lz4.dll "
              "rather than the MinGW build's liblz4.dll because MSVC has no "
              "library prefix; it is the same library and the same tag. The "
              "MinGW recipe builds -O3 from lib/Makefile, this one /O2 /Ob2 "
              "from CMake's MSVC Release, so the difference between the two "
              "artefacts is the compiler and its optimiser settings both.",
    ),
}
