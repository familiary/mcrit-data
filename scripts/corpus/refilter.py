"""Re-apply the compiler-runtime filter to already-committed reports.

The glue baseline is measured, not hardcoded, which is what keeps it from
rotting with the next compiler - but it also means the baseline can improve
after a family has been built and committed, and then every artefact built
before the improvement is wearing runtime under its own family's name.

That has happened twice, and this module exists because of the first time.
The x86 probe gained 64-bit division, which pulls libgcc's ``__divdi3``,
``__moddi3``, ``__udivdi3``, ``__umoddi3``, ``__divmoddi4`` and
``__udivmoddi4`` into the baseline; 44 of 154 committed MinGW artefacts
carried whichever of the six they linked, 148 functions in all.

The second round found more, and is worth recording because the defect was
invisible: the probe already *called* ``floor``, ``sin`` and ``localtime``,
and GCC folded them at -O2 as the builtins they are, so the libmingwex
bodies were never linked into the probe. A library calling ``floor()`` on a
value the compiler cannot see does link it, so ``floor`` was sitting in Lua,
libpng, libxml2 and in data/MinGW at once. Taking the address defeats the
builtin. With the reentrant time conversions and ``_vscprintf`` alongside,
that round removed a further 277 functions from 37 artefacts.

They are few - one to six per artefact, 148 across the corpus - but they
matter out of proportion to their count, because ``__udivmoddi4`` compiles to
the same bytes in every x86 binary that divides a 64-bit integer. That makes
them PicHash-identical across unrelated families, which is what
``validate --deep`` measures and what MCRIT uses for exact matches; left
alone they are the bulk of what survives its ten-instruction floor. They are
not small: measured in the committed Lua 5.3.6 export they run 122 to 175
instructions and each carries a full minhash, MCRIT's floor being ten. So
they corrupt fuzzy similarity as well as exact matching, and a library that
merely divides a 64-bit integer is scored as resembling every other library
that does.

Rebuilding 37 families to remove them would cost hours of compilation and
would produce the same disassembly, because nothing about the binaries
changes - only which of their functions this repository is willing to
attribute to the project. So the committed reports are filtered in place
instead, by the same ``is_glue`` the pipeline uses.

What that costs in fidelity was measured rather than assumed. Reading a
committed report back, re-exporting it and diffing against the committed
.mcrit gives one difference: the ``timestamp`` inside each entry of
``function_labels``, which MCRIT writes when it records a label. Labels
themselves, minhashes, PicHashes, sample entries and the export config are
identical.

The archive is a narrower claim, and an earlier version of this docstring
overstated it. It is *semantically* what the pipeline's own
``_drop_crt_glue`` produces - same functions, same statistics, same
binweight, and ``json.loads`` of the two compares equal - but not always the
same bytes. The pipeline serialises ``report.toDict()``, whose ``xcfg`` and
``xdata_refs_*`` keys are integers, so ``sort_keys=True`` orders them
numerically; this patches the stored dict, whose keys are the strings JSON
gave back, and the same call orders them lexicographically. Where an
artefact's offsets are not all the same width the two files differ in key
order and nowhere else - 8 of 14 sampled artefacts do. Nothing reads these
files by key order, so it costs nothing; it is written down because the
earlier claim was checked on an artefact whose keys happened to be uniform
and was wrong in general.

So a refiltered pair holds what a rebuild *of the same disassembly* would
have produced.

That qualifier is the whole of the difference. Nothing here re-runs SMDA, so
the fields describing the disassembly rather than the filter are deliberately
left alone: the report's ``timestamp`` and ``execution_time``, and
provenance's ``generated``, ``smda_version`` and ``compiler``. A real rebuild
would move all five, and they would still describe the same code. The binary
is not rebuilt either, so the recorded ``sha256`` stays correct by
construction.

The archive is patched as stored JSON rather than re-serialised from the
parsed report, for the reason reprocess.py gives: ``SmdaReport.toDict()``
drops ``xdata_refs_from`` entries, and a correction has no business
discarding data it was not asked about.

    python scripts/build_corpus.py refilter [family ...]
    python scripts/build_corpus.py refilter --dry-run
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile

from . import config, export, package, recipes
from .baseline import crt_glue, is_glue
from .reprocess import _read_archive, _write_archive, _export_path
from .smdaify import _recompute_statistics


LOGGER = logging.getLogger(__name__)


class RefilterError(RuntimeError):
    """An artefact that cannot be corrected in all of the files that hold it."""


def _filter_is_off_for():
    """Families whose recipes turn the glue filter off.

    A match in one of those is the point of the family, not leakage:
    data/libstdc++ exists to carry the C++ runtime, and SysWhispers links no
    runtime at all. Reading it from the recipes rather than listing it here
    means a recipe that changes its mind does not need this file changed too.
    """
    return {recipe.family for recipe in recipes.all_recipes().values()
            if not recipe.drop_crt_glue}


def _artifacts(families=None):
    """Yield (family, slug, entry, archive) for generated artefacts.

    Only families carrying a provenance record, which is what marks a family
    as produced by this tooling; the IDA-derived ones came from elsewhere and
    are not this contribution's to rewrite.
    """
    root = config.DATA_DIR
    off = _filter_is_off_for()
    names = families or sorted(name for name in os.listdir(root)
                               if os.path.isdir(os.path.join(root, name)))
    for family in names:
        provenance_path = os.path.join(root, family, "provenance.json")
        if not os.path.exists(provenance_path):
            # INFO, not DEBUG: a mistyped family name would otherwise be
            # reported as "0 artefact(s) corrected" and a zero exit, which
            # reads as a clean corpus rather than as a typo.
            LOGGER.info("skipping %s: no provenance record, so it was not "
                        "generated by this tooling", family)
            continue
        if family in off:
            LOGGER.info("skipping %s: its recipe turns the glue filter off",
                        family)
            continue
        with open(provenance_path, encoding="utf-8") as handle:
            provenance = json.load(handle)
        for slug, entry in sorted(provenance.items()):
            if not entry.get("toolchain"):
                # A blob was compiled upstream; the recorded toolchain is None
                # and there is no baseline that describes it.
                continue
            archive = os.path.join(config.REPO_ROOT, entry["smda"])
            if not os.path.exists(archive):
                LOGGER.warning("%s: %s is recorded but missing", slug, archive)
                continue
            yield family, slug, entry, archive


class ToolchainUnavailable(RefilterError):
    """This host cannot measure the baseline that built an artefact."""


def _usable_baseline(toolchain_id):
    """Fail loudly rather than filter an artefact against nothing.

    Two ways this command can quietly do nothing at all, both of which look
    exactly like a clean corpus:

    The toolchain may not exist on this host. The MSVC families can only be
    built on a Windows runner, so a Linux checkout - the only place the MinGW
    families can be refiltered - has no msvc143_x86 to measure. That is not an
    unreadable artefact and must not be counted as a failure, or the bare
    `refilter` this module documents could never exit 0 anywhere.

    Or the baseline may come back empty. crt_glue treats a probe that will not
    build as a warning and carries on, which is right for the pipeline, where
    the build is the deliverable and a thinner filter is better than no
    artefact. Here the baseline *is* the deliverable: with no symbols in it
    is_glue is false for everything, every artefact is skipped, and the
    command reports success over a corpus it never looked at.
    """
    from .toolchain import get_toolchain

    try:
        # KeyError alone, deliberately. get_toolchain raises nothing else
        # today, and the neighbouring failure - a toolchain that is registered
        # but whose compiler cannot actually be run - is a different thing that
        # pipeline.ToolchainUnusable reports as a *failure*. Catching
        # RuntimeError here would quietly reclassify that as "this host cannot
        # measure the baseline", skip every artefact and exit 0, which is the
        # outcome this function exists to prevent.
        get_toolchain(toolchain_id)
    except KeyError as error:
        raise ToolchainUnavailable(str(error))
    try:
        glue = crt_glue(toolchain_id)
    except Exception as error:
        # Measuring a baseline runs a compiler and then SMDA over what it
        # produced, so it can fail in ways this module cannot enumerate - a
        # compiler registered at import but gone by the time it is used, a
        # probe SMDA chokes on, mcrit or smda missing. None of them is a
        # reason to abandon the rest of the corpus with a traceback and no
        # FAIL line, which is exactly the defect the archive handler below was
        # fixed for; leaving this call bare reopened it one level up.
        raise RefilterError("the %s baseline could not be measured: %s: %s"
                            % (toolchain_id, type(error).__name__, error))
    if not glue:
        raise RefilterError(
            "the %s baseline came back empty, so nothing could be recognised "
            "as runtime glue; the probes did not build - see the warnings "
            "above" % toolchain_id)
    # A partial baseline is not caught here and cannot be: crt_glue warns per
    # failed probe and carries on, by design, and there is no count that says
    # what "enough" is. The consequence is a filter weaker than a rebuild's,
    # applied to committed files - recoverable, because the archive still holds
    # whatever was not removed and a later pass with a working baseline removes
    # it, but not reported. If probe warnings appeared above, treat this run as
    # provisional.
    return glue


def _glue_offsets(report, toolchain_id):
    return [offset for offset, function in report.xcfg.items()
            if is_glue(function, toolchain_id)]


def _corrected_archive(report_dict, report, offsets):
    """Apply the removal to both the parsed report and the stored dict.

    The parsed report is mutated so the statistics can be recomputed over what
    survives, exactly as the pipeline does it; the stored dict is what gets
    written back. xcfg is keyed by offset, and JSON has no integer keys, so
    the stored side is addressed by the decimal string SMDA wrote.
    """
    # Every offset is checked before any is deleted. Checking inside the
    # removal loop leaves both structures half-edited when the second of two
    # offsets is the one that is missing, and an artefact here drops one to
    # six functions, so "the second of two" is the normal case rather than a
    # corner. Nothing reaches disk either way - the caller abandons the
    # artefact - but a half-edited report is a trap for anything that later
    # reuses these objects, and the guarantee is cheap to make real.
    #
    # SMDA writes xcfg keys as decimal strings; anything else means the report
    # was not written by SMDA and must not be guessed at.
    missing = [offset for offset in offsets if str(offset) not in report_dict["xcfg"]]
    if missing:
        raise RefilterError(
            "%s in the parsed report but not in the stored one, so the two do "
            "not describe the same functions"
            % ", ".join("offset %d is" % offset for offset in sorted(missing)))
    removed = []
    for offset in offsets:
        removed.append(report.xcfg[offset].function_name)
        del report.xcfg[offset]
        del report_dict["xcfg"][str(offset)]
    # getFunctions() memoises, so the removal is invisible downstream without
    # this - the same trap smdaify._drop_crt_glue documents.
    report._sorted_functions = None
    _recompute_statistics(report)
    report_dict["statistics"] = report.statistics.toDict()
    report_dict.setdefault("metadata", {})["binweight"] = report.binweight
    return sorted(removed)


def _minhash_coverage(text):
    """(functions, how many of them carry a minhash) in an export."""
    entries = json.loads(text)
    compressed = entries.get("content", {}).get("is_compressed")
    total = hashed = 0
    for blob in entries.get("function_entries", {}).values():
        if compressed:
            from mcrit.libs.utility import decompress_decode
            blob = json.loads(decompress_decode(blob))
        for entry in blob.values():
            total += 1
            hashed += 1 if entry.get("minhash") else 0
    return total, hashed


def _assert_minhashes_survived(fresh_text, committed_path, removed):
    """Refuse an export that lost minhashes the committed one had.

    MCRIT computes minhashes in a job queue whose worker exceptions are logged
    and swallowed. When that job fails - a machine short of memory, a process
    pool that cannot spawn - getExportData still returns a structurally valid
    export, and every check export_reports makes (config hashes, sample count,
    a non-zero function count) passes on it. The minhashes are the entire
    point of a .mcrit in this corpus, and this is the first writer here that
    replaces known-good committed data rather than creating new: the pipeline
    only ever writes artefacts that did not exist, so a half-failed export
    cost nothing before.

    It would also be unrecoverable. A second run reads the already-filtered
    archive, finds no glue and skips, so the ruined export is never rebuilt -
    only a real recompilation would restore it.

    Not every function is minhashed: MCRIT indexes those above a minimum size,
    so a count below the function count is normal and is not what this looks
    at. What it refuses is a *drop* against the file being replaced, beyond
    the few functions deliberately removed.
    """
    if not os.path.exists(committed_path):
        return
    with open(committed_path, encoding="utf-8") as handle:
        before_total, before_hashed = _minhash_coverage(handle.read())
    after_total, after_hashed = _minhash_coverage(fresh_text)
    if before_hashed and not after_hashed:
        raise RefilterError(
            "the re-export carries no minhashes at all where the committed "
            "file has %d; MCRIT's hashing job failed without raising"
            % before_hashed)
    # Every removed function could at most have carried one minhash, so this
    # is the widest drop that can be legitimate.
    if after_hashed < before_hashed - len(removed):
        raise RefilterError(
            "the re-export carries %d minhashes where the committed file has "
            "%d and only %d function(s) were removed, so hashing did not "
            "finish" % (after_hashed, before_hashed, len(removed)))
    if after_total != before_total - len(removed):
        raise RefilterError(
            "the re-export holds %d functions; the committed file holds %d and "
            "%d were removed, so it does not describe the same sample"
            % (after_total, before_total, len(removed)))


def _write_export(path, report, removed):
    """Re-export ``report`` over ``path``, atomically.

    export_reports writes straight to its target, which is right for the work
    directory the pipeline gives it and wrong for a committed file: an
    interrupted write would leave a truncated .mcrit with no way back. It is
    written to a scratch directory and moved over the target.

    The scratch directory goes in the configured work directory rather than
    beside the target, because anything created under data/ is walked by
    validate - a crash mid-run would leave a .mcrit inside a dot-directory
    that then reads as a duplicate of the sample it was copied from. The work
    directory is where MCRIT_DATA_WORK_DIR points, which is the setting that
    exists for putting large intermediates somewhere with room: this module
    documents a 9.4 GB export peak, and defaulting to /tmp would put that on a
    tmpfs on some runners. The move still has to be atomic, so the text is
    read out and handed to atomic_write_text, which stages beside the target
    itself.
    """
    os.makedirs(config.WORK_DIR, exist_ok=True)
    staging = tempfile.mkdtemp(dir=config.WORK_DIR, prefix="refilter-")
    try:
        fresh = os.path.join(staging, os.path.basename(path))
        export.export_reports([report], fresh)
        package.check_size(fresh)
        with open(fresh, encoding="utf-8") as handle:
            text = handle.read()
    finally:
        # package._discard is os.remove, which cannot take a directory.
        shutil.rmtree(staging, ignore_errors=True)
    # Checked before the committed file is touched, so a bad export costs
    # nothing: the caller abandons the artefact with all three of its files
    # still agreeing with each other.
    _assert_minhashes_survived(text, path, removed)
    package.atomic_write_text(path, text)


def refilter(families=None, dry_run=False):
    """Drop newly-recognised compiler runtime from the committed reports.

    Returns (changes, failures, examined). Each change is (slug, [names
    removed]); each failure is a message about an artefact left exactly as it
    was found; ``examined`` counts the artefacts actually looked at, which the
    caller needs to tell "nothing to correct" from "nothing was reachable".

    That distinction matters more than it sounds. A toolchain id carries the
    compiler's major version - 155 of the records here name mingw13 - and it
    is resolved against the host lazily, so a machine with GCC 14, or with no
    MinGW at all, finds no toolchain for any of them, skips every artefact and
    would otherwise report a clean corpus it never opened.

    An artefact is corrected in all three places that describe it - the .7z,
    the .mcrit and the provenance record - or in none of them. Reading and
    filtering happen first, so an artefact that cannot be corrected costs only
    itself and the rest of the corpus is still walked.

    ``dry_run`` reports what would go without writing anything, which is how
    to see the scale of a baseline change before spending the corpus on it.
    """
    changes = []
    failures = []
    unavailable = set()
    examined = 0
    from smda.common.SmdaReport import SmdaReport

    for family, slug, entry, archive in _artifacts(families):
        toolchain_id = entry["toolchain"]
        if toolchain_id in unavailable:
            continue
        # The baseline is measured once per toolchain and memoised, but the
        # reasons it can be unusable have to be separated from the reasons an
        # artefact can be unreadable, or a Linux checkout reports the two MSVC
        # families as broken and the command can never exit 0.
        try:
            _usable_baseline(toolchain_id)
        except ToolchainUnavailable as error:
            unavailable.add(toolchain_id)
            LOGGER.info("skipping every %s artefact: this host cannot measure "
                        "that baseline (%s)", toolchain_id, error)
            continue
        except RefilterError as error:
            unavailable.add(toolchain_id)
            failures.append("%s: %s" % (toolchain_id, error))
            continue
        examined += 1
        try:
            member, report_dict = _read_archive(archive)
            report = SmdaReport.fromDict(report_dict)
            offsets = _glue_offsets(report, toolchain_id)
        except (OSError, RuntimeError, ValueError, KeyError, TypeError,
                AttributeError, subprocess.CalledProcessError) as error:
            # 7z runs with check=True, so a corrupt or unreadable archive
            # arrives as CalledProcessError, which is neither an OSError nor a
            # RuntimeError. Without it here one bad archive ends the walk with
            # a traceback instead of costing only itself.
            failures.append("%s: not read: %s" % (slug, error))
            continue
        if not offsets:
            continue

        # The record names its own export; deriving the path a second way
        # would be a second source of truth for the same file, and
        # validate.find_stale_provenance already checks this one.
        export_path = os.path.join(config.REPO_ROOT, entry["mcrit"]) \
            if entry.get("mcrit") else _export_path(archive, slug)
        if not os.path.exists(export_path):
            failures.append("%s: no .mcrit at %s, so the pair cannot be kept "
                            "in step; archive left alone" % (slug, export_path))
            continue

        # _write_export replaces the whole file with an export of this one
        # report, so a file describing several samples would lose the others.
        # No committed .mcrit holds more than one today, which makes this a
        # guard rather than a code path - and exactly the kind of assumption
        # that is silently wrong later. reprocess._corrected_export guards the
        # same thing for the same reason.
        try:
            with open(export_path, encoding="utf-8") as handle:
                samples = json.load(handle).get("sample_entries") or {}
        except (OSError, ValueError, AttributeError) as error:
            # AttributeError: a .mcrit whose top level is not an object gives
            # back a list or a string, and .get on it is not a ValueError.
            failures.append("%s: %s could not be read, archive left alone: %s"
                            % (slug, export_path, error))
            continue
        if len(samples) != 1:
            failures.append(
                "%s: %s describes %d samples; this rewrites an export from a "
                "single report and would drop the others, so it is left alone"
                % (slug, export_path, len(samples)))
            continue
        if report_dict.get("sha256") not in samples:
            failures.append(
                "%s: %s does not describe this report (sha256 %s), so the two "
                "are not a pair and neither is touched"
                % (slug, export_path, str(report_dict.get("sha256"))[:12]))
            continue

        try:
            removed = _corrected_archive(report_dict, report, offsets)
        except (RefilterError, KeyError) as error:
            failures.append("%s: %s" % (slug, error))
            continue

        if dry_run:
            LOGGER.info("%s: would drop %d (%s)", slug, len(removed),
                        ", ".join(removed))
            changes.append((slug, removed))
            continue

        # The export is rebuilt from the filtered report before the archive is
        # touched: if MCRIT cannot index it, nothing has been written yet and
        # the committed pair still agrees with itself.
        try:
            _write_export(export_path, report, removed)
        except (OSError, RuntimeError, ValueError, ImportError,
                AttributeError) as error:
            # ImportError: export.export_reports imports mcrit inside the
            # call, so a host with smda but not mcrit fails here rather than
            # at module load - and would otherwise take the run down on the
            # first artefact that needed writing.
            failures.append("%s: export not rewritten, archive untouched: %s"
                            % (slug, error))
            continue
        try:
            _write_archive(archive, member, report_dict)
        except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
            # CalledProcessError is the likeliest way this fails, not OSError:
            # _write_archive runs 7z with check=True, so a full disk, an
            # OOM-killed compressor or an unwritable staging directory all
            # arrive here as a non-zero exit. Leaving it out made the one
            # window this module cannot close - export written, archive not -
            # unreachable for its most common cause, and turned it into a
            # traceback out of main() with no FAIL line and the rest of the
            # corpus abandoned.
            #
            # Two files cannot be written at once, so the window itself stays
            # open. It is reported loudly rather than logged and forgotten, and
            # re-running repairs it: the archive still holds the glue, so the
            # artefact is picked up again and both files rewritten.
            failures.append("%s: %s was rewritten but %s could not be: %s"
                            % (slug, export_path, archive, error))
            continue

        # Provenance last, because a stale record is the least damaging of the
        # three to be left with: the data still agrees with itself, only the
        # description of it is behind. It is also the one case re-running
        # cannot repair - the archive no longer holds the glue, so the next
        # pass skips the artefact and reports a clean success over a record
        # that still claims the old count. validate.find_miscounted_provenance
        # exists to catch exactly that, so a failure here is visible later
        # even if this message is lost.
        recorded = sorted(set(entry.get("removed_runtime_functions") or ())
                          | set(removed))
        try:
            package.write_provenance(family, {slug: dict(
                entry,
                num_functions=report.num_functions,
                removed_runtime_functions=recorded)})
        except (OSError, ValueError) as error:
            # ValueError: write_provenance re-reads the existing file, so a
            # corrupt provenance.json surfaces here, after both data files
            # have already been written.
            failures.append(
                "%s: both data files were rewritten but provenance was not, so "
                "its num_functions is now stale and re-running will not fix it "
                "- correct it by hand: %s" % (slug, error))
            continue

        LOGGER.info("%s: dropped %d (%s)", slug, len(removed),
                    ", ".join(removed))
        changes.append((slug, removed))
    return changes, failures, examined
