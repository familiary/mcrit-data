#!/usr/bin/env python3
"""Generate MCRIT reference data from unmodified upstream source.

  python scripts/build_corpus.py list
  python scripts/build_corpus.py list --toolchain msvc_x64 --names-only
  python scripts/build_corpus.py build libzlib_1.3.1 [--toolchain mingw_x86]
  python scripts/build_corpus.py validate [data/libzlib]
  python scripts/build_corpus.py readme libzlib
"""

import argparse
import logging
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from corpus import config, recipes, validate
from corpus.pipeline import run_recipe
from corpus.toolchain import available_toolchains, canonical_alias


def _normalise_toolchain(toolchain_id):
    """Fold a versioned toolchain id onto its version-less alias.

    corpus.toolchain registers each compiler twice: under the concrete id it
    detected (``msvc143_x64``, ``mingw13_x86``) and under a stable alias that
    does not name the version (``msvc_x64``). Recipes use the alias, but the
    concrete id is a legal thing for one to declare, and a selector that
    matched only one spelling would silently drop such a recipe out of a CI
    leg rather than say so.

    The Linux toolchain is registered under two aliases rather than one -
    ``gcc_x64`` after its compiler and ``linux_x64`` after its target - so
    the fold is corpus.toolchain's rather than a regex here; see
    canonical_alias.
    """
    return canonical_alias(toolchain_id)


def _select_recipes(toolchain_ids):
    """Recipes declaring any of ``toolchain_ids``; all of them when empty.

    Matching is on what a recipe *declares*, deliberately not on what this
    host can run: an MSVC developer environment targets one architecture at a
    time, so the x86 runner never registers msvc_x64 and asking it which
    recipes the x64 leg should build has to still give the right answer.
    """
    registry = recipes.all_recipes()
    if not toolchain_ids:
        return registry
    wanted = {_normalise_toolchain(t) for t in toolchain_ids}
    return {name: recipe for name, recipe in registry.items()
            if wanted & {_normalise_toolchain(t) for t in recipe.toolchains}}


def _one_line(text, limit=300):
    """Flatten an error for the end-of-run summary.

    The summary is meant to be read at a glance; a multi-line or multi-hundred
    character message there pushes the other failures off the screen, which is
    the opposite of what it is for. The full text is still on the per-artefact
    line above and in build/<name>.log.
    """
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit - 3] + "..."


def _families_of(recipe):
    """Corpus families a recipe files artefacts under.

    Artifact.family overrides the recipe's for a vendored project, and
    corpus.pipeline files each artefact - and writes its provenance - under
    the artefact's family, so that is what names a data/ directory.
    """
    families = {artifact.family or recipe.family for artifact in recipe.artifacts}
    return families or {recipe.family}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    listing = subparsers.add_parser("list", help="show known recipes and toolchains")
    listing.add_argument("--toolchain", action="append", dest="toolchains",
                         metavar="ID",
                         help="restrict the listing to recipes that declare "
                              "this toolchain (repeatable). Matched against "
                              "what the recipe declares, not against what "
                              "this host has, so CI can ask one runner what "
                              "the other architecture's leg should build")
    listing.add_argument("--names-only", action="store_true",
                         help="print one recipe name per line and nothing "
                              "else, for feeding straight back into `build`")
    listing.add_argument("--families-only", action="store_true",
                         help="print one corpus family per line and nothing "
                              "else; a family appears once however many "
                              "recipes or artefacts file into it")

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
        if args.names_only and args.families_only:
            parser.error("--names-only and --families-only are mutually exclusive")
        selected = _select_recipes(args.toolchains)
        # An empty selection from an explicit filter is a mistyped toolchain id
        # or a recipe set that lost its last MSVC entry. Printing nothing and
        # exiting 0 would let a caller build nothing and call it success, which
        # is the failure mode this whole selector exists to remove.
        if args.toolchains and not selected:
            print("no recipe declares any of: %s" % ", ".join(args.toolchains),
                  file=sys.stderr)
            return 1
        if args.names_only:
            for name in sorted(selected):
                print(name)
            return 0
        if args.families_only:
            families = set()
            for recipe in selected.values():
                families |= _families_of(recipe)
            for family in sorted(families):
                print(family)
            return 0
        print("toolchains: %s" % ", ".join(available_toolchains()))
        print("recipes:")
        for name in sorted(selected):
            recipe = selected[name]
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
    failed = []
    produced = 0
    for name in names:
        try:
            recipe = recipes.get(name)
        except KeyError:
            # KeyError's body lists every recipe there is, which is a
            # screenful once thirty families are registered; the useful part
            # is the name that was wrong. `list` still has the full set.
            error = "unknown recipe %r, see `build_corpus.py list`" % name
            failed.append({"name": name, "reason": "recipe", "error": error})
            print("%-7s %s: %s" % ("FAILED", name, error))
            continue
        try:
            results = run_recipe(recipe, args.toolchains, dry_run=args.dry_run)
        except Exception as error:  # noqa: BLE001 - see below
            # A bug reached through a path run_recipe does not itself guard
            # used to abort every recipe still queued behind it. With thirty
            # recipes in a run that costs a whole CI cycle for everyone, so it
            # is recorded as this recipe's failure and the rest still run.
            # Nothing is swallowed: the traceback goes to stderr and the run
            # still exits non-zero.
            traceback.print_exc()
            failed.append({"name": name, "reason": "recipe", "error": str(error)})
            print("%-7s %s: %s" % ("FAILED", name, error))
            continue
        for result in results:
            status = result["status"]
            print("%-7s %s%s" % (status.upper(), result["name"],
                                 "" if status != "failed" else ": %s" % result["error"]))
            if status == "failed":
                failed.append(result)
            produced += status in ("ok", "fetched")
    # A baseline probe that would not compile is not a failure of any one
    # recipe - it costs precision in the compiler-runtime filter and nothing
    # else - so it does not appear above and never stopped a build. But every
    # artefact this run produced was then filtered against a smaller baseline
    # than the corpus is supposed to have, and nothing about the files says
    # so afterwards. Reported here, and fatal, for the reasons recorded at
    # baseline.probe_failures.
    from corpus.baseline import probe_failures

    broken_probes = probe_failures()
    if broken_probes:
        print("")
        print("baseline probe(s) did not build, so this run's artefacts were "
              "filtered against an incomplete compiler-runtime set:")
        for toolchain_id, names in broken_probes.items():
            print("  %s: %s" % (toolchain_id, ", ".join(names)))
        print("the compiler's own error is in the log above, at WARNING")

    if failed or broken_probes:
        # Repeated here because the per-artefact line above scrolls past
        # thousands of lines of compiler output. The last screen of the run is
        # the only place a reader reliably looks, so that is where the list of
        # what broke, and why, has to be.
        if failed:
            print("")
            print("%d artefact(s) failed:" % len(failed))
            for result in failed:
                print("  %s (%s): %s" % (result["name"],
                                         result.get("reason", "unknown"),
                                         _one_line(result.get("error", ""))))
        if produced:
            print("%d artefact(s) did build; they are still usable, but this "
                  "run is a failure." % produced)
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
