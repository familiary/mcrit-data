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

Measured (scratch run 42674927927, windows-2022, MSVC 19.44.35229, built
with the wide-stdio glue baseline merged on the scratch branch only),
kept + removed by the glue baseline = image:

    x64  putty 3761+206=3967   plink 3035+215=3250   pscp 2954+217=3171
         psftp 2964+215=3179   pageant 1334+183=1517 puttygen 1481+187=1668
    x86  putty 3778+200=3978   plink 3051+212=3263   pscp 2966+229=3195
         psftp 2978+212=3190   pageant 1339+179=1518 puttygen 1485+199=1684

Functions of 10+ instructions / distinct PicHashes, x64 | x86: putty
2186/2001 | 2285/2073, plink 1777/1595 | 1865/1663, pscp 1815/1625 |
1882/1681, psftp 1820/1628 | 1887/1684, pageant 915/822 | 938/844, puttygen
1027/919 | 1057/946. Every function of 10+ instructions is named (PDB).

Overlap (distinct PicHashes, 10+ instructions). Share of each tool's set
already in putty.exe, x64 | x86: plink 94.7% | 97.9%, pscp 88.4% | 91.3%,
psftp 88.2% | 91.2%, pageant 87.7% | 88.4%, puttygen 83.8% | 85.9%. The six
MSVC images together against the six MinGW images: 1 shared hash of 2584
(x64) and 1 of 2501 (x86); MSVC x86 against x64: 1. So the MSVC axis is new
reference data, not a duplicate of the MinGW one.

Glue survivors. The console tools (plink, pscp, psftp) keep no CRT name.
The three GUI tools (putty, pageant, puttygen) keep the WinMain flavour of
the VC startup code, which the baseline's EXE probes (console main) do not
emit: x64 __scrt_common_main_seh (92 instructions, PicHash
11271104747006965853), pre_c_initialization (48, 973123914783528695),
invoke_main (12, 18071112188852371364), WinMainCRTStartup (4,
10082331731223971200), __scrt_winmain_policy::set_app_type (2,
13166271553064441970); x86 __scrt_common_main_seh (110,
15412194987082466279), pre_c_initialization (53, 7114945967067284721),
invoke_main (11, 8721064936966453011), WinMainCRTStartup (2,
13477325577764728392), __scrt_winmain_policy::set_app_type (4,
2389322068591341037), plus a 10-instruction __scrt_common_main_seh$+0x124
fragment (PicHash 13184720424441161382) on x86 in pageant and puttygen.
These are Microsoft's code; a
WinMain probe in the baseline would remove them. Not done here (baseline.py
is shared tooling).
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_TOOLS = ("putty", "plink", "pscp", "psftp", "pageant", "puttygen")

_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
          '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /Zi" '
          '-DCMAKE_EXE_LINKER_FLAGS_RELEASE='
          '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')


_NOTES = ("Same tarball and digest as the MinGW and Linux recipes. "
          "Upstream's own release binaries are built with clang-cl and a "
          "static C runtime (/MT); these are cl (v143) against the DLL "
          "runtime (/MD), so the MSVC C runtime is imported and stays "
          "attributed to data/MSVC, and the images are not the shape of "
          "the official putty.exe. Six executables: putty, plink, pscp, "
          "psftp, pageant and puttygen.")


def _putty_msvc(version, sha256, tools=_TOOLS, notes=_NOTES):
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
                      % " ".join(tools)),
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/%s.exe" % tool,
                            component="%s.exe" % tool,
                            pdb="build-{arch}/%s.pdb" % tool)
                   for tool in tools],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release without /DNDEBUG, which "
                    "upstream's cmake/setup.cmake removes so assertions stay "
                    "on), upstream's /wd4244 /wd4267 /wd4018 /wd4146 /wd4293 "
                    "/wd4090; link /INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF "
                    "/OPT:NOICF plus upstream's /dynamicbase /nxcompat; no "
                    "/GL, no /LTCG; NMake Makefiles generator",
        notes=notes,
    )


RECIPES = {
    "PuTTY_0.77_msvc": _putty_msvc(
        "0.77",
        "419a76f45238fd45f2c76b42438993056e74fa78374f136052aaa843085beae5"),
    # puttytel and psocks, same tree, flags and toolchain, as a recipe of
    # their own so the six committed MSVC images are not rebuilt.
    "PuTTY_0.77_msvc_puttytel_psocks": _putty_msvc(
        "0.77",
        "419a76f45238fd45f2c76b42438993056e74fa78374f136052aaa843085beae5",
        tools=("puttytel", "psocks"),
        notes="Same tarball, digest, compiler and flags as the six-tool MSVC "
              "recipe beside it: puttytel.exe (the Telnet/raw/serial-only "
              "build of the PuTTY GUI) and psocks.exe (the SOCKS proxy "
              "server built on PuTTY's port-forwarding code), cl (v143) "
              "against the DLL runtime (/MD). A separate recipe so the six "
              "committed images are not rebuilt."),
}
