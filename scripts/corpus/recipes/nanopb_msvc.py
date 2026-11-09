"""nanopb built with MSVC, beside the MinGW builds of the same tags.

nanopb is the C implementation of the protobuf wire format that firmware and
embedded code use, and data/nanopb held MinGW artefacts only. The two
compilers lay out the same source differently, so a sample built with cl had
no exact-match reference here (the Jansson pilot, jansson_msvc.py, measured
the MinGW/MSVC PicHash overlap of a vendored C library at 0 to 1 functions).
This is that axis for nanopb.

Same three pins as nanopb.py (tags nanopb-0.3.9.10, nanopb-0.4.5 and
nanopb-0.4.9.2), so each MinGW/MSVC pair differs by compiler only. A separate
registry entry, for the reason given in sqlite3_msvc.py: one Recipe has one
build list and these steps are cmd.exe.

Build. As in nanopb.py, upstream's CMake is not used: its shared target needs
a protoc at configure time whether or not the generator is built. cl compiles
pb_common.c, pb_decode.c and pb_encode.c directly into one DLL, with no PB_*
defines (upstream's default configuration) and nothing in the upstream tree
patched. /O2 is cl's own optimisation default for release and the counterpart
of MinGW's -O2; /Zi gives a PDB so non-exported functions are named. At link:
/DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF, with no /GL and no
/LTCG, and /MD so the C runtime is imported and stays attributed to data/MSVC
(see README.md, "The MSVC half").

Exports. MinGW's ld exports every global symbol, whereas link.exe exports
nothing without a .def, so one is written beside the source tree
(`..\\nanopb-<arch>.def`, outside the checkout) listing the global functions
of the default no-define build of that version. That list was taken from `nm`
over a gcc -O2 compile of the three files at each tag, so it is the same API
the MinGW DLL exports: 34 names at 0.3.9.10, 35 at 0.4.5 and 36 at 0.4.9.2
(pb_release exists only from 0.4.9.2 without PB_ENABLE_MALLOC). The DLL is
named protobuf-nanopb.dll, which is what the upstream CMake target would
write under MSVC (no `lib` prefix), where MinGW writes libprotobuf-nanopb.dll.

Limitation, as in nanopb.py: the option set is not varied and embedded code
is often built size-optimised (-Os / /O1 /Os), which changes the code far
more than any of the PB_* options, so a real nanopb sample is more likely to
match by MinHash than by PicHash.

Read back from the runner (windows-2022, MSVC 19.44, v143), not assumed: the
cl line the build log prints is the one in _COMPILE; link.exe took the .def
and wrote protobuf-nanopb.dll (36,864 bytes at 0.4.9.2 x64) with a 545 KB PDB,
and neither tool printed a warning. No /GL is passed and no /LTCG is in play.

Counted on the runner, kept + removed = image total (removed is the
baseline's compiler-runtime filter, "dropped N compiler runtime functions"):

                    kept    removed    image
    0.3.9.10 x86      83      125       208
    0.3.9.10 x64      80      129       209
    0.4.5    x86      79      125       204
    0.4.5    x64      77      129       206
    0.4.9.2  x86      79      125       204
    0.4.9.2  x64      78      129       207

What the baseline removed is MSVC runtime glue (DllMain, _DllMainCRTStartup,
the __scrt_* startup functions, __castguard_*, __security_*, __report_*,
SEH handlers, kernel32 import thunks), compiled into the DLL even under /MD.

What survives, by name and PicHash: no unnamed function and no glue in any
of the six artefacts. Every kept function is either an exported pb_* routine
or a nanopb static (buf_read, buf_write, decode_field, decode_static_field,
encode_array, safe_read_bool and so on, 17 to 19 per artefact). At x86 the
PDB also labels three interior entry points of large functions
(decode_static_field$+0x1fd at 0.3.9.10, decode_static_field$+0x249 at 0.4.5,
encode_basic_field$+0x13d at 0.3.9.10), which are nanopb code and not glue.
At 0.4.9.2 x64 the statics are advance_iterator 16606061034253823674,
load_descriptor_values 9361589287834584332, buf_read 7805911138840976995,
decode_basic_field 2819844878615162245, decode_callback_field
15500451049100105837, decode_extension 8778844127214404292, decode_field
3816378724393654135, decode_pointer_field 2407915914967506153 (7
instructions), decode_static_field 9276057699374094180,
default_extension_decoder 11079785349539649306, read_raw_value
12392993382980208415, buf_write 9946167767070953582,
default_extension_encoder 2432676270308423099, encode_array
12456943543875295928, encode_basic_field 10583906757704221710,
encode_callback_field 9275046920793274101, encode_extension_field
15754941812377411732, encode_field 13065938681143563832, safe_read_bool
9149913116463287761.

validate --deep over nanopb plus cJSON, lz4, q3vm, aPLib and protobuf: 0
problems; 3 cross-family PicHashes at 10+ instructions, all carrying no
symbol, 0 leakage.

MinGW against MSVC, PicHash overlap over functions of 10+ instructions (same
tag, same arch):

                  mingw / msvc     shared
    0.3.9.10 x86     57 / 72         0
    0.3.9.10 x64     55 / 71         0
    0.4.5    x86     42 / 69         0
    0.4.5    x64     39 / 67         0
    0.4.9.2  x86     43 / 68         0
    0.4.9.2  x64     40 / 67         0

The pair shares no exact function body at all, which is the case for holding
the MSVC axis. The MSVC side has more functions of 10+ instructions than the
MinGW side at every tag.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Global functions of the default no-define build, from nm over gcc -O2
# objects at each tag (see the docstring).
_COMMON = (
    "pb_close_string_substream pb_decode pb_decode_bool pb_decode_fixed32 "
    "pb_decode_fixed64 pb_decode_svarint pb_decode_tag pb_decode_varint "
    "pb_decode_varint32 pb_encode pb_encode_fixed32 pb_encode_fixed64 "
    "pb_encode_string pb_encode_submessage pb_encode_svarint pb_encode_tag "
    "pb_encode_tag_for_field pb_encode_varint pb_field_iter_begin "
    "pb_field_iter_find pb_field_iter_next pb_get_encoded_size "
    "pb_istream_from_buffer pb_make_string_substream pb_ostream_from_buffer "
    "pb_read pb_skip_field pb_write")

_EXPORTS = {
    "0.3.9.10": _COMMON + " pb_decode_delimited pb_decode_delimited_noinit "
                          "pb_decode_noinit pb_decode_nullterminated "
                          "pb_encode_delimited pb_encode_nullterminated",
    "0.4.5": _COMMON + " pb_decode_ex pb_default_field_callback "
                       "pb_encode_ex pb_field_iter_begin_const "
                       "pb_field_iter_begin_extension "
                       "pb_field_iter_begin_extension_const "
                       "pb_field_iter_find_extension",
}
_EXPORTS["0.4.9.2"] = _EXPORTS["0.4.5"] + " pb_release"


def _def_step(version):
    # (echo EXPORTS& echo a& echo b ...) > file : no space before '&', or it
    # would end up in the name.
    names = ["EXPORTS"] + _EXPORTS[version].split()
    return BuildStep("(" + "& ".join("echo " + n for n in names)
                     + ") > ..\\nanopb-{arch}.def")


_COMPILE = ('cl /nologo /LD /O2 /MD /Zi /I. /Fobuild-{arch}\\ '
            '/Fdbuild-{arch}\\protobuf-nanopb.pdb '
            '/Febuild-{arch}\\protobuf-nanopb.dll '
            'pb_common.c pb_decode.c pb_encode.c '
            '/link /DEF:..\\nanopb-{arch}.def /DEBUG /Brepro /INCREMENTAL:NO '
            '/OPT:NOREF /OPT:NOICF '
            '/PDB:build-{arch}\\protobuf-nanopb.pdb')


# --- Generated-code configurations (backlog #38), 0.4.9.2 only. The same
# artefacts as nanopb.py adds on the MinGW side: runtime plus the generated
# driver.pb.c with the PB_* defines the tracker names. The driver .proto is
# written by the build; single quotes only, for cmd.exe.
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


_CONFIGS = [
    ("all", "protobuf-nanopb-all",
     "/DPB_FIELD_32BIT /DPB_NO_ERRMSG /DPB_BUFFER_ONLY /DPB_ENABLE_MALLOC"),
    ("small", "protobuf-nanopb-small", "/DPB_NO_ERRMSG /DPB_BUFFER_ONLY"),
    ("big", "protobuf-nanopb-big", "/DPB_FIELD_32BIT /DPB_ENABLE_MALLOC"),
]

_GRPC_TOOLS = "grpcio-tools==1.85.1"


def _def_from_objects(directory):
    # Defined External functions of every object in the directory, written to
    # a .def; the x86 cdecl underscore is stripped. Same rule as cmp_msvc.py.
    return BuildStep(
        'python -c "'
        "import subprocess,glob;"
        "o=''.join([subprocess.check_output(['dumpbin','/SYMBOLS',f]).decode() "
        "for f in sorted(glob.glob('%s/*.obj'))]);" % directory +
        "l=[t[t.index('|')+1] for t in map(str.split,o.splitlines()) "
        "if '|' in t and '()' in t and 'External' in t "
        "and any([w.startswith('SECT') for w in t])];"
        "p='{arch}'=='x86';"
        "n=sorted(set([s[1:] if p and s.startswith('_') else s for s in l]));"
        "assert n,'no exports found';"
        "open('%s/nanopb.def','w').write('EXPORTS\\n'+'\\n'.join(n)+'\\n');" % directory +
        "print(len(n),'exports')"
        '"')


def _config_steps(tag, dll, defines):
    d = "cfg-%s-{arch}" % tag
    return [
        BuildStep("if not exist %s mkdir %s" % (d, d)),
        BuildStep("cl /nologo /c /O2 /MD /Zi /I. /Igen %s /Fo%s\\ /Fd%s\\%s.pdb "
                  "pb_common.c pb_decode.c pb_encode.c gen\\driver.pb.c"
                  % (defines, d, d, dll)),
        _def_from_objects(d),
        BuildStep("link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO "
                  "/OPT:NOREF /OPT:NOICF /DEF:%s\\nanopb.def /PDB:%s\\%s.pdb "
                  "/OUT:%s\\%s.dll %s\\*.obj" % (d, d, dll, d, dll, d)),
    ]


def _nanopb_msvc(version, generated=False):
    steps = [
        BuildStep("if not exist build-{arch} mkdir build-{arch}"),
        _def_step(version),
        BuildStep(_COMPILE),
        BuildStep("dir build-{arch}", allow_failure=True),
    ]
    artifacts = [Artifact(path="build-{arch}/protobuf-nanopb.dll",
                          component="protobuf-nanopb.dll",
                          pdb="build-{arch}/protobuf-nanopb.pdb")]
    notes = ("Same tag as the MinGW recipe, same three files. Built against "
             "the DLL runtime so the MSVC C runtime stays attributed to "
             "data/MSVC. Exports come from a .def written outside the "
             "source tree. Evidence for inclusion is naming only.")
    if generated:
        steps = steps[:-1] + [
            BuildStep("python -m pip install --quiet --target gen-deps "
                      + _GRPC_TOOLS),
            BuildStep("if not exist gen mkdir gen"),
            BuildStep(_write("gen/driver.proto", _DRIVER_PROTO)),
            BuildStep(_write("gen/driver.options", _DRIVER_OPTIONS)),
            BuildStep("python ..\\generator\\nanopb_generator.py driver.proto",
                      cwd="gen", env={"PYTHONPATH": "..\\gen-deps"}),
        ]
        for tag, dll, defines in _CONFIGS:
            steps += _config_steps(tag, dll, defines)
            artifacts.append(Artifact(
                path="cfg-%s-{arch}/%s.dll" % (tag, dll),
                component=dll + ".dll",
                pdb="cfg-%s-{arch}/%s.pdb" % (tag, dll),
                build_flags="/O2 /MD /Zi %s, runtime plus generated "
                            "driver.pb.c; /DEBUG /Brepro /INCREMENTAL:NO "
                            "/OPT:NOREF /OPT:NOICF at link, exports from a "
                            "/DEF generated from the objects" % defines))
        steps.append(BuildStep("dir", allow_failure=True))
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
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi, no PB_* defines (upstream default), cl "
                    "directly over pb_common.c pb_decode.c pb_encode.c; "
                    "/DLL via .def, /DEBUG /Brepro /INCREMENTAL:NO "
                    "/OPT:NOREF /OPT:NOICF at link",
        notes=notes,
    )


RECIPES = {
    "nanopb_0.3.9.10_msvc": _nanopb_msvc("0.3.9.10"),
    "nanopb_0.4.5_msvc": _nanopb_msvc("0.4.5"),
    "nanopb_0.4.9.2_msvc": _nanopb_msvc("0.4.9.2", generated=True),
}
