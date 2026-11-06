"""LibreSSL built with MSVC (DRAFT docstring, rewritten after the runner)."""

from ..recipe import Artifact, BuildStep, Recipe, Source

_BASE = "https://cdn.openbsd.org/pub/OpenBSD/LibreSSL/libressl-%s.tar.gz"

_SHA256 = {
    "2.8.3": "9b640b13047182761a99ce3e4f000be9687566e0828b4a72709e9e6a3ef98477",
    "3.3.6": "3f28849365e1190db2baf9014ff9686012c25b1ca6df8b3a085f789e24fe4b9a",
    "4.0.0": "4d841955f0acc3dfc71d0e3dd35f283af461222350e26843fea9731c0246a1e4",
    "4.2.0": "0f7dba44d7cb8df8d53f2cfbf1955254bc128e0089595f1aba2facfaee8408b2",
    "4.3.4": "57c8b2f8c6f9505587abaeddab003ea243d615edb7ed71957968121fc6316bd6",
    "4.4.0": "7d02522ad5070b9adb32eb253ecabce181184a3750cf65abac0675ee908687c1",
}

_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

# The Visual Studio generator, because it is the one route upstream's
# CMakeLists.txt supports for MSVC: through 4.3.x the MASM sources are chosen
# only when CMAKE_GENERATOR_PLATFORM is x64 (or the generator name says
# Win64), which only -A sets, and from 4.4.0 the architecture is read from
# CMAKE_GENERATOR_PLATFORM too. Under NMake Makefiles neither is ever set,
# and CMAKE_SYSTEM_PROCESSOR is the host's AMD64 whichever developer
# environment is active, so an x64 leg would silently build without assembly
# and an x86 leg would be handed the x86-64 assembler sources.
_CMAKE = ('cmake -S . -B build-{arch} -G "Visual Studio 17 2022" -A %s '
          '-DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
          '-DBUILD_SHARED_LIBS=ON -DLIBRESSL_APPS=OFF -DLIBRESSL_TESTS=OFF '
          '-DLIBRESSL_SKIP_INSTALL=ON -DENABLE_ASM=ON '
          '-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL ' + _CFLAGS + ' '
          + _LDFLAGS)
_CMAKE_X64 = 'if "{arch}"=="x64" ' + _CMAKE % "x64"
_CMAKE_X86 = 'if "{arch}"=="x86" ' + _CMAKE % "Win32"

# The multi-config generator writes into a Release/ subdirectory, and DLL and
# PDB names carry the soversion from CMake 3.27 on, so they are copied to
# stable names; indexing the sorted glob fails the step on a miss.
_NORMALISE = (
    'python -c "'
    "import glob,shutil;"
    "[shutil.copy(sorted(glob.glob('build-{arch}/'+d+'/**/'+d+'*'+e, "
    "recursive=True))[0], 'build-{arch}/lib'+d+e) "
    "for d in ('crypto','ssl','tls') for e in ('.dll','.pdb')]"
    '"')


def _msvc(version):
    return Recipe(
        family="LibreSSL",
        version=version,
        upstream="https://www.libressl.org/",
        license="ISC (new code) over OpenSSL/SSLeay-licensed code, see COPYING",
        source=Source(url=_BASE % version, sha256=_SHA256[version]),
        build=[
            BuildStep(_CMAKE_X64),
            BuildStep(_CMAKE_X86),
            BuildStep("cmake --build build-{arch} --config Release --target crypto ssl tls "
                      "-- /m /v:n"),
            BuildStep(_NORMALISE),
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[
            Artifact(path="build-{arch}/libcrypto.dll", component="libcrypto",
                     pdb="build-{arch}/libcrypto.pdb"),
            Artifact(path="build-{arch}/libssl.dll", component="libssl",
                     pdb="build-{arch}/libssl.pdb"),
            Artifact(path="build-{arch}/libtls.dll", component="libtls",
                     pdb="build-{arch}/libtls.pdb"),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi",
    )


RECIPES = {"LibreSSL_%s_msvc" % v: _msvc(v) for v in _SHA256}
