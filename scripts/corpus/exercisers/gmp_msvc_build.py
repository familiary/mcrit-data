#!/usr/bin/env python3
"""Build GMP's generic C tree with cl, without running configure.

GMP is autotools plus GNU-assembler and m4-processed assembly, and its
configure refuses cl. Upstream documents MinGW for Windows and nothing for
MSVC. What the library needs from configure is small and mechanical, so this
does the same job in configure's and make's own order from the unmodified
tree, for the no-assembly (``path = generic``) configuration that
``--disable-assembly`` selects:

  1. config.h is config.in with each ``#undef NAME`` resolved from the table
     below, the answers configure would give cl on Windows (LLP64: long is 4
     bytes on x86 and x64, so the x64 limb is ``unsigned long long`` through
     ``_LONG_LONG_LIMB``, the way the MinGW x64 build has it). gmp.h is
     gmp-h.in with its @SUBSTITUTIONS@ filled. gmp-mparam.h is
     mpn/generic/gmp-mparam.h, which is what configure copies for the generic
     path. All of it goes to ``gen/``, outside the upstream files.
  2. fac_table.h, sieve_table.h, fib_table.h, mp_bases.h, trialdivtab.h,
     jacobitab.h, perfsqr.h and the two generated sources fib_table.c and
     mp_bases.c come from compiling gen-fac.c, gen-sieve.c, gen-fib.c,
     gen-bases.c, gen-trialdivtab.c, gen-jacobitab.c and gen-psqr.c with cl and
     running them with the arguments the rules in Makefile.in give them
     (``$(GMP_LIMB_BITS) $(GMP_NAIL_BITS)``, ``header`` / ``table``, 8000).
     The rules are read out of Makefile.in; no table is written down here.
  3. The source lists are read out of Makefile.in (``libgmp_la_SOURCES``,
     ``MPZ_OBJECTS`` and the other per-directory object lists) and, for mpn,
     out of configure.ac: ``gmp_mpn_functions`` and the multi-function-file
     table of ``GMP_MULFUNC_CHOICES``, resolved against mpn/generic exactly as
     configure resolves them for a path with no assembly (196 functions in
     6.3.0, the same set that ``./configure --disable-assembly`` puts in
     mpn/Makefile's OFILES). Each mpn file is compiled with
     ``-DOPERATION_<function>``, as mpn/Makefile.am does.
  4. Everything is compiled with ``-DHAVE_CONFIG_H -D__GMP_WITHIN_GMP`` and the
     corpus flags, then either linked to a DLL whose export table is every
     defined external function of the objects (the rule MinGW's ld applies and
     nettle_msvc_build.py uses; the data GMP exports is declared
     ``__declspec(dllexport)`` by gmp.h itself, which is built with
     ``__GMP_LIBGMP_DLL 1``) or, with ``--static``, archived with lib.exe into
     a static gmp.lib and gmp.h (``__GMP_LIBGMP_DLL 0``) under ``--prefix``,
     for gnutls_msvc_build.py.

No assembly of any kind: ``--enable-fat`` has no cl equivalent, so there is no
CPU dispatch and no mpn_* in assembler. The code is the portable C of
mpn/generic. Debug information is embedded in the objects (/Z7) rather than
written by a shared /Fd, because the sources are compiled in parallel; the
linker writes the PDB from them.

Every command is echoed before it runs so the runner's log shows the flags.
"""

import argparse
import concurrent.futures
import glob
import os
import re
import shutil
import subprocess
import sys


def _defines(arch):
    """What configure would have probed for cl on Windows.

    Anything config.in declares and this table does not mention stays
    undefined, which is what configure writes for a feature the platform
    lacks (all HAVE_NATIVE_* and HAVE_HOST_CPU_* among them: no assembly).
    """
    x64 = arch == "x64"
    return {
        "HAVE_ALLOCA": "1",
        "HAVE_DECL_FGETC": "1",
        "HAVE_DECL_FSCANF": "1",
        "HAVE_DECL_OPTARG": "0",
        "HAVE_DECL_SYS_ERRLIST": "0",
        "HAVE_DECL_SYS_NERR": "0",
        "HAVE_DECL_UNGETC": "1",
        "HAVE_DECL_VFPRINTF": "1",
        "HAVE_DOUBLE_IEEE_LITTLE_ENDIAN": "1",
        "HAVE_FCNTL_H": "1",
        "HAVE_FLOAT_H": "1",
        "HAVE_INTMAX_T": "1",
        "HAVE_INTPTR_T": "1",
        "HAVE_INTTYPES_H": "1",
        "HAVE_LIMB_LITTLE_ENDIAN": "1",
        "HAVE_LOCALECONV": "1",
        "HAVE_LOCALE_H": "1",
        "HAVE_LONG_DOUBLE": "1",
        "HAVE_LONG_LONG": "1",
        "HAVE_MEMORY_H": "1",
        "HAVE_MEMSET": "1",
        "HAVE_PTRDIFF_T": "1",
        "HAVE_RAISE": "1",
        "HAVE_STDINT_H": "1",
        "HAVE_STDLIB_H": "1",
        "HAVE_STRCHR": "1",
        "HAVE_STRERROR": "1",
        "HAVE_STRING_H": "1",
        "HAVE_STRNLEN": "1",
        "HAVE_STRTOL": "1",
        "HAVE_STRTOUL": "1",
        "HAVE_SYS_STAT_H": "1",
        "HAVE_SYS_TYPES_H": "1",
        "HAVE_UINT_LEAST32_T": "1",
        "HAVE_VSNPRINTF": "1",
        "NO_ASM": "1",
        "PACKAGE": '"gmp"',
        "PACKAGE_NAME": '"GNU MP"',
        "PACKAGE_TARNAME": '"gmp"',
        "RETSIGTYPE": "void",
        "SIZEOF_MP_LIMB_T": "8" if x64 else "4",
        "SIZEOF_UNSIGNED": "4",
        "SIZEOF_UNSIGNED_LONG": "4",
        "SIZEOF_UNSIGNED_SHORT": "2",
        "SIZEOF_VOID_P": "8" if x64 else "4",
        "STDC_HEADERS": "1",
        "WANT_FFT": "1",
        "WANT_TMP_ALLOCA": "1",
    }


CFLAGS_TEXT = "/O2 /MD /Z7"


def run(command, **kwargs):
    print("> " + " ".join(command), flush=True)
    subprocess.run(command, check=True, **kwargs)


def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def version_of(src):
    """configure's GMP_VERSION: the three __GNU_MP_VERSION* values of gmp-h.in."""
    text = read_text(os.path.join(src, "gmp-h.in"))
    parts = []
    for name in ("__GNU_MP_VERSION", "__GNU_MP_VERSION_MINOR",
                 "__GNU_MP_VERSION_PATCHLEVEL"):
        match = re.search(r"^#define\s+%s\s+(\d+)" % name, text, re.M)
        if not match:
            raise SystemExit("%s not found in gmp-h.in" % name)
        parts.append(match.group(1))
    return ".".join(parts)


def write_config(src, gen, arch, configured=None):
    defines = _defines(arch)
    if configured is not None:
        # The assembly build: no NO_ASM, and what configure decided about the
        # assembly (HAVE_NATIVE_mpn_*, the CPU family, WANT_FAT_BINARY) taken
        # from the config.h it wrote for the MinGW host of the same CPU.
        del defines["NO_ASM"]
        defines.update(configured)
    version = version_of(src)
    defines["PACKAGE_VERSION"] = '"%s"' % version
    defines["PACKAGE_STRING"] = '"GNU MP %s"' % version
    defines["VERSION"] = '"%s"' % version
    seen = set()

    def resolve(match):
        name = match.group(2)
        seen.add(name)
        if name in defines:
            return "#%sdefine %s %s" % (match.group(1), name, defines[name])
        return "/* #undef %s */" % name

    text = re.sub(r"^#(\s*)undef (\w+)\s*$", resolve,
                  read_text(os.path.join(src, "config.in")), flags=re.M)
    missing = sorted(set(defines) - seen)
    if missing:
        print("note: not declared by config.in: %s" % ", ".join(missing))
    with open(os.path.join(gen, "config.h"), "w", encoding="utf-8") as out:
        out.write(text)
    return version


def limb_bits(arch):
    return "64" if arch == "x64" else "32"


def write_gmp_h(src, gen, arch, dll):
    values = {
        "HAVE_HOST_CPU_FAMILY_power": "0",
        "HAVE_HOST_CPU_FAMILY_powerpc": "0",
        "GMP_LIMB_BITS": limb_bits(arch),
        "GMP_NAIL_BITS": "0",
        # configure: DEFN_LONG_LONG_LIMB is "#define _LONG_LONG_LIMB 1" when
        # the limb is a long long, which it is where long is narrower.
        "DEFN_LONG_LONG_LIMB": ("#define _LONG_LONG_LIMB 1" if arch == "x64"
                                else "/* #undef _LONG_LONG_LIMB */"),
        "LIBGMP_DLL": "1" if dll else "0",
        "CC": "cl",
        "CFLAGS": CFLAGS_TEXT,
    }
    text = re.sub(r"@(\w+)@", lambda m: values[m.group(1)],
                  read_text(os.path.join(src, "gmp-h.in")))
    with open(os.path.join(gen, "gmp.h"), "w", encoding="utf-8") as out:
        out.write(text)
    shutil.copyfile(os.path.join(src, "mpn", "generic", "gmp-mparam.h"),
                    os.path.join(gen, "gmp-mparam.h"))


def build_generators(src, gen, arch, flags):
    """Compile and run the gen-*.c programs the way Makefile.in's rules do."""
    makefile = read_text(os.path.join(src, "Makefile.in"))
    substitutions = {"$(GMP_LIMB_BITS)": limb_bits(arch),
                     "$(GMP_NAIL_BITS)": "0"}
    rules = re.findall(
        r"^(?:mpn/)?([\w.]+\.[ch]):\s*gen-(\w+)\$\(EXEEXT_FOR_BUILD\)\n"
        r"\t\./gen-\w+\s*([^>\n]*?)\s*>\s*(\S+)", makefile, re.M)
    if not rules:
        raise SystemExit("no gen-* rules found in Makefile.in")
    built = set()
    for target, tool, args, output in rules:
        exe = os.path.join(gen, "gen-%s.exe" % tool)
        if tool not in built:
            run(["cl", "/nologo", "/O2", "/MD", "/I" + src,
                 "/Fe:" + exe, "/Fo:" + os.path.join(gen, "gen-%s.obj" % tool),
                 os.path.join(src, "gen-%s.c" % tool)])
            built.add(tool)
        for key, value in substitutions.items():
            args = args.replace(key, value)
        command = [exe] + args.split()
        # mpn/perfsqr.h and mpn/fib_table.c land flat in gen/: the sources
        # find them through /Igen, not through their own directory.
        destination = os.path.join(gen, os.path.basename(output))
        print("> %s > %s" % (" ".join(command), destination), flush=True)
        result = subprocess.run(command, check=True, capture_output=True)
        with open(destination, "wb") as handle:
            handle.write(result.stdout)
    print("%d generated files: %s" % (len(rules), ", ".join(
        sorted(r[3] for r in rules))))
    return sorted(os.path.basename(r[3]) for r in rules)


def object_list(makefile, name):
    """Sources named by ``NAME = dir/a$U.lo dir/b$U.lo \\``-continued lists."""
    match = re.search(r"^%s\s*=((?:[^\n]*\\\n)*[^\n]*)" % re.escape(name),
                      makefile, re.M)
    if not match:
        raise SystemExit("%s not found in Makefile.in" % name)
    words = match.group(1).replace("\\\n", " ").split()
    return [w.replace("$U.lo", ".c") for w in words if w.endswith(".lo")]


def mpn_functions(src):
    """{function: generic file} configure resolves for a path with no asm."""
    text = read_text(os.path.join(src, "configure.ac"))
    block = text[text.index("define(GMP_MULFUNC_CHOICES"):]
    block = block[:block.index("esac")]
    choices = {}
    for patterns, value in re.findall(
            r'^\s*([\w| \t\n]+?)\)\s*\n?\s*tmp_mulfunc="([^"]*)"', block, re.M):
        for pattern in re.split(r"[|\s]+", patterns.strip()):
            if pattern:
                choices[pattern] = value.split()
    main = re.search(r'^gmp_mpn_functions="([^"]*)"', text, re.M).group(1)
    optional = re.search(r'^gmp_mpn_functions_optional="([^"]*)"', text,
                         re.M).group(1)
    names = [n for n in main.replace("\\\n", " ").split()
             if not n.startswith("$")]
    names += optional.replace("\\\n", " ").split()
    found = {}
    for name in names:
        for candidate in [name] + choices.get(name, []):
            if os.path.exists(os.path.join(src, "mpn", "generic",
                                           candidate + ".c")):
                found[name] = candidate
                break
    return found


def compile_one(job):
    source, obj, extra, flags = job
    command = (["cl", "/nologo", "/c", "/O2", "/MD", "/Z7", "/w"] + flags
               + extra + ["/Fo" + obj, source])
    result = subprocess.run(command, capture_output=True, text=True)
    return job, command, result


def compile_all(jobs):
    """Compile every job in parallel; print all failures, then stop."""
    failed = []
    workers = max(2, os.cpu_count() or 2)
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        for job, command, result in pool.map(compile_one, jobs):
            if result.returncode != 0:
                failed.append(job)
                print("> " + " ".join(command), flush=True)
                print(result.stdout + result.stderr, flush=True)
    print("compiled %d files, %d failed" % (len(jobs), len(failed)), flush=True)
    if failed:
        raise SystemExit("%d file(s) failed to compile: %s" % (
            len(failed), ", ".join(os.path.basename(j[0]) for j in failed[:40])))


def exports(objects, arch, path):
    names = set()
    for start in range(0, len(objects), 40):
        out = subprocess.check_output(
            ["dumpbin", "/SYMBOLS"] + objects[start:start + 40]).decode(
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
            names.add(name)
    if not names:
        raise SystemExit("no exports found")
    with open(path, "w") as handle:
        handle.write("EXPORTS\n" + "\n".join(sorted(names)) + "\n")
    print("%s: %d exports" % (path, len(names)))


ASM_SCRIPT = r'''
set -u
SRC="$(cygpath -u "$SRC_WIN")"
OBJ="$(cygpath -u "$OBJ_WIN")"
CFG="$(cygpath -u "$CFG_WIN")"
pacman -Sy --noconfirm --needed m4 make diffutils "$GCC_PKG" || exit 90
export PATH="$MINGW_PREFIX_DIR/bin:$PATH"
echo "gcc: $(command -v gcc) $(gcc -dumpmachine) $(gcc -dumpversion)  as: $(as --version | head -1)  m4: $(m4 --version | head -1)"
mkdir -p "$CFG" "$OBJ" && cd "$CFG"
"$SRC/configure" --build=$TRIPLE --host=$TRIPLE --enable-shared --disable-static $FAT_OPTION > configure.out 2>&1 || {
  echo "=== configure failed (exit $?)"; cat configure.out; tail -n 150 config.log; exit 91; }
grep -E "^(checking (for assembler|ABI|compiler)|config.status: linking)" configure.out
cd mpn
# The .asm.lo rule of mpn/Makefile, through mpn/m4-ccas: m4 with the -D
# options of COMPILE_FLAGS and libtool's pic_flag, then $(CCAS) on the result.
for stem in $ASM_STEMS; do
  echo "m4 -DHAVE_CONFIG_H -D__GMP_WITHIN_GMP -DOPERATION_$stem -DDLL_EXPORT -DPIC $stem.asm > tmp-$stem.s; gcc -c tmp-$stem.s -o $OBJ/$stem.o"
  m4 -DHAVE_CONFIG_H -D__GMP_WITHIN_GMP -DOPERATION_$stem -DDLL_EXPORT -DPIC $stem.asm > tmp-$stem.s || exit 92
  gcc -c tmp-$stem.s -o "$OBJ/$stem.o" || exit 93
  rm -f tmp-$stem.s
done
echo "=== assembled $(ls "$OBJ" | wc -l) files"
'''


def _bash_env(arch, src, cfg, obj, fat, stems):
    x64 = arch == "x64"
    env = dict(os.environ)
    env.update({
        "SRC_WIN": src, "CFG_WIN": cfg, "OBJ_WIN": obj,
        "TRIPLE": "x86_64-w64-mingw32" if x64 else "i686-w64-mingw32",
        "GCC_PKG": "mingw-w64-x86_64-gcc" if x64 else "mingw-w64-i686-gcc",
        "MINGW_PREFIX_DIR": "/mingw64" if x64 else "/mingw32",
        "FAT_OPTION": "--enable-fat" if fat else "",
        "ASM_STEMS": " ".join(stems),
        "MSYSTEM": "MSYS", "CHERE_INVOKING": "1",
    })
    return env


def configure_asm(src, work, arch, fat):
    """Run GMP's own configure for the MinGW host of the same CPU.

    cl has no assembler for GMP's m4/GNU-as sources, but the configure step
    and the assembly need no C compiler of the target: configure, run with
    the MinGW gcc of MSYS2 for <arch>-w64-mingw32 (the host the MinGW images
    of this family are built for), selects the CPU path, links the mpn
    sources into mpn/ and writes config.m4, config.h and gmp-mparam.h. Those
    choices are what this build takes; every C file is still compiled by cl.
    """
    cfg = os.path.join(work, "cfg")
    obj = os.path.join(work, "asmobj")
    bash = find_bash()
    # First pass: configure only (no assembly stems yet).
    env = _bash_env(arch, src, cfg, obj, fat, [])
    print("> %s -lc <configure for %s%s>" % (bash, env["TRIPLE"],
                                             " --enable-fat" if fat else ""),
          flush=True)
    result = subprocess.run([bash, "-lc", ASM_SCRIPT], env=env)
    if result.returncode != 0:
        raise SystemExit("configure of GMP for the assembly failed (exit %d)"
                         % result.returncode)
    mpn = os.path.join(cfg, "mpn")
    makefile = read_text(os.path.join(mpn, "Makefile"))
    match = re.search(r"^OFILES\s*=([^\n]*)", makefile, re.M)
    stems = [w.replace("$U.lo", "").replace(".lo", "")
             for w in match.group(1).split()]
    asm, c = [], []
    for stem in stems:
        if os.path.exists(os.path.join(mpn, stem + ".asm")):
            asm.append(stem)
        elif os.path.exists(os.path.join(mpn, stem + ".c")):
            c.append(stem)
        else:
            raise SystemExit("mpn/%s: neither .asm nor .c in the configured "
                             "tree" % stem)
    print("configured mpn: %d objects, %d assembly, %d C" % (
        len(stems), len(asm), len(c)), flush=True)
    print("ASM %s" % " ".join(asm))
    print("C %s" % " ".join(c))
    # Second pass: the configure is repeated (it is quick and idempotent) and
    # every assembly file goes through m4 and gcc -c, as the .asm.lo rule does.
    env = _bash_env(arch, src, cfg, obj, fat, asm)
    result = subprocess.run([bash, "-lc", ASM_SCRIPT], env=env)
    if result.returncode != 0:
        raise SystemExit("assembly of GMP's mpn files failed (exit %d)"
                         % result.returncode)
    configured = {}
    for line in read_text(os.path.join(cfg, "config.h")).splitlines():
        m = re.match(r"#define\s+((?:HAVE_NATIVE_|HAVE_HOST_CPU_FAMILY_|"
                     r"WANT_FAT_BINARY)\w*)\s+(.*)$", line)
        if m:
            configured[m.group(1)] = m.group(2).strip()
    print("from configure's config.h: %s" % ", ".join(sorted(configured)))
    objects = [os.path.join(obj, s + ".o") for s in asm]
    missing = [o for o in objects if not os.path.exists(o)]
    if missing:
        raise SystemExit("assembler left no object for %s" % missing[:5])
    return cfg, configured, c, objects


def find_bash():
    for candidate in (r"C:\msys64\usr\bin\bash.exe",):
        if os.path.exists(candidate):
            return candidate
    found = shutil.which("bash")
    if not found:
        raise SystemExit("no bash on this machine")
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--arch", required=True, choices=("x86", "x64"))
    parser.add_argument("--src", default=".", help="the unpacked gmp tree")
    parser.add_argument("--work", default="gmpbuild",
                        help="where generated files and objects go")
    parser.add_argument("--static", action="store_true",
                        help="build gmp.lib and gmp.h under --prefix, not a DLL")
    parser.add_argument("--prefix", default="")
    parser.add_argument("--asm", choices=("none", "native", "fat"),
                        default="none",
                        help="none: mpn/generic C (the default); native: the "
                             "assembly of configure's default CPU path for "
                             "<arch>-w64-mingw32; fat: --enable-fat, every "
                             "x86 CPU variant with CPUID dispatch")
    parser.add_argument("--cxx", action="store_true",
                        help="also build libgmpxx-4.dll (CXX_OBJECTS of "
                             "Makefile.in) against libgmp-10.dll")
    args = parser.parse_args()

    src = os.path.abspath(args.src)
    work = os.path.abspath(args.work)
    gen = os.path.join(work, "gen")
    os.makedirs(gen, exist_ok=True)

    configured = None
    if args.asm != "none":
        cfg, configured, asm_c, asm_objects = configure_asm(
            src, work, args.arch, fat=args.asm == "fat")
    version = write_config(src, gen, args.arch, configured)
    write_gmp_h(src, gen, args.arch, dll=not args.static)
    if configured is not None:
        # configure links the CPU path's gmp-mparam.h into the build root.
        shutil.copyfile(os.path.join(cfg, "gmp-mparam.h"),
                        os.path.join(gen, "gmp-mparam.h"))
    flags = ["/I" + gen, "/I" + src, "/DHAVE_CONFIG_H=1", "/D__GMP_WITHIN_GMP=1",
             "/D_CRT_SECURE_NO_WARNINGS", "/D_CRT_NONSTDC_NO_WARNINGS"]
    generated = build_generators(src, gen, args.arch, flags)

    makefile = read_text(os.path.join(src, "Makefile.in"))
    plain = []
    libgmp = re.search(r"^libgmp_la_SOURCES\s*=((?:[^\n]*\\\n)*[^\n]*)",
                       makefile, re.M).group(1).replace("\\\n", " ").split()
    plain += [w for w in libgmp if w.endswith(".c")]
    plain.append("tal-reent.c")
    for name in ("MPF_OBJECTS", "MPZ_OBJECTS", "MPQ_OBJECTS", "PRINTF_OBJECTS",
                 "SCANF_OBJECTS", "RANDOM_OBJECTS"):
        plain += object_list(makefile, name)
    # MPN_OBJECTS is just the two generated tables, compiled from gen/.
    tables = [n for n in object_list(makefile, "MPN_OBJECTS")]
    functions = mpn_functions(src)
    print("%d top-level/mpz/mpq/mpf/printf/scanf/rand sources, %d mpn "
          "functions, %d generated tables" % (len(plain), len(functions),
                                              len(tables)))

    objdir = os.path.join(work, "obj")
    jobs = []
    seen = set()
    for relative in plain:
        obj = os.path.join(objdir, relative[:-2].replace("/", "_") + ".obj")
        jobs.append((os.path.join(src, relative), obj, [], flags))
        seen.add(obj)
    for relative in tables:
        base = os.path.basename(relative)
        obj = os.path.join(objdir, "mpn_" + base[:-2] + ".obj")
        jobs.append((os.path.join(gen, base), obj, [], flags))
    if configured is None:
        for name, source in sorted(functions.items()):
            obj = os.path.join(objdir, "mpn_" + name + ".obj")
            jobs.append((os.path.join(src, "mpn", "generic", source + ".c"), obj,
                         ["/DOPERATION_" + name], flags))
    else:
        # The C half of the configured mpn/ (generic files the CPU path has
        # no assembly for, and with --enable-fat the fat_*.c wrappers and
        # fat.c), compiled by cl from the configured tree.
        for stem in asm_c:
            obj = os.path.join(objdir, "mpn_" + stem + ".obj")
            jobs.append((os.path.join(cfg, "mpn", stem + ".c"), obj,
                         ["/DOPERATION_" + stem], flags))
    os.makedirs(objdir, exist_ok=True)
    compile_all(jobs)
    objects = sorted(job[1] for job in jobs)
    if configured is not None:
        objects += asm_objects
    if len(objects) != len(set(objects)):
        raise SystemExit("object name collision")

    os.chdir(work)
    with open("objects.rsp", "w") as handle:
        handle.write("\n".join(objects) + "\n")
    if args.static:
        run(["lib", "/nologo", "/OUT:gmp.lib", "@objects.rsp"])
        prefix = os.path.abspath(args.prefix)
        os.makedirs(os.path.join(prefix, "include"), exist_ok=True)
        os.makedirs(os.path.join(prefix, "lib"), exist_ok=True)
        shutil.copyfile(os.path.join(gen, "gmp.h"),
                        os.path.join(prefix, "include", "gmp.h"))
        shutil.copyfile("gmp.lib", os.path.join(prefix, "lib", "gmp.lib"))
        print("gmp %s: static gmp.lib and gmp.h under %s" % (version, prefix))
    else:
        exports(objects, args.arch, "libgmp-10.def")
        command = ["link", "/nologo", "/DLL", "/DEBUG", "/Brepro",
                   "/INCREMENTAL:NO", "/OPT:NOREF", "/OPT:NOICF",
                   "/DEF:libgmp-10.def", "/PDB:libgmp-10.pdb",
                   "/OUT:libgmp-10.dll", "@objects.rsp"]
        print("> " + " ".join(command), flush=True)
        result = subprocess.run(command, capture_output=True, text=True)
        print(result.stdout + result.stderr, flush=True)
        if result.returncode != 0:
            # gmp.h gives cl `__inline` for its extern-inline functions
            # (mpn_add, mpz_neg, ...). Each object that calls one and does not
            # inline it carries a COMDAT copy, and the object that defines the
            # function out of line (the __GMP_FORCE_ file) carries a plain
            # one: LNK2005, for a function with a single definition in
            # meaning. If that is all that went wrong, link again letting the
            # first definition win.
            codes = set(re.findall(r"error (LNK\d+)", result.stdout + result.stderr))
            if codes and codes <= {"LNK2005", "LNK1169"}:
                print("only LNK2005/LNK1169 (the extern-inline functions of "
                      "gmp.h); linking again with /FORCE:MULTIPLE", flush=True)
                command.insert(1, "/FORCE:MULTIPLE")
                print("> " + " ".join(command), flush=True)
                result = subprocess.run(command, capture_output=True, text=True)
                print(result.stdout + result.stderr, flush=True)
        if result.returncode != 0:
            raise SystemExit("link of libgmp-10.dll failed")
        print("gmp %s: libgmp-10.dll" % version)
        if args.cxx:
            build_cxx(src, gen, work, makefile, args.arch)


def build_cxx(src, gen, work, makefile, arch):
    """libgmpxx: the C++ stream and limits wrapper, as --enable-cxx builds it.

    Its sources are CXX_OBJECTS of Makefile.in (cxx/*.cc), compiled with
    -D__GMP_WITHIN_GMPXX (what cxx/Makefile.am sets) so gmp.h marks their
    functions __declspec(dllexport), and linked against the import library
    of libgmp-10.dll; exports by the same every-defined-function rule.
    """
    match = re.search(r"^CXX_OBJECTS\s*=((?:[^\n]*\\\n)*[^\n]*)", makefile,
                      re.M)
    if not match:
        raise SystemExit("CXX_OBJECTS not found in Makefile.in")
    sources = [w[:-3] + ".cc" for w in
               match.group(1).replace("\\\n", " ").split() if w.endswith(".lo")]
    objdir = os.path.join(work, "objxx")
    os.makedirs(objdir, exist_ok=True)
    flags = ["/I" + gen, "/I" + src, "/DHAVE_CONFIG_H=1",
             "/D__GMP_WITHIN_GMPXX=1", "/EHsc", "/D_CRT_SECURE_NO_WARNINGS"]
    jobs = [(os.path.join(src, s), os.path.join(
        objdir, os.path.basename(s)[:-3] + ".obj"), [], flags) for s in sources]
    print("libgmpxx: %d sources: %s" % (len(jobs), " ".join(sources)))
    compile_all(jobs)
    objects = sorted(j[1] for j in jobs)
    exports(objects, arch, "libgmpxx-4.def")
    command = ["link", "/nologo", "/DLL", "/DEBUG", "/Brepro",
               "/INCREMENTAL:NO", "/OPT:NOREF", "/OPT:NOICF",
               "/DEF:libgmpxx-4.def", "/PDB:libgmpxx-4.pdb",
               "/OUT:libgmpxx-4.dll"] + objects + ["libgmp-10.lib"]
    run(command)
    print("libgmpxx-4.dll built")


if __name__ == "__main__":
    sys.exit(main())
