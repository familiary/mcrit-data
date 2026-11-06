"""Generate, derive an exerciser for, and compile one SysWhispers4 variant.

One recipe covers fifty option combinations, so the per-variant sequence -
run the generator, derive the exerciser from the header it wrote, compile the
pair into a DLL - lives here rather than as four shell steps repeated fifty
times in the recipe. The recipe stays a table of variants.

Three details are not obvious and are load-bearing.

**Each variant builds in its own directory.** Every invocation writes the same
``SW.c``/``SW.h``/``SW_stubs.c`` names, so variants sharing a directory would
overwrite each other's source between the generate and the compile.

**``--encrypt-ssn`` needs one translation unit.** With that flag upstream
declares the SSN keys ``SW4_KP0``/``SW4_KP1`` ``static`` in ``SW.c`` and then
references them from the top-level ``__asm__`` in ``SW_stubs.c``. As two
objects that cannot link - `undefined reference to SW4_KP0' - so ``--mode
onetu`` includes both into one file. That is a build-side arrangement of
upstream's own output, not a change to it.

**Two SDK enum types are missing from mingw-w64.** ``-p all`` declares
``NtWaitForMultipleObjects`` and ``NtCreateTimer`` with ``WAIT_TYPE`` and
``TIMER_TYPE``, which the Windows SDK has and mingw-w64 does not. They occur
only in declarations of stubs whose bodies are assembly, so the width is
immaterial to the emitted code and ``-D`` supplies them.
"""

import argparse
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



def sh(cmd, **kw):
    r = subprocess.run(cmd, shell=True, text=True, **kw)
    if r.returncode != 0:
        raise SystemExit("failed (%d): %s" % (r.returncode, cmd))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cc", required=True, help="C compiler command")
    p.add_argument("--opt", required=True, help="optimisation flag, e.g. -O2")
    p.add_argument("--mode", default="sep", choices=["sep", "onetu"])
    p.add_argument("--out", required=True, help="DLL path, relative to cwd")
    p.add_argument("--seed", default="20260101")
    p.add_argument("--prefix", default="SW4_")
    p.add_argument("gen", nargs=argparse.REMAINDER,
                   help="-- followed by syswhispers.py arguments")
    a = p.parse_args()
    gen_args = a.gen[1:] if a.gen and a.gen[0] == "--" else a.gen

    d = os.path.dirname(a.out) or "."
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)

    env = dict(os.environ, SW_SEED=a.seed)
    sh("%s %s syswhispers.py %s --out-dir %s -o SW"
       % (sys.executable, os.path.join(HERE, "syswhispers_gen.py"),
          " ".join(gen_args), d), env=env)
    sh("%s %s %s/SW.h %s/exer.c %s"
       % (sys.executable, os.path.join(HERE, "sw4_exerciser.py"), d, d, a.prefix))
    shutil.copy(os.path.join(HERE, "corpus_export.h"), d)

    if a.mode == "onetu":
        with open(os.path.join(d, "one.c"), "w") as h:
            h.write('#include "SW.c"\n#include "SW_stubs.c"\n')
        srcs = "%s/exer.c %s/one.c" % (d, d)
    else:
        srcs = "%s/exer.c %s/SW.c" % (d, d)
        if os.path.exists(os.path.join(d, "SW_stubs.c")):
            srcs += " %s/SW_stubs.c" % d

    sh("%s %s -shared -o %s %s -I%s -lntdll "
       "-DWAIT_TYPE=ULONG -DTIMER_TYPE=ULONG %s"
       % (a.cc, a.opt, a.out, srcs, d, repro_flags(a.cc)))
    print("built %s (%d bytes)" % (a.out, os.path.getsize(a.out)))


main()
