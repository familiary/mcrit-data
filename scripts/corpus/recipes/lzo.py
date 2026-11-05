"""LZO 2.10 - the LZO1X codec, common in VNC servers, packers and game data.

No coverage exists in the corpus today (data/liblzma and data/lz4 are
different codecs). UltraVNC is the reason this is wanted: it vendors miniLZO,
which is the lzo1x subset of this library.

Full LZO or miniLZO? Both were built and compared by PicHash, MinGW 13 -O2:

    full liblzo2-2.dll   x86 164 functions   x64 155
    minilzo.dll          x86  21 functions   x64  30

Every miniLZO function, 21 of 21 on x86 and 30 of 30 on x64, has a PicHash
that also occurs in the full build: minilzo.c is the same lzo1x_1_compress,
lzo1x_decompress, lzo1x_decompress_safe and lzo_adler32 sources, compiled
identically, so it adds nothing the full library lacks. As its own family it
would have made every one of those a cross-family duplicate for --deep to
flag, under a name that claims a distinction the code does not have. Only the
full library is built, and a sample carrying miniLZO matches the lzo1x
functions in it. (The miniLZO tarball is a byte-identical subset of the
minilzo/ directory in the full tarball; minilzo.c compares equal.)

What this does not give is the MSVC code shape UltraVNC itself ships. The
UltraVNC copy was not retrieved or compared here, so "byte-identical to
upstream miniLZO" remains the issue's claim rather than something measured.

The full library is also far from small, so Recipe.min_functions is not used:
the corpus floor of eight is cleared by a wide margin (and by miniLZO too).

Upstream publishes only a SHA1 for the tarball (4924676a9bae5db58ef129dc1cebce3baa3c4b5d
on the project page); the download matched it, and the SHA-256 pinned below
was computed from those verified bytes. The tarball is dated 2017-03-01 and
has not changed since.

Build: upstream's own ./configure with --host, shared only. libtool names the
DLL liblzo2-2.dll and exports the public lzo1x/lzo1y/... API; no source patch.
Upstream's default flags are -g -O2.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


RECIPES = {
    "lzo_2.10": Recipe(
        family="lzo",
        version="2.10",
        upstream="https://www.oberhumer.com/opensource/lzo/",
        license="GPL-2.0-or-later",
        source=Source(
            url="https://www.oberhumer.com/opensource/lzo/download/lzo-2.10.tar.gz",
            sha256="c0f892943208266f9b6543b3ae308fab6284c5c90e627931446fb49b4221a072"),
        build=[
            BuildStep("make distclean", allow_failure=True),
            BuildStep("./configure --host={host} --enable-shared --disable-static"),
            BuildStep("make -j$(nproc)"),
        ],
        artifacts=[Artifact(path="src/.libs/liblzo2-2.dll",
                            component="liblzo2-2.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-g -O2 (configure default)",
        notes="Full liblzo2. miniLZO (UltraVNC's copy) is the lzo1x subset: its "
              "functions all have PicHashes present here, so it is not a "
              "separate family.",
    ),
}
