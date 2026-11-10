#!/usr/bin/env python3
"""Build GnuTLS's libgnutls with cl, with GMP and Nettle as separate static libraries.

GnuTLS documents MinGW for Windows, not MSVC. Unlike GMP and Nettle it cannot
be built from a hand-written configuration: it carries about 240 gnulib
replacement files whose configure results drive the whole build. So the one
part of this build that is GnuTLS's own is its own ``configure``, run for cl
the way the GNU project documents running it (and gnulib's INSTALL.windows
documents for libunistring): through MSYS2's bash, with automake's ``compile``
and ``ar-lib`` wrappers in front of cl and lib. MSYS2 (or Git-bash) is used
only for configure and make; every object is compiled by cl.

Order, as the Linux and MinGW recipes build it:

  1. GMP 6.3.0 as a static gmp.lib, by gmp_msvc_build.py --static (the same
     no-assembly build that the GMP family's MSVC recipe produces as a DLL).
  2. Nettle 3.10.2 as static nettle.lib and hogweed.lib against that GMP, not
     mini-gmp: config.h and version.h are written the way
     nettle_msvc_build.py writes them (NETTLE_USE_MINI_GMP 0, the real
     GMP_NUMB_BITS), the ecc-*.h tables come from its eccdata.c rules with the
     real limb width, the source lists are read out of Makefile.in and
     libhogweed does not take mini-gmp.c. The public headers go to
     <prefix>/include/nettle.
  3. GnuTLS ``configure`` under bash, the same options as the Linux and MinGW
     recipes (bundled libtasn1 and libunistring, no p11-kit, zlib, brotli,
     zstd, TPM, idn, docs, tests, tools, C++ or DANE) plus
     --disable-hardware-acceleration (the x86 and x86_64 accelerated back
     ends are GNU-as assembly), --disable-shared --enable-static (libtool's
     DLL link for cl is not what is wanted: the link flags are the corpus's),
     and build = host = <arch>-w64-mingw32 so that configure runs the
     programs it compiles instead of guessing. Nettle and GMP are found
     through NETTLE_*/HOGWEED_* variables, as in the Linux recipe, not
     pkg-config.
  4. ``make -C gl`` and ``make -C lib``; libtool leaves lib/.libs/libgnutls.a,
     one archive holding the objects of lib/ and of every convenience library
     (gnulib, x509, auth, ext, algorithms, extras, hpke, accelerated, nettle
     glue, libtasn1, libunistring).
  5. That archive is linked to libgnutls-30.dll with the corpus flags:
     /WHOLEARCHIVE of the GnuTLS archive (libtool's convenience libraries are
     linked whole, too), gmp.lib, hogweed.lib and nettle.lib as ordinary
     archives (only the members that are referenced come in, as with the
     static libraries of the Linux and MinGW builds), exports generated from
     the objects with the rule of lib/Makefile.am for linkers without a
     version script: ``^(gnutls|_gnutls).*``.

The statics of the three helper libraries (symbols with storage class Static
in gmp.lib, nettle.lib and hogweed.lib) are listed in the log, so that the
recipe's exclusion list can be checked against what cl really produced.

Every command is echoed before it runs; configure's config.log and the make
errors are printed when a step fails.
"""

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nettle_msvc_build as nb  # noqa: E402


def run(command, **kwargs):
    print("> " + " ".join(command), flush=True)
    subprocess.run(command, check=True, **kwargs)


def extract(archive, destination):
    os.makedirs(destination, exist_ok=True)
    with tarfile.open(archive) as handle:
        try:
            handle.extractall(destination, filter="data")
        except TypeError:
            handle.extractall(destination)
    entries = [e for e in os.listdir(destination) if not e.startswith(".")]
    if len(entries) != 1:
        raise SystemExit("%s: expected one top-level directory" % archive)
    return os.path.join(destination, entries[0])


def limb_bits(arch):
    return "64" if arch == "x64" else "32"


def build_gmp(archive, deps, arch):
    source = extract(archive, os.path.join(deps, "src-gmp"))
    run([sys.executable, os.path.join(HERE, "gmp_msvc_build.py"),
         "--arch", arch, "--src", source,
         "--work", os.path.join(deps, "gmp-build"),
         "--static", "--prefix", os.path.join(deps, "prefix")])


def nettle_version_h(numb_bits):
    with open("configure.ac", encoding="utf-8") as handle:
        init = re.search(r"AC_INIT\(\[nettle\],\s*\[(\d+)\.(\d+)", handle.read())
    values = {"MAJOR_VERSION": init.group(1), "MINOR_VERSION": init.group(2),
              "NETTLE_USE_MINI_GMP": "0", "GMP_NUMB_BITS": numb_bits}
    with open("version.h.in", encoding="utf-8") as handle:
        text = handle.read()
    text = re.sub(r"@(\w+)@", lambda m: values[m.group(1)], text)
    with open(os.path.join("gen", "version.h"), "w", encoding="utf-8") as out:
        out.write(text)


def archive(name, sources, flags, objdir):
    os.makedirs(objdir, exist_ok=True)
    with open(name + ".rsp", "w") as handle:
        handle.write("\n".join(sources) + "\n")
    run(["cl", "/nologo", "/c", "/O2", "/MD", "/Z7", "/Fo%s\\" % objdir]
        + flags + ["@%s.rsp" % name])
    objects = sorted(glob.glob(os.path.join(objdir, "*.obj")))
    if len(objects) != len(sources):
        raise SystemExit("%s: %d sources but %d objects"
                         % (name, len(sources), len(objects)))
    with open(name + "_obj.rsp", "w") as handle:
        handle.write("\n".join(objects) + "\n")
    run(["lib", "/nologo", "/OUT:%s.lib" % name, "@%s_obj.rsp" % name])


def build_nettle(archive_path, deps, arch):
    prefix = os.path.abspath(os.path.join(deps, "prefix"))
    source = extract(archive_path, os.path.join(deps, "src-nettle"))
    numb = limb_bits(arch)
    previous = os.getcwd()
    os.chdir(source)
    try:
        os.makedirs("gen", exist_ok=True)
        with open("Makefile.in", encoding="utf-8") as handle:
            makefile = handle.read()
        nettle = nb.read_list(makefile, "nettle_SOURCES")
        hogweed = nb.read_list(makefile, "hogweed_SOURCES")
        if not nettle or not hogweed:
            raise SystemExit("could not read the source lists from Makefile.in")
        nettle += nb.replaced_functions(nettle)
        print("%d libnettle sources, %d libhogweed sources"
              % (len(nettle), len(hogweed)), flush=True)
        nb.write_config(arch, True)
        nettle_version_h(numb)
        nb.write_stdint()
        flags = ["/Igen", "/I.", "/I" + os.path.join(prefix, "include"),
                 "/DHAVE_CONFIG_H=1", "/D_CRT_SECURE_NO_WARNINGS", "/utf-8"]
        with open("nettle-types.h", encoding="utf-8") as handle:
            if "stdalign.h" in handle.read():
                flags += ["/std:c11", "/D_CRT_DECLARE_NONSTDC_NAMES=1"]
        nb.LIMB_BITS = numb
        nb.write_ecc_tables(makefile, flags)
        archive("nettle", nettle, flags, "obj_nettle")
        archive("hogweed", hogweed, flags, "obj_hogweed")
        headers = re.search(r"^HEADERS\s*=((?:[^\n]*\\\n)*[^\n]*)", makefile,
                            re.M).group(1).replace("\\\n", " ").split()
        target = os.path.join(prefix, "include", "nettle")
        os.makedirs(target, exist_ok=True)
        for header in [h for h in headers if h.endswith(".h")] + ["version.h"]:
            origin = os.path.join("gen", header) if header == "version.h" \
                else header
            shutil.copyfile(origin, os.path.join(target, header))
        os.makedirs(os.path.join(prefix, "lib"), exist_ok=True)
        for name in ("nettle", "hogweed"):
            shutil.copyfile(name + ".lib", os.path.join(prefix, "lib", name + ".lib"))
        print("nettle: %d headers, nettle.lib and hogweed.lib under %s"
              % (len(headers) + 1, prefix), flush=True)
    finally:
        os.chdir(previous)


def statics(path):
    """Names of the file-local functions in a static library."""
    out = subprocess.check_output(["dumpbin", "/SYMBOLS", path]).decode(
        "utf-8", "replace")
    names = set()
    for line in out.splitlines():
        tokens = line.split()
        if ("|" in tokens and "Static" in tokens and "()" in tokens
                and any(t.startswith("SECT") for t in tokens)):
            names.add(tokens[tokens.index("|") + 1])
    return sorted(names)


DIRENT_H = r"""/* Header-only dirent for the one place GnuTLS needs it (lib/x509/verify-high2.c
   loads a directory of CA files with opendir/readdir/closedir); the Windows
   SDK has none and the GnuTLS gl/ tree does not carry gnulib's dirent module.
   Written by gnutls_msvc_build.py into the build tree, not part of GnuTLS. */
#ifndef MCRIT_SHIM_DIRENT_H
#define MCRIT_SHIM_DIRENT_H
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>
struct dirent { char d_name[MAX_PATH]; };
typedef struct mcrit_shim_dir {
  HANDLE handle; WIN32_FIND_DATAA data; int first; struct dirent entry;
} DIR;
static __inline DIR *opendir(const char *name)
{
  char pattern[MAX_PATH + 3];
  size_t n = strlen(name);
  DIR *dir;
  if (n + 3 > sizeof(pattern)) return NULL;
  memcpy(pattern, name, n);
  if (n && name[n - 1] != '/' && name[n - 1] != '\\') pattern[n++] = '\\';
  pattern[n++] = '*';
  pattern[n] = 0;
  dir = (DIR *)malloc(sizeof(*dir));
  if (!dir) return NULL;
  dir->handle = FindFirstFileA(pattern, &dir->data);
  if (dir->handle == INVALID_HANDLE_VALUE) { free(dir); return NULL; }
  dir->first = 1;
  return dir;
}
static __inline struct dirent *readdir(DIR *dir)
{
  if (dir->first) dir->first = 0;
  else if (!FindNextFileA(dir->handle, &dir->data)) return NULL;
  lstrcpynA(dir->entry.d_name, dir->data.cFileName, MAX_PATH);
  return &dir->entry;
}
static __inline int closedir(DIR *dir)
{
  FindClose(dir->handle);
  free(dir);
  return 0;
}
#endif
"""

# Force-included (cl -FI) for the make phase only. GnuTLS 3.8.13 has MSVC
# branches for most GNU-isms and misses three: audit.c uses _Thread_local
# without including gthreads.h (which would define it), global.c puts
# __attribute__((constructor)) on its init functions unconditionally, and
# crau.h leaves CRAU_MAYBE_UNUSED undefined for compilers that are neither GCC
# nor C23. The definitions below are exactly what the tree's own MSVC branches
# and non-GCC fallbacks use elsewhere; no upstream file is modified.
SHIM_H = """/* Written by gnutls_msvc_build.py; force-included with cl -FI. */
#ifndef MCRIT_SHIM_MSVC_H
#define MCRIT_SHIM_MSVC_H
#define _Thread_local __declspec(thread)
#define __attribute__(x)
#define CRAU_MAYBE_UNUSED
#endif
"""


def write_shims(deps):
    directory = os.path.join(deps, "shim")
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, "dirent.h"), "w") as handle:
        handle.write(DIRENT_H)
    with open(os.path.join(directory, "msvc_shim.h"), "w") as handle:
        handle.write(SHIM_H)
    return directory


def find_bash():
    for candidate in (r"C:\msys64\usr\bin\bash.exe",
                      r"C:\Program Files\Git\bin\bash.exe",
                      r"C:\Program Files\Git\usr\bin\bash.exe"):
        if os.path.exists(candidate):
            return candidate
    found = shutil.which("bash")
    if not found:
        raise SystemExit("no bash on this machine")
    return found


CONFIGURE_OPTIONS = (
    "--disable-shared --enable-static --with-included-libtasn1 "
    "--with-included-unistring --without-p11-kit --without-idn --without-zlib "
    "--without-brotli --without-zstd --without-tpm --without-tpm2 --disable-doc "
    "--disable-tests --disable-tools --disable-cxx --disable-libdane "
    "--disable-nls --disable-guile --disable-hardware-acceleration "
    "--disable-dependency-tracking --disable-rpath --disable-gtk-doc")

SCRIPT = r'''
set -u
export PATH="$(cygpath -u "$MSVC_BIN"):$PATH"
SRC="$(cygpath -u "$SRC_WIN")"
D="$(cygpath -u "$DEPS_WIN")"
SHIM="$(cygpath -u "$SHIM_WIN")"
SHIM_M="$(cygpath -m "$SHIM_WIN")"
echo "bash: $(command -v bash)  cl: $(command -v cl)  link: $(command -v link)"
if ! command -v make >/dev/null 2>&1 || ! command -v m4 >/dev/null 2>&1; then
  echo "installing make and m4 with pacman"
  pacman -Sy --noconfirm --needed make m4 diffutils || exit 90
fi
echo "make: $(command -v make)  sed: $(command -v sed)  awk: $(command -v awk)"
export CC="$SRC/build-aux/compile cl -nologo"
export CXX="$CC"
export CFLAGS="-MD -O2 -Z7 -utf-8"
export CPPFLAGS="-I$D/include -D_CRT_SECURE_NO_WARNINGS -D_CRT_NONSTDC_NO_WARNINGS"
export LDFLAGS="-L$D/lib"
export LD=link
export NM="dumpbin -symbols"
export STRIP=:
export RANLIB=:
export AR="$SRC/build-aux/ar-lib lib"
export DLLTOOL=: OBJDUMP=: AS=: RC=: WINDRES=:
export NETTLE_CFLAGS="-I$D/include" NETTLE_LIBS="-L$D/lib -lnettle"
export HOGWEED_CFLAGS="-I$D/include" HOGWEED_LIBS="-L$D/lib -lhogweed -lnettle -lgmp"
mkdir -p build && cd build
"$SRC/configure" --build=$TRIPLE --host=$TRIPLE ''' + CONFIGURE_OPTIONS + r''' || {
  echo "=== configure failed (exit $?); config.log tail follows"
  tail -n 150 config.log
  exit 91
}
JOBS="$(nproc 2>/dev/null || echo 2)"
make -k -j"$JOBS" -C gl CPPFLAGS="$CPPFLAGS -I$SHIM -FI$SHIM_M/msvc_shim.h" > make-gl.log 2>&1
echo "=== make -C gl (exit $?)"; cat make-gl.log
echo "=== gl errors:"; grep -nE "error C[0-9]+|fatal error|\*\*\*|Error [0-9]" make-gl.log | head -300
test -f gl/libgnu.la && echo "=== gl/libgnu.la built" || echo "=== gl/libgnu.la was NOT built; lib is built anyway to collect its errors"
make -k -j"$JOBS" -C lib CPPFLAGS="$CPPFLAGS -I$SHIM -FI$SHIM_M/msvc_shim.h" > make-lib.log 2>&1
echo "=== make -C lib (exit $?)"; cat make-lib.log
echo "=== lib errors:"; grep -nE "error C[0-9]+|fatal error|\*\*\*|Error [0-9]" make-lib.log | head -600
ls -l lib/.libs | head -20
test -f lib/.libs/libgnutls.a -o -f lib/.libs/libgnutls.lib || { echo "=== libgnutls static archive was not built"; exit 93; }
echo "=== libgnutls static archive built"
'''


def configure_and_make(source, deps, arch):
    triple = "x86_64-w64-mingw32" if arch == "x64" else "i686-w64-mingw32"
    cl = shutil.which("cl")
    if not cl:
        raise SystemExit("cl is not on PATH")
    env = dict(os.environ)
    env.update({
        "MSVC_BIN": os.path.dirname(cl),
        "SRC_WIN": source,
        "DEPS_WIN": os.path.abspath(os.path.join(deps, "prefix")),
        "SHIM_WIN": write_shims(deps),
        "TRIPLE": triple,
        "MSYSTEM": "MSYS",
        "MSYS2_PATH_TYPE": "inherit",
        "CHERE_INVOKING": "1",
        "MSYS2_ENV_CONV_EXCL": "INCLUDE;LIB;LIBPATH;CL;_CL_;LINK;_LINK_",
    })
    command = [find_bash(), "-lc", SCRIPT]
    print("> %s -lc <configure and make script for %s>" % (command[0], triple),
          flush=True)
    result = subprocess.run(command, env=env)
    if result.returncode != 0:
        raise SystemExit("configure/make of GnuTLS failed (exit %d)"
                         % result.returncode)


def members(path):
    out = subprocess.check_output(["lib", "/nologo", "/LIST", path]).decode(
        "utf-8", "replace")
    return [line for line in out.splitlines() if line.strip()]


def link_dll(arch, prefix_lib):
    found = glob.glob(os.path.join("build", "lib", ".libs", "libgnutls.a")) \
        + glob.glob(os.path.join("build", "lib", ".libs", "libgnutls.lib"))
    if not found:
        raise SystemExit("libtool left no libgnutls archive in build/lib/.libs")
    archive_path = os.path.abspath(found[0])
    shutil.copyfile(archive_path, "libgnutls_static.lib")
    whole = ["libgnutls_static.lib"]
    # libtool merges the convenience libraries into a static library; check
    # that it did, and link the ones it did not as whole archives too.
    merged = len(members("libgnutls_static.lib"))
    others = [path for path in
              glob.glob(os.path.join("build", "**", ".libs", "*.a"), recursive=True)
              + glob.glob(os.path.join("build", "**", ".libs", "*.lib"), recursive=True)
              if os.path.abspath(path) != archive_path]
    counts = {path: len(members(path)) for path in others}
    print("libgnutls archive: %d members; convenience libraries: %s"
          % (merged, ", ".join("%s=%d" % (os.path.relpath(p, "build"), n)
                                for p, n in sorted(counts.items()))), flush=True)
    if merged < sum(counts.values()):
        print("the archive does not hold the convenience libraries: linking "
              "them whole as well", flush=True)
        for index, path in enumerate(sorted(others)):
            copy = "conv%d.lib" % index
            shutil.copyfile(path, copy)
            whole.append(copy)
    names = set()
    out = subprocess.check_output(["dumpbin", "/SYMBOLS",
                                   "libgnutls_static.lib"]).decode(
                                       "utf-8", "replace")
    for line in out.splitlines():
        tokens = line.split()
        if not ("|" in tokens and "External" in tokens
                and any(t.startswith("SECT") for t in tokens)
                and "()" in tokens):
            continue
        name = tokens[tokens.index("|") + 1]
        if arch == "x86" and name.startswith("_"):
            name = name[1:]
        if re.match(r"^(gnutls|_gnutls)", name):
            names.add(name)
    if not names:
        raise SystemExit("no gnutls exports found in libgnutls_static.lib")
    with open("libgnutls-30.def", "w") as handle:
        handle.write("EXPORTS\n" + "\n".join(sorted(names)) + "\n")
    print("libgnutls-30.def: %d exports" % len(names), flush=True)
    system = ["ws2_32.lib", "crypt32.lib", "bcrypt.lib", "advapi32.lib",
              "ncrypt.lib", "user32.lib", "secur32.lib", "shell32.lib"]
    command = ["link", "/nologo", "/DLL", "/DEBUG", "/Brepro", "/INCREMENTAL:NO",
               "/OPT:NOREF", "/OPT:NOICF", "/DEF:libgnutls-30.def",
               "/PDB:libgnutls-30.pdb", "/OUT:libgnutls-30.dll",
               "/LIBPATH:" + prefix_lib,
               ] + ["/WHOLEARCHIVE:" + name for name in whole] + whole + [
               "hogweed.lib", "nettle.lib", "gmp.lib"] + system
    print("> " + " ".join(command), flush=True)
    result = subprocess.run(command, capture_output=True, text=True)
    print(result.stdout[-300000:] + result.stderr[-300000:], flush=True)
    if result.returncode != 0:
        raise SystemExit("link of libgnutls-30.dll failed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--arch", required=True, choices=("x86", "x64"))
    parser.add_argument("--gmp-archive", required=True)
    parser.add_argument("--nettle-archive", required=True)
    parser.add_argument("--src", default=".", help="the unpacked gnutls tree")
    args = parser.parse_args()

    source = os.path.abspath(args.src)
    deps = os.path.abspath("deps")
    os.makedirs(deps, exist_ok=True)
    build_gmp(args.gmp_archive, deps, args.arch)
    build_nettle(args.nettle_archive, deps, args.arch)
    prefix_lib = os.path.join(deps, "prefix", "lib")
    for name in ("gmp", "nettle", "hogweed"):
        listing = statics(os.path.join(prefix_lib, name + ".lib"))
        print("STATICS %s.lib (%d): %s" % (name, len(listing), " ".join(listing)),
              flush=True)
    configure_and_make(source, deps, args.arch)
    link_dll(args.arch, prefix_lib)
    print("done")


if __name__ == "__main__":
    sys.exit(main())
