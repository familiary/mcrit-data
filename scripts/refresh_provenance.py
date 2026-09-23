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

That distinction is easy to lose because ``--check`` cannot tell the two
apart; it reports a ``build_flags`` string that no longer matches the recipe
either way. A live example: adding ``/INCREMENTAL:NO`` to seven MSVC link
lines made ``--check`` report 17 ``build_flags`` fields as out of date, and
running it would have stamped the new flag onto reports of binaries linked
without it - the artefacts had to be rebuilt instead. If a recipe edit
changed what the compiler or linker does, rebuild the family and do not run
this.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from corpus import config, package, recipes
from corpus.toolchain import canonical_alias


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
    # No fallback for an entry whose component names no artefact of the
    # recipe: the pipeline records artifact.component verbatim, so such an
    # entry means the recipe has been changed out from under data/ - which is
    # a mismatch to report, not one to guess a build_flags override through.
    raise Unmatched("component %r matches %d artefacts of the recipe"
                    % (component, len(matching)))


def _toolchain_of(slug, family, version):
    """The toolchain alias a slug names, e.g. "mingw_x64"; None if unreadable.

    Recipe.slug builds the stem as
    ``<family>_<version>_<producer><producer-version>_<arch>_<component>``,
    and family and component both legitimately contain underscores
    (nlohmann_json, event_core.dll), so the segment is taken by removing the
    known prefix rather than by counting underscores from either end. The
    producer's version digits are dropped because that is how recipes spell
    a toolchain: the slug says mingw13, the recipe declares mingw_x86.

    Dropping the digits is not always enough. The Linux toolchain's producer
    segment is "gcc13" and the alias its recipes declare is "linux_x64" -
    named after the target rather than the compiler, because that is what is
    different about it - so the fold goes through corpus.toolchain, which
    owns that correspondence. Without it every family that has both a MinGW
    and a Linux recipe for one version (all four of the string obfuscators)
    would be unresolvable: two candidates, and a slug that narrows to
    neither.
    """
    prefix = "%s_%s_" % (family, version)
    if not version or not slug.startswith(prefix):
        return None
    rest = slug[len(prefix):].split("_")
    if len(rest) < 2 or rest[1] not in ("x86", "x64"):
        return None
    return canonical_alias("%s_%s" % (re.sub(r"\d+$", "", rest[0]), rest[1]))


def _resolve(index, family, slug, entry):
    version = entry.get("version")
    candidates = index.get((family, version), [])
    if not candidates:
        raise Unmatched("no recipe produces %s %s" % (family, version))
    if len(candidates) > 1:
        # Every family that gained an MSVC recipe beside its MinGW one has
        # two recipes for each of its versions, which is 189 of this corpus's
        # entries - so (family, version) stopped identifying a recipe and the
        # script could no longer refresh any of them. The toolchain in the
        # slug is what separates them.
        #
        # This only ever narrows: a slug that cannot be read, or that names a
        # toolchain none of the candidates declares, is reported as ambiguous
        # exactly as before rather than resolved by guessing.
        #
        # A blob is excluded from narrowing outright, which is not the same
        # thing and was got wrong once. Recipe.slug labels a blob after the
        # compiler that produced it upstream, forcing producer="msvc" - and
        # "msvc" is a real toolchain alias, so such a slug parses to
        # msvc_x64 and would narrow happily onto whichever recipe declares
        # MSVC. It reads as a successful match and would attach that
        # recipe's build_flags. Nothing breaks today only because each blob
        # family has exactly one recipe; that is not a property to rely on.
        wanted = _toolchain_of(slug, family, version)
        if any(a.is_blob for _, recipe in candidates for a in recipe.artifacts):
            wanted = None
        narrowed = [(name, recipe) for name, recipe in candidates
                    if wanted in {canonical_alias(t)
                                  for t in recipe.toolchains}]
        if len(narrowed) == 1:
            candidates = narrowed
        else:
            raise Unmatched(
                "ambiguous: %s %s built by %s is produced by %s"
                % (family, version, wanted or "an unreadable toolchain",
                   ", ".join(n for n, _ in candidates)))
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
            recipe, artifact = _resolve(index, family, slug, entry)
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
        # Every record of the family is re-serialised here, so this is written
        # beside the original and moved over it: a truncated provenance.json
        # would lose the build history of artefacts this run never touched.
        package.atomic_write_text(
            path, json.dumps(entries, indent=2, sort_keys=True) + "\n")
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
