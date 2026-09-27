"""Re-derive the statistics block of already-committed reports.

When a report has functions removed from it - compiler runtime glue, here -
the statistics block has to be recomputed, and a defect in how that was done
shipped wrong ``num_leaf_functions`` and ``num_recursive_functions`` into
every affected sample. Those counts are copied into the .mcrit sample entry,
so consumers were comparing a number SMDA defines one way against one this
tooling defined another.

Rebuilding every family from source to correct two integers would cost hours
of compilation and would change nothing else, so this walks the committed
reports instead and recomputes the block with the same function the pipeline
now uses. It is not a substitute for regenerating: it only touches the fields
that function derives - the statistics block and binweight - and anything
that changes the disassembly itself needs a real rebuild.

A report lives in two committed files, the .7z and the .mcrit beside it, and
a correction that reaches only one of them leaves them describing the same
sample differently - the very defect this module removes. So both files are
corrected together or neither is, and a report that cannot be corrected in
both is reported as a failure rather than half-applied.

It touches only the reports that had functions removed, which are the only
ones whose block the pipeline recomputed in the first place - see
_had_functions_removed.

The stored JSON is edited rather than re-serialised from a parsed report.
SmdaReport.toDict() does not round-trip every field - xdata_refs_from loses
entries - so writing a parsed report back would quietly discard data that
has nothing to do with this correction.

    python scripts/build_corpus.py reprocess [family ...]
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile

from . import config, package
from .smdaify import _recompute_statistics


LOGGER = logging.getLogger(__name__)


class ReprocessError(RuntimeError):
    """A report that cannot be corrected in both of the files that hold it."""


def _read_archive(archive):
    """Return (member name, parsed report) from a committed .7z."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["7z", "x", "-y", "-o%s" % tmp, archive],
                       check=True, stdout=subprocess.DEVNULL)
        members = [os.path.join(dirpath, name)
                   for dirpath, _, names in os.walk(tmp) for name in names]
        if len(members) != 1:
            raise RuntimeError("%s holds %d files, expected exactly one"
                               % (archive, len(members)))
        with open(members[0], encoding="utf-8") as handle:
            return os.path.basename(members[0]), json.load(handle)


def _write_archive(archive, member, report_dict):
    """Replace ``archive`` with one holding ``report_dict``, or leave it alone.

    The new archive is built in a scratch directory beside the committed one
    and moved over it only after 7z has exited 0. Compressing straight onto
    the target means deleting it first, and then a 7z failure, an OOM kill or
    a Ctrl-C in between destroys an archive nothing in this repository can
    rebuild without recompiling the project it came from. 7z stores the member
    under its basename alone, so building elsewhere changes nothing about the
    bytes it produces.
    """
    staging = tempfile.mkdtemp(dir=os.path.dirname(archive) or ".",
                               prefix=".reprocess-")
    try:
        path = os.path.join(staging, member)
        with open(path, "w", encoding="utf-8") as handle:
            # SMDA's own spelling, so a reprocessed report stays byte-identical
            # to one the pipeline would write.
            handle.write(json.dumps(report_dict, indent=1, sort_keys=True))
        replacement = os.path.join(staging, "replacement.7z")
        subprocess.run(list(package.ARCHIVE_COMMAND) + [replacement, path],
                       check=True, stdout=subprocess.DEVNULL)
        # Same directory, so this is atomic: the committed path holds either
        # the old archive or the new one, never a partial write.
        os.replace(replacement, archive)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _recomputed(report_dict):
    """Return (statistics block, binweight) as the pipeline would write them.

    binweight comes along because _recompute_statistics resets it too, it is
    written into metadata by SmdaReport.toDict(), and MCRIT copies it into the
    sample entry - so correcting the statistics alone would still leave a
    report disagreeing with what a rebuild would produce.
    """
    from smda.common.SmdaReport import SmdaReport

    report = SmdaReport.fromDict(report_dict)
    _recompute_statistics(report)
    return report.statistics.toDict(), report.binweight


def _export_path(archive, slug):
    """The .mcrit that describes the same sample as this .7z."""
    return os.path.join(os.path.dirname(os.path.dirname(archive)),
                        "mcrit", "%s.mcrit" % slug)


def _corrected_export(path, sha256, statistics, binweight):
    """Return the .mcrit contents with this sample corrected, or None.

    None means the export already agrees and must not be rewritten.

    The entry is looked up by the report's own sha256 rather than by writing
    the block into every entry: export_reports takes a list of reports, so a
    multi-sample export would otherwise have the first sample's counts
    attributed to all of them. An export that does not exist, or does not
    describe this sample, raises - the caller asks for this before it touches
    the archive, because a .7z and a .mcrit that disagree about one sample is
    precisely the defect this module exists to remove, and rewriting the
    archive while the export cannot follow would create it.
    """
    if not os.path.exists(path):
        raise ReprocessError("no .mcrit at %s" % path)
    with open(path, encoding="utf-8") as handle:
        export = json.load(handle)
    entry = (export.get("sample_entries") or {}).get(sha256)
    if entry is None:
        raise ReprocessError("%s has no sample entry for %s" % (path, sha256))
    if entry.get("statistics") == statistics and entry.get("binweight") == binweight:
        return None
    entry["statistics"] = statistics
    entry["binweight"] = binweight
    return export


def _archives(families):
    root = config.DATA_DIR
    names = families or sorted(name for name in os.listdir(root)
                               if os.path.isdir(os.path.join(root, name)))
    for family in names:
        # Only families this tooling generated, which is what a provenance
        # record means. The IDA-derived families came from somewhere else and
        # their statistics are whatever produced them said; recomputing those
        # would be rewriting data that is not this contribution's to change.
        if not os.path.exists(os.path.join(root, family, "provenance.json")):
            LOGGER.info("skipping %s: not generated by this tooling", family)
            continue
        for dirpath, _, filenames in os.walk(os.path.join(root, family)):
            if os.path.basename(dirpath) != "smda":
                continue
            for filename in sorted(filenames):
                if filename.endswith(".7z"):
                    yield family, os.path.join(dirpath, filename)


def _had_functions_removed(family, slug):
    """Whether this artefact's report had functions taken out of it.

    Only those need their statistics recomputed - and only those may have
    them recomputed. Where nothing was removed the block is SMDA's own, and
    SMDA's bookkeeping does not always agree with a recomputation from the
    finished report: on the libstdc++ sample it marks four more functions
    non-leaf than any rule applied to the emitted blocks can account for,
    presumably from calls analysed during a pass whose instructions did not
    survive into the function. Rewriting those would replace SMDA's numbers
    with this tooling's opinion of them, which is the mixed-definition
    problem this whole exercise exists to remove.
    """
    path = os.path.join(config.DATA_DIR, family, "provenance.json")
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as handle:
        entry = json.load(handle).get(slug) or {}
    return bool(entry.get("removed_runtime_functions"))


def reprocess(families=None):
    """Recompute statistics for the committed reports that need it.

    Returns (changes, failures). Each change is (archive path, {field: (old,
    new)}); each failure is a message about a report that could not be
    corrected in both of the files that carry it. A report whose block is
    already correct is left untouched, so this is idempotent and a second run
    reports nothing.

    A report is corrected only if every part of the correction is known to be
    possible first, and one report that cannot be corrected costs only itself:
    the rest of the corpus is still walked, and the failure is handed back so
    the caller can exit non-zero over it.
    """
    changes = []
    failures = []
    for family, archive in _archives(families):
        slug = os.path.basename(archive)[:-len(".7z")]
        if not _had_functions_removed(family, slug):
            continue
        member, report_dict = _read_archive(archive)
        before = report_dict.get("statistics") or {}
        metadata = report_dict.setdefault("metadata", {})
        after, binweight = _recomputed(report_dict)
        differences = {key: (before.get(key), after[key])
                       for key in after if before.get(key) != after[key]}
        if metadata.get("binweight") != binweight:
            differences["binweight"] = (metadata.get("binweight"), binweight)
        if not differences:
            continue
        export = _export_path(archive, slug)
        try:
            # Before the archive is touched, so a report whose export cannot
            # follow it keeps both files agreeing with each other.
            corrected = _corrected_export(export, report_dict["sha256"],
                                          after, binweight)
        except (ReprocessError, KeyError, OSError, ValueError) as error:
            failures.append("%s: %s" % (archive, error))
            continue
        report_dict["statistics"] = after
        metadata["binweight"] = binweight
        try:
            _write_archive(archive, member, report_dict)
        except (OSError, subprocess.CalledProcessError) as error:
            failures.append("%s: archive not rewritten: %s" % (archive, error))
            continue
        if corrected is not None:
            try:
                package.atomic_write_text(export, json.dumps(corrected))
            except OSError as error:
                # The archive is already the corrected one, so this is the one
                # window where the pair can end up disagreeing. It cannot be
                # closed - two files cannot be written at once - so it is
                # reported loudly instead of logged and forgotten.
                failures.append("%s was corrected but %s could not be: %s"
                                % (archive, export, error))
                continue
        LOGGER.info("%s: %s", slug,
                    ", ".join("%s %s -> %s" % (k, o, n)
                              for k, (o, n) in sorted(differences.items())))
        changes.append((archive, differences))
    return changes, failures
