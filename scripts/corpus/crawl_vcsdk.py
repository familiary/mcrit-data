#!/usr/bin/env python3
"""Turn the C runtime of an old Visual C++ release into analysable PE images.

    python crawl_vcsdk.py --iso-url URL --iso-sha256 HASH \\
        --cab Setup/vc_stdamd64/vc_stdamd64.cab --out . libs
    python crawl_vcsdk.py ... dlls

data/MSVC was crawled from Visual Studio installs and holds Visual C++
2005/2008/2010 for x86 only. The x64 libraries of those compilers shipped with
the Windows SDK of the day, in a DVD image whose ``Setup\\vc_*`` directories
hold one MSI and one CAB per target (the CAB is what carries the files; the
MSI is only the installer's bookkeeping). The image is a UDF file system,
which 7-Zip reads. This script:

  * downloads the image once (``--cache``), refuses it unless its SHA-256
    equals ``--iso-sha256``, and extracts only the one CAB it needs;
  * unpacks that CAB. Its members are named after the installer's file keys
    (``FL_libcmt_lib_74650_74650_amd64_ln.<guid>``, ``FL_libcpmt_lib_x64``,
    ``F_CENTRAL_msvcr100_x64``); ``KEY_PATTERNS`` maps a key back to the file
    name it installs, and the mapping is written into the inputs record;
  * ``libs``: links each static library whole into one image, exactly as
    crawl_ucrt.py does (``/WHOLEARCHIVE /NODEFAULTLIB /FORCE:UNRESOLVED
    /FORCE:MULTIPLE``, no folding, no discarding), and the loose start-up
    objects (binmode.obj, setargv.obj, ...) into one more;
  * ``dlls``: copies the redistributable runtime DLLs and their PDBs, which
    are real shipped images and need no linking.

What each input is, is verified rather than assumed: the compiler records in
the objects of every library (CodeView S_COMPILE3: front end / back end
version and target machine) and the version resource of every DLL are written
to ``<name>.inputs.json``, which the pipeline copies into provenance.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from collections import Counter


# CAB member key -> installed file name. The first group is matched on the
# whole key. Order matters: the first pattern that matches wins.
KEY_PATTERNS = [
    # F_CENTRAL_msvcr100_x64 -> msvcr100.dll
    (re.compile(r"^F_CENTRAL_(?P<name>[A-Za-z0-9]+)_(?P<arch>x64|x86)$"), "dll"),
    # F_PDB_msvcr100_x64 -> msvcr100.pdb
    (re.compile(r"^F_PDB_(?P<name>[A-Za-z0-9]+)_(?P<arch>x64|x86)$"), "pdb"),
    # FL_libcmt_lib_74650_74650_amd64_ln.<guid>, FL_nohetoc_obj_amd64_ln,
    # FL_libcpmt_lib_x64 -> libcmt.lib, nohetoc.obj, libcpmt.lib
    (re.compile(r"^FL_(?P<name>[A-Za-z0-9]+)_(?P<ext>lib|obj|pdb)"
                r"(?:_\d+_\d+)?_(?:amd64_ln|x64)(?:\..*)?$"), None),
]

# Import libraries that make the runtime's calls into the OS visible as
# imports. They come from the Windows SDK the build host's developer
# environment (LIB) points at; a missing one only leaves those calls unresolved.
IMPORT_LIBS = ("kernel32.lib", "advapi32.lib", "user32.lib", "ntdll.lib")

# A low, fixed base: with /FORCE:UNRESOLVED an unresolved symbol is address 0
# and a rel32 fixup from a high base would overflow.
IMAGE_BASE = "0x10000000"

CODEVIEW_COMPILE2, CODEVIEW_COMPILE3 = 0x1116, 0x113C
MACHINES = {0xD0: "x64 (AMD64)", 0x06: "x86 (Pentium Pro)", 0x07: "x86 (Pentium II)"}


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command, **kwargs):
    result = subprocess.run(command, capture_output=True, text=True,
                            errors="replace", **kwargs)
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def find_7z():
    for candidate in (shutil.which("7z"), shutil.which("7za"),
                      r"C:\Program Files\7-Zip\7z.exe",
                      r"C:\Program Files (x86)\7-Zip\7z.exe"):
        if candidate and os.path.isfile(candidate):
            return candidate
    raise SystemExit("7-Zip is required to read the SDK image and its CAB")


def download(url, destination):
    curl = shutil.which("curl") or shutil.which("curl.exe")
    if not curl:
        raise SystemExit("curl is required to download %s" % url)
    code, output = run([curl, "--fail", "--location", "--silent", "--show-error",
                        "--retry", "5", "--retry-all-errors", "--retry-delay", "10",
                        "-o", destination, url])
    if code != 0:
        raise SystemExit("download of %s failed (curl exit %d): %s"
                         % (url, code, output.strip()))


def fetch_cab(args, cache):
    """Return (cab path, record of what was downloaded)."""
    os.makedirs(cache, exist_ok=True)
    iso = os.path.join(cache, os.path.basename(args.iso_url))
    if not os.path.isfile(iso) or sha256_file(iso) != args.iso_sha256:
        print("downloading %s" % args.iso_url, flush=True)
        download(args.iso_url, iso)
    observed = sha256_file(iso)
    print("image sha256 %s (%d bytes)" % (observed, os.path.getsize(iso)),
          flush=True)
    if observed != args.iso_sha256:
        raise SystemExit("%s hashes to %s, expected %s; refusing to use it"
                         % (args.iso_url, observed, args.iso_sha256))
    sevenzip = find_7z()
    extract = os.path.join(cache, "iso-members")
    os.makedirs(extract, exist_ok=True)
    cab = os.path.join(extract, *args.cab.split("/"))
    if not os.path.isfile(cab):
        code, output = run([sevenzip, "x", "-y", "-o" + extract, iso, args.cab])
        if code != 0 or not os.path.isfile(cab):
            code2, listing = run([sevenzip, "l", iso])
            raise SystemExit("could not extract %s from the image (7z exit %d):"
                             "\n%s\n--- image listing ---\n%s"
                             % (args.cab, code, output[-2000:], listing[-6000:]))
    record = {
        "image_url": args.iso_url,
        "image_sha256": observed,
        "image_bytes": os.path.getsize(iso),
        "cab": args.cab,
        "cab_sha256": sha256_file(cab),
        "cab_bytes": os.path.getsize(cab),
    }
    return cab, record


def unpack_cab(cab, destination):
    """Extract the CAB and return {installed file name: path}."""
    sevenzip = find_7z()
    os.makedirs(destination, exist_ok=True)
    code, output = run([sevenzip, "x", "-y", "-o" + destination, cab])
    # 7-Zip warns about the bytes after the CAB's end (the image pads it), and
    # exits 2; the files are intact and the listing below is the check.
    if code not in (0, 2):
        raise SystemExit("7z could not unpack %s (exit %d):\n%s"
                         % (cab, code, output[-2000:]))
    files = {}
    unmatched = []
    for key in sorted(os.listdir(destination)):
        full = os.path.join(destination, key)
        installed = None
        for pattern, ext in KEY_PATTERNS:
            match = pattern.match(key)
            if match:
                extension = ext or match.group("ext")
                installed = "%s.%s" % (match.group("name"), extension)
                break
        if installed is None:
            unmatched.append(key)
            continue
        files.setdefault(installed.lower(), []).append((key, full))
    ambiguous = {name: [k for k, _ in items] for name, items in files.items()
                 if len(items) > 1}
    if ambiguous:
        raise SystemExit("several CAB members map to one file name: %s"
                         % json.dumps(ambiguous, indent=1))
    print("%d CAB members mapped to file names, %d are not libraries or "
          "runtime DLLs (compilers, props, ...)" % (len(files), len(unmatched)),
          flush=True)
    # link.exe decides between an archive and an object by the file name's
    # extension, and a key such as FL_libcpmt_lib_x64 has none, so every file
    # is copied to its installed name first.
    named = os.path.join(destination, "named")
    os.makedirs(named, exist_ok=True)
    result = {}
    for name, items in files.items():
        key, full = items[0]
        target = os.path.join(named, name)
        shutil.copyfile(full, target)
        result[name] = (key, target)
    return result


def compiler_records(data):
    """Count CodeView compiler records: {(machine, front end, back end): n}.

    S_COMPILE2/S_COMPILE3 sit in every object's .debug$S, directly before the
    producer string; the version numbers in them are what the compiler
    reported, not what a file name claims.
    """
    counts = Counter()
    for match in re.finditer(rb"Microsoft \(R\) [A-Za-z ]*Compiler\x00", data):
        end = match.end()
        for back in range(8, 48):
            offset = match.start() - back
            if offset < 0:
                break
            length, kind = struct.unpack_from("<HH", data, offset)
            if kind not in (CODEVIEW_COMPILE2, CODEVIEW_COMPILE3) \
                    or offset + 2 + length != end:
                continue
            if kind == CODEVIEW_COMPILE2:
                _, machine, fma, fmi, fbd, bma, bmi, bbd = struct.unpack_from(
                    "<IHHHHHHH", data, offset + 4)
            else:
                (_, machine, fma, fmi, fbd, _fq, bma, bmi, bbd,
                 _bq) = struct.unpack_from("<IHHHHHHHHH", data, offset + 4)
            counts[(MACHINES.get(machine, "machine 0x%X" % machine),
                    "%d.%d.%d" % (fma, fmi, fbd),
                    "%d.%d.%d" % (bma, bmi, bbd))] += 1
            break
    return counts


def compiler_summary(paths):
    counts = Counter()
    for path in paths:
        with open(path, "rb") as handle:
            counts.update(compiler_records(handle.read()))
    return [{"target": machine, "front_end": front, "back_end": back,
             "objects": count}
            for (machine, front, back), count in sorted(counts.items())]


def list_members(lib_path):
    code, output = run(["lib", "/NOLOGO", "/LIST", lib_path])
    if code != 0:
        raise SystemExit("lib /LIST failed (exit %d) for %s:\n%s"
                         % (code, lib_path, output))
    return [line.strip() for line in output.splitlines() if line.strip()]


def linker_banner():
    _, banner = run(["link"])
    return banner.splitlines()[0].strip() if banner.strip() else ""


def write_json(path, info):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(info, handle, indent=2, sort_keys=True)
        handle.write("\n")


def link_image(name, libs, objs, out_dir, source_record, files_note):
    """Link ``libs`` (whole) and ``objs`` into ``<name>.dll`` with a PDB."""
    dll = os.path.join(out_dir, name + ".dll")
    pdb = os.path.join(out_dir, name + ".pdb")
    command = ["link", "/NOLOGO", "/DLL", "/NOENTRY", "/NODEFAULTLIB",
               "/MACHINE:X64"]
    command += ["/WHOLEARCHIVE:" + path for path in libs] + list(libs)
    command += list(objs) + list(IMPORT_LIBS)
    command += ["/OUT:" + dll, "/PDB:" + pdb, "/DEBUG", "/INCREMENTAL:NO",
                "/OPT:NOREF", "/OPT:NOICF", "/Brepro",
                "/FORCE:UNRESOLVED", "/FORCE:MULTIPLE",
                "/BASE:" + IMAGE_BASE, "/DYNAMICBASE:NO", "/LARGEADDRESSAWARE:NO",
                "/IGNORE:4099"]
    code, output = run(command)
    with open(os.path.join(out_dir, name + ".link.log"), "w",
              encoding="utf-8") as handle:
        handle.write("$ " + " ".join(command) + "\n" + output)
    if code != 0 or not os.path.isfile(dll) or not os.path.isfile(pdb):
        raise SystemExit("link failed for %s (exit %d):\n%s"
                         % (name, code, output[-4000:]))
    duplicates = sorted(set(re.findall(r"LNK4006: (\S+) already defined", output)))
    unresolved = sorted(set(re.findall(r"unresolved external symbol (\S+)", output)))
    members = sum(len(list_members(path)) for path in libs)
    info = dict(source_record)
    info.update({
        "inputs": files_note,
        "library_members": members,
        "start_up_objects": len(objs),
        "compiler_records": compiler_summary(list(libs) + list(objs)),
        "import_libraries": list(IMPORT_LIBS),
        "linker": linker_banner(),
        "ignored_duplicate_definitions": len(duplicates),
        "ignored_duplicate_definition_names": duplicates[:50],
        "unresolved_symbols": len(unresolved),
    })
    write_json(os.path.join(out_dir, name + ".inputs.json"), info)
    print("%s: %d archive members + %d objects, %d duplicate definitions "
          "ignored, %d unresolved symbols, compilers %s" % (
              name, members, len(objs), len(duplicates), len(unresolved),
              json.dumps(info["compiler_records"])), flush=True)


def pe_version_info(path):
    try:
        import pefile
    except ImportError:
        return {}
    pe = pefile.PE(path, fast_load=False)
    info = {"machine": hex(pe.FILE_HEADER.Machine),
            "linker_version": "%d.%d" % (pe.OPTIONAL_HEADER.MajorLinkerVersion,
                                         pe.OPTIONAL_HEADER.MinorLinkerVersion)}
    for entry in getattr(pe, "FileInfo", []) or []:
        for item in entry:
            for table in getattr(item, "StringTable", []) or []:
                for key, value in table.entries.items():
                    if key in (b"FileVersion", b"ProductVersion",
                               b"OriginalFilename", b"ProductName",
                               b"FileDescription"):
                        info[key.decode()] = value.decode(errors="replace")
    pe.close()
    return info


def cmd_libs(args, files, source_record, out_dir):
    libs = {n: p for n, (_, p) in files.items() if n.endswith(".lib")}
    objs = sorted(p for n, (_, p) in files.items() if n.endswith(".obj"))
    wanted = []
    for spec in args.names:
        wanted.append([part for part in spec.split("+") if part])
    for group in wanted:
        paths = []
        for stem in group:
            if stem == "objs":
                continue
            if stem + ".lib" not in libs:
                raise SystemExit("%s.lib is not in the CAB; libraries present: "
                                 "%s" % (stem, ", ".join(sorted(libs))))
            paths.append(libs[stem + ".lib"])
        name = "+".join(group).replace("+", "_")
        group_objs = objs if "objs" in group else []
        note = {"libraries": [{"file": s + ".lib",
                               "cab_member": files[s + ".lib"][0],
                               "sha256": sha256_file(libs[s + ".lib"]),
                               "bytes": os.path.getsize(libs[s + ".lib"])}
                              for s in group if s != "objs"]}
        if group_objs:
            note["objects"] = [{"file": os.path.basename(p), "sha256": sha256_file(p)}
                               for p in group_objs]
        link_image(name, paths, group_objs, out_dir, source_record, note)


def cmd_dlls(args, files, source_record, out_dir):
    for stem in args.names:
        for extension in ("dll", "pdb"):
            key = "%s.%s" % (stem, extension)
            if key not in files:
                raise SystemExit("%s is not in the CAB; present: %s"
                                 % (key, ", ".join(sorted(files))))
            shutil.copyfile(files[key][1], os.path.join(out_dir, key))
        info = dict(source_record)
        info.update({
            "cab_members": [files[stem + ".dll"][0], files[stem + ".pdb"][0]],
            "dll_sha256": sha256_file(os.path.join(out_dir, stem + ".dll")),
            "pdb_sha256": sha256_file(os.path.join(out_dir, stem + ".pdb")),
            "pe": pe_version_info(os.path.join(out_dir, stem + ".dll")),
        })
        write_json(os.path.join(out_dir, stem + ".inputs.json"), info)
        print("%s: %s" % (stem, json.dumps(info["pe"])), flush=True)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--iso-url", required=True)
    parser.add_argument("--iso-sha256", required=True)
    parser.add_argument("--cab", required=True,
                        help="path of the CAB inside the image")
    parser.add_argument("--cache", default=os.path.join(
        tempfile.gettempdir(), "mcrit-vcsdk-cache"),
        help="where the image and the unpacked CAB are kept between runs")
    parser.add_argument("--out", default=".")
    parser.add_argument("mode", choices=["libs", "dlls"])
    parser.add_argument("names", nargs="+",
                        help="libs: libcmt libcpmt+libcpmt1 objs ...; "
                             "dlls: msvcr100 msvcp100")
    args = parser.parse_args()
    args.iso_sha256 = args.iso_sha256.lower()
    cab, record = fetch_cab(args, args.cache)
    unpacked = os.path.join(args.cache, "cab-" + record["cab_sha256"][:16])
    files = unpack_cab(cab, unpacked)
    files = {name: (key, path) for name, (key, path) in files.items()}
    os.makedirs(args.out, exist_ok=True)
    out_dir = os.path.abspath(args.out)
    if args.mode == "libs":
        cmd_libs(args, files, record, out_dir)
    else:
        cmd_dlls(args, files, record, out_dir)


if __name__ == "__main__":
    sys.exit(main())
