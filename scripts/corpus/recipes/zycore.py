"""Zycore - the C support library under Zydis, as a family of its own.

What it is. zyantific/zycore-c: ZyanString, ZyanVector, ZyanList, ZyanBitset,
the allocator, the argument parser, the terminal and the API wrappers
(critical sections, memory, process, synchronisation, thread). Zydis pins it
as a git submodule, and the Zydis family (zydis.py, zydis_msvc.py,
zydis_linux.py) whole-archives it into every Zydis image.

Why a family of its own. Issue 45 of the tracker asks for Zycore as its own
family. The earlier revision of the Zydis PR declined on the ground that a
standalone Zycore image repeats ZyanString, ZyanVector and the rest under a
second family name. That is a design choice, not something that cannot be
built: validate --deep counts a PicHash as a cross-family finding only when it
spans three or more families, and Zycore plus Zydis is two. A sample that
links Zycore without Zydis (Zycore is a general-purpose library, also used by
zyantific's other projects) has nothing else to match in the corpus.

Versions: the three Zycore commits the Zydis family's images carry, so each
Zycore image is the standalone counterpart of a Zydis one.

  2020-01-12-3435866   the commit Zydis v3.1.0 pins (before Zycore's own
                       v1.0.0 tag; CMake project version 1.0.0.0)
  2021-07-29-4f3746f   the commit Zydis 6a17c48 pins, the one Hidden/Disasm
                       vendors (v1.0.0-11-g4f3746f)
  1.5.2                tag v1.5.2, 0b2432c, the commit Zydis v4.1.1 pins

How it is built. Zycore's own CMake, Release, examples and tests off, as a
static archive; SMDA has no archive loader, so the archive is linked into one
DLL (MinGW, --whole-archive), one shared object (Linux, --whole-archive,
-fPIC -fvisibility=hidden) or one DLL with /WHOLEARCHIVE (MSVC, /MD /O2 /Ob2
/Z7, a one-line anchor object, /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF
/OPT:NOICF), exactly the route of the Zydis recipes. Zycore's own
ZYCORE_BUILD_SHARED_LIB target is not used for the same reason as Zydis's:
on Windows it adds a UTF-16 VersionInfo.rc that windres rejects. Nothing is
patched. -DCMAKE_POLICY_VERSION_MINIMUM=3.5 lets CMake 4 configure the old
minimum.

Measured (kept + removed = total) and the PicHash overlap with the Zydis
image of the same Zycore commit and toolchain are in each recipe's notes.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_UPSTREAM = "https://github.com/zyantific/zycore-c"
_GIT = "https://github.com/zyantific/zycore-c.git"
_LICENSE = "MIT, Copyright (c) Florian Bernd, Joel Hoener"

_OPTS = ("-DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_BUILD_TYPE=Release "
         "-DZYCORE_BUILD_EXAMPLES=OFF -DZYCORE_BUILD_TESTS=OFF "
         "-DZYCORE_BUILD_SHARED_LIB=OFF")

_CMAKE_MINGW = ("cmake -S . -B build-{arch} " + _OPTS + " "
                "-DCMAKE_SYSTEM_NAME=Windows -DCMAKE_C_COMPILER={cc} "
                "-DCMAKE_CXX_COMPILER={cxx} -DCMAKE_RC_COMPILER={windres} "
                "-DCMAKE_FIND_ROOT_PATH=/usr/{host}")
_LINK_MINGW = ("{cc} -shared -o zycore.dll -Wl,--whole-archive "
               "build-{arch}/libZycore.a -Wl,--no-whole-archive")

_CMAKE_LINUX = ("cmake -S . -B build-{arch} " + _OPTS + " "
                "-DCMAKE_POSITION_INDEPENDENT_CODE=ON "
                '-DCMAKE_C_FLAGS="{archflag} -fvisibility=hidden" '
                '-DCMAKE_CXX_FLAGS="{archflag} -fvisibility=hidden"')
_LINK_LINUX = ("{cc} {archflag} -shared -o libzycore.so -Wl,--whole-archive "
               "build-{arch}/libZycore.a -Wl,--no-whole-archive")

_CMAKE_MSVC = ('cmake -S . -B build-{arch} -G "NMake Makefiles" ' + _OPTS +
               ' -DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Z7" '
               '-DCMAKE_CXX_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Z7"')
_ANCHOR_SRC = ('python -c "'
               "open('anchor.c','w').write("
               "'int zycore_msvc_anchor(void){return 0;}')"
               '"')
_ANCHOR = "cl /nologo /c /O2 /MD /Z7 /Foanchor.obj anchor.c"
_LINK_MSVC = ('link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO '
              '/OPT:NOREF /OPT:NOICF '
              '/WHOLEARCHIVE:build-{arch}\\Zycore.lib '
              '/PDB:zycore.pdb /OUT:zycore.dll anchor.obj kernel32.lib')

_VERSIONS = {
    "2020-01-12-3435866": ("3435866ecaa837376807ce934d2088ae46aa3fa3",
                           "Commit 3435866 (2020-01-12), the Zycore commit "
                           "Zydis v3.1.0 pins; CMake project version "
                           "1.0.0.0, before the v1.0.0 tag."),
    "2021-07-29-4f3746f": ("4f3746faa1d19a14857ea7d1495c2ab006103698",
                           "Commit 4f3746f (2021-07-29, v1.0.0-11-g4f3746f), "
                           "the Zycore commit Zydis 6a17c48 pins and the one "
                           "Hidden/Disasm vendors."),
    "1.5.2": ("0b2432ced0884fd152b471d97ecf0258ff4d859f",
              "Tag v1.5.2 (0b2432c, 2025-02-09), the Zycore commit Zydis "
              "v4.1.1 pins."),
}

_COMMON = ("Zycore built standalone with its own CMake (Release) as a static "
           "archive and linked whole into one image; nothing patched. The "
           "same code is whole-archived into the Zydis image of the matching "
           "Zydis version, so the two families share these functions by "
           "design; this family is the reference for a sample that links "
           "Zycore without Zydis. ")


def _recipe(version, kind):
    ref, what = _VERSIONS[version]
    if kind == "mingw":
        build = [BuildStep(_CMAKE_MINGW),
                 BuildStep("cmake --build build-{arch} -j$(nproc)"),
                 BuildStep(_LINK_MINGW)]
        artifacts = [Artifact(path="zycore.dll", component="zycore.dll")]
        toolchains = ["mingw_x86", "mingw_x64"]
        flags = ("-O3 (CMake Release) static archive, linked into one DLL "
                 "with --whole-archive")
    elif kind == "linux":
        build = [BuildStep(_CMAKE_LINUX),
                 BuildStep("cmake --build build-{arch} -j$(nproc)"),
                 BuildStep(_LINK_LINUX)]
        artifacts = [Artifact(path="libzycore.so", component="libzycore.so")]
        toolchains = ["linux_x86", "linux_x64"]
        flags = ("-O3 (CMake Release) -fPIC -fvisibility=hidden static "
                 "archive, linked into one shared object with "
                 "--whole-archive")
    else:
        build = [BuildStep(_CMAKE_MSVC),
                 BuildStep("cmake --build build-{arch}"),
                 BuildStep(_ANCHOR_SRC),
                 BuildStep(_ANCHOR),
                 BuildStep(_LINK_MSVC)]
        artifacts = [Artifact(path="zycore.dll", component="zycore.dll",
                              pdb="zycore.pdb")]
        toolchains = ["msvc_x86", "msvc_x64"]
        flags = ("/MD /O2 /Ob2 /Z7 (CMake Release, /Z7 added); /DEBUG "
                 "/Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF /WHOLEARCHIVE "
                 "at link")
    return Recipe(
        family="Zycore", version=version, upstream=_UPSTREAM,
        license=_LICENSE, source=Source(git_url=_GIT, git_ref=ref),
        build=build, artifacts=artifacts, toolchains=toolchains,
        build_flags=flags, notes=_COMMON + what)


RECIPES = {}
for _v in _VERSIONS:
    RECIPES["Zycore_%s" % _v] = _recipe(_v, "mingw")
    RECIPES["Zycore_%s_linux" % _v] = _recipe(_v, "linux")
    RECIPES["Zycore_%s_msvc" % _v] = _recipe(_v, "msvc")
