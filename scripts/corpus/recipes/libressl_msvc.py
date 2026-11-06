"""LibreSSL built with MSVC (DRAFT docstring, rewritten after the runner)."""

from ..recipe import Artifact, BuildStep, Recipe, Source

_BASE = "https://cdn.openbsd.org/pub/OpenBSD/LibreSSL/libressl-%s.tar.gz"

_SHA256 = {
    "2.8.3": "9b640b13047182761a99ce3e4f000be9687566e0828b4a72709e9e6a3ef98477",
    "3.3.6": "3f28849365e1190db2baf9014ff9686012c25b1ca6df8b3a085f789e24fe4b9a",
    "3.9.2": "7b031dac64a59eb6ee3304f7ffb75dad33ab8c9d279c847f92c89fb846068f97",
    "4.4.0": "7d02522ad5070b9adb32eb253ecabce181184a3750cf65abac0675ee908687c1",
}

# 2.8.3 and 3.3.6 add -Drestrict for WIN32 in their CMakeLists.txt, and the
# UCRT's corecrt_malloc.h spells __declspec(restrict), which becomes
# __declspec(1): C2485 on every translation unit that includes <stdlib.h>.
# No source in either tree uses the word, so the definition is cancelled on
# the command line instead of being edited out.
_UNDEF_RESTRICT = {"2.8.3", "3.3.6"}

def _cflags(version):
    extra = " /Urestrict" if version in _UNDEF_RESTRICT else ""
    return '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi%s"' % extra
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
def _cmake(version, platform):
    return ('cmake -S . -B build-{arch} -G "Visual Studio 17 2022" -A %s '
            '-DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
            '-DBUILD_SHARED_LIBS=ON -DLIBRESSL_APPS=OFF -DLIBRESSL_TESTS=OFF '
            '-DLIBRESSL_SKIP_INSTALL=ON -DENABLE_ASM=ON '
            '-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL %s %s'
            % (platform, _cflags(version), _LDFLAGS))


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
            BuildStep('if "{arch}"=="x64" ' + _cmake(version, "x64")),
            BuildStep('if "{arch}"=="x86" ' + _cmake(version, "Win32")),
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
