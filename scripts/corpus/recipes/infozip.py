"""Info-ZIP zip 3.0 / 3.1c and unzip 6.0 / funzip 6.0 - the other deflate and
inflate in the wild.

The FOSSIL study matched Info-ZIP's compression code in all five malware
families it analysed. It is not zlib: Info-ZIP's deflate (deflate.c, trees.c)
and inflate (inflate.c, explode.c, unshrink.c, unreduce.c) predate zlib and
zlib was written from the same lineage by Jean-loup Gailly and Mark Adler, but
the code that ships is separate and shares no PicHash with data/libzlib or
data/7-Zip (measured, see the README).

Two programs, two recipes, one family. zip and unzip are versioned
independently (3.0 and 6.0) and are different code bases, so each is built
from its own tarball. Both are programs, not libraries - upstream's win32
makefiles produce executables (plus zipcloak/zipnote/zipsplit and
unzipsfx/unzip32.dll that are not built, below; funzip is built, see the end of
the next section) - so the artefacts are
EXEs and the deflate/inflate code is the reusable part inside them.

Neither project publishes a checksum. Both tarballs were fetched from
SourceForge and from Debian's pool (orig.tar.gz) and were byte identical; the
sha256 below was computed from that download by whoever wrote this recipe.

Measured, MinGW GCC 13, glue baseline applied (kept + removed = image):

    zip.exe 3.0    x86  245 + 208 = 453    x64  317 + 204 = 521
    unzip.exe 6.0  x86  130 + 154 = 284    x64  213 + 149 = 362

The project's own compression code is a minority of each image. In zip it is
deflate.c (deflate, fill_window, lm_init, lm_free, longest_match) and trees.c
(ct_init, ct_tally, flush_block, compress_block, build_tree, send_tree,
scan_tree, pqdownheap, send_bits, bi_init, bi_windup, copy_block, init_block):
18 functions, 2140 of 31981 instructions on x86. In unzip it is inflate.c
(inflate, inflate_codes, inflate_dynamic, inflate_fixed, inflate_free,
huft_build, huft_free), explode.c (explode, get_tree) and unshrink.c
(unshrink): 10 functions, 3426 of 23320 instructions on x86. unreduce.c
compiles to nothing. The rest is the program - option parsing, zipfile and
extra-field handling, win32 and NT security glue - and each exe also keeps
the crc32 and traditional-crypt code.

Overlap with data/libzlib (every committed build) and data/7-Zip, by exact
PicHash: none of those 28 functions matches. The only cross-family hash at
ten instructions or more is the unnamed libgcc ___chkstk_ms probe (x86
dfe3cea2dbb80872, x64 ae8f920c3b4e652a), already known. The smaller matches
(35 of 245 x86 zip functions) are all under ten instructions: msvcrt import
thunks and, for lm_free, a one-instruction tail jump to free(). Info-ZIP's deflate is its own
code, as expected; what a matcher gets from this family is not shared with
zlib or 7-Zip.

Added for r0ny123/mcrit-data#23 (which asks for zip 3.1, unzip 6.0, funzip,
and a build without USE_ZLIB recorded in the notes):

zip 3.1 was never released. SourceForge's project files
(https://sourceforge.net/projects/infozip/files/) list "Zip 3.x (latest)" with
a single version, 3.0 (zip30.tar.gz, zip30.zip), and keep the 3.1 line under
"unreleased Betas/Zip betas": zip31a.zip (revision.h REVDATE "Sep 21st 2008",
VERSION "3.1a BETA"), zip31b.zip ("Apr 9th 2009", "3.1b BETA") and zip31c.zip
("Jun 22nd 2010", "3.1c BETA"), none later. Z_MAJORVER/Z_MINORVER are 3/1 in
all three, which is the "zip 3.1" the FOSSIL study lists (343 functions, a
count this build does not reproduce: see below). ftp.info-zip.org/pub/infozip/
could not be listed from the build host (the proxy answered HTTP 502), so the
upstream FTP mirror was not checked; the SourceForge file lists are the
evidence. The nearest real state is the newest beta, 3.1c, built here as
`infozip_zip_3.1c` from zip31c.zip (sha256 fda6d053..., equal to the digest
SourceForge lists for the file). It is a beta, labelled as one in the
provenance notes, and not the same code as 3.0: 109 of 185 (x64) and 118 of
189 (x86) PicHashes of the 3.0 zip.exe's 10+ instruction functions are also in
3.1c. 3.1a and 3.1b are built too (below). unzip's 6.1 betas (unzip610a/b.zip) exist
too and are not what the issue asks for.

3.1c's win32/makefile.gcc is not 3.0's. The assembler fast paths are ON unless
NOASM=1 (3.0 spells that OBJA= CRCA_O= CRCAUO= NO_ASM), its default is -O3
rather than -O2, it has no OBJA, and it also builds bzip2/zlib variants behind
USEBZ2/USEZLIB, neither set. A first attempt that reused the 3.0 overrides
failed with "match.S:403: Error: no such instruction: `this asm version is for
386 or 680x0 only'" (x64) and, once those were removed, "crc_i386.S:306:
Error: junk at end of line, first unrecognized character is `-'".

Without USE_ZLIB, recorded. Neither program here uses zlib: zip's makefile
only adds -DUSE_ZLIB when USEZLIB=1 is passed, which none of these builds do
(`-DUSE_ZLIB` occurs 0 times in the 3.1c build log, and the log shows deflate.c
and trees.c compiled), so the images carry Info-ZIP's own deflate: for 3.1c
16 named functions (deflate, fill_window, lm_init, lm_free, longest_match,
ct_init, ct_tally, flush_block, compress_block, build_tree, send_tree,
scan_tree, send_bits, bi_init, bi_windup, copy_block), 2533 of 36697
instructions on x86 and 2808 of 34847 on x64. The overlap of zip 3.1c's 10+
instruction PicHashes with every libzlib image and every 7-Zip image of the
same architecture is one hash, the unnamed 15-instruction libgcc ___chkstk_ms
probe the README already lists. Had USEZLIB=1 been used the image would be a
copy of data/libzlib, which is what the issue warns about. unzip 6.0 has no
zlib option at all.

funzip 6.0 (a second artefact of `infozip_unzip_6.0`: win32/Makefile.gcc
target funzip.exe from the unzip 6.0 tarball, same flags as unzip.exe): x86 22 + 134 = 156, x64
42 + 130 = 172 (kept + removed = total). Its own code is the stream filter
(main, err, getp, getch_win32) plus inflate.c (inflate, inflate_codes,
inflate_dynamic, inflate_fixed, inflate_free, huft_build, huft_free), crc32.c
and cryptf.c (decrypt_byte, init_keys, update_keys). The x64 image also keeps
20 one-instruction import thunks. PicHash overlap with unzip.exe 6.0: 11 of 16
(x86) and 7 of 18 (x64) of funzip's 10+ instruction functions, i.e. inflate.c
and crc32; the FOSSIL table lists funzip at 79 functions, again not
reproduced (this build is at -O2 with the glue baseline applied).

Measured zip 3.1c, glue baseline applied (kept + removed = image):

    zip.exe 3.1c   x86  247 + 209 = 456    x64  321 + 205 = 526

zip 3.1a and 3.1b (second pass for #23, so that every published 3.1 state is
in the corpus): `infozip_zip_3.1a` / `infozip_zip_3.1b` from SourceForge's
unreleased Betas/Zip betas/zip31a.zip (sha256 b68a8d1b..., 1380316 bytes) and
zip31b.zip (sha256 44e931c1..., 1473394 bytes); both digests equal the ones
SourceForge's file listing gives for those files. ftp.info-zip.org was tried
again and is unreachable from the build host (CONNECT answered HTTP 502, the
ftp host does not resolve), and no other mirror was used, so SourceForge is the
only source checked. win32/makefile.gcc of both has the same NOASM/NOASMATCH/
NOASMCRC switches and the same object lists as 3.1c's, so the recipe shape and
the overrides (NOASM=1, LDFLAGS='-o$@', LOCAL_ZIP='-include windows.h') are
the 3.1c ones unchanged; no source patch. 3.1b and 3.1c ship a zipfile1.c that no makefile lists
(3.1a has none); it is not compiled in any of the three builds.

Measured zip 3.1a / 3.1b, glue baseline applied (kept + removed = image):

    zip.exe 3.1a   x86  245 + 210 = 455    x64  317 + 204 = 521
    zip.exe 3.1b   x86  245 + 210 = 455    x64  318 + 205 = 523

PicHash overlap, 10+ instruction functions, MinGW (x86 / x64; the diagonal is
the number of such PicHashes in the image):

    3.0 189 / 185   3.1a 191 / 187   3.1b 191 / 187   3.1c 193 / 189
    3.0 vs 3.1a 127 / 118   3.0 vs 3.1b 122 / 112   3.0 vs 3.1c 118 / 109
    3.1a vs 3.1b 181 / 177  3.1a vs 3.1c 171 / 167   3.1b vs 3.1c 180 / 176

The 3.1 betas are one code line: 3.1b shares 181 of 191 (x86) with 3.1a and
3.1c shares 180 with 3.1b, while each shares only 109 to 127 with 3.0.

Both build with upstream's own makefile (win32/makefile.gcc for zip,
win32/Makefile.gcc for unzip), with command-line overrides and no source
patch. Four settings are needed and the first is not obvious:

  -include windows.h  - mingw-w64's winnt.h declares an ARM64 struct with a
                        bitfield named CR, and both programs define `CR` as
                        13 before they include <windows.h>. The macro then
                        rewrites the header. Including windows.h first lets
                        the header's include guard stop it being read again
                        after the macro exists. Passed through each
                        makefile's own hook (LOCAL_ZIP, LOCAL_UNZIP).
  NO_ASM / NOASM=1    - the assembler fast paths (match.S, crc_i386.S) are
                        32-bit only; match.S stops the x64 build with "this
                        asm version is for 386 or 680x0 only". Disabled on
                        both architectures so x86 and x64 are the same C and
                        deflate.c's longest_match is the C one a MSVC build
                        has. zip's OBJA/CRCA_O/CRCAUO are emptied to match.
  LDFLAGS / LD_RELEASE_OPT - both makefiles link with -s, which discards the
                        COFF symbol table this corpus names functions from.
  CC_CPU_OPT=         - unzip passes -mcpu=pentiumpro by default.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_NOTE_LICENSE = "Info-ZIP"

_BETAS = {"3.1a": "Sep 21st 2008", "3.1b": "Apr 9th 2009",
          "3.1c": "Jun 22nd 2010"}


def _note_beta(version):
    if version == "3.1c":
        return ("Version 3.1c is Info-ZIP's last public beta (Jun 22nd 2010); "
                "a final zip 3.1 was never released, so this is the nearest "
                "real state of the 3.1 line. ")
    return ("Version %s is an earlier public beta of the 3.1 line (%s BETA, "
            "%s); a final zip 3.1 was never released, so this is a state of "
            "the 3.1 line, not a release. "
            % (version, version.upper(), _BETAS[version]))


_INCLUDE = "-include windows.h"


_ZIP30_URL = "https://downloads.sourceforge.net/infozip/zip30.tar.gz"

def _beta_url(version):
    return ("https://downloads.sourceforge.net/project/infozip/"
            "unreleased%%20Betas/Zip%%20betas/zip%s.zip"
            % version.replace(".", ""))


_NO_ZLIB = ("USE_ZLIB (USEZLIB=1 in win32/makefile.gcc) is NOT set, so "
            "deflate.c and trees.c are compiled and the image carries "
            "Info-ZIP's own deflate, not zlib's. ")


_ZIP30_MAKE = ("make -f win32/makefile.gcc CC={cc} RC={windres} "
               "LDFLAGS='-o$@' LOCAL_ZIP='-DNO_ASM %s' "
               "OBJA= CRCA_O= CRCAUO= zip.exe" % _INCLUDE)
# 3.1c's makefile is organised differently: no OBJA, and the assembler fast
# paths are ON unless NOASM=1 is given (it then leaves USE_ASMMATCH and
# USE_ASMCRC empty itself). NOASM=1 is the same intent as the 3.0 overrides:
# match.S / crc_i386.S are 32-bit only and do not assemble for x64.
_ZIP31_MAKE = ("make -f win32/makefile.gcc CC={cc} RC={windres} NOASM=1 "
               "LDFLAGS='-o$@' LOCAL_ZIP='%s' zip.exe" % _INCLUDE)


def _zip(version, sha256, url=_ZIP30_URL, beta=False):
    return Recipe(
        family="Info-ZIP",
        version=version,
        upstream="https://infozip.sourceforge.net/Zip.html",
        license=_NOTE_LICENSE,
        source=Source(url=url, sha256=sha256),
        build=[
            BuildStep("make -f win32/makefile.gcc clean", allow_failure=True),
            BuildStep(_ZIP31_MAKE if beta else _ZIP30_MAKE),
        ],
        artifacts=[Artifact(path="zip.exe", component="zip.exe")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags=("-O3 (win32/makefile.gcc default), NOASM=1" if beta else
                     "-O2 (win32/makefile.gcc default), NO_ASM"),
        notes=_NO_ZLIB + (_note_beta(version) if beta else "") +
              "zip.exe only: zipcloak, zipnote and zipsplit link the same "
              "zipfile/fileio/util/crc32 objects again, built with -DUTIL, so "
              "they would duplicate zip.exe's functions under a second "
              "component. Assembler fast paths disabled (32-bit only).",
    )


def _unzip(version, sha256):
    return Recipe(
        family="Info-ZIP",
        version=version,
        upstream="https://infozip.sourceforge.net/UnZip.html",
        license=_NOTE_LICENSE,
        source=Source(url="https://downloads.sourceforge.net/infozip/unzip60.tar.gz",
                      sha256=sha256),
        build=[
            BuildStep("make -f win32/Makefile.gcc clean", allow_failure=True),
            BuildStep("make -f win32/Makefile.gcc CC={cc} RC={windres} NOASM=1 "
                      "CC_CPU_OPT= LD_RELEASE_OPT= LOCAL_UNZIP='%s' "
                      "unzip.exe funzip.exe" % _INCLUDE),
        ],
        artifacts=[Artifact(path="unzip.exe", component="unzip.exe"),
                   Artifact(path="funzip.exe", component="funzip.exe")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 (win32/Makefile.gcc default), NOASM",
        notes="unzip.exe and funzip.exe (the stream filter, the same "
              "inflate.c compiled with -DFUNZIP plus funzip.c, crc32.c and "
              "cryptf.c); unzipsfx is the same inflate.c compiled with -DSFX, "
              "and unzip32.dll is the same objects again, so neither is "
              "built. unzip does not use zlib at any point. Assembler CRC "
              "disabled (32-bit only).",
    )


RECIPES = {
    "infozip_zip_3.0": _zip(
        "3.0", "f0e8bb1f9b7eb0b01285495a2699df3a4b766784c1765a8f1aeedf63c0806369"),
    "infozip_zip_3.1a": _zip(
        "3.1a", "b68a8d1b3c759622cf9f9c01fa9823b041ed18a89c2e78eafc37991ab5428acf",
        url=_beta_url("3.1a"), beta=True),
    "infozip_zip_3.1b": _zip(
        "3.1b", "44e931c10b1748cb43e4ea4fb7d58f134551a478f5f8afaf0f2cfb613adc25bb",
        url=_beta_url("3.1b"), beta=True),
    "infozip_zip_3.1c": _zip(
        "3.1c", "fda6d0532c201597ea13ccdbcdc6f39b4a4ce666df0048e19f6b0f969aff398b",
        url=_beta_url("3.1c"), beta=True),
    "infozip_unzip_6.0": _unzip(
        "6.0", "036d96991646d0449ed0aa952e4fbe21b476ce994abc276e49d30e686708bd37"),
}


# --- The other executables upstream's makefiles build, and the x86
# assembler fast paths. The recipes above record zip.exe, unzip.exe and
# funzip.exe only. zipcloak, zipnote and zipsplit are not zip.exe relinked:
# each is its own main (zipcloak.c, zipnote.c, zipsplit.c) plus zipfile,
# fileio, util and crc32 compiled again with -DUTIL, which drops the
# compression code and changes the shared files; unzipsfx is unzip compiled
# again with -DSFX, and unzip32.dll is the DLL API (windll.c, api.c) with
# -DWINDLL -DDLL. Each is built by the same makefile with the same overrides
# as the shipped recipes, as separate versions ("<v>-utils", "6.0-sfxdll")
# so the shipped images are unchanged. The "-asm" versions are x86 only:
# upstream's default x86 build with match.S and crc_i386.S assembled in,
# which the shipped C-only recipes leave out for like-for-like x86/x64.
# The makefiles assemble match.S and crc_i386.S with $(CC) and ASFLAGS that
# include LOC/LOCFLAGS, so the -include windows.h the C files need reached
# the assembler ("vadefs.h:24: Error: no such instruction: `typedef
# __builtin_va_list __gnuc_va_list'"); ASFLAGS=-c on the command line keeps
# it to the C files (ASDEFS is empty without USE_ZLIB).
_UTILS = ["zipcloak.exe", "zipnote.exe", "zipsplit.exe"]
_ZIP30_UTILS_MAKE = _ZIP30_MAKE.replace(" zip.exe", " " + " ".join(_UTILS))
_ZIP31_UTILS_MAKE = _ZIP31_MAKE.replace(" zip.exe", " " + " ".join(_UTILS))


def _zip_utils(base):
    import dataclasses
    recipe = RECIPES[base]
    beta = recipe.version != "3.0"
    return dataclasses.replace(
        recipe, version=recipe.version + "-utils",
        build=[BuildStep("make -f win32/makefile.gcc clean",
                         allow_failure=True),
               BuildStep(_ZIP31_UTILS_MAKE if beta else _ZIP30_UTILS_MAKE)],
        artifacts=[Artifact(path=u, component=u) for u in _UTILS],
        notes=_NO_ZLIB.split(" so ")[0] + ". " +
              (_note_beta(recipe.version) if beta else "") +
              "zipcloak.exe, zipnote.exe and zipsplit.exe from the same "
              "win32/makefile.gcc and overrides as zip.exe: each is its own "
              "main plus zipfile, fileio, util and crc32 compiled with "
              "-DUTIL (zipcloak adds crypt). Assembler fast paths disabled "
              "(32-bit only).")


for _base in ("infozip_zip_3.0", "infozip_zip_3.1a", "infozip_zip_3.1b",
              "infozip_zip_3.1c"):
    RECIPES[_base + "-utils"] = _zip_utils(_base)

RECIPES["infozip_unzip_6.0-sfxdll"] = Recipe(
    family="Info-ZIP",
    version="6.0-sfxdll",
    upstream="https://infozip.sourceforge.net/UnZip.html",
    license=_NOTE_LICENSE,
    source=RECIPES["infozip_unzip_6.0"].source,
    build=[
        BuildStep("make -f win32/Makefile.gcc clean", allow_failure=True),
        # unzip32.dll is linked by a bare `dllwrap`, which then runs bare
        # dlltool, as and ld; the first attempt failed with "make: ***
        # [win32/Makefile.gcc:272: unzip32.dll] Error 127" (no dllwrap on
        # PATH), then "dllwrap: posix_spawnp: No such file or directory".
        # The cross tools are put on PATH under those names in .bin/, in the
        # build tree, not the source.
        BuildStep("mkdir -p .bin && for t in dllwrap dlltool as ld; do "
                  "ln -sf $(command -v {host}-$t) .bin/$t; done && "
                  "PATH=$PWD/.bin:$PATH make -f win32/Makefile.gcc CC={cc} "
                  "RC={windres} NOASM=1 "
                  "CC_CPU_OPT= LD_RELEASE_OPT= LOCAL_UNZIP='%s' "
                  "unzipsfx.exe unzip32.dll" % _INCLUDE),
    ],
    artifacts=[Artifact(path="unzipsfx.exe", component="unzipsfx.exe"),
               Artifact(path="unzip32.dll", component="unzip32.dll")],
    toolchains=["mingw_x86", "mingw_x64"],
    build_flags="-O2 (win32/Makefile.gcc default), NOASM",
    notes="unzipsfx.exe (the self-extractor stub, unzip's sources compiled "
          "again with -DSFX) and unzip32.dll (the DLL API, windll.c and "
          "api.c with the extraction core compiled with -DWINDLL -DDLL), "
          "from the same unzip 6.0 tarball, win32/Makefile.gcc and "
          "overrides as unzip.exe. unzip does not use zlib at any point. "
          "Assembler CRC disabled (32-bit only).",
)

# x86 only: the assembler fast paths in. zip 3.0's makefile.gcc assembles
# match.S and crc_i386.S by default (OBJA, CRCA_O) and the betas unless
# NOASM=1; unzip's Makefile.gcc assembles crc_i386.S unless NOASM=1.
RECIPES["infozip_zip_3.0-asm"] = Recipe(
    family="Info-ZIP",
    version="3.0-asm",
    upstream="https://infozip.sourceforge.net/Zip.html",
    license=_NOTE_LICENSE,
    source=RECIPES["infozip_zip_3.0"].source,
    build=[BuildStep("make -f win32/makefile.gcc clean", allow_failure=True),
           BuildStep("make -f win32/makefile.gcc CC={cc} RC={windres} "
                     "LDFLAGS='-o$@' LOCAL_ZIP='%s' ASFLAGS=-c zip.exe"
                     % _INCLUDE)],
    artifacts=[Artifact(path="zip.exe", component="zip.exe")],
    toolchains=["mingw_x86"],
    build_flags="-O2 (win32/makefile.gcc default), assembler match.S and "
                "crc_i386.S (upstream default on x86)",
    notes=_NO_ZLIB + "zip.exe with upstream's default x86 assembler fast "
          "paths: longest_match from match.S and crc32 from crc_i386.S "
          "instead of the C versions the zip 3.0 recipe builds. x86 only, "
          "because both files are 32-bit assembly.",
)
RECIPES["infozip_zip_3.1c-asm"] = Recipe(
    family="Info-ZIP",
    version="3.1c-asm",
    upstream="https://infozip.sourceforge.net/Zip.html",
    license=_NOTE_LICENSE,
    source=RECIPES["infozip_zip_3.1c"].source,
    build=[BuildStep("make -f win32/makefile.gcc clean", allow_failure=True),
           BuildStep("make -f win32/makefile.gcc CC={cc} RC={windres} "
                     "LDFLAGS='-o$@' LOCAL_ZIP='%s' ASFLAGS=-c zip.exe"
                     % _INCLUDE)],
    artifacts=[Artifact(path="zip.exe", component="zip.exe")],
    toolchains=["mingw_x86"],
    build_flags="-O3 (win32/makefile.gcc default), assembler match.S and "
                "crc_i386.S (upstream default on x86)",
    notes=_NO_ZLIB + _note_beta("3.1c") + "zip.exe with upstream's default "
          "x86 assembler fast paths (NOASM not given). x86 only.",
)
RECIPES["infozip_unzip_6.0-asm"] = Recipe(
    family="Info-ZIP",
    version="6.0-asm",
    upstream="https://infozip.sourceforge.net/UnZip.html",
    license=_NOTE_LICENSE,
    source=RECIPES["infozip_unzip_6.0"].source,
    build=[BuildStep("make -f win32/Makefile.gcc clean", allow_failure=True),
           BuildStep("make -f win32/Makefile.gcc CC={cc} RC={windres} "
                     "CC_CPU_OPT= LD_RELEASE_OPT= LOCAL_UNZIP='%s' ASFLAGS=-c "
                     "unzip.exe funzip.exe" % _INCLUDE)],
    artifacts=[Artifact(path="unzip.exe", component="unzip.exe"),
               Artifact(path="funzip.exe", component="funzip.exe")],
    toolchains=["mingw_x86"],
    build_flags="-O2 (win32/Makefile.gcc default), assembler crc_i386.S "
                "(upstream default on x86)",
    notes="unzip.exe and funzip.exe with upstream's default x86 assembler "
          "CRC (crc_i386.S; NOASM not given). x86 only. unzip does not use "
          "zlib at any point.",
)
for _beta in ("3.1a", "3.1b"):
    import dataclasses as _dc
    RECIPES["infozip_zip_%s-asm" % _beta] = _dc.replace(
        RECIPES["infozip_zip_3.1c-asm"], version=_beta + "-asm",
        source=RECIPES["infozip_zip_" + _beta].source,
        notes=_NO_ZLIB + _note_beta(_beta) + "zip.exe with upstream's "
              "default x86 assembler fast paths (NOASM not given). x86 only.")

# 3.1c's match.S and crc_i386.S end with an ELF-only
#     .section .note.GNU-stack, "", @progbits
#     .previous
# which the PE assembler rejects ("match.S:409: Error: junk at end of line,
# first unrecognized character is `-'", "crc_i386.S:306: ..."), so upstream's
# default x86 MinGW build of 3.1c does not assemble (3.1a and 3.1b do not have
# the lines). PATCHED BUILD TREE: the recipe deletes exactly those two lines
# from each file (a sed that checks both pairs were present and are gone);
# the 3.1c -asm image is therefore NOT byte-identical to a build of
# unmodified upstream. The lines only mark the stack non-executable on ELF and
# assemble to nothing in a PE.
_GNU_STACK = ("for f in match.S crc_i386.S; do "
              "test \"$(grep -c '^\\.section \\.note\\.GNU-stack' $f)\" = 1 && "
              "sed -i '/^\\.section \\.note\\.GNU-stack, \"\", @progbits$/,"
              "/^\\.previous$/d' $f && "
              "test \"$(grep -c 'GNU-stack\\|^\\.previous' $f)\" = 0 || exit 1; "
              "done")
RECIPES["infozip_zip_3.1c-asm"] = _dc.replace(
    RECIPES["infozip_zip_3.1c-asm"],
    build=[RECIPES["infozip_zip_3.1c-asm"].build[0], BuildStep(_GNU_STACK)]
    + RECIPES["infozip_zip_3.1c-asm"].build[1:],
    build_flags=RECIPES["infozip_zip_3.1c-asm"].build_flags
    + "; build tree patched: the ELF-only .note.GNU-stack section lines "
      "deleted from match.S and crc_i386.S",
    notes=RECIPES["infozip_zip_3.1c-asm"].notes + " PATCHED BUILD TREE: "
          "3.1c's match.S and crc_i386.S end with an ELF-only "
          "'.section .note.GNU-stack, \"\", @progbits' / '.previous' pair "
          "that the PE assembler rejects; the recipe deletes those two lines "
          "from each file, so this image is NOT byte-identical to a build of "
          "unmodified upstream.")
