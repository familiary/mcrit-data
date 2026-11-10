"""MinHook as upstream distributes it: the DLLs in the GitHub release assets.

The tracker issue (r0ny123/mcrit-data#11) is explicit that this is the thing
to have first. Kaspersky's StrikeShark write-up describes the DscCoreR.mui
stage as a zlib-compressed MinHook PE whose MH_Initialize and MH_CreateHook
are resolved by name - that is the prebuilt ``MinHook.x64.dll`` /
``MinHook.x86.dll`` upstream attaches to its releases, not a copy compiled
into the loader. The MinGW and MSVC recipes beside this one rebuild the same
two tags for coverage; this one files the bytes upstream actually shipped.

Both releases are harvested, for the reason minhook.py pins both tags:
v1.3.3 (2017-01-07) was the only release for eight years, v1.3.4
(2025-03-28) is current, and the published report does not say which one the
sample carries.

Pinned by the digest of the release asset rather than by a git ref, because
the binary is the thing being pinned and no commit identifies it:

    v1.3.3  MinHook_133_bin.zip  78163b7b74142fcf3adc9b426d516a60f636f1b1ebe98a19545e2913bbda95fa
    v1.3.4  MinHook_134_bin.zip  c9d723e18e8919a40a45cf35f3ac1f82936c480314225866424b9056c46f02b6

Only the ``_bin`` asset is taken. The same releases also publish
``MinHook_13x_lib.zip`` (static ``libMinHook.*.lib`` archives for several
Visual Studio versions), and SMDA has no COFF/ar loader, so those are not
reference data this pipeline can read.

**What compiled them**, read off the PE headers rather than inferred from the
host that runs the harvest (this Linux box):

    v1.3.3  linker 14.10, Rich-header build 24629   -> MSVC v141 (VS2017 RTM)
    v1.3.4  linker 14.43, Rich-header build 34808   -> MSVC v143 (VS2022 17.13)

so ``Artifact.producer`` states ``msvc141`` and ``msvc143``, and the README
labels each row "as distributed upstream". That matters for v1.3.4 in
particular: ``MinHook_1.3.4_msvc143_x64_MinHook.dll`` is already the stem of
the MSVC *source* build, so the harvested image takes the component
``MinHook_bin.dll`` - after upstream's own asset name, ``MinHook_134_bin.zip``
- and keeps the true version rather than overwriting that file or sharing its
README row.

Neither DLL carries a debug directory and no PDB is published, so the export
table is the only source of names: the twelve ``MH_*`` entry points are named
and everything they reach is ``sub_*``. ``min_named_ratio`` is therefore 0, as
it is for the other harvested MSVC prebuilt in this corpus (Meterpreter's).
What these reports add is the exact code shape of the shipped DLL, which is
what a match against a sample carrying it runs on; the source-built MSVC rows
in this family are where the names are.

What the four images contain, measured, kept + removed = total:

    1.3.3 x86   35 + 0 = 35   12 named (the exports), 28 of 10+ instructions
    1.3.3 x64   36 + 0 = 36   12 named, 26 of 10+ instructions
    1.3.4 x86   33 + 0 = 33   12 named, 28 of 10+ instructions
    1.3.4 x64   36 + 0 = 36   12 named, 26 of 10+ instructions

Nothing is removed as compiler runtime: these are /NOENTRY DLLs against the
DLL runtime, so no CRT body is linked in (the source-built MSVC rows say the
same), and the glue filter only drops a body whose name and PicHash both
match a probe, which no unnamed body can.

**They are not the source build.** PicHash overlap, functions of 10+
instructions, against the MSVC v143 rebuild of the same tag:

    1.3.4 x64   10 of 26 shared   (EnableHook, QueueHook, FreeBuffer, ...)
    1.3.4 x86    5 of 28 shared
    1.3.3 x64    5 of 26 shared   (v141 prebuilt vs v143 rebuild)
    1.3.3 x86    3 of 28 shared

and between the two prebuilts 8 (x64) and 5 (x86). Even at v1.3.4, where
both sides are v143, the length disassembler alone differs - 497 instructions
in the prebuilt against 502 in the rebuild - so the shipped bytes are worth
having in their own right rather than as a duplicate of a rebuild.

**HDE overlap.** ``hde32_disasm`` / ``hde64_disasm`` (Hacker Disassembler
Engine, Copyright (c) 2008-2009 Vyacheslav Patkov) is vendored in
``src/hde/`` and is inside these images, unnamed. ``data/APICallProxy``
vendors the same engine as ``DisableDSE/hde64.h``, but DisableDSE is one of
its user-mode projects that are not built, so that artefact contains no HDE
body: measured, none of the twelve MinHook images (MinGW, MSVC, prebuilt)
shares a PicHash of 10+ instructions with data/APICallProxy. A match on the
length disassembler is still shared third-party code rather than evidence of
MinHook specifically.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_NOTES = (
    "Harvested, not rebuilt: the MinHook.{x86,x64}.dll that upstream attaches "
    "to its GitHub release as MinHook_13x_bin.zip, pinned by the asset's "
    "sha256. This is the prebuilt PE the Kaspersky StrikeShark sample "
    "(securelist.com/strikeshark-campaign/120326) carries zlib-compressed in "
    "DscCoreR.mui. The producer is read off the PE headers (linker version "
    "and Rich-header build), not inferred from the Linux host that ran the "
    "harvest. No PDB is published and the DLLs have no debug directory, so "
    "only the twelve exported MH_* functions are named. The HDE length "
    "disassembler (hde32_disasm/hde64_disasm, Copyright (c) 2008-2009 "
    "Vyacheslav Patkov) is vendored in src/hde and is part of these images, "
    "unnamed. data/APICallProxy vendors the same engine as DisableDSE/hde64.h, "
    "but DisableDSE is one of its unbuilt user-mode projects, so no HDE body "
    "is in that artefact: measured, none of the MinHook images shares a "
    "PicHash of 10 or more instructions with data/APICallProxy. Not a "
    "duplicate of the source build: of the functions of 10+ instructions, "
    "10 of 26 (1.3.4 x64) and 5 of 28 (1.3.4 x86) share a PicHash with the "
    "MSVC v143 rebuild of the same tag.")


def _prebuilt(version, tag, asset, sha256, producer, linker):
    return Recipe(
        family="MinHook",
        version=version,
        upstream="https://github.com/TsudaKageyu/minhook",
        license="BSD-2-Clause",
        source=Source(
            url="https://github.com/TsudaKageyu/minhook/releases/download/%s/%s"
                % (tag, asset),
            sha256=sha256),
        # Nothing to build: the asset unpacks to bin/ and include/ and the
        # DLLs are taken as they are. A step is still recorded so the build
        # log shows what was there.
        build=[BuildStep("ls -l bin")],
        # One artefact with {arch} resolved per leg, as the Meterpreter
        # prebuilt does, so `component` stays unique within the recipe.
        artifacts=[Artifact(path="bin/MinHook.{arch}.dll",
                            component="MinHook_bin.dll",
                            producer=producer)],
        # A toolchain selects nothing here but which leg's file is read; the
        # architecture in the stem comes from the PE header.
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="%s (as distributed by upstream, %s); exact flags not "
                    "published" % (producer.replace("msvc", "MSVC v"), linker),
        min_named_ratio=0,
        notes=_NOTES,
    )


RECIPES = {
    # The release asset of tag v1.3.3 (2017-01-07).
    "MinHook_1.3.3_prebuilt": _prebuilt(
        "1.3.3", "v1.3.3", "MinHook_133_bin.zip",
        "78163b7b74142fcf3adc9b426d516a60f636f1b1ebe98a19545e2913bbda95fa",
        "msvc141", "PE linker 14.10, Rich build 24629"),
    # The release asset of tag v1.3.4 (2025-03-28).
    "MinHook_1.3.4_prebuilt": _prebuilt(
        "1.3.4", "v1.3.4", "MinHook_134_bin.zip",
        "c9d723e18e8919a40a45cf35f3ac1f82936c480314225866424b9056c46f02b6",
        "msvc143", "PE linker 14.43, Rich build 34808"),
}
