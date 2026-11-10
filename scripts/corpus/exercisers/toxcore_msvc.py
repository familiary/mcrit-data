"""Windows-side helper for the c-toxcore MSVC recipes.

Two jobs, both because c-toxcore's CMake build assumes things a bare
windows-2022 runner does not provide, and neither can be solved by a CMake
flag alone. Nothing here touches the upstream tree.

prepare <libsodium-dir> <pthreads4w-dir> <out-dir> [legacy]
    Writes, under <out-dir>:
      * unofficial-sodium/unofficial-sodium-config.cmake, an imported target
        pointing at the libsodium this recipe built from the pinned release
        tarball. On MSVC cmake/Dependencies.cmake looks libsodium up through
        find_package(unofficial-sodium), which is vcpkg's package name; the
        runner has no vcpkg tree this recipe controls, so the same target is
        supplied from the pinned build instead.
      * pthreads4w/pthreads4w-config.cmake, the same for pthreads4w built
        from its pinned release: toxcore uses pthread_rwlock and friends at
        every release, and Windows has no pthread.h. It defines the target
        newer releases look for and the variables older ones read.
      * pkg-config.bat, a stub. Dependencies.cmake runs
        find_package(PkgConfig REQUIRED) on every platform, and pkg-config is
        not part of a Visual Studio environment. The stub answers --version
        and reports every module as not found, which is also what makes the
        result independent of anything the runner happens to have installed:
        opus, libvpx and libconfig are all absent by construction.

link <build-dir> <out-dir> <libsodium-dir> <pthreads4w-dir> <x86|x64>
    Re-links c-toxcore's DLL from the objects CMake compiled, leaving the
    vendored cmp (third_party/cmp/cmp.c, TokTok/cmp) out. cmp is linked on its
    own into a throwaway cmp.dll whose import library resolves the references,
    so what is written to <out-dir>/toxcore.dll holds c-toxcore's own code and
    imports cmp the same way it imports libsodium. data/cmp is its own family
    and a copy of its functions here would be attributed twice.

    Exports: toxcore ships no export macros, and link has no export-all mode,
    so each DLL is given a .def listing the defined external functions of its
    own objects, read from dumpbin /SYMBOLS - the method cmp_msvc.py uses.

With "legacy", prepare also lays libsodium and pthreads out where releases up to
0.2.18 look for them (third_party/libsodium/<Win32|x64>/Release/v140/dynamic
and third_party/pthreads-win32/Pre-built.2, named in their cmake/Dependencies
.cmake). Those are dependency locations upstream documents for its MSVC build,
filled from the pinned builds; no upstream file is edited.
"""

import glob
import os
import shutil
import subprocess
import sys


def _find_one(pattern):
    found = glob.glob(pattern)
    if len(found) != 1:
        sys.exit("expected exactly one %s, found %r" % (pattern, found))
    return found[0]


def prepare(sodium_dir, pth_dir, out_dir, legacy):
    sodium_dir = os.path.abspath(sodium_dir)
    pth_dir = os.path.abspath(pth_dir)
    out_dir = os.path.abspath(out_dir)
    sodium_dll = _find_one(os.path.join(
        sodium_dir, "bin", "*", "Release", "v143", "dynamic", "libsodium.dll"))
    sodium_lib = sodium_dll[:-4] + ".lib"
    sodium_inc = os.path.join(sodium_dir, "src", "libsodium", "include")
    pth_dll = _find_one(os.path.join(pth_dir, "pthreadVC3.dll"))
    pth_lib = pth_dll[:-4] + ".lib"
    for path in (sodium_lib, os.path.join(sodium_inc, "sodium.h"),
                 os.path.join(sodium_inc, "sodium", "version.h"),
                 pth_lib, os.path.join(pth_dir, "pthread.h")):
        if not os.path.exists(path):
            sys.exit("missing %s" % path)

    def cm(path):
        return path.replace("\\", "/")

    os.makedirs(os.path.join(out_dir, "unofficial-sodium"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "pthreads4w"), exist_ok=True)
    with open(os.path.join(out_dir, "unofficial-sodium",
                           "unofficial-sodium-config.cmake"), "w") as out:
        out.write("add_library(unofficial-sodium::sodium SHARED IMPORTED)\n"
                  "set_target_properties(unofficial-sodium::sodium PROPERTIES\n"
                  '  IMPORTED_LOCATION "%s"\n'
                  '  IMPORTED_IMPLIB "%s"\n'
                  '  INTERFACE_INCLUDE_DIRECTORIES "%s")\n'
                  % (cm(sodium_dll), cm(sodium_lib), cm(sodium_inc)))
    with open(os.path.join(out_dir, "pthreads4w",
                           "pthreads4w-config.cmake"), "w") as out:
        out.write("add_library(pthreads4w::pthreads4w SHARED IMPORTED)\n"
                  "set_target_properties(pthreads4w::pthreads4w PROPERTIES\n"
                  '  IMPORTED_LOCATION "%s"\n'
                  '  IMPORTED_IMPLIB "%s"\n'
                  '  INTERFACE_INCLUDE_DIRECTORIES "%s")\n'
                  'set(pthreads4w_FOUND TRUE)\n'
                  'set(pthreads4w_INCLUDE_DIR "%s")\n'
                  'set(pthreads4w_LIBRARIES "%s")\n'
                  % (cm(pth_dll), cm(pth_lib), cm(pth_dir), cm(pth_dir),
                     cm(pth_lib)))
    with open(os.path.join(out_dir, "pkg-config.bat"), "w") as out:
        out.write('@if "%1"=="--version" (echo 0.29.2& exit /b 0)\r\n@exit /b 1\r\n')
    if legacy:
        plat = "x64" if os.path.basename(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(sodium_dll))))) == "x64" else "Win32"
        dyn = os.path.join("third_party", "libsodium", plat, "Release",
                           "v140", "dynamic")
        os.makedirs(dyn, exist_ok=True)
        shutil.copy(sodium_lib, dyn)
        shutil.copy(sodium_dll, dyn)
        shutil.copytree(sodium_inc, os.path.join("third_party", "libsodium",
                                                 "include"), dirs_exist_ok=True)
        base = os.path.join("third_party", "pthreads-win32", "Pre-built.2")
        libdir = os.path.join(base, "lib", "x64" if plat == "x64" else "x86")
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(os.path.join(base, "include"), exist_ok=True)
        # The old layout names pthreadVC2; the import library is pthreads4w's
        # pthreadVC3 under that name, which is all find_library looks at.
        shutil.copy(pth_lib, os.path.join(libdir, "pthreadVC2.lib"))
        for header in ("pthread.h", "sched.h", "semaphore.h", "_ptw32.h"):
            shutil.copy(os.path.join(pth_dir, header),
                        os.path.join(base, "include", header))
    print("libsodium: %s\npthreads4w: %s" % (sodium_dll, pth_dll))


def exports(objects, x86):
    names = set()
    for obj in objects:
        text = subprocess.check_output(["dumpbin", "/SYMBOLS", obj]).decode(
            "utf-8", "replace")
        for line in text.splitlines():
            tokens = line.split()
            if ("|" in tokens and "()" in tokens and "External" in tokens
                    and any(t.startswith("SECT") for t in tokens)):
                name = tokens[tokens.index("|") + 1]
                if x86 and name.startswith("_"):
                    name = name[1:]
                names.add(name)
    return sorted(names)


def run(command):
    print(" ".join(command))
    sys.stdout.flush()
    subprocess.check_call(command)


def link(build_dir, out_dir, sodium_dir, pth_dir, arch):
    build_dir = os.path.abspath(build_dir)
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    objects = sorted(glob.glob(os.path.join(
        build_dir, "CMakeFiles", "toxcore_shared.dir", "**", "*.obj"),
        recursive=True))
    if not objects:
        sys.exit("no objects under %s" % build_dir)
    cmp_objects = [o for o in objects
                   if o.replace("\\", "/").endswith("third_party/cmp/cmp.c.obj")]
    rest = [o for o in objects if o not in cmp_objects]
    x86 = arch == "x86"
    sodium_lib = _find_one(os.path.join(
        os.path.abspath(sodium_dir), "bin", "*", "Release", "v143", "dynamic",
        "libsodium.lib"))
    pth_lib = os.path.join(os.path.abspath(pth_dir), "pthreadVC3.lib")
    print("%d objects, %d of them cmp" % (len(objects), len(cmp_objects)))
    common = ["/nologo", "/DLL", "/DEBUG", "/Brepro", "/INCREMENTAL:NO",
              "/OPT:NOREF", "/OPT:NOICF"]
    libs = []
    if cmp_objects:
        names = exports(cmp_objects, x86)
        assert names, "no cmp exports found"
        with open(os.path.join(out_dir, "cmp.def"), "w") as out:
            out.write("EXPORTS\n" + "\n".join(names) + "\n")
        run(["link"] + common + [
            "/DEF:" + os.path.join(out_dir, "cmp.def"),
            "/PDB:" + os.path.join(out_dir, "cmp.pdb"),
            "/OUT:" + os.path.join(out_dir, "cmp.dll"),
            "/IMPLIB:" + os.path.join(out_dir, "cmp.lib")] + cmp_objects)
        libs.append(os.path.join(out_dir, "cmp.lib"))
    names = exports(rest, x86)
    assert names, "no toxcore exports found"
    with open(os.path.join(out_dir, "toxcore.def"), "w") as out:
        out.write("EXPORTS\n" + "\n".join(names) + "\n")
    print("%d toxcore exports" % len(names))
    with open(os.path.join(out_dir, "objects.rsp"), "w") as out:
        out.write("\n".join('"%s"' % o for o in rest) + "\n")
    run(["link"] + common + [
        "/DEF:" + os.path.join(out_dir, "toxcore.def"),
        "/PDB:" + os.path.join(out_dir, "toxcore.pdb"),
        "/OUT:" + os.path.join(out_dir, "toxcore.dll"),
        "/IMPLIB:" + os.path.join(out_dir, "toxcore.lib"),
        "@" + os.path.join(out_dir, "objects.rsp")] + libs
        + [sodium_lib, pth_lib, "iphlpapi.lib", "ws2_32.lib"])


if __name__ == "__main__":
    if len(sys.argv) in (5, 6) and sys.argv[1] == "prepare":
        prepare(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:] == ["legacy"])
    elif len(sys.argv) == 7 and sys.argv[1] == "link":
        link(*sys.argv[2:])
    else:
        sys.exit(__doc__)
