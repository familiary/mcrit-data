"""Visual Studio MSVC runtime, ATL and MFC libraries, one shard per toolset.

data/MSVC was crawled by hand from the VC directories of one installation per
Visual Studio release. The windows-2022 and windows-2025 runner images carry
several MSVC toolsets side by side, and the libraries of a toolset differ from
its neighbours' (measured on x64: libcmt.lib is 5.58 MB in 14.29, 6.53 MB in
14.44 and 6.61 MB in 14.51; libvcruntime.lib 1.22, 2.09 and 2.36 MB), so each
toolset gets its own reproducible crawl:

    windows-2022: 14.29 (VS 2019 toolset, v142) and 14.44 (v143)
    windows-2025: 14.29, 14.44 and 14.51 (VS 2026, v145)

14.44 is byte-identical across the two images and is imported once.

``scripts/corpus/crawl_vclibs.py`` links the libraries of one shard whole into
one image, the way crawl_ucrt.py does for the static UCRT, and the ordinary
pipeline analyses it. A shard is a group of libraries built with the same
runtime flavour (the linker refuses to mix /MT with /MD or release with
debug), which also keeps every committed file below
config.MAX_COMMITTED_FILE_SIZE (100 MB): the 2022 x86 non-MFC export of
data/MSVC would have been about 150 MB and was dropped for that reason.

14.29 has the CRT shards only: the images install ATL and MFC for the newest
toolset alone (measured: no ATLMFC directory under 14.29.30133).

Not crawled: clang_rt.* (sanitizer and libFuzzer runtimes, LLVM code), managed
(/clr) runtimes, pure import libraries (no object member), the
onecore/spectre variant directories, and the static UCRT (libucrt, see
MSVC_UCRT). What each shard
excluded is recorded per artefact under ``inputs.excluded`` in provenance,
next to the SHA-256 of every library that went in.

This is Visual Studio content, a different kind of input from data/MSVC. Only
function hashes and SMDA reports are committed, never the libraries.
"""

from ..crawl_vclibs import SHARDS, shards_for
from ..recipe import Artifact, BuildStep, Recipe, Source


# Toolset minors the runner images carry. The patch level is recorded in
# provenance (inputs.toolset); the recipe version is the minor so that a
# refreshed image with 14.44.35208 is the same recipe.
TOOLSETS = {
    "14.29": "VS 2019 toolset v142 (windows-2022 and windows-2025)",
    "14.44": "VS 2022 toolset v143 (windows-2022 and windows-2025)",
    "14.51": "VS 2026 toolset v145 (windows-2025)",
}

# Recipes that need the windows-2025 image; the workflow leaves them out of
# the windows-2022 enumeration.
WINDOWS_2025_ONLY = ("14.51",)


def _shard(toolset, shard):
    description = SHARDS[shard][1]
    return Recipe(
        family="MSVC_TOOLSETS",
        version=toolset,
        upstream="https://learn.microsoft.com/en-us/cpp/c-runtime-library/"
                 "crt-library-features",
        license="Microsoft Visual Studio; redistribution terms are for the "
                "maintainer to decide. Only function hashes and SMDA "
                "reports are recorded, not the libraries.",
        source=Source(local="Visual Studio MSVC toolset %s libraries on the "
                            "runner image (%s)" % (toolset, TOOLSETS[toolset])),
        build=[BuildStep(
            "python {repo}/scripts/corpus/crawl_vclibs.py --toolset %s "
            "--arch {arch} --out . %s" % (toolset, shard))],
        artifacts=[Artifact(path="%s.dll" % shard, component=shard,
                            pdb="%s.pdb" % shard,
                            inputs="%s.inputs.json" % shard)],
        toolchains=["msvc_x86", "msvc_x64"],
        drop_crt_glue=False,
        dedupe_functions=True,
        # The objects carry COFF public symbols, not full PDBs: static
        # functions of the CRT and MFC have no name to recover.
        min_named_ratio=0.15,
        build_flags="MSVC toolset %s, shard %s (%s): the COFF object members "
                    "of the shard's libraries unpacked and linked with link "
                    "/DLL /NOENTRY /NODEFAULTLIB /FORCE:UNRESOLVED "
                    "/FORCE:MULTIPLE /DEBUG /INCREMENTAL:NO /OPT:NOREF "
                    "/OPT:NOICF /Brepro" % (toolset, shard, description),
        notes="Derived from the Visual Studio installation on the runner "
              "image; inputs.libraries lists the SHA-256 of every library "
              "that went in and inputs.excluded every library of the "
              "directory that did not, with the reason. Only function "
              "hashes and SMDA reports are recorded, not the libraries.",
    )


def recipe_name(toolset, shard):
    return "MSVC_TOOLSETS_%s_%s" % (toolset, shard)


RECIPES = {recipe_name(t, s): _shard(t, s)
           for t in TOOLSETS for s in shards_for(t)}
