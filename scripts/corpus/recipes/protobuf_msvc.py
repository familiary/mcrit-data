"""Protocol Buffers built with MSVC, beside the MinGW builds of the same tags.

Protobuf inside Windows software is overwhelmingly MSVC-built and usually
statically linked, which is exactly the sighting this corpus exists to
answer, and data/protobuf carries only GCC code. C++ is also where the two
compilers diverge most - name mangling, exception tables, vtable and thunk
shapes and template instantiation all differ - so the MinGW artefacts match
an MSVC protobuf far more weakly than they would for a C library.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

**Abseil.** The MinGW recipe's arrangement for 31.1 carries across and gets
easier: protobuf is built shared so Abseil is built alongside as a shared
library and merely *imported*, which is what keeps some 30000 Abseil
functions out of an artefact labelled protobuf. Read in the pinned trees:

  * protobuf 31.1's CMakeLists.txt, under ``if (protobuf_BUILD_SHARED_LIBS)``,
    does ``set(BUILD_SHARED_LIBS ON)`` with the comment "Build Abseil as
    shared libraries to avoid ODR violations", and sets
    CMAKE_RUNTIME_OUTPUT_DIRECTORY / CMAKE_PDB_OUTPUT_DIRECTORY to
    ``${CMAKE_BINARY_DIR}/bin`` **under MSVC only** - which is why this
    recipe's artefact path has a bin/ in it where the MinGW one does not.
  * Abseil 20250127.0's ``absl/copts/AbseilConfigureCopts.cmake`` then does
    ``if (BUILD_SHARED_LIBS AND (MSVC OR ABSL_BUILD_MONOLITHIC_SHARED_LIBS))
    set(ABSL_BUILD_DLL TRUE); set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)``, and
    ``absl/CMakeLists.txt`` calls ``absl_make_dll()`` under that flag. So
    under MSVC the monolithic ``abseil_dll`` is upstream's own default for a
    shared build and needs no help - the export problem the re2 and MinGW
    protobuf recipes had to solve does not arise here at all.
  * protobuf 31.1 also sets ``CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON`` for
    itself at top level.

**Versions.** 21.12 and 31.1 only.

3.6.1 is dropped, and on a rule this corpus has already applied three times
rather than on a guess: ``cmake/CMakeLists.txt`` at v3.6.1 declares
``cmake_minimum_required(VERSION 3.1.3)``, and CMake 4 refuses a project
asking for less than 3.5 outright. That is the rule that already held back
lz4 1.9.4, mbedTLS 2.28.10 and libtiff 4.0.10. It is passable with
CMAKE_POLICY_VERSION_MINIMUM, as cJSON and libevent do where dropping the
version would lose the only coverage of a code generation - but here it would
not: 21.12 and 31.1 already cover two very different protobufs, and 3.6.1
carries a second, independent risk that could not be measured from here, that
2018 C++11 code compiles under v143 at all. Two avoidable risks for a third
version of a family that already has two is not a trade worth making.
Recorded rather than silently skipped, because the MinGW side does cover it.

**What else was read rather than assumed:**
  * both releases define ``LIB_PREFIX`` to ``lib`` under MSVC and set the
    libprotobuf target's OUTPUT_NAME to ``${LIB_PREFIX}protobuf``, so the DLL
    is ``libprotobuf.dll`` under both compilers - the same name, by two
    different routes (MinGW's "lib" library prefix, MSVC's explicit one).
    VERSION/SOVERSION do not reach a file name on Windows.
  * 21.12 sets no output directory of its own, so its DLL and the linker PDB
    land in the build root.
  * 21.12 declares ``cmake_minimum_required(VERSION 3.5)``, so CMP0091 is OLD
    and the ``/MD`` this recipe puts in CMAKE_CXX_FLAGS_RELEASE is the only
    thing selecting the DLL runtime. 31.1 declares ``3.16...3.26``, so
    CMP0091 is NEW, CMAKE_MSVC_RUNTIME_LIBRARY governs and defaults to
    MultiThreadedDLL, and the same ``/MD`` is a harmless duplicate. Either
    way the build is /MD. Both releases would replace /MD with /MT under
    ``protobuf_MSVC_STATIC_RUNTIME``, but that option is a
    cmake_dependent_option forced OFF whenever protobuf_BUILD_SHARED_LIBS is
    on, so a shared build cannot reach it.
  * 31.1 sets ``cmake_policy(SET CMP0141 OLD)`` explicitly and 21.12's 3.5
    floor leaves it OLD, so in both the debug information format comes from
    the compile flags - i.e. the ``/Zi`` below is what produces a PDB.
  * 31.1's ``protobuf_ALLOW_CCACHE`` branch strips /Zi, but only from the
    Debug and RelWithDebInfo flag variables, and it defaults off.
  * upstream adds ``/MP`` and ``/bigobj`` itself, along with a list of /wd
    suppressions and (21.12 onwards) ``/utf-8``. None of that is displaced by
    overriding the per-configuration flag variables.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# See xz_msvc.py for why these two variables rather than CMAKE_CXX_FLAGS /
# CMAKE_SHARED_LINKER_FLAGS: CMake's MSVC Release default carries neither /Zi
# nor /DEBUG, so the artefact would come back with no PDB and, MSVC keeping
# its symbols there rather than in a COFF symbol table, no function names
# either - which smdaify rejects. Overriding the per-configuration variables
# leaves CMake's own initialisation, /machine on the 32-bit leg among it, in
# place.
#
# /DEBUG so a PDB is written at all, /Brepro so the PE carries no build
# timestamp and two runs of identical source record the same sha256, and
# /OPT:NOREF /OPT:NOICF so unreferenced and identically-compiled routines both
# survive as separate reference samples - a serialization runtime is full of
# near-twin template instantiations, which is exactly what ICF folds.
# /INCREMENTAL:NO is CMake's own Release default and is restated because
# setting the variable replaces it.
_CXXFLAGS = '-DCMAKE_CXX_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

# NMake Makefiles: nmake ships with MSVC itself, the generator is
# single-configuration so CMAKE_BUILD_TYPE means what it says and the
# artefacts land where the recipe says rather than under a Release/
# subdirectory, and the target architecture comes from the developer
# environment the workflow set up.
#
# zlib support is off because zlib is its own family here and GzipInputStream
# would duplicate it; with it off, io/gzip_stream.cc compiles to nothing
# because its body is inside #ifdef HAVE_ZLIB. Tests are off because they
# need googletest and protoc; INSTALL is off because nothing is installed
# from this tree; protoc itself is not built because it is a host tool whose
# code is the compiler front end rather than the runtime library analysts
# meet inside a target.
_OPTIONS = ("-G \"NMake Makefiles\" -DCMAKE_BUILD_TYPE=Release "
            "-Dprotobuf_BUILD_TESTS=OFF -Dprotobuf_WITH_ZLIB=OFF "
            "-Dprotobuf_BUILD_PROTOC_BINARIES=OFF -Dprotobuf_INSTALL=OFF "
            "-Dprotobuf_BUILD_SHARED_LIBS=ON "
            + _CXXFLAGS + " " + _LDFLAGS)

_CMAKE_21 = "cmake -S . -B build-{arch} " + _OPTIONS

# 31.x resolves Abseil through find_package first and falls back to cloning it
# from GitHub during the configure step. Neither is acceptable here: the first
# would build against whatever the runner happens to have installed, the
# second records nothing. FORCE_FETCH_DEPENDENCIES takes the FetchContent
# branch and FETCHCONTENT_SOURCE_DIR_ABSL points it at the pinned checkout, so
# no network access happens and the Abseil release is in provenance.json.
# libupb is off because upb is the C runtime behind the Python, PHP and Ruby
# bindings rather than part of the C++ library this artefact stands for.
_CMAKE_31 = ("cmake -S . -B build-{arch} " + _OPTIONS + " "
             "-DCMAKE_CXX_STANDARD=17 -Dprotobuf_BUILD_LIBUPB=OFF "
             "-Dprotobuf_FORCE_FETCH_DEPENDENCIES=ON "
             "-DFETCHCONTENT_SOURCE_DIR_ABSL={absl}")


RECIPES = {
    # Last release before the Abseil dependency, so it is self-contained, and
    # the generation embedded in an enormous amount of shipped software.
    "protobuf_21.12_msvc": Recipe(
        family="protobuf",
        version="21.12",
        upstream="https://github.com/protocolbuffers/protobuf",
        license="BSD-3-Clause",
        # The same tag the MinGW recipe pins.
        source=Source(git_url="https://github.com/protocolbuffers/protobuf.git",
                      git_ref="v21.12"),
        build=[
            BuildStep(_CMAKE_21),
            BuildStep("cmake --build build-{arch} --target libprotobuf"),
            # Cheap insurance, as in xz_msvc.py: build.py reports a missing
            # artefact by the path it expected and nothing else.
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/libprotobuf.dll",
                            component="protobuf.dll",
                            pdb="build-{arch}/libprotobuf.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release, /Zi added), plus "
                    "upstream's /MP /bigobj /utf-8 and its /wd list; "
                    "PROTOBUF_USE_DLLS and LIBPROTOBUF_EXPORTS defined by the "
                    "shared build; /DEBUG /Brepro /OPT:NOREF /OPT:NOICF at "
                    "link",
        notes="Upstream's own libprotobuf DLL: the full C++ runtime, which "
              "also contains every libprotobuf-lite object. Where the MinGW "
              "artefact of this version is a static archive forced into a DLL "
              "with --whole-archive, this is the shared build upstream "
              "supports under MSVC through its PROTOBUF_USE_DLLS / "
              "LIBPROTOBUF_EXPORTS macros; /OPT:NOREF is what keeps the "
              "objects nothing exports from being dropped, so the two "
              "artefacts cover the same code. No zlib, because zlib is a "
              "family of its own here. No protoc or libprotoc, so the "
              "compiler front end and the code generators are absent. Built "
              "against the DLL runtime, so the MSVC C runtime is imported "
              "rather than linked in - but note this is a C++ artefact, so "
              "the MSVC STL instantiations compiled into it are attributed "
              "here, and the C++ side of the glue baseline is the narrowest "
              "part of it.",
    ),
    # Current release, and Abseil-based throughout.
    "protobuf_31.1_msvc": Recipe(
        family="protobuf",
        version="31.1",
        upstream="https://github.com/protocolbuffers/protobuf",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/protocolbuffers/protobuf.git",
                      git_ref="v31.1"),
        extra_sources={
            # The release cmake/dependencies.cmake names for this tag, and the
            # same pin the MinGW recipe uses. Pinned even though no Abseil
            # object code is linked in, because which Abseil supplied the
            # headers decides what inline and template code ended up in the
            # artefact.
            "absl": Source(git_url="https://github.com/abseil/abseil-cpp.git",
                           git_ref="20250127.0"),
        },
        build=[
            BuildStep(_CMAKE_31),
            # utf8_validity and abseil_dll are built as dependencies of this
            # one target; nothing else in the tree is.
            BuildStep("cmake --build build-{arch} --target libprotobuf"),
            BuildStep("dir build-{arch}\\bin", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/bin/libprotobuf.dll",
                            component="protobuf.dll",
                            pdb="build-{arch}/bin/libprotobuf.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi /std:c++17 (CMake Release, /Zi added), "
                    "plus upstream's /MP /bigobj /utf-8 and its /wd list; "
                    "PROTOBUF_USE_DLLS and LIBPROTOBUF_EXPORTS defined by the "
                    "shared build; /DEBUG /Brepro /OPT:NOREF /OPT:NOICF at "
                    "link",
        notes="Upstream's own libprotobuf DLL: the full C++ runtime, which "
              "also contains every libprotobuf-lite object. Abseil is built "
              "alongside as the monolithic abseil_dll that upstream's own "
              "CMake selects for a shared MSVC build, and the vendored "
              "utf8_range likewise as a shared library, so neither "
              "contributes object code to an artefact labelled protobuf; "
              "what is present is the Abseil inline and template code "
              "protobuf instantiates, as it would be in any protobuf binary. "
              "No zlib, because zlib is a family of its own here. No protoc, "
              "libprotoc or libupb, so the compiler front end, the code "
              "generators and the C runtime behind the non-C++ bindings are "
              "absent. Built against the DLL runtime, so the MSVC C runtime "
              "is imported rather than linked in - but this is a C++ "
              "artefact, so the MSVC STL instantiations compiled into it are "
              "attributed here.",
    ),
}
