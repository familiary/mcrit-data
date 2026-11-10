"""miniLZO as a family of its own, beside the full LZO library.

Tracker #59 asks for miniLZO and the full liblzo2 as two families. The lzo
family (lzo.py) already holds both, as two artefacts: liblzo2-2.dll and
minilzo.dll (version minilzo-2.10). Existing data is not renamed or moved,
so this family adds miniLZO 2.10 under its own name, from the same
minilzo-2.10 tarball (sha256 computed from the download, upstream lists a
SHA1 only), with minilzo.c compiled directly and nothing patched.

Which images are committed. A miniLZO family image built with the same
compiler and flags as the lzo family's minilzo.dll is the same code, and an
image whose PicHash set is identical to one already in the corpus adds
nothing, so it is not committed: the measurement is below. The
Linux ELF axis does not exist in the lzo family and is committed here.

Measured. MinGW (the same `{cc} -O2 -shared` over minilzo.c) and MSVC (the
lzo_minilzo_2.10_msvc command lines, scoped run 42775540720) were built under
the miniLZO name and are PicHash-identical, every function at every size, to
the lzo family's minilzo-2.10 images (MinGW x86 21 + 53 = 74, x64 30 + 54 =
84; MSVC x86 25 + 125 = 150, x64 25 + 131 = 156, the same counts), so they
are not committed and have no recipe here; those images are the lzo
family's. Linux ELF, -O2 -fPIC -fvisibility=hidden: x86 38 + 4 = 42 (16
PicHashes of ten instructions or more, 5 of them in the MinGW image), x64
32 + 6 = 38 (8, none in any PE image). Kept + removed = total, no
exclusions.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_SOURCE = Source(
    url="https://www.oberhumer.com/opensource/lzo/download/minilzo-2.10.tar.gz",
    sha256="eb4ce543aad19533c83550746e0e9d7bcf716b35a42429e3ba17d60fa0f3e47a")

_NOTES = ("miniLZO 2.10 (minilzo.c 213674 bytes, the size the tracker "
          "reports for UltraVNC's vendored lzo/minilzo.c), from the "
          "minilzo-2.10 tarball, as its own family per tracker #59. The lzo "
          "family carries the same build as its minilzo-2.10 artefact; "
          "every miniLZO function is also in the full liblzo2. ")

RECIPES = {
    "miniLZO_2.10_linux": Recipe(
        family="miniLZO", version="2.10",
        upstream="https://www.oberhumer.com/opensource/lzo/",
        license="GPL-2.0-or-later", source=_SOURCE,
        build=[BuildStep("{cc} {archflag} -O2 -fPIC -fvisibility=hidden "
                         "-shared -o libminilzo.so minilzo.c")],
        artifacts=[Artifact(path="libminilzo.so",
                            component="libminilzo.so")],
        toolchains=["linux_x86", "linux_x64"],
        build_flags="-O2 -fPIC -fvisibility=hidden (minilzo.c compiled "
                    "directly with -shared)",
        notes=_NOTES + "Linux ELF shared object, the axis the lzo family "
              "does not have; with hidden visibility nothing is exported "
              "and the names are in .symtab."),
}
