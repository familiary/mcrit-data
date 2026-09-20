"""Protocol Buffers - Google's serialization runtime.

Three releases, chosen where the C++ runtime was rebuilt rather than by
recency.

3.6.1 is the last of the 3.6 line and the generation a 2018-2020 binary
carries. Its wire parsing is still the old recursive one: parse_context.cc
and the EpsCopyInputStream rewrite only arrive in 3.11, and the table-driven
parser (generated_message_tctable_*) only in 3.19, so the hot path that
dominates any protobuf binary looks nothing like the later releases'.

21.12 is the last release before protobuf took a hard dependency on Abseil in
22.0, so it is self-contained, and it is the generation embedded in an
enormous amount of shipped software - it is what "protobuf 3.21.12" is, the
last of the 3.x numbering and still what many vendored copies and distro
packages carry.

31.1 is a current release and a materially different code base: everything
below the message classes is Abseil now (absl::string_view, absl::Cord,
absl::Mutex, the logging and status types), and utf8_range has been pulled in
as a vendored dependency. Anything in between is closer to one of these three
than they are to each other.

All three are built through upstream's CMake, and in every case the target is
libprotobuf, which is the full runtime and already contains every
libprotobuf-lite object - the lite archive would only duplicate it. How that
becomes a PE differs, because the releases differ in what a MinGW build can
produce:

  * 3.6.1 and 21.12 are built static and linked the way the cryptopp and
    abseil recipes link theirs, which is also how protobuf is usually
    embedded: SMDA cannot read a static archive, so libprotobuf.a goes into a
    DLL with --whole-archive, forcing every object in rather than only what
    an anchor happens to reference.
  * 31.1 is built shared, because that is what keeps Abseil out of a sample
    labelled protobuf: Abseil is built alongside as DLLs and libprotobuf.dll
    merely imports from it, so protobuf's own objects are all this artefact
    contains. The static route cannot do that here - ld ignores
    --unresolved-symbols on PE targets, so the re2 recipe's trick of leaving
    the Abseil references dangling is not available, and the only static
    alternative would have been to link Abseil's archives in and file some
    30000 Abseil functions under the protobuf name. A MinGW DLL is a usable
    artefact in 31.x because it sets CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS.

protoc is deliberately not built. It is a host tool, its code is the compiler
front end rather than the runtime library analysts meet inside a target, and
nobody ships a MinGW-cross-compiled protoc.exe.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Shared configure options. zlib support is off because zlib is its own family
# here and GzipInputStream would duplicate it; with it off, io/gzip_stream.cc
# compiles to nothing because its body is inside #ifdef HAVE_ZLIB. Tests are
# off because they need googletest and protoc, and INSTALL is off because
# nothing is installed from this tree.
_OPTIONS = ("-DCMAKE_SYSTEM_NAME=Windows -DCMAKE_C_COMPILER={cc} "
            "-DCMAKE_CXX_COMPILER={cxx}-posix "
            "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
            "-Dprotobuf_BUILD_TESTS=OFF -Dprotobuf_WITH_ZLIB=OFF "
            "-Dprotobuf_BUILD_PROTOC_BINARIES=OFF -Dprotobuf_INSTALL=OFF")

# 21.x still keeps a CMakeLists.txt under cmake/, but it only warns and
# includes the top-level one; the root project is what upstream documents from
# 21.0 onwards, so that is what is configured here.
_CMAKE_21 = "cmake -S . -B build-{arch} " + _OPTIONS

# 3.6 has no top-level CMakeLists.txt at all - cmake/ is the project - and no
# protobuf_INSTALL option, so the shared option list cannot be reused verbatim
# or CMake would warn about a variable the project never reads.
_CMAKE_36 = ("cmake -S cmake -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
             "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx}-posix "
             "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
             "-Dprotobuf_BUILD_TESTS=OFF -Dprotobuf_WITH_ZLIB=OFF "
             "-Dprotobuf_BUILD_PROTOC_BINARIES=OFF")

# -shared-libgcc, and never -static-libstdc++: linking the C++ runtime in
# would add roughly 13500 libstdc++ and libgcc functions to this sample and
# attribute them to protobuf. winpthread is the only library this archive
# needs beyond the CRT, because the posix-threads compiler puts std::mutex
# and std::once_flag there.
_LINK_21 = ("echo 'int anchor(){return 0;}' > anchor.cc && "
            "{cxx}-posix -std=c++11 -O2 -shared -o protobuf.dll anchor.cc "
            "-Wl,--whole-archive build-{arch}/libprotobuf.a "
            "-Wl,--no-whole-archive -lwinpthread -shared-libgcc")

# 31.x resolves Abseil through find_package first and falls back to cloning it
# from GitHub during the configure step. Neither is acceptable here: the first
# would build against whatever the host happens to have installed, the second
# records nothing. FORCE_FETCH_DEPENDENCIES takes the FetchContent branch and
# FETCHCONTENT_SOURCE_DIR_ABSL points it at the pinned checkout, so no network
# access happens and the Abseil release is in provenance.json.
# libupb is off because upb is the C runtime behind the Python, PHP and Ruby
# bindings rather than part of the C++ library this artefact stands for.
# BUILD_SHARED_LIBS makes both protobuf and Abseil DLLs, which is what keeps
# Abseil's object code out of an artefact labelled protobuf; -shared-libgcc is
# stated rather than relied on, because -static-libstdc++ would add roughly
# 13500 libstdc++ and libgcc functions to this sample.
_CMAKE_31 = ("cmake -S . -B build-{arch} " + _OPTIONS + " "
             "-DCMAKE_CXX_STANDARD=17 -Dprotobuf_BUILD_LIBUPB=OFF "
             "-Dprotobuf_BUILD_SHARED_LIBS=ON "
             "-DCMAKE_SHARED_LINKER_FLAGS=-shared-libgcc "
             "-Dprotobuf_FORCE_FETCH_DEPENDENCIES=ON "
             "-DFETCHCONTENT_SOURCE_DIR_ABSL={absl}")


RECIPES = {
    # The generation before the parser rewrite, and what a 2018-2020 vintage
    # binary carries.
    "protobuf_3.6.1": Recipe(
        family="protobuf",
        version="3.6.1",
        upstream="https://github.com/protocolbuffers/protobuf",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/protocolbuffers/protobuf.git",
                      git_ref="v3.6.1"),
        build=[
            BuildStep(_CMAKE_36),
            BuildStep("cmake --build build-{arch} -j$(nproc) --target libprotobuf"),
            BuildStep(_LINK_21),
        ],
        artifacts=[Artifact(path="protobuf.dll", component="protobuf.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        # See the 21.12 entry for why Release means -O3 here. HAVE_PTHREAD is
        # 3.6's own define, set because CMake found a thread library, and it
        # is what selects the pthread mutex implementation over the Win32 one.
        build_flags="-O3 -DNDEBUG -std=c++11 -DGOOGLE_PROTOBUF_CMAKE_BUILD "
                    "-DHAVE_PTHREAD (CMake Release, all protobuf code); "
                    "-O2 for the anchor.cc link stub only",
        notes="Full C++ runtime (libprotobuf, which also contains every "
              "libprotobuf-lite object). No zlib: GzipInputStream/"
              "GzipOutputStream are compiled out, because zlib is a family of "
              "its own here. No protoc or libprotoc, so the compiler front end "
              "and the code generators are absent. Built with the "
              "posix-threads compiler, because the win32-threads <mutex> is "
              "unusable.",
    ),
    # Last release before the Abseil dependency, and the generation embedded
    # in most of what is in the field.
    "protobuf_21.12": Recipe(
        family="protobuf",
        version="21.12",
        upstream="https://github.com/protocolbuffers/protobuf",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/protocolbuffers/protobuf.git",
                      git_ref="v21.12"),
        build=[
            BuildStep(_CMAKE_21),
            BuildStep("cmake --build build-{arch} -j$(nproc) --target libprotobuf"),
            BuildStep(_LINK_21),
        ],
        artifacts=[Artifact(path="protobuf.dll", component="protobuf.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        # Every object that ends up in the sample comes from the CMake Release
        # build, and protobuf sets no CMAKE_CXX_FLAGS_RELEASE of its own - its
        # only flag surgery is the MSVC /MD -> /MT replacement - so Release is
        # CMake's GNU default of -O3 -DNDEBUG. The -O2 line applies to the
        # three-line anchor.cc stub the archive is linked around and nothing
        # else.
        build_flags="-O3 -DNDEBUG -std=c++11 -DGOOGLE_PROTOBUF_CMAKE_BUILD "
                    "(CMake Release, all protobuf code); -O2 for the anchor.cc "
                    "link stub only",
        notes="Full C++ runtime (libprotobuf, which also contains every "
              "libprotobuf-lite object). No zlib: GzipInputStream/"
              "GzipOutputStream are compiled out, because zlib is a family of "
              "its own here. No protoc or libprotoc, so the compiler front end "
              "and the code generators are absent. Built with the "
              "posix-threads compiler, because the win32-threads <mutex> is "
              "unusable.",
    ),
    # Current release, and Abseil-based throughout.
    "protobuf_31.1": Recipe(
        family="protobuf",
        version="31.1",
        upstream="https://github.com/protocolbuffers/protobuf",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/protocolbuffers/protobuf.git",
                      git_ref="v31.1"),
        extra_sources={
            # The release cmake/dependencies.cmake names for this tag. Pinned
            # even though no Abseil object code is linked in, because which
            # Abseil supplied the headers decides what inline and template
            # code ended up in the artefact.
            "absl": Source(git_url="https://github.com/abseil/abseil-cpp.git",
                           git_ref="20250127.0"),
        },
        build=[
            BuildStep(_CMAKE_31),
            # utf8_validity and the Abseil libraries libprotobuf links against
            # are built as dependencies of this one target; nothing else in
            # the tree is.
            BuildStep("cmake --build build-{arch} -j$(nproc) --target libprotobuf"),
        ],
        artifacts=[Artifact(path="build-{arch}/libprotobuf.dll",
                            component="protobuf.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        # As for 21.12: protobuf sets no CMAKE_CXX_FLAGS_RELEASE, so every
        # object in the sample is built with CMake's GNU Release default. The
        # standard is fixed by the targets themselves (cxx_std_17), not by the
        # command line. The two DLL defines are what the shared build adds.
        build_flags="-O3 -DNDEBUG -std=c++17 -DGOOGLE_PROTOBUF_CMAKE_BUILD "
                    "-DPROTOBUF_USE_DLLS -DLIBPROTOBUF_EXPORTS "
                    "(CMake Release, shared build)",
        notes="Upstream's own libprotobuf DLL: the full C++ runtime, which "
              "also contains every libprotobuf-lite object. Abseil and the "
              "vendored utf8_range are built alongside as DLLs and only "
              "imported, so no Abseil or utf8_range object code is attributed "
              "to protobuf; what is present is the Abseil inline and template "
              "code protobuf instantiates, as it would be in any protobuf "
              "binary - that is why some 15 per cent of the functions here "
              "demangle to absl names, most of them raw_hash_set and Status "
              "instantiations over protobuf's own types. No zlib, because "
              "zlib is a family of its own here. No "
              "protoc, libprotoc or libupb, so the compiler front end, the "
              "code generators and the C runtime behind the non-C++ bindings "
              "are absent. Built with the posix-threads compiler, because the "
              "win32-threads <mutex> is unusable.",
    ),
}
