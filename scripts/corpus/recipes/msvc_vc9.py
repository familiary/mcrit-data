"""The Visual C++ 2008 (VC9, toolset v90) x64 C runtime, from Visual Studio 2008.

data/MSVC holds Visual Studio 2008 for x86 only (the Express edition has no x64
compiler). The x64 libraries and runtime DLLs of VC9 ship with the full
Visual Studio 2008 media. Only function hashes and SMDA reports are committed,
never the libraries.

PROVENANCE CAVEAT. The image is not a Microsoft download. It is the
archive.org item https://archive.org/details/microsoft-visual-studio-2008
(file Microsoft_Visual_Studio_2008.iso, SHA-256 and size pinned in this
recipe, observed by streaming the download; archive.org itself lists only a
SHA-1 for it, an uploader-supplied value, and Microsoft publishes no digest
for this media any more). A pinned hash proves the build reads the same bytes
every time, not that those bytes are Microsoft's. So the content is verified
instead of the origin trusted: the compiler records of every library object
(CodeView S_COMPILE: AMD64, front end and back end 15.0.21022, which is
cl 15.00.21022.08, the Visual Studio 2008 RTM compiler) and the version
resources of the DLLs (9.00.21022.8) are written to provenance. A forged
library would have to forge those as well. The edition is a full one (Remote
Debugger, Crystal Reports, VSTO and Windows Mobile SDK on the same media), not
Express.

Inputs (scripts/corpus/crawl_vcsdk.py, profile ``vs2008``): the root CABs of
the image carry the files of every platform under installer keys that do not
name the platform (FL_libcmt_lib_<n>_<n>_x86_ln is x86, IA64, ARM, SH4 and so
on), so the platform is read from the COFF machine field of the objects and
only AMD64 files are used. Static libraries libcmt, libcmtd, libcpmt, libcpmtd,
msvcrt/msvcprt/oldnames (the import side of the DLL runtime), comsupp,
delayimp, runtmchk and the start-up objects are linked whole into images
(import records and the /clr:pure objects are left out, see crawl_vcsdk.py);
the shipped x64 msvcr90/msvcp90 DLLs and their debug builds are analysed as
they are, with their PDBs. The managed libraries (msvcmrt, msvcurt, ptrust*)
are not analysed.

No compiler runtime baseline is applied: this IS the runtime. Functions
sharing PicHash and name are collapsed (dedupe_functions).

Measured (CI run 42522855728, scratch/msvc-vc10x64; the first attempt,
42519569857, was stopped by the crawler treating an object with four different
AMD64 builds as fatal, and its 3.5 GB download took 37 minutes on one
connection): image 3,554,287,616 bytes, SHA-256 above, re-verified on the
runner. Functions kept (+ collapsed): libcmt 2470 (+247), libcmtd 2604 (+261),
libcpmt 1426 (+383), libcpmtd 1680 (+630), msvcrt+msvcprt+oldnames 135 (+13),
msvcrtd+msvcprtd 143 (+13), comsupp+comsuppw+delayimp 66 (+7),
comsuppd+comsuppwd+runtmchk 99 (+9), objs 36 (+1), msvcr90 1964 (+4),
msvcp90 2582 (+436), msvcr90d 2298 (+12), msvcp90d 3280 (+459); total 18783
kept, 2475 collapsed. Verified in the data: 1834 library objects with an
AMD64 compiler record, front end and back end 15.0.21022; DLL file version
9.00.21022.8 (Microsoft_VC90_CRT_x64.RTM). Files that exist in several
different AMD64 builds on the medium (alloca16.obj, amdsecgs.obj, ...) are not
used and are listed in provenance (skipped_ambiguous).

PicHash overlap (functions of 10+ instructions; 5808 distinct in the new
data): 0 with data/MSVC 2008_express_x86 (5886 distinct) and with
2005/2010 x86; 483 (8.3% of the new, 5.7% of the old) with 2012_Express_x64;
1146 with the MSVC_VC10 x64 data and 49 with MSVC_VC8.

Filed under the family MSVC_CRT with the other old Visual C++ x64 runtimes
(the version distinguishes VC8, VC9 and VC10): the same C functions recur in
all of them, and the cross-family PicHash check would otherwise report them as
leakage between three families.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


ISO_URL = ("https://archive.org/download/microsoft-visual-studio-2008/"
           "Microsoft_Visual_Studio_2008.iso")
ISO_SHA256 = "52ebf5731b75ccc460384ce3fd25bc984fb2d828ae51501ebaf0cadc27a33ee9"

LIB_IMAGES = [
    "libcmt", "libcmtd", "libcpmt", "libcpmtd",
    "msvcrt+msvcprt+oldnames~", "msvcrtd+msvcprtd",
    "comsupp+comsuppw~+delayimp~", "comsuppd+comsuppwd~+runtmchk~",
    "objs",
]
DLLS = ["msvcr90", "msvcp90", "msvcr90d", "msvcp90d"]

_CRAWL = ("python {repo}/scripts/corpus/crawl_vcsdk.py --iso-url %s "
          "--iso-sha256 %s --profile vs2008 --free-disk --out . %%s"
          % (ISO_URL, ISO_SHA256))


def _stem(spec):
    return spec.replace("~", "").replace("+", "_")


def _vc9():
    artifacts = [Artifact(path=_stem(spec) + ".dll", component=_stem(spec),
                          pdb=_stem(spec) + ".pdb",
                          inputs=_stem(spec) + ".inputs.json")
                 for spec in LIB_IMAGES]
    artifacts += [Artifact(path=name + ".dll", component=name,
                           pdb=name + ".pdb", inputs=name + ".inputs.json")
                  for name in DLLS]
    return Recipe(
        family="MSVC_CRT",
        version="9.0.21022",
        upstream="https://learn.microsoft.com/en-us/previous-versions/"
                 "visualstudio/visual-studio-2008/",
        license="Microsoft Visual Studio 2008 / Visual C++ 2008 runtime; "
                "redistribution terms are for the maintainer to decide. Only "
                "function hashes and SMDA reports are recorded, not the "
                "libraries. The installation image is an archive.org copy "
                "whose hash is uploader-supplied, not a Microsoft digest.",
        source=Source(local="Visual Studio 2008 DVD image from archive.org "
                            "(microsoft-visual-studio-2008), downloaded by the "
                            "build step and verified by SHA-256; AMD64 files "
                            "selected by COFF machine type"),
        build=[BuildStep(_CRAWL % ("libs " + " ".join(LIB_IMAGES))),
               BuildStep(_CRAWL % ("dlls " + " ".join(DLLS)))],
        artifacts=artifacts,
        toolchains=["msvc_x64"],
        drop_crt_glue=False,
        dedupe_functions=True,
        notes="Source image is an archive.org copy with an uploader-supplied "
              "hash only; content verified by compiler records (AMD64, "
              "15.0.21022) and DLL file versions (9.00.21022.8).",
        build_flags="VC9 (cl 15.00.21022) x64 objects from Visual Studio 2008; "
                    "libraries linked whole: link /DLL /NOENTRY /NODEFAULTLIB "
                    "/WHOLEARCHIVE /FORCE:UNRESOLVED /FORCE:MULTIPLE /DEBUG "
                    "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF /Brepro; the "
                    "msvcr90/msvcp90 DLLs are the shipped images",
    )


RECIPES = {"MSVC_CRT_9.0.21022": _vc9()}
