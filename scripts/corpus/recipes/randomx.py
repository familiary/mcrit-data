"""RandomX - tevador's proof-of-work, as a DLL and as a shared object.

Backlog issue #18. XMRig vendors RandomX in src/crypto/randomx with no module
identity of its own, so a Monero reference miner, or any other miner that
embeds RandomX, would be answered "XMRig" by a corpus that has only XMRig
(data/XMRig, issue #8). This is the family that stops that.

Versions. v1.2.1 (commit 102f8acf), v1.2.2 (6c4340ba), v1.2.3 (12f2c2ff),
v2.0 (e0db3c4a) and v2.0.1 (aaafe713) are built (MSVC: randomx_msvc.py, below). The
three tags added after the first two are near-duplicates of them, measured on the PicHashes of the
functions of ten instructions or more: v1.2.1, v1.2.2 and v1.2.3 share all of
them on Linux x64 (188), MinGW x64 (172) and MinGW x86 (140), and 321 of 322 on
Linux x86; v2.0 and v2.0.1 share all of them on all four axes (198, 353, 181,
145). The function names and the kept and removed counts are the same too. Across the two
lines, the 1.2.x hashes found in 2.0.x are 77% (Linux x64), 6% (Linux x86),
72% (MinGW x64) and 81% (MinGW x86). So there are two bodies of code on these
axes, not five. Where the shared object is byte-identical (same sha256)
to an existing one, it is not filed again, because validate refuses a
duplicate sample in a family and nothing would be gained (donut_1.1 does the
same for v1.0): on Linux x64 v1.2.2, v1.2.3 and v2.0 (identical to v1.2.1,
v1.2.1 and v2.0.1), and on Linux x86 v1.2.3 (identical to v1.2.2). What is
filed: Linux x86 of v1.2.2 (321 of 322 PicHashes of v1.2.1's; the one
difference is the whole addition) and of v2.0, and MinGW x86 and x64 of all
three, which differ in bytes from the existing ones (the cause was not
investigated) with the same functions, so a
sample that names one of those releases finds its own label. They add no
function that v1.2.1 or v2.0.1 does not already have.

MSVC (randomx_msvc.py), built on the windows runner against the wide-stdio
glue baseline, is filed for all three tags on x86 and x64: none of the six
DLLs is byte-identical to a filed one, so validate accepts them, but the code
is the same. Kept and removed are 848 and 378 on x64 and 862 and 369 on x86
for v1.2.1, v1.2.2 and v1.2.3, and 881 and 378 on x64 and 886 and 369 on x86
for v2.0 and v2.0.1. At ten instructions or more v1.2.1, v1.2.2 and v1.2.3
share all of their PicHashes (254 on x64, 243 on x86) and v2.0 and v2.0.1
share all of theirs (260, 245); the 1.2.x hashes found in 2.0.x are 195 of
254 (77%) on x64 and 201 of 243 (83%) on x86. So the three new MSVC images
are near-duplicates of the two built before them and add no PicHash. Upstream tevador/RandomX
rather than XMRig's vendored tree, which the issue offers as the alternative:
XMRig's copy is a fork (it has no argon2_core.c or assembly generator of its
own, and adds RISC-V sources) and is already in
data/XMRig as part of the miner, where it is filed under XMRig as the stock
build ships it. Building it a second time as this family would have put the
same bytes under two names. Measured the other way round, the overlap is small: of XMRig's 2466 functions
of ten instructions or more on Linux x64, 22 share a PicHash with RandomX
(1.2.1 and 2.0.1 together) - seven libstdc++ vector instantiations, five
RandomX functions under the same name (BytecodeMachine::executeInstruction,
initDataset, Blake2Generator's constructor and two SuperscalarInstructionInfo
ones) and the rest the same function under XMRig's `rx_blake2b_*`,
`xmrig_ar2_*` and `hashAes1Rx4<0>` spellings against RandomX's `randomx_*` and
`hashAes1Rx4<false>`. `validate --deep` flags a PicHash only when three or
more families carry it, so a pair like this is not reported; with the open
argon2 branch's data present it reported `xor_block`, `copy_block`, `rotr64`
and `blake2b_*` under RandomX, XMRig and argon2 together. The XMRig side of
those that are Argon2's own, by PicHash against data/argon2 and data/BLAKE2,
is now removed by exact name (xmrig.py, _stack_vendored.py), which clears all
but `blake2b_increment_counter` (BLAKE2, RandomX, argon2) and `rotr64` (those
and OpenSSL, XMRig's MSVC image); RandomX's own copies are left in here.

What is in it. Argon2d and Blake2b are RandomX's own copies of the PHC
reference code (src/argon2_core.c, argon2_ref.c, blake2/blake2b.c) and stay
filed here, as the issue directs, not as separate families. On x64 the JIT
(jit_compiler_x86.cpp plus the hand-written jit_compiler_x86_static.S, or
.asm under MSVC) is compiled in; on x86 CMake adds it only when the pointer
size is 8, so the 32-bit artefacts are the interpreter only and the two
architectures are different code, not the same code twice (Linux 494 against
498 functions, MinGW 464 against 417, MSVC 848 against 862 for 1.2.1).
The JIT emitters are ordinary C++ and disassemble normally; only the bytes
they emit at run time are not here.

How it is built. Upstream's CMake builds a static librandomx and three test
programs; only the library is built (`--target randomx`) and it is linked
whole into a DLL or shared object, the way data/cryptopp is, because SMDA
cannot read an archive. On Linux that is `-fvisibility=hidden` so the
library's own calls do not go through .plt stubs (README, "Build
-fvisibility=hidden"). On MinGW the DLL is linked with `-shared-libgcc`.

Instruction set. `-DARCH=default`, upstream's own default, which is the one
that does not pass -march=native. On x86-64 that adds -maes to everything
and -mssse3 and -mavx2 to the two Argon2 units (argon2_ssse3.c,
argon2_avx2.c; /arch:AVX2 on the second under MSVC); which of them runs is
decided at run time from CPUID, so the baseline of the other code is plain
x86-64 with SSE2 and AES intrinsics. On x86 no -maes is set and nothing
else is added.

Axes. MinGW x86 and x64, Linux ELF x86 and x64 (glibc) and MSVC x86 and x64,
all six, each measured to share almost nothing with the others: at ten
instructions or more, RandomX 1.2.1 x64 shares 0 of 188/172 PicHashes between
GCC and MinGW, 0 of 188/254 between GCC and MSVC and 1 of 172/254 between
MinGW and MSVC; x86 shares 5, 0 and 0 (2.0.1: 3, 2 and 3 on x64, 4, 0 and 0
on x86). Calling-convention, PIC and compiler differences leave nothing for
one axis to stand in for another.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_UPSTREAM = "https://github.com/tevador/RandomX"

# CMake's Release is -O3 -DNDEBUG and does not strip; -DARCH=default is
# upstream's own default and the one that does not pass -march=native.
_CONFIG = "-DCMAKE_BUILD_TYPE=Release -DARCH=default"
_HIDDEN = " -DCMAKE_C_FLAGS=-fvisibility=hidden -DCMAKE_CXX_FLAGS=-fvisibility=hidden"

_WHOLE = ("-Wl,--whole-archive build-{arch}/librandomx.a "
          "-Wl,--no-whole-archive")


def _randomx(version, tag, linux, archs=None):
    if linux:
        configure = "cmake -S . -B build-{arch} " + _CONFIG + _HIDDEN
        link = ("{cxx} {archflag} -shared -o build-{arch}/librandomx.so "
                + _WHOLE)
        artifact = Artifact(path="build-{arch}/librandomx.so",
                            component="librandomx.so")
        toolchains = archs or ["linux_x86", "linux_x64"]
    else:
        configure = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
                     "-DCMAKE_SYSTEM_PROCESSOR={platform} "
                     "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx} "
                     "-DCMAKE_RC_COMPILER={windres} "
                     "-DCMAKE_FIND_ROOT_PATH=/usr/{host} " + _CONFIG)
        link = ("{cxx} -shared -o build-{arch}/randomx.dll " + _WHOLE
                + " -shared-libgcc")
        artifact = Artifact(path="build-{arch}/randomx.dll",
                            component="randomx.dll")
        toolchains = ["mingw_x86", "mingw_x64"]
    return Recipe(
        family="RandomX",
        version=version,
        upstream=_UPSTREAM,
        license="BSD-3-Clause",
        source=Source(git_url=_UPSTREAM + ".git", git_ref=tag),
        build=[
            BuildStep(configure, env={"CFLAGS": "", "CXXFLAGS": ""}),
            BuildStep("cmake --build build-{arch} --target randomx -j$(nproc)"),
            BuildStep(link),
        ],
        artifacts=[artifact],
        toolchains=toolchains,
        build_flags="-O3 -DNDEBUG (CMake Release)"
                    + (", -fvisibility=hidden" if linux else "")
                    + ", ARCH=default (-maes, and -mssse3 / -mavx2 on the "
                      "two Argon2 units, x86-64 only)",
        notes="Upstream tevador/RandomX at the tag, built with its own CMake "
              "(library target only) and linked whole into a shared object. "
              "x64 includes the JIT; x86 is the interpreter. Argon2d and "
              "Blake2b are RandomX's own copies and are filed here. "
              "ARCH=default, so no -march=native; AES-NI, SSSE3 and AVX2 are "
              "selected at run time.",
    )


RECIPES = {
    "RandomX_1.2.1": _randomx("1.2.1", "v1.2.1", linux=False),
    "RandomX_1.2.1_linux": _randomx("1.2.1", "v1.2.1", linux=True),
    "RandomX_1.2.2": _randomx("1.2.2", "v1.2.2", linux=False),
    # Linux x86 only: the x64 shared object of v1.2.2, v1.2.3 and v2.0 is
    # byte-identical (same sha256) to v1.2.1's, v1.2.1's and v2.0.1's, and
    # validate refuses a sample filed twice in a family. v1.2.3 x86 is
    # byte-identical to v1.2.2's, so v1.2.3 has no Linux recipe.
    "RandomX_1.2.2_linux": _randomx("1.2.2", "v1.2.2", linux=True,
                                    archs=["linux_x86"]),
    "RandomX_1.2.3": _randomx("1.2.3", "v1.2.3", linux=False),
    "RandomX_2.0": _randomx("2.0", "v2.0", linux=False),
    "RandomX_2.0_linux": _randomx("2.0", "v2.0", linux=True,
                                  archs=["linux_x86"]),
    "RandomX_2.0.1": _randomx("2.0.1", "v2.0.1", linux=False),
    "RandomX_2.0.1_linux": _randomx("2.0.1", "v2.0.1", linux=True),
}
