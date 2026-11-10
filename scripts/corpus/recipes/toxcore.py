"""c-toxcore - the Tox protocol library, embedded whole inside Crytox (issue #21).

Crytox is a ransomware family first seen in 2020 whose samples carry an entire
uTox client, and so the Tox core. The evidence is structural: K7 Labs and
Zscaler both say the uTox client is embedded; nobody has published a
function-level match, and the vendors disagree on the unpacked size (about
2.9 MB against 1.23 MB). Nothing in the corpus covered Tox under any name.

What is built: the combined libtoxcore (toxcore, toxencryptsave and the event
and group layers each release has), as a DLL on Windows and a shared object on
Linux, never the uTox GUI. toxav is switched off with -DBUILD_TOXAV=OFF: it
needs libvpx and opus, neither of which is a family here, and the issue asks
for them disabled. DHT_bootstrap, tox-bootstrapd, the unit tests and the
auto tests are off for the same reason - they are programs and harnesses, not
library code. Nothing else is configured; optimisation and warnings are
upstream's CMake Release.

Axes, all built from the same three tags, x86 and x64:
  MinGW-w64 GCC 13   (the corpus default; Crytox is a Windows PE)
  MSVC v143          (cl 19.44, /MD /O2 /Ob2 /Zi, upstream's own /W4 /analyze)
  Linux ELF GCC 13   (the shared object, CMake Release -O3)
The issue names only the PE, so the ELF axis is carried as a measured
extra rather than evidence-led: c-toxcore is shipped on Linux and the library
is the same code, but no Linux sample is cited. MinGW and MSVC share no
PicHash at the 10-instruction floor (0 shared at every tag and arch), so
neither answers for the other; MinGW and ELF share none on x64 and 37-47 on
x86.

Versions. The issue recovers no version from the reports and suggests a
2020-era release plus a current one. v0.2.12 (2020-05-01) is the release
current when Crytox appeared and the last before a 19-month gap; v0.2.24
(2026-11-01) is the newest tag; v0.2.18 (2022-04-18) is the last release of
the 2022 series, the one that gained the msgpack events layer (cmp) and so
the code shape of everything from 0.2.18 to 0.2.20. v0.2.13-v0.2.17 and
v0.2.19-v0.2.21 were not built. v0.2.20 was built (MinGW, both arches) and
dropped as a near neighbour: PicHash overlap of functions of 10+ instructions,
x64 / x86 MinGW, share of the first version's sample:

  v0.2.12 / v0.2.18  13% / 15%     v0.2.18 / v0.2.20  27% / 33%
  v0.2.12 / v0.2.24   2% /  4%     v0.2.20 / v0.2.24  25% / 26%
  v0.2.18 / v0.2.24   6% /  9%     v0.2.12 / v0.2.20  10% / 12%

so the three kept are each at most 18% shared with a neighbour under any
compiler (MSVC 7-18%, ELF 2-14%); 0.2.20 sits at about a quarter with both
neighbours and adds little.

Dependencies and how the code is separated.

  * libsodium (1.0.20, the signed tarball and digest data/libsodium pins) is
    built from source by the recipe and linked as a DLL / shared object, never
    statically. So none of it is in the image: what remains is 19-21 named
    one-instruction import thunks (sodium_*, randombytes*, crypto_box_*,
    crypto_auth*...; on ELF unnamed PLT stubs). libsodium's own code is
    data/libsodium's and was not measured here because nothing of it is
    present.
  * pthread. MinGW imports libwinpthread (named pthread_* thunks); MSVC needs a
    pthread.h, which Windows lacks, so pthreads4w 3.0.0 is built from its
    release zip (SourceForge, sha256 pinned below, an `extra_sources` entry so
    the digest is recorded; its LICENSE file is the Apache License 2.0) and
    imported through pthreadVC3.dll. Only its import library and headers are
    used; none of its code is in an artefact.
  * cmp, the C MessagePack library, is compiled into toxcore from the git
    submodule third_party/cmp (TokTok/cmp: 4c3737d at v0.2.18, 52bfcfa at
    v0.2.24; v0.2.12 predates it) with -DCMP_NO_FLOAT=1. data/cmp is its own
    family, so a copy here would be attributed twice. Measured on an unsplit
    MinGW x64 0.2.24 build: 165 cmp-named functions in the image, 28 of
    data/cmp v20's 148 functions of 10+ instructions matching by name and
    PicHash - exactly the case `validate --deep` fails as leakage. So cmp is
    linked on its own and toxcore imports it, the way it imports libsodium:
    MinGW and ELF drop cmp.c.o from the link line CMake wrote and add an import
    library / -lcmp (the throwaway cmp.dll / libcmp.so is not an artefact);
    MSVC does the same through exercisers/toxcore_msvc.py, which re-links from
    the objects CMake compiled. Each is upstream's own link command with one
    object moved; no source, CMakeLists or header is touched, and the flags
    the objects were compiled with are upstream's. After the split the image
    holds 0 of data/cmp's name+PicHash matches at 10+ instructions (the one
    remaining equal PicHash is an unnamed function).

MSVC is built the way upstream's CMake describes, with three things supplied
that a bare runner lacks: libsodium from the pinned tarball through its
vs2022 project (ReleaseDLL, as libsodium_msvc.py does), pthreads4w through
`nmake VC`, and the two lookups cmake/Dependencies.cmake makes -
find_package(unofficial-sodium) / find_package(pthreads4w) - answered by config
files the helper writes, plus a pkg-config stub (Dependencies.cmake does
find_package(PkgConfig REQUIRED) everywhere) that reports every module absent,
so opus, libvpx and libconfig cannot be picked up from the runner. 0.2.12 and
0.2.18 look for libsodium and pthreads in third_party/ (their Dependencies
.cmake documents the paths); the helper's "legacy" mode fills those from the
same builds. upstream defines no export macro, so CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS
is set for CMake's own link and the final DLL is linked with a /DEF generated
from dumpbin /SYMBOLS of the objects (cmp_msvc.py's method). Link flags: /DEBUG
/Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF, no /GL, no /LTCG. Every
function in every MSVC artefact is named (PDB).

ELF is built with upstream's own -DSTRICT_ABI=ON, which writes an LD version
script exporting only the tox_* API. Without it each of the library's own
global functions would be reached through a PLT stub (the README's -fvisibility
point, for a library that sets none); with it the internal calls are direct.
The 350 or so unnamed 2-3 instruction functions per x64 artefact that remain
are libc/libsodium PLT stubs; 80-85% of functions are named.

Counts, kept + removed = image total (removed is the baseline filter's
compiler-runtime functions; MinGW: startup, dtoa/printf, libmingwex; MSVC:
static CRT startup, SEH/GS helpers and kernel32 thunks):

                    x86                         x64
  0.2.12 MinGW   808 + 123 =  931          848 + 115 =  963
  0.2.12 MSVC   1134 + 169 = 1303         1132 + 158 = 1290
  0.2.12 ELF     997 +   7 = 1004          988 +   5 =  993
  0.2.18 MinGW  1252 + 117 = 1369         1293 + 109 = 1402
  0.2.18 MSVC   1808 + 163 = 1971         1805 + 150 = 1955
  0.2.18 ELF    1597 +   7 = 1604         1587 +   5 = 1592
  0.2.24 MinGW  2045 + 120 = 2165         2089 + 110 = 2199
  0.2.24 MSVC   2955 + 167 = 3122         2945 + 151 = 3096
  0.2.24 ELF    2349 +   7 = 2356         2338 +   5 = 2343

Glue that survives, by name and PicHash. MinGW: the unnamed ___chkstk_ms stack
probe (15 instructions; x64 ae8f920c3b4e652a, x86 dfe3cea2dbb80872, the case
README already records) in every artefact, plus one unnamed 37-instruction
x64 body at 0.2.24. MSVC: none. ELF x64: none by name. ELF x86: _init,
register_tm_clones, deregister_tm_clones, __do_global_dtors_aux,
__stack_chk_fail_local and __x86.get_pc_thunk.* - the 32-bit PIC bodies whose
GOT delta is the image's own, as the README's Linux section explains for the
other ELF families; 0.2.18 x86 also has two unnamed bodies of 30 and 7
instructions. `validate --deep` over c-toxcore with cmp, libsodium, cJSON,
MinGW and MSVC reports 0 leakage.

Licences, as facts: c-toxcore's LICENSE is the GNU GPL version 3 and its
source files carry SPDX GPL-3.0-or-later; libsodium is ISC; cmp is MIT;
pthreads4w 3.0.0 ships the Apache License 2.0.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_SODIUM = Source(url="https://download.libsodium.org/libsodium/releases/libsodium-1.0.20.tar.gz",
                 sha256="ebb65ef6ca439333c2bb41a0c1990587288da07f6c7fd07cb3a18cc18d30ce19")

_SODIUM_BUILD = ("mkdir -p sodium-src-{arch} && tar xf {libsodium_src} -C sodium-src-{arch} "
                 "--strip-components=1 && cd sodium-src-{arch} && "
                 "./configure --host={host} --prefix=$PWD/../sodium-{arch} "
                 "--enable-shared --disable-static && make -j$(nproc) && make install")

_NOTES = ("The combined libtoxcore (toxcore, toxencryptsave, events and groups), "
          "toxav off (libvpx and opus are not families here). libsodium 1.0.20 "
          "is built from the pinned tarball and linked dynamically, so only "
          "its import thunks are present; the vendored cmp (TokTok/cmp "
          "submodule, 0.2.18 and later) is linked as a separate throwaway "
          "library so it stays attributed to data/cmp. See the recipe "
          "docstring for the separation measurement. Crytox evidence is "
          "structural (K7 Labs, Zscaler); no function-level match is "
          "published.")

_PE_FLAGS = ("upstream CMake Release: -O3 (CMake Release) after the toolchain's "
             "-O2, -DNDEBUG, -std=c11/gnu99 per release, -DCMP_NO_FLOAT=1; "
             "BUILD_TOXAV, DHT_BOOTSTRAP, BOOTSTRAP_DAEMON, UNITTEST, AUTOTEST "
             "off; shared library only; unstripped; cmp.c.o relinked out")

_MP_NOTE = "; msgpack-c 3.3.0 (C library) built shared from the pinned tarball and imported"

_ELF_FLAGS = ("upstream CMake Release: -O3 -fPIC (CMake Release) after the "
              "toolchain's -O2, -DNDEBUG, -DCMP_NO_FLOAT=1; STRICT_ABI=ON "
              "(version script exporting tox_* only); BUILD_TOXAV, DHT_BOOTSTRAP, "
              "BOOTSTRAP_DAEMON, UNITTEST, AUTOTEST off; shared object only; "
              "unstripped; cmp.c.o relinked out")

_MSVC_FLAGS = ("upstream CMake Release with /MD /O2 /Ob2 /DNDEBUG /Zi (plus "
               "upstream's /W4 /analyze), -DCMP_NO_FLOAT=1; BUILD_TOXAV, "
               "DHT_BOOTSTRAP, BOOTSTRAP_DAEMON, UNITTEST, AUTOTEST off; "
               "/DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link, "
               "no /GL or /LTCG; final DLL re-linked from the compiled objects "
               "with a /DEF generated from them, cmp linked separately")

_CMAKE_COMMON = ("-DCMAKE_BUILD_TYPE=Release -DBUILD_TOXAV=OFF -DENABLE_STATIC=OFF "
                 "-DENABLE_SHARED=ON -DUNITTEST=OFF -DAUTOTEST=OFF -DDHT_BOOTSTRAP=OFF "
                 "-DBOOTSTRAP_DAEMON=OFF -DBUILD_MISC_TESTS=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5")

_CMAKE_PE = ("PKG_CONFIG_PATH=$PWD/sodium-{arch}/lib/pkgconfig cmake -S . -B build-{arch} "
             "-DCMAKE_SYSTEM_NAME=Windows -DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx} "
             "-DCMAKE_RC_COMPILER={windres} -DCMAKE_FIND_ROOT_PATH=/usr/{host} "
             + _CMAKE_COMMON)


# Relink without the vendored cmp (see the docstring): cmp.c.obj is dropped from the
# object archive CMake already built, cmp is linked on its own to give an import
# library, and the toxcore link line CMake wrote is run again with it appended.
_SPLIT_PE = ("cd build-{arch} && D=CMakeFiles/toxcore_shared.dir && "
             "{cc} -O3 -shared -o cmp.dll $D/third_party/cmp/cmp.c.obj "
             "-Wl,--out-implib,libcmp.dll.a && {ar} d $D/objects.a cmp.c.obj && "
             "sh -c \"$(tail -n 1 $D/link.txt) libcmp.dll.a\"")


# msgpack-c, which v0.2.16 and v0.2.17 require (cmake/Dependencies.cmake:
# pkg_use_module(MSGPACK msgpack); events_alloc.h includes <msgpack.h>, and the
# first MSVC attempt stopped with "C1083: Cannot open include file:
# 'msgpack.h'" in run 42780737122). Built from the pinned release as a shared
# library (C part only), so none of its code is in the toxcore image; before
# v0.2.16 msgpack was only for tox-spectest, from v0.2.18 cmp replaces it.
_MSGPACK = Source(
    url="https://github.com/msgpack/msgpack-c/releases/download/cpp-3.3.0/"
        "msgpack-3.3.0.tar.gz",
    sha256="6e114d12a5ddb8cb11f669f83f32246e484a8addd0ce93f274996f1941c1f07b")
_MSGPACK_OPTS = ("-DCMAKE_BUILD_TYPE=Release -DMSGPACK_ENABLE_CXX=OFF "
                 "-DMSGPACK_BUILD_TESTS=OFF -DMSGPACK_BUILD_EXAMPLES=OFF "
                 "-DMSGPACK_ENABLE_SHARED=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5 "
                 "-DCMAKE_INSTALL_LIBDIR=lib")
_MSGPACK_PE = ("mkdir -p mp-src-{arch} && tar xf {msgpack_src} -C mp-src-{arch} "
               "--strip-components=1 && cmake -S mp-src-{arch} -B mp-build-{arch} "
               "-DCMAKE_SYSTEM_NAME=Windows -DCMAKE_C_COMPILER={cc} "
               "-DCMAKE_CXX_COMPILER={cxx} -DCMAKE_RC_COMPILER={windres} "
               "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_INSTALL_PREFIX=$PWD/sodium-{arch} "
               + _MSGPACK_OPTS + " && cmake --build mp-build-{arch} -j$(nproc) "
               "--target msgpackc && cmake --install mp-build-{arch}")
_MSGPACK_ELF = ("mkdir -p mp-src-{arch} && tar xf {msgpack_src} -C mp-src-{arch} "
                "--strip-components=1 && cmake -S mp-src-{arch} -B mp-build-{arch} "
                "-DCMAKE_INSTALL_PREFIX=$PWD/sodium-{arch} " + _MSGPACK_OPTS +
                " && cmake --build mp-build-{arch} -j$(nproc) --target msgpackc "
                "&& cmake --install mp-build-{arch}")


def _mingw(version, ref, cmp=True, msgpack=False):
    return Recipe(
        family="c-toxcore", version=version,
        upstream="https://github.com/TokTok/c-toxcore", license="GPL-3.0-or-later",
        source=Source(git_url="https://github.com/TokTok/c-toxcore.git", git_ref=ref),
        extra_sources=dict({"libsodium_src": _SODIUM},
                           **({"msgpack_src": _MSGPACK} if msgpack else {})),
        build_flags=_PE_FLAGS + (_MP_NOTE if msgpack else ""), notes=_NOTES,
        build=[BuildStep(_SODIUM_BUILD),
               *([BuildStep(_MSGPACK_PE)] if msgpack else []), BuildStep(_CMAKE_PE),
               BuildStep("cmake --build build-{arch} -j$(nproc) --target toxcore_shared"),
               *([BuildStep(_SPLIT_PE)] if cmp else []),
               BuildStep("find build-{arch} -name '*.dll'", allow_failure=True)],
        artifacts=[Artifact(path="build-{arch}/libtoxcore.dll", component="libtoxcore.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
    )


_SODIUM_ELF = ("mkdir -p sodium-src-{arch} && tar xf {libsodium_src} -C sodium-src-{arch} "
               "--strip-components=1 && cd sodium-src-{arch} && "
               "./configure --host={host} --prefix=$PWD/../sodium-{arch} "
               "--enable-shared --disable-static && make -j$(nproc) && make install")

_CMAKE_ELF = ("PKG_CONFIG_PATH=$PWD/sodium-{arch}/lib/pkgconfig cmake -S . -B build-{arch} "
              "-DSTRICT_ABI=ON " + _CMAKE_COMMON)

_SPLIT_ELF = ("cd build-{arch} && D=CMakeFiles/toxcore_shared.dir && "
              "{cc} {archflag} -O3 -shared -o libcmp.so $D/third_party/cmp/cmp.c.o && "
              "sh -c \"$(grep -e ' -shared ' $D/link.txt | head -n 1 | "
              "sed 's# '$D'/third_party/cmp/cmp.c.o##') -L. -lcmp\"")


def _elf(version, ref, cmp=True, msgpack=False):
    return Recipe(
        family="c-toxcore", version=version,
        upstream="https://github.com/TokTok/c-toxcore", license="GPL-3.0-or-later",
        source=Source(git_url="https://github.com/TokTok/c-toxcore.git", git_ref=ref),
        extra_sources=dict({"libsodium_src": _SODIUM},
                           **({"msgpack_src": _MSGPACK} if msgpack else {})),
        build_flags=_ELF_FLAGS + (_MP_NOTE if msgpack else ""), notes=_NOTES,
        build=[BuildStep(_SODIUM_ELF),
               *([BuildStep(_MSGPACK_ELF)] if msgpack else []), BuildStep(_CMAKE_ELF),
               BuildStep("cmake --build build-{arch} -j$(nproc) --target toxcore_shared"),
               *([BuildStep(_SPLIT_ELF)] if cmp else []),
               BuildStep("ls -l build-{arch}", allow_failure=True)],
        artifacts=[Artifact(path="build-{arch}/libtoxcore.so", component="libtoxcore.so")],
        toolchains=["linux_x86", "linux_x64"],
    )


RECIPES = {
    "c-toxcore_0.2.24": _mingw("0.2.24", "v0.2.24"),
    "c-toxcore_0.2.18": _mingw("0.2.18", "v0.2.18"),
    "c-toxcore_0.2.12": _mingw("0.2.12", "v0.2.12", cmp=False),
    "c-toxcore_0.2.24_linux": _elf("0.2.24", "v0.2.24"),
    "c-toxcore_0.2.18_linux": _elf("0.2.18", "v0.2.18"),
    "c-toxcore_0.2.12_linux": _elf("0.2.12", "v0.2.12", cmp=False),
}

# --- MSVC ------------------------------------------------------------------

_PTHREADS = Source(
    url="https://sourceforge.net/projects/pthreads4w/files/"
        "pthreads4w-code-v3.0.0.zip/download",
    sha256="b81136effb7185c77601fe2e0e6ac19bd996912e4814cebdd3010b0fac9e259b")

_PROPS = (
    'python -c "'
    "open('msvcprops.props','w').write("
    "'<Project><ItemDefinitionGroup><ClCompile>'"
    "'<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>'"
    "'</ClCompile><Link>'"
    "'<GenerateDebugInformation>true</GenerateDebugInformation>'"
    "'<ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile>'"
    "'<EnableCOMDATFolding>false</EnableCOMDATFolding>'"
    "'<OptimizeReferences>false</OptimizeReferences>'"
    "'<AdditionalOptions>/Brepro</AdditionalOptions>'"
    "'</Link></ItemDefinitionGroup></Project>')"
    '"')

_HELPER = 'python {repo}/scripts/corpus/exercisers/toxcore_msvc.py'

_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')


def _msvc(version, ref, cmp=True, legacy=False, pc=False):
    cmake = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
             '-DCMAKE_BUILD_TYPE=Release -DCMAKE_VERBOSE_MAKEFILE=ON '
             '"-DCMAKE_PREFIX_PATH=%CD%\\tox-deps" '
             '"-DPKG_CONFIG_EXECUTABLE=%CD%\\tox-deps\\pkg-config.bat" '
             + _CMAKE_COMMON + ' -DCMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON '
             + _CFLAGS + ' ' + _LDFLAGS)
    return Recipe(
        family="c-toxcore", version=version,
        upstream="https://github.com/TokTok/c-toxcore", license="GPL-3.0-or-later",
        source=Source(git_url="https://github.com/TokTok/c-toxcore.git", git_ref=ref),
        extra_sources={"libsodium_src": _SODIUM, "pthreads_src": _PTHREADS},
        build_flags=_MSVC_FLAGS, notes=_NOTES,
        build=[
            BuildStep("mkdir sodium pth"),
            BuildStep("tar -xf {libsodium_src} -C sodium --strip-components=1"),
            BuildStep("tar -xf {pthreads_src} -C pth --strip-components=1"),
            BuildStep(_PROPS),
            BuildStep('msbuild sodium\\builds\\msvc\\vs2022\\libsodium\\libsodium.vcxproj '
                      '/p:Configuration=ReleaseDLL /p:Platform={msbuild_platform} '
                      '/p:PlatformToolset=v143 '
                      '/p:ForceImportBeforeCppTargets=%CD%\\msvcprops.props '
                      '/m /v:minimal'),
            BuildStep("nmake /nologo /E VC", cwd="pth"),
            BuildStep(_HELPER + " prepare sodium pth tox-deps"
                      + (" legacy" if legacy else "") + (" pc" if pc else "")),
            BuildStep(cmake),
            BuildStep("type build-{arch}\\CMakeFiles\\toxcore_shared.dir\\flags.make",
                      allow_failure=True),
            BuildStep("cmake --build build-{arch} --target toxcore_shared"),
            BuildStep(_HELPER + " link build-{arch} tox-out-{arch} sodium pth {arch}"),
            BuildStep("dir tox-out-{arch}", allow_failure=True),
        ],
        artifacts=[Artifact(path="tox-out-{arch}/toxcore.dll", component="toxcore.dll",
                            pdb="tox-out-{arch}/toxcore.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
    )


RECIPES.update({
    "c-toxcore_0.2.24_msvc": _msvc("0.2.24", "v0.2.24"),
    "c-toxcore_0.2.18_msvc": _msvc("0.2.18", "v0.2.18", legacy=True),
    "c-toxcore_0.2.12_msvc": _msvc("0.2.12", "v0.2.12", cmp=False, legacy=True),
})

# Added in the final sweep: every other v0.2.x tag between the three first
# built (v0.2.20 was built and dropped as a near neighbour; v0.2.13-v0.2.17,
# v0.2.19 and v0.2.21-v0.2.23 were not built). Same recipes; cmp is vendored
# as a submodule from v0.2.18, and only releases up to v0.2.17 look for
# libsodium/pthreads4w in the legacy third_party layout (their
# cmake/Dependencies.cmake names Pre-built.2), as v0.2.18 does.
for _v in ("0.2.13", "0.2.14", "0.2.15", "0.2.16", "0.2.17", "0.2.19",
           "0.2.20", "0.2.21", "0.2.22", "0.2.23"):
    _cmp = _v not in ("0.2.13", "0.2.14", "0.2.15", "0.2.16", "0.2.17")
    _mp = _v in ("0.2.16", "0.2.17")
    RECIPES["c-toxcore_%s" % _v] = _mingw(_v, "v" + _v, cmp=_cmp, msgpack=_mp)
    RECIPES["c-toxcore_%s_linux" % _v] = _elf(_v, "v" + _v, cmp=_cmp, msgpack=_mp)
    # v0.2.19 and v0.2.20 require libsodium through pkg-config before their
    # MSVC find_package ("None of the required 'libsodium' found" in run
    # 42780737122), so the helper's pkg-config stub answers for libsodium.
    RECIPES["c-toxcore_%s_msvc" % _v] = _msvc(
        _v, "v" + _v, cmp=_cmp, legacy=not _cmp, pc=_v in ("0.2.19", "0.2.20"))

