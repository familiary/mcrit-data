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


def run(cmd, cwd=None, timeout=900, input=None, check=True, quiet=False, env=None):
    """Run a command, return (rc, stdout-bytes). stderr is merged in."""
    t = time.time()
    p = subprocess.run(cmd, cwd=cwd, input=input, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=timeout, env=env)
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


def compile_all(srcs, builddir, includes, defines, extra_for=None, jobs=4):
    """Compile (src, objname, cwd) in parallel; return (objects, failures)."""
    cl = Cl(None)
    ok, bad = [], []

    def one(item):
        src, obj, cwd = item
        extra = (extra_for or {}).get(os.path.basename(src), ())
        cmd = cl.compile_cmd(src, obj, includes(cwd), defines, extra)
        rc, out = run(cmd, cwd=cwd, timeout=600, check=False, quiet=True)
        return item, rc, out.decode("utf-8", "replace")

    with concurrent.futures.ThreadPoolExecutor(jobs) as ex:
        for item, rc, out in ex.map(one, srcs):
            if rc == 0:
                ok.append(os.path.join(item[2], item[1]))
            else:
                errs = [l for l in out.splitlines() if re.search(r"error|fatal", l)]
                bad.append((item[0], errs[:8]))
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
    return run(cmd, cwd=cwd, input=stdin, quiet=True)[1]


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


def build_gpg_error(arch, src, work, prefix, diag=False):
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
    rc, tab = run([os.path.join(b, "mkerrcodes.exe")], cwd=b)
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
                   "../config.h", version, vnum], cwd=b)
    with open(os.path.join(b, "gpg-error.h"), "wb") as f:
        f.write(hdr)
    shutil.copyfile(os.path.join(b, "gpg-error.h"), os.path.join(b, "gpgrt.h"))
    # gpg-error.def (needs config.h, hence the preprocessor)
    shutil.copyfile(os.path.join(sdir, "gpg-error.def.in"), os.path.join(b, "_gpg-error.def.h"))
    rc, d = run(["cl", "/nologo", "/EP"] + cc_inc + ["_gpg-error.def.h"], cwd=b)
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
    defines = ["HAVE_CONFIG_H", "DLL_EXPORT",
               'LOCALEDIR="/usr/local/share/locale"', 'SYSCONFDIR="/usr/local/etc"']
    ok, bad = compile_all(items, b, lambda cwd: [b, sdir, bld], defines)
    report("libgpg-error", bad)
    if bad or missing:
        raise SystemExit("libgpg-error: not every translation unit compiled")
    dll = os.path.join(b, "libgpg-error-0.dll")
    rc = link_dll(dll, ok, SYSLIBS, os.path.join(b, "gpg-error.def"),
                  implib=os.path.join(b, "gpg-error.lib"), cwd=b)
    if rc:
        raise SystemExit("libgpg-error: link failed")
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
    return dll


# ----------------------------------------------------------------- libgcrypt

def build_gcrypt(arch, src, work, prefix):
    bld = os.path.join(work, "gc")
    if os.path.isdir(bld):
        shutil.rmtree(bld)
    triple = ("x86_64" if arch == "x64" else "i686") + "-w64-mingw32"
    say("libgcrypt: configure")
    cmd = [os.path.join(MSYS, "bash.exe"), fwd(os.path.join(HERE, "gnupg_cl.sh")),
           arch, src, bld, os.path.join(work, "gcinst"), "--"] + OPTS_GC + \
          ["--with-libgpg-error-prefix=" + fwd(prefix)]
    env = dict(os.environ, MSYS2_PATH_TYPE="inherit",
               GNUPG_EXTRA_PATH=os.path.join(prefix, "bin"))
    rc, out = run(cmd, timeout=1800, check=False, env=env)
    sys.stdout.write(out.decode("utf-8", "replace")[-12000:])
    if rc:
        raise SystemExit("libgcrypt configure failed")

    libs = []   # (subdir, [obj names])
    items = []
    missing = []
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
                if s is None or s.endswith((".S", ".s")):
                    missing.append("%s/%s" % (sub, o))
                    continue
                oname = os.path.splitext(os.path.basename(o))[0]
                if sub == "src" and oname.startswith("libgcrypt_la-"):
                    oname = oname[len("libgcrypt_la-"):]
                items.append((s, sub + "-" + oname + ".obj", os.path.join(bld, sub)))
    say("libgcrypt: %d objects from upstream's Makefiles" % (len(items) + len(missing)))
    if missing:
        say("libgcrypt: no C source for: %s" % " ".join(missing))

    inc = prefix + os.sep + "include"

    def includes(cwd):
        sub = os.path.basename(cwd)
        out = [cwd, os.path.join(src, sub), bld, os.path.join(bld, "src"),
               os.path.join(src, "src"), os.path.join(bld, "mpi"),
               os.path.join(src, "mpi"), inc]
        return out
    # rndjent is compiled without optimisation upstream (its timing loop must
    # not be optimised away); the flag is the only change.
    extra = {"rndjent.c": ["/Od"], "jitterentropy-base.c": ["/Od"]}
    ok, bad = compile_all(items, bld, includes, ["HAVE_CONFIG_H", "DLL_EXPORT"], extra)
    report("libgcrypt", bad)
    out_dir = os.path.join(bld, "src")
    dll = os.path.join(out_dir, "libgcrypt-20.dll")
    deff = os.path.join(src, "src", "libgcrypt.def")
    if bad:
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
        build_gpg_error(arch, ge, work, prefix, False)
        build_gcrypt(arch, src, work, prefix)
    say("done")


if __name__ == "__main__":
    main()
