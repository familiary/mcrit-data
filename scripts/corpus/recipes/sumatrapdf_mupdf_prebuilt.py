"""SumatraPDF 3.3.3's libmupdf.dll as upstream distributes it (tracker #67).

The tracker issue (r0ny123/mcrit-data#67) describes UNC2970's BURNBOOK as a
libmupdf.dll rebuilt from *modified* SumatraPDF 3.3.3 source, loaded beside a
SumatraPDF.exe, and gives that DLL's MD5 as 57e8a7ef21e7586d008d4116d70062a6
(SumatraPDF.exe 91841e006225ac500de7630740a21d91). This recipe files the
unmodified-upstream reference to compare it with: the libmupdf.dll that
SumatraPDF 3.3.3's own installers carry. The sibling recipe
sumatrapdf_mupdf_msvc.py rebuilds the same tag from source; this one is the
shipped binary.

**The modification itself is not reproduced.** Nothing here is the issue's
DLL. Its MD5 is a fact recorded in the notes, and the unmodified MD5s differ
from it, as they must:

    x64 libmupdf.dll  ece8e9908233891c003d6ed498852541  (sha256 8b91ca37...73e7)
    x86 libmupdf.dll  e1d7de37980056757b630db08d0f6e7c  (sha256 f77144ed...1cd)

which of the upstream functions the attackers touched is unknown (the issue
grades the evidence structural), so no function is marked as modified here.

**Where the DLL is.** The 3.3.3 portable executables link MuPDF into
SumatraPDF.exe; the DLL exists in the installers, which are the viewer
executable with an appended archive of three files (libmupdf.dll,
PdfFilter.dll, PdfPreview.dll). 7z opens the installer as a PE and yields the
payload as the resource ``.rsrc/RCDATA/1``; that is an "LzSA" archive (x86
BCJ + LZMA1, a CRC-32 per file) which scripts/corpus/extract_lzsa.py decodes
and checks without running anything. PdfFilter.dll and PdfPreview.dll are the
shell extensions and are not taken.

    x64  https://files.sumatrapdfreader.org/software/sumatrapdf/rel/3.3.3/SumatraPDF-3.3.3-64-install.exe
         (also https://www.sumatrapdfreader.org/dl/rel/3.3.3/SumatraPDF-3.3.3-64-install.exe, a 307 to it)
         sha256 cb1d73323d3d80004ada185844b0d461abd9ded736d5dc690607f935b4f2b58a
    x86  https://files.sumatrapdfreader.org/software/sumatrapdf/rel/3.3.3/SumatraPDF-3.3.3-install.exe
         sha256 e4801235defdf5ae7c5e384d45ae867e7993bd5efc53ce26ce7df24a8065180b

The x64 digest is the one a previous agent recorded; the download was checked
against it.

**What compiled them**, read off the PE headers: linker 14.29, Rich-header
build 30132 (Visual Studio 2019 16.10), PDB
``C:\\Users\\kjk\\src\\sumatrapdf\\out\\rel{64,32}\\libmupdf.pdb``, not
published, so ``Artifact.producer`` is ``msvc142`` and the README says "as
distributed upstream". The 816 exports named in libmupdf.def are the only
recovered names, so ``min_named_ratio`` is 0. The source-built row in this
family is MSVC v143 with a PDB; these are v142 and are different bytes, so
they take their own file names.

**Measured**, kept + removed = total (nothing is removed: the DLL links the
DLL runtime, and no unnamed body can match a glue probe): x64 8,547 + 0 =
8,547; x86 9,230 + 0 = 9,230; no excluded functions. Functions of 10+
instructions: x64 7,292 (7,039 distinct PicHashes), x86 8,301 (7,870).
PicHash overlap at that floor: with the v143 source build of the same tag,
same architecture, x64 2,021 and x86 3,791 (cross-architecture 2 and 2);
between the two shipped DLLs 2.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_ISSUE_MD5 = "57e8a7ef21e7586d008d4116d70062a6"

_NOTES = (
    "Harvested, not rebuilt: libmupdf.dll from the SumatraPDF 3.3.3 "
    "installer %(name)s (sha256 %(sha)s), unpacked with 7z and "
    "scripts/corpus/extract_lzsa.py (the installer's LzSA payload, every file "
    "checked against its stored CRC-32) and never executed. Unmodified "
    "upstream: the reference for the modified libmupdf.dll of tracker issue "
    "#67 (UNC2970 BURNBOOK), whose MD5 is " + _ISSUE_MD5 + "; this image's "
    "MD5 is %(md5)s. The modification itself is not reproduced and which "
    "functions it touched is unknown. Producer from the PE headers (linker "
    "14.29, Rich build 30132: MSVC v142, VS2019 16.10); the PDB is not "
    "published, so only the 816 exported functions carry a name. Bundled "
    "dependency attribution (zlib, libjpeg-turbo, freetype, jbig2dec, "
    "openjpeg, lcms2, harfbuzz, mujs, gumbo, DjVu, WebP, unarr) and the "
    "licence remain maintainer decisions.")


def _installer(toolchain, name, sha256, md5):
    return Recipe(
        family="MuPDF",
        version="SumatraPDF-3.3.3",
        upstream="https://github.com/sumatrapdfreader/sumatrapdf",
        license="GPL-3.0 / AGPL-3.0 and bundled dependencies",
        source=Source(
            url="https://files.sumatrapdfreader.org/software/sumatrapdf/rel/"
                "3.3.3/" + name,
            sha256=sha256),
        build=[BuildStep("python3 {repo}/scripts/corpus/extract_lzsa.py "
                         ".rsrc/RCDATA/1 payload"),
               BuildStep("ls -l payload/libmupdf.dll")],
        artifacts=[Artifact(path="payload/libmupdf.dll",
                            component="libmupdf_bin",
                            producer="msvc142")],
        toolchains=[toolchain],
        build_flags="MSVC v142 (as distributed by upstream: PE linker "
                    "14.29, Rich build 30132, /MD); exact flags not published",
        min_named_ratio=0,
        notes=_NOTES % {"name": name, "sha": sha256, "md5": md5},
    )


RECIPES = {
    "sumatrapdf_3.3.3_libmupdf_x64_prebuilt": _installer(
        "mingw_x64", "SumatraPDF-3.3.3-64-install.exe",
        "cb1d73323d3d80004ada185844b0d461abd9ded736d5dc690607f935b4f2b58a",
        "ece8e9908233891c003d6ed498852541"),
    "sumatrapdf_3.3.3_libmupdf_x86_prebuilt": _installer(
        "mingw_x86", "SumatraPDF-3.3.3-install.exe",
        "e4801235defdf5ae7c5e384d45ae867e7993bd5efc53ce26ce7df24a8065180b",
        "e1d7de37980056757b630db08d0f6e7c"),
}
