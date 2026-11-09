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

Final link: as poco.py, plus the five import libraries from the prefix.
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
        "-DPCRE2_SUPPORT_JIT=OFF")),
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
