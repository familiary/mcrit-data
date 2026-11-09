"""nanopb - Protocol Buffers for small C targets (pb_common.c, pb_decode.c,
pb_encode.c).

backlog r0ny123/mcrit-data#38. data/protobuf is Google's C++ runtime; this
is the unrelated C implementation of the same wire format that firmware,
embedded and IoT code uses instead, so a sample that parses protobuf without
Google's library had no reference here. The evidence for wanting it is
naming only: nobody has shown a Windows sample built on nanopb, and the
project is firmware-oriented, so its value in this corpus is the family's
presence rather than a measured hit. It shares no code with data/protobuf
(different language, different design), and that is the point of the entry.

Upstream publishes no release checksums, hence git tags. Each release has
three tag spellings of one commit (`0.4.9.2`, `nanopb-0.4.9.2`, and for the
last two `0.4.92`); `nanopb-<version>` is used since it is the only form
present for every release.

Build. The library is three C files. Upstream's CMake does have a shared
target (`BUILD_SHARED_LIBS=ON` gives `protobuf-nanopb`), but it fails at
configure unless a `protoc` is found, whether or not the generator is built,
and it sets no optimisation level without CMAKE_BUILD_TYPE (that is -O0, see
below). So the DLL is linked directly from the three files with the
toolchain's own flags (-O2) and no defines; MinGW's ld exports every global
symbol when no dllexport is used, so the report carries the real API names.
No upstream file is patched. Measured on 0.4.9.2, 43 functions of 10+
instructions on x86 and 40 on x64.

Default build, and what the options do. Upstream's default defines nothing:
no PB_ENABLE_MALLOC, no PB_FIELD_32BIT, no PB_BUFFER_ONLY. Each was built
over 0.4.9.2 and compared by PicHash (10+ instructions, default build
x86 43 / x64 40):

  PB_ENABLE_MALLOC   +2 functions, +4 of 10+ instructions (pb_release and
                     friends); shares 40 / 37 of the
                     default's hashes. Additive, so the default already
                     recognises most of it.
  PB_FIELD_32BIT     same function list, but shares only 25 / 23: the field
                     descriptor layout changes the address arithmetic of
                     every decode and encode routine.
  PB_BUFFER_ONLY     shares 21 / 21 (stream callbacks removed).
  PB_NO_ERRMSG       shares 19 / 16.
  PB_NO_PACKED_STRUCTS  identical to default (43 / 40).

Those options do change the code materially. No variant is shipped, because
the matrix is unbounded and the project says nothing about which
combination any given firmware used; the limitation is stated instead.
The compiler flags matter far more: against the -O2 default, -O3 shares 21 /
23, -Os 1 / 2 and -O0 1 / 1 (and is 77 / 78 functions rather than 43 / 40).
Embedded code is commonly built -Os, so a real nanopb sample is more likely
to match this family by MinHash than by PicHash.

Versions, measured by PicHash overlap on functions of 10+ instructions
(x86 / x64, % of the smaller set):

  0.3.9.10 vs 0.4.5     20 of 42 (48%) / 18 of 39 (46%)
  0.4.5    vs 0.4.9.2   27 of 43 (63%) / 25 of 40 (63%)
  0.3.9.10 vs 0.4.9.2   11 of 43 (26%) / 9 of 40 (23%)

0.3.9.10 is the last of the 0.3 line (February 2024, still shipped by
distributions) and shares under a quarter with current code. 0.4.5 sits
between: 0.4.7 and 0.4.9 are, for the library, the same code (43 of 43 and
39 of 39 hashes in common), and 0.4.9.2 differs from them by three, so
neither is kept. 0.4.9.2 is the current release and carries the callback
and nesting-depth fixes. 0.4.0 - 0.4.4 and 0.4.6 were not measured. Artefacts
hold 62 / 71 (0.3.9.10), 48 / 57 (0.4.5) and 50 / 59 (0.4.9.2) functions on
x86 / x64, so the corpus floor is met without min_functions.

Known baseline gap, left to the baseline: libgcc's stack probe
(`___chkstk_ms`, 15 instructions) is carried unnamed in all six artefacts,
PicHash dfe3cea2dbb80872 on x86 and ae8f920c3b4e652a on x64.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


def _nanopb(version):
    return Recipe(
        family="nanopb",
        version=version,
        upstream="https://github.com/nanopb/nanopb",
        license="Zlib",
        source=Source(git_url="https://github.com/nanopb/nanopb.git",
                      git_ref="nanopb-" + version),
        build=[
            BuildStep("mkdir -p build-{arch}"),
            BuildStep("{cc} {cflags} -I. -shared "
                      "-o build-{arch}/libprotobuf-nanopb.dll "
                      "pb_common.c pb_decode.c pb_encode.c"),
        ],
        artifacts=[Artifact(path="build-{arch}/libprotobuf-nanopb.dll",
                            component="libprotobuf-nanopb.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 (toolchain default), no PB_* defines (upstream default), "
                    "linked directly from pb_common.c, pb_decode.c, pb_encode.c",
        notes="Three source files built as one DLL; upstream CMake needs protoc "
              "even for the runtime, so it is not used. Evidence for inclusion "
              "is naming only.",
    )


RECIPES = {
    "nanopb_0.3.9.10": _nanopb("0.3.9.10"),
    "nanopb_0.4.5": _nanopb("0.4.5"),
    "nanopb_0.4.9.2": _nanopb("0.4.9.2"),
}
