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

The reference value is in the helper routines the stubs call - the syscall
number resolution that walks the PEB and parses the export directory - and
those are what an implant actually copies.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_MAIN = (
    'echo #include "syscalls.h" > main.c && '
    'echo int main(void){ NtClose(0); return 0; } >> main.c')


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
            BuildStep("{masm} /c /Fo syscallsstubs.obj syscallsstubs.asm"),
            BuildStep(_MAIN),
            BuildStep("cl /nologo /c /O2 /I. main.c syscalls.c"),
            BuildStep("link /nologo /OUT:syswhispers.exe main.obj syscalls.obj "
                      "syscallsstubs.obj ntdll.lib kernel32.lib "
                      "/NODEFAULTLIB:libcmt.lib msvcrt.lib"),
        ],
        artifacts=[Artifact(path="syswhispers.exe", component="syswhispers.exe")],
        # MASM x64 only; upstream states the generator targets x64.
        toolchains=["msvc_x64"],
        build_flags="/O2, generated with --preset common",
        notes="Built from the generator's own output; the reference value is "
              "in the syscall-resolution helpers rather than the stubs.",
    ),
}
