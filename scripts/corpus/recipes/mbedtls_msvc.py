"""mbedTLS built with MSVC, beside the MinGW build of the same tag.

data/mbedTLS carries only MinGW artefacts. mbedTLS is one of the two crypto
stacks that actually turn up inside Windows ransomware and commodity loaders
- the other being OpenSSL - and those binaries are MSVC-built, so this is the
compiler the family should have had first.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

Only 3.6.7 is covered, of the four versions the MinGW side carries.

  * 3.6.7 is the current LTS and what anything built today links.
  * 2.28.10 is the other line worth having, and it is deliberately left for
    later rather than dropped on judgement: its CMakeLists.txt declares
    cmake_minimum_required(VERSION 2.8.12), which CMake 4 refuses outright
    unless CMAKE_POLICY_VERSION_MINIMUM is passed. That is a cache variable
    and so would be legitimate here, but it makes the build's success depend
    on which CMake the runner image happens to carry - the same reason
    lz4_msvc.py holds back lz4 1.9.4. 3.6.7 declares 3.5.1 and has no such
    dependency.
  * 2.16.12 is 2019 code and the survey's own risk list names it as one of
    the versions v143 may simply reject; 3.0.0 is a short-lived release
    between the two LTS lines and is the least likely of the four to be met
    in the wild.

What was read rather than assumed, in CMakeLists.txt and library/CMakeLists
.txt at mbedtls-3.6.7:

  * USE_SHARED_MBEDTLS_LIBRARY is upstream's own option (default OFF) and
    selects "add_library(... SHARED ...)" for all three libraries;
    USE_STATIC_MBEDTLS_LIBRARY is turned off so only the DLLs are built.
    Exactly one of the two must be on or the configure stops with a
    FATAL_ERROR.
  * **mbedTLS has no export machinery at all.** There is not one
    __declspec(dllexport) in the tree, and nothing sets
    WINDOWS_EXPORT_ALL_SYMBOLS. Under MinGW that does not matter, because ld
    auto-exports; under MSVC it means mbedcrypto.dll would export nothing,
    no import library would be produced, and the mbedx509 link - which
    target_link_libraries against the mbedcrypto *target* - would then fail
    outright. -DCMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON is therefore not a
    nicety here but the thing that makes the MSVC shared build exist. It is
    a CMake cache variable, so upstream source stays untouched.
  * MBEDTLS_FATAL_WARNINGS defaults ON and, in its MSVC branch, appends /WX
    to a CMAKE_C_FLAGS that the MSVC branch above it has already set to
    "/W3 /utf-8". The MinGW recipe turns the option off too, but for a
    different failure (-Werror=format= on a time_t), so the reason is
    re-derived here rather than copied: under v143 it is /WX at /W3 over a
    2024 code base, which is a coin flip this build does not need to take.
  * the generated sources - error.c, version_features.c,
    ssl_debug_helpers_generated.c, psa_crypto_driver_wrappers.h - are
    committed in the pinned tree, and GEN_FILES defaults OFF on Windows
    hosts as well as elsewhere, so neither Perl nor the Python jinja
    generators are needed. Python is looked for but only to print a
    configuration warning, and is not REQUIRED.
  * link_to_source, the one place upstream makes a symlink, is called only
    from the tests branch and copies rather than links on a non-Unix host
    anyway. ENABLE_TESTING is off here and already defaults off for MSVC
    upstream, because "the test suites currently have compile errors with
    MSVC".
  * the three add_library calls live in library/CMakeLists.txt, so with a
    single-configuration generator the DLLs and their PDBs land in
    build-<arch>/library/ - the same relative path the MinGW recipe uses.
    Only the names differ: MSVC's empty library prefix makes them
    mbedcrypto.dll / mbedx509.dll / mbedtls.dll where MinGW's "lib" prefix
    makes them libmbedcrypto.dll and so on. VERSION and SOVERSION are set on
    the targets but do not reach the file name on a platform without
    sonames.
  * the MSVC branch of the compiler-flag block touches CMAKE_C_FLAGS only,
    not CMAKE_C_FLAGS_RELEASE, so the per-configuration override below is
    not fighting upstream for the same variable.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# See xz_msvc.py for why the per-configuration variables and not
# CMAKE_C_FLAGS / CMAKE_SHARED_LINKER_FLAGS: CMake's MSVC Release default
# carries neither /Zi nor /DEBUG, so the artefacts would come back with no
# PDB and no names, and overriding the per-configuration variables leaves
# CMake's own initialisation - /machine on the 32-bit leg among it - in
# place.
#
# /MD is spelled out rather than left to CMAKE_MSVC_RUNTIME_LIBRARY.
# mbedTLS declares cmake_minimum_required(VERSION 3.5.1), so CMP0091 is OLD
# and the runtime flag is whatever CMAKE_C_FLAGS_<CONFIG> says - which means
# replacing that variable without /MD in it would silently hand the build
# cl's default /MT and file the static MSVC C runtime under the mbedTLS name.
_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
# /DEBUG so a PDB is written at all, /Brepro so the PE carries no build
# timestamp and two runs of identical source record the same sha256,
# /OPT:NOREF /OPT:NOICF so unreferenced and identically-compiled routines
# both survive as separate reference samples. /INCREMENTAL:NO is CMake's own
# Release default and is restated because setting the variable replaces it.
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

# NMake Makefiles: nmake ships with MSVC itself, the generator is
# single-configuration so CMAKE_BUILD_TYPE means what it says and the
# artefacts land beside their CMakeLists rather than under a Release/
# subdirectory, and the target architecture comes from the developer
# environment the workflow sets up.
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release '
          '-DUSE_SHARED_MBEDTLS_LIBRARY=ON -DUSE_STATIC_MBEDTLS_LIBRARY=OFF '
          '-DCMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON '
          '-DENABLE_TESTING=OFF -DENABLE_PROGRAMS=OFF '
          '-DMBEDTLS_FATAL_WARNINGS=OFF %s %s' % (_CFLAGS, _LDFLAGS))


def _artifact(name):
    return Artifact(path="build-{arch}/library/%s.dll" % name,
                    component="%s.dll" % name,
                    pdb="build-{arch}/library/%s.pdb" % name)


RECIPES = {
    "mbedTLS_3.6.7_msvc": Recipe(
        family="mbedTLS",
        version="3.6.7",
        upstream="https://github.com/Mbed-TLS/mbedtls",
        license="Apache-2.0",
        # The fetch stage initialises submodules; mbedTLS >= 3.6 needs the
        # framework submodule at configure time even with testing disabled.
        source=Source(git_url="https://github.com/Mbed-TLS/mbedtls.git",
                      git_ref="mbedtls-3.6.7"),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch}"),
            # Cheap insurance, as in xz_msvc.py: puts the names the build
            # actually wrote into the log the workflow prints on failure.
            BuildStep("dir build-{arch}\\library", allow_failure=True),
        ],
        artifacts=[_artifact("mbedcrypto"), _artifact("mbedx509"),
                   _artifact("mbedtls")],
        toolchains=["msvc_x86", "msvc_x64"],
        # Not the same string as the MinGW recipe, and deliberately not: that
        # one records -O2 because upstream's GNU-compiler branch overwrites
        # CMAKE_C_FLAGS_RELEASE with "-O2". The MSVC branch sets no
        # per-configuration flags at all, so what governs this build is the
        # value passed on the command line.
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release, /Zi added) plus the "
                    "/W3 /utf-8 upstream appends for MSVC, /WX suppressed "
                    "with MBEDTLS_FATAL_WARNINGS=OFF; /DEBUG /Brepro "
                    "/OPT:NOREF /OPT:NOICF at link; exports generated by "
                    "CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS because mbedTLS "
                    "declares none itself",
        notes="Three DLLs per build, as under MinGW, and the same split: "
              "mbedcrypto is the primitives, mbedx509 the certificate "
              "handling, mbedtls the protocol. Named without the lib prefix "
              "because MSVC has none. No external dependencies: the "
              "libraries link ws2_32 and bcrypt from Win32 and are built "
              "against the DLL runtime, so the MSVC C runtime is imported "
              "rather than linked in and stays attributed to data/MSVC. Two "
              "in-tree third-party libraries, Everest (HACL* Curve25519) and "
              "p256-m, are compiled and linked into mbedcrypto by upstream's "
              "CMake, but their translation units are guarded by "
              "MBEDTLS_ECDH_VARIANT_EVEREST_ENABLED and the p256-m driver "
              "switch, neither of which the default mbedtls_config.h turns "
              "on, so effectively no code from either reaches this artefact. "
              "mbedTLS and wolfSSL implement the same primitives and both "
              "appear in this corpus - a cross-family PicHash hit between "
              "them is two independent implementations of one algorithm, not "
              "code leaking from one family into the other. The export "
              "tables of the two toolchains' artefacts arrive by different "
              "routes - a CMake-generated .def here, GNU ld's auto-export "
              "there - so do not read a difference between them as a "
              "difference in what was built; the function bodies are what "
              "the corpus matches on.",
    ),
}
