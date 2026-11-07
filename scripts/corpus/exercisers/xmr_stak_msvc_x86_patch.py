"""Patch an xmr-stak 2.10.8 source tree for the MSVC x86 build.

Run from the source root by xmr_stak_msvc_x86.py (the patches are listed in
that recipe's docstring); nothing here is committed to the upstream tree.

1. cryptonight_aesni.h: the `#error You are trying to do a 32-bit build` line
   is deleted and `#ifdef _WIN64` becomes `#ifdef _WIN32` (five places: the
   Win32 includes and the VirtualAlloc, VirtualProtect and
   FlushInstructionCache branches; _WIN64 is undefined on x86).
2. The two MASM sources, cryptonight_v8_main_loop.asm and
   cnR/CryptonightR_template.asm, are 64-bit (r8-r15, rbp, ...) and ml.exe
   cannot assemble them for x86. Each is overwritten with a stub: one
   `name PROC / ret / name ENDP` for every symbol the original PUBLIC-declares.
3. xmr_stak_msvc_x86_compat.h is copied to the source root (which CMake puts
   on the include path) so that /FI can name it without a path.
"""
import os
import re
import shutil
import sys

root = sys.argv[1] if len(sys.argv) > 1 else "."
here = os.path.dirname(os.path.abspath(__file__))
crypto = os.path.join(root, "xmrstak", "backend", "cpu", "crypto")

hdr = os.path.join(crypto, "cryptonight_aesni.h")
text = open(hdr, newline="").read()
err = re.compile(r"^#error You are trying to do a 32-bit build[^\n]*\n", re.M)
assert len(err.findall(text)) == 1
text = err.sub("", text)
assert text.count("#ifdef _WIN64") == 5
text = text.replace("#ifdef _WIN64", "#ifdef _WIN32")
open(hdr, "w", newline="").write(text)

total = 0
for rel in ("asm/cryptonight_v8_main_loop.asm", "asm/cnR/CryptonightR_template.asm"):
    path = os.path.join(crypto, *rel.split("/"))
    names = re.findall(r"^PUBLIC (\w+)", open(path).read(), re.M)
    assert names and len(set(names)) == len(names)
    out = [".386", ".model flat, C", ".code"]
    for n in names:
        out += ["PUBLIC %s" % n, "%s PROC" % n, "\tret", "%s ENDP" % n]
    out.append("END")
    open(path, "w", newline="").write("\r\n".join(out) + "\r\n")
    total += len(names)
    print("stubbed %s: %d symbols" % (rel, len(names)))
print("stubs: %d" % total)

shutil.copyfile(os.path.join(here, "xmr_stak_msvc_x86_compat.h"),
                os.path.join(root, "xs_msvc_x86_compat.h"))
