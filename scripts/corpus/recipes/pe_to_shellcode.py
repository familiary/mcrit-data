"""pe_to_shellcode loader stubs (mcrit-data issue #6).

The issue asks to "convert stubs from the project". They cannot be rebuilt
here - loader_v2 is built with `cl` plus `ml`/`ml64` and the external
masm_shc tool - but they do not need rebuilding: upstream commits the
compiled stubs as raw .bin files, and those MSVC-built bytes are what ships
inside anything using pe2shc. They are disassembled as buffers.

Only stub2 is covered. stub1 (`hldr32`/`hldr64`) is a single hand-written
assembly routine of ~130 instructions by hh86; it yields too few distinct
functions to carry a useful minhash, and the pipeline's minimum-function
check rejects it on those grounds. It also carries a separate CC-BY licence
that would require attribution if it were ever included.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


def _pe2shc(version, git_ref):
    return Recipe(
        family="pe_to_shellcode",
        version=version,
        upstream="https://github.com/hasherezade/pe_to_shellcode",
        license="BSD-2-Clause",
        source=Source(git_url="https://github.com/hasherezade/pe_to_shellcode.git",
                      git_ref=git_ref),
        # The stubs are committed as raw binaries; nothing needs building.
        build=[],
        artifacts=[
            Artifact(path="pe2shc/stub2/stub32.bin", component="stub2_x86",
                     is_blob=True, bitness=32, is_library=False),
            Artifact(path="pe2shc/stub2/stub64.bin", component="stub2_x64",
                     is_blob=True, bitness=64, is_library=False),
        ],
        toolchains=["mingw_x64"],
        build_flags="MSVC /O1 (as committed upstream)",
        notes="Compiled by upstream with MSVC and committed; not rebuilt here.",
    )


RECIPES = {
    # First release carrying the loader_v2 C++ stub.
    "pe_to_shellcode_1.0": _pe2shc("1.0", "7d91fccb04b6230988115fb758033077fee13ae1"),
    # Current; loader_v2 gained DLL-unload support.
    "pe_to_shellcode_1.2": _pe2shc("1.2", "0f606929eac1530a4fb39b9494a0d46f4c73eaed"),
}
