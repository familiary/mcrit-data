"""The Visual C++ 2010 (VC10, toolset v100) x64 C runtime, from Windows SDK 7.1.

data/MSVC holds Visual Studio 2005, 2008 and 2010 for x86 only: the Express
editions it was crawled from carry no x64 compiler. The x64 libraries of VC10
shipped with the Windows SDK 7.1 (``GRMSDKX_EN_DVD.iso``, the SDK that
installs the v100 x64 compilers and libraries), in ``Setup\\vc_stdamd64\\
vc_stdamd64.cab``. Only function hashes and SMDA reports are committed, never
the libraries.

Inputs, all from that one CAB (scripts/corpus/crawl_vcsdk.py):

  * the static libraries - libcmt/libcmtd (C), libcpmt and its variants
    libcpmt1/libcpmtd/libcpmtd0/libcpmtd1 (C++), msvcrt/msvcprt/oldnames (the
    import side of the DLL runtime), comsupp, delayimp, runtmchk - each linked
    whole into one image, and the loose start-up objects (binmode.obj,
    setargv.obj, ...) into one more;
  * the shipped x64 runtime DLLs msvcr100, msvcp100 and their debug builds,
    with the PDBs the SDK ships for them (version 10.00.30319.1).

The managed-code libraries (msvcmrt, msvcurt, ptrust*) are not analysed: they
are for /clr builds and their code is MSIL.

No compiler runtime baseline is applied: this IS the runtime. Functions
sharing PicHash and name are collapsed (dedupe_functions); the number
collapsed is in provenance. The image is verified by SHA-256 before use and the
compiler records of every library object (front end and back end 16.0.30319,
machine AMD64) are written to provenance.

Measured (CI run 42513443097, scratch/msvc-vc10x64; kept + collapsed = functions
before collapsing; no runtime baseline removes anything):

  libcmt 4653 (+140 collapsed)      libcmtd 4904 (+134)
  libcpmt 2617 (+96)   libcpmt1 2729 (+105)   libcpmtd 3356 (+106)
  libcpmtd0 3129 (+111)   libcpmtd1 3309 (+111)
  msvcrt+msvcprt+oldnames 139 (+13)   msvcrtd+msvcprtd 145 (+12)
  comsupp+comsuppw+delayimp 64 (+7)   comsuppd+comsuppwd+runtmchk 98 (+9)
  objs 36 (+1)
  msvcr100 2822 (+3)   msvcp100 2021 (+350)
  msvcr100d 4585 (+118)   msvcp100d 4390 (+394)
  total 38997 kept, 1710 collapsed.

PicHash overlap (functions of 10+ instructions; 8430 distinct in the new data):
0 with data/MSVC 2010_Express_x86 (11488 distinct; a different instruction
set, so none is expected), 1479 (17.5% of the new, 17.4% of the old) with
data/MSVC 2012_Express_x64 (8492 distinct). Inside the family, 1320 of libcmt's
2203 hashes are also in msvcr100 and 2592 of libcmtd's 2781 in msvcr100d.

The start-up objects are linked without their /clr:pure twins (pbinmode.obj
and the like, LNK1313); msvcrt, msvcprt and oldnames are linked from their
object members because link /WHOLEARCHIVE rejects import records (LNK1127).
oldnames.lib and chkstk.obj are assembler/alias thunks and carry no compiler
record. The x64 msvcr100.dll in the SDK is the CLR 4.0 build
(OriginalFilename msvcr100_clr0400.dll, FileVersion 10.00.30319.1).

Filed under the family MSVC_CRT with the other old Visual C++ x64 runtimes
(the version distinguishes VC8, VC9 and VC10): the same C functions recur in
all of them, and the cross-family PicHash check would otherwise report them as
leakage between three families.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


ISO_URL = ("https://download.microsoft.com/download/F/1/0/"
           "F10113F5-B750-4969-A255-274341AC6BCE/GRMSDKX_EN_DVD.iso")
ISO_SHA256 = "9f495e52f33d68125277cbca3565ce57904af7d506758a14691fa6e2479ad65c"
CAB = "Setup/vc_stdamd64/vc_stdamd64.cab"

# One linked image per entry; "+" joins libraries linked into the same image.
LIB_IMAGES = [
    "libcmt", "libcmtd",
    "libcpmt", "libcpmt1", "libcpmtd", "libcpmtd0", "libcpmtd1",
    "msvcrt+msvcprt+oldnames", "msvcrtd+msvcprtd",
    "comsupp+comsuppw+delayimp", "comsuppd+comsuppwd+runtmchk",
    "objs",
]
DLLS = ["msvcr100", "msvcp100", "msvcr100d", "msvcp100d"]

_CRAWL = ("python {repo}/scripts/corpus/crawl_vcsdk.py --iso-url %s "
          "--iso-sha256 %s --cab %s --out . %%s" % (ISO_URL, ISO_SHA256, CAB))


def _stem(spec):
    return spec.replace("+", "_")


def _vc10():
    artifacts = [Artifact(path=_stem(spec) + ".dll", component=_stem(spec),
                          pdb=_stem(spec) + ".pdb",
                          inputs=_stem(spec) + ".inputs.json")
                 for spec in LIB_IMAGES]
    artifacts += [Artifact(path=name + ".dll", component=name,
                           pdb=name + ".pdb", inputs=name + ".inputs.json")
                  for name in DLLS]
    return Recipe(
        family="MSVC_CRT",
        version="10.0.30319",
        upstream="https://learn.microsoft.com/en-us/previous-versions/"
                 "visualstudio/visual-studio-2010/ms164311(v=vs.100)",
        license="Microsoft Windows SDK 7.1 / Visual C++ 2010 runtime; "
                "redistribution terms are for the maintainer to decide. Only "
                "function hashes and SMDA reports are recorded, not the "
                "libraries.",
        source=Source(local="Windows SDK 7.1 GRMSDKX_EN_DVD.iso, "
                            "Setup/vc_stdamd64/vc_stdamd64.cab, downloaded by "
                            "the build step and verified by SHA-256"),
        build=[BuildStep(_CRAWL % ("libs " + " ".join(LIB_IMAGES))),
               BuildStep(_CRAWL % ("dlls " + " ".join(DLLS)))],
        artifacts=artifacts,
        toolchains=["msvc_x64"],
        drop_crt_glue=False,
        dedupe_functions=True,
        build_flags="VC10 (cl 16.00.30319) x64 objects from Windows SDK 7.1; "
                    "libraries linked whole: link /DLL /NOENTRY /NODEFAULTLIB "
                    "/WHOLEARCHIVE /FORCE:UNRESOLVED /FORCE:MULTIPLE /DEBUG "
                    "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF /Brepro; the "
                    "msvcr100/msvcp100 DLLs are the shipped images",
    )


RECIPES = {"MSVC_CRT_10.0.30319": _vc10()}
