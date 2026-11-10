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
flag, under a name that claims a distinction the code does not have. (The
miniLZO tarball is a byte-identical subset of the minilzo/ directory in the
full tarball; minilzo.c compares equal.)

miniLZO is nevertheless built as its own artefact now (backlog #59: the issue
recommends both, and a reference that is only the 164-function full library
carries 100+ functions a miniLZO-only sample never has, which weakens a
similarity match). It is recipe ``lzo_minilzo_2.10`` (version ``minilzo-2.10``,
component ``minilzo.dll``), from the minilzo-2.10.tar.gz published beside the
full tarball: sha256 eb4ce543aad19533c83550746e0e9d7bcf716b35a42429e3ba17d60fa0f3e47a
(computed from the download; upstream lists SHA1 c7432708d49017a3f0b4f44c99d336f8a1be84f5),
minilzo.c 213674 bytes, md5 c3d88dfeeabec417b0e3ed0f74e9e91f - the size the
tracker reports for UltraVNC's lzo/minilzo.c; the UltraVNC file itself was not
re-hashed here. ``minilzo.c`` is compiled directly with -O2 -shared; no
configure step, no patch.

Counts, kept + removed = image total (x86 / x64): 21 + 53 = 74 / 30 + 54 = 84
(full library: 164 + 53 = 217 / 155 + 54 = 209). Overlap with the existing
liblzo2 artefact, PicHash: all 14 (x86) / 15 (x64) distinct hashes of miniLZO
are in the full build, and so are the 9 / 9 distinct hashes of 10+
instructions; nothing in miniLZO is new code. The artefact is kept because
a miniLZO-only sample is then matched as a near-complete image of its own
rather than as 9 functions of 100+.

Overlap with the UltraVNC data on branch claude/corpus-ultravnc-tightvnc
(winvnc 1.8.3.1 MinGW, 1.8.3.2 MSVC; vendored miniLZO is in the UltraVNC
image under its own names), miniLZO's functions of 10+ instructions by name
and PicHash. MinGW: 3 of 8 identical on both arches (``lzo_config_check``,
``_lzo_init_v2``, ``lzo_align_gap``: 147 / 57 / 11 instructions on x64) plus
the unnamed 15-instruction ``___chkstk_ms``; the compression and decompression
routines (``lzo1x_1_compress`` 179 -> 183 instructions, ``lzo1x_decompress``
310 -> 475 and so on) differ, so UltraVNC is not compiled at this -O2 and
those match by MinHash, not PicHash. MSVC: 0 of 8 against this MinGW build,
as expected for another compiler; the MSVC miniLZO artefact (lzo_msvc.py)
is the one to compare with UltraVNC's cl-built image.

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


# miniLZO as its own artefact (backlog #59), the form UltraVNC vendors. The
# minilzo-2.10 tarball is the one upstream publishes beside lzo-2.10; its
# minilzo.c is 213674 bytes, md5 c3d88dfeeabec417b0e3ed0f74e9e91f, the size the
# tracker reports for UltraVNC's lzo/minilzo.c. Four files (minilzo.c,
# minilzo.h, lzoconf.h, lzodefs.h), no configure step; compiled directly.
_MINILZO = Recipe(
    family="lzo",
    version="minilzo-2.10",
    upstream="https://www.oberhumer.com/opensource/lzo/",
    license="GPL-2.0-or-later",
    source=Source(
        url="https://www.oberhumer.com/opensource/lzo/download/minilzo-2.10.tar.gz",
        sha256="eb4ce543aad19533c83550746e0e9d7bcf716b35a42429e3ba17d60fa0f3e47a"),
    build=[BuildStep("{cc} -O2 -shared -o minilzo.dll minilzo.c")],
    artifacts=[Artifact(path="minilzo.dll", component="minilzo.dll")],
    toolchains=["mingw_x86", "mingw_x64"],
    build_flags="-O2 (minilzo.c compiled directly with -shared)",
    notes="miniLZO 2.10, the lzo1x subset vendored byte-identically in "
          "UltraVNC (minilzo.c 213674 bytes), built from the minilzo-2.10 "
          "tarball. Its functions also occur in the full liblzo2 artefact of "
          "the same release; see the recipe docstring for the measurement.",
)


RECIPES = {
    "lzo_minilzo_2.10": _MINILZO,
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
