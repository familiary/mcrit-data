"""The Visual C++ 2005 (VC8) x64 C runtime libraries, from the Platform SDK R2.

data/MSVC holds Visual Studio 2005 for x86 only. The x64 libraries of the
compiler generation that became Visual C++ 2005 shipped with the Platform SDK
for Windows Server 2003 R2 (March 2006). Only function hashes and SMDA reports
are committed, never the libraries.

WHAT THIS IS, AND IS NOT. The AMD64 build tools in that SDK are
cl 14.00.40310.41 and link 8.00.40310.39 - the pre-release build that
preceded Visual Studio 2005 RTM (14.00.50727). The libraries are therefore
VC8-generation x64 code, not the RTM runtime that Visual Studio 2005 shipped
and that the x86 data/MSVC 2005 report covers; they will match binaries linked
against this SDK and may differ from RTM-linked ones. The SDK ships no x64
msvcr80/msvcp80 (its msvcr80.dll and msvcp80.dll are x86, 8.00.40310.39, for
the cross compiler), so there are no DLL artefacts. msvcrt.lib and msvcprt.lib
import from the operating system's msvcrt.dll and msvcp60.dll, not from a
VC8 DLL.

PROVENANCE CAVEAT. The image is not a Microsoft download. It is the
archive.org item https://archive.org/details/platform-sdk-for-microsoft-
windows-server-2003-r2-march-2006-edition-english (en_platformsdk_
windowsr2_march2006.iso, SHA-256 and size pinned in this recipe, observed by
streaming the download; archive.org lists only an uploader-supplied SHA-1 and
Microsoft publishes no digest for it any more). The content is verified
instead: the CodeView compiler records of the library objects (AMD64, front end
and back end 14.0.40310) and the version resources of the compiler binaries
and DLLs in the same CABs are written to provenance.

Inputs (scripts/corpus/crawl_vcsdk.py, profile ``psdk2003r2``): the
``PSDK-SDK_Core_BLD_AMD64-common.*.cab`` members, files of AMD64 machine type
only. libc, libcd, libci, libcid, libcimt, libcimtd, libcmt, libcmtd, libcp,
libcpd, libcpmt, libcpmtd, msvcrt/msvcprt/oldnames, comsupp, delayimp and the
start-up objects are linked whole (import records are left out).

No compiler runtime baseline is applied: this IS the runtime. Functions
sharing PicHash and name are collapsed (dedupe_functions).
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


ISO_URL = ("https://archive.org/download/platform-sdk-for-microsoft-windows-"
           "server-2003-r2-march-2006-edition-english/"
           "en_platformsdk_windowsr2_march2006.iso")
ISO_SHA256 = "3d2f97178e72cabe0a972b14c4d0aae80f7ed99ec73be9970cc95f42a31bfdb6"

LIB_IMAGES = [
    "libc", "libcd", "libci", "libcid", "libcimt", "libcimtd",
    "libcmt", "libcmtd", "libcp", "libcpd", "libcpmt", "libcpmtd",
    "msvcrt+msvcprt+oldnames~", "msvcrtd+msvcprtd",
    "comsupp+delayimp~", "comsuppd",
    "objs",
]

_CRAWL = ("python {repo}/scripts/corpus/crawl_vcsdk.py --iso-url %s "
          "--iso-sha256 %s --profile psdk2003r2 --free-disk --out . %%s"
          % (ISO_URL, ISO_SHA256))


def _stem(spec):
    return spec.replace("~", "").replace("+", "_")


def _vc8():
    return Recipe(
        family="MSVC_VC8",
        version="8.0.40310",
        upstream="https://learn.microsoft.com/en-us/previous-versions/"
                 "windows/desktop/",
        license="Microsoft Platform SDK for Windows Server 2003 R2; "
                "redistribution terms are for the maintainer to decide. Only "
                "function hashes and SMDA reports are recorded, not the "
                "libraries. The installation image is an archive.org copy "
                "whose hash is uploader-supplied, not a Microsoft digest.",
        source=Source(local="Platform SDK for Windows Server 2003 R2 (March "
                            "2006) image from archive.org, downloaded by the "
                            "build step and verified by SHA-256; AMD64 build "
                            "CABs only"),
        build=[BuildStep(_CRAWL % ("libs " + " ".join(LIB_IMAGES)))],
        artifacts=[Artifact(path=_stem(spec) + ".dll", component=_stem(spec),
                            pdb=_stem(spec) + ".pdb",
                            inputs=_stem(spec) + ".inputs.json")
                   for spec in LIB_IMAGES],
        toolchains=["msvc_x64"],
        drop_crt_glue=False,
        dedupe_functions=True,
        notes="Pre-RTM VC8 generation (cl 14.00.40310.41) from the Platform "
              "SDK R2; image is an archive.org copy with an uploader-supplied "
              "hash only; content verified by compiler records (AMD64, "
              "14.0.40310).",
        build_flags="cl 14.00.40310.41 x64 objects from the Platform SDK R2; "
                    "libraries linked whole: link /DLL /NOENTRY /NODEFAULTLIB "
                    "/WHOLEARCHIVE /FORCE:UNRESOLVED /FORCE:MULTIPLE /DEBUG "
                    "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF /Brepro",
    )


RECIPES = {"MSVC_VC8_8.0.40310": _vc8()}
