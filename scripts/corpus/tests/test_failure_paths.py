"""Failure-path tests for the writers that replace committed files.

Every test here runs against a temporary tree with config.DATA_DIR patched
to point at it, so none of them can touch data/. What they cover is the
behaviour that is invisible when everything works: what is left on disk
when a replace is interrupted, when 7z fails, when an export is missing or
describes a different sample. That class of defect had already cost this
repository an archive, and it is not caught by running the pipeline.

    python -m unittest discover -s scripts/corpus/tests
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

# scripts/, so "corpus" imports the same way build_corpus.py imports it.
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from corpus import config, package, reprocess


def _read(path):
    with open(path, "rb") as handle:
        return handle.read()


def _text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class TempCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="corpus-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.data = os.path.join(self.tmp, "data")
        os.makedirs(self.data)
        patch = mock.patch.object(config, "DATA_DIR", self.data)
        patch.start()
        self.addCleanup(patch.stop)

    def write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path


class CommitArtifactsTest(TempCase):
    def _existing_pair(self):
        smda = self.write(os.path.join(package.smda_dir("Fam", "x64"), "s.7z"), "old-7z")
        mcrit = self.write(os.path.join(package.mcrit_dir("Fam", "x64"), "s.mcrit"), "old-mcrit")
        return smda, mcrit

    def _staged_pair(self):
        stage = os.path.join(self.tmp, "build")
        return (self.write(os.path.join(stage, "s.7z"), "new-7z"),
                self.write(os.path.join(stage, "s.mcrit"), "new-mcrit"))

    def test_commits_both(self):
        old_smda, old_mcrit = self._existing_pair()
        archive, export = self._staged_pair()
        package.commit_artifacts("Fam", "x64", "s", archive, export)
        self.assertEqual(_text(old_smda), "new-7z")
        self.assertEqual(_text(old_mcrit), "new-mcrit")
        self.assertFalse(os.path.exists(archive))
        self.assertFalse(os.path.exists(export))
        self.assertEqual(self._strays(), [])

    def test_failure_on_second_move_keeps_both_originals(self):
        old_smda, old_mcrit = self._existing_pair()
        archive, export = self._staged_pair()
        real_replace = os.replace
        failed = []

        def flaky(src, dst):
            # Fail the .mcrit going into place - the second of the two
            # commits, which is exactly the case the old code lost both
            # committed files to. Once only, so the put-back still works.
            if dst.endswith(".mcrit") and not failed:
                failed.append(dst)
                raise OSError("interrupted")
            return real_replace(src, dst)

        with mock.patch("os.replace", flaky):
            with self.assertRaises(OSError):
                package.commit_artifacts("Fam", "x64", "s", archive, export)
        self.assertEqual(_text(old_smda), "old-7z")
        self.assertEqual(_text(old_mcrit), "old-mcrit")
        self.assertEqual(self._strays(), [])

    def test_failure_with_no_previous_pair_leaves_nothing_behind(self):
        archive, export = self._staged_pair()
        real_replace = os.replace
        failed = []

        def flaky(src, dst):
            if dst.endswith(".mcrit") and not failed:
                failed.append(dst)
                raise OSError("interrupted")
            return real_replace(src, dst)

        with mock.patch("os.replace", flaky):
            with self.assertRaises(OSError):
                package.commit_artifacts("Fam", "x64", "s", archive, export)
        self.assertFalse(os.path.exists(
            os.path.join(package.smda_dir("Fam", "x64"), "s.7z")))
        self.assertFalse(os.path.exists(
            os.path.join(package.mcrit_dir("Fam", "x64"), "s.mcrit")))
        self.assertEqual(self._strays(), [])

    def test_copy_failure_leaves_committed_pair_untouched(self):
        old_smda, old_mcrit = self._existing_pair()
        archive, export = self._staged_pair()
        with mock.patch("shutil.copyfile", side_effect=OSError("no space")):
            with self.assertRaises(OSError):
                package.commit_artifacts("Fam", "x64", "s", archive, export)
        self.assertEqual(_text(old_smda), "old-7z")
        self.assertEqual(_text(old_mcrit), "old-mcrit")
        self.assertEqual(self._strays(), [])

    def _strays(self):
        return sorted(name
                      for _, _, names in os.walk(self.data)
                      for name in names
                      if name not in ("s.7z", "s.mcrit"))


class AtomicWriteTest(TempCase):
    def test_interrupted_write_keeps_the_original(self):
        path = self.write(os.path.join(self.data, "provenance.json"), "original\n")
        with mock.patch("os.replace", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                package.atomic_write_text(path, "replacement\n")
        self.assertEqual(_text(path), "original\n")
        self.assertEqual(os.listdir(self.data), ["provenance.json"])

    def test_replaces_on_success(self):
        path = self.write(os.path.join(self.data, "provenance.json"), "original\n")
        package.atomic_write_text(path, "replacement\n")
        self.assertEqual(_text(path), "replacement\n")
        self.assertEqual(os.listdir(self.data), ["provenance.json"])

    def test_write_provenance_survives_an_interrupted_rewrite(self):
        first = package.write_provenance("Fam", {"a": {"license": "MIT"}})
        with mock.patch("os.replace", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                package.write_provenance("Fam", {"b": {"license": "MIT"}})
        self.assertEqual(sorted(json.load(open(first))), ["a"])
        self.assertEqual(os.listdir(os.path.dirname(first)), ["provenance.json"])


class WriteArchiveTest(TempCase):
    def _archive(self):
        directory = os.path.join(self.data, "Fam", "x64", "smda")
        os.makedirs(directory)
        archive = os.path.join(directory, "s.7z")
        member = os.path.join(self.tmp, "s.smda")
        self.write(member, json.dumps({"statistics": {"n": 1}}))
        subprocess.run(list(package.ARCHIVE_COMMAND) + [archive, member],
                       check=True, stdout=subprocess.DEVNULL)
        return archive

    def test_7z_failure_keeps_the_committed_archive(self):
        archive = self._archive()
        before = _read(archive)
        with mock.patch("subprocess.run",
                        side_effect=subprocess.CalledProcessError(2, "7z")):
            with self.assertRaises(subprocess.CalledProcessError):
                reprocess._write_archive(archive, "s.smda", {"statistics": {"n": 2}})
        self.assertEqual(_read(archive), before)
        self.assertEqual(os.listdir(os.path.dirname(archive)), ["s.7z"])

    def test_interrupt_between_compress_and_replace_keeps_the_archive(self):
        archive = self._archive()
        before = _read(archive)
        with mock.patch("os.replace", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                reprocess._write_archive(archive, "s.smda", {"statistics": {"n": 2}})
        self.assertEqual(_read(archive), before)
        self.assertEqual(os.listdir(os.path.dirname(archive)), ["s.7z"])

    def test_replacement_is_byte_identical_to_a_freshly_staged_archive(self):
        archive = self._archive()
        payload = {"statistics": {"n": 2}}
        reprocess._write_archive(archive, "s.smda", payload)
        elsewhere = os.path.join(self.tmp, "elsewhere")
        os.makedirs(elsewhere)
        member = os.path.join(elsewhere, "s.smda")
        self.write(member, json.dumps(payload, indent=1, sort_keys=True))
        reference = os.path.join(elsewhere, "ref.7z")
        subprocess.run(list(package.ARCHIVE_COMMAND) + [reference, member],
                       check=True, stdout=subprocess.DEVNULL)
        self.assertEqual(_read(archive), _read(reference))


class CorrectedExportTest(TempCase):
    def _export(self, entries):
        return self.write(os.path.join(self.data, "s.mcrit"),
                          json.dumps({"sample_entries": entries}))

    def test_missing_export_raises(self):
        with self.assertRaises(reprocess.ReprocessError):
            reprocess._corrected_export(os.path.join(self.data, "gone.mcrit"),
                                        "aa", {"num_functions": 1}, 1.0)

    def test_unknown_sha256_raises(self):
        path = self._export({"bb": {"sha256": "bb", "statistics": {}, "binweight": 1.0}})
        with self.assertRaises(reprocess.ReprocessError):
            reprocess._corrected_export(path, "aa", {"num_functions": 1}, 1.0)

    def test_only_the_matching_entry_is_touched(self):
        path = self._export({
            "aa": {"sha256": "aa", "statistics": {"num_functions": 9}, "binweight": 9.0},
            "bb": {"sha256": "bb", "statistics": {"num_functions": 5}, "binweight": 5.0},
        })
        corrected = reprocess._corrected_export(path, "aa", {"num_functions": 1}, 1.0)
        self.assertEqual(corrected["sample_entries"]["aa"]["statistics"],
                         {"num_functions": 1})
        self.assertEqual(corrected["sample_entries"]["aa"]["binweight"], 1.0)
        self.assertEqual(corrected["sample_entries"]["bb"]["statistics"],
                         {"num_functions": 5})
        self.assertEqual(corrected["sample_entries"]["bb"]["binweight"], 5.0)

    def test_agreeing_export_is_not_rewritten(self):
        path = self._export({"aa": {"sha256": "aa", "statistics": {"num_functions": 1},
                                    "binweight": 1.0}})
        self.assertIsNone(
            reprocess._corrected_export(path, "aa", {"num_functions": 1}, 1.0))


class ReprocessDriverTest(TempCase):
    """The archive must not be touched when its .mcrit cannot follow."""

    def _corpus(self, with_export=True, sha256="aa"):
        family_dir = os.path.join(self.data, "Fam")
        smda = os.path.join(family_dir, "x64", "smda")
        os.makedirs(smda)
        archive = os.path.join(smda, "s.7z")
        member = os.path.join(self.tmp, "s.smda")
        self.write(member, "{}")
        subprocess.run(list(package.ARCHIVE_COMMAND) + [archive, member],
                       check=True, stdout=subprocess.DEVNULL)
        self.write(os.path.join(family_dir, "provenance.json"),
                   json.dumps({"s": {"removed_runtime_functions": ["x"]}}))
        if with_export:
            self.write(os.path.join(family_dir, "x64", "mcrit", "s.mcrit"),
                       json.dumps({"sample_entries": {sha256: {"sha256": sha256}}}))
        return archive

    def _patch_report(self, sha256="aa"):
        report = {"sha256": sha256, "statistics": {"num_functions": 0},
                  "metadata": {"binweight": 0.0}}
        return (mock.patch.object(reprocess, "_read_archive",
                                  return_value=("s.smda", dict(report))),
                mock.patch.object(reprocess, "_recomputed",
                                  return_value=({"num_functions": 7}, 7.0)))

    def test_missing_export_is_a_failure_and_the_archive_is_untouched(self):
        archive = self._corpus(with_export=False)
        before = _read(archive)
        read, recomputed = self._patch_report()
        with read, recomputed:
            changes, failures = reprocess.reprocess(["Fam"])
        self.assertEqual(changes, [])
        self.assertEqual(len(failures), 1)
        self.assertEqual(_read(archive), before)

    def test_export_without_this_sample_is_a_failure(self):
        archive = self._corpus(sha256="bb")
        before = _read(archive)
        read, recomputed = self._patch_report(sha256="aa")
        with read, recomputed:
            changes, failures = reprocess.reprocess(["Fam"])
        self.assertEqual(changes, [])
        self.assertEqual(len(failures), 1)
        self.assertEqual(_read(archive), before)

    def test_both_files_are_corrected_together(self):
        archive = self._corpus()
        read, recomputed = self._patch_report()
        with read, recomputed:
            changes, failures = reprocess.reprocess(["Fam"])
        self.assertEqual(failures, [])
        self.assertEqual(len(changes), 1)
        self.assertEqual(dict(changes[0][1]),
                         {"num_functions": (0, 7), "binweight": (0.0, 7.0)})
        _, report = reprocess._read_archive(archive)
        self.assertEqual(report["statistics"], {"num_functions": 7})
        self.assertEqual(report["metadata"]["binweight"], 7.0)
        with open(os.path.join(self.data, "Fam", "x64", "mcrit",
                               "s.mcrit"), encoding="utf-8") as handle:
            export = json.load(handle)
        self.assertEqual(export["sample_entries"]["aa"]["statistics"],
                         {"num_functions": 7})
        self.assertEqual(export["sample_entries"]["aa"]["binweight"], 7.0)


class SlugTest(unittest.TestCase):
    def test_slug_uses_the_artifact_family(self):
        from corpus.recipe import Artifact, Recipe, Source

        recipe = Recipe(family="Host", version="1.0", source=Source(),
                        build=[], artifacts=[], toolchains=["mingw13_x64"])
        vendored = Artifact(path="lib/x.dll", component="x.dll", family="Vendored")
        self.assertTrue(recipe.slug("mingw13_x64", vendored).startswith("Vendored_1.0_"))
        own = Artifact(path="x.dll", component="x.dll")
        self.assertTrue(recipe.slug("mingw13_x64", own).startswith("Host_1.0_"))

    def test_hostile_characters_still_raise(self):
        from corpus.recipe import Artifact, Recipe, Source

        recipe = Recipe(family="Host", version="1.0 (rc)", source=Source(),
                        build=[], artifacts=[], toolchains=["mingw13_x64"])
        with self.assertRaises(ValueError):
            recipe.slug("mingw13_x64", Artifact(path="x.dll", component="x.dll"))


class PipelineHandlerTest(unittest.TestCase):
    def test_slug_valueerror_is_caught_per_artefact(self):
        import inspect

        from corpus import pipeline

        source = inspect.getsource(pipeline.run_recipe)
        self.assertIn("except (RuntimeError, ValueError, OSError,", source)


class UnrecordedArtifactsTest(TempCase):
    def _family(self, slugs, recorded):
        family = os.path.join(self.data, "Fam")
        for slug in slugs:
            arch = "x64" if "_x64_" in slug else "x86"
            self.write(os.path.join(family, arch, "smda", slug + ".7z"), "x")
            self.write(os.path.join(family, arch, "mcrit", slug + ".mcrit"), "x")
        records = {}
        for slug in recorded:
            arch = "x64" if "_x64_" in slug else "x86"
            records[slug] = {"smda": "data/Fam/%s/smda/%s.7z" % (arch, slug),
                             "mcrit": "data/Fam/%s/mcrit/%s.mcrit" % (arch, slug)}
        self.write(os.path.join(family, "provenance.json"), json.dumps(records))
        return family

    def test_dropped_architecture_records_are_reported(self):
        from corpus import validate

        self._family(["Fam_1.0_mingw13_x64_lib.dll", "Fam_1.0_mingw13_x86_lib.dll"],
                     ["Fam_1.0_mingw13_x64_lib.dll"])
        with mock.patch.object(config, "REPO_ROOT", self.tmp):
            problems = validate.find_unrecorded_artifacts(self.data)
        self.assertEqual(len(problems), 2, problems)
        self.assertTrue(all("_x86_" in p for p in problems), problems)

    def test_artefacts_from_another_toolchain_are_left_alone(self):
        from corpus import validate

        # data/libzlib in miniature: reports that predate this tooling next to
        # ones it generated. The old ones record nothing and cannot.
        self._family(["Fam_1.0_mingw13_x64_lib.dll", "Fam_1.0_msvc12_x64_lib.dll"],
                     ["Fam_1.0_mingw13_x64_lib.dll"])
        with mock.patch.object(config, "REPO_ROOT", self.tmp):
            self.assertEqual(validate.find_unrecorded_artifacts(self.data), [])

    def test_family_without_provenance_is_left_alone(self):
        from corpus import validate

        with mock.patch.object(config, "REPO_ROOT", self.tmp):
            self.write(os.path.join(self.data, "Old", "x64", "smda",
                                    "Old_1.0_mingw13_x64_a.7z"), "x")
            self.assertEqual(validate.find_unrecorded_artifacts(self.data), [])


class CrossFamilyFloorTest(TempCase):
    """The instruction floor on the deep check.

    Without it the check reports hundreds of hits that are not leakage - a
    thunk that loads an import and jumps has one shape in every project that
    calls that import - and a gate nobody can act on is not a gate.
    """

    def _corpus(self, functions):
        """Write one .mcrit per family, uncompressed so no mcrit import is needed.

        functions maps family -> [(pichash, num_instructions), ...].
        """
        for family, entries in functions.items():
            export = {
                "content": {"is_compressed": False},
                "sample_entries": {family: {"family": family}},
                "function_entries": {
                    family: {
                        str(index): {"pichash": pichash,
                                     "num_instructions": size}
                        for index, (pichash, size) in enumerate(entries)
                    }
                },
            }
            self.write(os.path.join(self.data, family, "x64", "mcrit",
                                    "%s.mcrit" % family), json.dumps(export))

    def test_short_shared_functions_are_below_the_floor(self):
        from corpus import validate

        self._corpus({"A": [("deadbeef", 3)],
                      "B": [("deadbeef", 3)],
                      "C": [("deadbeef", 3)]})
        self.assertEqual(validate.find_cross_family_functions(self.data), {})

    def test_a_long_shared_function_is_reported_with_its_size(self):
        from corpus import validate

        self._corpus({"A": [("deadbeef", 40)],
                      "B": [("deadbeef", 40)],
                      "C": [("deadbeef", 40)]})
        self.assertEqual(validate.find_cross_family_functions(self.data),
                         {"deadbeef": (["A", "B", "C"], 40)})

    def test_zero_counts_everything_for_investigating_by_hand(self):
        from corpus import validate

        self._corpus({"A": [("deadbeef", 3)],
                      "B": [("deadbeef", 3)],
                      "C": [("deadbeef", 3)]})
        found = validate.find_cross_family_functions(self.data,
                                                     min_instructions=0)
        self.assertEqual(found, {"deadbeef": (["A", "B", "C"], 3)})

    def test_two_families_are_below_the_family_threshold(self):
        from corpus import validate

        self._corpus({"A": [("deadbeef", 40)], "B": [("deadbeef", 40)]})
        self.assertEqual(validate.find_cross_family_functions(self.data), {})

    def test_the_floor_is_applied_before_families_are_counted(self):
        """A hash long enough in one family and short in two is not three."""
        from corpus import validate

        self._corpus({"A": [("deadbeef", 40)],
                      "B": [("deadbeef", 2)],
                      "C": [("deadbeef", 2)]})
        self.assertEqual(validate.find_cross_family_functions(self.data), {})


if __name__ == "__main__":
    unittest.main(verbosity=2)


class RefilterTest(TempCase):
    """The refilter has to be all-or-nothing across three files.

    An artefact is described by its .7z, its .mcrit and a provenance record,
    and one of them corrected without the others is worse than none: the
    corpus would then disagree with itself about which functions a sample
    has, which is the defect the whole in-place-correction class exists to
    avoid. These check the abandon paths rather than the happy one - the
    happy one is what a pipeline run already covers.
    """

    def setUp(self):
        super().setUp()
        patch = mock.patch.object(config, "REPO_ROOT", self.tmp)
        patch.start()
        self.addCleanup(patch.stop)

    def _artefact(self, removed=("__old",)):
        """A committed .7z / .mcrit / provenance trio for one x86 artefact."""
        slug = "Fam_1.0_mingw13_x86_f.dll"
        smda = os.path.join("data", "Fam", "x86", "smda", "%s.7z" % slug)
        mcrit = os.path.join("data", "Fam", "x86", "mcrit", "%s.mcrit" % slug)
        archive = os.path.join(self.tmp, smda)
        os.makedirs(os.path.dirname(archive), exist_ok=True)
        member = self.write(os.path.join(self.tmp, "r.smda"), json.dumps(
            {"xcfg": {"4096": {}, "8192": {}}, "statistics": {}, "sha256": "aa"}))
        subprocess.run(list(package.ARCHIVE_COMMAND) + [archive, member],
                       check=True, stdout=subprocess.DEVNULL)
        self.write(os.path.join(self.tmp, mcrit), json.dumps(
            {"sample_entries": {"aa": {}}}))
        self.write(os.path.join(self.data, "Fam", "provenance.json"),
                   json.dumps({slug: {
                       "toolchain": "mingw13_x86", "smda": smda, "mcrit": mcrit,
                       "num_functions": 2,
                       "removed_runtime_functions": list(removed)}}))
        return slug, archive, os.path.join(self.tmp, mcrit)

    def test_a_family_whose_recipe_disables_the_filter_is_skipped(self):
        from corpus import refilter

        self._artefact()
        recipe = mock.Mock(family="Fam", drop_crt_glue=False)
        with mock.patch("corpus.recipes.all_recipes", return_value={"r": recipe}):
            self.assertEqual(list(refilter._artifacts()), [])

    def test_a_family_with_no_provenance_is_not_touched(self):
        from corpus import refilter

        os.makedirs(os.path.join(self.data, "Ida", "x86", "smda"))
        with mock.patch("corpus.recipes.all_recipes", return_value={}):
            self.assertEqual([f for f, _, _, _ in refilter._artifacts()], [])

    def test_a_blob_has_no_toolchain_and_is_not_filtered(self):
        from corpus import refilter

        self.write(os.path.join(self.data, "Fam", "provenance.json"),
                   json.dumps({"s": {"toolchain": None, "smda": "x"}}))
        with mock.patch("corpus.recipes.all_recipes", return_value={}):
            self.assertEqual(list(refilter._artifacts()), [])

    def test_a_missing_export_leaves_the_archive_alone(self):
        from corpus import refilter

        slug, archive, mcrit = self._artefact()
        os.remove(mcrit)
        before = _read(archive)
        report = mock.Mock(xcfg={4096: mock.Mock(function_name="___divdi3")})
        with mock.patch("corpus.recipes.all_recipes", return_value={}), \
             mock.patch("corpus.refilter.is_glue", return_value=True), \
             mock.patch("smda.common.SmdaReport.SmdaReport.fromDict",
                        return_value=report):
            changes, failures = refilter.refilter()
        self.assertEqual(changes, [])
        self.assertEqual(len(failures), 1)
        self.assertIn("no .mcrit", failures[0])
        self.assertEqual(_read(archive), before)

    def test_a_failing_export_leaves_both_committed_files_alone(self):
        from corpus import refilter

        slug, archive, mcrit = self._artefact()
        before_archive, before_mcrit = _read(archive), _read(mcrit)
        report = mock.Mock(xcfg={4096: mock.Mock(function_name="___divdi3")})
        with mock.patch("corpus.recipes.all_recipes", return_value={}), \
             mock.patch("corpus.refilter.is_glue", return_value=True), \
             mock.patch("smda.common.SmdaReport.SmdaReport.fromDict",
                        return_value=report), \
             mock.patch("corpus.refilter._corrected_archive",
                        return_value=["___divdi3"]), \
             mock.patch("corpus.refilter._write_export",
                        side_effect=OSError("disk full")):
            changes, failures = refilter.refilter()
        self.assertEqual(changes, [])
        self.assertIn("archive untouched", failures[0])
        self.assertEqual(_read(archive), before_archive)
        self.assertEqual(_read(mcrit), before_mcrit)

    def test_an_offset_missing_from_the_stored_report_is_refused(self):
        from corpus import refilter

        report_dict = {"xcfg": {"4096": {}}}
        report = mock.Mock(xcfg={8192: mock.Mock(function_name="___divdi3")})
        with self.assertRaises(refilter.RefilterError):
            refilter._corrected_archive(report_dict, report, [8192])
        # The stored report is not half-edited by the attempt.
        self.assertEqual(report_dict["xcfg"], {"4096": {}})

    def test_dry_run_writes_nothing(self):
        from corpus import refilter

        slug, archive, mcrit = self._artefact()
        before_archive, before_mcrit = _read(archive), _read(mcrit)
        provenance = os.path.join(self.data, "Fam", "provenance.json")
        before_provenance = _read(provenance)
        report = mock.Mock(xcfg={4096: mock.Mock(function_name="___divdi3")})
        with mock.patch("corpus.recipes.all_recipes", return_value={}), \
             mock.patch("corpus.refilter.is_glue", return_value=True), \
             mock.patch("smda.common.SmdaReport.SmdaReport.fromDict",
                        return_value=report), \
             mock.patch("corpus.refilter._corrected_archive",
                        return_value=["___divdi3"]):
            changes, failures = refilter.refilter(dry_run=True)
        self.assertEqual(changes, [(slug, ["___divdi3"])])
        self.assertEqual(failures, [])
        self.assertEqual(_read(archive), before_archive)
        self.assertEqual(_read(mcrit), before_mcrit)
        self.assertEqual(_read(provenance), before_provenance)

    def test_nothing_to_drop_is_not_a_write(self):
        from corpus import refilter

        slug, archive, mcrit = self._artefact()
        before = _read(archive)
        report = mock.Mock(xcfg={4096: mock.Mock(function_name="f")})
        with mock.patch("corpus.recipes.all_recipes", return_value={}), \
             mock.patch("corpus.refilter.is_glue", return_value=False), \
             mock.patch("smda.common.SmdaReport.SmdaReport.fromDict",
                        return_value=report):
            changes, failures = refilter.refilter()
        self.assertEqual((changes, failures), ([], []))
        self.assertEqual(_read(archive), before)

    def test_newly_removed_names_are_merged_into_the_recorded_ones(self):
        """The record lists what the filter has ever taken, not the last pass."""
        from corpus import refilter

        slug, archive, mcrit = self._artefact(removed=("__scrt", "__chkstk"))
        report = mock.Mock(xcfg={4096: mock.Mock(function_name="___divdi3")},
                           num_functions=1)
        with mock.patch("corpus.recipes.all_recipes", return_value={}), \
             mock.patch("corpus.refilter.is_glue", return_value=True), \
             mock.patch("smda.common.SmdaReport.SmdaReport.fromDict",
                        return_value=report), \
             mock.patch("corpus.refilter._corrected_archive",
                        return_value=["___divdi3"]), \
             mock.patch("corpus.refilter._write_export"), \
             mock.patch("corpus.refilter._write_archive"):
            changes, failures = refilter.refilter()
        self.assertEqual(failures, [])
        with open(os.path.join(self.data, "Fam", "provenance.json"),
                  encoding="utf-8") as handle:
            entry = json.load(handle)[slug]
        self.assertEqual(entry["removed_runtime_functions"],
                         ["___divdi3", "__chkstk", "__scrt"])
        self.assertEqual(entry["num_functions"], 1)
