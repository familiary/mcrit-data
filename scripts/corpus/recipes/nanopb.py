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

Those options do change the code materially. The matrix is unbounded and the
project says nothing about which combination any given firmware used, so only
three combinations are shipped, for 0.4.9.2 and as additional artefacts of the
same recipe beside the default build (see the next section); the limitation
for every other combination is stated instead.

Generated code and the build-time defines (backlog #38). Three further DLLs,
each the three runtime files plus ``driver.pb.c``, which the build generates
with upstream's own ``generator/nanopb_generator.py`` from a minimal
``driver.proto`` (one enum, two messages, scalar, string, bytes, repeated,
nested-message and oneof fields) and a ``driver.options`` giving the
strings and arrays fixed sizes. Both files are written by the build, and the
generator runs against protoc from ``grpcio-tools==1.85.1`` installed with
``pip --target`` into the build tree, so nothing is installed on the host. The
defines are in each artefact's build_flags:

  libprotobuf-nanopb-all    PB_FIELD_32BIT PB_NO_ERRMSG PB_BUFFER_ONLY
                            PB_ENABLE_MALLOC (the four the tracker names)
  libprotobuf-nanopb-small  PB_NO_ERRMSG PB_BUFFER_ONLY
  libprotobuf-nanopb-big    PB_FIELD_32BIT PB_ENABLE_MALLOC

Kept + removed = image total, x86 / x64: all 48 + 51 = 99 / 58 + 52 = 110,
small 48 + 51 = 99 / 58 + 52 = 110, big 52 + 51 = 103 / 61 + 52 = 113 (the
default 0.4.9.2 build is 50 + 51 = 101 / 59 + 52 = 111). A generated ``*.pb.c``
is a table of ``pb_msgdesc_t`` descriptors and contains no function, so it
adds no code to an image: the symbols that differ from the default build are
all runtime functions selected by the defines (``pb_release_single_field``,
``allocate_field`` with PB_ENABLE_MALLOC; ``encode_basic_field`` inlined or
not under PB_BUFFER_ONLY). What the .proto changes is which descriptor
layout the runtime is called with, and the driver is not intended to
vary function bodies; no name in any of the three images mentions it.
PicHash overlap, functions of 10+ instructions, x86 / x64, against the default
build (43 / 40 distinct): all 4 / 5, small 12 / 12, big 24 / 22; among the
three, all~small 22 / 20, all~big 15 / 15, small~big 4 / 5. They are
therefore distinct data, not copies of the default artefact. Only 0.4.9.2 is
built this way (the 0.3.9.10 and 0.4.5 generators were not tried).
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


# The driver .proto the generated *.pb.c comes from, written by the build
# rather than kept as a repository file. Single quotes only (the python -c
# line is double-quoted for both sh and cmd, and proto accepts 'proto3').
_DRIVER_PROTO = [
    "syntax = \\x27proto3\\x27;",
    "package driver;",
    "enum Kind { KIND_NONE = 0; KIND_PING = 1; KIND_DATA = 2; }",
    "message Point { sint32 x = 1; sint32 y = 2; }",
    "message Packet {",
    "  uint32 id = 1;",
    "  int64 stamp = 2;",
    "  fixed32 crc = 3;",
    "  bool urgent = 4;",
    "  float gain = 5;",
    "  double offset = 6;",
    "  string name = 7;",
    "  bytes payload = 8;",
    "  Kind kind = 9;",
    "  repeated int32 samples = 10;",
    "  Point origin = 11;",
    "  repeated Point path = 12;",
    "  oneof body { string text = 13; uint64 counter = 14; }",
    "}",
]
_DRIVER_OPTIONS = [
    "driver.Packet.name max_size:32",
    "driver.Packet.payload max_size:64",
    "driver.Packet.samples max_count:16",
    "driver.Packet.path max_count:8",
    "driver.Packet.text max_size:48",
]


def _write(name, lines):
    body = ", ".join("'%s'" % line for line in lines)
    return ('python -c "open(\'%s\',\'w\').write(\'\\n\'.join([%s])+\'\\n\')"'
            % (name, body))


# Generated-code configurations, additional artefacts of 0.4.9.2 only. Each
# compiles the three runtime files plus the generated driver.pb.c with the
# build-time defines the tracker names (#38).
_CONFIGS = [
    ("libprotobuf-nanopb-all.dll",
     "-DPB_FIELD_32BIT -DPB_NO_ERRMSG -DPB_BUFFER_ONLY -DPB_ENABLE_MALLOC"),
    ("libprotobuf-nanopb-small.dll", "-DPB_NO_ERRMSG -DPB_BUFFER_ONLY"),
    ("libprotobuf-nanopb-big.dll", "-DPB_FIELD_32BIT -DPB_ENABLE_MALLOC"),
]

_GRPC_TOOLS = "grpcio-tools==1.85.1"


def _nanopb(version, generated=False):
    steps = [
        BuildStep("mkdir -p build-{arch}"),
        BuildStep("{cc} {cflags} -I. -shared "
                  "-o build-{arch}/libprotobuf-nanopb.dll "
                  "pb_common.c pb_decode.c pb_encode.c"),
    ]
    artifacts = [Artifact(path="build-{arch}/libprotobuf-nanopb.dll",
                          component="libprotobuf-nanopb.dll")]
    notes = ("Three source files built as one DLL; upstream CMake needs "
             "protoc even for the runtime, so it is not used. Evidence for "
             "inclusion is naming only.")
    if generated:
        steps += [
            BuildStep("python -m pip install --quiet --target gen-deps "
                      + _GRPC_TOOLS),
            BuildStep("mkdir gen"),
            BuildStep(_write("gen/driver.proto", _DRIVER_PROTO)),
            BuildStep(_write("gen/driver.options", _DRIVER_OPTIONS)),
            BuildStep("python ../generator/nanopb_generator.py driver.proto",
                      cwd="gen", env={"PYTHONPATH": "../gen-deps"}),
        ]
        for component, defines in _CONFIGS:
            steps.append(BuildStep(
                "{cc} {cflags} -I. -Igen %s -shared "
                "-o build-{arch}/%s pb_common.c pb_decode.c pb_encode.c "
                "gen/driver.pb.c" % (defines, component)))
            artifacts.append(Artifact(
                path="build-{arch}/" + component, component=component,
                build_flags="-O2 (toolchain default) %s, runtime plus "
                            "generated driver.pb.c" % defines))
        notes += (" The -all, -small and -big DLLs add the generated "
                  "driver.pb.c (nanopb_generator.py over a minimal "
                  "driver.proto and driver.options, protoc from "
                  + _GRPC_TOOLS + ") and the PB_* defines named in their "
                  "build_flags.")
    return Recipe(
        family="nanopb",
        version=version,
        upstream="https://github.com/nanopb/nanopb",
        license="Zlib",
        source=Source(git_url="https://github.com/nanopb/nanopb.git",
                      git_ref="nanopb-" + version),
        build=steps,
        artifacts=artifacts,
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 (toolchain default), no PB_* defines (upstream default), "
                    "linked directly from pb_common.c, pb_decode.c, pb_encode.c",
        notes=notes,
    )


RECIPES = {
    "nanopb_0.3.9.10": _nanopb("0.3.9.10"),
    "nanopb_0.4.5": _nanopb("0.4.5"),
    "nanopb_0.4.9.2": _nanopb("0.4.9.2", generated=True),
}
