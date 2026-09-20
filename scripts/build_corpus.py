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

from corpus import recipes, validate
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

    table = subparsers.add_parser("readme", help="render README table rows for a family")
    table.add_argument("family", help="corpus family, e.g. libzlib")

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

    if args.command == "readme":
        from corpus.readme import render_family
        print(render_family(args.family))
        return 0

    if args.command == "validate":
        problems = validate.validate_all(args.path)
        for problem in problems:
            print("FAIL %s" % problem)
        print("%d problem(s)" % len(problems))
        return 1 if problems else 0

    names = sorted(recipes.all_recipes()) if args.recipe == ["all"] else args.recipe
    failures = 0
    for name in names:
        results = run_recipe(recipes.get(name), args.toolchains, dry_run=args.dry_run)
        for result in results:
            status = result["status"]
            print("%-7s %s%s" % (status.upper(), result["name"],
                                 "" if status != "failed" else ": %s" % result["error"]))
            failures += status == "failed"
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
