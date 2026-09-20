"""Download, verify and unpack unmodified upstream source."""

import hashlib
import os
import shutil
import subprocess
import tarfile
import zipfile

from . import config


class FetchError(RuntimeError):
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url, expected_sha256=None):
    """Fetch ``url`` into the download cache and verify it.

    A cached file whose digest no longer matches is re-downloaded once, which
    covers a truncated earlier transfer without masking a genuine mismatch.
    """
    config.ensure_dirs()
    target = os.path.join(config.DOWNLOAD_DIR, os.path.basename(url.split("?")[0]))
    for attempt in range(2):
        if not os.path.exists(target):
            subprocess.run(["curl", "-sSL", "--fail", "--retry", "3",
                            "-o", target, url], check=True)
        digest = sha256_file(target)
        if expected_sha256 is None:
            return target, digest
        if digest == expected_sha256:
            return target, digest
        os.remove(target)
        if attempt:
            raise FetchError("sha256 mismatch for %s: expected %s, got %s"
                             % (url, expected_sha256, digest))
    raise FetchError("unreachable")


def fetch_dependency(source, name):
    """Materialise a statically linked dependency, returning (path, provenance).

    A dependency whose code ends up inside the artefact has to be pinned and
    recorded just like the main source; fetching one inside a build step with
    curl would verify nothing and record nothing.

    A tarball is returned as the verified archive path, for the recipe to
    unpack where it wants; a git source is returned as a checkout directory.
    """
    if source.git_url:
        return fetch_source(source, name)
    archive, digest = download(source.url, source.sha256)
    return archive, {"url": source.url, "sha256": digest,
                     "archive": os.path.basename(archive)}


def _extract(archive, destination):
    os.makedirs(destination, exist_ok=True)
    if archive.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(destination)
    elif archive.endswith((".7z", ".lzma")):
        subprocess.run(["7z", "x", "-y", "-o%s" % destination, archive],
                       check=True, stdout=subprocess.DEVNULL)
    else:
        with tarfile.open(archive) as tf:
            tf.extractall(destination)


def _single_child(path):
    entries = [e for e in os.listdir(path) if not e.startswith(".")]
    if len(entries) == 1 and os.path.isdir(os.path.join(path, entries[0])):
        return os.path.join(path, entries[0])
    return path


def fetch_source(source, name):
    """Materialise ``source`` and return (source_root, provenance_dict).

    The source tree is always unpacked fresh so a previous build cannot leak
    into the next one; upstream files themselves are never modified.
    """
    config.ensure_dirs()
    workspace = os.path.join(config.SOURCE_DIR, name)
    if os.path.exists(workspace):
        shutil.rmtree(workspace)

    if source.git_url:
        if not source.git_ref:
            raise FetchError("git sources must pin git_ref to a tag or commit")
        os.makedirs(workspace)
        subprocess.run(["git", "init", "-q", workspace], check=True)
        subprocess.run(["git", "-C", workspace, "remote", "add", "origin", source.git_url],
                       check=True)
        subprocess.run(["git", "-C", workspace, "fetch", "-q", "--depth", "1",
                        "origin", source.git_ref], check=True)
        subprocess.run(["git", "-C", workspace, "checkout", "-q", "FETCH_HEAD"], check=True)
        subprocess.run(["git", "-C", workspace, "submodule", "update", "-q",
                        "--init", "--recursive", "--depth", "1"], check=False)
        commit = subprocess.run(["git", "-C", workspace, "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=True).stdout.strip()
        root = workspace
        provenance = {"git_url": source.git_url, "git_ref": source.git_ref, "commit": commit}
    else:
        if not source.url:
            raise FetchError("source needs either url or git_url")
        archive, digest = download(source.url, source.sha256)
        _extract(archive, workspace)
        root = _single_child(workspace)
        provenance = {"url": source.url, "sha256": digest,
                      "archive": os.path.basename(archive)}

    if source.strip_prefix:
        root = os.path.join(root, source.strip_prefix)
    if not os.path.isdir(root):
        raise FetchError("source root %s does not exist after extraction" % root)
    return root, provenance
