#!/usr/bin/env python3
"""Link the libraries of one Visual Studio MSVC toolset into analysable PE images.

    python crawl_vclibs.py --toolset 14.44 --arch x64 --out . crt_mt atl
    python crawl_vclibs.py --toolset 14.44 --arch x64 --out . --inventory

data/MSVC was crawled by hand from Visual Studio's library directories. This
is the reproducible counterpart, one run per (toolset, architecture, shard),
for the toolsets the CI images carry side by side:

    VC\\Tools\\MSVC\\<toolset>\\lib\\<arch>           the C/C++ runtime
    VC\\Tools\\MSVC\\<toolset>\\ATLMFC\\lib\\<arch>   ATL and MFC

SMDA reads PE images, not archives, so a shard (a group of libraries) becomes
one image the same way crawl_ucrt.py does it for the static UCRT:
``link /DLL /NOENTRY /WHOLEARCHIVE`` pulls in every member of every library of
the shard, ``/NODEFAULTLIB`` keeps anything else out, ``/FORCE:UNRESOLVED``
leaves references to other shards (and to the static UCRT, which is crawled
separately) as unresolved symbols, and ``/FORCE:MULTIPLE`` is the safety net
for two members defining one symbol. The number of ignored definitions is
recorded. Link flags follow the repository's rules: /OPT:NOREF /OPT:NOICF
/INCREMENTAL:NO /Brepro, no /GL, no /LTCG, plus a PDB so SMDA can name the
functions.

Shards are chosen so that the libraries linked together were built with the
same runtime flavour. The CRT and STL objects carry ``detect_mismatch``
directives (RuntimeLibrary, _ITERATOR_DEBUG_LEVEL) and the linker refuses to
mix /MT with /MTd or /MD with /MDd in one image (LNK2038). That is also why
release and debug are separate shards, which is what keeps each committed file
below config.MAX_COMMITTED_FILE_SIZE.

Left out, and recorded per library in the ``excluded`` list of the inputs file:

  * ``clang_rt.*``: the sanitizer and libFuzzer runtimes, LLVM code that ships
    with the toolset but is not the Microsoft runtime (the 2022 report in
    data/MSVC carried several of 22-27 MB each);
  * libraries with no code member at all: a pure import library (every member
    is a ``*.dll`` import descriptor) holds thunks the linker synthesises and
    no function of its own.

Per shard it writes ``<shard>.dll``, ``<shard>.pdb``, ``<shard>.link.log`` and
``<shard>.inputs.json``, which the pipeline records in provenance.
"""

import argparse
import glob
import hashlib
import json
import os
import platform
import re
import subprocess
import sys


# Import libraries that make the runtime's calls into the OS visible as
# imports, as they are in a real binary. Only those present are passed.
IMPORT_LIBS = ("kernel32.lib", "advapi32.lib", "user32.lib", "ntdll.lib",
               "ole32.lib", "oleaut32.lib", "gdi32.lib")

# A low, fixed base: with /FORCE:UNRESOLVED an unresolved symbol is address 0,
# and a 64-bit rel32 fixup from a high image base to 0 would overflow.
IMAGE_BASE = "0x10000000"

# Shard name -> (directory kind, description). The assignment itself is
# classify(); this table is what the recipes and the tests enumerate.
SHARDS = {
    "crt_mt": ("crt", "C/C++ runtime, /MT release: libcmt, libvcruntime, "
                      "libcpmt*, libconcrt, oldnames, legacy_stdio_*, "
                      "delayimp and the startup objects"),
    "crt_mt_debug": ("crt", "C/C++ runtime, /MTd: the d variants of crt_mt"),
    "crt_md": ("crt", "C/C++ runtime, /MD release: the parts of msvcrt, "
                      "msvcprt, msvcurt, vcruntime, concrt, vcomp ... that "
                      "contain code"),
    "crt_md_debug": ("crt", "C/C++ runtime, /MDd: the d variants of crt_md"),
    "atl": ("atlmfc", "ATL static libraries, release"),
    "atl_debug": ("atlmfc", "ATL static libraries, debug"),
    "mfc_ansi": ("atlmfc", "MFC static, ANSI (nafxcw), release"),
    "mfc_ansi_debug": ("atlmfc", "MFC static, ANSI (nafxcwd)"),
    "mfc_unicode": ("atlmfc", "MFC static, Unicode (uafxcw), release"),
    "mfc_unicode_debug": ("atlmfc", "MFC static, Unicode (uafxcwd)"),
    "mfc_dll": ("atlmfc", "MFC for use as a DLL (mfc*, mfcs*, mfcm*), release"),
    "mfc_dll_debug": ("atlmfc", "MFC for use as a DLL, debug"),
}

# Runtime library stems. "<stem>d<digits>" is the debug variant of
# "<stem><digits>" (libcpmtd0.lib, libcpmtd1.lib, libcmtd.lib, msvcrtd.lib).
_STEMS = ("libcmt", "libvcruntime", "libcpmt", "libconcrt", "msvcrt",
          "msvcprt", "msvcurt", "msvcmrt", "vcruntime", "concrt", "vcomp",
          "ptrust", "vccorlib")
_DEBUG = re.compile(r"^(%s)d(\d*)$" % "|".join(_STEMS))
_MT = re.compile(r"^(libcmt|libvcruntime|libcpmt\d*|libconcrt)$")
_MT_OTHER = re.compile(r"^(oldnames|legacy_stdio_\w+|delayimp)$")
_MT_DEBUG_STEMS = ("libcmt", "libvcruntime", "libcpmt", "libconcrt")


def is_excluded(name):
    """The reason a file is not crawled at all, or None."""
    base = name.lower()
    if base.startswith("clang_rt."):
        return ("clang/LLVM sanitizer or libFuzzer runtime, not part of the "
                "Microsoft runtime")
    return None


def classify(name, kind):
    """Shard of a library or object file in the directory of ``kind``."""
    base, ext = os.path.splitext(name.lower())
    if kind == "crt":
        match = _DEBUG.match(base)
        if match:
            return ("crt_mt_debug" if match.group(1) in _MT_DEBUG_STEMS
                    else "crt_md_debug")
        if ext == ".obj" or _MT.match(base) or _MT_OTHER.match(base):
            return "crt_mt"
        return "crt_md"
    debug = re.match(r"^(atl\w*?|nafxcw|uafxcw|mfc\w*?)d(\d*)$", base) is not None
    suffix = "_debug" if debug else ""
    if base.startswith("atl"):
        return "atl" + suffix
    if base.startswith("nafx"):
        return "mfc_ansi" + suffix
    if base.startswith("uafx"):
        return "mfc_unicode" + suffix
    return "mfc_dll" + suffix


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


def vc_root():
    root = os.environ.get("VCINSTALLDIR")
    if root and os.path.isdir(os.path.join(root, "Tools", "MSVC")):
        return root
    for pattern in (r"C:\Program Files\Microsoft Visual Studio\*\*\VC",
                    r"C:\Program Files (x86)\Microsoft Visual Studio\*\*\VC"):
        for hit in sorted(glob.glob(pattern), reverse=True):
            if os.path.isdir(os.path.join(hit, "Tools", "MSVC")):
                return hit
    raise SystemExit("no Visual Studio VC directory found (VCINSTALLDIR=%r)"
                     % os.environ.get("VCINSTALLDIR"))


def _version_key(name):
    return [int(part) if part.isdigit() else 0 for part in name.split(".")]


def installed_toolsets(root):
    base = os.path.join(root, "Tools", "MSVC")
    return sorted((d for d in os.listdir(base)
                   if os.path.isdir(os.path.join(base, d))), key=_version_key)


def toolset_dir(root, toolset):
    """Full directory name of the toolset ``14.44`` (14.44.35207)."""
    found = [d for d in installed_toolsets(root)
             if d == toolset or d.startswith(toolset + ".")]
    if not found:
        raise SystemExit("toolset %s is not installed; this image has: %s"
                         % (toolset, ", ".join(installed_toolsets(root))))
    return found[-1]


def tool_binary(tool_root, arch, name):
    """The toolset's own link.exe / lib.exe, else whatever PATH offers."""
    host = "HostX64" if platform.machine().lower() in ("amd64", "x86_64") \
        else "HostX86"
    path = os.path.join(tool_root, "bin", host, arch, name + ".exe")
    return path if os.path.isfile(path) else name


def sdk_import_dir(arch):
    """Newest Windows SDK um\\<arch> directory that carries kernel32.lib."""
    program_files = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    root = os.environ.get("WindowsSdkDir") or os.path.join(
        program_files, "Windows Kits", "10")
    candidates = sorted(glob.glob(os.path.join(root, "Lib", "*", "um", arch)),
                        key=lambda p: _version_key(p.split(os.sep)[-3]))
    for path in reversed(candidates):
        if os.path.isfile(os.path.join(path, "kernel32.lib")):
            return path
    return None


def list_members(lib_tool, lib_path):
    code, output = run([lib_tool, "/NOLOGO", "/LIST", lib_path])
    if code != 0:
        raise SystemExit("lib /LIST failed (exit %d) for %s:\n%s"
                         % (code, lib_path, output))
    return [line.strip() for line in output.splitlines() if line.strip()]


def code_members(members):
    """Members that are objects rather than import descriptors."""
    return [m for m in members if not m.lower().endswith(".dll")]


def directories(tool_root, arch):
    return {"crt": os.path.join(tool_root, "lib", arch),
            "atlmfc": os.path.join(tool_root, "ATLMFC", "lib", arch)}


def scan(tool_root, arch, lib_tool):
    """Every .lib/.obj of both directories with its assignment."""
    entries = []
    for kind, directory in directories(tool_root, arch).items():
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory), key=str.lower):
            path = os.path.join(directory, name)
            if not os.path.isfile(path) or \
                    not name.lower().endswith((".lib", ".obj")):
                continue
            entry = {"file": name, "kind": kind, "path": path,
                     "bytes": os.path.getsize(path)}
            reason = is_excluded(name)
            if reason:
                entry["excluded"] = reason
            else:
                entry["shard"] = classify(name, kind)
                if name.lower().endswith(".lib"):
                    members = list_members(lib_tool, path)
                    entry["members"] = len(members)
                    entry["code_members"] = len(code_members(members))
                    if not entry["code_members"]:
                        entry["excluded"] = ("import library: every member is "
                                             "an import descriptor, no code")
                        del entry["shard"]
            entries.append(entry)
    return entries


def tool_banner(tool):
    _, text = run([tool])
    return text.splitlines()[0].strip() if text.strip() else ""


def inventory(root, arch, out_dir):
    """Describe every installed toolset: used on the CI image, no linking."""
    result = {"architecture": arch, "vc_root": root, "toolsets": {}}
    for name in installed_toolsets(root):
        tool_root = os.path.join(root, "Tools", "MSVC", name)
        lib_tool = tool_binary(tool_root, arch, "lib")
        libs = []
        for entry in scan(tool_root, arch, lib_tool):
            entry = dict(entry)
            entry["sha256"] = sha256_file(entry.pop("path"))
            libs.append(entry)
        extra = {}
        for sub in ("onecore", "store", "spectre", "enclave", "uwp"):
            pattern = os.path.join(tool_root, "lib", sub, arch, "*.lib")
            extra[sub] = len(glob.glob(pattern))
        result["toolsets"][name] = {"linker": tool_banner(
            tool_binary(tool_root, arch, "link")), "libraries": libs,
            "variant_directories_not_crawled": extra}
    path = os.path.join(out_dir, "inventory-%s.json" % arch)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=1, sort_keys=True)
    for name, data in result["toolsets"].items():
        used = [e for e in data["libraries"] if "shard" in e]
        print("toolset %s %s: %d files, %d crawled, %d excluded" % (
            name, arch, len(data["libraries"]), len(used),
            len(data["libraries"]) - len(used)))


def crawl(root, toolset, arch, shard, out_dir):
    kind = SHARDS[shard][0]
    full = toolset_dir(root, toolset)
    tool_root = os.path.join(root, "Tools", "MSVC", full)
    link_tool = tool_binary(tool_root, arch, "link")
    lib_tool = tool_binary(tool_root, arch, "lib")
    entries = scan(tool_root, arch, lib_tool)
    mine = [e for e in entries if e.get("shard") == shard]
    excluded = [{"file": e["file"], "bytes": e["bytes"], "reason": e["excluded"]}
                for e in entries if e["kind"] == kind and "excluded" in e]
    if not mine:
        raise SystemExit("SHARD-EMPTY: %s has no input for shard %s (%s); "
                         "excluded here: %s" % (
                             os.path.join(tool_root, "lib"), shard, arch,
                             ", ".join(x["file"] for x in excluded) or "none"))
    for entry in mine:
        entry["sha256"] = sha256_file(entry["path"])
    imports = []
    um_dir = sdk_import_dir(arch)
    if um_dir:
        imports = [os.path.join(um_dir, lib) for lib in IMPORT_LIBS
                   if os.path.isfile(os.path.join(um_dir, lib))]

    dll = os.path.join(out_dir, shard + ".dll")
    pdb = os.path.join(out_dir, shard + ".pdb")
    command = [link_tool, "/NOLOGO", "/DLL", "/NOENTRY", "/NODEFAULTLIB",
               "/MACHINE:" + ("X64" if arch == "x64" else "X86")]
    for entry in mine:
        if entry["file"].lower().endswith(".lib"):
            command.append("/WHOLEARCHIVE:" + entry["path"])
        command.append(entry["path"])
    command += imports + [
        "/OUT:" + dll, "/PDB:" + pdb, "/DEBUG", "/INCREMENTAL:NO",
        "/OPT:NOREF", "/OPT:NOICF", "/Brepro",
        "/FORCE:UNRESOLVED", "/FORCE:MULTIPLE",
        "/BASE:" + IMAGE_BASE, "/DYNAMICBASE:NO", "/LARGEADDRESSAWARE:NO",
        "/IGNORE:4099"]
    if arch == "x86":
        command.append("/SAFESEH:NO")
    code, output = run(command)
    with open(os.path.join(out_dir, shard + ".link.log"), "w",
              encoding="utf-8") as handle:
        handle.write("$ " + " ".join(command) + "\n" + output)
    if code != 0 or not os.path.isfile(dll) or not os.path.isfile(pdb):
        raise SystemExit("link failed for shard %s (exit %d):\n%s"
                         % (shard, code, output[-4000:]))

    duplicates = sorted(set(re.findall(
        r"LNK4006: (\S+) already defined", output)))
    unresolved = sorted(set(re.findall(
        r"unresolved external symbol (\S+)", output)))
    info = {
        "toolset": full,
        "toolset_requested": toolset,
        "architecture": arch,
        "shard": shard,
        "shard_description": SHARDS[shard][1],
        "directory": "VC/Tools/MSVC/%s/%s" % (
            full, "lib/" + arch if kind == "crt" else "ATLMFC/lib/" + arch),
        "libraries": [{k: e[k] for k in ("file", "bytes", "sha256", "members",
                                          "code_members") if k in e}
                      for e in mine],
        "excluded": excluded,
        "import_libraries": [os.path.basename(p) for p in imports],
        "linker": tool_banner(link_tool),
        "ignored_duplicate_definitions": len(duplicates),
        "ignored_duplicate_definition_names": duplicates[:50],
        "unresolved_symbols": len(unresolved),
        "image_bytes": os.path.getsize(dll),
    }
    with open(os.path.join(out_dir, shard + ".inputs.json"), "w",
              encoding="utf-8") as handle:
        json.dump(info, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("%s %s %s: %d inputs, %d duplicate definitions ignored, %d "
          "unresolved symbols, %d bytes image" % (
              full, arch, shard, len(mine), len(duplicates), len(unresolved),
              os.path.getsize(dll)))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--toolset", help="e.g. 14.44")
    parser.add_argument("--arch", required=True, choices=["x86", "x64"])
    parser.add_argument("--out", default=".")
    parser.add_argument("--inventory", action="store_true",
                        help="describe every installed toolset, link nothing")
    parser.add_argument("shards", nargs="*", choices=sorted(SHARDS))
    args = parser.parse_args()
    root = vc_root()
    os.makedirs(args.out, exist_ok=True)
    if args.inventory:
        inventory(root, args.arch, args.out)
        return 0
    if not args.toolset or not args.shards:
        parser.error("--toolset and at least one shard are required")
    for shard in args.shards:
        crawl(root, args.toolset, args.arch, shard, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
