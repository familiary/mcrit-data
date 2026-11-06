"""Generate and compile one SysWhispers2 or SysWhispers3 option point.

Unlike SysWhispers4, these two need no derived exerciser: their resolver is
declared ``EXTERN_C`` with external linkage, so ``SW2_PopulateSyscallList``,
``SW2_GetSyscallNumber``, ``SW2_HashSyscall`` and their v3 equivalents land
in a DLL built from the generated ``.c`` alone, and MinGW's COFF symbol
table names them. The per-function stubs are a separate matter and are
discussed in the recipes.

Three things the command line has to supply, each found by building:

**``-masm=intel``** for SysWhispers3. Its MinGW output is GCC inline
assembly written in Intel syntax with no ``.intel_syntax`` directive of its
own, so without the flag GAS reads it as AT&T and rejects it with "operand
size mismatch for `mov'" on every stub. Upstream's own README passes it.

**``-DRANDSYSCALL``** for SysWhispers2's randomised stubs.
``SW2_GetRandomSyscallAddress`` is guarded by ``#ifdef RANDSYSCALL`` in the
generated ``.c`` while ``SStubs.rnd.*`` calls it unconditionally, so the
randomised flavour does not link without it - "undefined reference to
`SW2_GetRandomSyscallAddress'".

**A stub file chosen by name.** SysWhispers2 emits all twelve combinations of
{std, rnd} x {x86, x64} x {masm, nasm, gas} from one run, so the recipe names
the one it wants rather than the generator being told.
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# mingw-w64's ld makes a DLL that is not byte-reproducible, in two ways that
# both had to be found by building the same source three times and diffing:
#
#   * It stamps the PE TimeDateStamp, like MSVC does without /Brepro.
#   * It picks a pseudo-random ImageBase for a DLL ("auto image base"), so
#     every absolute address in the image moves. Two runs of one source
#     differed in 1117 bytes, and all but two of them were the high half of
#     a 64-bit address: 0x00024A2B0000 against 0x00022F690000.
#
# PicHashes are position-independent and did not move, which is why the
# measurements were stable either way - but provenance records a sha256 per
# artefact, and an artefact whose digest changes on every rebuild cannot be
# traced to the source it came from. With the three flags below, three runs
# produce one digest.
#
# 0x180000000 is the conventional x64 DLL base and 0x10000000 the x86 one;
# the value only has to be fixed, not meaningful.
def repro_flags(cc):
    base = "0x10000000" if "i686" in cc else "0x180000000"
    return ("-Wl,--no-insert-timestamp -Wl,--disable-auto-image-base "
            "-Wl,--image-base,%s" % base)



def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cc", required=True)
    p.add_argument("--opt", default="-O2")
    p.add_argument("--out", required=True, help="DLL path, relative to cwd")
    p.add_argument("--seed", default="20260101")
    p.add_argument("--stub", default="",
                   help="glob matching the generated stub file to assemble")
    p.add_argument("--cflags", default="", help="extra compiler flags")
    p.add_argument("gen", nargs=argparse.REMAINDER)
    a = p.parse_args()
    gen_args = a.gen[1:] if a.gen and a.gen[0] == "--" else a.gen

    d = os.path.dirname(a.out) or "."
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)

    env = dict(os.environ, SW_SEED=a.seed)
    cmd = ("%s %s syswhispers.py %s -o %s/S"
           % (sys.executable, os.path.join(HERE, "syswhispers_gen.py"),
              " ".join(gen_args), d))
    if subprocess.run(cmd, shell=True, env=env).returncode:
        raise SystemExit("generator failed: " + cmd)

    srcs = "%s/S.c" % d
    if a.stub:
        # Matched by glob rather than by exact name: SysWhispers2 spells the
        # stub files "SStubs.std.x64.s" on some invocations and
        # "S_Stubs.std.x64.s" on others from the same commit, and the recipe
        # should name the flavour it wants rather than track that.
        found = sorted(glob.glob(os.path.join(d, a.stub)))
        if len(found) != 1:
            raise SystemExit(
                "%r matched %d files in %s; the generator wrote %s"
                % (a.stub, len(found), d, sorted(os.listdir(d))))
        srcs += " " + found[0]

    link = ("%s %s -shared -o %s %s -I%s %s %s"
            % (a.cc, a.opt, a.out, srcs, d, a.cflags, repro_flags(a.cc)))
    if subprocess.run(link, shell=True).returncode:
        raise SystemExit("compile failed: " + link)
    print("built %s (%d bytes)" % (a.out, os.path.getsize(a.out)))


main()
