#!/usr/bin/env python3
"""Link a Windows SDK static UCRT library into one analysable PE image.

    python crawl_ucrt.py --sdk 10.0.22621 --arch x64 --out . libucrt libucrtd

The static C runtime of the Universal CRT (libucrt.lib, and libucrtd.lib for
the debug flavour) ships in ``Windows Kits\\10\\Lib\\<sdk>\\ucrt\\<arch>``, not
in the Visual Studio ``VC`` directories that data/MSVC was crawled from. Every
``/MT`` binary of VS2015 and later embeds code from it (``__acrt_*``,
``__stdio_common_*``, the locale, heap and conversion helpers).

SMDA reads PE images, not archives, so each archive is turned into one image:

  * ``lib /LIST`` records how many members the archive has;
  * ``link /DLL /NOENTRY /WHOLEARCHIVE`` pulls in every member, which is the
    same set of objects extracting all of them would give;
  * ``/NODEFAULTLIB`` keeps the VC runtime (vcruntime, libcmt, which are
    already covered by data/MSVC) out of the image, and the symbols UCRT
    expects from there stay unresolved (``/FORCE:UNRESOLVED``);
  * kernel32/advapi32/user32/ntdll import libraries are given so the calls
    UCRT makes into the OS appear as imports, as they do in a real binary;
  * ``/FORCE:MULTIPLE`` is a safety net for two members defining one external
    symbol; the number of ignored second definitions is recorded.

The link flags follow the repository's rules: ``/OPT:NOREF /OPT:NOICF`` so no
function is folded or discarded, ``/INCREMENTAL:NO`` so there is no jump
table, ``/Brepro``, and a PDB so SMDA can name the functions.

Per library it writes ``<name>.dll``, ``<name>.pdb``, ``<name>.link.log`` and
``<name>.inputs.json`` (digest and member count of the installed library, link
warnings), which the pipeline records in provenance.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys


# Import libraries that make UCRT's calls into the OS visible as imports.
# Only those present for the chosen SDK are passed.
IMPORT_LIBS = ("kernel32.lib", "advapi32.lib", "user32.lib", "ntdll.lib")

# A low, fixed base. With /FORCE:UNRESOLVED an unresolved symbol is address 0,
# and a 64-bit rel32 fixup from a high image base to address 0 would overflow.
IMAGE_BASE = "0x10000000"


def sdk_root():
    root = os.environ.get("WindowsSdkDir")
    if root and os.path.isdir(root):
        return root
    program_files = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    return os.path.join(program_files, "Windows Kits", "10")


def run(command):
    result = subprocess.run(command, capture_output=True, text=True,
                            errors="replace")
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def list_members(lib_path):
    code, output = run(["lib", "/NOLOGO", "/LIST", lib_path])
    if code != 0:
        raise SystemExit("lib /LIST failed (exit %d) for %s:\n%s"
                         % (code, lib_path, output))
    return [line.strip() for line in output.splitlines() if line.strip()]


def crawl(root, sdk, arch, name, out_dir):
    lib_dir = os.path.join(root, "Lib", sdk, "ucrt", arch)
    lib_path = os.path.join(lib_dir, name + ".lib")
    if not os.path.isfile(lib_path):
        available = []
        base = os.path.join(root, "Lib")
        if os.path.isdir(base):
            available = sorted(os.listdir(base))
        raise SystemExit("%s does not exist; Windows SDKs under %s: %s"
                         % (lib_path, base, ", ".join(available) or "none"))
    members = list_members(lib_path)
    um_dir = os.path.join(root, "Lib", sdk, "um", arch)
    imports = [os.path.join(um_dir, lib) for lib in IMPORT_LIBS
               if os.path.isfile(os.path.join(um_dir, lib))]

    dll = os.path.join(out_dir, name + ".dll")
    pdb = os.path.join(out_dir, name + ".pdb")
    command = ["link", "/NOLOGO", "/DLL", "/NOENTRY", "/NODEFAULTLIB",
               "/MACHINE:" + ("X64" if arch == "x64" else "X86"),
               "/WHOLEARCHIVE:" + lib_path, lib_path] + imports + [
               "/OUT:" + dll, "/PDB:" + pdb, "/DEBUG", "/INCREMENTAL:NO",
               "/OPT:NOREF", "/OPT:NOICF", "/Brepro",
               "/FORCE:UNRESOLVED", "/FORCE:MULTIPLE",
               "/BASE:" + IMAGE_BASE, "/DYNAMICBASE:NO", "/LARGEADDRESSAWARE:NO",
               "/IGNORE:4099"]
    if arch == "x86":
        command.append("/SAFESEH:NO")
    code, output = run(command)
    with open(os.path.join(out_dir, name + ".link.log"), "w",
              encoding="utf-8") as handle:
        handle.write("$ " + " ".join(command) + "\n" + output)
    if code != 0 or not os.path.isfile(dll) or not os.path.isfile(pdb):
        raise SystemExit("link failed for %s (exit %d):\n%s"
                         % (lib_path, code, output[-4000:]))

    duplicates = sorted(set(re.findall(
        r"LNK4006: (\S+) already defined", output)))
    unresolved = sorted(set(re.findall(
        r"unresolved external symbol (\S+)", output)))
    _, linker_banner = run(["link"])
    banner = linker_banner.splitlines()[0].strip() if linker_banner.strip() else ""
    info = {
        "sdk_version": sdk,
        "architecture": arch,
        "library": "Windows Kits/10/Lib/%s/ucrt/%s/%s.lib" % (sdk, arch, name),
        "library_sha256": sha256_file(lib_path),
        "library_bytes": os.path.getsize(lib_path),
        "library_members": len(members),
        "import_libraries": [os.path.basename(p) for p in imports],
        "linker": banner,
        "ignored_duplicate_definitions": len(duplicates),
        "ignored_duplicate_definition_names": duplicates[:50],
        "unresolved_symbols": len(unresolved),
    }
    with open(os.path.join(out_dir, name + ".inputs.json"), "w",
              encoding="utf-8") as handle:
        json.dump(info, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("%s: %d members, %d duplicate definitions ignored, %d unresolved "
          "symbols, %d bytes image" % (name, len(members), len(duplicates),
                                       len(unresolved), os.path.getsize(dll)))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sdk", required=True, help="e.g. 10.0.22621")
    parser.add_argument("--arch", required=True, choices=["x86", "x64"])
    parser.add_argument("--out", default=".")
    parser.add_argument("libraries", nargs="+", help="libucrt libucrtd")
    args = parser.parse_args()
    root = sdk_root()
    os.makedirs(args.out, exist_ok=True)
    for name in args.libraries:
        crawl(root, args.sdk, args.arch, name, args.out)


if __name__ == "__main__":
    sys.exit(main())
