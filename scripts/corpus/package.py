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


def smda_dir(family, arch):
    return os.path.join(config.DATA_DIR, family, arch, "smda")


def mcrit_dir(family, arch):
    return os.path.join(config.DATA_DIR, family, arch, "mcrit")


def write_smda_archive(report, family, arch, slug):
    """Serialise ``report`` and store it as data/<family>/<arch>/smda/<slug>.7z."""
    target_dir = smda_dir(family, arch)
    os.makedirs(target_dir, exist_ok=True)
    archive = os.path.join(target_dir, "%s.7z" % slug)
    if os.path.exists(archive):
        os.remove(archive)
    with tempfile.TemporaryDirectory() as tmp:
        report_path = os.path.join(tmp, "%s.smda" % slug)
        report.toFile(report_path)
        # -mx=9 matches the compression level of the archives already committed.
        subprocess.run(["7z", "a", "-t7z", "-mx=9", archive, report_path],
                       check=True, stdout=subprocess.DEVNULL)
    _check_size(archive)
    return archive


def write_mcrit(export_path, family, arch, slug):
    target_dir = mcrit_dir(family, arch)
    os.makedirs(target_dir, exist_ok=True)
    target = os.path.join(target_dir, "%s.mcrit" % slug)
    shutil.move(export_path, target)
    _check_size(target)
    return target


def _check_size(path):
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
