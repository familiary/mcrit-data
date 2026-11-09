"""PuTTY 0.77 - the SSH/Telnet client, and the code UNC4034 recompiled.

The reference value is upstream PuTTY itself: UNC4034 rebuilt putty.exe from
the 0.77 source with their own code added to two named functions, so
everything else in that binary is Simon Tatham's code and is what this family
describes. The Linux build of the console tools is the second recipe below.

Source. The release tarball, pinned by SHA-256. chiark.greenend.org.uk
redirects its downloads to the.earth.li, whose sha256sums file for 0.77 lists
the same digest, and putty-0.77.tar.gz.gpg verifies against upstream's
release key 2CF6 134B D3F7 7A65 88EB D668 E4F8 3EA2 AA49 15EC (certified by
the PuTTY Master Key; the release key has since expired, as released keys
do). The git tag 0.77 on git.tartarus.org is 61ab33efe48c; the tarball
differs from it only in generated documentation (doc/html, the man pages),
version.h and cmake/gitcommit.cmake, which a release tarball stamps with the
release number and the commit instead of asking git. No source file differs.
0.77 is the first release with a CMake build; 0.76 has only the Perl-generated
makefiles.

Build. Upstream's CMake, cross-compiled with -DCMAKE_SYSTEM_NAME=Windows as
the other C recipes do; its own cmake/toolchain-mingw.cmake is not used
because the recipe has to select the 32-bit compiler too. Nothing is patched.
cmake/setup.cmake strips -DNDEBUG from the Release flags itself (defs.h
#errors if it is defined), so the binaries are -O3 with assertions on.
CFLAGS is cleared for the configure step, since the toolchain environment's
-O2 would otherwise be folded into CMAKE_C_FLAGS ahead of upstream's -O3.
The binaries import only system DLLs (msvcrt.dll among them).

Which executables. The issue names putty.exe, and that is built. The others
were measured, by PicHash overlap of whole-image functions of 10 or more
instructions, before the runtime filter. putty.exe has 1500 (x64) and 1629
(x86) such functions; against putty.exe alone and then against putty.exe plus
psftp.exe, each other tool adds, x64 / x86:

  psftp.exe    142 / 144 beyond putty.exe,  0 / 0 after that
  pscp.exe     132 / 131 beyond putty.exe, 26 / 25 beyond putty+psftp
  plink.exe     33 /  32 beyond putty.exe, 11 /  8 beyond putty+psftp
  puttytel.exe  15 /   5 beyond putty.exe, 12 /  5 beyond putty+psftp
  puttygen.exe 121 / 116 beyond putty.exe, 118 / 116 beyond putty+psftp
  pageant.exe   80 /  84 beyond putty.exe,  76 /  84 beyond putty+psftp

putty.exe already holds nearly all of the SSH client. psftp.exe adds the SFTP
client (sftp.c, psftp.c, psftpcommon.c) and is kept. plink, pscp and puttytel
add under 2% each and are not built; pscp's 26 are scp.c. puttygen and
pageant add real code but are key tools, not the SSH client, and not what the
issue is about; they are the follow-up if one turns up abused.

Linux. PuTTY's SSH core is portable and ships on Linux (Debian's
putty-tools: plink, pscp, psftp, puttygen), so the same tree was built with the
host gcc for both ELF architectures and measured. It shares no PicHash with
the Windows build on x64 (0 of 1231 plink and 0 of 1269 psftp functions of 10
or more instructions) and 84 of 1452 / 80 of 1490 on x86, because the ABI
changes every function: a different reference value, so plink and psftp are
kept (PuTTY_0.77_linux). In the Linux set psftp is the base and plink adds 81
functions on x64 (the Unix console front end, uxplink.c); pscp adds 28 beyond
those two and puttygen 77 (a key tool, not the SSH client), and neither is
built. The GTK putty and pterm need GTK, which this host does not have, so
there is no Linux build of the GUI.

Linking is dynamic, as in the distribution package, so glibc is not in the
image and about 280 functions per artefact are unnamed one- to three-
instruction .plt stubs; of 10 or more instructions only four unnamed pieces
of PuTTY's own code remain on x64 (inside ssh2_connection_free,
share_connstate_free, dsa_sign and prng_free). Executables are
position-independent by default on this gcc and are left so, because that is
what a distribution ships; on 32-bit PIC a function that touches a global
embeds this image's own GOT delta, so the x86 PicHashes of two different PuTTY
binaries rarely agree (see The Linux half in the corpus README), and the
x86 artefacts keep _init, the tm_clones pair, __do_global_dtors_aux and
__stack_chk_fail_local for the same reason. Kept 2073 of 2078 (x64 plink),
2071 of 2076 (x64 psftp), 2078 of 2085 and 2071 of 2078 (x86); 1787 to 1793 of
each are defined in PuTTY's own objects.

Another version. 0.78, built the same way, shares 1106 of its 1650 putty.exe
PicHashes with 0.77 on x64 (67%; 74% of 0.77's side) and 1214 of 1793 on x86
(68%). That is a substantial difference, but the issue is about 0.77 and no
abuse of 0.78 is reported, so it is not added.

Own code against helpers, measured by matching each reported function to the
symbols defined in PuTTY's own object files. putty.exe x64: 2244 kept of 2442
in the image (198 removed as measured MinGW glue). Of those, 1938 are defined
in PuTTY's source, 16 are libc or Win32 import thunks of one to three
instructions (Imm*, strcpy, strstr, wcscmp, __p__acmdln ...) and 290 are
unnamed: nearly all one-instruction import jumps, ___chkstk_ms (known libgcc,
PicHash ae8f920c3b4e652a x64 / dfe3cea2dbb80872 x86, left in place), and two
of PuTTY's own dialog procedures that SMDA found but whose symbols fall inside
a neighbour (255 and 43 instructions). x86 is 2044 kept of 2247: 2020 PuTTY's
own, 15 import thunks and 8 unnamed. psftp.exe: x64 1744 of 1939 (1625 own,
7 thunks, 111 unnamed), x86 1714 of 1914 (1698 own, 7 thunks, 8 unnamed). No
function of 10 or more instructions that is not PuTTY's own survives except
___chkstk_ms; no new baseline gap.

Not built: the Windows-native compilers. 0.77 has no Makefile.vc; its only
Windows build system is this CMake tree, and upstream's own release script
(Buildscr) builds the shipped binaries with clang-cl, Release, /MT /O2, so
the C runtime is linked statically (-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded).
The same tree also builds with cl on the Windows runner. Either would be a
different code shape from this MinGW one and the better match for the
official putty.exe and for a build made on a Windows host; neither can be
produced here, so no MSVC data is written. Both are follow-ups, and a static
CRT means the MSVC glue baseline needs to be checked for that link mode
before the artefacts are trusted. MinGW is itself an upstream-supported
configuration: Buildscr test-builds it with cmake/toolchain-mingw.cmake.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_RC_COMPILER={windres} "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release")


def _putty(version, sha256):
    return Recipe(
        family="PuTTY",
        version=version,
        upstream="https://www.chiark.greenend.org.uk/~sgtatham/putty/",
        license="MIT",
        source=Source(
            url="https://www.chiark.greenend.org.uk/~sgtatham/putty/%s/"
                "putty-%s.tar.gz"
                % (version, version),
            sha256=sha256),
        build=[
            # The toolchain environment exports CFLAGS=-O2, which CMake would
            # take as the initial CMAKE_C_FLAGS; emptied so the compile line is
            # exactly upstream's own.
            BuildStep(_CMAKE, env={"CFLAGS": ""}),
            BuildStep("cmake --build build-{arch} -j$(nproc) "
                      "--target putty psftp plink pscp pageant puttygen"),
        ],
        artifacts=[
            Artifact(path="build-{arch}/%s.exe" % tool, component="%s.exe" % tool)
            for tool in ("putty", "psftp", "plink", "pscp", "pageant",
                         "puttygen")
        ],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (CMake Release; upstream's cmake/setup.cmake removes "
                    "-DNDEBUG so assertions stay enabled)",
        notes="MinGW build of the unmodified 0.77 source. Upstream's own "
              "release binaries are built with clang-cl and a static C "
              "runtime, which is not covered here (the MSVC /MD build is "
              "putty_msvc.py). Six executables: putty, psftp, plink, pscp, "
              "pageant and puttygen; puttytel is not built.",
    )


# CC already carries -m32 or -m64 (toolchain.environment), and CFLAGS is
# emptied for the configure step so the compile line is upstream's own -O3
# Release flags rather than the toolchain's -O2 ahead of them.
_CMAKE_LINUX = "cmake -S . -B build-{arch} -DCMAKE_BUILD_TYPE=Release"


def _putty_linux(version, sha256):
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
            BuildStep(_CMAKE_LINUX, env={"CFLAGS": ""}),
            BuildStep("cmake --build build-{arch} -j$(nproc) "
                      "--target plink psftp"),
        ],
        artifacts=[
            Artifact(path="build-{arch}/plink", component="plink"),
            Artifact(path="build-{arch}/psftp", component="psftp"),
        ],
        toolchains=["linux_x86", "linux_x64"],
        build_flags="-O3 (CMake Release; upstream's cmake/setup.cmake removes "
                    "-DNDEBUG so assertions stay enabled), PIE, dynamic glibc",
        notes="Console tools only; the GTK programs are not built. Same "
              "tarball as the Windows artefacts. The glibc dependency is "
              "dynamic, so about 280 functions per artefact are unnamed "
              ".plt stubs.",
    )


RECIPES = {
    "PuTTY_0.77": _putty(
        "0.77",
        "419a76f45238fd45f2c76b42438993056e74fa78374f136052aaa843085beae5"),
    "PuTTY_0.77_linux": _putty_linux(
        "0.77",
        "419a76f45238fd45f2c76b42438993056e74fa78374f136052aaa843085beae5"),
}
