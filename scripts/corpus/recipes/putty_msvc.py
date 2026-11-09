"""PuTTY 0.77 built with MSVC, beside the MinGW and Linux builds of the same tarball.

Same release tarball and sha256 as putty.py (419a76f4...beae5), so the two
Windows axes differ by compiler and nothing else on the source side. A
separate registry entry, for the reason in sqlite3_msvc.py: one Recipe has
one build list and these steps are cmd.exe.

Executables: putty, plink, pscp, psftp, pageant and puttygen - the six the
tracker issue names. puttytel, pterm and psocks are not built.

Build. Upstream's own CMake tree (0.77 has no Makefile.vc), configured with
the NMake Makefiles generator inside the developer environment the workflow
set up, so cl and link are the runner's v143. Nothing is patched.

CRT. Upstream's release script (Buildscr) builds the shipped binaries with
clang-cl and -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded, i.e. a statically
linked C runtime. This corpus builds against the DLL runtime instead (/MD),
so the MSVC C runtime is imported rather than linked into every executable
and stays attributed to data/MSVC; the images are therefore not the shape of
the official putty.exe, whose CRT bodies are inside it. cmake_minimum_required
is 3.7, so CMP0091 is OLD and the runtime switch lives in
CMAKE_C_FLAGS_RELEASE itself; /MD is stated there.

Flags. CMAKE_C_FLAGS_RELEASE is overridden to "/MD /O2 /Ob2 /Zi" - CMake's
Release default with /Zi added and without /DNDEBUG, because
cmake/setup.cmake strips /DNDEBUG from the Release flags anyway (defs.h
#errors if it is defined): assertions stay on, as upstream intends.
CMAKE_EXE_LINKER_FLAGS_RELEASE is "/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF
/OPT:NOICF"; upstream adds /dynamicbase /nxcompat and, for the GUI tools,
/manifest:no. No /GL, no /LTCG.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_TOOLS = ("putty", "plink", "pscp", "psftp", "pageant", "puttygen")

_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
          '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /Zi" '
          '-DCMAKE_EXE_LINKER_FLAGS_RELEASE='
          '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')


def _putty_msvc(version, sha256):
    return Recipe(
        family="PuTTY",
        version=version,
        upstream="https://www.chiark.greenend.org.uk/~sgtatham/putty/",
        license="MIT",
        source=Source(
            url="https://www.chiark.greenend.org.uk/~sgtatham/putty/%s/"
                "putty-%s.tar.gz" % (version, version),
            sha256=sha256),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} --target %s"
                      % " ".join(_TOOLS)),
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/%s.exe" % tool,
                            component="%s.exe" % tool,
                            pdb="build-{arch}/%s.pdb" % tool)
                   for tool in _TOOLS],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release without /DNDEBUG, which "
                    "upstream's cmake/setup.cmake removes so assertions stay "
                    "on), upstream's /wd4244 /wd4267 /wd4018 /wd4146 /wd4293 "
                    "/wd4090; link /INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF "
                    "/OPT:NOICF plus upstream's /dynamicbase /nxcompat; no "
                    "/GL, no /LTCG; NMake Makefiles generator",
        notes="Same tarball and digest as the MinGW and Linux recipes. "
              "Upstream's own release binaries are built with clang-cl and a "
              "static C runtime (/MT); these are cl (v143) against the DLL "
              "runtime (/MD), so the MSVC C runtime is imported and stays "
              "attributed to data/MSVC, and the images are not the shape of "
              "the official putty.exe. Six executables: putty, plink, pscp, "
              "psftp, pageant and puttygen.",
    )


RECIPES = {
    "PuTTY_0.77_msvc": _putty_msvc(
        "0.77",
        "419a76f45238fd45f2c76b42438993056e74fa78374f136052aaa843085beae5"),
}
