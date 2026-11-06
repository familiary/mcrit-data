"""Generate, derive an exerciser for, and link one SysWhispers4 MSVC variant.

The MSVC counterpart of sw4_build.py. It exists as a separate file because
the two toolchains differ in more than the compiler name:

* **The stubs are MASM, in a file whose name depends on the architecture.**
  ``-a x64`` and ``-a arm64`` write ``SW.asm``, ``-a x86`` writes
  ``SW.x86.asm`` and ``-a wow64`` writes ``SW.wow64.asm``, so the assembler
  input is found rather than named.
* **The assembler depends on the architecture too.** ml64 for x64, ml for
  x86 and WoW64, armasm64 for ARM64 - and ARM64 is attempted rather than
  assumed, because the runner may not carry the cross assembler.
* **Symbols come from a PDB, not a COFF symbol table.** MSVC puts nothing in
  the image, and the resolver chain is ``static``, so without ``/Zi`` and a
  PDB SMDA can name only what is exported. The recipe declares the PDB.
* **The object file names collide.** ``SW.c`` and ``SW.asm`` both want
  ``SW.obj``, which is the same clash upstream's own NMakefile works around;
  the assembler output is written to ``SW_asm.obj`` here.

Nothing is run. The DLL is compiled, assembled, linked and disassembled.
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Architecture -> (assembler, glob matching the stub file the generator writes)
_ASM = {
    "x64":   ("ml64", "SW.asm"),
    "x86":   ("ml", "SW.x86.asm"),
    "wow64": ("ml", "SW.wow64.asm"),
    "arm64": ("armasm64", "SW.asm"),
}


def sh(cmd, **kw):
    if subprocess.run(cmd, shell=True, **kw).returncode:
        raise SystemExit("failed: " + cmd)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--arch", required=True, choices=sorted(_ASM))
    p.add_argument("--out", required=True, help="DLL path, relative to cwd")
    p.add_argument("--seed", default="20260101")
    p.add_argument("--prefix", default="SW4_")
    p.add_argument("--cflags", default="/O2")
    p.add_argument("gen", nargs=argparse.REMAINDER)
    a = p.parse_args()
    gen_args = a.gen[1:] if a.gen and a.gen[0] == "--" else a.gen

    d = os.path.dirname(a.out) or "."
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)
    stem = os.path.splitext(os.path.basename(a.out))[0]

    env = dict(os.environ, SW_SEED=a.seed)
    sh("%s %s syswhispers.py %s --out-dir %s -o SW"
       % (sys.executable, os.path.join(HERE, "syswhispers_gen.py"),
          " ".join(gen_args), d), env=env)
    sh("%s %s %s\\SW.h %s\\exer.c %s"
       % (sys.executable, os.path.join(HERE, "sw4_exerciser.py"), d, d, a.prefix))
    shutil.copy(os.path.join(HERE, "corpus_export.h"), d)

    assembler, stub_glob = _ASM[a.arch]
    found = sorted(glob.glob(os.path.join(d, stub_glob)))
    if len(found) != 1:
        raise SystemExit("%r matched %d files; the generator wrote %s"
                         % (stub_glob, len(found), sorted(os.listdir(d))))

    # /MD not /MT, no /GL, and /Zi so the PDB carries the static resolver's
    # names. The two enum types the mingw side supplies with -D are in the
    # Windows SDK, so nothing is needed for them here; /FI supplies the one
    # NT typedef the SDK omits. See sw4_msvc_compat.h.
    compat = os.path.join(HERE, "sw4_msvc_compat.h")
    cflags = ("/nologo /c /O2 /MD /Zi /FI\"%s\" /I%s" % (compat, d))
    sh("cl %s /Fd%s\\%s.pdb /Fo%s\\SW_c.obj %s\\SW.c"
       % (cflags, d, stem, d, d))
    sh("cl %s /Fd%s\\%s.pdb /Fo%s\\exer.obj %s\\exer.c"
       % (cflags, d, stem, d, d))
    sh("%s /nologo /c /Fo%s\\SW_asm.obj %s" % (assembler, d, found[0]))

    # /Brepro so two runs of one commit produce the same bytes; /OPT:NOREF
    # and /OPT:NOICF so nothing the exerciser only takes the address of is
    # folded or dropped; /INCREMENTAL:NO because /DEBUG implies /INCREMENTAL
    # and the /OPT:NO* forms do not suppress it, which would put a jump-thunk
    # table in the image that SMDA recovers as thousands of unnamed
    # functions.
    sh("link /nologo /DLL /DEBUG /Brepro /OPT:NOREF /OPT:NOICF "
       "/INCREMENTAL:NO /PDB:%s\\%s.pdb /OUT:%s %s\\SW_c.obj %s\\exer.obj "
       "%s\\SW_asm.obj" % (d, stem, a.out, d, d, d))
    print("built %s (%d bytes)" % (a.out, os.path.getsize(a.out)))


main()
