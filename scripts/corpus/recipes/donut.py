"""donut - position-independent loader generator (mcrit-data issue #5).

What is worth covering here is the loader, not the generator. The loader is
the position-independent code donut embeds in whatever it is asked to
package, so it is what turns up in samples; the generator is a builder that
runs on the operator's machine. Upstream commits the loader as MSVC-compiled
C arrays in loader_exe_x86.h and loader_exe_x64.h, and those same arrays are
what ships in the release binaries and in the donut-shellcode PyPI package,
so they are extracted and disassembled as buffers.

The generator is deliberately not built. Makefile.mingw links
lib/aplib64.lib, so donut.exe would statically contain aPLib's compressor -
and aPLib is already its own family in this repository, so those functions
would be duplicated under the donut name. The generator is also built
without any -O, which makes for poor reference code even setting the
duplication aside.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


def _donut(version, git_ref):
    return Recipe(
        family="donut",
        version=version,
        upstream="https://github.com/TheWover/donut",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/TheWover/donut.git", git_ref=git_ref),
        build=[
            BuildStep("python3 {repo}/scripts/corpus/extract_blob.py carray "
                      "loader_exe_x86.h donut_loader_x86.bin"),
            BuildStep("python3 {repo}/scripts/corpus/extract_blob.py carray "
                      "loader_exe_x64.h donut_loader_x64.bin"),
        ],
        artifacts=[
            Artifact(path="donut_loader_x86.bin", component="loader_x86",
                     is_blob=True, bitness=32,
                     build_flags="MSVC -Zp8 -Gy -Os -O1 -GR- -EHa -Oi -GS- "
                                 "(Makefile.msvc, as committed upstream)"),
            Artifact(path="donut_loader_x64.bin", component="loader_x64",
                     is_blob=True, bitness=64,
                     build_flags="MSVC -Zp8 -Gy -Os -O1 -GR- -EHa -Oi -GS- "
                                 "(Makefile.msvc, as committed upstream)"),
        ],
        # Nothing is compiled here - the blobs come out of the repository as
        # upstream committed them - but the pipeline still needs one
        # toolchain entry to run under.
        toolchains=["mingw_x64"],
        build_flags="see the per-artefact flags",
        notes="The loader blobs committed upstream in loader_exe_x86.h and "
              "loader_exe_x64.h, which is the code donut embeds in its "
              "output. The generator is not built: it statically links the "
              "vendored lib/aplib64.lib, and aPLib is already a family in "
              "this repository.",
    )


RECIPES = {
    # Current release. v1.0 carries byte-identical loader blobs, so it adds
    # nothing on that axis and is not covered separately.
    "donut_1.1": _donut("1.1", "47758d787209dd1744f58c140102ac91b649df16"),
}
