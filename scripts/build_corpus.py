#!/usr/bin/env python3
"""Generate MCRIT reference data from unmodified upstream source.

  python scripts/build_corpus.py list
  python scripts/build_corpus.py build libzlib_1.3.1 [--toolchain mingw_x86]
  python scripts/build_corpus.py validate [data/libzlib]
  python scripts/build_corpus.py readme libzlib
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from corpus import config, recipes, validate
from corpus.pipeline import run_recipe
from corpus.toolchain import available_toolchains


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="show known recipes and toolchains")

    build = subparsers.add_parser("build", help="run one or more recipes")
    build.add_argument("recipe", nargs="+", help="recipe name, or 'all'")
    build.add_argument("--toolchain", action="append", dest="toolchains",
                       help="restrict to this toolchain (repeatable)")
    build.add_argument("--dry-run", action="store_true",
                       help="fetch sources and stop, to check provenance only")

    check = subparsers.add_parser("validate", help="check generated artefacts")
    check.add_argument("path", nargs="?", help="directory to check, default data/")
    check.add_argument("--deep", action="store_true",
                       help="also look for PicHashes shared across families, "
                            "which is how statically linked code leaks in "
                            "under the wrong name; loads every .mcrit. Fails "
                            "only on hashes carrying one symbol name across "
                            "every family sharing them - the kind that has "
                            "been misattribution every time - and reports "
                            "the other kinds as notes")
    check.add_argument("--strict", action="store_true",
                       help="also fail on problems in the families this "
                            "tooling does not generate (data/MSVC, "
                            "data/Golang and the rest of the IDA-derived "
                            "data, which carry no provenance.json). They are "
                            "reported as notes either way")
    check.add_argument("--min-instructions", type=int, default=None,
                       metavar="N",
                       help="with --deep, ignore shared functions shorter "
                            "than N instructions (default %d). Short bodies "
                            "collide across unrelated projects for reasons "
                            "that are not leakage. 0 counts everything."
                            % config.MIN_CROSS_FAMILY_INSTRUCTIONS)

    again = subparsers.add_parser(
        "reprocess",
        help="recompute the statistics block of committed reports in place")
    again.add_argument("family", nargs="*", help="families, default all")

    sift = subparsers.add_parser(
        "refilter",
        help="re-apply the compiler-runtime filter to committed reports, for "
             "when the measured baseline has improved since they were built")
    sift.add_argument("family", nargs="*", help="families, default all")
    sift.add_argument("--dry-run", action="store_true",
                      help="report what would be dropped without writing")

    table = subparsers.add_parser("readme", help="render README table rows for a family")
    table.add_argument("family", nargs="?", help="corpus family, e.g. libzlib")
    table.add_argument("--update", action="store_true",
                       help="rewrite every fenced table in README.md in place")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.command == "list":
        print("toolchains: %s" % ", ".join(available_toolchains()))
        print("recipes:")
        for name in sorted(recipes.all_recipes()):
            recipe = recipes.get(name)
            print("  %-28s %s %s -> %s" % (name, recipe.family, recipe.version,
                                           ", ".join(recipe.toolchains)))
        return 0

    if args.command == "reprocess":
        from corpus.reprocess import reprocess
        changes, failures = reprocess(args.family or None)
        for failure in failures:
            print("FAIL %s" % failure)
        print("%d report(s) corrected" % len(changes))
        # A report left half-corrected, or not corrected at all, means a .7z
        # and its .mcrit may now describe the same sample differently. That is
        # what this command exists to prevent, so it must not be reported as
        # success.
        if failures:
            print("%d report(s) could not be corrected" % len(failures))
            return 1
        return 0

    if args.command == "refilter":
        from corpus.refilter import refilter
        changes, failures, examined = refilter(args.family or None,
                                               dry_run=args.dry_run)
        for failure in failures:
            print("FAIL %s" % failure)
        dropped = sum(len(names) for _, names in changes)
        print("%d artefact(s) %s, %d function(s)"
              % (len(changes), "would change" if args.dry_run else "corrected",
                 dropped))
        # "0 corrected" means one of two opposite things: the corpus is already
        # filtered, or nothing here could be opened - a mistyped family name, a
        # host whose MinGW is a different major than the one the records name.
        # Both printed the same line and exited 0, so the second read as the
        # first. Only the count of artefacts actually examined separates them.
        if not examined:
            print("no artefact was examined: every family was skipped, either "
                  "because it was not named correctly or because this host "
                  "cannot measure the toolchain its records were built with")
            return 1
        # Same reasoning as reprocess: an artefact corrected in one of the
        # three files that describe it and not the others is worse than one
        # left alone, so a partial run must not look like success.
        if failures:
            print("%d artefact(s) could not be corrected" % len(failures))
            return 1
        return 0

    if args.command == "readme":
        from corpus.readme import render_family, update_readme
        if args.update:
            changed = update_readme()
            print("updated: %s" % ", ".join(changed) if changed
                  else "README is already up to date")
            return 0
        if not args.family:
            parser.error("readme needs a family, or --update")
        print(render_family(args.family))
        return 0

    if args.command == "validate":
        notes = []
        problems = validate.validate_all(
            args.path, deep=args.deep, min_instructions=args.min_instructions,
            strict=args.strict, notes=notes)
        # Notes first: they are the context for the FAIL lines, and a reader
        # who sees "0 problem(s)" at the bottom should not have to scroll back
        # past them to find out what was checked and what was excused.
        for note in notes:
            print("NOTE %s" % note)
        for problem in problems:
            print("FAIL %s" % problem)
        print("%d problem(s)" % len(problems))
        return 1 if problems else 0

    names = sorted(recipes.all_recipes()) if args.recipe == ["all"] else args.recipe
    failures = 0
    produced = 0
    for name in names:
        results = run_recipe(recipes.get(name), args.toolchains, dry_run=args.dry_run)
        for result in results:
            status = result["status"]
            print("%-7s %s%s" % (status.upper(), result["name"],
                                 "" if status != "failed" else ": %s" % result["error"]))
            failures += status == "failed"
            produced += status in ("ok", "fetched")
    if failures:
        return 1
    # A run where every recipe was skipped exits non-zero too. Otherwise a host
    # whose cross compilers are missing prints a screen of SKIPPED and reports
    # success, and CI cannot tell "nothing to do" from "nothing worked".
    if not produced:
        print("no artefacts were produced: every requested build was skipped")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
