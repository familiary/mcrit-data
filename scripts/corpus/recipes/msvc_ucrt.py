"""Static UCRT (libucrt.lib / libucrtd.lib) from the Windows SDK.

data/MSVC was crawled from Visual Studio's own VC directories, and none of it
contains ``__acrt_*`` or ``__stdio_common_*`` names: the static Universal CRT
lives in ``Windows Kits\\10\\Lib\\<sdk>\\ucrt\\{x86,x64}``. Every ``/MT``-linked
VS2015+ binary embeds code from it, so this is the missing half of the
Microsoft runtime coverage. The vcruntime/libcmt halves are in VS and already
covered.

This is Windows SDK content, a different kind of input from data/MSVC. Only
function hashes and SMDA reports are committed, never the libraries.

Each archive is linked whole into one image (scripts/corpus/crawl_ucrt.py) and
analysed by the ordinary pipeline, one report per (SDK, architecture,
release/debug). No compiler runtime baseline is applied: this IS the runtime.
Functions sharing PicHash and name are collapsed (dedupe_functions).

The windows-2022 runner carries SDKs 10.0.10240, 17763, 19041, 22621 and 26100.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


SDKS = ["10.0.10240", "10.0.17763", "10.0.19041", "10.0.22621", "10.0.26100"]

_CRAWL = ("python {repo}/scripts/corpus/crawl_ucrt.py --sdk %s --arch {arch} "
          "--out . libucrt libucrtd")


# Measured on the committed reports (PicHash of functions with 10+
# instructions, Jaccard overlap between neighbouring SDKs, in the order
# 10240-17763, 17763-19041, 19041-22621, 22621-26100):
#   x86 libucrt  0.28 0.36 0.39 0.43     x86 libucrtd 0.44 0.67 0.40 0.60
#   x64 libucrt  0.18 0.60 0.28 0.37     x64 libucrtd 0.30 0.69 0.34 0.48
# Every SDK adds at least 467 PicHashes that no older SDK has (x64 libucrtd
# 19041 is the minimum), so none is a near-duplicate and all five are kept.
# Same-named functions, 19041 against 22621 x64 libucrt: 5692 in common, 3405
# with the same PicHash.
_NOTES = ("Static UCRT from the Windows SDK, not from Visual Studio, and a "
          "different kind of content from data/MSVC. Linked whole into one "
          "image per library (lib /LIST member count and the library digest "
          "are under 'inputs'); symbols UCRT expects from vcruntime stay "
          "unresolved, so calls to them target address 0. Functions with "
          "equal PicHash and name are collapsed ('deduplicated_functions'). "
          "No compiler runtime baseline is removed: this is the runtime. "
          "PicHash overlap between neighbouring SDKs is 0.18-0.69 (Jaccard, "
          "functions of 10+ instructions); every SDK adds at least 467 "
          "PicHashes absent from all older ones, so all five are kept. "
          "Only function hashes and SMDA reports are committed.")


def _ucrt(sdk, notes=_NOTES):
    return Recipe(
        family="MSVC_UCRT",
        version=sdk,
        upstream="https://learn.microsoft.com/en-us/windows/win32/"
                 "debug/c-runtime-library-reference",
        license="Microsoft Windows SDK; redistribution terms are for the "
                "maintainer to decide. Only function hashes and SMDA "
                "reports are recorded, not the libraries.",
        source=Source(local="Windows SDK %s static UCRT libraries on the "
                            "windows-2022 runner image" % sdk),
        build=[BuildStep(_CRAWL % sdk)],
        artifacts=[
            Artifact(path="libucrt.dll", component="libucrt",
                     pdb="libucrt.pdb", inputs="libucrt.inputs.json"),
            Artifact(path="libucrtd.dll", component="libucrtd",
                     pdb="libucrtd.pdb", inputs="libucrtd.inputs.json"),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        drop_crt_glue=False,
        dedupe_functions=True,
        build_flags="Windows SDK %s libucrt.lib / libucrtd.lib linked whole: "
                    "link /DLL /NOENTRY /NODEFAULTLIB /WHOLEARCHIVE "
                    "/FORCE:UNRESOLVED /FORCE:MULTIPLE /DEBUG /INCREMENTAL:NO "
                    "/OPT:NOREF /OPT:NOICF /Brepro" % sdk,
        notes=notes,
    )


RECIPES = {"MSVC_UCRT_%s" % sdk: _ucrt(sdk) for sdk in SDKS}
