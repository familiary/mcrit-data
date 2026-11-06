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


def replaced_functions(sources):
    """Sources configure adds through AC_REPLACE_FUNCS, which libc lacks.

    2.7.1 compiles memxor.c only because Windows has no memxor; later releases
    list it in nettle_SOURCES outright.
    """
    with open("configure.ac", encoding="utf-8") as handle:
        text = handle.read()
    extra = []
    for group in re.findall(r"AC_REPLACE_FUNCS\(\[?([^)\]]*)", text):
        for name in group.split():
            if os.path.exists(name + ".c") and name + ".c" not in sources:
                extra.append(name + ".c")
    return extra


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
    """Write the .def and return {data symbol: object} for the objects.

    The map is for the data a second DLL cannot import: see link_hogweed.
    """
    names = set()
    data = {}
    for obj in objects:
        out = subprocess.check_output(["dumpbin", "/SYMBOLS", obj]).decode(
            "utf-8", "replace")
        for line in out.splitlines():
            tokens = line.split()
            if not ("|" in tokens and "External" in tokens
                    and any(t.startswith("SECT") for t in tokens)):
                continue
            name = tokens[tokens.index("|") + 1]
            if "()" not in tokens:
                data[name] = obj
                continue
            if arch == "x86" and name.startswith("_"):
                name = name[1:]
            names.add(name)
    if not names:
        raise SystemExit("no exports found in %s" % ", ".join(objects[:3]))
    with open(path, "w") as handle:
        handle.write("EXPORTS\n" + "\n".join(sorted(names)) + "\n")
    print("%s: %d exports" % (path, len(names)))
    return data


def link(name, objects, libs):
    with open(name + "_obj.rsp", "w") as handle:
        handle.write("\n".join(objects) + "\n")
    command = ["link", "/nologo", "/DLL", "/DEBUG", "/Brepro", "/INCREMENTAL:NO",
               "/OPT:NOREF", "/OPT:NOICF", "/DEF:%s.def" % name,
               "/PDB:lib%s.pdb" % name, "/OUT:lib%s.dll" % name,
               "@%s_obj.rsp" % name] + libs
    print("> " + " ".join(command), flush=True)
    result = subprocess.run(command, capture_output=True, text=True)
    print(result.stdout + result.stderr, flush=True)
    return result


def build_library(name, sources, arch, flags, libs, data=None):
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
    defined = exports(objects, arch, name + ".def")
    result = link(name, objects, libs)
    if result.returncode != 0 and data:
        # libhogweed refers to data that libnettle defines (the nettle_sha256
        # family of hash descriptors). A DLL can export data, but cl code can
        # only reach it through __declspec(dllimport), which the headers do
        # not carry and which this build does not add; MinGW's ld has
        # auto-import for the case, link.exe does not. The descriptors are
        # const tables of names, sizes and function pointers, so the objects
        # that define them are linked in whole (their code is none) and the
        # functions they point at still resolve through libnettle's import
        # library. Only what the linker names as unresolved is pulled in.
        wanted = set(re.findall(r"unresolved external symbol (\S+)",
                                result.stdout + result.stderr))
        if wanted and wanted <= set(data):
            extra = sorted({data[symbol] for symbol in wanted})
            print("pulling in %d libnettle object(s) for data: %s"
                  % (len(extra), ", ".join(extra)), flush=True)
            result = link(name, objects + extra, libs)
    if result.returncode != 0:
        raise SystemExit("link of lib%s.dll failed" % name)
    return defined


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
    nettle += replaced_functions(nettle)
    print("%d libnettle sources, %d libhogweed sources" % (len(nettle), len(hog)))

    write_config(args.arch, hogweed)
    write_version(hogweed)
    write_stdint()

    # /DHAVE_CONFIG_H makes every file include gen/config.h, found through
    # /Igen; /I. is the source root itself. /utf-8 because the sources carry
    # a non-ASCII author name in their comments.
    flags = ["/Igen", "/I.", "/DHAVE_CONFIG_H=1", "/D_CRT_SECURE_NO_WARNINGS",
             "/utf-8"]
    with open("nettle-types.h", encoding="utf-8") as handle:
        if "stdalign.h" in handle.read():
            # 4.0 uses C11 alignas. cl only ships <stdalign.h> under /std:c11,
            # and that mode defines __STDC__, which hides the CRT's
            # non-standard names (alloca among them) unless asked.
            flags += ["/std:c11", "/D_CRT_DECLARE_NONSTDC_NAMES=1"]
    if hogweed:
        write_ecc_tables(makefile, flags)

    data = build_library("nettle", nettle, args.arch, flags, [])
    if hogweed:
        build_library("hogweed", hog + ["mini-gmp.c"], args.arch, flags,
                      ["libnettle.lib"], data)
    print("done")


if __name__ == "__main__":
    sys.exit(main())
