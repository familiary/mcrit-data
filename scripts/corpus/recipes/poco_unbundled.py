"""POCO 1.15.4 with POCO_UNBUNDLED=ON - the decision variant for tracker #22.

poco.py builds Poco the way upstream ships it by default: zlib, pcre2, expat,
utf8proc and sqlite3 compiled from Poco's dependencies/ directory into the
Poco archives, so that image files 1122 (x64) functions of five other
projects under Poco's name. Tracker #22 asks for the bundled versus
POCO_UNBUNDLED decision before more Poco is built; this recipe is the other
side of that decision, built the same way in every other respect (same tag,
same 21 components, same -O3 RelWithDebInfo trick, same static archives
linked whole into one poco.dll), so the two images differ only in where the
third-party code lives.

Version string "1.15.4-unbundled". refresh_provenance.py resolves a record to
its recipe by (family, version) and then by toolchain, and both this and
poco.py are poco 1.15.4 on mingw_x86/mingw_x64, so the variant needs its own
version key. The source is the same tag, poco-1.15.4-release.

The external libraries are built from pinned upstream sources at the exact
versions Poco 1.15.4 bundles (dependencies/*/CMakeLists.txt names them), as
MinGW DLLs with import libraries, into a private prefix the Poco configure
is pointed at (CMAKE_PREFIX_PATH and CMAKE_FIND_ROOT_PATH). Shared rather
than static, because a Linux distribution's or a vcpkg-style unbundled
build links the system's shared libraries, and because a static archive
would put the reached third-party objects back inside poco.dll, which is
what this variant exists to avoid:

    zlib       1.3.2   zlib-1.3.2.tar.gz (zlib.net/fossils), CMake, shared only
    pcre2      10.48   pcre2-10.48.tar.bz2 (GitHub release), CMake, 8-bit, no JIT
    expat      2.8.5   expat-2.8.5.tar.xz (GitHub release R_2_8_5), CMake
    utf8proc   2.11.3  git tag v2.11.3 = e5e799221b45bbb90f5fdc5c69b6b8dfbf017e78
    sqlite3    3.53.4  sqlite-amalgamation-3530400.zip, one gcc -O2 -shared
                       line as in sqlite3.py, SQLITE_THREADSAFE=1 (what
                       Poco's unbundled CMake assumes)

All are built with the toolchain's compiler at their own CMake Release
defaults (-O3 for CMake projects); only poco.dll is recorded. zlib, pcre2
and sqlite3 are families of their own here (data/libzlib, data/pcre2,
data/sqlite3, at other versions); expat and utf8proc are not.

What stays bundled even when unbundled, read in the 1.15.4 CMake files:
double-conversion 3.4.0 and the header-only tessil ordered-map (Poco has no
unbundled switch for them), and two pcre2 files, pcre2_ucd.c and
pcre2_tables.c, which Foundation/CMakeLists.txt compiles into Foundation from
dependencies/pcre2 whenever the external pcre2 is not a static library
("HACK: Foundation Unicode.cpp requires functions from these files").

pcre2 import library. Poco's cmake/FindPCRE2.cmake decides the library type
from the last extension of PCRE2_LIBRARY: ".a" is CMAKE_STATIC_LIBRARY_SUFFIX
on MinGW, so the import library libpcre2-8.dll.a is taken for a static
pcre2, Foundation skips the two embedded pcre2 files, and every Poco
executable then fails to link (scratch run 42674927927, both architectures):

    ld: ../../lib/libPocoFoundation.a(Unicode.cpp.obj):Unicode.cpp:
    (.rdata$.refptr._pcre2_ucp_gentype_8[...]+0x0): undefined reference to
    `_pcre2_ucp_gentype_8'   (and _pcre2_ucd_records_8, _pcre2_ucd_stage1_8,
    _pcre2_ucd_stage2_8), in bin/f2cpsp.exe and bin/poco-arc.exe

The recipe copies the import library to libpcre2-8.implib in the private
prefix and passes that path as PCRE2_LIBRARY (and PCRE2_INCLUDE_DIR), so the
type is UNKNOWN, no PCRE2_STATIC is set, and Foundation takes the
"embedding internal sources" branch its CMake has for a shared pcre2. GNU ld
reads the import library under any name. Nothing in the Poco tree changes.

Final link: as poco.py, plus the five import libraries from the prefix.

Measured (scoped scratch run 42678836328, MinGW-w64 GCC 13.2.0-6ubuntu1+26.1
on ubuntu-24.04, the same packages as the host that built the bundled
poco.dll; the first attempt, run 42674927927, failed on the pcre2 type
detection above). Kept + removed by the MinGW glue baseline = image:

    x64  15702 + 164 = 15866   (bundled 1.15.4: 17630 + 170 = 17800)
    x86  30223 + 173 = 30396   (bundled 1.15.4: 30140 + 180 = 30320)

Against the bundled image, by recovered name: there are 14178 C++-named
functions in both on x64 (16445 bundled, 17209 unbundled on x86, which the bundled
x86 image's 10681 unnamed bodies make hard to compare); functions with a
plain C name fall from 2771 to 805 on x64 and from 2788 to 818 on x86, and
what is left of them is Poco's own static initialisers and long mangled
names SMDA did not demangle, plus 93 one-instruction import thunks into the
five dependency DLLs. No sqlite3, pcre2, expat, zlib or utf8proc body of 10
or more instructions remains (the one sqlite3-named function of 589/708
instructions is Poco's Poco::AnyCast<sqlite3*&>); pcre2_ucd.c and
pcre2_tables.c contribute tables, not functions. double-conversion stays:
120 functions on x64, 144 on x86.

PicHash overlap, distinct hashes of functions with 10+ instructions:

    unbundled against bundled   x64 7177 of 7421 (96.7%; bundled has 9136)
                                x86 8659 of 9501 (91.1%; bundled has 10970)
    bundled-only functions      x64 1745 plain-C (the vendored libraries)
                                    + 351 C++; x86 1787 + 575 + 99 unnamed
    unbundled-only functions    x64 352 C++ + 2 unnamed; x86 948 C++ + 3
                                    plain-C + 65 unnamed

The C++ functions that differ are Poco code whose call sites into the
dependencies became import calls; their bodies are otherwise the same
source.

Against the existing families (all MinGW versions in data/, x64 | x86):

    data/libzlib (247 | 247 hashes)    bundled 36 | 38    unbundled 1 | 3
    data/pcre2   (425 | 441)           bundled 61 | 65    unbundled 1 | 2
    data/sqlite3 (3911 | 4009)         bundled 217 | 236  unbundled 1 | 3

So the unbundled image is Poco's own code (plus double-conversion and
tessil) and shares essentially nothing with the zlib, pcre2 and sqlite3
families, while the bundled one files 314 (x64) and 339 (x86) of their
hashes under Poco. expat has no family here; the roughly 115 (x64) / 130
(x86) bundled-only functions of 10+ instructions whose names are expat's
leave the unbundled image as well.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_VERSIONS = {"zlib": "1.3.2", "pcre2": "10.48", "expat": "2.8.5",
             "sqlite": "3530400"}

_XCMAKE = ("-DCMAKE_SYSTEM_NAME=Windows -DCMAKE_SYSTEM_PROCESSOR={platform} "
           "-DCMAKE_C_COMPILER={cc} -DCMAKE_RC_COMPILER={windres} "
           "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
           "-DCMAKE_INSTALL_PREFIX=$PWD/deps-{arch}")


def _dep(src, build, options):
    return ("cmake -S %s -B %s %s %s && cmake --build %s -j$(nproc) && "
            "cmake --install %s" % (src, build, _XCMAKE, options, build, build))


_DEPS = [
    BuildStep("tar xf {zlib_archive} && " + _dep(
        "zlib-1.3.2", "b-zlib-{arch}",
        "-DZLIB_BUILD_STATIC=OFF -DZLIB_BUILD_TESTING=OFF")),
    BuildStep("tar xf {pcre2_archive} && " + _dep(
        "pcre2-10.48", "b-pcre2-{arch}",
        "-DBUILD_SHARED_LIBS=ON -DBUILD_STATIC_LIBS=OFF "
        "-DPCRE2_BUILD_PCRE2GREP=OFF -DPCRE2_BUILD_TESTS=OFF "
        "-DPCRE2_SUPPORT_JIT=OFF") +
        # See "pcre2 import library" in the docstring.
        " && cp deps-{arch}/lib/libpcre2-8.dll.a deps-{arch}/lib/libpcre2-8.implib"),
    BuildStep("tar xf {expat_archive} && " + _dep(
        "expat-2.8.5", "b-expat-{arch}",
        "-DEXPAT_SHARED_LIBS=ON -DEXPAT_BUILD_TOOLS=OFF "
        "-DEXPAT_BUILD_EXAMPLES=OFF -DEXPAT_BUILD_TESTS=OFF "
        "-DEXPAT_BUILD_DOCS=OFF")),
    BuildStep(_dep("{utf8proc_src}", "b-utf8proc-{arch}",
                   "-DBUILD_SHARED_LIBS=ON -DUTF8PROC_ENABLE_TESTING=OFF")),
    BuildStep("python3 -c \"import zipfile,sys;"
              "zipfile.ZipFile(sys.argv[1]).extractall('.')\" "
              "{sqlite_archive} && mkdir -p deps-{arch}/bin deps-{arch}/lib "
              "deps-{arch}/include && cd sqlite-amalgamation-3530400 && "
              "{cc} -O2 -shared -o ../deps-{arch}/bin/libsqlite3.dll sqlite3.c "
              "'-DSQLITE_API=__declspec(dllexport)' -DSQLITE_THREADSAFE=1 "
              "-Wl,--out-implib,../deps-{arch}/lib/libsqlite3.dll.a && "
              "cp sqlite3.h sqlite3ext.h ../deps-{arch}/include/"),
    BuildStep("find deps-{arch} -type f | sort", allow_failure=True),
]

_CMAKE = (
    "cmake -S . -B build-{arch} "
    "-DCMAKE_SYSTEM_NAME=Windows -DCMAKE_SYSTEM_PROCESSOR={platform} "
    "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx}-posix "
    "\"-DCMAKE_FIND_ROOT_PATH=/usr/{host};$PWD/deps-{arch}\" "
    "-DCMAKE_PREFIX_PATH=$PWD/deps-{arch} "
    "-DPCRE2_LIBRARY=$PWD/deps-{arch}/lib/libpcre2-8.implib "
    "-DPCRE2_INCLUDE_DIR=$PWD/deps-{arch}/include "
    "-DCMAKE_MC_COMPILER={prefix}windmc -DCMAKE_RC_COMPILER={windres} "
    "-DCMAKE_BUILD_TYPE=RelWithDebInfo "
    "-DCMAKE_C_FLAGS_RELWITHDEBINFO='-O3 -DNDEBUG' "
    "-DCMAKE_CXX_FLAGS_RELWITHDEBINFO='-O3 -DNDEBUG' "
    "-DBUILD_SHARED_LIBS=OFF "
    "-DENABLE_TESTS=OFF -DENABLE_SAMPLES=OFF "
    "-DENABLE_CRYPTO=OFF -DENABLE_NETSSL=OFF -DENABLE_JWT=OFF "
    "-DENABLE_DATA_MYSQL=OFF -DENABLE_DATA_ODBC=OFF "
    "-DENABLE_DATA_POSTGRESQL=OFF -DENABLE_APACHECONNECTOR=OFF "
    "-DENABLE_FASTLOGGER=OFF -DENABLE_PDF=OFF -DENABLE_SEVENZIP=OFF "
    "-DPOCO_UNBUNDLED=ON")

_LINK = ("printf 'int anchor(){return 0;}\\n' > anchor.cc && "
         "{cxx}-posix -std=c++20 -O2 -shared -o poco.dll anchor.cc "
         "-Wl,--whole-archive $(ls build-{arch}/lib/libPoco*.a | tr '\\n' ' ') "
         "-Wl,--no-whole-archive "
         "$(ls deps-{arch}/lib/*.dll.a | tr '\\n' ' ') "
         "-lmswsock -lws2_32 -liphlpapi -ladvapi32 -lcrypt32 -lole32 "
         "-loleaut32 -luuid -lwinpthread -shared-libgcc")

RECIPES = {
    "poco_1.15.4_unbundled": Recipe(
        family="poco",
        version="1.15.4-unbundled",
        upstream="https://github.com/pocoproject/poco",
        license="BSL-1.0",
        source=Source(git_url="https://github.com/pocoproject/poco.git",
                      git_ref="poco-1.15.4-release"),
        extra_sources={
            "zlib_archive": Source(
                url="https://zlib.net/fossils/zlib-1.3.2.tar.gz",
                sha256="bb329a0a2cd0274d05519d61c667c062e06990d72e125ee2dfa8de64f0119d16"),
            "pcre2_archive": Source(
                url="https://github.com/PCRE2Project/pcre2/releases/download/"
                    "pcre2-10.48/pcre2-10.48.tar.bz2",
                sha256="b6c68fdf6f3ac31388b50aa89ff0fc49c00c987c16e7b5146491d12003f2c8ed"),
            "expat_archive": Source(
                url="https://github.com/libexpat/libexpat/releases/download/"
                    "R_2_8_5/expat-2.8.5.tar.xz",
                sha256="1e727b8933ec51a77a9a9d9afcf8e688bce45d907c13e36ab7393fe36e703182"),
            "sqlite_archive": Source(
                url="https://www.sqlite.org/2026/sqlite-amalgamation-3530400.zip",
                sha256="1e71ddf93849c6a6ecf58b827c0692073d2dd7ee40196158068f7b29f422e87d"),
            "utf8proc_src": Source(
                git_url="https://github.com/JuliaStrings/utf8proc.git",
                git_ref="e5e799221b45bbb90f5fdc5c69b6b8dfbf017e78"),
        },
        build=_DEPS + [
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
            BuildStep(_LINK),
        ],
        artifacts=[Artifact(path="poco.dll", component="poco.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="POCO_UNBUNDLED=ON; -O3 -DNDEBUG -std=c++20 (CMake "
                    "RelWithDebInfo with Release's flags, as poco.py); static "
                    "Poco archives linked into one DLL with --whole-archive; "
                    "zlib 1.3.2, pcre2 10.48, expat 2.8.5, utf8proc 2.11.3 "
                    "and sqlite3 3.53.4 built from pinned sources as MinGW "
                    "DLLs and imported",
        notes="The POCO_UNBUNDLED side of the tracker #22 decision, beside "
              "the bundled poco_1.15.4: same tag, same 21 components and the "
              "same link shape, with Poco's five bundled dependencies "
              "replaced by external DLLs built from the exact versions Poco "
              "bundles. Only poco.dll is recorded; the dependency DLLs are "
              "not. double-conversion, tessil and pcre2_ucd.c/pcre2_tables.c "
              "remain compiled into Foundation, as Poco's CMake does in "
              "unbundled mode.",
    ),
}
