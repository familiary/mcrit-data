"""Post-generation checks on committed artefacts.

Runs standalone (``python scripts/build_corpus.py validate``) so the whole
data directory, including everything that was already in the repository, can
be re-checked after a contribution.
"""

import json
import os
import re
import subprocess
import tempfile

from . import config


class ValidationError(RuntimeError):
    pass


def _iter_data_files(suffix, root=None):
    root = root or config.DATA_DIR
    for dirpath, _, filenames in os.walk(root):
        for filename in sorted(filenames):
            if filename.endswith(suffix):
                yield os.path.join(dirpath, filename)


def validate_mcrit_file(path):
    """Check one .mcrit export is well formed and importable."""
    problems = []
    with open(path, encoding="utf-8") as handle:
        try:
            export = json.load(handle)
        except ValueError as error:
            return ["%s: not valid JSON (%s)" % (path, error)]

    for key in ("config", "content", "family_mapping", "sample_entries", "function_entries"):
        if key not in export:
            problems.append("%s: missing top level key %r" % (path, key))
    if problems:
        return problems

    if export["config"].get("minhash") != config.EXPECTED_MINHASH_CONFIG:
        problems.append("%s: minhash config hash does not match the rest of the corpus" % path)
    if export["config"].get("shingler") != config.EXPECTED_SHINGLER_CONFIG:
        problems.append("%s: shingler config hash does not match the rest of the corpus" % path)

    samples = export["sample_entries"]
    functions = export["function_entries"]
    if export["content"]["num_samples"] != len(samples):
        problems.append("%s: content.num_samples=%s but %d sample entries"
                        % (path, export["content"]["num_samples"], len(samples)))
    if set(samples) != set(functions):
        problems.append("%s: sample_entries and function_entries disagree on sha256 keys" % path)

    families = set(export["family_mapping"].values())
    for sha256, sample in samples.items():
        if sample.get("sha256") != sha256:
            problems.append("%s: sample keyed by %s carries sha256 %s"
                            % (path, sha256, sample.get("sha256")))
        if not sample.get("family"):
            problems.append("%s: sample %s has no family" % (path, sha256[:12]))
        elif sample["family"] not in families:
            problems.append("%s: sample family %r is not in family_mapping"
                            % (path, sample["family"]))
        if not sample.get("version"):
            problems.append("%s: sample %s has no version recorded" % (path, sha256[:12]))
        # Every sample in this corpus is reference material. MCRIT keys its
        # library-only views and its library-versus-malware family counts off
        # this flag, so a false here makes a reference sample count as malware.
        if not sample.get("is_library"):
            problems.append("%s: sample %s is not marked is_library" % (path, sha256[:12]))
        if sample.get("statistics", {}).get("num_functions", 0) < 1:
            problems.append("%s: sample %s reports no functions" % (path, sha256[:12]))
    return problems


def validate_smda_archive(path):
    """Check a committed .7z holds a parsable SMDA report with provenance."""
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(["7z", "x", "-y", "-o%s" % tmp, path],
                                capture_output=True)
        if result.returncode != 0:
            return ["%s: 7z extraction failed" % path]
        reports = [os.path.join(dirpath, name)
                   for dirpath, _, names in os.walk(tmp) for name in names]
        if not reports:
            return ["%s: archive is empty" % path]
        for report_path in reports:
            with open(report_path, encoding="utf-8") as handle:
                try:
                    report = json.load(handle)
                except ValueError as error:
                    problems.append("%s: %s is not valid JSON (%s)"
                                    % (path, os.path.basename(report_path), error))
                    continue
            metadata = report.get("metadata", {})
            if not metadata.get("family"):
                problems.append("%s: report has no family" % path)
            if not metadata.get("version"):
                problems.append("%s: report has no version" % path)
            if report.get("status") != "ok":
                problems.append("%s: report status is %r" % (path, report.get("status")))
            if not report.get("xcfg"):
                problems.append("%s: report contains no functions" % path)
    return problems


def find_duplicate_samples(root=None):
    """Report sha256 values that appear in more than one .mcrit file."""
    seen = {}
    duplicates = []
    for path in _iter_data_files(".mcrit", root):
        with open(path, encoding="utf-8") as handle:
            try:
                export = json.load(handle)
            except ValueError:
                continue
        for sha256 in export.get("sample_entries", {}):
            if sha256 in seen:
                duplicates.append((sha256, seen[sha256], path))
            else:
                seen[sha256] = path
    return duplicates


def find_cross_family_functions(root=None, threshold=3):
    """Report PicHashes that appear under more than one family name.

    A handful of shared hashes is normal - libraries do vendor each other, and
    tiny thunks collide. A hash under several unrelated families is the
    signature of compiler runtime or a statically linked dependency leaking in
    under the host project's name, which is what the glue filter exists to
    prevent and what commit 0108024 had to fix by hand.
    """
    from mcrit.libs.utility import decompress_decode

    by_hash = {}
    for path in _iter_data_files(".mcrit", root):
        with open(path, encoding="utf-8") as handle:
            try:
                export = json.load(handle)
            except ValueError:
                continue
        compressed = export.get("content", {}).get("is_compressed")
        for sha256, blob in export.get("function_entries", {}).items():
            # A sample with no family is already reported by validate_mcrit_file;
            # here it only needs a name that sorts, so the report still renders.
            family = export.get("sample_entries", {}).get(sha256, {}).get(
                "family") or "(unknown)"
            entries = json.loads(decompress_decode(blob)) if compressed else blob
            for entry in entries.values():
                pichash = entry.get("pichash")
                if pichash:
                    by_hash.setdefault(pichash, set()).add(family)
    return {h: sorted(f) for h, f in by_hash.items() if len(f) >= threshold}


def _counterpart(path, from_kind, to_kind, from_suffix, to_suffix):
    """Map data/<fam>/<arch>/smda/<slug>.7z to its .mcrit sibling, or back."""
    directory, filename = os.path.split(path)
    parent, kind = os.path.split(directory)
    if kind != from_kind or not filename.endswith(from_suffix):
        return None
    return os.path.join(parent, to_kind, filename[:-len(from_suffix)] + to_suffix)


def find_unpaired_artifacts(root=None):
    """Report a .7z without its .mcrit, or a .mcrit without its .7z.

    The two are written together and are only useful together: an archive on
    its own is a report nothing can import, an export on its own has no
    disassembly behind it. A half-written pair is what a run that died between
    the two writes leaves behind, and it is otherwise invisible.
    """
    problems = []
    for suffix, args in ((".7z", ("smda", "mcrit", ".7z", ".mcrit")),
                         (".mcrit", ("mcrit", "smda", ".mcrit", ".7z"))):
        for path in _iter_data_files(suffix, root):
            expected = _counterpart(path, *args)
            if expected and not os.path.exists(expected):
                problems.append("%s has no matching %s"
                                % (path, os.path.basename(expected)))
    return problems


def find_stale_provenance(root=None):
    """Report provenance records whose artefacts are not in the tree.

    write_provenance merges new records over the existing file and never
    prunes, so renaming a slug - a version string corrected, a component
    renamed - leaves the old record behind for good, describing a file that
    is no longer there.
    """
    problems = []
    for path in _iter_data_files("provenance.json", root):
        with open(path, encoding="utf-8") as handle:
            try:
                records = json.load(handle)
            except ValueError as error:
                problems.append("%s: not valid JSON (%s)" % (path, error))
                continue
        for slug, entry in sorted(records.items()):
            if not isinstance(entry, dict):
                continue
            for key in ("smda", "mcrit"):
                relative = entry.get(key)
                if relative and not os.path.exists(
                        os.path.join(config.REPO_ROOT, relative)):
                    problems.append("%s: record %s points at %s, which does not exist"
                                    % (path, slug, relative))
    return problems


_LINK = re.compile(r"\[[^\]]*\]\((data/[^)\s]+)\)")


def find_broken_readme_links(root=None):
    """Report README links that point at files which are not in the tree.

    The tables are the only index of this corpus, so a row pointing at a
    filename that no longer exists is silently useless - which is how twelve
    dead links survived in this README. Checking them here means a
    regeneration that renames an artefact cannot be committed without the
    table being brought along.
    """
    readme = os.path.join(config.REPO_ROOT, "README.md")
    if not os.path.exists(readme):
        return []
    with open(readme, encoding="utf-8") as handle:
        text = handle.read()
    missing = []
    for target in sorted(set(_LINK.findall(text))):
        if not os.path.exists(os.path.join(config.REPO_ROOT, target)):
            missing.append(target)
    return missing


def find_undocumented_families(root=None):
    """Report families present in data/ that no README link mentions.

    Data nobody can find from the README is data nobody will use.
    """
    readme = os.path.join(config.REPO_ROOT, "README.md")
    if not os.path.exists(readme) or not os.path.isdir(config.DATA_DIR):
        return []
    with open(readme, encoding="utf-8") as handle:
        linked = {target.split("/")[1] for target in _LINK.findall(handle.read())
                  if target.count("/") > 1}
    return sorted(name for name in os.listdir(config.DATA_DIR)
                  if os.path.isdir(os.path.join(config.DATA_DIR, name))
                  and name not in linked)


def validate_all(root=None, check_size=True, deep=False):
    """Check everything under ``root`` (default data/).

    ``deep`` adds the cross-family PicHash check. It is opt-in because it
    loads and decompresses every .mcrit in the corpus, which is far too slow
    for the per-family check the Windows workflow runs after each build.
    """
    problems = []
    for path in _iter_data_files(".mcrit", root):
        problems.extend(validate_mcrit_file(path))
        if check_size and os.path.getsize(path) > config.MAX_COMMITTED_FILE_SIZE:
            problems.append("%s: exceeds the GitHub blob size limit" % path)
    for path in _iter_data_files(".7z", root):
        problems.extend(validate_smda_archive(path))
        if check_size and os.path.getsize(path) > config.MAX_COMMITTED_FILE_SIZE:
            problems.append("%s: exceeds the GitHub blob size limit" % path)
    for sha256, first, second in find_duplicate_samples(root):
        problems.append("duplicate sample %s in %s and %s" % (sha256[:12], first, second))
    problems.extend(find_unpaired_artifacts(root))
    problems.extend(find_stale_provenance(root))
    if deep:
        for pichash, families in sorted(find_cross_family_functions(root).items()):
            problems.append("PicHash %s appears under %d families: %s"
                            % (pichash, len(families), ", ".join(families)))
    # Only when the whole corpus is being checked: a run scoped to one family
    # cannot say anything about the README as a whole.
    if root is None:
        for target in find_broken_readme_links():
            problems.append("README links %s, which does not exist" % target)
        for family in find_undocumented_families():
            problems.append("data/%s is not linked from the README" % family)
    return problems
