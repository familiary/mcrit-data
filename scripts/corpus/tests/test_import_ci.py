"""Tests for the importer that brings CI-built artefacts into data/.

scripts/import_ci_artifacts.py is the only thing in this repository that
writes data/ from bytes it did not produce itself, so what it refuses matters
as much as what it accepts. Every test here runs against a temporary tree with
config.DATA_DIR patched to point at it, so none of them can touch data/.

The cases are the ones that have actually gone wrong, or would have:

* the two architectures are uploaded as separate artifacts, and merging them
  by unpacking one over the other let whichever landed last overwrite the
  other's provenance records;
* upload-artifact strips the longest common directory prefix of what it
  matched, so the zip's root depends on how many families the run built;
* a .7z whose .mcrit did not survive describes a sample the corpus cannot
  search, and vice versa;
* a record whose sha256 does not match the report it claims to describe is a
  mixed-up or truncated upload, not reference data;
* and a failure part way through must leave what is already committed alone -
  this repository has lost an archive to an interrupted in-place write.

    python -m unittest discover -s scripts/corpus/tests
"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

# scripts/, so "corpus" imports the same way build_corpus.py imports it and
# the standalone importer is importable by its own module name.
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

import import_ci_artifacts as ci
from corpus import config, package


HAVE_7Z = shutil.which("7z") is not None

SHA_A = "a" * 64
SHA_B = "b" * 64


def _text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _read(path):
    # The committed .7z is binary once it has been replaced by a real archive,
    # so the before/after comparisons have to be on bytes.
    with open(path, "rb") as handle:
        return handle.read()


def _records(family_dir):
    return json.loads(_text(os.path.join(family_dir, "provenance.json")))


class Spec(object):
    """One artefact as it would appear in an uploaded artifact.

    Defaults describe a consistent artefact; a test names only the field it
    wants wrong, which keeps each case about the one thing it is checking.
    """

    def __init__(self, family="Fam", arch="x64", slug=None, sha256=SHA_A,
                 count=12, version="1.0", component="lib.dll",
                 report_sha256=None, report_count=None, export_count=None,
                 minhash=None, with_archive=True, with_export=True,
                 with_record=True, record_overrides=None):
        self.family = family
        self.arch = arch
        self.slug = slug or "%s_%s_msvc143_%s_%s" % (family, version, arch, component)
        self.sha256 = sha256
        self.count = count
        self.version = version
        self.component = component
        self.report_sha256 = report_sha256 or sha256
        self.report_count = count if report_count is None else report_count
        self.export_count = count if export_count is None else export_count
        self.minhash = minhash or config.EXPECTED_MINHASH_CONFIG
        self.with_archive = with_archive
        self.with_export = with_export
        self.with_record = with_record
        self.record_overrides = record_overrides or {}

    def record(self):
        record = {
            "family": self.family,
            "architecture": self.arch,
            "version": self.version,
            "component": self.component,
            "sha256": self.sha256,
            "num_functions": self.count,
            "smda": "data/%s/%s/smda/%s.7z" % (self.family, self.arch, self.slug),
            "mcrit": "data/%s/%s/mcrit/%s.mcrit" % (self.family, self.arch, self.slug),
        }
        record.update(self.record_overrides)
        return record

    def report(self):
        return {"sha256": self.report_sha256,
                "statistics": {"num_functions": self.report_count},
                "metadata": {"family": self.family, "version": self.version,
                             "component": self.component}}

    def export(self):
        return {"config": {"minhash": self.minhash,
                           "shingler": config.EXPECTED_SHINGLER_CONFIG},
                "content": {"num_samples": 1},
                "sample_entries": {self.sha256: {
                    "sha256": self.sha256,
                    "family": self.family,
                    "version": self.version,
                    "component": self.component,
                    "statistics": {"num_functions": self.export_count}}},
                "function_entries": {self.sha256: {}}}


@unittest.skipUnless(HAVE_7Z, "7z is required to build the test archives")
class TempCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="corpus-ci-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.data = os.path.join(self.tmp, "data")
        os.makedirs(self.data)
        patch = mock.patch.object(config, "DATA_DIR", self.data)
        patch.start()
        self.addCleanup(patch.stop)
        self.stage = os.path.join(self.tmp, "stage")
        self.scratch = os.path.join(self.tmp, "scratch")
        os.makedirs(self.scratch)

    # -- building the inputs -------------------------------------------

    def _archive(self, spec, directory):
        """A .7z holding exactly one <slug>.smda, as the pipeline writes."""
        member = os.path.join(self.scratch, "%s.smda" % spec.slug)
        with open(member, "w", encoding="utf-8") as handle:
            json.dump(spec.report(), handle)
        archive = os.path.join(directory, "%s.7z" % spec.slug)
        subprocess.run(list(package.ARCHIVE_COMMAND) + [archive, member],
                       check=True, stdout=subprocess.DEVNULL)
        os.remove(member)
        return archive

    def artifact(self, arch, specs, root="family", provenance_name=None,
                 extra_files=None):
        """Write one uploaded artifact zip and return its path.

        ``root`` is how much of the path upload-artifact stripped: "family"
        for a run that built several families (the common prefix is data/),
        "arch" for one that built a single family (the prefix reaches
        data/<Family>/), "data" for a hypothetical upload that kept it all.
        """
        tree = os.path.join(self.scratch, "tree-%s" % arch)
        shutil.rmtree(tree, ignore_errors=True)
        by_family = {}
        for spec in specs:
            family_dir = os.path.join(tree, spec.family)
            by_family.setdefault(spec.family, []).append(spec)
            if spec.with_archive:
                smda = os.path.join(family_dir, spec.arch, "smda")
                os.makedirs(smda, exist_ok=True)
                self._archive(spec, smda)
            if spec.with_export:
                mcrit = os.path.join(family_dir, spec.arch, "mcrit")
                os.makedirs(mcrit, exist_ok=True)
                with open(os.path.join(mcrit, "%s.mcrit" % spec.slug),
                          "w", encoding="utf-8") as handle:
                    json.dump(spec.export(), handle)
        # The workflow writes one provenance.<arch>.json per family, holding
        # only the slugs that leg produced - so a family whose x86 leg builds
        # nothing ships an empty object, which is not an error.
        for family in sorted(set([s.family for s in specs])):
            os.makedirs(os.path.join(tree, family), exist_ok=True)
            records = {s.slug: s.record()
                       for s in by_family.get(family, []) if s.with_record}
            name = provenance_name or "provenance.%s.json" % arch
            with open(os.path.join(tree, family, name), "w",
                      encoding="utf-8") as handle:
                json.dump(records, handle)
        for relative, body in (extra_files or {}).items():
            path = os.path.join(tree, relative)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(body)

        zip_path = os.path.join(self.scratch, "reference-data-%s.zip" % arch)
        with zipfile.ZipFile(zip_path, "w") as archive:
            for dirpath, _, names in os.walk(tree):
                for name in names:
                    full = os.path.join(dirpath, name)
                    parts = os.path.relpath(full, tree).split(os.sep)
                    if root == "data":
                        parts = ["data"] + parts
                    elif root == "arch":
                        # The single-family case: the family name is gone too,
                        # and only the records still say where the files go.
                        parts = parts[1:]
                    archive.write(full, "/".join(parts))
        return zip_path

    # -- driving the importer ------------------------------------------

    def run_import(self, zips, dry_run=False):
        """The same sequence main() runs, without the argument parsing."""
        per_artifact, files, problems = ci.gather(zips, self.stage)
        merged, collisions = ci.merge_records(per_artifact)
        problems.extend(collisions)
        artefacts, failures = ci.verify(merged, files)
        problems.extend(failures)
        changed, commit_problems = ci.commit(artefacts, dry_run=dry_run)
        return changed, problems + commit_problems

    def commit_existing(self, spec, archive_body="old-7z", export_body="old-mcrit"):
        """Put an older copy of an artefact into data/, as a checkout has."""
        smda = os.path.join(package.smda_dir(spec.family, spec.arch),
                            "%s.7z" % spec.slug)
        mcrit = os.path.join(package.mcrit_dir(spec.family, spec.arch),
                             "%s.mcrit" % spec.slug)
        for path, body in ((smda, archive_body), (mcrit, export_body)):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(body)
        return smda, mcrit


class MergeTest(TempCase):
    def test_the_two_architectures_merge_rather_than_overwrite(self):
        x64 = Spec(arch="x64")
        x86 = Spec(arch="x86")
        zips = [self.artifact("x64", [x64]), self.artifact("x86", [x86])]
        changed, problems = self.run_import(zips)
        self.assertEqual(problems, [])
        self.assertEqual(sorted(a.slug for a in changed), sorted([x64.slug, x86.slug]))
        # The defect this guards: provenance.json is per-family, so an import
        # that took one leg's copy of it whole would leave the other leg's
        # artefacts in the tree with no record at all.
        self.assertEqual(sorted(_records(os.path.join(self.data, "Fam"))),
                         sorted([x64.slug, x86.slug]))
        for spec in (x64, x86):
            self.assertTrue(os.path.exists(
                os.path.join(package.smda_dir("Fam", spec.arch), "%s.7z" % spec.slug)))
            self.assertTrue(os.path.exists(
                os.path.join(package.mcrit_dir("Fam", spec.arch),
                             "%s.mcrit" % spec.slug)))

    def test_an_empty_leg_does_not_revert_the_other(self):
        # SysWhispers exactly: its generator emits MASM for x64 only, so the
        # x86 leg builds nothing and ships provenance.x86.json == {}. Taking
        # that as the family's records would delete the x64 leg's.
        x64 = Spec(family="SysWhispers", arch="x64")
        zips = [self.artifact("x64", [x64]),
                self.artifact("x86", [Spec(family="SysWhispers", arch="x86",
                                           with_archive=False, with_export=False,
                                           with_record=False)])]
        changed, problems = self.run_import(zips)
        self.assertEqual(problems, [])
        self.assertEqual([a.slug for a in changed], [x64.slug])
        self.assertEqual(list(_records(os.path.join(self.data, "SysWhispers"))),
                         [x64.slug])

    def test_records_of_other_toolchains_survive_the_merge(self):
        # data/libzlib in miniature: a family can hold reports that predate
        # this tooling. Importing one artefact must not re-write the file down
        # to what this run happened to build.
        family_dir = os.path.join(self.data, "Fam")
        os.makedirs(family_dir)
        with open(os.path.join(family_dir, "provenance.json"), "w",
                  encoding="utf-8") as handle:
            json.dump({"Fam_1.0_msvc12_x64_lib.dll": {"family": "Fam"}}, handle)
        spec = Spec()
        self.run_import([self.artifact("x64", [spec])])
        self.assertEqual(sorted(_records(family_dir)),
                         sorted(["Fam_1.0_msvc12_x64_lib.dll", spec.slug]))

    def test_an_x64_record_inside_the_x86_artifact_is_refused(self):
        # What the workflow's scoping step exists to prevent. Before it, each
        # leg uploaded data/<family>/** from a checkout that already held the
        # other architecture's committed files.
        stray = Spec(arch="x64")
        _, problems = self.run_import([self.artifact("x86", [stray])])
        self.assertTrue(any("arrived in the reference-data-x86 artifact" in p
                            for p in problems), problems)
        self.assertFalse(os.path.exists(os.path.join(self.data, "Fam")))

    def test_a_whole_family_provenance_in_the_artifact_is_refused(self):
        # The upload excludes data/*/provenance.json for the same reason. One
        # that reappears is the per-family file both legs would ship a whole
        # copy of, so it is reported rather than read.
        spec = Spec()
        zip_path = self.artifact("x64", [spec], provenance_name="provenance.json")
        changed, problems = self.run_import([zip_path])
        self.assertEqual(changed, [])
        self.assertTrue(any("per-family, not per-architecture" in p
                            for p in problems), problems)


class VerificationTest(TempCase):
    def test_a_mismatched_sha256_is_refused(self):
        # The digest in provenance is of the analysed binary, which the
        # artefact does not carry - so what is checkable is that the record,
        # the SMDA report and the MCRIT export all name the same one. They
        # stop agreeing when an upload is mixed up or truncated.
        spec = Spec(sha256=SHA_A, report_sha256=SHA_B)
        changed, problems = self.run_import([self.artifact("x64", [spec])])
        self.assertEqual(changed, [])
        self.assertTrue(any("the SMDA report in the archive is of" in p
                            for p in problems), problems)
        self.assertFalse(os.path.exists(os.path.join(self.data, "Fam")))

    def test_an_export_of_a_different_sample_is_refused(self):
        spec = Spec()
        zip_path = self.artifact("x64", [spec])
        # Rewrite the export inside the zip to hold a sample the record does
        # not name, which is the .mcrit half of the same mix-up.
        other = Spec(sha256=SHA_B).export()
        _rewrite(zip_path, "Fam/x64/mcrit/%s.mcrit" % spec.slug,
                 json.dumps(other))
        changed, problems = self.run_import([zip_path])
        self.assertEqual(changed, [])
        self.assertTrue(any("export holds samples" in p for p in problems), problems)

    def test_an_archive_with_no_export_is_refused(self):
        # A .7z whose .mcrit did not survive the upload describes a sample the
        # corpus cannot search. Half an artefact is worse than none.
        spec = Spec(with_export=False)
        changed, problems = self.run_import([self.artifact("x64", [spec])])
        self.assertEqual(changed, [])
        self.assertTrue(any(".mcrit matches 0 staged files" in p
                            for p in problems), problems)
        self.assertFalse(os.path.exists(os.path.join(self.data, "Fam")))

    def test_an_export_with_no_archive_is_refused(self):
        spec = Spec(with_archive=False)
        changed, problems = self.run_import([self.artifact("x64", [spec])])
        self.assertEqual(changed, [])
        self.assertTrue(any(".7z matches 0 staged files" in p
                            for p in problems), problems)

    def test_a_file_no_record_accounts_for_is_refused(self):
        # Both files present, record pruned away: nothing ties the bytes to a
        # build, which is what provenance is for.
        spec = Spec(with_record=False)
        changed, problems = self.run_import([self.artifact("x64", [spec])])
        self.assertEqual(changed, [])
        self.assertEqual(len([p for p in problems
                              if "no provenance record accounts" in p]), 2, problems)

    def test_a_function_count_that_disagrees_is_refused(self):
        spec = Spec(count=12, export_count=11)
        changed, problems = self.run_import([self.artifact("x64", [spec])])
        self.assertEqual(changed, [])
        self.assertTrue(any("the export has 11" in p for p in problems), problems)

    def test_a_report_count_that_disagrees_is_refused(self):
        spec = Spec(count=12, report_count=99)
        changed, problems = self.run_import([self.artifact("x64", [spec])])
        self.assertEqual(changed, [])
        self.assertTrue(any("the SMDA report has 99" in p for p in problems), problems)

    def test_an_export_from_a_foreign_minhash_config_is_refused(self):
        # Such an export imports into MCRIT and then matches nothing, which is
        # worse than not having the family at all.
        spec = Spec(minhash="f" * 64)
        changed, problems = self.run_import([self.artifact("x64", [spec])])
        self.assertEqual(changed, [])
        self.assertTrue(any("minhash config" in p for p in problems), problems)

    def test_a_record_pointing_outside_the_expected_layout_is_refused(self):
        spec = Spec(record_overrides={"smda": "data/Fam/x64/reports/s.7z"})
        changed, problems = self.run_import([self.artifact("x64", [spec])])
        self.assertEqual(changed, [])
        self.assertTrue(any("record's smda path is" in p for p in problems), problems)

    def test_an_archive_holding_more_than_its_report_is_refused(self):
        spec = Spec()
        zip_path = self.artifact("x64", [spec])
        _add(zip_path, "Fam/x64/smda/stray.7z", "not an archive")
        changed, problems = self.run_import([zip_path])
        # The stray is refused for having no record; the real artefact still
        # imports, because one bad file in a run does not condemn the others.
        self.assertEqual([a.slug for a in changed], [spec.slug])
        self.assertTrue(any("stray.7z" in p for p in problems), problems)

    def test_one_bad_artefact_does_not_block_the_good_ones(self):
        good = Spec(family="Good")
        bad = Spec(family="Bad", sha256=SHA_A, report_sha256=SHA_B)
        changed, problems = self.run_import([self.artifact("x64", [good, bad])])
        self.assertEqual([a.slug for a in changed], [good.slug])
        self.assertTrue(problems)
        self.assertTrue(os.path.exists(os.path.join(self.data, "Good")))
        self.assertFalse(os.path.exists(os.path.join(self.data, "Bad")))


class ZipShapeTest(TempCase):
    def test_a_zip_rooted_at_the_family_is_understood(self):
        # What a run that builds all three MSVC families uploads: the longest
        # common prefix is data/, so that is what upload-artifact strips.
        spec = Spec()
        changed, problems = self.run_import([self.artifact("x64", [spec],
                                                           root="family")])
        self.assertEqual(problems, [])
        self.assertEqual([a.slug for a in changed], [spec.slug])

    def test_a_zip_rooted_at_the_architecture_is_understood(self):
        # A run that builds one family strips data/<Family>/ instead, so the
        # family name is nowhere in the tree and only the records still say
        # where the files belong. This is what the planned wave of one-family
        # MSVC builds will produce.
        spec = Spec()
        changed, problems = self.run_import([self.artifact("x64", [spec],
                                                           root="arch")])
        self.assertEqual(problems, [])
        self.assertEqual([a.slug for a in changed], [spec.slug])
        self.assertTrue(os.path.exists(
            os.path.join(package.smda_dir("Fam", "x64"), "%s.7z" % spec.slug)))

    def test_a_zip_that_kept_the_data_prefix_is_understood(self):
        spec = Spec()
        changed, problems = self.run_import([self.artifact("x64", [spec],
                                                           root="data")])
        self.assertEqual(problems, [])
        self.assertEqual([a.slug for a in changed], [spec.slug])

    def test_an_entry_escaping_the_staging_directory_is_refused(self):
        spec = Spec()
        zip_path = self.artifact("x64", [spec])
        _add(zip_path, "../escaped.txt", "x")
        with self.assertRaises(ci.ImportProblem):
            ci.gather([zip_path], self.stage)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "escaped.txt")))


class FailurePathTest(TempCase):
    def test_a_failure_part_way_leaves_committed_data_untouched(self):
        # Two artefacts, both already committed from an earlier run. The
        # second one's .mcrit fails to go into place; the first must be
        # updated and the second must be exactly as it was - not half
        # replaced, and not deleted, which is what an in-place writer that
        # removes before it writes leaves behind.
        first = Spec(family="Aaa")
        second = Spec(family="Zzz")
        first_files = self.commit_existing(first)
        second_files = self.commit_existing(second)
        zip_path = self.artifact("x64", [first, second])

        real_replace = os.replace
        failed = []

        def flaky(src, dst):
            if dst.endswith("%s.mcrit" % second.slug) and not failed:
                failed.append(dst)
                raise OSError("interrupted")
            return real_replace(src, dst)

        with mock.patch("os.replace", flaky):
            changed, problems = self.run_import([zip_path])

        self.assertEqual([a.slug for a in changed], [first.slug])
        self.assertTrue(any("not imported" in p for p in problems), problems)
        self.assertNotEqual(_read(first_files[0]), b"old-7z")
        self.assertEqual(_read(second_files[0]), b"old-7z")
        self.assertEqual(_read(second_files[1]), b"old-mcrit")
        self.assertEqual(self._strays(), [])

    def test_a_verification_failure_writes_nothing_at_all(self):
        spec = Spec()
        smda, mcrit = self.commit_existing(spec)
        broken = Spec(slug=spec.slug, sha256=SHA_A, report_sha256=SHA_B)
        changed, problems = self.run_import([self.artifact("x64", [broken])])
        self.assertEqual(changed, [])
        self.assertTrue(problems)
        self.assertEqual(_read(smda), b"old-7z")
        self.assertEqual(_read(mcrit), b"old-mcrit")

    def test_a_dry_run_writes_nothing(self):
        spec = Spec()
        smda, mcrit = self.commit_existing(spec)
        changed, problems = self.run_import([self.artifact("x64", [spec])],
                                            dry_run=True)
        self.assertEqual([a.slug for a in changed], [spec.slug])
        self.assertEqual(problems, [])
        self.assertEqual(_read(smda), b"old-7z")
        self.assertEqual(_read(mcrit), b"old-mcrit")
        self.assertFalse(os.path.exists(
            os.path.join(self.data, "Fam", "provenance.json")))

    def test_the_record_is_written_only_after_both_files_land(self):
        # A record pointing at bytes that are not there cannot be repaired by
        # re-running, so the order is: pair first, record second.
        spec = Spec()
        order = []
        real_commit = package.commit_artifacts
        real_provenance = package.write_provenance

        def note_commit(*args, **kwargs):
            order.append("files")
            return real_commit(*args, **kwargs)

        def note_provenance(*args, **kwargs):
            order.append("record")
            return real_provenance(*args, **kwargs)

        with mock.patch.object(package, "commit_artifacts", note_commit), \
                mock.patch.object(package, "write_provenance", note_provenance):
            self.run_import([self.artifact("x64", [spec])])
        self.assertEqual(order, ["files", "record"])

    def _strays(self):
        expected = set()
        for dirpath, _, names in os.walk(self.data):
            for name in names:
                if name.endswith((".7z", ".mcrit", "provenance.json")):
                    continue
                expected.add(os.path.join(dirpath, name))
        return sorted(expected)


class MainTest(TempCase):
    """The driver, so the command's own exit codes are covered too."""

    def _main(self, *extra):
        argv = ["import_ci_artifacts.py", "--stage-dir", self.stage] + list(extra)
        out = io.StringIO()
        with mock.patch.object(sys, "argv", argv):
            with contextlib.redirect_stdout(out):
                code = ci.main()
        return code, out.getvalue()

    def test_a_clean_import_exits_zero_and_names_what_changed(self):
        spec = Spec()
        code, output = self._main("--zip", self.artifact("x64", [spec]))
        self.assertEqual(code, 0, output)
        self.assertIn("imported Fam/x64 %s" % spec.slug, output)
        self.assertIn("families touched: Fam", output)

    def test_a_refused_artefact_exits_non_zero(self):
        spec = Spec(sha256=SHA_A, report_sha256=SHA_B)
        code, output = self._main("--zip", self.artifact("x64", [spec]))
        self.assertEqual(code, 1, output)
        self.assertIn("REFUSED", output)

    def test_zip_and_run_id_together_are_rejected(self):
        code, output = self._main("--zip", self.artifact("x64", [Spec()]),
                                  "--run-id", "1")
        self.assertEqual(code, 1, output)
        self.assertIn("takes the place of", output)

    def test_an_artifact_with_nothing_in_it_exits_non_zero(self):
        # A run whose legs all built nothing is not a successful import; it
        # means the workflow changed or the wrong run was named.
        empty = Spec(with_archive=False, with_export=False, with_record=False)
        code, output = self._main("--zip", self.artifact("x64", [empty]))
        self.assertEqual(code, 1, output)
        self.assertIn("nothing to import", output)


def _rewrite(zip_path, name, body):
    """Replace one member of a zip, leaving the rest as they were."""
    keep = []
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            if info.filename != name:
                keep.append((info.filename, archive.read(info.filename)))
    with zipfile.ZipFile(zip_path, "w") as archive:
        for filename, data in keep:
            archive.writestr(filename, data)
        archive.writestr(name, body)


def _add(zip_path, name, body):
    with zipfile.ZipFile(zip_path, "a") as archive:
        archive.writestr(name, body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
