#!/usr/bin/env python3
"""Re-derive the descriptive provenance fields from the recipes.

  python scripts/refresh_provenance.py [--check] [family ...]

data/<family>/provenance.json is written at build time by copying fields off
the recipe, so a recipe whose ``license``, ``build_flags``, ``upstream`` or
``notes`` turns out to be wrong keeps handing out the wrong answer from the
records already committed, no matter how the recipe is corrected afterwards.
Rebuilding a family to repair a metadata string would cost hours of compiling
and disassembly to change nothing in the artefact: the binary, its sha256 and
every recovered function are identical either way. This rewrites just those
four strings in place instead.

It is not a substitute for regenerating a family whose build actually
changed. The moment a source pin, a build step, a compiler, a toolchain or a
feature flag moves, the artefact itself is different and the reports have to
be rebuilt - this script would then only paper a new description over old
disassembly. Use it for corrections to how a build is described, never for
corrections to how it is performed.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from corpus import config, recipes


# Everything else in an entry - digests, source pin, compiler, counts, paths,
# the removed-function list - records what happened during a build and cannot
# be re-derived from a recipe without redoing that build.
REFRESHED_FIELDS = ("license", "build_flags", "upstream", "notes")


class Unmatched(Exception):
    """An entry no recipe accounts for, reported rather than guessed at."""


def _index():
    """Map (family, version) to the recipes that produce it.

    Keyed on the artefact's family rather than the recipe's, because a recipe
    may attribute an artefact to a different family than its own.
    """
    index = {}
    for name, recipe in recipes.all_recipes().items():
        for artifact in recipe.artifacts:
            family = artifact.family or recipe.family
            index.setdefault((family, recipe.version), {})[name] = recipe
    return {key: list(value.items()) for key, value in index.items()}


def _pick_artifact(recipe, entry):
    """Find the artefact an entry came from, for its build_flags override."""
    component = entry.get("component", "")
    matching = [a for a in recipe.artifacts if a.component == component]
    if len(matching) == 1:
        return matching[0]
    if not matching and len(recipe.artifacts) == 1:
        # Older entries of single-artefact recipes may carry a component
        # derived from the path rather than a declared one.
        return recipe.artifacts[0]
    raise Unmatched("component %r matches %d artefacts of the recipe"
                    % (component, len(matching)))


def _resolve(index, family, entry):
    version = entry.get("version")
    candidates = index.get((family, version), [])
    if not candidates:
        raise Unmatched("no recipe produces %s %s" % (family, version))
    if len(candidates) > 1:
        raise Unmatched("ambiguous: %s %s is produced by %s"
                        % (family, version, ", ".join(n for n, _ in candidates)))
    _, recipe = candidates[0]
    return recipe, _pick_artifact(recipe, entry)


def _desired(recipe, artifact):
    return {
        "license": recipe.license,
        "build_flags": artifact.build_flags or recipe.build_flags,
        "upstream": recipe.upstream,
        # The pipeline omits the key entirely when a recipe has no notes, so
        # a note that has been dropped from a recipe has to be dropped here
        # too rather than left behind as a stale string.
        "notes": recipe.notes or None,
    }


def refresh_family(family, path, check=False):
    """Rewrite one provenance file. Returns (changes, problems)."""
    with open(path, encoding="utf-8") as handle:
        entries = json.load(handle)
    index = _index()
    changes = []
    problems = []
    for slug in sorted(entries):
        entry = entries[slug]
        try:
            recipe, artifact = _resolve(index, family, entry)
        except Unmatched as error:
            problems.append("%s: %s" % (slug, error))
            continue
        for field, value in _desired(recipe, artifact).items():
            current = entry.get(field)
            if current == value:
                continue
            changes.append((slug, field, current, value))
            if value is None:
                entry.pop(field, None)
            else:
                entry[field] = value
    if changes and not check:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(entries, handle, indent=2, sort_keys=True)
            handle.write("\n")
    return changes, problems


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("family", nargs="*",
                        help="families to refresh, default every family that "
                             "has a provenance.json")
    parser.add_argument("--check", action="store_true",
                        help="report what would change, write nothing")
    args = parser.parse_args()

    families = args.family
    if not families:
        families = sorted(name for name in os.listdir(config.DATA_DIR)
                          if os.path.exists(os.path.join(config.DATA_DIR, name,
                                                         "provenance.json")))

    total_changes = 0
    total_problems = 0
    for family in families:
        path = os.path.join(config.DATA_DIR, family, "provenance.json")
        if not os.path.exists(path):
            print("%s: no provenance.json" % family)
            total_problems += 1
            continue
        changes, problems = refresh_family(family, path, check=args.check)
        for slug, field, old, new in changes:
            print("%s: %s" % (family, slug))
            print("    %s: %r" % (field, old))
            print("    %s-> %r" % (" " * len(field), new))
        for problem in problems:
            print("%s: UNMATCHED %s" % (family, problem))
        total_changes += len(changes)
        total_problems += len(problems)

    verb = "would change" if args.check else "changed"
    print("\n%d field(s) %s across %d family/families; %d entry/entries "
          "could not be matched to a recipe" % (total_changes, verb,
                                                len(families), total_problems))
    # An unmatched entry is a real inconsistency between data/ and the
    # recipes, so it has to be visible to a caller, not only in the log.
    return 1 if total_problems else 0


if __name__ == "__main__":
    sys.exit(main())
