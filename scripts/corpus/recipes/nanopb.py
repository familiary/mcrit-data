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

Generated code and the build-time defines (backlog #38). Three further DLLs
per version (0.3.9.10, 0.4.5 and 0.4.9.2; the older two are described under
"The older generators" below),
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
therefore distinct data, not copies of the default artefact.
The older generators (0.3.9.10 and 0.4.5). The same three DLLs per version,
the same driver and defines, built by the same recipe function. Both
generators are far older than the current protoc, so protoc comes from
``grpcio-tools==1.51.3 grpcio==1.51.3 protobuf==4.21.12 setuptools==84.2.1``
(protoc 3.21.x, installed with ``pip --target`` under Python 3.11, the
interpreter of the local and CI builds). Nothing in the upstream tree is
patched; at 0.3.9.10 the two *_pb2.py files are build outputs written into
generator/proto, as upstream's Makefile does.

  0.4.5      nanopb_generator.py takes driver.proto and runs protoc itself
             (grpc_tools.protoc through PYTHONPATH); driver.options is used
             exactly as for 0.4.9.2.
  0.3.9.10   The generator is Python-2 era and does not take a .proto. It
             reads a protoc descriptor set and imports
             generator/proto/{nanopb,plugin}_pb2.py, which upstream's
             Makefile makes with ``protoc --python_out=.``; the build runs
             that command through grpc_tools.protoc (no protoc binary is
             needed), writes the descriptor set with ``-o driver.pb`` and runs
             ``nanopb_generator.py driver.pb``. One obstacle: its options-file
             reader opens the file with mode "rU", which Python 3.11 rejects
             (``ValueError: invalid mode: 'rU'``, nanopb_generator.py line
             1644). So there is no driver.options at 0.3.9.10: the same fixed
             sizes (name 32, payload 64, samples 16, path 8, text 48) are given
             inline in driver.proto as ``[(nanopb).max_size = N]`` and
             ``[(nanopb).max_count = N]``, nanopb's documented alternative,
             with ``import 'nanopb.proto'``. The generated structs match the
             0.4 ones (char name[32], int32_t samples[16], ...).

Kept + removed = image total, x86 / x64:

                       0.3.9.10                       0.4.5
  default   62 + 49 = 111 / 71 + 50 = 121   48 + 50 = 98 / 57 + 51 = 108
  -all      63 + 51 = 114 / 72 + 52 = 124   48 + 50 = 98 / 58 + 51 = 109
  -small    61 + 49 = 110 / 70 + 50 = 120   47 + 50 = 97 / 57 + 51 = 108
  -big      66 + 51 = 117 / 75 + 52 = 127   51 + 50 = 101 / 60 + 51 = 111

PicHash overlap, functions of 10+ instructions, x86 / x64, distinct hashes in
the default build 57 / 55 (0.3.9.10) and 42 / 39 (0.4.5):

                         0.3.9.10     0.4.5
  default ~ all           5 / 5        4 / 5
  default ~ small        14 / 12      12 / 12
  default ~ big          31 / 29      24 / 22
  all ~ small            29 / 27      22 / 20
  all ~ big              17 / 15      15 / 15
  small ~ big             5 / 5        4 / 5

Across versions, the same configuration shares (0.3.9.10~0.4.5 / 0.3.9.10~
0.4.9.2 / 0.4.5~0.4.9.2, x86; x64 in brackets): default 20 / 11 / 27 (18 / 9 /
25), all 18 / 10 / 28 (14 / 7 / 26), small 18 / 10 / 27 (14 / 7 / 25), big 21
/ 12 / 31 (19 / 10 / 28). As at 0.4.9.2 the generated driver.pb.c is a
descriptor table and adds no function; what differs from the default build is
runtime code selected by the defines (pb_release, pb_release_single_field and
initialize_pointer_field at 0.3.9.10; pb_release, pb_release_single_field and
encode_basic_field at 0.4.5 are present in the -all image and not in the
default one; buf_read and buf_write are absent from it, inlined away). No function name in any of the
twelve new images mentions the driver.

The compiler flags matter far more: against the -O2 default, -O3 shares 21 /
23, -Os 1 / 2 and -O0 1 / 1 (and is 77 / 78 functions rather than 43 / 40).
Embedded code is commonly built -Os, so that build is shipped too.

The size-optimised build. Every version has a fifth DLL,
``libprotobuf-nanopb-Os.dll``: the default runtime (three files, no defines,
no driver) compiled with -Os in place of -O2 and nothing else changed. Kept +
removed = image total, x86 / x64, with the -O2 default beside it:

              -Os                               -O2
  0.3.9.10    64 + 49 = 113 / 73 + 50 = 123     62 + 49 = 111 / 71 + 50 = 121
  0.4.5       51 + 49 = 100 / 60 + 50 = 110     48 + 50 = 98 / 57 + 51 = 108
  0.4.9.2     52 + 49 = 101 / 61 + 50 = 111     50 + 51 = 101 / 59 + 52 = 111

-Os keeps two or three more functions (less inlining) and removes one or two
fewer at 0.4.x: memset (and at 0.4.9.2 memcpy) is not linked at -Os, where GCC
expands those calls inline. PicHash overlap of the -Os image with the -O2
default of the same version, functions of 10+ instructions, x86 / x64, as
shared of distinct -Os / -O2 hashes: 0.3.9.10 1 of 55 / 57 and 2 of 47 / 55;
0.4.5 1 of 47 / 42 and 2 of 41 / 39; 0.4.9.2 1 of 47 / 43 and 2 of 41 / 40.
So the -Os images share almost nothing with the -O2 ones and are separate
data. They carry the same unnamed stack probe as the default build (see the
last paragraph). Only the default configuration is built at -Os; the -all,
-small and -big define sets remain -O2 only, so an -Os sample built with
other PB_* options is still more likely to match by MinHash than by PicHash.

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
(`___chkstk_ms`, 15 instructions) is carried unnamed in every artefact,
PicHash dfe3cea2dbb80872 on x86 and ae8f920c3b4e652a on x64.

Second pass: the other define combinations and -Os of the shipped sets, as
versions "<tag>-defines" so the images above are unchanged. Per tag, the
runtime plus generated driver.pb.c with each of the twelve non-empty subsets
of {PB_FIELD_32BIT, PB_NO_ERRMSG, PB_BUFFER_ONLY, PB_ENABLE_MALLOC} not
already shipped (libprotobuf-nanopb-<field32, noerrmsg, bufferonly, malloc
joined by "-">.dll) at -O2, and -all, -small and -big at -Os
(libprotobuf-nanopb-<set>-Os.dll). Kept + removed = total (no exclusions):

    0.3.9.10-defines libprotobuf-nanopb-all-Os.dll x86 67 + 49 = 116, x64 76 + 50 = 126
    0.3.9.10-defines libprotobuf-nanopb-big-Os.dll x86 69 + 49 = 118, x64 78 + 50 = 128
    0.3.9.10-defines libprotobuf-nanopb-bufferonly-malloc.dll x86 64 + 49 = 113, x64 73 + 50 = 123
    0.3.9.10-defines libprotobuf-nanopb-bufferonly.dll x86 60 + 49 = 109, x64 69 + 50 = 119
    0.3.9.10-defines libprotobuf-nanopb-field32-bufferonly-malloc.dll x86 64 + 51 = 115, x64 73 + 52 = 125
    0.3.9.10-defines libprotobuf-nanopb-field32-bufferonly.dll x86 60 + 51 = 111, x64 69 + 52 = 121
    0.3.9.10-defines libprotobuf-nanopb-field32-noerrmsg-bufferonly.dll x86 61 + 51 = 112, x64 70 + 52 = 122
    0.3.9.10-defines libprotobuf-nanopb-field32-noerrmsg-malloc.dll x86 65 + 51 = 116, x64 74 + 52 = 126
    0.3.9.10-defines libprotobuf-nanopb-field32-noerrmsg.dll x86 63 + 51 = 114, x64 72 + 52 = 124
    0.3.9.10-defines libprotobuf-nanopb-field32.dll x86 62 + 51 = 113, x64 71 + 52 = 123
    0.3.9.10-defines libprotobuf-nanopb-malloc.dll x86 66 + 49 = 115, x64 75 + 50 = 125
    0.3.9.10-defines libprotobuf-nanopb-noerrmsg-bufferonly-malloc.dll x86 63 + 49 = 112, x64 72 + 50 = 122
    0.3.9.10-defines libprotobuf-nanopb-noerrmsg-malloc.dll x86 65 + 49 = 114, x64 74 + 50 = 124
    0.3.9.10-defines libprotobuf-nanopb-noerrmsg.dll x86 63 + 49 = 112, x64 72 + 50 = 122
    0.3.9.10-defines libprotobuf-nanopb-small-Os.dll x86 62 + 49 = 111, x64 71 + 50 = 121
    0.4.5-defines libprotobuf-nanopb-all-Os.dll x86 53 + 49 = 102, x64 62 + 50 = 112
    0.4.5-defines libprotobuf-nanopb-big-Os.dll x86 55 + 49 = 104, x64 64 + 50 = 114
    0.4.5-defines libprotobuf-nanopb-bufferonly-malloc.dll x86 49 + 50 = 99, x64 58 + 51 = 109
    0.4.5-defines libprotobuf-nanopb-bufferonly.dll x86 46 + 50 = 96, x64 55 + 51 = 106
    0.4.5-defines libprotobuf-nanopb-field32-bufferonly-malloc.dll x86 49 + 50 = 99, x64 58 + 51 = 109
    0.4.5-defines libprotobuf-nanopb-field32-bufferonly.dll x86 46 + 50 = 96, x64 55 + 51 = 106
    0.4.5-defines libprotobuf-nanopb-field32-noerrmsg-bufferonly.dll x86 47 + 50 = 97, x64 57 + 51 = 108
    0.4.5-defines libprotobuf-nanopb-field32-noerrmsg-malloc.dll x86 50 + 50 = 100, x64 60 + 51 = 111
    0.4.5-defines libprotobuf-nanopb-field32-noerrmsg.dll x86 49 + 50 = 99, x64 59 + 51 = 110
    0.4.5-defines libprotobuf-nanopb-field32.dll x86 48 + 50 = 98, x64 57 + 51 = 108
    0.4.5-defines libprotobuf-nanopb-malloc.dll x86 51 + 50 = 101, x64 60 + 51 = 111
    0.4.5-defines libprotobuf-nanopb-noerrmsg-bufferonly-malloc.dll x86 48 + 50 = 98, x64 58 + 51 = 109
    0.4.5-defines libprotobuf-nanopb-noerrmsg-malloc.dll x86 50 + 50 = 100, x64 60 + 51 = 111
    0.4.5-defines libprotobuf-nanopb-noerrmsg.dll x86 49 + 50 = 99, x64 59 + 51 = 110
    0.4.5-defines libprotobuf-nanopb-small-Os.dll x86 49 + 49 = 98, x64 58 + 50 = 108
    0.4.9.2-defines libprotobuf-nanopb-all-Os.dll x86 53 + 49 = 102, x64 62 + 50 = 112
    0.4.9.2-defines libprotobuf-nanopb-big-Os.dll x86 55 + 49 = 104, x64 64 + 50 = 114
    0.4.9.2-defines libprotobuf-nanopb-bufferonly-malloc.dll x86 50 + 51 = 101, x64 59 + 52 = 111
    0.4.9.2-defines libprotobuf-nanopb-bufferonly.dll x86 48 + 51 = 99, x64 57 + 52 = 109
    0.4.9.2-defines libprotobuf-nanopb-field32-bufferonly-malloc.dll x86 50 + 51 = 101, x64 59 + 52 = 111
    0.4.9.2-defines libprotobuf-nanopb-field32-bufferonly.dll x86 48 + 51 = 99, x64 57 + 52 = 109
    0.4.9.2-defines libprotobuf-nanopb-field32-noerrmsg-bufferonly.dll x86 48 + 51 = 99, x64 58 + 52 = 110
    0.4.9.2-defines libprotobuf-nanopb-field32-noerrmsg-malloc.dll x86 50 + 51 = 101, x64 60 + 52 = 112
    0.4.9.2-defines libprotobuf-nanopb-field32-noerrmsg.dll x86 50 + 51 = 101, x64 60 + 52 = 112
    0.4.9.2-defines libprotobuf-nanopb-field32.dll x86 50 + 51 = 101, x64 59 + 52 = 111
    0.4.9.2-defines libprotobuf-nanopb-malloc.dll x86 52 + 51 = 103, x64 61 + 52 = 113
    0.4.9.2-defines libprotobuf-nanopb-noerrmsg-bufferonly-malloc.dll x86 48 + 51 = 99, x64 58 + 52 = 110
    0.4.9.2-defines libprotobuf-nanopb-noerrmsg-malloc.dll x86 50 + 51 = 101, x64 60 + 52 = 112
    0.4.9.2-defines libprotobuf-nanopb-noerrmsg.dll x86 50 + 51 = 101, x64 60 + 52 = 112
    0.4.9.2-defines libprotobuf-nanopb-small-Os.dll x86 50 + 49 = 99, x64 59 + 50 = 109

Not committed, because the images were PicHash-identical (every function at
every size) to committed ones: the empty define set with the driver
(identical to libprotobuf-nanopb.dll of the same tag and architecture, all
six targets) and upstream's CMake build (see the comment at the end of this
file). Against the nearest other image of the same tag and architecture the
committed images share between 43% and 93% of their PicHashes of ten
instructions or more.
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

# protoc for the generator. 0.4.9.2 uses the current grpcio-tools; the 0.3.9.10
# and 0.4.5 generators are older code, so they get an older protoc/protobuf
# pair, installed the same way (pip --target into the build tree). The
# resolved set is what a clean install of these pins gives (python 3.11):
# grpcio 1.51.3, grpcio-tools 1.51.3 (protoc 3.21.x), protobuf 4.21.12,
# setuptools 84.2.1.
_GRPC_TOOLS = "grpcio-tools==1.85.1"
_OLD_TOOLS = ("grpcio-tools==1.51.3 grpcio==1.51.3 protobuf==4.21.12 "
              "setuptools==84.2.1")

# 0.3.9.10 reads fixed sizes from the .proto itself (see _generate_steps).
_DRIVER_PROTO_INLINE = [
    "syntax = \\x27proto3\\x27;",
    "package driver;",
    "import \\x27nanopb.proto\\x27;",
    "enum Kind { KIND_NONE = 0; KIND_PING = 1; KIND_DATA = 2; }",
    "message Point { sint32 x = 1; sint32 y = 2; }",
    "message Packet {",
    "  uint32 id = 1;",
    "  int64 stamp = 2;",
    "  fixed32 crc = 3;",
    "  bool urgent = 4;",
    "  float gain = 5;",
    "  double offset = 6;",
    "  string name = 7 [(nanopb).max_size = 32];",
    "  bytes payload = 8 [(nanopb).max_size = 64];",
    "  Kind kind = 9;",
    "  repeated int32 samples = 10 [(nanopb).max_count = 16];",
    "  Point origin = 11;",
    "  repeated Point path = 12 [(nanopb).max_count = 8];",
    "  oneof body {",
    "    string text = 13 [(nanopb).max_size = 48];",
    "    uint64 counter = 14;",
    "  }",
    "}",
]

# version -> (pip requirements for the generator's protoc, how it is driven)
_GENERATORS = {
    "0.4.9.2": (_GRPC_TOOLS, "proto"),
    "0.4.5": (_OLD_TOOLS, "proto"),
    "0.3.9.10": (_OLD_TOOLS, "pb"),
}


def _generate_steps(version):
    tools, style = _GENERATORS[version]
    steps = [
        BuildStep("python -m pip install --quiet --target gen-deps " + tools),
        BuildStep("mkdir gen"),
    ]
    if style == "proto":
        # 0.4.x: nanopb_generator.py takes the .proto and runs protoc itself
        # (grpc_tools.protoc is found through PYTHONPATH).
        steps += [
            BuildStep(_write("gen/driver.proto", _DRIVER_PROTO)),
            BuildStep(_write("gen/driver.options", _DRIVER_OPTIONS)),
            BuildStep("python ../generator/nanopb_generator.py driver.proto",
                      cwd="gen", env={"PYTHONPATH": "../gen-deps"}),
        ]
    else:
        # 0.3.9.10: the generator reads a protoc descriptor set (.pb) and
        # imports generator/proto/{nanopb,plugin}_pb2.py, which upstream's
        # Makefile (and proto/__init__.py, through a protoc on PATH) makes
        # with `protoc --python_out=.`; both are done here with
        # grpc_tools.protoc so no protoc binary is needed. Its options-file
        # reader opens the file with mode "rU", which Python 3.11 rejects
        # (ValueError: invalid mode: 'rU'), so there is no driver.options
        # and the same sizes are given inline as (nanopb).max_size /
        # max_count in driver.proto, nanopb's documented alternative.
        steps += [
            BuildStep("python -m grpc_tools.protoc -I. --python_out=. "
                      "nanopb.proto plugin.proto", cwd="generator/proto",
                      env={"PYTHONPATH": "../../gen-deps"}),
            BuildStep(_write("gen/driver.proto", _DRIVER_PROTO_INLINE)),
            BuildStep("python -m grpc_tools.protoc -I. "
                      "-I../generator/proto -o driver.pb driver.proto",
                      cwd="gen", env={"PYTHONPATH": "../gen-deps"}),
            BuildStep("python ../generator/nanopb_generator.py driver.pb",
                      cwd="gen", env={"PYTHONPATH": "../gen-deps"}),
        ]
    return steps


def _nanopb(version, generated=False):
    steps = [
        BuildStep("mkdir -p build-{arch}"),
        BuildStep("{cc} {cflags} -I. -shared "
                  "-o build-{arch}/libprotobuf-nanopb.dll "
                  "pb_common.c pb_decode.c pb_encode.c"),
    ]
    artifacts = [Artifact(path="build-{arch}/libprotobuf-nanopb.dll",
                          component="libprotobuf-nanopb.dll")]
    # The default runtime again, size-optimised: embedded code is commonly
    # built -Os, and against -O2 that changes nearly every function body.
    # No {cflags}, so -Os is the only optimisation flag on the line.
    steps.append(BuildStep("{cc} -Os -I. -shared "
                           "-o build-{arch}/libprotobuf-nanopb-Os.dll "
                           "pb_common.c pb_decode.c pb_encode.c"))
    artifacts.append(Artifact(
        path="build-{arch}/libprotobuf-nanopb-Os.dll",
        component="libprotobuf-nanopb-Os.dll",
        build_flags="-Os, no PB_* defines (upstream default), linked "
                    "directly from pb_common.c, pb_decode.c, pb_encode.c"))
    notes = ("Three source files built as one DLL; upstream CMake needs "
             "protoc even for the runtime, so it is not used. Evidence for "
             "inclusion is naming only.")
    if generated:
        steps += _generate_steps(version)
        tools = _GENERATORS[version][0]
        if _GENERATORS[version][1] == "proto":
            opts = " and driver.options"
        else:
            opts = " with the sizes inline"
        # 0.4.9.2 keeps the text it was imported with.
        how = ("" if version == "0.4.9.2" else
               " (nanopb_generator.py %s, protoc from %s)" % (version, tools))
        for component, defines in _CONFIGS:
            steps.append(BuildStep(
                "{cc} {cflags} -I. -Igen %s -shared "
                "-o build-{arch}/%s pb_common.c pb_decode.c pb_encode.c "
                "gen/driver.pb.c" % (defines, component)))
            artifacts.append(Artifact(
                path="build-{arch}/" + component, component=component,
                build_flags="-O2 (toolchain default) %s, runtime plus "
                            "generated driver.pb.c%s" % (defines, how)))
        notes += (" The -all, -small and -big DLLs add the generated "
                  "driver.pb.c (nanopb_generator.py over a minimal "
                  "driver.proto%s, protoc from %s) and the PB_* defines "
                  "named in their build_flags." % (opts, tools))
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
    "nanopb_0.3.9.10": _nanopb("0.3.9.10", generated=True),
    "nanopb_0.4.5": _nanopb("0.4.5", generated=True),
    "nanopb_0.4.9.2": _nanopb("0.4.9.2", generated=True),
}


# --- Every other combination of the four PB_* defines the tracker names
# (#38), and size-optimised builds of the three shipped sets. The shipped
# recipes above carry three combinations (-all, -small, -big) at -O2 and -Os
# for the default runtime only; these recipes add, for each version, the
# runtime plus the generated driver.pb.c with each of the other twelve
# non-empty subsets of {PB_FIELD_32BIT, PB_NO_ERRMSG, PB_BUFFER_ONLY,
# PB_ENABLE_MALLOC} plus the empty set with the driver, at -O2, and the
# -all, -small and -big sets at -Os. Separate versions ("<tag>-defines") so
# the shipped images are unchanged. A combination whose image turns out
# PicHash-identical to one already committed is not committed (see the
# notes of each version for the measurement).
_DEFINE_NAMES = [("field32", "PB_FIELD_32BIT"), ("noerrmsg", "PB_NO_ERRMSG"),
                 ("bufferonly", "PB_BUFFER_ONLY"), ("malloc", "PB_ENABLE_MALLOC")]
_SHIPPED = {(0, 1, 2, 3), (1, 2), (0, 3)}


def _combinations():
    import itertools
    combos = []
    # The empty set with the driver is not built: its image is
    # PicHash-identical to the committed default build of the same tag and
    # architecture (driver.pb.c is a descriptor table with no function),
    # measured with MinGW and MSVC on all three tags.
    for size in range(1, 5):
        for subset in itertools.combinations(range(4), size):
            if subset in _SHIPPED:
                continue
            tag = "-".join(_DEFINE_NAMES[i][0] for i in subset) or "driver"
            defines = " ".join("-D" + _DEFINE_NAMES[i][1] for i in subset)
            combos.append((tag, defines))
    return combos


DEFINE_COMBINATIONS = _combinations()
SIZE_SETS = [("all", _CONFIGS[0][1]), ("small", _CONFIGS[1][1]),
             ("big", _CONFIGS[2][1])]


def _nanopb_defines(version, keep=None):
    steps = [BuildStep("mkdir -p build-{arch}")] + _generate_steps(version)
    artifacts = []
    tools = _GENERATORS[version][0]
    how = " (nanopb_generator.py %s, protoc from %s)" % (version, tools)
    for tag, defines in DEFINE_COMBINATIONS:
        component = "libprotobuf-nanopb-%s.dll" % tag
        if keep is not None and component not in keep:
            continue
        steps.append(BuildStep(
            "{cc} {cflags} -I. -Igen %s -shared -o build-{arch}/%s "
            "pb_common.c pb_decode.c pb_encode.c gen/driver.pb.c"
            % (defines, component)))
        artifacts.append(Artifact(
            path="build-{arch}/" + component, component=component,
            build_flags="-O2 (toolchain default) %s, runtime plus generated "
                        "driver.pb.c%s" % (defines or "no PB_* defines", how)))
    for tag, defines in SIZE_SETS:
        component = "libprotobuf-nanopb-%s-Os.dll" % tag
        if keep is not None and component not in keep:
            continue
        steps.append(BuildStep(
            "{cc} -Os -I. -Igen %s -shared -o build-{arch}/%s "
            "pb_common.c pb_decode.c pb_encode.c gen/driver.pb.c"
            % (defines, component)))
        artifacts.append(Artifact(
            path="build-{arch}/" + component, component=component,
            build_flags="-Os %s, runtime plus generated driver.pb.c%s"
                        % (defines, how)))
    return Recipe(
        family="nanopb",
        version=version + "-defines",
        upstream="https://github.com/nanopb/nanopb",
        license="Zlib",
        source=Source(git_url="https://github.com/nanopb/nanopb.git",
                      git_ref="nanopb-" + version),
        build=steps,
        artifacts=artifacts,
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 (toolchain default) or -Os, PB_* defines per "
                    "artefact, runtime plus generated driver.pb.c",
        notes="Tag nanopb-%s, the same tree, generator and driver.proto as "
              "the %s recipe. The other combinations of the four build-time "
              "defines the tracker names (PB_FIELD_32BIT, PB_NO_ERRMSG, "
              "PB_BUFFER_ONLY, PB_ENABLE_MALLOC) beside the shipped -all, "
              "-small and -big, plus -Os builds of those three sets; each "
              "artefact's defines are in its build_flags. Nothing patched. "
              "Evidence for inclusion is naming only." % (version, version),
    )


for _v in ("0.3.9.10", "0.4.5", "0.4.9.2"):
    RECIPES["nanopb_%s-defines" % _v] = _nanopb_defines(_v)


# --- Upstream's own CMake (the gap the direct compile above left open) was
# built and measured and is not a recipe on this axis: configured with a
# pinned protoc 21.12 release binary (protoc-21.12-linux-x86_64.zip, sha256
# 3a4c1e5f2516c639d3079b1586e703fc7bcfa2136d58bda24d1d54f949c315e8, which
# 0.4.9.2's CMakeLists needs at configure time) and nanopb_BUILD_GENERATOR=
# OFF, BUILD_SHARED_LIBS=ON and no CMAKE_BUILD_TYPE, upstream's
# protobuf-nanopb target compiles the same three files with the toolchain's
# own -O2 (CMake takes it from CFLAGS when no build type adds flags) and the
# resulting libprotobuf-nanopb.dll is PicHash-identical, every function at
# every size, to the committed direct build at all three tags on both
# architectures, so it would add nothing. The MSVC CMake build differs on
# x64 and is in nanopb_msvc.py.
