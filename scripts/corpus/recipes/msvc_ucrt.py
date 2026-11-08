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


def _ucrt(sdk, notes=""):
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
