"""Build-side helper for the SoftEther VPN 5.x MSVC recipe.

softether_vpn5.py's MSVC recipe calls this twice. It changes nothing under
the cloned source tree: ``prepare`` writes two small files next to it that
are handed to CMake on the command line, and ``names`` only reads the
finished build.

``prepare <source_root> <arch>``

  * ``vcpkg-triplets/se-<arch>-windows-release.cmake``, an overlay vcpkg
    triplet: dynamic CRT, dynamic libraries, release only. It is vcpkg's own
    ``<arch>-windows`` triplet minus the debug build of every port, so
    OpenSSL, zlib and libsodium arrive as DLLs plus import libraries and none
    of their code can be linked into vpnserver.exe.
  * ``se-msvc-runtime.cmake``, passed as CMAKE_PROJECT_INCLUDE. Upstream's
    top-level CMakeLists.txt sets, before project(),
    ``set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")``
    ("Link MSVC runtime statically"). A normal variable shadows the cache
    entry, so ``-DCMAKE_MSVC_RUNTIME_LIBRARY=...`` on the command line cannot
    change it, and the corpus builds /MD. CMAKE_PROJECT_INCLUDE is read as the
    last step of project(), so the file sets the variable again to
    ``MultiThreadedDLL`` for every target created afterwards. No upstream
    file is edited.

``names <build_dir>``

  Prints the evidence the exclusion table is checked against: the functions
  defined (dumpbin /symbols, External or Static, type ``()`` in a code
  section) in the vendored static libraries and objects of this very build -
  liboqs, the OQS provider and blake2s - and in none of SoftEther's own
  libraries (mayaqua.lib, cedar.lib, libhamcore), the membership test the
  Linux and MinGW legs use. Lines are ``VENDOR <library> <name>``,
  ``OWN <count>`` and ``CONFLICT <name>``; nothing is written to disk.
"""

import os
import re
import subprocess
import sys


_TRIPLET = """\
set(VCPKG_TARGET_ARCHITECTURE %s)
set(VCPKG_CRT_LINKAGE dynamic)
set(VCPKG_LIBRARY_LINKAGE dynamic)
set(VCPKG_BUILD_TYPE release)
"""

_RUNTIME = """\
# SoftEther VPN 5.x MSVC leg: see scripts/corpus/softether5_msvc.py
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")
"""

# 0AB 00000000 SECT3  notype ()    External     | OQS_init
_SYMBOL = re.compile(
    r"^\s*[0-9A-Fa-f]+ [0-9A-Fa-f]+ +SECT[0-9A-Fa-f]+ +\w+ +\(\) +"
    r"(?:External|Static) +\| (\S+)")

_OWN = ("mayaqua", "cedar", "libhamcore", "hamcore")
_VENDOR_LIBS = {"oqs": "liboqs", "oqs-internal": "liboqs",
                "oqsprovider": "liboqs-provider"}


def prepare(source_root, arch):
    triplets = os.path.join(source_root, "vcpkg-triplets")
    os.makedirs(triplets, exist_ok=True)
    with open(os.path.join(triplets, "se-%s-windows-release.cmake" % arch),
              "w", encoding="utf-8", newline="\n") as handle:
        handle.write(_TRIPLET % arch)
    with open(os.path.join(source_root, "se-msvc-runtime.cmake"), "w",
              encoding="utf-8", newline="\n") as handle:
        handle.write(_RUNTIME)


def _defined(path):
    out = subprocess.run(["dumpbin", "/nologo", "/symbols", path],
                         capture_output=True, text=True, errors="replace")
    names = set()
    for line in out.stdout.splitlines():
        match = _SYMBOL.match(line)
        if match:
            names.add(match.group(1))
    return names


def names(build_dir):
    libs, objs = [], []
    for dirpath, _, files in os.walk(build_dir):
        for name in files:
            full = os.path.join(dirpath, name)
            stem = name.rsplit(".", 1)[0]
            if name.endswith(".lib"):
                libs.append((stem, full))
            elif name.endswith(".obj") and stem.lower().startswith("blake2s"):
                objs.append((stem, full))
    print("LIBS " + " ".join(sorted(s for s, _ in libs)))
    vendor = {}
    own = set()
    for stem, full in sorted(libs):
        if stem in _VENDOR_LIBS:
            vendor.setdefault(_VENDOR_LIBS[stem], set()).update(_defined(full))
        elif stem.lower() in _OWN or stem.lower().startswith(_OWN):
            own |= _defined(full)
    for stem, full in objs:
        vendor.setdefault("BLAKE2", set()).update(_defined(full))
    # blake2s.c is compiled straight into cedar.lib, so its names are in the
    # library the OWN set is read from; they are the vendor's, not SoftEther's.
    own -= vendor.get("BLAKE2", set())
    print("OWN %d" % len(own))
    for lib in sorted(vendor):
        clean = sorted(vendor[lib] - own)
        print("VENDOR-COUNT %s %d" % (lib, len(clean)))
        for name in clean:
            print("VENDOR %s %s" % (lib, name))
        for name in sorted(vendor[lib] & own):
            print("CONFLICT %s" % name)


def main(argv):
    if argv[1] == "prepare":
        prepare(argv[2], argv[3])
    elif argv[1] == "names":
        names(argv[2])
    else:
        raise SystemExit("usage: softether5_msvc.py prepare <source_root> <arch> | names <build_dir>")


if __name__ == "__main__":
    main(sys.argv)
