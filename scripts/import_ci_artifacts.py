#!/usr/bin/env python3
"""Bring the artefacts a Windows CI run built into data/.

  python scripts/import_ci_artifacts.py --run-id 35533512099
  python scripts/import_ci_artifacts.py --branch main
  python scripts/import_ci_artifacts.py --commit 26f394f --dry-run
  python scripts/import_ci_artifacts.py --zip reference-data-x64.zip \\
                                        --zip reference-data-x86.zip

.github/workflows/windows-reference-data.yml builds the families that need
MSVC - VX-API, BlackBone, SysWhispers - on a windows-2022 runner and uploads
the results with actions/upload-artifact instead of committing them, so that a
maintainer reviews them before they enter the corpus. Nothing carried out the
other half of that: the five MSVC artefacts in data/ were downloaded and
placed by hand, and a planned wave of MSVC builds across ~30 library families
would mean a manual download, unpack and merge per family. This is that half.

What makes it more than "unzip into data/":

* Each job uploads only the architecture it built. The checkout it builds from
  already holds the committed artefacts of the *other* architecture, so the
  workflow's "Scope the artefacts to what this job produced" step prunes the
  tree to the slugs that run actually produced, and - because provenance.json
  is per-family rather than per-architecture - writes a provenance.<arch>.json
  beside it and uploads that instead. Unpacking both artifacts naively let
  whichever landed last overwrite the other architecture's records; for
  SysWhispers, whose x86 leg builds nothing, the x86 copy is an empty object
  and would have reverted the x64 leg outright. Records are merged here, per
  family, across architectures and with what is already committed.

* upload-artifact strips the longest common directory prefix of the files it
  matches. With all three families present that prefix is "data", so the zip
  is rooted at <Family>/..., not data/<Family>/...; build a single family and
  the prefix becomes data/<Family> and the zip is rooted at <arch>/...  The
  tree is therefore located from the provenance records - which carry the full
  repository-relative path of every file - rather than from the zip's shape.

* Nothing committed is destroyed by a failure. Every artefact is verified
  before anything is written, and the writes go through corpus.package, whose
  commit_artifacts stages both files beside their targets and moves them into
  place with os.replace. This repository has already lost an archive to an
  interrupted in-place write; the same discipline applies here.

Verification, per artefact, before a byte of data/ is touched:

* the downloaded zip matches the sha256 GitHub records for the artifact;
* the tree is exactly data/<Family>/<arch>/{smda,mcrit}/<slug>.{7z,mcrit},
  with <arch> and <Family> agreeing with the record's own fields;
* the .7z and the .mcrit are both present - a lone one of either is refused,
  and so is a file no provenance record accounts for;
* the .7z holds exactly one <slug>.smda and nothing else;
* the sha256 recorded in provenance is the digest of the analysed binary, so
  it cannot be recomputed from the artefact - what is checked instead is that
  the record, the SMDA report inside the .7z and the sample entry inside the
  .mcrit all name the same digest, which is what a mixed-up or truncated
  upload breaks;
* num_functions in the record equals the report's statistics and the export's,
  and family, version and component agree across all three;
* the export carries the corpus minhash and shingler config hashes, since one
  that disagrees would import into MCRIT and then match nothing;
* neither file is over the GitHub blob limit.

Exits non-zero if any artefact failed verification or could not be committed.
"""

import argparse
import hashlib
import json
import os
import posixpath
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from corpus import config, package


DEFAULT_REPO = "r0ny123/mcrit-data"
WORKFLOW = "windows-reference-data.yml"
API = "https://api.github.com"

# Where downloads and unpacked trees go. Under the work directory, which
# .gitignore excludes, so a half-imported run never shows up in git status.
STAGE_DIR = os.path.join(config.WORK_DIR, "ci-import")


class ImportProblem(RuntimeError):
    """A problem that stops the run before anything is written."""


class Artefact(object):
    """One verified .7z/.mcrit/record triple waiting to be committed."""

    def __init__(self, family, arch, slug, record, archive, export):
        self.family = family
        self.arch = arch
        self.slug = slug
        self.record = record
        self.archive = archive
        self.export = export

    def __repr__(self):
        return "<Artefact %s>" % self.slug


# --------------------------------------------------------------------------
# GitHub
# --------------------------------------------------------------------------

class _StripAuthOnRedirect(urllib.request.HTTPRedirectHandler):
    """Drop the bearer token when a download redirects off api.github.com.

    The artifact download endpoint answers 302 with a pre-signed blob URL that
    already carries its own signature. urllib copies every header of the
    original request onto the redirect target, so the token is presented to
    the blob store as well, and it answers 401 "Server failed to authenticate
    the request" - which reads like a bad token rather than one too many. curl
    drops the header on a cross-host redirect; urllib does not, so it is
    dropped here.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super(_StripAuthOnRedirect, self).redirect_request(
            req, fp, code, msg, headers, newurl)
        if new is not None:
            for store in (new.headers, new.unredirected_hdrs):
                for name in [n for n in store if n.lower() == "authorization"]:
                    del store[name]
        return new


def _token():
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(name)
        if value:
            return value
    raise ImportProblem(
        "no GitHub token in GITHUB_TOKEN or GH_TOKEN. Listing and downloading "
        "workflow artifacts both need one; pass --zip with files fetched "
        "another way to work without it")


def _request(url, token):
    # The download endpoint answers 415 to Accept: application/zip - it is a
    # normal API call that happens to redirect to a zip, so it wants the API
    # media type like every other one.
    return urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "mcrit-data/import_ci_artifacts",
    })


def _api(path, token):
    opener = urllib.request.build_opener(_StripAuthOnRedirect)
    try:
        with opener.open(_request(API + path, token)) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise ImportProblem("GET %s: HTTP %d %s" % (path, error.code, error.reason))


def resolve_run(repo, token, run_id=None, branch=None, commit=None):
    """Find the workflow run to import from.

    A run id names one run outright. Otherwise the newest successful run of
    the Windows workflow is taken, optionally narrowed to a branch or to a
    commit - narrowed by commit rather than filtered client-side, because the
    API has no head_sha filter and a commit can be several pages back.
    """
    if run_id:
        run = _api("/repos/%s/actions/runs/%s" % (repo, run_id), token)
        conclusion = run.get("conclusion")
        if conclusion != "success":
            # A named run is imported anyway, with a warning. The workflow
            # deliberately uploads the artefacts that built even when another
            # recipe failed - one broken recipe used to discard a whole leg's
            # output - so refusing a red run here would throw away exactly the
            # data that arrangement exists to save. Every artefact is verified
            # individually further down regardless of how the run concluded,
            # which is what actually makes this safe; the run's conclusion is
            # a hint about completeness, not about correctness.
            #
            # Only for an explicitly named run. The branch and commit searches
            # below still take successful runs only, because there "newest" is
            # a guess and a red run is the wrong guess.
            if conclusion is None:
                raise ImportProblem(
                    "run %s has not finished (status %r); its artefacts are "
                    "incomplete" % (run_id, run.get("status")))
            LOGGER.warning(
                "run %s concluded %r, not success. Importing it anyway "
                "because it was named explicitly - but it built less than it "
                "was asked to, so expect fewer artefacts than recipes.",
                run_id, conclusion)
        return run

    query = "?status=success&per_page=100"
    if branch:
        query += "&branch=" + urllib.parse.quote(branch)
    page = _api("/repos/%s/actions/workflows/%s/runs%s" % (repo, WORKFLOW, query),
                token)
    runs = page.get("workflow_runs", [])
    if commit:
        runs = [r for r in runs if r.get("head_sha", "").startswith(commit)]
    if not runs:
        raise ImportProblem(
            "no successful %s run found for %s" % (WORKFLOW, branch or commit or repo))
    # The API returns runs newest first, and a re-run of the same commit is a
    # separate run, so this is the most recent green result.
    return runs[0]


def list_artifacts(repo, run_id, token):
    page = _api("/repos/%s/actions/runs/%s/artifacts?per_page=100" % (repo, run_id),
                token)
    return [a for a in page.get("artifacts", [])
            if a.get("name", "").startswith("reference-data-")]


def download_artifact(artifact, token, dest_dir):
    """Fetch one artifact zip and check it against the digest GitHub records.

    The digest is the only end-to-end integrity check available on the way in:
    everything after this point reads files that came out of this zip, so a
    truncated transfer would otherwise surface as a confusing parse error
    somewhere in verification.
    """
    os.makedirs(dest_dir, exist_ok=True)
    target = os.path.join(dest_dir, "%s.zip" % artifact["name"])
    opener = urllib.request.build_opener(_StripAuthOnRedirect)
    digest = hashlib.sha256()
    # Written beside the target and moved over it, so an interrupted download
    # cannot leave a short zip that a later run mistakes for a complete one.
    temp = target + ".part"
    try:
        with opener.open(_request(artifact["archive_download_url"], token)) as response:
            with open(temp, "wb") as handle:
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    digest.update(chunk)
                    handle.write(chunk)
        expected = (artifact.get("digest") or "").split(":")[-1]
        if expected and digest.hexdigest() != expected:
            raise ImportProblem("%s: downloaded zip is %s, GitHub records %s"
                               % (artifact["name"], digest.hexdigest(), expected))
        os.replace(temp, target)
    except urllib.error.HTTPError as error:
        raise ImportProblem("downloading %s: HTTP %d %s"
                           % (artifact["name"], error.code, error.reason))
    finally:
        if os.path.exists(temp):
            os.remove(temp)
    return target


# --------------------------------------------------------------------------
# Unpacking and discovery
# --------------------------------------------------------------------------

def unpack(zip_path, dest_dir):
    """Extract one artifact zip into its own directory under ``dest_dir``."""
    name = os.path.basename(zip_path)
    if name.endswith(".zip"):
        name = name[:-4]
    target = os.path.join(dest_dir, name)
    # A re-run must not read files an earlier run left behind: the workflow
    # prunes to what each job built, so a leftover from a previous import
    # would be an artefact this run is not importing at all.
    shutil.rmtree(target, ignore_errors=True)
    os.makedirs(target)
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.namelist():
            # zipfile sanitises these itself, but an entry that needed
            # sanitising means the zip is not what this expects, and silently
            # importing a renamed version of it is worse than refusing.
            if os.path.isabs(member) or ".." in member.replace("\\", "/").split("/"):
                raise ImportProblem("%s: refusing entry %r" % (zip_path, member))
        archive.extractall(target)
    return target


def _staged_files(root):
    """Map every unpacked .7z/.mcrit to its path relative to ``root``."""
    files = {}
    for dirpath, _, names in os.walk(root):
        for name in names:
            if name.endswith((".7z", ".mcrit")):
                full = os.path.join(dirpath, name)
                files[os.path.relpath(full, root).replace(os.sep, "/")] = full
    return files


def _staged_records(root, problems):
    """Read every provenance.<arch>.json an unpacked artifact carries.

    provenance.json itself is excluded from the upload - it is per-family and
    both jobs would ship their own whole-file copy of it - so only the
    architecture-named ones are read, and a run whose workflow predates that
    split has nothing here and is reported rather than half-imported.
    """
    records = {}
    found = False
    for dirpath, _, names in os.walk(root):
        for name in sorted(names):
            if not (name.startswith("provenance.") and name.endswith(".json")):
                continue
            if name == "provenance.json":
                problems.append(
                    "%s: carries a whole-family provenance.json; that file is "
                    "per-family, not per-architecture, and importing it would "
                    "overwrite the other architecture's records"
                    % os.path.relpath(os.path.join(dirpath, name), root))
                continue
            found = True
            with open(os.path.join(dirpath, name), encoding="utf-8") as handle:
                for slug, record in json.load(handle).items():
                    if slug in records and records[slug] != record:
                        problems.append(
                            "%s: two provenance files in one artifact disagree "
                            "about %s" % (os.path.basename(root), slug))
                        continue
                    records[slug] = record
    if not found:
        problems.append("%s: holds no provenance.<arch>.json"
                        % os.path.basename(root))
    return records


def _match(record_path, files):
    """Find the staged file a record's repository-relative path refers to.

    upload-artifact strips the longest common directory prefix of what it
    matched, and how much that is depends on how many families the run built,
    so the staged path is a suffix of the recorded one rather than equal to
    it: with three families the zip is rooted at <Family>/, with one it is
    rooted at <arch>/. Matching on the suffix covers every prefix the uploader
    can strip while still refusing a file that is somewhere else entirely.
    """
    wanted = record_path.replace("\\", "/").strip("/").split("/")
    hits = []
    for key, (relative, full) in files.items():
        parts = relative.split("/")
        if parts and len(parts) <= len(wanted) \
                and parts == wanted[len(wanted) - len(parts):]:
            hits.append((key, full))
    return hits


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------

def _read_smda(archive, slug):
    """Return the one SMDA report inside a staged .7z."""
    with tempfile.TemporaryDirectory(prefix="ci-import-") as tmp:
        result = subprocess.run(["7z", "x", "-y", "-o" + tmp, archive],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise ImportProblem("7z could not read %s: %s"
                               % (os.path.basename(archive),
                                  result.stderr.decode("utf-8", "replace").strip()))
        members = sorted(os.path.relpath(os.path.join(d, n), tmp)
                         for d, _, ns in os.walk(tmp) for n in ns)
        if members != ["%s.smda" % slug]:
            raise ImportProblem("%s holds %s, expected one %s.smda"
                               % (os.path.basename(archive),
                                  ", ".join(members) or "nothing", slug))
        with open(os.path.join(tmp, members[0]), encoding="utf-8") as handle:
            return json.load(handle)


def _check_layout(family, arch, slug, record, problems):
    """The paths a record states have to be the layout data/ actually uses."""
    if arch not in ("x86", "x64"):
        problems.append("%s: architecture %r is not x86 or x64" % (slug, arch))
        return False
    ok = True
    for key, subdir, suffix in (("smda", "smda", ".7z"), ("mcrit", "mcrit", ".mcrit")):
        expected = posixpath.join("data", family, arch, subdir, slug + suffix)
        actual = (record.get(key) or "").replace("\\", "/")
        if actual != expected:
            problems.append("%s: record's %s path is %r, expected %r"
                            % (slug, key, actual, expected))
            ok = False
    return ok


def verify(records, files):
    """Check every record against its files, and every file against a record.

    Returns (artefacts, problems). Nothing here writes, so a caller can run
    the whole check before deciding to commit anything.
    """
    artefacts = []
    problems = []
    claimed = set()
    for slug in sorted(records):
        record = records[slug]
        family = record.get("family")
        arch = record.get("architecture")
        if not family:
            problems.append("%s: record names no family" % slug)
            continue
        if not _check_layout(family, arch, slug, record, problems):
            continue

        paths = {}
        missing = False
        for key in ("smda", "mcrit"):
            hits = _match(record[key], files)
            if len(hits) != 1:
                # The pairing rule: a .7z whose .mcrit did not survive the
                # upload describes a sample the corpus cannot search, and a
                # .mcrit with no .7z has no report behind it. Either way the
                # artefact is refused rather than half-imported.
                problems.append("%s: %s matches %d staged files, expected 1 (%s)"
                                % (slug, record[key], len(hits), record[key]))
                missing = True
                continue
            paths[key] = hits[0][1]
            claimed.add(hits[0][0])
        if missing:
            continue

        try:
            _verify_contents(slug, record, family, arch, paths)
        except (ImportProblem, package.PackagingError) as error:
            problems.append("%s: %s" % (slug, error))
            continue
        except (ValueError, KeyError, OSError) as error:
            problems.append("%s: unreadable artefact: %s" % (slug, error))
            continue
        artefacts.append(Artefact(family, arch, slug, record,
                                  paths["smda"], paths["mcrit"]))

    for key in sorted(set(files) - claimed):
        # An artefact with no record cannot be traced back to a build, which
        # is the whole point of provenance; committing it would leave data/ in
        # the state validate.find_unrecorded_artifacts reports. This is also
        # what catches a .7z whose .mcrit never made it into the upload when
        # the record for it was pruned away too.
        problems.append("%s: no provenance record accounts for this file" % key)
    return artefacts, problems


def _verify_contents(slug, record, family, arch, paths):
    """Cross-check the record, the SMDA report and the MCRIT export."""
    package.check_size(paths["smda"])
    package.check_size(paths["mcrit"])

    sha256 = record.get("sha256")
    if not sha256:
        raise ImportProblem("record has no sha256")
    count = record.get("num_functions")

    report = _read_smda(paths["smda"], slug)
    if report.get("sha256") != sha256:
        raise ImportProblem("provenance records sha256 %s, the SMDA report in "
                           "the archive is of %s" % (sha256, report.get("sha256")))
    report_count = report.get("statistics", {}).get("num_functions")
    if count is not None and report_count != count:
        raise ImportProblem("provenance records %r functions, the SMDA report "
                           "has %r" % (count, report_count))
    metadata = report.get("metadata", {})
    for key, value in (("family", family), ("version", record.get("version")),
                       ("component", record.get("component"))):
        if value is not None and metadata.get(key) != value:
            raise ImportProblem("SMDA report's %s is %r, provenance says %r"
                               % (key, metadata.get(key), value))

    with open(paths["mcrit"], encoding="utf-8") as handle:
        export = json.load(handle)
    minhash = export.get("config", {}).get("minhash")
    shingler = export.get("config", {}).get("shingler")
    if minhash != config.EXPECTED_MINHASH_CONFIG:
        raise ImportProblem("export's minhash config %s does not match the "
                           "corpus (%s)" % (minhash, config.EXPECTED_MINHASH_CONFIG))
    if shingler != config.EXPECTED_SHINGLER_CONFIG:
        raise ImportProblem("export's shingler config %s does not match the "
                           "corpus (%s)" % (shingler, config.EXPECTED_SHINGLER_CONFIG))
    samples = export.get("sample_entries", {})
    if list(samples) != [sha256]:
        raise ImportProblem("export holds samples %s, expected only %s"
                           % (", ".join(s[:12] for s in samples) or "none",
                              sha256[:12]))
    sample = samples[sha256]
    export_count = sample.get("statistics", {}).get("num_functions")
    if count is not None and export_count != count:
        raise ImportProblem("provenance records %r functions, the export has %r"
                           % (count, export_count))
    for key, value in (("family", family), ("version", record.get("version"))):
        if value is not None and sample.get(key) != value:
            raise ImportProblem("export's %s is %r, provenance says %r"
                               % (key, sample.get(key), value))


# --------------------------------------------------------------------------
# Merging and committing
# --------------------------------------------------------------------------

def merge_records(per_artifact):
    """Union the records of every architecture, refusing a genuine collision.

    ``per_artifact`` is a list of (label, records) - one entry per downloaded
    artifact. A slug carries its own architecture, so the two legs cannot
    legitimately describe the same one; if they do, the scoping step in the
    workflow has stopped working and merging would silently pick a winner.
    """
    merged = {}
    origin = {}
    problems = []
    for label, records in per_artifact:
        for slug, record in records.items():
            if slug in merged and merged[slug] != record:
                problems.append("%s: %s and %s disagree about this artefact"
                                % (slug, origin[slug], label))
                continue
            merged[slug] = record
            origin.setdefault(slug, label)
    return merged, problems


def commit(artefacts, dry_run=False):
    """Move the verified artefacts into data/, one artefact at a time.

    Each artefact is described by three files - the .7z, the .mcrit and its
    provenance record - and lands in all three or in none. commit_artifacts
    stages both data files beside their targets and swaps them in with
    os.replace, keeping whatever was committed under a scratch name until both
    replacements are in place, so a failure leaves the previously committed
    pair exactly as it was. The record is written only once that pair has
    landed: a record pointing at bytes that are not there is worse than an
    artefact this run has not got round to recording yet, and validate's
    find_miscounted_provenance reports the latter.

    Artefacts are committed in order and the first failure stops the run, so
    what is on disk afterwards is a prefix of this list plus everything that
    was already there.
    """
    changed = []
    problems = []
    for artefact in artefacts:
        if dry_run:
            changed.append(artefact)
            continue
        try:
            package.commit_artifacts(artefact.family, artefact.arch, artefact.slug,
                                     artefact.archive, artefact.export)
        except (OSError, package.PackagingError) as error:
            problems.append("%s: not imported: %s" % (artefact.slug, error))
            break
        try:
            package.write_provenance(artefact.family, {artefact.slug: artefact.record})
        except OSError as error:
            # The one window this cannot close. Both data files are in place
            # and the record is not, which validate reports as an unrecorded
            # artefact; re-running the import repairs it.
            problems.append("%s: files committed but provenance was not written "
                            "(%s); re-run to repair" % (artefact.slug, error))
            break
        changed.append(artefact)
    return changed, problems


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------

def _scope_to_artifact_arch(label, records, problems):
    """Drop records whose architecture is not the one this artifact is for.

    reference-data-x86 carrying an x64 record is the shape the workflow's
    scoping step exists to prevent: before it existed each leg uploaded
    data/<family>/** from a checkout that already held the other
    architecture's committed files, and unpacking both artifacts let whichever
    landed last overwrite the architecture it had not built. If that ever
    comes back, the two artifacts overlap and merging them would be a coin
    toss, so the record is refused rather than merged.
    """
    arch = label.rsplit("-", 1)[-1]
    if arch not in ("x86", "x64"):
        return records
    kept = {}
    for slug, record in records.items():
        if record.get("architecture") == arch:
            kept[slug] = record
        else:
            problems.append("%s: record is %r but arrived in the %s artifact"
                            % (slug, record.get("architecture"), label))
    return kept


def gather(zips, stage_dir):
    """Unpack each artifact zip and read what it holds.

    Returns (per_artifact, files, problems), where per_artifact pairs each
    artifact's label with its records and ``files`` maps a unique key to the
    (relative path, absolute path) of every staged data file across all of
    them.
    """
    per_artifact = []
    files = {}
    problems = []
    for zip_path in zips:
        root = unpack(zip_path, stage_dir)
        label = os.path.basename(root)
        records = _scope_to_artifact_arch(
            label, _staged_records(root, problems), problems)
        per_artifact.append((label, records))
        for relative, full in _staged_files(root).items():
            # Keyed under the artifact's name so that two legs shipping the
            # same relative path stay distinguishable, which is what lets
            # verify report an overlap instead of silently merging one away.
            files[posixpath.join(label, relative)] = (relative, full)
    return per_artifact, files, problems


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--run-id", help="import this workflow run")
    source.add_argument("--branch",
                        help="import the latest successful run of this branch")
    source.add_argument("--commit",
                        help="import the latest successful run of this commit")
    parser.add_argument("--repo", default=DEFAULT_REPO,
                        help="owner/name to fetch from (default %(default)s)")
    parser.add_argument("--zip", action="append", dest="zips", metavar="PATH",
                        help="import an already-downloaded artifact zip "
                             "instead of fetching one; repeatable")
    parser.add_argument("--stage-dir", default=STAGE_DIR,
                        help="where downloads and unpacked trees go "
                             "(default %(default)s)")
    parser.add_argument("--dry-run", action="store_true",
                        help="verify and report, write nothing")
    args = parser.parse_args()

    # A host without 7z cannot check what is inside a single archive, and an
    # import that skipped that check would be committing unread bytes.
    try:
        package.check_7z()
    except package.PackagingError as error:
        print("ERROR: %s" % error)
        return 1

    zips = list(args.zips or [])
    try:
        if not zips:
            token = _token()
            run = resolve_run(args.repo, token, run_id=args.run_id,
                              branch=args.branch, commit=args.commit)
            print("run %s (%s, %s) %s" % (run["id"], run.get("head_branch"),
                                          (run.get("head_sha") or "")[:12],
                                          run.get("html_url", "")))
            artifacts = list_artifacts(args.repo, run["id"], token)
            if not artifacts:
                raise ImportProblem(
                    "run %s has no reference-data-* artifacts; a red run "
                    "uploads only build logs, and artifacts expire" % run["id"])
            for artifact in artifacts:
                if artifact.get("expired"):
                    raise ImportProblem("artifact %s has expired"
                                       % artifact["name"])
                print("downloading %s (%.1f MB)"
                      % (artifact["name"], artifact["size_in_bytes"] / 1024.0 / 1024))
                zips.append(download_artifact(artifact, token, args.stage_dir))
        elif args.run_id or args.branch or args.commit:
            raise ImportProblem("--zip takes the place of --run-id/--branch/--commit")
    except ImportProblem as error:
        print("ERROR: %s" % error)
        return 1

    per_artifact, files, problems = gather(zips, args.stage_dir)
    merged, collisions = merge_records(per_artifact)
    problems.extend(collisions)

    artefacts, failures = verify(merged, files)
    problems.extend(failures)

    for problem in problems:
        print("REFUSED %s" % problem)

    if not artefacts:
        # An empty provenance.<arch>.json is normal on its own, and so is a
        # family being absent from a leg entirely: SysWhispers builds nothing
        # on x86, and the workflow's scoping step now leaves such a family out
        # of the upload rather than shipping an empty record for it. Either
        # shape is fine because the other families supply the records this
        # needs. But a run whose artifacts together yield nothing means the
        # wrong run was named or the workflow has changed, so the caller is
        # told by the exit code and not only by a line of output it may not be
        # reading.
        print("\nnothing to import")
        return 1

    changed, commit_problems = commit(artefacts, dry_run=args.dry_run)
    verb = "would import" if args.dry_run else "imported"
    for artefact in changed:
        print("%s %s/%s %s" % (verb, artefact.family, artefact.arch, artefact.slug))
    for problem in commit_problems:
        print("FAILED %s" % problem)

    families = sorted({a.family for a in changed})
    print("\n%s %d artefact(s) across %d family/families; %d refused, %d failed"
          % (verb, len(changed), len(families), len(problems), len(commit_problems)))
    if families:
        print("families touched: %s" % ", ".join(families))
    return 1 if (problems or commit_problems) else 0


if __name__ == "__main__":
    sys.exit(main())
