#!/usr/bin/env python3
"""Link the static runtime libraries of one installed MSVC toolset into images.

    python crawl_vclib.py --list
    python crawl_vclib.py --toolset 14.16.27023 --arch x64 --out . mt mtd

data/MSVC holds one merged report per Visual Studio release, built from the
.lib/.obj files of a single install. The minor toolsets of a release differ
from each other (14.20 to 14.29 are all "VS 2019"), and a binary built by any
of them carries the runtime code of that minor. This helper turns the runtime
libraries of one installed toolset into analysable PE images, one per shard.

SMDA reads PE images, not archives, so each shard is linked whole (the same
route scripts/corpus/crawl_ucrt.py takes for the Windows SDK's static UCRT):

  * ``link /DLL /NOENTRY /WHOLEARCHIVE:<lib>`` pulls in every member;
  * ``/NODEFAULTLIB`` keeps the libraries out of each other, and the symbols a
    shard expects from elsewhere (the UCRT, the other shards) stay
    unresolved (``/FORCE:UNRESOLVED``);
  * Win32 import libraries from the newest installed Windows SDK are given so
    calls into the OS appear as imports, as they do in a real binary;
  * ``/FORCE:MULTIPLE`` lets two members define one external symbol; the
    number of ignored second definitions is recorded;
  * ``/OPT:NOREF /OPT:NOICF`` so nothing is folded or discarded,
    ``/INCREMENTAL:NO`` so there is no jump table, ``/Brepro``, and a PDB so
    SMDA can name the functions.

The linker is the one on PATH (the runner's own); only the *inputs* belong to
the toolset being crawled, and its linker version is recorded.

Shards (a shard with no library installed for the toolset is skipped); see
SHARDS for the library lists:

  mt, mt1, mtd, mtd0, mtd1   the /MT and /MTd runtime (libcmt, libvcruntime,
                             libcpmt, libconcrt), one shard per
                             _ITERATOR_DEBUG_LEVEL
  md, mdd                    msvcrt(d).lib, the static half of /MD
  support                    legacy_stdio_definitions, delayimp, ...
  com, comd                  comsupp (_com_error, _bstr_t, _variant_t)
  startup                    the *.obj files in the lib directory
  atlmfc, atlmfcd            ATL and MFC static libraries

Sanitizer, fuzzer and clang_rt libraries are never taken: they are not part of
the runtime a binary links by default and no toolset here carries them in the
library directory this reads.
"""

import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys


SHARDS = {
    # The /MT runtime. libcpmt1/libconcrt1 and libcpmtd0/1, libconcrtd0/1 are
    # the same code built with another _ITERATOR_DEBUG_LEVEL; the linker
    # refuses to mix levels (LNK2038), so each level is a shard of its own.
    "mt": ["libcmt", "libvcruntime", "libcpmt", "libconcrt"],
    "mt1": ["libcpmt1", "libconcrt1"],
    "mtd": ["libcmtd", "libvcruntimed", "libcpmtd", "libconcrtd"],
    "mtd0": ["libcpmtd0", "libconcrtd0"],
    "mtd1": ["libcpmtd1", "libconcrtd1"],
    # The static half of /MD. msvcprt(d).lib is not a shard: the linker
    # rejects it as corrupt (LNK1127) in every toolset here.
    "md": ["msvcrt"],
    "mdd": ["msvcrtd"],
    # Compatibility and helper libraries binaries link implicitly.
    "support": ["legacy_stdio_definitions", "legacy_stdio_wide_specifiers",
                "iso_stdio_wide_specifiers", "delayimp", "aligned_new",
                "exe_initialize_mta"],
    "com": ["comsupp", "comsuppw"],
    "comd": ["comsuppd", "comsuppwd"],
    "startup": None,
    "atlmfc": ["atls", "nafxcw", "uafxcw"],
    "atlmfcd": ["atlsd", "nafxcwd", "uafxcwd"],
}
ATLMFC_SHARDS = ("atlmfc", "atlmfcd")

# The Win32 import libraries given to every link, so OS calls are imports.
IMPORT_LIBS = ("kernel32", "advapi32", "user32", "gdi32", "ole32", "oleaut32",
               "shell32", "comctl32", "comdlg32", "winspool", "ws2_32", "ntdll")

IMAGE_BASE = "0x10000000"
EXCLUDE = re.compile(r"asan|ubsan|fuzzer|clang_rt|sanitizer", re.I)

# Where the toolsets are installed by the workflow (C:\BT\<n>) and where the
# VS 2015 (v140) component puts itself.
SEARCH_ROOTS = [r"C:\BT\*", r"C:\Program Files (x86)\Microsoft Visual Studio 14.0"]


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


def find_toolsets():
    """{version: {"base": dir holding lib\\<arch>, "atlmfc": ..., "root": ...}}.

    Versions are the directory names of VC\\Tools\\MSVC\\<ver>; the VS 2015
    layout (VC\\lib, VC\\lib\\amd64) is reported as ``14.0``.
    """
    found = {}
    for pattern in SEARCH_ROOTS:
        for root in glob.glob(pattern):
            for tools in glob.glob(os.path.join(root, "VC", "Tools", "MSVC", "14.*")):
                version = os.path.basename(tools)
                found[version] = {"layout": "msvc", "dir": tools, "root": root}
            old = os.path.join(root, "VC", "lib", "amd64", "libcmt.lib")
            if os.path.isfile(old):
                found["14.0"] = {"layout": "vc14", "dir": os.path.join(root, "VC"),
                                 "root": root}
            elif os.path.isfile(os.path.join(root, "lib", "amd64", "libcmt.lib")):
                found["14.0"] = {"layout": "vc14", "dir": root, "root": root}
    return found


def lib_dirs(toolset, arch):
    """(runtime lib dir, atlmfc lib dir) for a toolset entry and architecture."""
    base = toolset["dir"]
    if toolset["layout"] == "msvc":
        sub = "x64" if arch == "x64" else "x86"
        return (os.path.join(base, "lib", sub),
                os.path.join(base, "atlmfc", "lib", sub))
    sub = "amd64" if arch == "x64" else ""
    return (os.path.join(base, "lib", sub) if sub else os.path.join(base, "lib"),
            os.path.join(base, "atlmfc", "lib", sub) if sub
            else os.path.join(base, "atlmfc", "lib"))


def sdk_import_dir(arch):
    """The um\\<arch> directory of the newest installed Windows 10 SDK."""
    program_files = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    base = os.path.join(program_files, "Windows Kits", "10", "Lib")
    versions = sorted(glob.glob(os.path.join(base, "10.*")))
    for candidate in reversed(versions):
        path = os.path.join(candidate, "um", arch)
        if os.path.isdir(path):
            return path
    return None


def list_members(lib_path):
    code, output = run(["lib", "/NOLOGO", "/LIST", lib_path])
    if code != 0:
        return None
    return [line.strip() for line in output.splitlines() if line.strip()]


def describe(toolset, arch):
    """Everything the toolset has for this architecture, for the log."""
    runtime, atlmfc = lib_dirs(toolset, arch)
    info = {"runtime_dir": runtime, "atlmfc_dir": atlmfc}
    for label, directory in (("runtime", runtime), ("atlmfc", atlmfc)):
        entries = []
        if os.path.isdir(directory):
            for name in sorted(os.listdir(directory)):
                path = os.path.join(directory, name)
                if os.path.isfile(path):
                    entries.append([name, os.path.getsize(path)])
        info[label + "_files"] = entries
    return info


def shard_inputs(toolset, arch, shard):
    """(list of library paths, list of object paths) a shard is made of."""
    runtime, atlmfc = lib_dirs(toolset, arch)
    if shard == "startup":
        objs = sorted(glob.glob(os.path.join(runtime, "*.obj")))
        names = {os.path.basename(o) for o in objs}
        # pbinmode.obj and friends are the /clr:pure twins of binmode.obj and
        # cannot be linked with native objects (LNK1313).
        return [], [o for o in objs
                    if not EXCLUDE.search(os.path.basename(o))
                    and not (os.path.basename(o).startswith("p")
                             and os.path.basename(o)[1:] in names)]
    directory = atlmfc if shard in ATLMFC_SHARDS else runtime
    libs = []
    for name in SHARDS[shard]:
        path = os.path.join(directory, name + ".lib")
        if os.path.isfile(path) and not EXCLUDE.search(name):
            libs.append(path)
    return libs, []


def crawl(version, toolset, arch, shard, out_dir):
    libs, objs = shard_inputs(toolset, arch, shard)
    if not libs and not objs:
        print("%s %s %s: nothing installed, shard skipped" % (version, arch, shard))
        return None
    sdk = sdk_import_dir(arch)
    imports = []
    if sdk:
        imports = [os.path.join(sdk, name + ".lib") for name in IMPORT_LIBS
                   if os.path.isfile(os.path.join(sdk, name + ".lib"))]

    name = "%s_%s" % (shard, version.replace(".", "_"))
    dll = os.path.join(out_dir, name + ".dll")
    pdb = os.path.join(out_dir, name + ".pdb")
    command = ["link", "/NOLOGO", "/DLL", "/NOENTRY", "/NODEFAULTLIB",
               "/MACHINE:" + ("X64" if arch == "x64" else "X86")]
    command += ["/WHOLEARCHIVE:" + lib for lib in libs] + libs + objs + imports
    command += ["/OUT:" + dll, "/PDB:" + pdb, "/DEBUG", "/INCREMENTAL:NO",
                "/OPT:NOREF", "/OPT:NOICF", "/Brepro",
                "/FORCE:UNRESOLVED", "/FORCE:MULTIPLE",
                "/BASE:" + IMAGE_BASE, "/DYNAMICBASE:NO", "/LARGEADDRESSAWARE:NO",
                "/IGNORE:4099,4006,4088,4070"]
    if arch == "x86":
        command.append("/SAFESEH:NO")
    code, output = run(command)
    with open(os.path.join(out_dir, name + ".link.log"), "w",
              encoding="utf-8") as handle:
        handle.write("$ " + " ".join(command) + "\n" + output)
    if code != 0 or not os.path.isfile(dll) or not os.path.isfile(pdb):
        raise SystemExit("link failed for %s %s %s (exit %d):\n%s"
                         % (version, arch, shard, code, output[-4000:]))

    duplicates = sorted(set(re.findall(r"LNK4006: (\S+) already defined", output)))
    unresolved = sorted(set(re.findall(r"unresolved external symbol (\S+)", output)))
    _, banner = run(["link"])
    banner = banner.splitlines()[0].strip() if banner.strip() else ""
    root = toolset["root"]
    inputs = []
    for path in libs:
        members = list_members(path)
        inputs.append({"file": os.path.relpath(path, root).replace("\\", "/"),
                       "sha256": sha256_file(path),
                       "bytes": os.path.getsize(path),
                       "members": len(members) if members is not None else None})
    if objs:
        inputs.append({"objects": len(objs),
                       "files": [os.path.basename(o) for o in objs],
                       "sha256": {os.path.basename(o): sha256_file(o) for o in objs}})
    info = {
        "toolset": version,
        "architecture": arch,
        "shard": shard,
        "inputs": inputs,
        "import_libraries": [os.path.basename(p) for p in imports],
        "windows_sdk_import_dir": sdk,
        "linker": banner,
        "ignored_duplicate_definitions": len(duplicates),
        "ignored_duplicate_definition_names": duplicates[:50],
        "unresolved_symbols": len(unresolved),
    }
    with open(os.path.join(out_dir, name + ".inputs.json"), "w",
              encoding="utf-8") as handle:
        json.dump(info, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("%s %s %s: %d libraries, %d objects, %d duplicate definitions "
          "ignored, %d unresolved symbols, %d bytes image"
          % (version, arch, shard, len(libs), len(objs), len(duplicates),
             len(unresolved), os.path.getsize(dll)))
    return name


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true",
                        help="print the installed toolsets and their files")
    parser.add_argument("--toolset", help="e.g. 14.16.27023, or 14.0")
    parser.add_argument("--arch", choices=["x86", "x64"])
    parser.add_argument("--out", default=".")
    parser.add_argument("shards", nargs="*")
    args = parser.parse_args()
    toolsets = find_toolsets()
    if args.list:
        report = {}
        for version, toolset in sorted(toolsets.items()):
            report[version] = dict(toolset)
            for arch in ("x86", "x64"):
                report[version][arch] = describe(toolset, arch)
        print(json.dumps(report, indent=1))
        return 0
    if not (args.toolset and args.arch and args.shards):
        parser.error("--toolset, --arch and at least one shard are required")
    unknown = [s for s in args.shards if s not in SHARDS]
    if unknown:
        parser.error("unknown shard(s): %s" % ", ".join(unknown))
    if args.toolset not in toolsets:
        raise SystemExit("toolset %s is not installed; found: %s"
                         % (args.toolset, ", ".join(sorted(toolsets)) or "none"))
    os.makedirs(args.out, exist_ok=True)
    for shard in args.shards:
        crawl(args.toolset, toolsets[args.toolset], args.arch, shard, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
