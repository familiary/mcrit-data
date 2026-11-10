"""PuTTY 0.77 as upstream distributes it: the official w32 and w64 release binaries.

putty.py and putty_msvc.py rebuild the 0.77 tarball with MinGW and with cl
/MD. Neither is the shape of the putty.exe that users download and that
UNC4034's trojanized build imitated: upstream's release script (Buildscr)
builds the shipped binaries with clang-cl, Release, ``/MT /O2``
(-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded), so the C runtime is linked in
statically. Rather than reproduce that toolchain, this recipe files the bytes
upstream actually shipped.

Pinned by the digest of the release asset, the per-architecture zip that
holds the six tools, because the binary is the thing being pinned:

    w64/putty.zip  b91cef86f839d8eaa8f86b379e45f999b071796c73e21aa373edd7e85330555f
    w32/putty.zip  2f49ec1e6c35e10ca8d263544ebfd9314dfad9a5762642d2b375fdaf846d121d

Both digests are the ones upstream's sha256sums for 0.77 lists
(https://the.earth.li/~sgtatham/putty/0.77/sha256sums), and that file's
clearsigned copy sha256sums.gpg verifies ("Good signature") against the
PuTTY release key 2CF6 134B D3F7 7A65 88EB D668 E4F8 3EA2 AA49 15EC, signed
2022-05-27 (the key has since expired, as released keys do). Each of the
twelve executables inside the zips is byte-identical to the standalone
w32/<tool>.exe and w64/<tool>.exe of the same release, whose own sha256sums
lines were checked too. The w64 zip is the recipe's source and the w32 zip a
pinned extra source; the build step only copies them into rel-x64 and rel-x86.
The Arm builds (wa32, wa64) are not taken because SMDA reads x86 and x64 only;
w32old (the Windows XP-compatible build) is not taken either.

**What compiled them**, read off the images rather than inferred from the
Linux host that runs the harvest:

  * no Rich header in any of the twelve, and PE linker version 14.0 - the
    signature of lld-link, since Microsoft's link.exe always writes a Rich
    header and stamps its own 14.x minor version;
  * PuTTY's buildinfo string, compiled into every tool, reads
    "Compiler: clang 14.0.0 (https://github.com/llvm/llvm-project/
    b6c218d4fdb74c0ee467e078721438c3396dc599)";
  * no import of msvcrt, ucrtbase, api-ms-win-crt-* or vcruntime: the C
    runtime is static, as Buildscr's /MT says.

so ``Artifact.producer`` states ``clang14``. The static CRT itself is
Microsoft's (libcmt / libucrt / libvcruntime of whatever Visual Studio and SDK
the build host had, which is not recorded), and it is inside these images.

**Names.** None. The images have no debug directory, no PDB is published, they
export nothing, and the link maps Buildscr asks for (-DPUTTY_LINK_MAPS=ON) are
not published either (404 on the.earth.li, and not in sha256sums). So every
function is ``sub_*``, ``min_named_ratio`` is 0, and nothing can be removed as
compiler runtime: the glue filter drops a body only when its name and its
PicHash both match a probe, which no unnamed body can. The static CRT bodies
therefore stay in the kept count, unnamed. What these reports add is the exact
code shape of the shipped binaries, which is what a match against a sample
built from them runs on; the source-built rows of this family are where the
names are.

What the twelve images contain, measured, kept + removed = total (nothing is
removed, see above), functions of 10+ instructions / distinct PicHashes. The
only named function in each is SMDA's ``original_entry_point``:

    x64  putty 2500+0  1978/1949   plink 2267+0  1777/1742   pscp 2258+0  1804/1770
         psftp 2308+0  1842/1806   puttygen 1266+0  1049/1024   pageant 1143+0  928/911
    x86  putty 2698+0  2194/2145   plink 2527+0  2024/1958   pscp 2518+0  2038/1973
         psftp 2577+0  2080/2013   puttygen 1503+0  1258/1204   pageant 1323+0  1087/1047

**They are not the source build.** PicHash overlap, distinct hashes of
functions of 10+ instructions, against our own cl v143 /MD build of the same
program (putty_msvc.py):

    x64  putty 3 of 1949   plink 1 of 1742   pscp 1 of 1770   psftp 1 of 1806
         puttygen 2 of 1024   pageant 2 of 911
    x86  putty 7 of 2145   plink 5 of 1958   pscp 4 of 1973   psftp 4 of 2013
         puttygen 3 of 1204   pageant 4 of 1047

and against every image already committed in the family (MinGW, MSVC, Linux)
at most 8 of 2145 (x86 putty, 0.4%). A different compiler (clang against cl
and GCC) and a different C runtime linkage change essentially every function,
so these twelve are a reference value of their own: what a match against the
binary users actually download, or a sample built from it, runs on. None is
PicHash-identical to a committed image.

Within the release set, the share of each tool's hashes already in
putty_release.exe: plink 89.3% / 90.5% (x64 / x86), pscp 84.7% / 86.5%, psftp
83.1% / 84.5%, puttygen 83.6% / 86.4%, pageant 89.1% / 91.7%. Part of every
image, and part of that shared share, is the statically linked Microsoft C
runtime, which cannot be told apart from PuTTY's code without names. The x86
and x64 putty_release.exe share no hash.

The release directory also carries pterm.exe and puttytel.exe (standalone,
not in putty.zip); the six tools the tracker issue names are the ones taken.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_TOOLS = ("putty", "plink", "pscp", "psftp", "puttygen", "pageant")

_W64_ZIP = ("https://the.earth.li/~sgtatham/putty/0.77/w64/putty.zip",
            "b91cef86f839d8eaa8f86b379e45f999b071796c73e21aa373edd7e85330555f")
_W32_ZIP = ("https://the.earth.li/~sgtatham/putty/0.77/w32/putty.zip",
            "2f49ec1e6c35e10ca8d263544ebfd9314dfad9a5762642d2b375fdaf846d121d")

_NOTES = (
    "Harvested, not rebuilt: the official PuTTY 0.77 release executables "
    "from w64/putty.zip and w32/putty.zip on the.earth.li, pinned by the "
    "sha256 that upstream's PGP-signed sha256sums lists (verified against "
    "release key 2CF6134BD3F77A6588EBD668E4F83EA2AA4915EC). The producer is "
    "read off the images: no Rich header and PE linker version 14.0 "
    "(lld-link), PuTTY's own buildinfo string 'Compiler: clang 14.0.0', and "
    "no C runtime DLL import (static /MT, as upstream's Buildscr builds them "
    "with clang-cl /MT /O2). No PDB, no debug directory, no exports and no "
    "published link map, so no function is named and none can be removed as "
    "compiler runtime; the statically linked Microsoft C runtime is inside "
    "these images, unnamed. Not a duplicate of the cl /MD rebuild "
    "(putty_msvc.py): see the recipe docstring for the measured overlap.")


RECIPES = {
    "PuTTY_0.77_prebuilt": Recipe(
        family="PuTTY",
        version="0.77",
        upstream="https://www.chiark.greenend.org.uk/~sgtatham/putty/",
        license="MIT",
        source=Source(url=_W64_ZIP[0], sha256=_W64_ZIP[1]),
        extra_sources={"w32_putty_zip": Source(url=_W32_ZIP[0],
                                               sha256=_W32_ZIP[1])},
        # Nothing to build: both zips are unpacked side by side and the
        # executables taken as they are. The sha256 of each is logged.
        build=[BuildStep(
            "mkdir -p rel-x64 rel-x86 && "
            "cp PAGEANT.EXE PLINK.EXE PSCP.EXE PSFTP.EXE PUTTY.EXE "
            "PUTTYGEN.EXE rel-x64/ && "
            "unzip -oq {w32_putty_zip} -d rel-x86 && "
            "sha256sum rel-x86/*.EXE rel-x64/*.EXE")],
        # The component is not "putty.exe": the MinGW and MSVC rebuilds
        # already use those, and refresh_provenance tells a harvested
        # prebuilt from a rebuild of the same version by component.
        artifacts=[Artifact(path="rel-{arch}/%s.EXE" % tool.upper(),
                            component="%s_release.exe" % tool,
                            producer="clang14")
                   for tool in _TOOLS],
        # A toolchain selects nothing here but which leg's file is read; the
        # architecture in the stem comes from the PE header.
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="clang-cl 14.0.0 (LLVM b6c218d4fdb7), lld-link, Release "
                    "/MT /O2 per upstream's Buildscr (as distributed by "
                    "upstream; read off the images: no Rich header, linker "
                    "14.0, buildinfo 'Compiler: clang 14.0.0')",
        min_named_ratio=0,
        notes=_NOTES,
    ),
}
