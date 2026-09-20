"""Write generated artefacts into data/ following repository conventions.

Layout mirrors what is already committed:

    data/<Family>/<arch>/smda/<slug>.7z     (7z of one <slug>.smda report)
    data/<Family>/<arch>/mcrit/<slug>.mcrit
"""

import json
import os
import shutil
import subprocess
import tempfile

from . import config


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


def commit_artifacts(family, arch, slug, archive, export_path):
    """Move a staged .7z and .mcrit into data/ together.

    Both are moved only once both exist and both passed the size check, so
    data/ never gains half an artefact.
    """
    check_size(archive)
    check_size(export_path)
    archive_target = os.path.join(smda_dir(family, arch), "%s.7z" % slug)
    mcrit_target = os.path.join(mcrit_dir(family, arch), "%s.mcrit" % slug)
    os.makedirs(os.path.dirname(archive_target), exist_ok=True)
    os.makedirs(os.path.dirname(mcrit_target), exist_ok=True)
    moved = []
    try:
        for source, target in ((archive, archive_target), (export_path, mcrit_target)):
            if os.path.exists(target):
                os.remove(target)
            shutil.move(source, target)
            moved.append(target)
    except OSError:
        # Put data/ back the way it was; a lone .7z is exactly what this
        # function exists to prevent.
        for target in moved:
            if os.path.exists(target):
                os.remove(target)
        raise
    return archive_target, mcrit_target


def check_size(path):
    size = os.path.getsize(path)
    if size > config.MAX_COMMITTED_FILE_SIZE:
        raise PackagingError(
            "%s is %.1f MB, above the %d MB GitHub blob limit - this artefact "
            "cannot be committed as-is" % (path, size / 1024 / 1024,
                                           config.MAX_COMMITTED_FILE_SIZE // 1024 // 1024))


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
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(existing, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path
