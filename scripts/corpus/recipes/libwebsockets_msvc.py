"""libwebsockets built with MSVC, beside the MinGW builds of the same tags.

The same four tags as libwebsockets.py (v4.0.21, v4.3.10, v4.5.8, v5.1.0),
the same feature switches and the same TLS backend: OpenSSL 1.1.1w, as a
separate DLL. Only the compiler differs, so the two axes can be compared
function by function. A separate registry entry rather than another toolchain
on the MinGW recipe because one Recipe has one build list and these steps are
cmd.exe, not sh.

OpenSSL. The archive is the one libwebsockets.py and openssl.py pin (same
sha256) and it is configured exactly as recipes/openssl_msvc.py configures it
(`perl Configure VC-WIN64A|VC-WIN32 shared no-tests no-asm no-makedepend`,
`nmake build_libs`; the two Configure lines are imported from there, not
restated). It is unpacked and built under the output directory, outside the
libwebsockets tree, because 4.3.10 and later reject an include directory that
lies inside their own source directory. libwebsockets is then linked against
the two import libraries that build writes (libssl.lib, libcrypto.lib), so the
DLL imports libssl-1_1[-x64].dll and libcrypto-1_1[-x64].dll and none of
OpenSSL's code is in the artefact; see data/OpenSSL for that code. The runner
image carries an OpenSSL of its own (3.x, under Program Files) and Strawberry
Perl ships a pkg-config with a MinGW openssl.pc; neither is used. Passing
LWS_OPENSSL_LIBRARIES and LWS_OPENSSL_INCLUDE_DIRS, upstream's documented
override, sets OPENSSL_FOUND before lib/tls/CMakeLists.txt (CMakeLists.txt at
4.0.21) reaches its pkg_check_modules/find_package(OpenSSL) block, so that
block does not run.

All four recipes of one leg use the same OpenSSL build: the first one to run
builds it and writes built.ok beside it, the others find that file and skip
the five OpenSSL steps. The marker is written only after `nmake build_libs`
returned 0, and a tree without it is deleted and rebuilt, so a half-built
OpenSSL is never reused. Source, flags and compiler are identical for all
four, so this saves three OpenSSL builds per leg and changes nothing else.

Flags only, upstream untouched:
  * CMAKE_C_FLAGS_RELEASE / CMAKE_SHARED_LINKER_FLAGS_RELEASE as in
    libevent_msvc.py: /MD /O2 /Ob2 /DNDEBUG /Zi, and /INCREMENTAL:NO /DEBUG
    /Brepro /OPT:NOREF /OPT:NOICF at link. 4.5.8 and 5.1.0 also set
    CMAKE_MSVC_RUNTIME_LIBRARY to MultiThreadedDLL themselves
    (LWS_MSVC_STATIC_RUNTIME is OFF by default), so /MD is there twice.
  * `_CL_=/WX-`. 4.3.10 and 4.5.8 do add_compile_options(/W3 /WX) for MSVC
    unconditionally (DISABLE_WERROR only gates the GCC -Werror there; 5.1.0
    gates /WX on it too, 4.0.21 has no /WX). cl appends the _CL_ environment
    variable to its command line, so /WX- comes last and wins; this is the
    MSVC spelling of the MinGW recipe's -Wno-error and changes no code.
  * `CL=/I<openssl>/include`, the counterpart of the -I the MinGW recipe puts
    in CMAKE_C_FLAGS so that lws' check_c_source_compiles probes of the
    OpenSSL API see the headers. cl prepends CL to its command line.
  * The LWS_* switches are the MinGW recipe's, unchanged, including the four
    5.x ones (_CMAKE_V5 is imported): LWS_WITH_SCHANNEL=OFF keeps the TLS
    backend OpenSSL on 5.1.0, where SChannel is the Windows default;
    LWS_HAVE_PTHREAD_H=0, LWS_WITH_SPAWN=OFF and LWS_WITH_HTTP3=OFF are not
    needed by MSVC but keep the feature set equal to the MinGW image.
  * CMAKE_POLICY_VERSION_MINIMUM=3.5 is insurance for 4.0.21 and 4.3.10
    (cmake_minimum_required 2.8.9 / 2.8.12) against a CMake 4 on the runner;
    the CMake the image carries today (3.31) ignores it.

The DLL is websockets.dll, not libwebsockets.dll: the target's OUTPUT_NAME is
"websockets" and MSVC has no "lib" prefix. The component records the name the
build produces, as libevent_msvc.py does.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from .libwebsockets import _CMAKE_V5, _OPENSSL_SHA256, _OPENSSL_VERSION
from .openssl_msvc import _CONFIGURE_X64, _CONFIGURE_X86


# Where OpenSSL is unpacked and built: under the output directory, one tree
# per architecture, shared by the four recipes of a leg.
_STAGE = r"{out}\lws-openssl-msvc-{arch}"
_OPENSSL = _STAGE + r"\openssl-" + _OPENSSL_VERSION
_MARKER = _STAGE + r"\built.ok"

# cmd.exe's own "if", as in openssl_msvc.py: a false "if" runs nothing and
# leaves ERRORLEVEL at 0, so a skipped step is not a failure.
_UNLESS_BUILT = "if not exist " + _MARKER + " "

_OPENSSL_STEPS = [
    BuildStep(_UNLESS_BUILT + "cmake -E rm -rf " + _STAGE),
    BuildStep(_UNLESS_BUILT + "cmake -E make_directory " + _STAGE),
    BuildStep(_UNLESS_BUILT + "cmake -E tar xf {openssl_archive}", cwd=_STAGE),
    BuildStep(_UNLESS_BUILT + _CONFIGURE_X64, cwd=_OPENSSL),
    BuildStep(_UNLESS_BUILT + _CONFIGURE_X86, cwd=_OPENSSL),
    BuildStep(_UNLESS_BUILT + "nmake build_libs", cwd=_OPENSSL),
    BuildStep(_UNLESS_BUILT + "cmake -E touch " + _MARKER),
]

# See the docstring. Not quoted: a path with a space in it cannot be given to
# cl through these variables, and the runner's work directory has none.
_ENV = {"CL": "/I" + _OPENSSL + r"\include", "_CL_": "/WX-"}

_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

# The cache type is spelled out (:PATH) because CMake converts a PATH entry to
# forward slashes when it stores it, and these values are later expanded
# inside CMake code where a backslash would start an escape sequence.
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
          '-DLWS_WITH_SHARED=ON -DLWS_WITH_STATIC=OFF -DLWS_WITH_SSL=ON '
          '-DLWS_WITHOUT_TESTAPPS=ON -DLWS_WITH_MINIMAL_EXAMPLES=OFF '
          '-DLWS_WITH_PLUGINS=OFF -DDISABLE_WERROR=ON '
          '-DLWS_OPENSSL_INCLUDE_DIRS:PATH=' + _OPENSSL + r'\include '
          '"-DLWS_OPENSSL_LIBRARIES:PATH=' + _OPENSSL + r'\libssl.lib;'
          + _OPENSSL + r'\libcrypto.lib" '
          + _CFLAGS + ' ' + _LDFLAGS)


def _libwebsockets_msvc(version, git_ref, cmake_extra=""):
    return Recipe(
        family="libwebsockets",
        version=version,
        upstream="https://github.com/warmcat/libwebsockets",
        license="MIT",
        source=Source(git_url="https://github.com/warmcat/libwebsockets.git",
                      git_ref=git_ref),
        extra_sources={"openssl_archive": Source(
            url="https://github.com/openssl/openssl/releases/download/"
                "OpenSSL_1_1_1w/openssl-%s.tar.gz" % _OPENSSL_VERSION,
            sha256=_OPENSSL_SHA256)},
        build=[BuildStep("cmake --version", allow_failure=True)]
        + _OPENSSL_STEPS + [
            BuildStep(_CMAKE + cmake_extra, env=_ENV),
            BuildStep("cmake --build build-{arch} --target websockets_shared",
                      env=_ENV),
            # What the configure probes decided and what the build wrote, for
            # the log the workflow uploads: build.py names a missing artefact
            # by the path it expected and nothing else.
            BuildStep(r"type build-{arch}\lws_config.h", allow_failure=True),
            BuildStep(r"dir /s /b build-{arch}\*.dll build-{arch}\*.pdb",
                      allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/bin/websockets.dll",
                            component="websockets.dll",
                            pdb="build-{arch}/bin/websockets.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        requires=["perl"],
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release, /Zi added), /WX- "
                    "through _CL_; /INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF "
                    "/OPT:NOICF at link; TLS via OpenSSL %s as a separate "
                    "DLL (not part of the artefact)" % _OPENSSL_VERSION,
        notes="The same tag, feature switches and TLS backend as the MinGW "
              "recipe for this version; only the compiler differs. OpenSSL "
              "%s is built from the pinned archive with MSVC (shared, "
              "no-asm) and linked through its import libraries, so it is "
              "imported, not linked in. The DLL is websockets.dll because "
              "MSVC has no library prefix. Built against the DLL runtime, so "
              "the MSVC C runtime is imported and stays attributed to "
              "data/MSVC. No-TLS, SChannel and mbedTLS builds are different "
              "code and are not covered." % _OPENSSL_VERSION,
    )


RECIPES = {
    "libwebsockets_4.0.21_msvc": _libwebsockets_msvc("4.0.21", "v4.0.21"),
    "libwebsockets_4.3.10_msvc": _libwebsockets_msvc("4.3.10", "v4.3.10"),
    "libwebsockets_4.5.8_msvc": _libwebsockets_msvc("4.5.8", "v4.5.8"),
    "libwebsockets_5.1.0_msvc": _libwebsockets_msvc("5.1.0", "v5.1.0",
                                                    _CMAKE_V5),
}
