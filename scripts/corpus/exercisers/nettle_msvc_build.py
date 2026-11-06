#!/usr/bin/env python3
"""Build Nettle's two shared libraries with cl, without running configure.

Nettle is autotools: ./configure writes config.h, version.h, config.make and
the elliptic-curve tables, and make compiles the lists of sources it names.
There is no shell, m4 or make on the runner that this could rely on, and the
assembly (GNU as syntax, run through m4) is not something cl can take at all,
so this does the same job in the order configure and make do it, from the
unmodified tree:

  1. config.h is config.h.in with each ``#undef NAME`` resolved the way
     config.status resolves it, from the small table below. version.h is
     version.h.in with its four @SUBSTITUTIONS@ filled. Both are written to
     ``gen/``, outside the upstream files, and found through /Igen.
  2. The ecc-*.h tables are produced the way make produces them: eccdata.c
     (it #includes mini-gmp.c) is compiled with cl and run once per
     ``ecc-<curve>.h: eccdata.stamp`` rule, with the arguments Makefile.in
     gives that rule. Nothing about the curves is written down here.
  3. The two source lists are read out of Makefile.in (``nettle_SOURCES`` and
     ``hogweed_SOURCES``), so one script serves every release and nothing in
     it names a file.
  4. Each library is compiled with the corpus flags and linked to a DLL
     whose export table is every defined external function in its objects,
     the rule MinGW's ld applies by default and the one lzo_msvc.py uses.
     libhogweed links against the import library of libnettle, as the real
     one does.

C only: ``--disable-assembler`` has no cl equivalent, so none of the x86_64
fat dispatch or AES-NI code exists in this build. mini-gmp is compiled into
libhogweed (``--enable-mini-gmp`` in the MinGW recipe), the only GMP-free
configuration upstream supports.

Every command is echoed before it runs so the runner's log shows the exact
flags.
"""

import argparse
import glob
import os
import re
import subprocess
import sys


# What configure would have probed, for cl on Windows. Anything config.h.in
# declares and this table does not mention stays undefined, which is what
# configure produces for a feature the platform lacks.
def _defines(arch, hogweed):
    table = {
        "HAVE_ALLOCA": "1",
        "HAVE_MALLOC_H": "1",
        "HAVE_INTTYPES_H": "1",
        "HAVE_STDINT_H": "1",
        "HAVE_STDIO_H": "1",
        "HAVE_STDLIB_H": "1",
        "HAVE_STRING_H": "1",
        "HAVE_SYS_STAT_H": "1",
        "HAVE_SYS_TYPES_H": "1",
        "STDC_HEADERS": "1",
        # LLP64: long is 32 bits on both x86 and x64 Windows, which also makes
        # mini-gmp's limb (an unsigned long) 32 bits on both.
        "SIZEOF_LONG": "4",
        "SIZEOF_SIZE_T": "8" if arch == "x64" else "4",
    }
    if hogweed:
        table["WITH_HOGWEED"] = "1"
    return table


LIMB_BITS = "32"


def run(command, **kwargs):
    print("> " + " ".join(command), flush=True)
    subprocess.run(command, check=True, **kwargs)


def read_list(text, name):
    """The value of a ``name = a.c b.c \\``-continued Makefile.in variable."""
    match = re.search(r"^%s\s*=((?:[^\n]*\\\n)*[^\n]*)" % re.escape(name),
                      text, re.M)
    if not match:
        return []
    return [word for word in match.group(1).replace("\\\n", " ").split()
            if word.endswith(".c")]


def write_config(arch, hogweed):
    defines = _defines(arch, hogweed)
    with open("config.h.in", encoding="utf-8") as handle:
        text = handle.read()
    seen = set()

    def resolve(match):
        name = match.group(2)
        seen.add(name)
        if name in defines:
            return "#%sdefine %s %s" % (match.group(1), name, defines[name])
        return "/* #undef %s */" % name

    text = re.sub(r"^#(\s*)undef (\w+)\s*$", resolve, text, flags=re.M)
    missing = sorted(set(defines) - seen)
    if missing:
        # A name that config.h.in does not declare is a name this release's
        # sources cannot be reading; say so rather than drop it silently.
        print("note: not declared by config.h.in: %s" % ", ".join(missing))
    with open(os.path.join("gen", "config.h"), "w", encoding="utf-8") as out:
        out.write(text)


def write_version(hogweed):
    if not os.path.exists("version.h.in"):
        return
    with open("configure.ac", encoding="utf-8") as handle:
        init = re.search(r"AC_INIT\(\[nettle\],\s*\[(\d+)\.(\d+)", handle.read())
    values = {"MAJOR_VERSION": init.group(1), "MINOR_VERSION": init.group(2),
              "NETTLE_USE_MINI_GMP": "1" if hogweed else "0",
              "GMP_NUMB_BITS": LIMB_BITS}
    with open("version.h.in", encoding="utf-8") as handle:
        text = handle.read()
    text = re.sub(r"@(\w+)@", lambda m: values[m.group(1)], text)
    with open(os.path.join("gen", "version.h"), "w", encoding="utf-8") as out:
        out.write(text)


def write_stdint():
    """nettle-stdint.h, which releases before 3.0 expect configure to write.

    configure builds it from the compiler's own <stdint.h> when there is one,
    which is what this is for cl: all the header has to do is include it.
    """
    if os.path.exists("nettle-stdint.h"):
        return
    for header in glob.glob("*.h"):
        with open(header, encoding="utf-8", errors="replace") as handle:
            if "nettle-stdint.h" in handle.read():
                with open(os.path.join("gen", "nettle-stdint.h"), "w") as out:
                    out.write("#include <stdint.h>\n")
                print("gen/nettle-stdint.h: includes <stdint.h>")
                return


def write_ecc_tables(makefile, flags):
    rules = re.findall(
        r"^(ecc-[\w-]+\.h):[^\n]*\n\t\./eccdata\$\(EXEEXT_FOR_BUILD\)([^>\n]*?)"
        r"\$\((?:GMP_)?NUMB_BITS\)\s*>", makefile, re.M)
    if not rules:
        raise SystemExit("no ecc table rules found in Makefile.in")
    run(["cl", "/nologo", "/O2", "/MD", "/Fe:eccdata.exe", "/Fo:eccdata.obj",
         "eccdata.c"] + flags)
    for header, args in rules:
        command = [os.path.abspath("eccdata.exe")] + args.split() + [LIMB_BITS]
        print("> %s > gen\\%s" % (" ".join(command), header), flush=True)
        result = subprocess.run(command, check=True, capture_output=True)
        with open(os.path.join("gen", header), "wb") as out:
            out.write(result.stdout)
    print("%d ecc tables generated" % len(rules))


def exports(objects, arch, path):
    names = set()
    for obj in objects:
        out = subprocess.check_output(["dumpbin", "/SYMBOLS", obj]).decode(
            "utf-8", "replace")
        for line in out.splitlines():
            tokens = line.split()
            if ("|" in tokens and "()" in tokens and "External" in tokens
                    and any(t.startswith("SECT") for t in tokens)):
                name = tokens[tokens.index("|") + 1]
                if arch == "x86" and name.startswith("_"):
                    name = name[1:]
                names.add(name)
    if not names:
        raise SystemExit("no exports found in %s" % ", ".join(objects[:3]))
    with open(path, "w") as handle:
        handle.write("EXPORTS\n" + "\n".join(sorted(names)) + "\n")
    print("%s: %d exports" % (path, len(names)))


def build_library(name, sources, arch, flags, libs):
    objdir = "obj_" + name
    os.makedirs(objdir, exist_ok=True)
    with open(name + ".rsp", "w") as handle:
        handle.write("\n".join(sources) + "\n")
    run(["cl", "/nologo", "/c", "/O2", "/MD", "/Zi", "/Fd%s.pdb" % name,
         "/Fo%s\\" % objdir] + flags + ["@%s.rsp" % name])
    objects = sorted(glob.glob(objdir + "\\*.obj")
                     if os.name == "nt" else glob.glob(objdir + "/*.obj"))
    if len(objects) != len(sources):
        raise SystemExit("%s: %d sources but %d objects"
                         % (name, len(sources), len(objects)))
    exports(objects, arch, name + ".def")
    with open(name + "_obj.rsp", "w") as handle:
        handle.write("\n".join(objects) + "\n")
    run(["link", "/nologo", "/DLL", "/DEBUG", "/Brepro", "/INCREMENTAL:NO",
         "/OPT:NOREF", "/OPT:NOICF", "/DEF:%s.def" % name,
         "/PDB:lib%s.pdb" % name, "/OUT:lib%s.dll" % name,
         "@%s_obj.rsp" % name] + libs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--arch", required=True, choices=("x86", "x64"))
    parser.add_argument("--no-hogweed", action="store_true",
                        help="libnettle only (2.7.1 has no mini-gmp option)")
    args = parser.parse_args()
    hogweed = not args.no_hogweed

    os.makedirs("gen", exist_ok=True)
    with open("Makefile.in", encoding="utf-8") as handle:
        makefile = handle.read()
    nettle = read_list(makefile, "nettle_SOURCES")
    hog = read_list(makefile, "hogweed_SOURCES")
    if not nettle or (hogweed and not hog):
        raise SystemExit("could not read the source lists from Makefile.in")
    print("%d libnettle sources, %d libhogweed sources" % (len(nettle), len(hog)))

    write_config(args.arch, hogweed)
    write_version(hogweed)
    write_stdint()

    # /DHAVE_CONFIG_H makes every file include gen/config.h, found through
    # /Igen; /I. is the source root itself. /utf-8 because the sources carry
    # a non-ASCII author name in their comments.
    flags = ["/Igen", "/I.", "/DHAVE_CONFIG_H=1", "/D_CRT_SECURE_NO_WARNINGS",
             "/utf-8"]
    if hogweed:
        write_ecc_tables(makefile, flags)

    build_library("nettle", nettle, args.arch, flags, [])
    if hogweed:
        build_library("hogweed", hog + ["mini-gmp.c"], args.arch, flags,
                      ["libnettle.lib"])
    print("done")


if __name__ == "__main__":
    sys.exit(main())
