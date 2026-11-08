#!/usr/bin/env python3
"""Link the libraries of one Visual Studio MSVC toolset into analysable PE images.

    python crawl_vclibs.py --toolset 14.44 --arch x64 --out . crt_mt atl
    python crawl_vclibs.py --toolset 14.44 --arch x64 --out . --inventory

data/MSVC was crawled by hand from Visual Studio's library directories. This
is the reproducible counterpart, one run per (toolset, architecture, shard),
for the toolsets the CI images carry side by side:

    VC\\Tools\\MSVC\\<toolset>\\lib\\<arch>           the C/C++ runtime
    VC\\Tools\\MSVC\\<toolset>\\ATLMFC\\lib\\<arch>   ATL and MFC (14.44, 14.51)

SMDA reads PE images, not archives, so a shard (a group of libraries) becomes
one image the same way crawl_ucrt.py does it for the static UCRT, except that
the archives are unpacked here instead of passed to ``/WHOLEARCHIVE``: the
linker reports some mixed object/import libraries (msvcprt.lib, mfc140d.lib)
as corrupt under /WHOLEARCHIVE. Every COFF object member of every library is
passed to ``link /DLL /NOENTRY`` (import members are skipped, they hold no
code), ``/NODEFAULTLIB`` keeps anything else out, ``/FORCE:UNRESOLVED`` leaves
references to other shards (and to the static UCRT, crawled separately)
unresolved, and ``/FORCE:MULTIPLE`` is the safety net for two members defining
one symbol; the number of ignored definitions is recorded. Link flags follow
the repository's rules: /OPT:NOREF /OPT:NOICF /INCREMENTAL:NO /Brepro, no /GL,
no /LTCG, plus a PDB so SMDA can name the functions.

Libraries are added to the image first-fit: all of them at once and, when the
linker refuses (LNK2038/LNK1319 detect_mismatch conflicts between runtime
flavours or _ITERATOR_DEBUG_LEVEL values, LNK1313 /clr:pure objects), one by
one in descending size, and a library the linker rejects is left out of the
image and recorded with the linker's message. The shards are chosen so that
this is the exception: libraries of one runtime flavour (/MT, /MTd, /MD, /MDd
and one iterator-debug level) share a shard, and release and debug are
separate, which also keeps every committed file below
config.MAX_COMMITTED_FILE_SIZE.

Left out, and recorded per library in the ``excluded`` list of the inputs file:

  * ``clang_rt.*``: the sanitizer and libFuzzer runtimes, LLVM code that ships
    with the toolset but is not the Microsoft runtime (the 2022 report in
    data/MSVC carried several of 22-27 MB each);
  * managed runtimes (msvcmrt*, msvcurt*, *_netcore) and /clr:pure startup
    objects (p*.obj): MSIL, which SMDA cannot disassemble, and which the
    linker will not mix with native objects;
  * libraries with no object member at all: a pure import library holds
    thunks the linker synthesises and no function of its own.

Per shard it writes ``<shard>.dll``, ``<shard>.pdb``, ``<shard>.link.log`` and
``<shard>.inputs.json``, which the pipeline records in provenance. A failure
leaves its full text in ``<work dir>/diag/`` for the workflow to upload.
"""

import argparse
import glob
import hashlib
import json
import os
import platform
import re
import shutil
import struct
import subprocess
import sys


# Import libraries that make the runtime's calls into the OS visible as
# imports, as they are in a real binary. Only those present are passed.
IMPORT_LIBS = ("kernel32.lib", "advapi32.lib", "user32.lib", "ntdll.lib",
               "ole32.lib", "oleaut32.lib", "gdi32.lib")

# A low, fixed base: with /FORCE:UNRESOLVED an unresolved symbol is address 0,
# and a 64-bit rel32 fixup from a high image base to 0 would overflow.
IMAGE_BASE = "0x10000000"

# Shard name -> (directory kind, description).
SHARDS = {
    "crt_mt": ("crt", "C/C++ runtime, /MT release: libcmt, libvcruntime, "
                      "libcpmt, libconcrt, oldnames, legacy_stdio_*, "
                      "delayimp and the startup objects"),
    "crt_mt_idl1": ("crt", "C++ runtime, /MT release with "
                           "_ITERATOR_DEBUG_LEVEL=1: libcpmt1, libconcrt1"),
    "crt_mt_debug": ("crt", "C/C++ runtime, /MTd: libcmtd, libvcruntimed, "
                            "libcpmtd, libconcrtd"),
    "crt_mt_debug_idl0": ("crt", "C++ runtime, /MTd with "
                                 "_ITERATOR_DEBUG_LEVEL=0: libcpmtd0, "
                                 "libconcrtd0"),
    "crt_mt_debug_idl1": ("crt", "C++ runtime, /MTd with "
                                 "_ITERATOR_DEBUG_LEVEL=1: libcpmtd1, "
                                 "libconcrtd1"),
    "crt_md": ("crt", "C/C++ runtime, /MD release: the parts of msvcrt, "
                      "msvcprt, vcruntime, vcomp, vccorlib, comsupp ... "
                      "that contain code"),
    "crt_md_debug": ("crt", "C/C++ runtime, /MDd: the d variants of crt_md"),
    "atl": ("atlmfc", "ATL static library (atls)"),
    "mfc_ansi": ("atlmfc", "MFC static, ANSI (nafxcw), release"),
    "mfc_ansi_debug": ("atlmfc", "MFC static, ANSI (nafxcwd)"),
    "mfc_unicode": ("atlmfc", "MFC static, Unicode (uafxcw), release"),
    "mfc_unicode_debug": ("atlmfc", "MFC static, Unicode (uafxcwd)"),
    "mfc_dll": ("atlmfc", "MFC for use as a DLL (mfc*, mfcs*, mfcm*, "
                          "afxnmcd), release"),
    "mfc_dll_debug": ("atlmfc", "MFC for use as a DLL, debug"),
}

CRT_SHARDS = [n for n, v in SHARDS.items() if v[0] == "crt"]
ATLMFC_SHARDS = [n for n, v in SHARDS.items() if v[0] == "atlmfc"]


def shards_for(toolset):
    """Shards a toolset can have. 14.29 ships no ATLMFC libraries at all (the
    windows-2022 image installs the ATL/MFC component for the newest toolset
    only), which the inventory artefact of the first run showed."""
    return CRT_SHARDS if toolset == "14.29" else CRT_SHARDS + ATLMFC_SHARDS


_MANAGED = re.compile(r"^(msvcmrt|msvcurt)|_netcore$")
_PURE_OBJ = re.compile(r"^p(.+)\.obj$")
_IDL1 = re.compile(r"^(libcpmt|libconcrt)1$")
_IDL0_DEBUG = re.compile(r"^(libcpmt|libconcrt)d0$")
_IDL1_DEBUG = re.compile(r"^(libcpmt|libconcrt)d1$")
_MT_DEBUG = re.compile(r"^(libcmt|libvcruntime|libcpmt|libconcrt)d$")
_MT = re.compile(r"^(libcmt|libvcruntime|libcpmt|libconcrt)$")
_MT_OTHER = re.compile(r"^(oldnames|legacy_stdio_\w+|delayimp)$")


def is_excluded(name, siblings=()):
    """The reason a file is not crawled at all, or None."""
    base = name.lower()
    stem = os.path.splitext(base)[0]
    if base.startswith("clang_rt."):
        return ("clang/LLVM sanitizer or libFuzzer runtime, not part of the "
                "Microsoft runtime")
    if _MANAGED.search(stem):
        return "managed (/clr) runtime: MSIL, not native code"
    match = _PURE_OBJ.match(base)
    if match and match.group(1) + ".obj" in {s.lower() for s in siblings}:
        return "/clr:pure startup object: MSIL, cannot link with native objects"
    return None


def classify(name, kind, siblings=()):
    """Shard of a library or object file in the directory of ``kind``."""
    base, ext = os.path.splitext(name.lower())
    if kind == "crt":
        if _IDL1.match(base):
            return "crt_mt_idl1"
        if _IDL0_DEBUG.match(base):
            return "crt_mt_debug_idl0"
        if _IDL1_DEBUG.match(base):
            return "crt_mt_debug_idl1"
        if _MT_DEBUG.match(base):
            return "crt_mt_debug"
        if ext == ".obj" or _MT.match(base) or _MT_OTHER.match(base):
            return "crt_mt"
        # A debug flavour of a library that also exists without the d:
        # msvcrtd, msvcprtd, vcompd, comsuppwd, vccorlibd ...
        if base.endswith("d") and base[:-1] + ext in {
                s.lower() for s in siblings}:
            return "crt_md_debug"
        return "crt_md"
    if base.startswith("afxnmcd"):
        debug = base.endswith("dd")
    else:
        debug = re.match(r"^(atl\w*?|nafxcw|uafxcw|mfc\w*?)d$", base) \
            is not None
    suffix = "_debug" if debug else ""
    if base.startswith("atl"):
        # No debug ATL libraries ship: atls is the only one.
        return "atl"
    if base.startswith("nafx"):
        return "mfc_ansi" + suffix
    if base.startswith("uafx"):
        return "mfc_unicode" + suffix
    return "mfc_dll" + suffix


def run(command):
    result = subprocess.run(command, capture_output=True, text=True,
                            errors="replace")
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def diagnose(label, text):
    """Keep a failure's full text where the workflow uploads it.

    The pipeline writes a step's output to one log per (recipe, toolchain), so
    the next shard of the same toolset overwrites the reason for the last.
    """
    work = os.environ.get("MCRIT_DATA_WORK_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "build")
    directory = os.path.join(work, "diag")
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, label + ".txt"), "w",
              encoding="utf-8") as handle:
        handle.write(text)


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
    """The toolset's own link.exe, else whatever PATH offers."""
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


def unpack_archive(lib_path, dest=None):
    """COFF object members of an ``!<arch>`` library, written into ``dest``.

    Returns (members, object_paths). Linker members and import objects (the
    short import header: signature 0x0000 0xFFFF, version 0) are not objects.
    With ``dest`` None nothing is written and the paths are just names.
    """
    with open(lib_path, "rb") as handle:
        data = handle.read()
    if data[:8] != b"!<arch>\n":
        raise ValueError("%s is not an archive" % lib_path)
    longnames = b""
    position = 8
    members = 0
    objects = []
    while position + 60 <= len(data):
        header = data[position:position + 60]
        name = header[:16].decode("latin-1").strip()
        size = int(header[48:58].decode("latin-1").strip() or 0)
        body = data[position + 60:position + 60 + size]
        position += 60 + size + (size & 1)
        if name == "//":
            longnames = body
            continue
        if name == "/" or name.startswith("/<") or name.startswith("/ECSYM"):
            continue
        members += 1
        if name.startswith("/") and name[1:].isdigit():
            start = int(name[1:])
            ends = [e for e in (longnames.find(b"\x00", start),
                                longnames.find(b"\n", start)) if e != -1]
            name = longnames[start:min(ends) if ends else None].decode(
                "latin-1").rstrip("/")
        else:
            name = name.rstrip("/")
        if len(body) >= 8 and body[:2] == b"\x00\x00" and \
                body[2:4] == b"\xff\xff" and \
                struct.unpack("<H", body[4:6])[0] < 2:
            continue  # short import object
        if len(body) < 20:
            continue
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(
            name.replace("\\", "/")))[:80] or "member"
        path = "%05d_%s" % (len(objects), safe)
        if dest is not None:
            path = os.path.join(dest, path)
            if not path.lower().endswith((".obj", ".o")):
                path += ".obj"
            with open(path, "wb") as out:
                out.write(body)
        objects.append(path)
    return members, objects


def directories(tool_root, arch):
    return {"crt": os.path.join(tool_root, "lib", arch),
            "atlmfc": os.path.join(tool_root, "ATLMFC", "lib", arch)}


def scan(tool_root, arch, unpack_to=None):
    """Every .lib/.obj of both directories with its assignment.

    With ``unpack_to`` ({shard: directory}) the object members of the
    libraries assigned to those shards are written below it, and ``objects``
    holds their paths.
    """
    entries = []
    for kind, directory in directories(tool_root, arch).items():
        if not os.path.isdir(directory):
            continue
        names = sorted(os.listdir(directory), key=str.lower)
        for name in names:
            path = os.path.join(directory, name)
            if not os.path.isfile(path) or \
                    not name.lower().endswith((".lib", ".obj")):
                continue
            entry = {"file": name, "kind": kind, "path": path,
                     "bytes": os.path.getsize(path)}
            reason = is_excluded(name, names)
            if reason:
                entry["excluded"] = reason
                entries.append(entry)
                continue
            entry["shard"] = classify(name, kind, names)
            if name.lower().endswith(".lib"):
                want = unpack_to is not None and entry["shard"] in unpack_to
                dest = None
                if want:
                    dest = os.path.join(unpack_to[entry["shard"]],
                                        "%s_%s" % (kind, name))
                    os.makedirs(dest, exist_ok=True)
                try:
                    members, objects = unpack_archive(path, dest)
                except (ValueError, OSError, struct.error) as error:
                    entry["excluded"] = "unreadable archive: %s" % error
                    del entry["shard"]
                    entries.append(entry)
                    continue
                entry["members"] = members
                entry["code_members"] = len(objects)
                if not objects:
                    entry["excluded"] = ("import library: every member is "
                                         "an import descriptor, no code")
                    del entry["shard"]
                elif want:
                    entry["objects"] = objects
            else:
                entry["objects"] = [path]
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
        libs = []
        for entry in scan(tool_root, arch):
            entry = dict(entry)
            entry["sha256"] = sha256_file(entry.pop("path"))
            entry.pop("objects", None)
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


def _link(link_tool, arch, inputs, imports, dll, pdb, response):
    """One link of ``inputs`` (object paths); returns (ok, output)."""
    with open(response, "w", encoding="utf-8") as handle:
        for path in inputs:
            handle.write('"%s"\n' % path)
    command = [link_tool, "/NOLOGO", "/DLL", "/NOENTRY", "/NODEFAULTLIB",
               "/MACHINE:" + ("X64" if arch == "x64" else "X86"),
               "@" + response] + imports + [
        "/OUT:" + dll, "/PDB:" + pdb, "/DEBUG", "/INCREMENTAL:NO",
        "/OPT:NOREF", "/OPT:NOICF", "/Brepro",
        "/FORCE:UNRESOLVED", "/FORCE:MULTIPLE",
        "/BASE:" + IMAGE_BASE, "/DYNAMICBASE:NO", "/LARGEADDRESSAWARE:NO",
        "/IGNORE:4099"]
    if arch == "x86":
        command.append("/SAFESEH:NO")
    for path in (dll, pdb):
        if os.path.exists(path):
            os.remove(path)
    code, output = run(command)
    ok = code == 0 and os.path.isfile(dll) and os.path.isfile(pdb)
    return ok, "$ " + " ".join(command[:6]) + " ...\n" + output


def _reason(output, entry):
    """Why the linker refused: the lines that name the entry, else fatal."""
    lines = output.splitlines()
    own = [l for l in lines if entry["file"].lower() in l.lower()
           and ("LNK2038" in l or "LNK1" in l)]
    fatal = [l for l in lines if "fatal error" in l]
    return " | ".join((own[:2] + fatal[:2]) or ["link failed"])[:600]


def crawl(root, toolset, arch, shard, out_dir):
    kind = SHARDS[shard][0]
    full = toolset_dir(root, toolset)
    label = "%s-%s-%s" % (full, arch, shard)
    tool_root = os.path.join(root, "Tools", "MSVC", full)
    link_tool = tool_binary(tool_root, arch, "link")
    if shard not in shards_for(toolset):
        message = "SHARD-NOT-APPLICABLE: toolset %s has no %s libraries" % (
            toolset, kind)
        diagnose(label, message)
        raise SystemExit(message)
    unpack_root = os.path.join(out_dir, "objects-" + shard)
    os.makedirs(unpack_root, exist_ok=True)
    entries = scan(tool_root, arch, {shard: unpack_root})
    mine = [e for e in entries if e.get("shard") == shard]
    excluded = [{"file": e["file"], "bytes": e["bytes"], "reason": e["excluded"]}
                for e in entries if e["kind"] == kind and "excluded" in e]
    if not mine:
        message = ("SHARD-EMPTY: %s has no input for shard %s (%s); files "
                   "seen: %s" % (tool_root, shard, arch,
                                 ", ".join(e["file"] for e in entries)))
        diagnose(label, message)
        raise SystemExit(message)
    for entry in mine:
        entry["sha256"] = sha256_file(entry["path"])
    imports = []
    um_dir = sdk_import_dir(arch)
    if um_dir:
        imports = [os.path.join(um_dir, lib) for lib in IMPORT_LIBS
                   if os.path.isfile(os.path.join(um_dir, lib))]

    dll = os.path.join(out_dir, shard + ".dll")
    pdb = os.path.join(out_dir, shard + ".pdb")
    trial_dll = os.path.join(out_dir, shard + ".trial.dll")
    trial_pdb = os.path.join(out_dir, shard + ".trial.pdb")
    response = os.path.join(out_dir, shard + ".rsp")

    def attempt(group):
        ok, output = _link(link_tool, arch,
                           [o for e in group for o in e["objects"]], imports,
                           trial_dll, trial_pdb, response)
        if ok:
            os.replace(trial_dll, dll)
            os.replace(trial_pdb, pdb)
        return ok, output

    log = []
    ok, output = attempt(mine)
    log.append(output[-30000:])
    accepted = list(mine)
    if not ok:
        diagnose(label + "-all-at-once", output[-60000:])
        # First-fit, largest first: the core libraries go in before anything
        # that might conflict with them.
        accepted = []
        output = ""
        for entry in sorted(mine, key=lambda e: -e["bytes"]):
            ok, trial_output = attempt(accepted + [entry])
            if ok:
                accepted.append(entry)
                output = trial_output
            else:
                reason = _reason(trial_output, entry)
                excluded.append({"file": entry["file"], "bytes": entry["bytes"],
                                 "reason": "rejected by the linker: " + reason})
                log.append("REJECTED %s: %s" % (entry["file"], reason))
        ok = bool(accepted)
    with open(os.path.join(out_dir, shard + ".link.log"), "w",
              encoding="utf-8") as handle:
        handle.write("\n".join(log) + "\n" + output[-200000:])
    if not ok:
        diagnose(label, "\n".join(log))
        errors = [l for l in "\n".join(log).splitlines()
                  if "fatal error" in l or "REJECTED" in l]
        raise SystemExit("link failed for shard %s:\n%s"
                         % (shard, "\n".join(errors[:15])))

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
                      for e in accepted],
        "excluded": excluded,
        "import_libraries": [os.path.basename(p) for p in imports],
        "linker": tool_banner(link_tool),
        "ignored_duplicate_definitions": len(duplicates),
        "ignored_duplicate_definition_names": duplicates[:50],
        "unresolved_symbols": len(unresolved),
        "object_members": sum(len(e["objects"]) for e in accepted),
        "image_bytes": os.path.getsize(dll),
    }
    with open(os.path.join(out_dir, shard + ".inputs.json"), "w",
              encoding="utf-8") as handle:
        json.dump(info, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("%s %s %s: %d libraries (%d excluded), %d objects, %d duplicate "
          "definitions ignored, %d bytes image" % (
              full, arch, shard, len(accepted), len(excluded),
              info["object_members"], len(duplicates), os.path.getsize(dll)))
    shutil.rmtree(unpack_root, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--toolset", help="e.g. 14.44")
    parser.add_argument("--arch", required=True, choices=["x86", "x64"])
    parser.add_argument("--out", default=".")
    parser.add_argument("--inventory", action="store_true",
                        help="describe every installed toolset, link nothing")
    parser.add_argument("shards", nargs="*", metavar="SHARD",
                        help="one of: " + ", ".join(sorted(SHARDS)))
    args = parser.parse_args()
    root = vc_root()
    os.makedirs(args.out, exist_ok=True)
    if args.inventory:
        inventory(root, args.arch, args.out)
        return 0
    if not args.toolset or not args.shards:
        parser.error("--toolset and at least one shard are required")
    unknown = [s for s in args.shards if s not in SHARDS]
    if unknown:
        parser.error("unknown shard(s) %s" % ", ".join(unknown))
    for shard in args.shards:
        crawl(root, args.toolset, args.arch, shard, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
