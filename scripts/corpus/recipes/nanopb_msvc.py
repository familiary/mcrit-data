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

MEASUREMENTS_PLACEHOLDER
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


def _nanopb_msvc(version):
    return Recipe(
        family="nanopb",
        version=version,
        upstream="https://github.com/nanopb/nanopb",
        license="Zlib",
        source=Source(git_url="https://github.com/nanopb/nanopb.git",
                      git_ref="nanopb-" + version),
        build=[
            BuildStep("if not exist build-{arch} mkdir build-{arch}"),
            _def_step(version),
            BuildStep(_COMPILE),
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/protobuf-nanopb.dll",
                            component="protobuf-nanopb.dll",
                            pdb="build-{arch}/protobuf-nanopb.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi, no PB_* defines (upstream default), cl "
                    "directly over pb_common.c pb_decode.c pb_encode.c; "
                    "/DLL via .def, /DEBUG /Brepro /INCREMENTAL:NO "
                    "/OPT:NOREF /OPT:NOICF at link",
        notes="Same tag as the MinGW recipe, same three files. Built against "
              "the DLL runtime so the MSVC C runtime stays attributed to "
              "data/MSVC. Exports come from a .def written outside the "
              "source tree. Evidence for inclusion is naming only.",
    )


RECIPES = {
    "nanopb_0.3.9.10_msvc": _nanopb_msvc("0.3.9.10"),
    "nanopb_0.4.5_msvc": _nanopb_msvc("0.4.5"),
    "nanopb_0.4.9.2_msvc": _nanopb_msvc("0.4.9.2"),
}
