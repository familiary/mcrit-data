"""Install the WDK that still has x86 kernel-mode libraries, on a Windows runner.

WDK 10.0.26100.0, the kit on the windows-2022 image, ships no Lib\\<ver>\\km\\x86
directory and its msbuild targets reject Win32 kernel drivers ("'Win32' is not a
valid architecture for Kernel mode drivers or UMDF drivers"). The NuGet package
Microsoft.Windows.WDK.x86 (10.0.26100.1 through 10.0.28000.x) was inspected and
carries no km libraries either: its only .lib files are KMDF's wdfldr and
wdfdriverentry and four um stubs. The last kit that carries the x86 kernel
libraries is WDK 10.0.22621, so the x86 driver recipes install that one beside
the kit that is already there. Nothing is replaced: the kits live in separate
Include\\Lib\\build version directories, and the x64 recipes keep naming
10.0.26100.0 explicitly.

What is pinned: the installer stub, by URL and sha256. The stub downloads its
payload from Microsoft at install time, which this script cannot pin; the
version it installs is fixed by the stub (10.1.22621.382).

Never fakes anything: if the libraries are not there afterwards the script exits
non-zero and the recipe fails with the log of the installer.
"""

import hashlib
import glob
import os
import subprocess
import sys
import urllib.request

KIT = "10.0.22621.0"
STUB_URL = ("https://download.microsoft.com/download/c/6/4/"
            "c64e8e90-4143-4e86-93d7-0209b0b30626/wdk/wdksetup.exe")
STUB_SHA256 = "f3948d1486f8a7821bcef431487d3893fcd3a053d97ab37a1333a0c26e0bd232"
REQUIRED_LIBS = ("ntoskrnl.lib", "hal.lib", "wdmsec.lib", "fltmgr.lib",
                 "BufferOverflowK.lib", "BufferOverflowFastFailK.lib")


def sdk_root():
    base = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    return os.path.join(base, "Windows Kits", "10")


def missing():
    root = sdk_root()
    lib = os.path.join(root, "Lib", KIT, "km", "x86")
    need = [os.path.join(lib, name) for name in REQUIRED_LIBS]
    need.append(os.path.join(root, "Include", KIT, "km", "ntddk.h"))
    return [path for path in need if not os.path.isfile(path)]


def inventory(label):
    root = sdk_root()
    print("---- %s ----" % label)
    for sub in ("Include", "Lib"):
        found = sorted(os.path.basename(p) for p in
                       glob.glob(os.path.join(root, sub, "10.*")))
        print("%s versions: %s" % (sub, ", ".join(found) or "none"))
    for path in sorted(glob.glob(os.path.join(root, "Lib", "10.*", "km", "*"))):
        print("km libs dir: %s" % path)
    print("-------------------")
    sys.stdout.flush()


def run(command, log=None):
    print("$ %s" % " ".join(command))
    sys.stdout.flush()
    result = subprocess.run(command)
    print("exit code %d" % result.returncode)
    if log and os.path.isfile(log):
        with open(log, errors="replace") as handle:
            lines = handle.read().splitlines()
        print("---- last 60 lines of %s ----" % log)
        print("\n".join(lines[-60:]))
    sys.stdout.flush()
    return result.returncode


def main():
    inventory("before")
    todo = missing()
    if not todo:
        print("WDK %s x86 kernel libraries already present" % KIT)
        return 0
    print("missing: %s" % ", ".join(todo))

    temp = os.environ.get("RUNNER_TEMP") or os.environ.get("TEMP") or "."
    stub = os.path.join(temp, "wdksetup-%s.exe" % KIT)
    log = os.path.join(temp, "wdksetup-%s.log" % KIT)
    with urllib.request.urlopen(STUB_URL, timeout=300) as response:
        data = response.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != STUB_SHA256:
        print("installer stub sha256 %s does not match the pin %s"
              % (digest, STUB_SHA256))
        return 2
    with open(stub, "wb") as handle:
        handle.write(data)
    print("installer stub sha256 verified: %s" % digest)

    run([stub, "/quiet", "/norestart", "/log", log], log)
    todo = missing()
    if todo:
        # Second route: the Chocolatey package is the same kit.
        print("after wdksetup, still missing: %s" % ", ".join(todo))
        inventory("after wdksetup")
        run(["choco", "install", "windowsdriverkit11", "-y", "--no-progress"])
        todo = missing()
    inventory("after")
    if todo:
        print("the WDK %s x86 kernel libraries are not available: %s"
              % (KIT, ", ".join(todo)))
        return 1
    print("WDK %s x86 kernel libraries installed" % KIT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
