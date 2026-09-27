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


def download(url, expected_sha256):
    """Fetch ``url`` into the download cache and verify it against its pin.

    A cached file whose digest no longer matches is re-downloaded once, which
    covers a truncated earlier transfer without masking a genuine mismatch.
    """
    if not expected_sha256:
        raise FetchError("url sources must pin sha256 (%s); an unpinned "
                         "download records whatever the server happened to "
                         "serve and cannot be reproduced" % url)
    config.ensure_dirs()
    # The basename alone is not unique - "v1.0.0.tar.gz" and "master.zip" are
    # what a dozen GitHub archive URLs are called - so two recipes would share
    # one cache entry and the second would silently build the first's source.
    # The URL digest namespaces the cache; the file keeps its own name so
    # recorded provenance stays readable.
    bucket = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    cache_dir = os.path.join(config.DOWNLOAD_DIR, bucket)
    os.makedirs(cache_dir, exist_ok=True)
    target = os.path.join(cache_dir, os.path.basename(url.split("?")[0]))
    for attempt in range(2):
        if not os.path.exists(target):
            subprocess.run(["curl", "-sSL", "--fail", "--retry", "3",
                            "-o", target, url], check=True)
        digest = sha256_file(target)
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


def _reject_escaping_paths(names, destination):
    """Refuse members that would be written outside ``destination``.

    CVE-2007-4559: an archive member may be named "../../x" or be an absolute
    path, and a plain extractall happily writes there. Upstream archives are
    pinned by digest, but a pin only proves the file is the one upstream
    published, not that it is harmless.
    """
    root = os.path.realpath(destination)
    for name in names:
        target = os.path.realpath(os.path.join(root, name))
        if target != root and not target.startswith(root + os.sep):
            raise FetchError("archive member %r would extract outside %s"
                             % (name, destination))


def _extract(archive, destination):
    # tarfile and zipfile raise their own exception hierarchies, and the
    # "data" filter's rejections are TarErrors rather than RuntimeErrors, so
    # none of them would be caught by callers that handle FetchError.
    try:
        _extract_unchecked(archive, destination)
    except (tarfile.TarError, zipfile.BadZipFile) as error:
        raise FetchError("could not unpack %s: %s" % (archive, error))


def _extract_unchecked(archive, destination):
    os.makedirs(destination, exist_ok=True)
    if archive.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            _reject_escaping_paths(zf.namelist(), destination)
            zf.extractall(destination)
    elif archive.endswith((".7z", ".lzma")):
        subprocess.run(["7z", "x", "-y", "-o%s" % destination, archive],
                       check=True, stdout=subprocess.DEVNULL)
    else:
        with tarfile.open(archive) as tf:
            # The "data" filter rejects escaping paths, absolute names, links
            # pointing out of the tree and device nodes. It landed in 3.11.4,
            # so an older interpreter falls back to the path check alone.
            if hasattr(tarfile, "data_filter"):
                tf.extractall(destination, filter="data")
            else:
                _reject_escaping_paths((m.name for m in tf.getmembers()), destination)
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
        # A submodule that fails to fetch used to be ignored, which produces a
        # build from an incomplete tree - and the artefact then silently lacks
        # whatever the submodule contributed.
        subprocess.run(["git", "-C", workspace, "submodule", "update", "-q",
                        "--init", "--recursive", "--depth", "1"], check=True)
        commit = subprocess.run(["git", "-C", workspace, "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=True).stdout.strip()
        root = workspace
        provenance = {"git_url": source.git_url, "git_ref": source.git_ref, "commit": commit}
        # Submodule code ends up in the artefact, so the commit of the parent
        # repository alone does not pin what was built.
        submodules = subprocess.run(["git", "-C", workspace, "submodule", "status",
                                     "--recursive"],
                                    capture_output=True, text=True, check=True).stdout
        recorded = [line.strip() for line in submodules.splitlines() if line.strip()]
        if recorded:
            provenance["submodules"] = recorded
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
