"""libcurl built with MSVC, beside the MinGW builds of the same tags.

libcurl inside a downloader or a dropper is the archetypal MSVC-built
Windows dependency, and data/libcurl currently answers every one of those
sightings with GCC code. The survey ranks this third of thirty-one families
for coverage gained per unit of work.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

What was read rather than assumed, at both pinned tags:
  * ``lib/CMakeLists.txt`` sets ``PREFIX "" OUTPUT_NAME
    "${LIBCURL_OUTPUT_NAME}"`` on the shared target, and
    ``LIBCURL_OUTPUT_NAME`` defaults to ``libcurl``. The "lib" is part of the
    name rather than a platform prefix, so the DLL is ``libcurl.dll`` under
    MSVC exactly as it is under MinGW - unlike lz4, where dropping the prefix
    renamed the artefact. It lands in ``lib/`` under the build directory,
    which is where the MinGW recipe already looks.
  * ``cmake_minimum_required(VERSION 3.7...3.16)`` at both tags. The policy
    range reaches past 3.15, so CMP0091 is NEW and CMake selects the runtime
    library through ``CMAKE_MSVC_RUNTIME_LIBRARY`` - whose default is the DLL
    runtime - rather than by putting /MD in the flags. The /MD this recipe
    adds to ``CMAKE_C_FLAGS_RELEASE`` is therefore a duplicate under a NEW
    policy and the only source of it under an OLD one; either way the build
    is /MD, which is what matters.
  * ``CURL_STATIC_CRT`` exists at both tags and defaults to OFF, so nothing
    upstream flips this to /MT behind the recipe's back.
  * the OpenSSL default is computed as ``if(WIN32 OR CURL_USE_SCHANNEL OR …)
    set(_openssl_default OFF)``, so on Windows ``CURL_USE_OPENSSL`` is off
    before Schannel is even asked for, and ``find_package(OpenSSL)`` is never
    reached. That is checked rather than assumed because a windows runner
    does carry an OpenSSL, and libcurl absorbing it would put a second
    project's code under this family's name.
  * ``CURL_USE_LIBSSH2`` defaults to **ON** at both tags and
    ``USE_NGHTTP2`` defaults to ON at 8.15.0. Both are searched for with
    ``find_package``; neither was found in the cross environment the MinGW
    recipe configures in, which is why that recipe never had to name them.
    A windows-2022 runner is a different proposition - it carries vcpkg - and
    a found libssh2 or nghttp2 would be linked as a static .lib and absorbed.
    Both are switched off here explicitly.

Both configure lines were run through CMake (against the MinGW cross
compiler, which is what exists on this machine) and neither reported an
unused variable, so every option named below exists at both tags; both
reported "Enabled SSL backends: Schannel" and nothing else.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# See xz_msvc.py for why these two variables rather than CMAKE_C_FLAGS /
# CMAKE_SHARED_LINKER_FLAGS: CMake's MSVC Release default carries neither /Zi
# nor /DEBUG, so the artefact would come back with no PDB and no names, and
# overriding the per-configuration variables leaves CMake's own
# initialisation - /machine on the 32-bit leg among it - in place.
_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

# NMake Makefiles: nmake ships with MSVC itself, the generator is
# single-configuration so CMAKE_BUILD_TYPE means what it says, and the target
# architecture comes from the developer environment the workflow sets up.
#
# The option block is the MinGW recipe's, minus the cross-compilation
# variables and plus the two dependency switches read above. Schannel is what
# makes this family dependency-free: it is Windows' own TLS stack, so there
# is no OpenSSL, no mbedTLS and no certificate library to absorb, and it is
# also what a Windows build most often actually uses.
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release '
          '-DBUILD_SHARED_LIBS=ON -DCURL_USE_SCHANNEL=ON '
          '-DCURL_USE_LIBPSL=OFF -DCURL_ZLIB=OFF -DCURL_BROTLI=OFF '
          '-DCURL_ZSTD=OFF -DUSE_LIBIDN2=OFF -DCURL_USE_LIBSSH2=OFF '
          '-DUSE_NGHTTP2=OFF -DBUILD_TESTING=OFF -DBUILD_CURL_EXE=OFF '
          '%s %s' % (_CFLAGS, _LDFLAGS))


def _libcurl_msvc(version, git_ref):
    return Recipe(
        family="libcurl",
        version=version,
        upstream="https://github.com/curl/curl",
        license="curl (MIT-like)",
        source=Source(git_url="https://github.com/curl/curl.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            # BUILD_CURL_EXE and BUILD_TESTING are both off, so the default
            # target is the library and the two documentation targets; naming
            # a target here would only risk naming it wrongly.
            BuildStep("cmake --build build-{arch}"),
            # Cheap insurance, as in xz_msvc.py: build.py reports a missing
            # artefact by the path it expected and nothing else, and this
            # puts the names the build actually wrote into the log the
            # workflow prints on failure.
            BuildStep("dir build-{arch}\\lib", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/lib/libcurl.dll",
                            component="libcurl.dll",
                            pdb="build-{arch}/lib/libcurl.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release, /Zi added), "
                    "Schannel TLS backend; /DEBUG /Brepro /OPT:NOREF "
                    "/OPT:NOICF at link",
        notes="The same CMake options as the MinGW recipe for this version, "
              "so the two artefacts differ in the compiler rather than in the "
              "feature set. No dependencies: Schannel is Windows' own TLS "
              "stack, and zlib, brotli, zstd, libpsl, libidn2, libssh2 and "
              "nghttp2 are all switched off - the last two explicitly, "
              "because unlike the cross environment a windows runner may well "
              "have them and a found one would be absorbed as a static "
              "library. Built against the DLL runtime, so the MSVC C runtime "
              "is imported rather than linked in and stays attributed to "
              "data/MSVC. The MinGW recipe builds -O3, this one /O2 /Ob2 from "
              "CMake's MSVC Release, so the two differ in optimiser settings "
              "as well as in the code generator.",
    )


RECIPES = {
    # The same two tags the MinGW recipe pins, so each MSVC artefact sits
    # beside a MinGW one built from identical source.
    "libcurl_8.4.0_msvc": _libcurl_msvc("8.4.0", "curl-8_4_0"),
    "libcurl_8.15.0_msvc": _libcurl_msvc("8.15.0", "curl-8_15_0"),
}
