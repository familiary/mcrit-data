"""LibreSSL built with MSVC, beside the MinGW and Linux builds of the same tags.

Same four versions as libressl.py (2.8.3, 3.3.6, 3.9.2, 4.4.0) and the same
sha256 pins, so each pair differs by compiler and nothing else on the source
side; libressl.py records why those four. A separate registry entry, for the
reason in sqlite3_msvc.py: one Recipe has one build list and these steps are
cmd.exe.

**Generator: Visual Studio 17 2022 with -A, not NMake Makefiles.** Read in
CMakeLists.txt at the pinned tags, not assumed. Through 4.3.x (2.8.3, 3.3.6
and 3.9.2 here) the x86-64 MASM sources are chosen only when
CMAKE_GENERATOR_PLATFORM is x64 or the generator name contains Win64, and
only -A sets either; from 4.4.0 the architecture is read from
CMAKE_GENERATOR_PLATFORM when it is set and otherwise from
CMAKE_SYSTEM_PROCESSOR, which under NMake is the host's AMD64 whichever
developer environment is active. So NMake would silently build x64 without
assembly and, at 4.4.0, hand the x86 leg the x86-64 assembler sources. The
multi-config generator writes to <dir>/Release/, so the DLLs and PDBs are
found with a recursive glob and copied to libcrypto/libssl/libtls.dll and
.pdb; the component names are the same as the MinGW and Linux ones so the
README rows line up.

**Assembly, read back from the runner's log.** x64 at 4.4.0: ml64 assembles
aes-masm, aesni-masm, ghash-masm and rc4-masm (bignum assembly is commented
out upstream for MASM); at 3.3.6 and 3.9.2 15 ml64 invocations (the bignum
modules are on as well); at 2.8.3 and on every x86 leg OPENSSL_NO_ASM is
defined and the C fallbacks are compiled. -DENABLE_ASM=ON is passed to say so
rather than inherit it. The MASM routines carry no PDB symbols: the x64
artefacts of the three MASM versions hold 22 (4.4.0), 41 (3.9.2) and 35
(3.3.6) unnamed functions of libcrypto, 2.8.3 holds none, and x86 holds none
anywhere. Instruction baseline: cl's defaults, no /arch, which is SSE2 on
both x86 and x64 for v143; no /GL, no /LTCG. The assembly selects
AES-NI/PCLMUL at run time from CPUID.

**Flags, read back from the log** (windows-2022, MSVC 19.44.35229, v143):
compile `/Zi /W4 /MP /O2 /Ob2 /MD /GS /fp:precise /Zc:inline /TC` plus
upstream's definitions; link `/INCREMENTAL:NO /DEBUG /OPT:NOREF /OPT:NOICF
/Brepro /DYNAMICBASE /NXCOMPAT` and the .def file CMake writes from
crypto.sym/ssl.sym/tls.sym. The overrides go through CMAKE_C_FLAGS_RELEASE
and CMAKE_SHARED_LINKER_FLAGS_RELEASE as in jansson_msvc.py;
CMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL states /MD, and /MD is restated in
the flags for 2.8.3, whose cmake_minimum_required of 3.0 leaves CMP0091 OLD.
CMAKE_POLICY_VERSION_MINIMUM=3.5 is insurance against a CMake 4 runner. Apps
and tests are off (LIBRESSL_APPS, LIBRESSL_TESTS), nothing is installed.

**/Urestrict for 2.8.3 and 3.3.6.** Their CMakeLists.txt adds -Drestrict for
WIN32; the UCRT's corecrt_malloc.h writes __declspec(restrict), which
becomes __declspec(1) and fails with C2485 in every unit that includes
<stdlib.h> (220 errors on the first run, run 42175805545). No source in
either tree uses the word. Cancelling the definition on the command line
works: cl prints D9025 "overriding /Drestrict with /Urestrict" and the build
passes (run 42180962594, all 24 artefacts). The later trees do not define it.
Nothing is patched.

Counts on the runner, kept + removed = image, summed over components
(x86 | x64); removed is the baseline's compiler-runtime filter:

    2.8.3  6217+441=6658 | 6177+457=6634   3.3.6  6876+445=7321 | 6904+461=7365
    3.9.2  6949+476=7425 | 6973+483=7456   4.4.0  7007+466=7473 | 6985+482=7467

Unlike MinGW, libtls is carried at 3.3.6 too (329 functions x64): the MSVC
import library keeps it from linking libcrypto and libssl in.

PicHash overlap, libcrypto + libssl, 10+ instructions, MSVC against MinGW
(x64 | x86): 2.8.3 8 | 0, 3.3.6 10 | 0, 3.9.2 1 | 0, 4.4.0 0 | 0; against
Linux 0 | 0 except 3.3.6 x64 with 1. Sizes of the MSVC sets are 3010-3507
(x64) and 3383-3866 (x86) hashes, so the MSVC axis shares essentially nothing
with the other two and is new reference data.

Glue survivors, by name and PicHash: none that is MSVC runtime. The kept
names that begin with underscores are LibreSSL's own (`__gmtime_r`,
`__secs_to_tm`, `__tm_to_secs` from its compat layer) or one-instruction
import thunks of the UCRT (`__read`, `__open`, `__strdup`, `_freezero`...
below the 10-instruction cross-family floor). The baseline cannot be
measured on a Linux host, so this is read from the committed names, not
recomputed.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_BASE = "https://cdn.openbsd.org/pub/OpenBSD/LibreSSL/libressl-%s.tar.gz"

from .libressl import _SHA256  # noqa: E402  (one digest table for all legs)

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


# 3.5.4's MSVC libtls DLL links libcrypto and libssl in whole (6,756
# functions on x64 against 329 for 3.3.6 and 440-451 for 3.9.2-4.4.0), the
# same reason libressl.py leaves libtls out of 3.3.6 and 3.5.4 on MinGW: the
# image would file libcrypto/libssl bodies a second time under libtls. It is
# left out for that version.
_MSVC_NO_LIBTLS = {"3.5.4"}


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
        ] + ([] if version in _MSVC_NO_LIBTLS else [
            Artifact(path="build-{arch}/libtls.dll", component="libtls",
                     pdb="build-{arch}/libtls.pdb"),
        ]),
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release, /Zi added), /W4 /GS "
                    "from upstream; /INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF "
                    "/OPT:NOICF at link; no /GL, no /LTCG; Visual Studio "
                    "generator; x64 MASM assembly for AES/AES-NI/GHASH/RC4"
                    + (" and bignum" if version in ("3.3.6", "3.9.2") else "")
                    + ("" if version != "2.8.3" else "; no assembly (2.8.3)")
                    + "; x86 C only",
        notes="Same tag and digest as the MinGW recipe. Visual Studio "
              "generator because the MASM selection in CMakeLists.txt keys "
              "on CMAKE_GENERATOR_PLATFORM. Built against the DLL runtime, "
              "so the MSVC C runtime is imported and stays attributed to "
              "data/MSVC. Named libcrypto/libssl/libtls here as in the MinGW "
              "and Linux rows although the DLLs are crypto, ssl and tls."
              + (" /Urestrict cancels the -Drestrict this version's "
                 "CMakeLists.txt adds, which breaks the current UCRT headers."
                 if version in _UNDEF_RESTRICT else ""),
    )


# 3.1.0 is the v141_xp recipes' (libressl_v141xp_msvc.py): a v143 build of it
# would declare the same toolchain alias and components, which
# refresh_provenance.py cannot tell apart from them.
RECIPES = {"LibreSSL_%s_msvc" % v: _msvc(v) for v in _SHA256 if v != "3.1.0"}
