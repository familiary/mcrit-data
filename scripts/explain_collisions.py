#!/usr/bin/env python3
"""Say what the cross-family PicHash collisions actually are.

``build_corpus.py validate --deep`` answers "how many functions appear under
three or more unrelated family names". That number is the alarm, not the
diagnosis, and on its own it is not actionable: it was 754 before the
instruction floor, 97 after, 79 today, and none of those figures says whether
what is left is compiler runtime leaking into library families or C++ header
code that genuinely is in every binary that uses it.

This groups the survivors by what they are called, which is the thing that
distinguishes the two. It is how both rounds of leakage on this branch were
found:

* The six libgcc division helpers turned up as one symbol name repeated
  across Lua, OpenSSL, 7-Zip and libstdc++ - the same function, under four
  project names, which is misattribution.
* ``floor``, ``sin``, ``cos``, ``frexp``, ``modf``, ``atan2``, the two
  ``time_t`` widths of ``gmtime_s``/``localtime_s`` and ``_emu_vscprintf``
  turned up the same way, and ``floor`` was additionally shared with
  data/MinGW itself, which is as direct a demonstration as the corpus
  offers. The probe was already calling those functions; GCC was folding
  them as builtins at -O2, so their library bodies never entered the
  baseline.

What it should NOT find, and what is expected to remain:

* ``std::vector<T>::_M_realloc_insert``, ``std::_Rb_tree``,
  ``std::basic_string`` and friends. libstdc++ instantiates these into every
  project that uses them and the code is identical for any pointer-sized T,
  so the sharing is real rather than mistaken.
* Short bodies - ten to seventeen instructions - whose names differ entirely
  between the families sharing them. Those are not one function under
  several names; they are different functions that happen to hash alike, and
  the instruction floor bounds that rather than removing it.

The rule of thumb: a hash whose symbol name is the SAME across families is
leakage worth chasing; one whose names DIFFER is a coincidence worth
ignoring.

    python scripts/explain_collisions.py
    python scripts/explain_collisions.py --min-instructions 20
"""

import argparse
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from corpus import config


def _iter_exports(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for filename in sorted(filenames):
            if filename.endswith(".mcrit"):
                yield os.path.join(dirpath, filename)


def collect(root, min_instructions):
    """{pichash: (families, size, names)} for hashes shared by 3+ families."""
    by_hash, sizes, names = {}, {}, {}
    decompress = None
    for path in _iter_exports(root):
        with open(path, encoding="utf-8") as handle:
            try:
                export = json.load(handle)
            except ValueError:
                continue
        compressed = (export.get("content") or {}).get("is_compressed")
        samples = export.get("sample_entries") or {}
        for sha256, blob in (export.get("function_entries") or {}).items():
            family = (samples.get(sha256) or {}).get("family") or "(unknown)"
            if compressed:
                if decompress is None:
                    from mcrit.libs.utility import decompress_decode as decompress
                entries = json.loads(decompress(blob))
            else:
                entries = blob
            for entry in entries.values():
                pichash = entry.get("pichash")
                size = entry.get("num_instructions") or 0
                if not pichash or size < min_instructions:
                    continue
                by_hash.setdefault(pichash, set()).add(family)
                sizes[pichash] = size
                if entry.get("function_name"):
                    names.setdefault(pichash, set()).add(entry["function_name"])
    return {h: (sorted(f), sizes[h], sorted(names.get(h) or []))
            for h, f in by_hash.items() if len(f) >= 3}


def _same_symbol(found):
    """Whether every family calls this function by the same name.

    Compared with a leading underscore stripped, because the 32-bit MinGW ABI
    decorates cdecl symbols with one and the 64-bit ABI does not - the same
    function is "_floor" in one artefact and "floor" in another, and treating
    those as different names would hide exactly what this looks for.
    """
    bare = {name.lstrip("_") for name in found}
    return len(bare) == 1


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", help="directory, default data/")
    parser.add_argument("--min-instructions", type=int,
                        default=config.MIN_CROSS_FAMILY_INSTRUCTIONS,
                        metavar="N", help="ignore shorter functions (default %(default)s)")
    args = parser.parse_args()

    root = args.path or config.DATA_DIR
    shared = collect(root, args.min_instructions)
    print("cross-family PicHashes at >= %d instructions: %d\n"
          % (args.min_instructions, len(shared)))

    suspect, benign, unnamed = [], [], []
    for pichash, (families, size, found) in shared.items():
        if not found:
            unnamed.append((pichash, families, size, found))
        elif _same_symbol(found):
            suspect.append((pichash, families, size, found))
        else:
            benign.append((pichash, families, size, found))

    print("LIKELY LEAKAGE - one symbol name across every family sharing it")
    print("(chase these: extend the baseline probe so they are recognised)")
    if not suspect:
        print("  none\n")
    for pichash, families, size, found in sorted(suspect, key=lambda r: -r[2]):
        print("  %4d ins  %-34s  %s" % (size, sorted(found)[0][:34],
                                        ", ".join(families)[:70]))
    print()

    print("EXPECTED - names differ between families, so not one function")
    print("(%d hashes; the instruction floor bounds these rather than removing them)"
          % len(benign))
    templates = [r for r in benign
                 if any("std::" in n or "__gnu_cxx" in n for n in r[3])]
    print("  of which C++ standard library instantiations: %d" % len(templates))
    print()
    if unnamed:
        print("UNNAMED - %d hashes carry no symbol in any family" % len(unnamed))
    return 1 if suspect else 0


if __name__ == "__main__":
    sys.exit(main())
