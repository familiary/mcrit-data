"""POCO C++ Libraries (mcrit-data issue #10).

A single DLL per architecture holding every Poco component that builds for
Windows without an external dependency: Foundation, XML, JSON, Util, Net, Zip,
Data and its SQLite connector, Encodings, MongoDB, Redis, Prometheus,
ActiveRecord, CppParser, CodeGeneration and the five RemotingNG libraries. 21
static archives linked into one image with ``--whole-archive``, the way
abseil.py, cryptopp.py and protobuf.py build theirs.

**The shared build does not work with GCC, and that is why this is one DLL
rather than twenty-one.** Poco explicitly instantiates several templates in
Foundation and marks them ``Foundation_API``: ``Poco::Dynamic::Struct``,
``Poco::BasicUnbufferedStreamBuf`` and ``Poco::BasicBufferedStreamBuf``. A
consumer therefore references their vtables and typeinfo as ``dllimport``,
but GCC does not export an explicit instantiation's vtable from a DLL the way
MSVC does, so ``PocoFoundation.dll`` never provides them. Measured rather than
assumed: with ``BUILD_SHARED_LIBS=ON`` the link fails for JSON on
``__imp__ZTVN4Poco7Dynamic6StructI...``, for Zip on
``__imp__ZTVN4Poco22BasicBufferedStreamBufI...`` and for Net on
``Poco::BasicUnbufferedStreamBuf<char, ...>::underflow()`` and its typeinfo.
Those three then block everything downstream of them - Util needs JSON, and
MongoDB, Redis, Prometheus and PageCompiler need Net - so a shared build
yields 9 components out of 21. The static build produces all 21 with no
failures at all, because nothing is imported or exported across the boundary.

What that costs is granularity: one artefact means the component field cannot
say which library a match landed in, and only the symbol name does. That is
the trade taken, and it is the same one abseil makes.

Two different counts appear below and they are not in conflict. The link
produces 21878 *text symbols* on x64, which is what ``nm`` reports over the
image; SMDA then recovers 17630 *functions* from it after this corpus drops
compiler runtime glue, and 12584 of those clear the ten-instruction census
floor. The symbol partition is the one that says where the code came from, so
it is given first; the artefact partition is in ``notes``.

The partition of the x64 image, 21878 text symbols, counted by symbol rather
than estimated:

    Poco's own                20137   92.0%
    Win32 import thunks         565    2.6%
    libstdc++ instantiations    335    1.5%
    sqlite3   (bundled)         256    1.2%
    compiler/CRT glue           244    1.1%
    pcre2     (bundled)         106    0.5%
    expat     (bundled)          87    0.4%
    zlib      (bundled)          63    0.3%
    double-conversion (bundled)  53    0.2%
    utf8proc  (bundled)          30    0.1%
    tessil    (bundled)           2

**597 of those symbols are bundled third-party code, and four of the projects
they come from are already families here** - sqlite3, pcre2, zlib and the
expat behind libxml2's neighbourhood. They are present because a real Poco
binary contains them: Poco vendors them under ``dependencies/`` and
``Poco::RegularExpression``, the deflating streams, the XML parser and the
SQLite connector are compiled against those copies, not against a system
library. That is BlackBone's situation exactly, where the vendored AsmJit and
rewolf-wow64ext sources are recorded under the BlackBone name because any real
BlackBone DLL carries them. The alternative, ``POCO_UNBUNDLED=ON``, needs
mingw builds of zlib, pcre2, expat and sqlite3, and none of those is packaged
for this toolchain. So the bundled code stays, and the count above is the
honest statement of how much of this artefact is not Poco.

Three groups are deliberately not built:

  * ``PDF`` and ``SevenZip``. Their bundled payloads are libharu with libpng,
    and the 7-Zip LZMA SDK - and libpng and 7-Zip are families of their own
    here, so including two thin Poco wrappers would file hundreds of
    functions of someone else's code under this name. The same judgement
    boost.py makes about the Iostreams codec filters.
  * ``Crypto``, ``NetSSL_OpenSSL`` and ``JWT`` need OpenSSL for the target,
    and ``Data``'s MySQL, ODBC and PostgreSQL connectors need their client
    libraries. OpenSSL is its own family here in any case.
  * ``FastLogger``, which is on by default and pulls in the bundled quill and
    fmtquill - 269 symbols of a separate upstream logging project, measured
    on a Foundation build with it enabled. It is an optional feature, so it
    is turned off rather than recorded under this name.

Four things upstream's CMake needs before it will cross-compile, all of them
command-line settings rather than edits:

  1. ``CMAKE_MC_COMPILER``. ``cmake/PocoMacros.cmake`` runs
     ``find_program(CMAKE_MC_COMPILER mc.exe ...)`` against Windows SDK
     directories, finds nothing on Linux and stops with "message compiler not
     found: required to build". It is a cache variable, so pre-seeding it
     skips the search, and GNU ``windmc`` takes the same ``-h <dir>``
     ``-r <dir> <file.mc>`` arguments the macro passes.
  2. ``CMAKE_SYSTEM_PROCESSOR``. The top-level CMakeLists dereferences it
     unquoted in ``if (${CMAKE_SYSTEM_PROCESSOR} STREQUAL "ARM64")``, which is
     a hard CMake error when the variable is empty - and setting
     ``CMAKE_SYSTEM_NAME`` without it leaves it empty.
  3. **The build type cannot be Release.**
     ``cmake/DefinePlatformSpecific.cmake`` does
     ``add_link_options($<$<CONFIG:Release>:-s>)`` for every non-Apple,
     non-MSVC compiler, which strips the COFF symbol table: a Release
     ``libPocoFoundation.dll`` came out with *zero* symbols, which SMDA cannot
     read and ``min_named_ratio`` would refuse. ``add_link_options`` appends
     and cannot be undone from the command line, but the generator expression
     names Release alone, so the build type is ``RelWithDebInfo`` with its
     flags overridden to ``-O3 -DNDEBUG``. That is Release's codegen with the
     symbols kept and no DWARF added. The same 6691-symbol Foundation build
     gave 0 under Release and 6691 under this.
  4. ``-lmswsock`` at the final link, for ``TransmitFile``, which
     ``Poco::Net`` calls and which lives there rather than in ws2_32.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CMAKE = (
    "cmake -S . -B build-{arch} "
    "-DCMAKE_SYSTEM_NAME=Windows -DCMAKE_SYSTEM_PROCESSOR={platform} "
    "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx}-posix "
    "-DCMAKE_FIND_ROOT_PATH=/usr/{host} "
    "-DCMAKE_MC_COMPILER={prefix}windmc -DCMAKE_RC_COMPILER={windres} "
    "-DCMAKE_BUILD_TYPE=RelWithDebInfo "
    "-DCMAKE_C_FLAGS_RELWITHDEBINFO='-O3 -DNDEBUG' "
    "-DCMAKE_CXX_FLAGS_RELWITHDEBINFO='-O3 -DNDEBUG' "
    "-DBUILD_SHARED_LIBS=OFF "
    "-DENABLE_TESTS=OFF -DENABLE_SAMPLES=OFF "
    "-DENABLE_CRYPTO=OFF -DENABLE_NETSSL=OFF -DENABLE_JWT=OFF "
    "-DENABLE_DATA_MYSQL=OFF -DENABLE_DATA_ODBC=OFF "
    "-DENABLE_DATA_POSTGRESQL=OFF -DENABLE_APACHECONNECTOR=OFF "
    "-DENABLE_FASTLOGGER=OFF -DENABLE_PDF=OFF -DENABLE_SEVENZIP=OFF")

# -shared-libgcc and never -static-libstdc++, for the reason the protobuf,
# abseil and boost recipes give: the static C++ runtime would add roughly
# 13500 libstdc++ and libgcc bodies to this sample under the Poco name. The
# Windows libraries are the ones Poco's own build links; mswsock is there for
# TransmitFile alone.
_LINK = ("printf 'int anchor(){return 0;}\\n' > anchor.cc && "
         "{cxx}-posix -std=c++20 -O2 -shared -o poco.dll anchor.cc "
         "-Wl,--whole-archive $(ls build-{arch}/lib/libPoco*.a | tr '\\n' ' ') "
         "-Wl,--no-whole-archive "
         "-lmswsock -lws2_32 -liphlpapi -ladvapi32 -lcrypt32 -lole32 "
         "-loleaut32 -luuid -lwinpthread -shared-libgcc")


RECIPES = {
    "poco_1.15.4": Recipe(
        family="poco",
        version="1.15.4",
        upstream="https://github.com/pocoproject/poco",
        license="BSL-1.0",
        source=Source(git_url="https://github.com/pocoproject/poco.git",
                      git_ref="poco-1.15.4-release"),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
            BuildStep(_LINK),
        ],
        artifacts=[Artifact(path="poco.dll", component="poco.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 -DNDEBUG -std=c++20 (CMake RelWithDebInfo with its "
                    "flags overridden to Release's, because Poco appends -s to "
                    "Release links and that strips the symbol table); static "
                    "libraries linked into one DLL with --whole-archive; "
                    "-O2 for the one-line anchor.cc link stub only",
        notes="Every Poco component that builds for Windows without an "
              "external dependency, in one image: Foundation, XML, JSON, Util, "
              "Net, Zip, Data with its SQLite connector, Encodings, MongoDB, "
              "Redis, Prometheus, ActiveRecord, CppParser, CodeGeneration and "
              "the five RemotingNG libraries. One DLL rather than one per "
              "component because GCC will not export the vtables of the "
              "templates Poco explicitly instantiates in Foundation, so a "
              "shared build cannot link JSON, Net or Zip and loses everything "
              "downstream of them; the static build produces all 21 archives "
              "with no failures. 21878 text symbols on x64, of which 20137 are "
              "Poco's own and 597 are bundled third-party: sqlite3 256, pcre2 "
              "106, expat 87, zlib 63, double-conversion 53, utf8proc 30, "
              "tessil 2. Four of those projects are families of their own "
              "here, and they are present because a real Poco binary contains "
              "them - Poco vendors them under dependencies/ and compiles "
              "RegularExpression, the deflating streams, the XML parser and "
              "the SQLite connector against those copies. As SMDA recovers "
              "them the artefacts hold 17630 functions on x64 and 30140 on "
              "x86, of which 12584 and 16175 clear the ten-instruction census "
              "floor; named Poco bodies are 13317 and 15532, bundled "
              "third-party 1122 and 1136. The x86 image carries 10681 unnamed "
              "bodies against x64's 483, which is measured and not yet "
              "explained. POCO_UNBUNDLED would "
              "need mingw builds of all four and none is packaged. PDF and "
              "SevenZip are not built, because their bundled libharu/libpng "
              "and LZMA SDK payloads would file hundreds of functions of two "
              "existing families under this name; Crypto, NetSSL and JWT need "
              "OpenSSL; FastLogger is off because it pulls in 269 symbols of "
              "the bundled quill. libstdc++ and libgcc are imported rather "
              "than linked, so no standard-library body is attributed here.",
    ),
}
