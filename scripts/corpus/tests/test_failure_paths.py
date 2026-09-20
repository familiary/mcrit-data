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
        self.assertEqual(sorted(json.loads(_text(first))), ["a"])
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
            changes, failures, _ = refilter.refilter()
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
            changes, failures, _ = refilter.refilter()
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
            changes, failures, _ = refilter.refilter(dry_run=True)
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
            changes, failures, _ = refilter.refilter()
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
            changes, failures, _ = refilter.refilter()
        self.assertEqual(failures, [])
        with open(os.path.join(self.data, "Fam", "provenance.json"),
                  encoding="utf-8") as handle:
            entry = json.load(handle)[slug]
        self.assertEqual(entry["removed_runtime_functions"],
                         ["___divdi3", "__chkstk", "__scrt"])
        self.assertEqual(entry["num_functions"], 1)


class CorrectedArchiveTest(TempCase):
    """The removal itself, which the failure-path tests only ever mocked."""

    def _pair(self):
        """A stored dict and a parsed report that agree, with three functions."""
        from smda.common.SmdaReport import SmdaReport

        report_dict = {
            "architecture": "intel", "base_addr": 0, "binary_size": 64,
            "bitness": 32, "code_areas": [], "code_sections": [],
            "confidence_threshold": 0.0, "disassembly_errors": {},
            "execution_time": 0.0, "identified_alignment": 0,
            "message": "", "metadata": {"family": "Fam", "version": "1.0",
                                        "component": "c", "is_library": True,
                                        "filename": "f.dll", "binweight": 0,
                                        # A real report carries this populated;
                                        # left unset it serialises as None the
                                        # first time and {} thereafter, so the
                                        # fixture would not be a fixed point.
                                        "language": {"c/asm": 0.1}},
            "oep": 0, "sha256": "aa", "md5": "bb", "sha1": "cc",
            "smda_version": "4.8.0", "status": "ok", "timestamp": "2026-01-01T00-00-00",
            "statistics": {}, "xcfg": {}, "xdata_refs_from": {},
            "xdata_refs_to": {}, "xheader": "4d5a", "xmetadata": {},
            "pe_header_hash": "",
        }
        # Field shapes taken from a committed report rather than invented:
        # blocks are {address: [[address, bytes, mnemonic, operands], ...]},
        # and fromDict rejects anything else.
        for offset, name in ((4096, "keep"), (8192, "___divdi3"), (12288, "___moddi3")):
            report_dict["xcfg"][str(offset)] = {
                "offset": offset, "apirefs": {}, "blockrefs": {},
                "inrefs": [], "outrefs": {}, "stringrefs": {},
                "is_exported": False,
                "metadata": {"function_name": name, "is_library": False,
                             "binweight": 1.0, "confidence": 1.0,
                             "nesting_depth": 0, "characteristics": "",
                             "pic_hash": offset,
                             "strongly_connected_components": [],
                             "tfidf": None},
                "blocks": {str(offset): [[offset, "c3", "ret", ""]]},
            }
        # What a committed .7z holds: SMDA's own serialisation, through
        # JSON, so every field toDict() emits is present and every key is a
        # string. Hand-building the dict omitted fields and made comparisons
        # against the pipeline fail for reasons unrelated to the filter.
        stored = json.loads(json.dumps(SmdaReport.fromDict(report_dict).toDict()))
        return stored, SmdaReport.fromDict(stored)

    def test_both_structures_lose_exactly_the_named_functions(self):
        from corpus import refilter

        report_dict, report = self._pair()
        removed = refilter._corrected_archive(report_dict, report, [8192, 12288])
        self.assertEqual(removed, ["___divdi3", "___moddi3"])
        self.assertEqual(sorted(report_dict["xcfg"]), ["4096"])
        self.assertEqual(sorted(report.xcfg), [4096])
        self.assertEqual(report.num_functions, 1)

    def test_the_stored_statistics_are_rewritten_to_match_what_survives(self):
        from corpus import refilter

        report_dict, report = self._pair()
        refilter._corrected_archive(report_dict, report, [8192, 12288])
        self.assertEqual(report_dict["statistics"], report.statistics.toDict())
        self.assertEqual(report_dict["statistics"]["num_functions"], 1)
        self.assertEqual(report_dict["metadata"]["binweight"], report.binweight)

    def test_it_writes_what_the_pipelines_own_filter_would_write(self):
        """The whole design rests on this: in place must equal a rebuild.

        So it is checked the way the pipeline actually produces an archive -
        smdaify._drop_crt_glue over the report, then the serialisation
        package.stage_smda_archive performs - rather than by recomputing the
        statistics twice and comparing them to themselves, which is what an
        earlier version of this test did and could not fail.
        """
        from corpus import refilter, smdaify

        report_dict, report = self._pair()
        refilter._corrected_archive(report_dict, report, [8192, 12288])

        # What the pipeline would do to the same report: is_glue picks the
        # same two functions, and the archive is written from toDict().
        _, rebuilt = self._pair()
        glue = {"___divdi3", "___moddi3"}
        with mock.patch("corpus.smdaify.is_glue",
                        side_effect=lambda f, _: f.function_name in glue):
            removed = smdaify._drop_crt_glue(rebuilt, "mingw13_x86")
        self.assertEqual(sorted(removed), ["___divdi3", "___moddi3"])

        mine = json.dumps(report_dict, indent=1, sort_keys=True)
        theirs = json.dumps(rebuilt.toDict(), indent=1, sort_keys=True)
        # Equal as data. This is the property the module depends on.
        self.assertEqual(json.loads(mine), json.loads(theirs))
        self.assertEqual(report_dict["statistics"],
                         rebuilt.statistics.toDict())
        self.assertEqual(report_dict["metadata"]["binweight"],
                         rebuilt.binweight)

    def test_the_two_serialisations_can_differ_in_key_order_only(self):
        """Documents the one way refilter's archive is not byte-identical.

        toDict() hands back integer xcfg keys, so sort_keys orders them
        numerically; the stored dict's keys are the strings JSON returned, and
        the same call orders them lexicographically. The docstring used to
        claim byte-identity, which held only where every offset had the same
        number of digits. Pinned here so the claim cannot drift back.
        """
        from corpus import refilter, smdaify

        report_dict, report = self._pair()
        # 4096 and 12288 differ in width, which is what exposes the ordering.
        refilter._corrected_archive(report_dict, report, [8192])
        _, rebuilt = self._pair()
        glue = {"___divdi3"}
        with mock.patch("corpus.smdaify.is_glue",
                        side_effect=lambda f, _: f.function_name in glue):
            smdaify._drop_crt_glue(rebuilt, "mingw13_x86")

        self.assertEqual(list(report_dict["xcfg"]), ["4096", "12288"])
        self.assertEqual([str(k) for k in rebuilt.toDict()["xcfg"]],
                         ["4096", "12288"])
        # Same content, and any byte difference is confined to ordering.
        self.assertEqual(json.loads(json.dumps(report_dict, sort_keys=True)),
                         json.loads(json.dumps(rebuilt.toDict(), sort_keys=True)))

    def test_a_missing_offset_leaves_both_structures_untouched(self):
        """The half-edit the earlier single-offset test could not see."""
        from corpus import refilter

        report_dict, report = self._pair()
        del report_dict["xcfg"]["12288"]
        with self.assertRaises(refilter.RefilterError):
            # 8192 is present and would be deleted first by a loop that
            # checked as it went; 12288 is the one that is missing.
            refilter._corrected_archive(report_dict, report, [8192, 12288])
        self.assertEqual(sorted(report_dict["xcfg"]), ["4096", "8192"])
        self.assertEqual(sorted(report.xcfg), [4096, 8192, 12288])


class MinhashGuardTest(TempCase):
    """A re-export that lost its minhashes must never replace a good one."""

    def _export(self, hashed, total):
        entries = {str(i): {"minhash": "ff" if i < hashed else ""}
                   for i in range(total)}
        return json.dumps({"content": {"is_compressed": False},
                           "function_entries": {"aa": entries}})

    def test_an_export_with_no_minhashes_at_all_is_refused(self):
        from corpus import refilter

        committed = self.write(os.path.join(self.tmp, "s.mcrit"),
                               self._export(80, 88))
        with self.assertRaises(refilter.RefilterError) as caught:
            refilter._assert_minhashes_survived(self._export(0, 87), committed,
                                                ["___divdi3"])
        self.assertIn("no minhashes at all", str(caught.exception))

    def test_a_partial_hashing_failure_is_refused(self):
        from corpus import refilter

        committed = self.write(os.path.join(self.tmp, "s.mcrit"),
                               self._export(80, 88))
        with self.assertRaises(refilter.RefilterError):
            refilter._assert_minhashes_survived(self._export(40, 87), committed,
                                                ["___divdi3"])

    def test_losing_only_the_removed_functions_is_accepted(self):
        from corpus import refilter

        committed = self.write(os.path.join(self.tmp, "s.mcrit"),
                               self._export(80, 88))
        refilter._assert_minhashes_survived(self._export(79, 87), committed,
                                            ["___divdi3"])

    def test_a_function_count_that_does_not_match_the_removal_is_refused(self):
        from corpus import refilter

        committed = self.write(os.path.join(self.tmp, "s.mcrit"),
                               self._export(80, 88))
        with self.assertRaises(refilter.RefilterError) as caught:
            refilter._assert_minhashes_survived(self._export(80, 85), committed,
                                                ["___divdi3"])
        self.assertIn("does not describe the same sample", str(caught.exception))

    def test_a_compressed_export_is_counted_the_same_as_a_plain_one(self):
        """Every export this pipeline writes is compressed; only the plain
        form was covered, so the branch that actually runs was untested."""
        from corpus import refilter
        from mcrit.libs.utility import compress_encode

        entries = {"0": {"minhash": "ff"}, "1": {"minhash": ""}}
        blob = compress_encode(json.dumps(entries))
        text = json.dumps({"content": {"is_compressed": True},
                           "function_entries": {"aa": blob}})
        self.assertEqual(refilter._minhash_coverage(text), (2, 1))

    def test_unhashed_functions_below_mcrits_size_floor_are_not_a_failure(self):
        """Most artefacts here carry fewer minhashes than functions."""
        from corpus import refilter

        committed = self.write(os.path.join(self.tmp, "s.mcrit"),
                               self._export(617, 703))
        refilter._assert_minhashes_survived(self._export(617, 699), committed,
                                            ["a", "b", "c", "d"])


class BaselineGuardTest(TempCase):
    def test_a_toolchain_this_host_lacks_is_not_a_failure(self):
        from corpus import refilter

        with mock.patch("corpus.toolchain.get_toolchain",
                        side_effect=KeyError("unknown toolchain 'msvc143_x64'")):
            with self.assertRaises(refilter.ToolchainUnavailable):
                refilter._usable_baseline("msvc143_x64")

    def test_an_empty_baseline_is_a_failure_rather_than_a_quiet_no_op(self):
        from corpus import refilter

        with mock.patch("corpus.toolchain.get_toolchain", return_value=object()), \
             mock.patch("corpus.refilter.crt_glue", return_value={}):
            with self.assertRaises(refilter.RefilterError) as caught:
                refilter._usable_baseline("mingw13_x86")
        self.assertIn("came back empty", str(caught.exception))
        self.assertNotIsInstance(caught.exception, refilter.ToolchainUnavailable)


class ArchiveFailureIsCaughtTest(TempCase):
    """7z exits non-zero; that is a CalledProcessError, not an OSError."""

    def setUp(self):
        super().setUp()
        patch = mock.patch.object(config, "REPO_ROOT", self.tmp)
        patch.start()
        self.addCleanup(patch.stop)

    def test_a_7z_failure_is_reported_rather_than_escaping(self):
        from corpus import refilter

        slug = "Fam_1.0_mingw13_x86_f.dll"
        smda = os.path.join("data", "Fam", "x86", "smda", "%s.7z" % slug)
        mcrit = os.path.join("data", "Fam", "x86", "mcrit", "%s.mcrit" % slug)
        archive = os.path.join(self.tmp, smda)
        os.makedirs(os.path.dirname(archive), exist_ok=True)
        member = self.write(os.path.join(self.tmp, "r.smda"),
                            json.dumps({"xcfg": {}, "sha256": "aa"}))
        subprocess.run(list(package.ARCHIVE_COMMAND) + [archive, member],
                       check=True, stdout=subprocess.DEVNULL)
        self.write(os.path.join(self.tmp, mcrit),
                   json.dumps({"sample_entries": {"aa": {}}}))
        self.write(os.path.join(self.data, "Fam", "provenance.json"),
                   json.dumps({slug: {"toolchain": "mingw13_x86", "smda": smda,
                                      "mcrit": mcrit, "num_functions": 2}}))
        report = mock.Mock(xcfg={4096: mock.Mock(function_name="___divdi3")},
                           num_functions=1)
        with mock.patch("corpus.recipes.all_recipes", return_value={}), \
             mock.patch("corpus.refilter._usable_baseline"), \
             mock.patch("corpus.refilter.is_glue", return_value=True), \
             mock.patch("smda.common.SmdaReport.SmdaReport.fromDict",
                        return_value=report), \
             mock.patch("corpus.refilter._corrected_archive",
                        return_value=["___divdi3"]), \
             mock.patch("corpus.refilter._write_export") as written, \
             mock.patch("corpus.refilter._write_archive",
                        side_effect=subprocess.CalledProcessError(2, "7z")):
            # Must return, not raise: a traceback here abandons the rest of
            # the corpus and prints no FAIL line at all.
            changes, failures, _ = refilter.refilter()
        self.assertEqual(changes, [])
        self.assertEqual(len(failures), 1)
        self.assertIn("could not be", failures[0])
        # The message claims the export was rewritten and the archive was not.
        # That has to be true, or it sends whoever reads it to the wrong file.
        self.assertEqual(written.call_count, 1)

    def test_an_unreadable_archive_costs_only_itself(self):
        from corpus import refilter

        slug = "Fam_1.0_mingw13_x86_f.dll"
        smda = os.path.join("data", "Fam", "x86", "smda", "%s.7z" % slug)
        self.write(os.path.join(self.tmp, smda), "not an archive")
        self.write(os.path.join(self.data, "Fam", "provenance.json"),
                   json.dumps({slug: {"toolchain": "mingw13_x86", "smda": smda,
                                      "mcrit": "x"}}))
        with mock.patch("corpus.recipes.all_recipes", return_value={}), \
             mock.patch("corpus.refilter._usable_baseline"):
            changes, failures, _ = refilter.refilter()
        self.assertEqual(changes, [])
        self.assertEqual(len(failures), 1)
        self.assertIn("not read", failures[0])


class MiscountedProvenanceTest(TempCase):
    def setUp(self):
        super().setUp()
        patch = mock.patch.object(config, "REPO_ROOT", self.tmp)
        patch.start()
        self.addCleanup(patch.stop)

    def _family(self, recorded, held):
        mcrit = os.path.join("data", "Fam", "x86", "mcrit", "s.mcrit")
        self.write(os.path.join(self.tmp, mcrit), json.dumps(
            {"content": {"num_functions": held}, "sample_entries": {"aa": {}}}))
        self.write(os.path.join(self.data, "Fam", "provenance.json"),
                   json.dumps({"s": {"num_functions": recorded, "mcrit": mcrit}}))

    def test_a_record_left_behind_by_an_interrupted_refilter_is_reported(self):
        from corpus import validate

        self._family(recorded=88, held=85)
        problems = validate.find_miscounted_provenance(self.data)
        self.assertEqual(len(problems), 1)
        self.assertIn("says 88 functions", problems[0])

    def test_agreement_is_silent(self):
        from corpus import validate

        self._family(recorded=85, held=85)
        self.assertEqual(validate.find_miscounted_provenance(self.data), [])

    def test_a_record_with_no_count_is_not_a_problem(self):
        """The IDA-derived families carry no provenance at all, but a record
        that simply omits the field must not be invented a count for."""
        from corpus import validate

        mcrit = os.path.join("data", "Fam", "x86", "mcrit", "s.mcrit")
        self.write(os.path.join(self.tmp, mcrit), json.dumps(
            {"content": {"num_functions": 85}, "sample_entries": {"aa": {}}}))
        self.write(os.path.join(self.data, "Fam", "provenance.json"),
                   json.dumps({"s": {"mcrit": mcrit}}))
        self.assertEqual(validate.find_miscounted_provenance(self.data), [])

    def test_a_multi_sample_export_is_not_judged_against_one_record(self):
        """content.num_functions covers every sample in the file, so it
        answers for a record only when the file holds one sample."""
        from corpus import validate

        mcrit = os.path.join("data", "Fam", "x86", "mcrit", "s.mcrit")
        self.write(os.path.join(self.tmp, mcrit), json.dumps(
            {"content": {"num_functions": 170},
             "sample_entries": {"aa": {}, "bb": {}}}))
        self.write(os.path.join(self.data, "Fam", "provenance.json"),
                   json.dumps({"s": {"num_functions": 85, "mcrit": mcrit}}))
        self.assertEqual(validate.find_miscounted_provenance(self.data), [])

    def test_a_missing_export_is_left_to_find_stale_provenance(self):
        from corpus import validate

        self.write(os.path.join(self.data, "Fam", "provenance.json"),
                   json.dumps({"s": {"num_functions": 85,
                                     "mcrit": "data/Fam/x86/mcrit/gone.mcrit"}}))
        self.assertEqual(validate.find_miscounted_provenance(self.data), [])


class HiddenDirectoriesTest(TempCase):
    def test_a_staging_directory_left_by_a_crash_is_not_walked(self):
        from corpus import validate

        good = os.path.join(self.data, "Fam", "x86", "mcrit", "s.mcrit")
        self.write(good, "{}")
        # .reprocess-* is the one that really occurs: _write_archive stages
        # beside the committed archive and has to, because os.replace is
        # atomic only within a filesystem. The prune fixes the symptom; the
        # cause stays, so the name under test is the real one.
        self.write(os.path.join(self.data, "Fam", "x86", "mcrit",
                                ".reprocess-abc", "s.mcrit"), "{}")
        self.write(os.path.join(self.data, "Fam", "x86", "smda",
                                ".refilter-abc", "s.mcrit"), "{}")
        self.assertEqual(list(validate._iter_data_files(".mcrit", self.data)),
                         [good])


if __name__ == "__main__":
    unittest.main(verbosity=2)
