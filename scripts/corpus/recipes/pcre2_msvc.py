"""PCRE2 built with MSVC, beside the MinGW builds of the same tags.

PCRE2 is in a great deal of current software and the Windows copies of it are
MSVC-built; data/pcre2 carries only MinGW artefacts.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

What was read rather than assumed, in CMakeLists.txt at both tags:
  * ``BUILD_SHARED_LIBS`` defaults to **OFF** and ``BUILD_STATIC_LIBS`` to
    **ON**, so an unmodified configure produces the static ``pcre2-8.lib``
    that SMDA cannot read. Both are named explicitly here.
  * the shared target is ``pcre2-8-shared`` with ``OUTPUT_NAME pcre2-8``, and
    the ``PREFIX ""`` override is inside ``if(MINGW)`` at both tags. MSVC has
    no library prefix of its own, so the file is **pcre2-8.dll**, where the
    MinGW artefact is libpcre2-8.dll. The component is recorded as the name
    this build produces.
  * 10.45 names the PDB itself: ``set(DLL_PDB_FILES
    $<TARGET_PDB_FILE_DIR:pcre2-8-shared>/pcre2-8.pdb …)``, which is CMake's
    own rule (the runtime artefact's prefix and base name, in the runtime
    output directory) written out by upstream. 10.39 has no such line but the
    target is shaped identically, so the PDB is pcre2-8.pdb there too.
  * ``pcre2-posix-shared`` is a second, separate DLL that links against this
    one. It is not built: ``--target pcre2-8-shared`` keeps the build to the
    engine, which is the only thing data/pcre2 holds.
  * ``if(MSVC) add_compile_definitions(_CRT_SECURE_NO_DEPRECATE
    _CRT_SECURE_NO_WARNINGS)`` is upstream's, at both tags; nothing here has
    to ask for it.

The two versions do **not** configure alike, and the difference is exactly
the one the corpus has been bitten by:

  * 10.45 declares ``cmake_minimum_required(VERSION 3.15 FATAL_ERROR)``, so
    CMP0091 is NEW and CMake picks the runtime library through
    ``CMAKE_MSVC_RUNTIME_LIBRARY``, which defaults to the DLL runtime.
  * 10.39 declares ``CMAKE_MINIMUM_REQUIRED(VERSION 3.0.0)``. CMP0091 is
    therefore **OLD**, CMake writes the runtime flag into
    ``CMAKE_C_FLAGS_<CONFIG>`` - and this recipe replaces that variable
    wholesale. Without the /MD spelled out in it, 10.39 would silently come
    back /MT and its artefact would be half MSVC C runtime.

``-DCMAKE_POLICY_VERSION_MINIMUM=3.5`` covers the other half of that: CMake
4 refuses a ``cmake_minimum_required`` below 3.5 outright, which is what
lz4_msvc.py declined to work around for lz4 1.9.4. The reasoning differs here
because the conclusion can be checked: the variable was measured on CMake
3.28 against both of these trees and is simply reported as unused, the
configure succeeding as before. So it costs a warning line on a CMake that
does not need it and saves the family on a CMake that does - unlike lz4,
where a newer tag was available that needed neither.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# See xz_msvc.py for why these two variables rather than CMAKE_C_FLAGS /
# CMAKE_SHARED_LINKER_FLAGS: CMake's MSVC Release default carries neither /Zi
# nor /DEBUG, so the artefact would come back with no PDB and no names, and
# overriding the per-configuration variables leaves CMake's own
# initialisation - /machine on the 32-bit leg among it - in place. The /MD in
# it is load-bearing for 10.39, as the docstring explains.
_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

# NMake Makefiles: nmake ships with MSVC itself, the generator is
# single-configuration so the DLL lands in the build root, and the target
# architecture comes from the developer environment the workflow sets up.
#
# JIT is on for the same reason the MinGW recipe turns it on: it is what
# distributions and vendored copies ship, and it is a large and distinctive
# body of code. BUILD_STATIC_LIBS=OFF is not only tidiness - it halves the
# compile, since upstream would otherwise build every source twice.
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
          '-DCMAKE_BUILD_TYPE=Release '
          '-DBUILD_SHARED_LIBS=ON -DBUILD_STATIC_LIBS=OFF '
          '-DPCRE2_SUPPORT_JIT=ON -DPCRE2_BUILD_TESTS=OFF '
          '-DPCRE2_BUILD_PCRE2GREP=OFF %s %s' % (_CFLAGS, _LDFLAGS))


def _pcre2_msvc(version, git_ref):
    return Recipe(
        family="pcre2",
        version=version,
        upstream="https://github.com/PCRE2Project/pcre2",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/PCRE2Project/pcre2.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} --target pcre2-8-shared"),
            # Cheap insurance, as in xz_msvc.py: build.py reports a missing
            # artefact by the path it expected and nothing else, and this
            # puts the names the build actually wrote into the log the
            # workflow prints on failure.
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/pcre2-8.dll",
                            component="pcre2-8.dll",
                            pdb="build-{arch}/pcre2-8.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release, /Zi added), JIT "
                    "enabled; /DEBUG /Brepro /OPT:NOREF /OPT:NOICF at link",
        notes="The same CMake options as the MinGW recipe for this version, "
              "with JIT on, so the two artefacts differ in the compiler "
              "rather than in the feature set. Named pcre2-8.dll rather than "
              "the MinGW build's libpcre2-8.dll because upstream applies the "
              "empty library prefix only under MINGW and MSVC has none of its "
              "own; it is the same library and the same tag. Only the 8-bit "
              "engine is built - pcre2-posix is a separate DLL and is not in "
              "this family. No dependencies: PCRE2 links only the CRT, and is "
              "built against the DLL runtime so the MSVC C runtime is "
              "imported rather than linked in and stays attributed to "
              "data/MSVC. The MinGW recipe builds -O3, this one /O2 /Ob2 from "
              "CMake's MSVC Release.",
    )


RECIPES = {
    # The same two tags the MinGW recipe pins, so each MSVC artefact sits
    # beside a MinGW one built from identical source. 10.39 is before the
    # 10.43 compile/JIT rework; 10.45 is current.
    "pcre2_10.39_msvc": _pcre2_msvc("10.39", "pcre2-10.39"),
    "pcre2_10.45_msvc": _pcre2_msvc("10.45", "pcre2-10.45"),
}
