"""Post-generation checks on committed artefacts.

Runs standalone (``python scripts/build_corpus.py validate``) so the whole
data directory, including everything that was already in the repository, can
be re-checked after a contribution.
"""

import json
import os
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


def validate_all(root=None, check_size=True):
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
    return problems
