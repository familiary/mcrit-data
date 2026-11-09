"""Static runtime libraries of older MSVC toolsets: VC++ 14.0, 14.1x, 14.2x.

data/MSVC holds one merged report per Visual Studio release, built from the
.lib/.obj files of a single install. The minor toolsets inside a release are
not interchangeable: 14.20 to 14.29 are all "Visual Studio 2019", yet the
runtime code a binary carries is that of the minor toolset which linked it.
Malware keeps being built with whichever old toolset its author had, so each
minor that adds code the others lack is crawled here.

Each toolset was installed on a windows-2022 runner with the Visual Studio
Build Tools bootstrapper of the matching Visual Studio (aka.ms/vs/15 for
VC++ 14.0 and 14.11 to 14.15, aka.ms/vs/16 for 14.20 to 14.28), and its
runtime libraries are linked whole into one analysable image per shard
(scripts/corpus/crawl_vclib.py): /MT release and debug, the static half of
/MD, the compatibility libraries, comsupp, the startup objects and, for a
few toolsets, ATL/MFC. Only function hashes and SMDA reports are committed.

The installers are the evergreen bootstrappers: their sha256 is pinned in the
workflow that ran them (and recorded in the README), the payloads they then
download are NOT pinned. The sha256 of every library that went into an image
is recorded in provenance ("inputs").

Which toolsets are kept. Every installed toolset was measured (PicHash of the
functions with 10+ instructions, runtime shards only: ATL/MFC excluded). A
toolset is kept when, on either architecture, it adds at least 500 PicHashes
and 5% of its own to the toolsets kept before it (14.28.29333 adds 510 / 494,
about 7%). The others are near-duplicates, recorded here and in the README.
Share of each one's hashes already present in the earlier kept toolsets
(x64 / x86):

    14.13.26128   96.0% / 97.4%  (14.12 and 14.14 hold it)
    14.16.27023   99.0% / 99.5%  (the same code as 14.15.26726)
    14.21.27702   95.0% / 95.8%
    14.24.28314   95.9% / 96.5%
    14.26.28801   97.4% / 98.3%
    14.27.29110   95.7% / 96.4%

Not committed either, though measured and linked: the three _ITERATOR_DEBUG_LEVEL
variants of the C++ library (libcpmt1/libconcrt1, libcpmtd0/1, libconcrtd0/1)
add only about 150 to 195 hashes to the default level, and the debug ATL/MFC
libraries (about 100 MB each) and the ATL/MFC of the minors whose ATL/MFC
overlaps another kept one. msvcprt.lib and msvcprtd.lib cannot be analysed:
the linker rejects them as corrupt (LNK1127) in every toolset. The sanitizer,
fuzzer and clang_rt libraries of the 14.2x toolsets are not part of a default
link and are left out.

The file names say msvc143 because that is the linker (the runner's own)
that joined the images; the toolset is the version field.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# toolset directory -> (Visual Studio that ships it, component id, atlmfc?)
TOOLSETS = {
    "14.0": ("Visual Studio 2015 (v140)",
             "Microsoft.VisualStudio.Component.VC.140 (VS 2017 installer)", True),
    "14.11.25503": ("Visual Studio 2017 15.4",
                    "Microsoft.VisualStudio.Component.VC.Tools.14.11", False),
    "14.12.25827": ("Visual Studio 2017 15.5",
                    "Microsoft.VisualStudio.Component.VC.Tools.14.12", False),
    "14.14.26428": ("Visual Studio 2017 15.7",
                    "Microsoft.VisualStudio.Component.VC.Tools.14.14", True),
    "14.15.26726": ("Visual Studio 2017 15.8 and 15.9 (14.16.27023 is the same code)",
                    "Microsoft.VisualStudio.Component.VC.Tools.14.15", False),
    "14.20.27508": ("Visual Studio 2019 16.0",
                    "Microsoft.VisualStudio.Component.VC.14.20.x86.x64", True),
    "14.22.27905": ("Visual Studio 2019 16.2",
                    "Microsoft.VisualStudio.Component.VC.14.22.x86.x64", False),
    "14.23.28105": ("Visual Studio 2019 16.3",
                    "Microsoft.VisualStudio.Component.VC.14.23.x86.x64", False),
    "14.25.28610": ("Visual Studio 2019 16.5",
                    "Microsoft.VisualStudio.Component.VC.14.25.x86.x64", True),
    "14.28.29333": ("Visual Studio 2019 16.8",
                    "Microsoft.VisualStudio.Component.VC.14.28.x86.x64", True),
    "14.28.29910": ("Visual Studio 2019 16.9",
                    "Microsoft.VisualStudio.Component.VC.14.28.16.9.x86.x64", False),
}

# shard -> short description recorded as the component's meaning
SHARDS = ["mt", "mtd", "md", "mdd", "support", "com", "comd", "startup"]


def _dll(shard, version):
    return "%s_%s" % (shard, version.replace(".", "_"))


def _recipe(version, release, component, atlmfc):
    shards = SHARDS + (["atlmfc"] if atlmfc else [])
    artifacts = []
    for shard in shards:
        stem = _dll(shard, version)
        artifacts.append(Artifact(path=stem + ".dll", component=shard,
                                  pdb=stem + ".pdb", inputs=stem + ".inputs.json"))
    return Recipe(
        family="MSVC_oldtoolsets",
        version=version,
        upstream="https://learn.microsoft.com/en-us/visualstudio/releases/"
                 "2019/history",
        license="Microsoft Visual Studio Build Tools; redistribution terms are "
                "for the maintainer to decide. Only function hashes and SMDA "
                "reports are recorded, not the libraries.",
        source=Source(local="%s runtime libraries, installed on the "
                            "windows-2022 runner from %s" % (release, component)),
        build=[BuildStep(
            "python {repo}/scripts/corpus/crawl_vclib.py --toolset %s "
            "--arch {arch} --out . %s" % (version, " ".join(shards)))],
        artifacts=artifacts,
        toolchains=["msvc_x86", "msvc_x64"],
        drop_crt_glue=False,
        dedupe_functions=True,
        build_flags="%s static runtime libraries linked whole: link /DLL "
                    "/NOENTRY /NODEFAULTLIB /WHOLEARCHIVE /FORCE:UNRESOLVED "
                    "/FORCE:MULTIPLE /DEBUG /INCREMENTAL:NO /OPT:NOREF "
                    "/OPT:NOICF /Brepro" % release,
        notes="Shards: mt = libcmt, libvcruntime, libcpmt, libconcrt (/MT); "
              "mtd = the debug libraries (/MTd); md, mdd = msvcrt(d).lib; "
              "support = legacy_stdio_definitions, delayimp, aligned_new, ...; "
              "com, comd = comsupp; startup = the lib directory's *.obj"
              + ("; atlmfc = atls, nafxcw, uafxcw" if atlmfc else ""),
    )


RECIPES = {"MSVC_oldtoolsets_%s" % v: _recipe(v, *meta)
           for v, meta in TOOLSETS.items()}
