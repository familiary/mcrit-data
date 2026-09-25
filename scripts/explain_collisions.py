#!/usr/bin/env python3
"""Say what the cross-family PicHash collisions actually are.

``build_corpus.py validate --deep`` answers "how many functions appear under
three or more unrelated family names". That number is the alarm, not the
diagnosis, and on its own it is not actionable: 76 collisions before the two
rounds of runtime removal, 58 after, and neither figure says whether what is
left is compiler runtime leaking into library families or C++ header code
that genuinely is in every binary that uses it.

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

The classification itself lives in ``corpus/validate.py`` and is imported
from there, because ``validate --deep`` fails on exactly the bucket this
prints first. Two copies of that judgement would drift, and had begun to:
the first version of this script called ``std::__cxx11::basic_stringbuf``
leakage while validate called every collision a problem, so the two
disagreed about the same corpus on the same day.

    python scripts/explain_collisions.py
    python scripts/explain_collisions.py --min-instructions 20
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from corpus import config, validate


def _print_rows(rows):
    for pichash, collision in rows:
        print("  %4d ins  %-34s  %s"
              % (collision.num_instructions,
                 (sorted(collision.names)[0] if collision.names else "")[:34],
                 ", ".join(collision.families)[:70]))


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
    grouped = validate.group_cross_family_functions(root, args.min_instructions)
    total = sum(len(rows) for rows in grouped.values())
    print("cross-family PicHashes at >= %d instructions: %d\n"
          % (args.min_instructions, total))

    suspect = grouped[validate.LEAKAGE]
    print("LIKELY LEAKAGE - one symbol name across every family sharing it")
    print("(chase these: extend the baseline probe so they are recognised.")
    print(" these, and only these, fail validate --deep)")
    if not suspect:
        print("  none\n")
    _print_rows(suspect)
    print()

    print("EXPECTED - C++ standard library instantiated into each project")
    print("(%d hashes; every symbol sharing the hash is a libstdc++ one, so "
          "the same\n header really is in each of these binaries)"
          % len(grouped[validate.STDLIB]))
    print()

    print("EXPECTED - names differ between families, so not one function")
    print("(%d hashes; the instruction floor bounds these rather than removing them)"
          % len(grouped[validate.DIFFERENT_NAMES]))
    print()
    if grouped[validate.UNNAMED]:
        print("UNNAMED - %d hashes carry no symbol in any family"
              % len(grouped[validate.UNNAMED]))
    return 1 if suspect else 0


if __name__ == "__main__":
    sys.exit(main())
