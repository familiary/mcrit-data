"""SysWhispers (mcrit-data issue #9) - the v1 generator, MSVC only.

The issue asks for "SysWhisper versions and derivates". Of the four, v1 is
the one worth covering and the one that needs Windows: its generated stubs
are around a hundred instructions each, carrying real PEB version dispatch,
while SysWhispers2 and 3 emit 2- to 15-instruction stubs that differ only by
one immediate and would form a large, low-value cluster. v1's output is MASM
and is rejected by both nasm and GAS, so it needs ml/ml64.

SysWhispers2_x86 is deliberately absent: it is pre-generated MASM with no
LICENSE file of any kind, which is a maintainer decision rather than a
technical one.

Each v1 stub resolves its own syscall number inline: it loads the PEB from
gs:[60h] and walks major version, minor version and build number down a chain
of comparisons before issuing the syscall. That dispatch ladder is the
recognisable part, and it is what an implant carries when it copies this
generator's output verbatim.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# The generator writes <basename>.asm and <basename>.h and nothing else, so
# the stubs are the whole of the compiled output. Exporting every PROC gives
# SMDA a named entry point for each one without a PDB, and it is also what
# keeps them in the image: nothing calls them, and /OPT:NOREF alone would
# leave them anonymous. The .def is derived from the generated assembly
# rather than hardcoded, so it follows whichever preset was generated.
_EXPORTS = (
    'python -c "'
    "import re; "
    "names = re.findall(r'^(\\w+) PROC', open('syscalls.asm').read(), re.M); "
    "open('syscalls.def','w').write('EXPORTS\\n' + '\\n'.join(names) + '\\n')"
    '"')

# /NOENTRY with /NODEFAULTLIB keeps the C runtime out entirely: the stubs are
# self-contained, and a DLL holding only them is reference data with nothing
# to mis-attribute. It is not loadable, which does not matter here.
_LINK = ('link /nologo /DLL /NOENTRY /NODEFAULTLIB /OPT:NOREF '
         '/DEF:syscalls.def /OUT:syscalls.dll syscalls.obj')


RECIPES = {
    "SysWhispers_2021-07-06": Recipe(
        family="SysWhispers",
        version="2021-07-06",
        upstream="https://github.com/jthuraisamy/SysWhispers",
        license="Apache-2.0",
        source=Source(git_url="https://github.com/jthuraisamy/SysWhispers.git",
                      git_ref="3960669f184388ea3cbd33ee5c9e345f2f702f08"),
        build=[
            # --preset all crashes on entries present in syscall_numbers.json
            # but missing from prototypes.json; common is complete and is what
            # the project's own documentation demonstrates.
            BuildStep("python -m pip install --quiet jmespath"),
            BuildStep("python syswhispers.py --preset common -o syscalls"),
            BuildStep("{masm} /c /Fo syscalls.obj syscalls.asm"),
            BuildStep(_EXPORTS),
            BuildStep(_LINK),
        ],
        artifacts=[Artifact(path="syscalls.dll", component="syscalls.dll")],
        # MASM x64 only; upstream states the generator targets x64.
        toolchains=["msvc_x64"],
        # Nothing here goes through a C compiler, so no optimization setting
        # applies; what varies between users of this generator is the preset.
        build_flags="assembled with ml64, generated with --preset common",
        # /NODEFAULTLIB means there is no runtime in the image to drop.
        drop_crt_glue=False,
        notes="Built from the generator's own output. The DLL holds the 29 "
              "generated stubs and nothing else - no C runtime, no entry "
              "point - and exports them so each carries its name.",
    ),
}
