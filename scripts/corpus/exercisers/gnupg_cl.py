"""Build libgpg-error or libgcrypt with cl, without running upstream's make.

Upstream is autotools only, and under MSYS2 on the windows-2022 runner its
Makefiles never get past remaking themselves (configure is re-run until the
job is killed), so no object is ever compiled. Everything `make` would
contribute is small and mechanical, and is reproduced here from upstream's
own generated files:

  * configure runs for real (gnupg_cl.sh, cl as the compiler, a *-mingw32*
    host triple because that is what selects the Windows code), producing
    config.h, gcrypt.h and the Makefiles;
  * the object list of each library is read from the generated Makefiles
    (am_*_OBJECTS), so it is upstream's list for that release and
    configuration, not a copy of it kept here;
  * the few files libgpg-error's Makefile generates with awk and with
    helper programs (code-to-errno.h, code-from-errno.h, gpg-error.h,
    gpgrt.h, gpg-error.def) are generated with the same awk scripts, the same
    helper sources and the same arguments, the helpers compiled with cl;
  * every translation unit is compiled with cl (/MD /O2 /Z7, no /GL) and the
    objects are linked into the DLL with the .def file upstream ships (or
    generates), /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF.

usage: gnupg_cl.py <x86|x64> <gpg-error|gcrypt> <source root> [<libgpg-error tarball>]

The environment variable GNUPG_CL_DIAG=1 additionally asks make, bounded, why
it remakes itself (output goes to the build log).
"""

import concurrent.futures
import glob
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time

MSYS = r"C:\msys64\usr\bin"
OPTS_GE = ["--disable-static", "--enable-shared", "--disable-doc",
           "--disable-tests", "--disable-languages", "--disable-nls"]
OPTS_GC = ["--disable-static", "--enable-shared", "--disable-doc", "--disable-asm"]
SYSLIBS = ["kernel32.lib", "advapi32.lib", "user32.lib", "ws2_32.lib",
           "shell32.lib", "ole32.lib"]

HERE = os.path.dirname(os.path.abspath(__file__))


def say(*a):
    print("[%s]" % time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def run(cmd, cwd=None, timeout=900, input=None, check=True, quiet=False, env=None, merge=True):
    """Run a command, return (rc, stdout-bytes). stderr is merged in."""
    t = time.time()
    p = subprocess.run(cmd, cwd=cwd, input=input, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT if merge else subprocess.DEVNULL, timeout=timeout, env=env)
    if not quiet:
        say("rc=%d %.1fs %s" % (p.returncode, time.time() - t,
                                " ".join(cmd) if isinstance(cmd, list) else cmd))
    if p.returncode and check:
        sys.stdout.write(p.stdout.decode("utf-8", "replace")[-3000:])
        raise SystemExit("command failed (%d): %s" % (p.returncode, cmd))
    return p.returncode, p.stdout


def fwd(p):
    return p.replace("\\", "/")


# ---------------------------------------------------------------- Makefiles

def parse_makefile(path):
    """Variables of an automake-generated Makefile, continuation lines joined."""
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    text = re.sub(r"\\\r?\n", " ", text)
    var = {}
    for line in text.splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(\+?=)\s*(.*)$", line)
        if not m:
            continue
        name, op, val = m.groups()
        var[name] = (var.get(name, "") + " " + val) if op == "+=" else val
    return var


def expand(var, s, depth=0):
    if depth > 20:
        return s
    def sub(m):
        return expand(var, var.get(m.group(1), ""), depth + 1)
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"\$[({]([A-Za-z0-9_]+)[)}]", sub, s)
    return s


def objects(var, *names):
    """Objects named by the given variables (am_*_OBJECTS, and the .lo files
    that a LIBADD adds, which is where configure-selected modules go)."""
    out = []
    for n in names:
        for t in expand(var, var.get(n, "")).split():
            if t.endswith(".lo") and t not in out:
                out.append(t)
    return out


def find_source(obj, dirs):
    """Source file for a libtool object name such as libgpg_error_la-init.lo."""
    base = obj[:-3] if obj.endswith(".lo") else os.path.splitext(obj)[0]
    cands = [base]
    m = re.match(r"^[A-Za-z0-9_]+_la-(.*)$", base)
    if m:
        cands.insert(0, m.group(1))
    for c in cands:
        for d in dirs:
            for ext in (".c", ".S", ".s", ".rc"):
                p = os.path.join(d, c + ext)
                if os.path.isfile(p):
                    return p
    return None


# --------------------------------------------------------------- compiling

class Cl:
    def __init__(self, arch):
        self.arch = arch

    def compile_cmd(self, src, obj, includes, defines, extra=()):
        cmd = ["cl", "/nologo", "/c", "/MD", "/O2", "/Z7", "/FS", "/utf-8",
               "/D_CRT_SECURE_NO_WARNINGS", "/D_CRT_NONSTDC_NO_WARNINGS",
               "/W1"]
        cmd += ["/I" + i for i in includes]
        cmd += ["/D" + d for d in defines]
        cmd += list(extra)
        cmd += ["/Fo" + obj, src]
        return cmd


def compile_all(srcs, builddir, includes, defines, extra_for=None, jobs=4, force=None):
    """Compile (src, objname, cwd) in parallel; return (objects, failures)."""
    cl = Cl(None)
    ok, bad = [], []

    def one(item):
        src, obj, cwd = item
        extra = list((extra_for or {}).get(os.path.basename(src), ()))
        if force:
            extra.append("/FI" + force)
        extra = list(extra)
        cmd = cl.compile_cmd(src, obj, includes(cwd), defines, extra)
        rc, out = run(cmd, cwd=cwd, timeout=600, check=False, quiet=True)
        text = out.decode("utf-8", "replace")
        if rc and "C1001" in text:
            # internal compiler error: record it, then try the same unit with
            # progressively less optimisation
            say("C1001 in %s, compiler said: %s" % (os.path.basename(src), " | ".join(
                l.strip() for l in text.splitlines() if "C1001" in l or "msc1" in l or "INTERNAL" in l)[:600]))
            for opt in (["/Od"], ["/O1"], ["/Od", "/GS-"]):
                cmd = cl.compile_cmd(src, obj, includes(cwd), defines, extra + opt)
                rc, out = run(cmd, cwd=cwd, timeout=600, check=False, quiet=True)
                text = out.decode("utf-8", "replace")
                say("C1001 in %s: recompiled with %s -> rc=%d" % (os.path.basename(src), " ".join(opt), rc))
                if rc == 0:
                    break
        return item, rc, text

    with concurrent.futures.ThreadPoolExecutor(jobs) as ex:
        for item, rc, out in ex.map(one, srcs):
            if rc == 0:
                ok.append(os.path.join(item[2], item[1]))
            else:
                errs = [l for l in out.splitlines() if re.search(r"error|fatal", l)]
                bad.append((item[0], errs[:12]))
    return ok, bad


def link_dll(out, objs, libs, deffile, implib=None, cwd=None):
    cmd = ["link", "/nologo", "/DLL", "/DEBUG", "/Brepro", "/INCREMENTAL:NO",
           "/OPT:NOREF", "/OPT:NOICF", "/OUT:" + out,
           "/PDB:" + os.path.splitext(out)[0] + ".pdb"]
    if deffile:
        cmd.append("/DEF:" + deffile)
    if implib:
        cmd.append("/IMPLIB:" + implib)
    cmd += objs + libs
    rc, o = run(cmd, cwd=cwd, timeout=900, check=False)
    sys.stdout.write(o.decode("utf-8", "replace")[-4000:])
    return rc


def report(tag, bad):
    say("%s: %d translation unit(s) failed to compile" % (tag, len(bad)))
    for src, errs in bad:
        print("  FAILED %s" % src)
        for e in errs:
            print("      " + e.strip()[:300])
    sys.stdout.flush()


# ------------------------------------------------------------- libgpg-error

def awk(awkfile, infile, args=(), stdin=None, cwd=None):
    exe = os.path.join(MSYS, "awk.exe")
    cmd = [exe] + list(args) + ["-f", fwd(awkfile)] + ([fwd(infile)] if infile else [])
    return run(cmd, cwd=cwd, input=stdin, quiet=True, merge=False)[1]


SHIM_H = r"""/* build-side compatibility for cl, written by gnupg_cl.py; upstream is not edited */
#ifndef GNUPG_CL_SHIM_H
#define GNUPG_CL_SHIM_H
#include <stddef.h>
#include <sys/types.h>
#include <io.h>
#include <process.h>
#include <direct.h>
#include <malloc.h>
#include <sys/stat.h>
/* gcrypt.h declares these two the same way for every non-GNU compiler */
typedef long ssize_t;
typedef int pid_t;
#ifndef F_OK
# define F_OK 0
# define X_OK 1
# define W_OK 2
# define R_OK 4
#endif
#ifndef S_ISREG
# define S_ISREG(m) (((m) & _S_IFMT) == _S_IFREG)
# define S_ISDIR(m) (((m) & _S_IFMT) == _S_IFDIR)
#endif
#ifndef S_IRUSR
# define S_IRUSR _S_IREAD
# define S_IWUSR _S_IWRITE
# define S_IXUSR _S_IEXEC
#endif
#ifndef STDIN_FILENO
# define STDIN_FILENO 0
# define STDOUT_FILENO 1
# define STDERR_FILENO 2
#endif
#endif
"""


def make_shim(work, gpgerr_macro_function):
    """Headers cl lacks (<unistd.h>, <sys/file.h>) and a forced-include file.

    GPGRT_HAVE_MACRO_FUNCTION: libgpg-error's gpg-error.h only defines it for
    GCC, but __FUNCTION__ is a cl builtin and visibility.c calls the internal
    assert function with three arguments when it is not defined (a four
    argument prototype), so the libgpg-error translation units get it
    defined, after gpg-error.h has been read, by the forced include."""
    d = os.path.join(work, "shim")
    os.makedirs(os.path.join(d, "sys"), exist_ok=True)
    with open(os.path.join(d, "gnupg_cl_shim.h"), "w") as f:
        f.write(SHIM_H)
    with open(os.path.join(d, "unistd.h"), "w") as f:
        f.write('#include "gnupg_cl_shim.h"\n')
    with open(os.path.join(d, "sys", "file.h"), "w") as f:
        f.write("/* empty */\n")
    with open(os.path.join(d, "sys", "time.h"), "w") as f:
        f.write("/* empty: the code that needs it is under HAVE_GETTIMEOFDAY */\n")
    with open(os.path.join(d, "gnupg_cl_fi.h"), "w") as f:
        f.write('#include "gnupg_cl_shim.h"\n')
    if gpgerr_macro_function:
        with open(os.path.join(d, "visibility_cl.c"), "w") as f:
            f.write('#include <config.h>\n#include <stdarg.h>\n#include <stdlib.h>\n'
                    '#define _GPGRT_INCL_BY_VISIBILITY_C 1\n#include "gpgrt-int.h"\n'
                    '#undef GPGRT_HAVE_MACRO_FUNCTION\n'
                    '#define GPGRT_HAVE_MACRO_FUNCTION 1\n#include "visibility.c"\n')
    return d


# ----------------------------------------------------------- build-tree edits
#
# cl has no variable-length arrays (C99 6.7.5.2), and these are the only
# places in the translation units that are built here that need them (found
# by compiling every one of them with gcc -Wvla). They are edited in the build
# tree, never in a committed tree, and every edit is printed as a unified diff
# into the build log. The image is therefore NOT byte-identical to a build of
# unmodified upstream. Each edit keeps the object's size and semantics:
#   * constant bound: the array size is rewritten as the constant expression
#     its operands already are (cipher-ccm.c: blocksize is the constant 16;
#     mpi/ec.c: wsize is (256 + BITS_PER_MPI_LIMB - 1) / BITS_PER_MPI_LIMB);
#   * run-time bound: the array becomes a pointer to _alloca() storage of the
#     same element count, which is what the compiler does for a VLA (function
#     lifetime, stack, no free) - sntrup761.c and mceliece6688128f.c.
# The arrays are never used with sizeof, which was checked.
PATCHES = [
    ("cipher/cipher-ccm.c",
     "  unsigned char tmp[blocksize];\n",
     "  unsigned char tmp[16]; /* blocksize */\n"),
    ("mpi/ec.c",
     "  mpi_limb_t n[wsize + 1];\n  mpi_limb_t s[wsize + 1];\n",
     "  mpi_limb_t n[(256 + BITS_PER_MPI_LIMB - 1) / BITS_PER_MPI_LIMB + 1];\n"
     "  mpi_limb_t s[(256 + BITS_PER_MPI_LIMB - 1) / BITS_PER_MPI_LIMB + 1];\n"),
    ("cipher/mceliece6688128f.c",
     "  int32 temp[2*n];\n  int16 pi_test[n], diff;\n",
     "  int32 *temp = (int32 *) _alloca (sizeof (int32) * (2*n));\n"
     "  int16 *pi_test = (int16 *) _alloca (sizeof (int16) * n);\n  int16 diff;\n"),
    ("cipher/sntrup761.c",
     "      uint16_t R2[(len + 1) / 2];\n      uint16_t M2[(len + 1) / 2];\n"
     "      uint16_t bottomr[len / 2];\n      uint32_t bottomt[len / 2];\n",
     "      uint16_t *R2 = (uint16_t *) _alloca (sizeof (uint16_t) * ((len + 1) / 2));\n"
     "      uint16_t *M2 = (uint16_t *) _alloca (sizeof (uint16_t) * ((len + 1) / 2));\n"
     "      uint16_t *bottomr = (uint16_t *) _alloca (sizeof (uint16_t) * (len / 2));\n"
     "      uint32_t *bottomt = (uint32_t *) _alloca (sizeof (uint32_t) * (len / 2));\n"),
    ("cipher/sntrup761.c",
     "      uint16_t R2[(len + 1) / 2];\n      uint16_t M2[(len + 1) / 2];\n      long long i;\n",
     "      uint16_t *R2 = (uint16_t *) _alloca (sizeof (uint16_t) * ((len + 1) / 2));\n"
     "      uint16_t *M2 = (uint16_t *) _alloca (sizeof (uint16_t) * ((len + 1) / 2));\n      long long i;\n"),
    ("cipher/sntrup761.c",
     "  unsigned char x[inlen + 1];\n",
     "  unsigned char *x = (unsigned char *) _alloca (inlen + 1);\n"),
]


def apply_patches(src):
    import difflib
    applied = []
    for rel, old, new in PATCHES:
        path = os.path.join(src, *rel.split("/"))
        if not os.path.isfile(path):
            continue
        with open(path, newline="") as f:
            text = f.read()
        crlf = "\r\n" in text
        o, n = (old.replace("\n", "\r\n"), new.replace("\n", "\r\n")) if crlf else (old, new)
        if text.count(o) != 1:
            continue
        out = text.replace(o, n)
        with open(path, "w", newline="") as f:
            f.write(out)
        diff = "".join(difflib.unified_diff(text.replace("\r\n", "\n").splitlines(True),
                                            out.replace("\r\n", "\n").splitlines(True),
                                            "a/" + rel, "b/" + rel, n=1))
        print("PATCH applied to %s:\n%s" % (rel, diff), flush=True)
        applied.append(rel)
    say("source edits applied to: %s" % (", ".join(applied) or "none"))
    return applied


def host_gcc():
    """A MinGW gcc for mkheader.c, upstream's build-host helper: it includes
    <unistd.h>, which cl does not have. The helper only runs at build time and
    is not part of any artefact."""
    g = shutil.which("gcc")
    if g:
        return g
    for d in (r"C:\mingw64\bin", r"C:\msys64\mingw64\bin", r"C:\msys64\ucrt64\bin",
              r"C:\ProgramData\mingw64\mingw64\bin"):
        if os.path.isfile(os.path.join(d, "gcc.exe")):
            return os.path.join(d, "gcc.exe")
    w = shutil.which("windres")
    if w and os.path.isfile(os.path.join(os.path.dirname(w), "gcc.exe")):
        return os.path.join(os.path.dirname(w), "gcc.exe")
    raise SystemExit("no gcc for mkheader.c")


def build_gpg_error(arch, src, work, prefix, diag=False, lenient=False):
    bld = os.path.join(work, "ge")
    if os.path.isdir(bld):
        shutil.rmtree(bld)
    triple = ("x86_64" if arch == "x64" else "i686") + "-w64-mingw32"
    say("libgpg-error: configure (%s)" % triple)
    cmd = [os.path.join(MSYS, "bash.exe"), fwd(os.path.join(HERE, "gnupg_cl.sh")),
           arch, src, bld, prefix] + (["diag"] if diag else []) + ["--"] + OPTS_GE
    env = dict(os.environ, MSYS2_PATH_TYPE="inherit")
    rc, out = run(cmd, timeout=1500, check=False, env=env)
    sys.stdout.write(out.decode("utf-8", "replace")[-12000:])
    if rc:
        raise SystemExit("libgpg-error configure failed")

    sdir = os.path.join(src, "src")
    b = os.path.join(bld, "src")
    mk = parse_makefile(os.path.join(b, "Makefile"))
    version = expand(mk, mk.get("PACKAGE_VERSION", ""))
    vnum = expand(mk, mk.get("VERSION_NUMBER", ""))
    say("libgpg-error %s (%s), host %s" % (version, vnum, triple))
    cc_inc = ["/I" + b, "/I" + sdir, "/I" + bld]

    # code-to-errno.h
    with open(os.path.join(b, "code-to-errno.h"), "wb") as f:
        f.write(awk(os.path.join(sdir, "mkerrnos.awk"), os.path.join(sdir, "errnos.in")))
    # mkerrcodes.h: the errno names this compiler's headers know
    pre = awk(os.path.join(sdir, "mkerrcodes1.awk"), os.path.join(sdir, "errnos.in"))
    with open(os.path.join(b, "_mkerrcodes.h"), "wb") as f:
        f.write(pre)
    rc, cpp = run(["cl", "/nologo", "/EP", "_mkerrcodes.h"], cwd=b, check=False, quiet=True)
    grepped = b"\n".join(l for l in cpp.splitlines() if b"GPG_ERR_" in l) + b"\n"
    with open(os.path.join(b, "mkerrcodes.h"), "wb") as f:
        f.write(awk(os.path.join(sdir, "mkerrcodes.awk"), None, stdin=grepped))
    run(["cl", "/nologo", "/MD", "/I" + b, "/I" + sdir, "/Femkerrcodes.exe",
         os.path.join(sdir, "mkerrcodes.c")], cwd=b)
    rc, tab = run([os.path.join(b, "mkerrcodes.exe")], cwd=b, merge=False)
    with open(os.path.join(b, "code-from-errno.h"), "wb") as f:
        f.write(awk(os.path.join(sdir, "mkerrcodes2.awk"), None, stdin=tab))
    # gpg-error.h / gpgrt.h
    gcc = host_gcc()
    say("mkheader.c with " + gcc)
    run([gcc, "-g", "-O0", "-I" + b, "-I" + sdir, "-o", "mkheader.exe",
         os.path.join(sdir, "mkheader.c")], cwd=b)
    lock = os.path.join(b, "lock-obj-pub.native.h")
    if os.path.exists(lock):
        os.remove(lock)
    cross = expand(mk, mk.get("mkheader_opts", "")).split()
    rc, hdr = run([os.path.join(b, "mkheader.exe")] + cross + [triple, fwd(os.path.join(sdir, "gpg-error.h.in")),
                   "../config.h", version, vnum], cwd=b, merge=False)
    with open(os.path.join(b, "gpg-error.h"), "wb") as f:
        f.write(hdr)
    shutil.copyfile(os.path.join(b, "gpg-error.h"), os.path.join(b, "gpgrt.h"))
    # gpg-error.def (needs config.h, hence the preprocessor)
    shutil.copyfile(os.path.join(sdir, "gpg-error.def.in"), os.path.join(b, "_gpg-error.def.h"))
    rc, d = run(["cl", "/nologo", "/EP"] + cc_inc + ["_gpg-error.def.h"], cwd=b, merge=False)
    with open(os.path.join(b, "gpg-error.def"), "wb") as f:
        f.write(b"\n".join(l for l in d.splitlines() if not l.startswith(b"#")) + b"\n")
    # older releases include this from w32 code
    if not os.path.exists(os.path.join(b, "mkw32errmap.map.c")):
        with open(os.path.join(b, "mkw32errmap.map.c"), "w") as f:
            f.write("/*dummy*/\n")

    objs = objects(mk, "am_libgpg_error_la_OBJECTS", "libgpg_error_la_LIBADD")
    say("libgpg-error: %d objects listed by upstream's Makefile" % len(objs))
    items, missing = [], []
    for o in objs:
        s = find_source(o, [b, sdir])
        if s is not None and s.endswith(".rc"):
            say("libgpg-error: %s is a resource, not compiled" % o)
            continue
        if s is None or s.endswith((".S", ".s")):
            missing.append(o)
            continue
        items.append((s, os.path.splitext(os.path.basename(o))[0] + ".obj", b))
    if missing:
        say("libgpg-error: no C source for: %s" % " ".join(missing))
    defines = ["HAVE_CONFIG_H", "DLL_EXPORT", "strcasecmp=_stricmp", "strncasecmp=_strnicmp",
               'LOCALEDIR="/usr/local/share/locale"', 'SYSCONFDIR="/usr/local/etc"']
    shim = make_shim(work, True)
    # only visibility.c needs it; it defines this macro itself before reading
    # the header, so the command-line definition is the same definition
    items = [(os.path.join(shim, "visibility_cl.c"), "visibility.obj", b)
             if os.path.basename(i[0]) == "visibility.c" else i for i in items]
    ok, bad = compile_all(items, b, lambda cwd: [b, sdir, bld, shim], defines,
                          force=os.path.join(shim, "gnupg_cl_fi.h"))
    report("libgpg-error", bad)
    dll = os.path.join(b, "libgpg-error-0.dll")
    failed = bool(bad or missing)
    if not failed:
        rc = link_dll(dll, ok, SYSLIBS, os.path.join(b, "gpg-error.def"),
                      implib=os.path.join(b, "gpg-error.lib"), cwd=b)
        failed = bool(rc)
    if failed and not lenient:
        raise SystemExit("libgpg-error: build incomplete")
    # the "install" libgcrypt's configure and compile look for
    for d in ("bin", "lib", "include", os.path.join("lib", "pkgconfig")):
        os.makedirs(os.path.join(prefix, d), exist_ok=True)
    for name, dest in (("gpgrt-config", "bin"), ("gpg-error-config-old", "bin"),
                       ("libgpg-error-0.dll", "bin"), ("gpg-error.lib", "lib"),
                       ("gpg-error.h", "include"), ("gpgrt.h", "include"),
                       ("gpg-error.pc", os.path.join("lib", "pkgconfig"))):
        p = os.path.join(b, name)
        if os.path.exists(p):
            shutil.copyfile(p, os.path.join(prefix, dest, name))
    old = os.path.join(prefix, "bin", "gpg-error-config-old")
    if os.path.exists(old):
        shutil.copyfile(old, os.path.join(prefix, "bin", "gpg-error-config"))
    return None if failed else dll


def generic_mpi_modules(bld, src, items):
    """mpi/config.links picks the C or assembler file of each standard
    multi-precision primitive (mpih-add1 ...). Under this configure run its
    conditionals came out false, so the generated mpi/Makefile lists none of
    them and the DLL would lack _gcry_mpih_add_n and friends. They are added
    here from the generic/ directory, which is the file config.links selects
    with --disable-asm."""
    try:
        with open(os.path.join(src, "mpi", "Makefile.am"), encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return []
    block = re.search(r"#BEGIN_ASM_LIST(.*?)#END_ASM_LIST", text, re.S)
    mods = []
    if block:
        for m in re.finditer(r"^#\s*(\S+)\s+(\S+)\s*$", block.group(1), re.M):
            if m.group(2) != "O":
                mods.append(m.group(1))
    have = {os.path.splitext(os.path.basename(i[0]))[0] for i in items}
    added = []
    for fn in mods:
        if fn in have:
            continue
        path = os.path.join(src, "mpi", "generic", fn + ".c")
        if os.path.isfile(path):
            added.append((path, "mpi-" + fn + ".obj", os.path.join(bld, "mpi")))
    say("libgcrypt: standard mpi modules %s; added from mpi/generic (absent from the generated "
        "mpi/Makefile): %s" % (" ".join(mods), " ".join(os.path.basename(a[0]) for a in added) or "none"))
    return added


def resolve_hwfeatures(items, includes, defines, force, arch, shim, bld, src):
    """Bisect cl's internal compiler error (C1001) in src/hwfeatures.c.

    1.10.4 and 1.11.3 abort in cl on this file whatever the optimiser setting.
    With --disable-asm HAVE_CPU_ARCH_X86 is not defined, so the table
    `hwflist[] = { ... }` has no initialiser at all (an empty brace list for an
    array of structs, which cl turns into a zero-size array) and is the
    suspect. Each variant below is one separate cl invocation, all of them
    logged; the first that compiles supplies the real object:

      orig        the file as shipped (known to crash)
      x86tab      /DHAVE_CPU_ARCH_X86=1 for this file only: the table gets its
                  x86 rows; the detection branch then calls
                  _gcry_hwf_detect_x86, which hwf-x86.c (compiled with the GCC
                  CPU macro, as for 1.8.14) provides and which reports no
                  features without CPUID
      noparse     parse_hwf_deny_file returns at once (build-tree edit)
      nosysconf   _gcry_get_sysconfdir returns the fixed fallback (build-tree edit)
      noparse+nosysconf, and the original under /std:c11, /Zc:preprocessor,
      /Od /Zi and /d2SSAOptimizer-
    """
    pos = [k for k, i in enumerate(items) if os.path.basename(i[0]) == "hwfeatures.c"]
    if not pos:
        return items, False
    k = pos[0]
    path, objname, cwd = items[k]
    with open(path, newline="") as f:
        text = f.read()

    def noparse(t):
        return t.replace("parse_hwf_deny_file (void)\n{\n", "parse_hwf_deny_file (void)\n{\n  return;\n", 1)

    def nosysconf(t):
        return t.replace("  static char *appdata;\n",
                         "  return \"c:/ProgramData/GNU/etc/gcrypt/\";\n  static char *appdata;\n", 1)
    variants = [
        ("orig", [], None, False),
        ("x86tab", ["/DHAVE_CPU_ARCH_X86=1"], None, True),
        ("noparse", [], noparse, False),
        ("nosysconf", [], nosysconf, False),
        ("noparse+nosysconf", [], lambda t: nosysconf(noparse(t)), False),
        ("orig /std:c11", ["/std:c11"], None, False),
        ("orig /Zc:preprocessor", ["/Zc:preprocessor"], None, False),
        ("orig /Od /Zi", ["/Od", "/Zi"], None, False),
        ("orig /d2SSAOptimizer-", ["/d2SSAOptimizer-"], None, False),
        ("x86tab+noparse", ["/DHAVE_CPU_ARCH_X86=1"], noparse, True),
    ]
    cl = Cl(None)
    winner = None
    for n, (name, flags, edit, needs_x86) in enumerate(variants):
        src_v = path
        if edit:
            t2 = edit(text)
            if t2 == text:
                say("hwfeatures variant %-22s: edit did not apply, skipped" % name)
                continue
            src_v = os.path.join(shim, "hwfeatures_v%d.c" % n)
            with open(src_v, "w", newline="") as f:
                f.write(t2)
        extra = ["/FI" + force] + flags
        cmd = cl.compile_cmd(src_v, "hwf_probe_%d.obj" % n, includes(cwd), defines, extra)
        rc, out = run(cmd, cwd=cwd, timeout=600, check=False, quiet=True)
        o = out.decode("utf-8", "replace")
        msg = " | ".join(l.strip() for l in o.splitlines() if "error" in l or "INTERNAL" in l)[:300]
        say("hwfeatures variant %-22s: rc=%s %s" % (name, rc, msg if rc else "COMPILES"))
        if rc == 0 and winner is None:
            winner = (name, src_v, flags, needs_x86)
    if winner is None:
        say("hwfeatures: no variant compiles")
        return items, False
    name, src_v, flags, needs_x86 = winner
    say("hwfeatures: using variant '%s'" % name)
    items = list(items)
    items[k] = (src_v, objname, cwd)
    HWF_EXTRA.extend(flags)
    return items, needs_x86


HWF_EXTRA = []


def gen_gost_sb(bld, src):
    """cipher/gost-sb.h is generated at build time by a build-host program."""
    c = os.path.join(src, "cipher", "gost-s-box.c")
    if not os.path.isfile(c):
        return
    gcc = host_gcc()
    d = os.path.join(bld, "cipher")
    run([gcc, "-O0", "-o", "gost-s-box.exe", c], cwd=d)
    run([os.path.join(d, "gost-s-box.exe"), "gost-sb.h"], cwd=d)
    say("gost-sb.h generated (%d bytes)" % os.path.getsize(os.path.join(d, "gost-sb.h")))


# ----------------------------------------------------------------- libgcrypt

def build_gcrypt(arch, src, work, prefix):
    bld = os.path.join(work, "gc")
    if os.path.isdir(bld):
        shutil.rmtree(bld)
    triple = ("x86_64" if arch == "x64" else "i686") + "-w64-mingw32"
    say("libgcrypt: configure")
    cmd = [os.path.join(MSYS, "bash.exe"), fwd(os.path.join(HERE, "gnupg_cl.sh")),
           arch, src, bld, os.path.join(work, "gcinst"), "--"] + OPTS_GC + \
          ["--with-libgpg-error-prefix=" + fwd(prefix),
           # AC_TYPE_PID_T would #define pid_t __int64 on Win64, against the
           # `typedef int pid_t` that gcrypt.h itself makes for non-GNU compilers
           "ac_cv_type_pid_t=yes",
           # configure's link tests mis-detect these under cl (they are
           # intrinsics or CRT functions that exist); without them g10lib.h
           # renames memmove to bcopy, atexit to on_exit and raise to kill
           "ac_cv_func_memmove=yes", "ac_cv_func_strtoul=yes", "ac_cv_func_atexit=yes",
           "ac_cv_func_raise=yes", "ac_cv_func_strerror=yes", "ac_cv_func_rand=yes",
           "ac_cv_func_stricmp=yes"]
    env = dict(os.environ, MSYS2_PATH_TYPE="inherit",
               GNUPG_EXTRA_PATH=os.path.join(prefix, "bin"))
    rc, out = run(cmd, timeout=1800, check=False, env=env)
    sys.stdout.write(out.decode("utf-8", "replace")[-12000:])
    if rc:
        raise SystemExit("libgcrypt configure failed")

    items = []
    missing = []
    asm_skipped = []
    patched = apply_patches(src)
    gen_gost_sb(bld, src)
    for sub in ("compat", "mpi", "cipher", "random", "src"):
        mkp = os.path.join(bld, sub, "Makefile")
        if not os.path.isfile(mkp):
            continue
        mk = parse_makefile(mkp)
        lib = "libgcrypt" if sub == "src" else "lib" + sub
        for n in [(("am_%s_la_OBJECTS" % lib, "%s_la_LIBADD" % lib))]:
            for o in objects(mk, *n):
                s = find_source(o, [os.path.join(bld, sub), os.path.join(src, sub)])
                if s is not None and s.endswith(".rc"):
                    say("libgcrypt: %s is a resource, not compiled" % o)
                    continue
                if s is not None and s.endswith((".S", ".s")):
                    asm_skipped.append("%s/%s" % (sub, o))
                    continue
                if s is None:
                    missing.append("%s/%s" % (sub, o))
                    continue
                oname = os.path.splitext(os.path.basename(o))[0]
                if sub == "src" and oname.startswith("libgcrypt_la-"):
                    oname = oname[len("libgcrypt_la-"):]
                items.append((s, sub + "-" + oname + ".obj", os.path.join(bld, sub)))
    items += generic_mpi_modules(bld, src, items)
    say("libgcrypt: %d objects from upstream's Makefiles, %d GNU-syntax assembler modules "
        "not assembled by cl (the C code does not reference them: no USE_*_ASM is defined): %s"
        % (len(items) + len(missing) + len(asm_skipped), len(asm_skipped), " ".join(asm_skipped)))
    if missing:
        say("libgcrypt: no C source for: %s" % " ".join(missing))

    inc = prefix + os.sep + "include"
    shim = make_shim(work, False)

    def includes(cwd):
        sub = os.path.basename(cwd)
        out = [cwd, os.path.join(src, sub), bld, os.path.join(bld, "src"),
               os.path.join(src, "src"), os.path.join(bld, "mpi"),
               os.path.join(src, "mpi"), inc, shim]
        return out
    # rndjent is compiled without optimisation upstream (its timing loop must
    # not be optimised away); the flag is the only change.
    # hwf-x86.c (1.8.14 lists it for every x86 host) refuses to compile unless
    # the GCC CPU macro is defined; with only that macro (no __GNUC__) it
    # compiles its CPUID-less fallback, which reports no features.
    extra = {"rndjent.c": ["/Od"], "jitterentropy-base.c": ["/Od"],
             "hwf-x86.c": ["/D__x86_64__" if arch == "x64" else "/D__i386__"],
             }
    base_defs = ["HAVE_CONFIG_H", "DLL_EXPORT",
                 "HAVE_GCC_STORAGE_CLASS__THREAD=1", "__thread=__declspec(thread)"]
    items, needs_x86 = resolve_hwfeatures(items, includes, base_defs,
                                          os.path.join(shim, "gnupg_cl_fi.h"), arch, shim, bld, src)
    if needs_x86 and not any(os.path.basename(i[0]) == "hwf-x86.c" for i in items):
        hx = os.path.join(src, "src", "hwf-x86.c")
        if os.path.isfile(hx):
            items.append((hx, "src-hwf-x86.obj", os.path.join(bld, "src")))
            say("libgcrypt: hwf-x86.c added (provides _gcry_hwf_detect_x86 for the x86 table variant)")
    for i in items:
        if os.path.basename(i[0]).startswith("hwfeatures"):
            extra[os.path.basename(i[0])] = list(HWF_EXTRA)
    ok, bad = compile_all(items, bld, includes, ["HAVE_CONFIG_H", "DLL_EXPORT",
                           "HAVE_GCC_STORAGE_CLASS__THREAD=1", "__thread=__declspec(thread)"], extra,
                          force=os.path.join(shim, "gnupg_cl_fi.h"))
    report("libgcrypt", bad)
    out_dir = os.path.join(bld, "src")
    dll = os.path.join(out_dir, "libgcrypt-20.dll")
    deff = os.path.join(src, "src", "libgcrypt.def")
    if bad or not os.path.isfile(os.path.join(prefix, "lib", "gpg-error.lib")):
        # link what compiled, so the unresolved set is on record too
        say("libgcrypt: linking the %d objects that compiled, for the record" % len(ok))
    rc = link_dll(dll, ok, [os.path.join(prefix, "lib", "gpg-error.lib")] + SYSLIBS,
                  deff, cwd=out_dir)
    if bad or missing or rc:
        raise SystemExit("libgcrypt: build incomplete (%d failed, %d without C source, link rc %d)"
                         % (len(bad), len(missing), rc))
    return dll


def main():
    arch, pkg, src = sys.argv[1], sys.argv[2], os.path.abspath(sys.argv[3])
    work = os.path.join(src, "msvc-" + arch)
    os.makedirs(work, exist_ok=True)
    prefix = os.path.join(work, "inst")
    diag = os.environ.get("GNUPG_CL_DIAG") == "1"
    if pkg == "gpg-error":
        build_gpg_error(arch, src, work, prefix, diag)
    else:
        tar = os.path.abspath(sys.argv[4])
        with tarfile.open(tar) as t:
            t.extractall(work)
        ge = glob.glob(os.path.join(work, "libgpg-error-*"))[0]
        build_gpg_error(arch, ge, work, prefix, False, lenient=True)
        build_gcrypt(arch, src, work, prefix)
    say("done")


if __name__ == "__main__":
    main()
