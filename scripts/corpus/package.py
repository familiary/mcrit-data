"""Write generated artefacts into data/ following repository conventions.

Layout mirrors what is already committed:

    data/<Family>/<arch>/smda/<slug>.7z     (7z of one <slug>.smda report)
    data/<Family>/<arch>/mcrit/<slug>.mcrit
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile

from . import config


LOGGER = logging.getLogger(__name__)


class PackagingError(RuntimeError):
    pass


# -mx=9 matches the compression level of the archives already committed.
# -mt?=off drops the stored timestamps: they are the only part of the archive
# that changes when the report does not, and with them in, regenerating
# unchanged data always produces a diff and byte-for-byte reproducibility
# cannot be checked at all. Shared with corpus.reprocess, which rewrites the
# same archives in place and must write them identically.
ARCHIVE_COMMAND = ("7z", "a", "-t7z", "-mx=9", "-mtm=off", "-mtc=off", "-mta=off")


def smda_dir(family, arch):
    return os.path.join(config.DATA_DIR, family, arch, "smda")


def mcrit_dir(family, arch):
    return os.path.join(config.DATA_DIR, family, arch, "mcrit")


def check_7z():
    """Fail before a build starts rather than after it, if 7z is missing.

    Every artefact has to be archived, so a host without 7z cannot produce
    anything - discovering that after a twenty minute compile is pure waste.
    """
    if shutil.which("7z") is None:
        raise PackagingError("7z is not on PATH; it is required to write "
                             "data/<family>/<arch>/smda/*.7z")


def stage_smda_archive(report, slug, stage_dir=None):
    """Serialise ``report`` into <work dir>/<slug>.7z and size-check it.

    Staged rather than written straight into data/ so that a later failure -
    a .mcrit over the GitHub blob limit, most of all - cannot leave a
    committable .7z behind with no .mcrit and no provenance beside it.
    """
    stage_dir = stage_dir or config.WORK_DIR
    os.makedirs(stage_dir, exist_ok=True)
    archive = os.path.join(stage_dir, "%s.7z" % slug)
    if os.path.exists(archive):
        os.remove(archive)
    with tempfile.TemporaryDirectory() as tmp:
        report_path = os.path.join(tmp, "%s.smda" % slug)
        report.toFile(report_path)
        subprocess.run(list(ARCHIVE_COMMAND) + [archive, report_path],
                       check=True, stdout=subprocess.DEVNULL)
    check_size(archive)
    return archive


def _sibling_temp(path):
    """Reserve a scratch name in the directory ``path`` lives in.

    os.replace is only atomic within one filesystem, so anything that will be
    moved over a committed file has to be staged next to it rather than in the
    work dir, which MCRIT_DATA_WORK_DIR can put on a different device.
    """
    directory, name = os.path.split(path)
    handle, temp = tempfile.mkstemp(dir=directory, prefix=".%s." % name,
                                    suffix=".tmp")
    os.close(handle)
    return temp


def _discard(path):
    """Remove a scratch file without masking the error that led here."""
    try:
        os.remove(path)
    except OSError:
        pass


def commit_artifacts(family, arch, slug, archive, export_path):
    """Move a staged .7z and .mcrit into data/ together.

    Both are moved only once both exist and both passed the size check, so
    data/ never gains half an artefact.

    Each replacement is copied in beside its target first and then put in
    place with os.replace, and whatever was already committed is kept under a
    scratch name until both replacements have landed. Removing a target before
    writing its successor - which is what this did - meant a failure on the
    second file left the first one already deleted, with nothing left to
    restore: the pair this is supposed to keep together was destroyed rather
    than left alone. Two files cannot be swapped in one step, but each
    individual swap is atomic and nothing that is already committed is removed
    until its replacement is in place, so data/ ends up holding both new files
    or both old ones - and in the one case that cannot be undone, a put-back
    that itself fails, the old file is left on disk under its scratch name and
    the path to it is logged.
    """
    check_size(archive)
    check_size(export_path)
    archive_target = os.path.join(smda_dir(family, arch), "%s.7z" % slug)
    mcrit_target = os.path.join(mcrit_dir(family, arch), "%s.mcrit" % slug)
    os.makedirs(os.path.dirname(archive_target), exist_ok=True)
    os.makedirs(os.path.dirname(mcrit_target), exist_ok=True)
    staged = []
    backups = {}
    committed = []
    try:
        # Copying is the part that can run out of space or cross a device
        # boundary, and while it runs nothing committed has been touched yet.
        for source, target in ((archive, archive_target),
                               (export_path, mcrit_target)):
            incoming = _sibling_temp(target)
            staged.append((source, incoming, target))
            shutil.copyfile(source, incoming)
        for _, incoming, target in staged:
            if os.path.exists(target):
                backup = _sibling_temp(target)
                os.replace(target, backup)
                backups[target] = backup
            os.replace(incoming, target)
            committed.append(target)
    except OSError:
        # Put data/ back the way it was: restore anything that was moved
        # aside, and remove a replacement that landed where there had been
        # nothing. A lone .7z, or a .7z that no longer matches its .mcrit, is
        # exactly what this function exists to prevent.
        for _, incoming, target in staged:
            _discard(incoming)
            backup = backups.pop(target, None)
            if backup is None:
                if target in committed:
                    _discard(target)
                continue
            try:
                os.replace(backup, target)
            except OSError:
                # A rename inside one directory that just succeeded in the
                # other direction, so this should not happen - but if it does,
                # the previously committed file is still on disk under the
                # scratch name and must not be cleaned up behind the error.
                LOGGER.error("could not put %s back; the file that was there "
                             "is now at %s", target, backup)
        raise
    for backup in backups.values():
        _discard(backup)
    # The staged pair is consumed, as it was when this moved rather than
    # copied: the work dir is scratch space and a leftover copy there would be
    # picked up by a later run as if it were fresh.
    for source, _, _ in staged:
        _discard(source)
    return archive_target, mcrit_target


def check_size(path):
    size = os.path.getsize(path)
    if size > config.MAX_COMMITTED_FILE_SIZE:
        raise PackagingError(
            "%s is %.1f MB, above the %d MB GitHub blob limit - this artefact "
            "cannot be committed as-is" % (path, size / 1024 / 1024,
                                           config.MAX_COMMITTED_FILE_SIZE // 1024 // 1024))


def atomic_write_text(path, text):
    """Replace ``path`` with ``text``, or leave it exactly as it was.

    Opening a committed file for writing truncates it before a single byte of
    the replacement exists, so an interruption - a crash, an OOM kill, a
    Ctrl-C - leaves a half-written file where a valid one used to be. The
    replacement is written beside the original and moved over it with
    os.replace, which is atomic on the same filesystem: a reader, or the next
    run, sees either the whole old file or the whole new one.

    Shared by every in-place writer in this tooling (provenance records here
    and in refresh_provenance, the patched exports in corpus.reprocess), which
    all rewrite a file the repository already has committed.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    temp = _sibling_temp(path)
    try:
        with open(temp, "w", encoding="utf-8") as handle:
            handle.write(text)
            # The rename is ordered against the data only once the data has
            # actually reached the disk; without this a power loss can leave
            # the new name pointing at an empty file.
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except BaseException:
        _discard(temp)
        raise


def write_provenance(family, entries):
    """Record how each artefact of a family was produced.

    The SMDA metadata block only has room for family/version/component, which
    is not enough to retrace a build. Everything else - source URL, archive
    digest or commit, compiler and flags, and any functions removed - is kept
    here so a generated artefact stays traceable to unmodified upstream source.
    """
    path = os.path.join(config.DATA_DIR, family, "provenance.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    existing = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            existing = json.load(handle)
    existing.update(entries)
    # Re-serialised whole, so a write that stops half way would otherwise take
    # every other record of the family down with the one being added.
    atomic_write_text(path, json.dumps(existing, indent=2, sort_keys=True) + "\n")
    return path
