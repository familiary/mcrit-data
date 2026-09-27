"""bzip2 - long-lived compression code found in installers and archivers.

No coverage exists in the corpus today. Upstream ships no Windows DLL rule,
so the objects are compiled individually and linked against the libbz2.def
that upstream does ship - the sources themselves stay untouched.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_OBJECTS = "blocksort huffman crctable randtable compress decompress bzlib"


def _bzip2(version, sha256):
    return Recipe(
        family="bzip2",
        version=version,
        upstream="https://sourceware.org/pub/bzip2/",
        license="bzip2-1.0.6 (BSD-like)",
        source=Source(url="https://sourceware.org/pub/bzip2/bzip2-%s.tar.gz" % version,
                      sha256=sha256),
        build=[
            BuildStep("rm -f *.o libbz2.dll bzip2.exe", allow_failure=True),
            BuildStep("for unit in %s; do {cc} -O2 -D_FILE_OFFSET_BITS=64 "
                      "-c $unit.c -o $unit.o || exit 1; done" % _OBJECTS),
            # --enable-stdcall-fixup silences the x86 decoration warnings; the
            # resulting DLL is identical with or without it.
            BuildStep("{cc} -shared -Wl,--enable-stdcall-fixup -o libbz2.dll "
                      "libbz2.def *.o -Wl,--out-implib,libbz2.dll.a"),
            BuildStep("{cc} -O2 -o bzip2.exe bzip2.c *.o"),
        ],
        # bzip2.exe statically links the same objects as libbz2.dll: the two
        # share 45 of the DLL's 46 functions, so shipping both would add one
        # function and 45 duplicates. The EXE is the superset and is kept.
        artifacts=[Artifact(path="bzip2.exe", component="bzip2.exe")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2",
    )


RECIPES = {
    # The release almost everything has shipped since 2019.
    "bzip2_1.0.8": _bzip2(
        "1.0.8", "ab5a03176ee106d3f0fa90e381da478ddae405918153cca248e682cd0c4a2269"),
}
