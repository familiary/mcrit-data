"""sRDI / DAVESHELL - reflective DLL injection shellcode (mcrit-data issue #3).

The shellcode cannot be rebuilt here: it needs MSVC's `/ORDER:@function_link_order.txt`,
`/ENTRY:LoadDLL` and `/Oi` intrinsics, and a MinGW port would produce a code
shape that nobody ships. It does not need rebuilding, though - upstream commits
the compiled MSVC blob into Python/ShellcodeRDI.py, and that blob is precisely
what is encountered in the wild. It is extracted and disassembled as a buffer,
the same route the aPLib reports in this repository took.

The repository has no tags, so versions are pinned to the commits that changed
the blob. The three chosen bracket the two largest code-shape breaks.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_EXTRACT = ("python3 {repo}/scripts/corpus/extract_blob.py python "
            "Python/ShellcodeRDI.py %s %s")


def _srdi(version, git_ref):
    return Recipe(
        family="sRDI",
        version=version,
        upstream="https://github.com/monoxgas/sRDI",
        license="GPL-3.0, with BSD-licensed PIC_BindShell and "
                "ReflectiveDLLInjection primitives",
        source=Source(git_url="https://github.com/monoxgas/sRDI.git", git_ref=git_ref),
        build=[
            BuildStep(_EXTRACT % ("rdiShellcode32", "rdi_x86.bin")),
            BuildStep(_EXTRACT % ("rdiShellcode64", "rdi_x64.bin")),
        ],
        artifacts=[
            Artifact(path="rdi_x86.bin", component="ShellcodeRDI_x86",
                     is_blob=True, bitness=32),
            Artifact(path="rdi_x64.bin", component="ShellcodeRDI_x64",
                     is_blob=True, bitness=64),
        ],
        # The blobs are already compiled; the toolchain here only selects which
        # machine runs the extraction, and the architecture comes from the blob.
        toolchains=["mingw_x64"],
        build_flags="MSVC /O1 (as committed upstream)",
        notes="Compiled by upstream with MSVC and committed; not rebuilt here.",
    )


RECIPES = {
    # The long-lived 2018-2019 build, pre-refactor.
    "sRDI_2018-05-27": _srdi("2018-05-27", "59b07c5c7d4fd0503ebf404528b577775cd683c1"),
    # Core symbol lookup migrated to ntdll - a large code-shape change.
    "sRDI_2020-04-15": _srdi("2020-04-15", "783d530084289f9244dea6e450e21d4011fc2472"),
    # Current head.
    "sRDI_2022-06-17": _srdi("2022-06-17", "9fdd5c44383039519accd1e6bac4acd5a046a92c"),
}
