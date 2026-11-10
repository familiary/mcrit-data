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
client (sftp.c, psftp.c, psftpcommon.c). The tracker issue (#65) names six
executables, so plink, pscp, pageant and puttygen are built as well although
they add little beyond putty and psftp. puttytel and psocks, the two
Windows programs left, are built by PuTTY_0.77_puttytel_psocks (see
puttytel and psocks below). Measured on
the images as committed (distinct PicHashes of 10+ instructions, x64 / x86),
the share of each new tool already in putty.exe + psftp.exe: plink 98.9% /
99.2% (12 / 10 new hashes), pscp 97.7% / 97.9% (26 / 27), pageant 86.9% /
86.4% (76 / 86), puttygen 82.7% / 84.3% (112 / 111). Kept + removed = image:
plink x64 1735+192=1927, x86 1708+198=1906; pscp x64 1722+197=1919, x86
1693+202=1895; pageant x64 856+144=1000, x86 763+148=911; puttygen x64
949+186=1135, x86 850+192=1042. Those four were built by the scoped CI run
42678836328 (MinGW-w64 GCC 13.2.0-6ubuntu1+26.1 on ubuntu-24.04, the same
packages as the host that built putty.exe and psftp.exe); the same run also
rebuilt putty.exe and psftp.exe, which were NOT re-imported: x64 came out
with the committed counts, x86 with 2 more kept functions each (putty
2046+203, psftp 1716+200, against the committed 2044+203 and 1714+200), and
every sha256 differs, the build directory being part of the image.

puttytel and psocks. Same tarball, toolchain and flags, a recipe of its own
so the six images above are not rebuilt. Kept + removed = image, functions of
10+ instructions / distinct PicHashes, and the share of those hashes already
in the six MinGW images of the same architecture:

    x64  puttytel 1245+183=1428  666/660  98.2% (12 new; 645 in putty.exe)
         psocks    499+181=680   289/285  87.7% (35 new)
    x86  puttytel 1020+184=1204  727/715  99.4% (4 new; 710 in putty.exe)
         psocks    491+181=672   328/318  90.6% (30 new)

puttytel is putty.exe without the SSH backends, so nearly all of it is
already in putty.exe; it is a separate shipped binary and its PicHash set
is not identical to any committed image, so it is kept with that overlap
stated. psocks adds the SOCKS front end (psocks.c, windows/psocks.c).

Linux. PuTTY's SSH core is portable and ships on Linux (Debian's
putty-tools: plink, pscp, psftp, puttygen), so the same tree was built with the
host gcc for both ELF architectures and measured. It shares no PicHash with
the Windows build on x64 (0 of 1231 plink and 0 of 1269 psftp functions of 10
or more instructions) and 84 of 1452 / 80 of 1490 on x86, because the ABI
changes every function: a different reference value, so plink and psftp are
kept (PuTTY_0.77_linux). In the Linux set psftp is the base and plink adds 81
functions on x64 (the Unix console front end, uxplink.c); pscp adds 28 beyond
those two and puttygen 77 (a key tool, not the SSH client). Both are built by
PuTTY_0.77_linux_pscp_puttygen, same tarball and flags, a recipe of its own
so plink and psftp are not rebuilt; like those two they were configured on a
host without GTK (NOT_X_WINDOWS on). Kept + removed = image, functions of 10+
instructions / distinct PicHashes, share of those hashes already in the
committed Linux plink + psftp of the same architecture:

    x64  pscp     2053+5=2058  1309/1254  97.8% (28 new)
         puttygen  994+5=999    656/631   87.8% (77 new)
    x86  pscp     2053+7=2060  1497/1476   9.7% (1333 new)
         puttygen  998+9=1007   750/742   12.5% (649 new)

The x86 figures are low for the 32-bit PIC reason given below (a function that
touches a global embeds this image's own GOT delta), not because the code
differs. None is PicHash-identical to a committed image. The GTK programs are
the GTK paragraph below.

GTK. PuTTY_0.77_linux_gtk builds the four GTK 3 programs, putty, pterm,
puttytel and pageant (Linux pageant needs GTK for its passphrase prompt),
from the same tarball and flags. GTK is not installed on the build host: apt
cannot co-install libgtk-3-dev for amd64 and i386 there
("libglib2.0-dev:i386 : Depends: libglib2.0-dev-bin:i386", which would
replace the host's amd64 python3), and a host-wide install would also turn
NOT_X_WINDOWS off for every other Linux build on that machine, the console
tools above included. Instead each leg downloads the Ubuntu 24.04 packages
listed in putty_gtk_sysroot.txt (the Depends closure of libgtk-3-dev and
libglib2.0-dev, GTK 3.24.41, GLib 2.80.0, Pango 1.52.1, cairo 1.18.0, libX11
1.8.7, each pinned by the sha256 of the archive index), checks every digest,
unpacks them into a private sysroot, and configures with PKG_CONFIG_SYSROOT_DIR
and CMAKE_PREFIX_PATH pointing there, -DPUTTY_GTK_VERSION=3, and
-L/-rpath-link to the sysroot's libdir (without -L upstream's
check_symbol_exists probes for pango_font_family_is_monospace and
pango_font_map_list_families fail to link and silently select the fallback
code; with it both are found, as on a distribution host). GDK's X11 backend
is found, so NOT_X_WINDOWS is off. PuTTY's tree is not modified; only the
sysroot's absolute symlinks are re-pointed inside it.

Kept + removed = image, functions of 10+ instructions / distinct PicHashes,
then the share of those hashes in the committed Linux console tools of the
same architecture and in the GTK putty:

    x64  putty    3302+5=3307  1665/1621  73.5% in console tools (430 new)
         pterm    1905+5=1910   682/671   33.7%; 96.9% in GTK putty
         puttytel 2179+5=2184   821/808   46.7%; 99.9% in GTK putty (807)
         pageant  1519+5=1524   828/797   89.5%; 87.0% in GTK putty
    x86  putty    3302+7=3309  1893/1872   8.2% in console tools
         pterm    1916+5=1921   780/779    4.1%;  7.3% in GTK putty
         puttytel 2187+5=2192   944/943    5.2%;  7.8% in GTK putty
         pageant  1526+7=1533   958/948   10.2%; 10.2% in GTK putty

The x86 shares are low for the 32-bit PIC reason below, not because the code
differs. puttytel on x64 is putty without the SSH backends and shares 807 of
its 808 hashes with putty; it is kept as a separate shipped program with that
overlap stated, since no image here is PicHash-identical to another. Removed
as glue: the five crtstuff/_init functions on x64; on x86 frame_dummy and the
four __x86.get_pc_thunk.* helpers, plus __divdi3 and __udivdi3 in putty and
pageant.

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

MSVC. putty_msvc.py builds the same six with cl (v143) against the DLL
runtime. Upstream's own release script (Buildscr) builds the shipped binaries
with clang-cl, Release, /MT /O2 (-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded),
so the C runtime is linked statically there. That build is not reproduced;
putty_prebuilt.py harvests upstream's own signed w32/w64 release binaries
instead, which share at most 0.4% of their PicHashes with anything built
here. MinGW is itself an upstream-supported configuration: Buildscr
test-builds it with cmake/toolchain-mingw.cmake.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_RC_COMPILER={windres} "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release")


_TOOLS = ("putty", "psftp", "plink", "pscp", "pageant", "puttygen")

_NOTES = ("MinGW build of the unmodified 0.77 source. Upstream's own "
          "release binaries are built with clang-cl and a static C "
          "runtime; they are harvested as distributed by putty_prebuilt.py "
          "(the MSVC /MD build is putty_msvc.py). Six executables: putty, "
          "psftp, plink, pscp, pageant and puttygen; puttytel and psocks "
          "come from the PuTTY_0.77_puttytel_psocks recipe.")


def _putty(version, sha256, tools=_TOOLS, notes=_NOTES):
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
                      "--target %s" % " ".join(tools)),
        ],
        artifacts=[
            Artifact(path="build-{arch}/%s.exe" % tool, component="%s.exe" % tool)
            for tool in tools
        ],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (CMake Release; upstream's cmake/setup.cmake removes "
                    "-DNDEBUG so assertions stay enabled)",
        notes=notes,
    )


# CC already carries -m32 or -m64 (toolchain.environment), and CFLAGS is
# emptied for the configure step so the compile line is upstream's own -O3
# Release flags rather than the toolchain's -O2 ahead of them.
_CMAKE_LINUX = "cmake -S . -B build-{arch} -DCMAKE_BUILD_TYPE=Release"


_LINUX_NOTES = ("Console tools only; the GTK programs are built by "
                "PuTTY_0.77_linux_gtk. Same "
                "tarball as the Windows artefacts. The glibc dependency is "
                "dynamic, so about 280 functions per artefact are unnamed "
                ".plt stubs.")


def _putty_linux(version, sha256, tools=("plink", "psftp"),
                 notes=_LINUX_NOTES):
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
                      "--target %s" % " ".join(tools)),
        ],
        artifacts=[Artifact(path="build-{arch}/%s" % tool, component=tool)
                   for tool in tools],
        toolchains=["linux_x86", "linux_x64"],
        build_flags="-O3 (CMake Release; upstream's cmake/setup.cmake removes "
                    "-DNDEBUG so assertions stay enabled), PIE, dynamic glibc",
        notes=notes,
    )


_EXTRA_NOTES = (
    "MinGW build of the unmodified 0.77 source, same tarball, toolchain and "
    "flags as the six-tool recipe beside it: puttytel.exe (the Telnet/raw/"
    "serial-only build of the PuTTY GUI) and psocks.exe (the SOCKS proxy "
    "server sharing PuTTY's port-forwarding code). A separate recipe so the "
    "six committed images are not rebuilt.")

_LINUX_EXTRA_NOTES = (
    "Linux console tools pscp and puttygen from the same tarball and flags "
    "as the plink/psftp recipe; a separate recipe so those two are not "
    "rebuilt. The glibc dependency is dynamic, so the .plt stubs are "
    "unnamed.")


# The GTK programs. Ubuntu cannot co-install libgtk-3-dev for amd64 and i386
# (libglib2.0-dev:i386 needs libglib2.0-dev-bin:i386, which would replace
# the host's amd64 python3), and installing it on the shared build host would
# also flip NOT_X_WINDOWS for every other Linux build there. So each leg
# unpacks the pinned .debs of putty_gtk_sysroot.txt into a private sysroot,
# verifies every one against the sha256 the Ubuntu archive index lists, and
# points pkg-config and CMake at it. Nothing in PuTTY's tree is touched; the
# sysroot's absolute symlinks are re-pointed inside it.
_GTK_SYSROOT = (
    "A=$([ {bitness} = 64 ] && echo amd64 || echo i386) && "
    "mkdir -p debs sysroot && : > debs/SHA256SUMS && "
    "grep -E \"_($A|all)\\.deb \" {repo}/scripts/corpus/recipes/putty_gtk_sysroot.txt | "
    "while read name version file sha; do "
    "curl -sSfL --retry 5 --retry-all-errors -o debs/$(basename $file) "
    "https://archive.ubuntu.com/ubuntu/$file || exit 1; "
    "echo \"$sha  debs/$(basename $file)\" >> debs/SHA256SUMS; done && "
    "sha256sum -c --quiet debs/SHA256SUMS && wc -l < debs/SHA256SUMS && "
    "for d in debs/*.deb; do dpkg-deb -x $d sysroot || exit 1; done && "
    "find sysroot -type l -lname '/*' | while read l; do "
    "ln -sfn \"$PWD/sysroot$(readlink $l)\" $l; done && rm -rf debs")

_GTK_CMAKE = (
    "T=$([ {bitness} = 64 ] && echo x86_64-linux-gnu || echo i386-linux-gnu) && "
    "S=$PWD/sysroot && "
    "PKG_CONFIG_SYSROOT_DIR=$S "
    "PKG_CONFIG_LIBDIR=$S/usr/lib/$T/pkgconfig:$S/usr/share/pkgconfig "
    "cmake -S . -B build-{arch} -DCMAKE_BUILD_TYPE=Release "
    "-DPUTTY_GTK_VERSION=3 -DCMAKE_LIBRARY_ARCHITECTURE=$T "
    "-DCMAKE_PREFIX_PATH=$S/usr "
    "-DCMAKE_EXE_LINKER_FLAGS=\"-L$S/usr/lib/$T "
    "-Wl,-rpath-link,$S/usr/lib/$T\" && "
    "grep -E '^GTK_FOUND:INTERNAL=1$' build-{arch}/CMakeCache.txt && "
    "grep -E '^X11_X11_LIB:|^HAVE_PANGO|^HAVE_GDK|^GTK_VERSION:' "
    "build-{arch}/CMakeCache.txt")

_GTK_TOOLS = ("putty", "pterm", "puttytel", "pageant")

_GTK_NOTES = (
    "GTK 3 programs (putty, pterm, puttytel, pageant) from the unmodified "
    "0.77 tarball, same -O3 Release flags as the console recipes, linked "
    "dynamically against GTK 3.24.41 / GLib 2.80.0 / X11 from Ubuntu 24.04 "
    "packages unpacked into a private sysroot, each .deb pinned by the sha256 "
    "of the archive index (scripts/corpus/recipes/putty_gtk_sysroot.txt). "
    "With GDK's X11 backend present NOT_X_WINDOWS is off, as in a "
    "distribution build. Not the console tools' configuration, which had no "
    "GTK and so NOT_X_WINDOWS on.")


def _putty_gtk(version, sha256):
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
            BuildStep(_GTK_SYSROOT),
            BuildStep(_GTK_CMAKE, env={"CFLAGS": ""}),
            BuildStep("cmake --build build-{arch} -j$(nproc) --target %s"
                      % " ".join(_GTK_TOOLS)),
            # The sysroot is several hundred MB and nothing reads it after
            # the link.
            BuildStep("rm -rf sysroot"),
        ],
        artifacts=[Artifact(path="build-{arch}/%s" % tool, component=tool)
                   for tool in _GTK_TOOLS],
        toolchains=["linux_x86", "linux_x64"],
        requires=["dpkg-deb", "pkg-config", "curl"],
        build_flags="-O3 (CMake Release; upstream's cmake/setup.cmake removes "
                    "-DNDEBUG so assertions stay enabled), PIE, dynamic glibc, "
                    "GTK 3.24.41 and X11 from a pinned Ubuntu 24.04 sysroot "
                    "(-DPUTTY_GTK_VERSION=3, NOT_X_WINDOWS off)",
        notes=_GTK_NOTES,
    )


RECIPES = {
    "PuTTY_0.77": _putty(
        "0.77",
        "419a76f45238fd45f2c76b42438993056e74fa78374f136052aaa843085beae5"),
    "PuTTY_0.77_linux": _putty_linux(
        "0.77",
        "419a76f45238fd45f2c76b42438993056e74fa78374f136052aaa843085beae5"),
    # The two Windows programs the six above leave out, from the same tree
    # with the same flags, as a recipe of their own so that building them
    # does not rebuild (and re-hash) the six committed images.
    "PuTTY_0.77_puttytel_psocks": _putty(
        "0.77",
        "419a76f45238fd45f2c76b42438993056e74fa78374f136052aaa843085beae5",
        tools=("puttytel", "psocks"),
        notes=_EXTRA_NOTES),
    # Likewise the two console tools the Linux recipe above leaves out.
    "PuTTY_0.77_linux_pscp_puttygen": _putty_linux(
        "0.77",
        "419a76f45238fd45f2c76b42438993056e74fa78374f136052aaa843085beae5",
        tools=("pscp", "puttygen"),
        notes=_LINUX_EXTRA_NOTES),
    # The GTK programs, Linux ELF, against a pinned private GTK 3 sysroot.
    "PuTTY_0.77_linux_gtk": _putty_gtk(
        "0.77",
        "419a76f45238fd45f2c76b42438993056e74fa78374f136052aaa843085beae5"),
}
