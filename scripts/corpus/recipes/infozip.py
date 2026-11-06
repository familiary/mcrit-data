"""Info-ZIP zip 3.0 and unzip 6.0 - the other deflate and inflate in the wild.

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
funzip/unzipsfx/unzip32.dll that are not built, below) - so the artefacts are
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

_INCLUDE = "-include windows.h"


def _zip(version, sha256):
    return Recipe(
        family="Info-ZIP",
        version=version,
        upstream="https://infozip.sourceforge.net/Zip.html",
        license=_NOTE_LICENSE,
        source=Source(url="https://downloads.sourceforge.net/infozip/zip30.tar.gz",
                      sha256=sha256),
        build=[
            BuildStep("make -f win32/makefile.gcc clean", allow_failure=True),
            BuildStep("make -f win32/makefile.gcc CC={cc} RC={windres} "
                      "LDFLAGS='-o$@' LOCAL_ZIP='-DNO_ASM %s' "
                      "OBJA= CRCA_O= CRCAUO= zip.exe" % _INCLUDE),
        ],
        artifacts=[Artifact(path="zip.exe", component="zip.exe")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 (win32/makefile.gcc default), NO_ASM",
        notes="zip.exe only: zipcloak, zipnote and zipsplit link the same "
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
                      "CC_CPU_OPT= LD_RELEASE_OPT= LOCAL_UNZIP='%s' unzip.exe"
                      % _INCLUDE),
        ],
        artifacts=[Artifact(path="unzip.exe", component="unzip.exe")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 (win32/Makefile.gcc default), NOASM",
        notes="unzip.exe only: funzip and unzipsfx are the same inflate.c "
              "compiled with -DFUNZIP / -DSFX, and unzip32.dll is the same "
              "objects again. Assembler CRC disabled (32-bit only).",
    )


RECIPES = {
    "infozip_zip_3.0": _zip(
        "3.0", "f0e8bb1f9b7eb0b01285495a2699df3a4b766784c1765a8f1aeedf63c0806369"),
    "infozip_unzip_6.0": _unzip(
        "6.0", "036d96991646d0449ed0aa952e4fbe21b476ce994abc276e49d30e686708bd37"),
}
