"""jitasm built for Linux, from the same exerciser as the PE builds.

jitasm's README lists Linux, FreeBSD and Mac beside Windows - jitasm.h
allocates executable memory with mmap where it does not have VirtualAlloc - so
an ELF reference describes a consumer the project supports, and the sample
chain that motivates the family is irrelevant to it. It is built because it is
cheap and because it is a different artefact: PicHash overlap with the MinGW
build at the ten-instruction floor is zero on x64 and 4 of 863 on x86, and
with the MSVC build zero on both, since the System V ABI and 32-bit PIC change
every body.

The exerciser is the one the PE builds use; its <windows.h> include is
guarded on _WIN32, which is the only reason that file knows about this
platform. See jitasm.py for the -O measurement, the exerciser and what it
costs.

Built as a shared object with -fPIC and -fvisibility=hidden, as every ELF
artefact in this corpus is (README, "The Linux half"): a -shared object links
glibc and libstdc++ dynamically so none of their bodies enter the image, and
hidden visibility keeps calls inside the object direct instead of through
PLT stubs. -O2, as the PE builds.

Counts, kept + removed = total: x86 1654 + 5 = 1659, x64 2045 + 6 = 2051, of
which 1374 and 1734 are ten instructions or more. 1576 of 1654 (x86) and 1963
of 2045 (x64) kept functions are named; the rest are PLT stubs for libstdc++
and libc. 196 (x86) and 265 (x64) functions are the exerciser's scaffolding
and upstream's sixty test cases, recognisable by name.

Glue survivors, by name and PicHash, on x86 only, as the README describes for
every 32-bit ELF artefact: _init (5966282171574051400), register_tm_clones
(4039128032752531076), deregister_tm_clones (2739738298669719287),
__do_global_dtors_aux (16899601281644636652), __stack_chk_fail_local
(14997637065571920018) and __x86.get_pc_thunk.bp, .cx and .si
(8978313489863221434, 8547562632060595966, 11029392869810893897). Their
PicHash differs between images because the GOT delta is baked in, which is why
the filter, matching symbol and PicHash, leaves them.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_BUILD = ("{cxx} {archflag} -O2 -fno-operator-names -mmmx -msse -msse2 "
          "-shared -fPIC -fvisibility=hidden -I. "
          "-o libjitasm.so {repo}/scripts/corpus/exercisers/jitasm.cpp")

RECIPES = {
    "jitasm_2018-11-24_linux": Recipe(
        family="jitasm",
        version="2018-11-24",
        upstream="https://github.com/hikaru-i/jitasm",
        license="New BSD (three-clause), Copyright (c) 2009-2011 Hikaru "
                "Inoue, Akihiro Yamasaki",
        source=Source(git_url="https://github.com/hikaru-i/jitasm.git",
                      git_ref="7cb9d72982c793374c49b804bec842deb1506d92"),
        build=[BuildStep(_BUILD)],
        artifacts=[Artifact(path="libjitasm.so", component="libjitasm.so")],
        toolchains=["linux_x86", "linux_x64"],
        build_flags="-O2 -fno-operator-names -mmmx -msse -msse2 -shared "
                    "-fPIC -fvisibility=hidden",
        notes="The ELF build of the same commit and the same exerciser as "
              "the PE artefacts of this family. jitasm supports Linux, so "
              "this describes a supported consumer; it is not evidence for "
              "the Windows sample chain. Measured: 1654 functions kept of "
              "1659 on x86 (5 removed), 2045 of 2051 on x64 (6), 1374 and "
              "1734 of them ten instructions or more. PicHash overlap with "
              "the MinGW build at the ten-instruction floor is 4 of 863 on "
              "x86 and zero on x64, and zero with the MSVC build. The x86 "
              "image keeps the 32-bit PIC link glue the filter cannot match "
              "by PicHash (_init, the tm_clones pair, "
              "__do_global_dtors_aux, __stack_chk_fail_local and the "
              "get_pc_thunk helpers).",
    ),
}
