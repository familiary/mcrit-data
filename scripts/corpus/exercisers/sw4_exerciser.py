"""Derive a SysWhispers4 exerciser from the header the generator just wrote.

Three things make a fixed exerciser unusable for this generator.

The resolver is `static`. SysWhispers4 emits ``SW4_HashStr``,
``SW4_GetNtdllBase``, ``SW4_GetProcByHash``, ``SW4_SortExports``,
``SW4_FindSection`` and the resolver proper (``SW4_FreshyCalls``,
``SW4_HellsGate``, ...) with internal linkage, reachable only from
``SW4_Initialize``. Nothing of them is in a DLL unless something calls that.

Which entry points exist depends on the flags. ``--etw-bypass`` adds
``SW4_PatchEtw``, ``--veh-encrypt`` adds ``SW4_VehEncryptInit`` and
``SW4_VehEncryptShutdown``, and so on for eleven flags; the stub list follows
``--preset``, which ranges from 24 functions to 86. A file naming them would
have to be rewritten per variant and would silently drop whatever it missed.

And the names are prefixed. ``--prefix`` renames every generated identifier,
so the exerciser cannot hardcode ``SW4_``.

So it is derived: every ``EXTERN_C`` declaration in the generated header gets
its address taken through a volatile sink, and ``<prefix>Initialize`` is
called so the static resolver chain is reachable. Addresses as well as calls
because the stubs are reached by nothing else and -O2 would otherwise fold
the lot away.

Nothing here is ever run. The DLL is compiled and disassembled only, so the
arguments are whatever makes a declaration resolve, and several would be
meaningless if anything did call them.
"""

import re
import sys


def main():
    header, output, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
    # Optional fourth argument: a prefix whose declarations are NOT
    # referenced. Needed for --arch wow64, whose MASM declares each stub as a
    # bare "NAME PROC" with no parameter list, so under ".model flat,
    # stdcall" ml decorates it @0 while the generated header declares it
    # NTAPI and cl asks the linker for @16, @44 and so on. Nothing can match
    # both, and the mismatch is in the generator's own output.
    #
    # Skipping the references costs nothing: the stub object is named on the
    # link line rather than pulled from a library, and these recipes link
    # /OPT:NOREF, so every PROC in it stays in the image whether anything
    # refers to it or not.
    skip = sys.argv[4] if len(sys.argv) > 4 else None
    text = open(header, encoding="utf-8", errors="replace").read()

    # EXTERN_C <ret> [NTAPI] <prefix><name>(<args>);  - the generator writes
    # every public declaration in that one shape, stubs and helpers alike.
    decls = re.findall(
        r"EXTERN_C\s+(.+?)\s+(?:NTAPI\s+)?(" + re.escape(prefix) +
        r"[A-Za-z0-9_]+)\s*\(.*?\)\s*;", text, re.S)
    names = []
    for _ret, name in decls:
        if name not in names:
            names.append(name)
    if not names:
        raise SystemExit("%s declares no %s* entry points" % (header, prefix))

    init = prefix + "Initialize"
    lines = [
        '#include "%s"' % header.replace("\\", "/").rsplit("/", 1)[-1],
        '#include "corpus_export.h"',
        "",
        "/* Volatile: taking each address through it keeps every stub in the",
        "   image and stops the optimiser folding the references away. */",
        "static void* volatile corpus_sink;",
        "",
        "CORPUS_EXPORT int corpus_exercise(void)",
        "{",
        "    int acc = 0;",
    ]
    if init in names:
        lines.append("    acc += %s() ? 1 : 0;" % init)
    for name in names:
        if name == init:
            continue
        if skip and name.startswith(skip):
            continue
        lines.append("    corpus_sink = (void*)&%s;" % name)
    lines += [
        "    return acc + (corpus_sink != 0);",
        "}",
        "",
    ]
    open(output, "w", encoding="utf-8").write("\n".join(lines))
    stubs = sum(1 for n in names if n.startswith(prefix + "Nt"))
    print("%s: %d stubs%s, %d other entry points"
          % (output, stubs, " (not referenced)" if skip else "",
             len(names) - stubs))


main()
