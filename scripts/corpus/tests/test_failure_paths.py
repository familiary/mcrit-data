"""Failure-path tests for the writers that replace committed files.

Every test here runs against a temporary tree with config.DATA_DIR patched
to point at it, so none of them can touch data/. What they cover is the
behaviour that is invisible when everything works: what is left on disk
when a replace is interrupted, when 7z fails, when an export is missing or
describes a different sample. That class of defect had already cost this
repository an archive, and it is not caught by running the pipeline.

    python -m unittest discover -s scripts/corpus/tests
"""

import io
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
                         {"deadbeef": (["A", "B", "C"], 40, [])})

    def test_zero_counts_everything_for_investigating_by_hand(self):
        from corpus import validate

        self._corpus({"A": [("deadbeef", 3)],
                      "B": [("deadbeef", 3)],
                      "C": [("deadbeef", 3)]})
        found = validate.find_cross_family_functions(self.data,
                                                     min_instructions=0)
        self.assertEqual(found, {"deadbeef": (["A", "B", "C"], 3, [])})

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


class ClassifyCollisionTest(unittest.TestCase):
    """What separates leakage from the two kinds of legitimate sharing.

    This is the judgement the whole deep check rests on, and until now it
    lived only in scripts/explain_collisions.py, where nothing tested it and
    validate did not use it. Each branch is pinned with a name taken from the
    corpus rather than invented, so a future edit that widens the standard
    library exemption has to widen it past a real symbol.
    """

    def test_one_name_across_every_family_is_leakage(self):
        from corpus import validate

        self.assertEqual(validate.classify_collision(["__udivmoddi4"]),
                         validate.LEAKAGE)

    # MSVC names an unnamed lambda <lambda_HEX> from its source, so the same
    # id in two projects means the same source - but not whose source. These
    # four pin that the exemption keys on evidence from the corpus and not on
    # the shape of the name, because a lambda out of a vendored third-party
    # header looks identical and is leakage worth reporting.
    _HOST = ("std::basic_string<char,std::char_traits<char>,"
             "std::allocator<char> >::_Reallocate_grow_by"
             "<<lambda_319d5e083f45f90dcdce5dce53cbb275>,char>")
    _BARE = "<lambda_319d5e083f45f90dcdce5dce53cbb275>::operator()"

    def test_a_lambda_a_std_symbol_names_is_standard_library(self):
        from corpus import validate

        known = validate.stdlib_lambda_ids([self._HOST])
        self.assertEqual(validate.classify_collision([self._BARE], known),
                         validate.STDLIB)

    def test_a_lambda_nothing_explains_is_still_leakage(self):
        """The whole point: an unexplained lambda is not excused."""
        from corpus import validate

        known = validate.stdlib_lambda_ids([self._HOST])
        other = "<lambda_ffffffffffffffffffffffffffffffff>::operator()"
        self.assertEqual(validate.classify_collision([other], known),
                         validate.LEAKAGE)

    def test_a_lambda_only_a_project_symbol_names_is_not_excused(self):
        """And the std:: adapters MSVC emits beside it must not excuse it.

        The first version of this test passed a project host alone, which
        pinned nothing: MSVC emits std::forward and std::invoke next to
        absl::base_internal::CallOnceImpl every time, and keyed on the
        namespace alone those laundered the lambda. Six real abseil
        call_once lambdas were excused that way.
        """
        from corpus import validate

        names = [
            "google::protobuf::internal::CallOnceInitialize"
            "<<lambda_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa> >",
            "std::forward<<lambda_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa> >",
            "std::invoke<<lambda_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa> >",
        ]
        bare = "<lambda_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa>::operator()"
        self.assertEqual(validate.stdlib_lambda_ids(names), set())
        self.assertEqual(
            validate.classify_collision([bare],
                                        validate.stdlib_lambda_ids(names)),
            validate.LEAKAGE)

    def test_a_project_lambda_passed_to_a_std_algorithm_is_not_excused(self):
        """abseil's own lambda over its own type, hosted by std::remove_if.

        Taken from data/abseil: a public algorithm template takes whatever
        callable it is handed, so its instantiation says who *used* the
        lambda and nothing about who wrote it.
        """
        from corpus import validate

        host = ("std::remove_if<std::_Vector_iterator<std::_Vector_val<"
                "std::_Simple_types<absl::lts_20250127::log_internal::"
                "`anonymous namespace'::VModuleInfo> > >,"
                "<lambda_05587629fa8d10fb5f42977c40063bb4> >")
        bare = "<lambda_05587629fa8d10fb5f42977c40063bb4>::operator()"
        self.assertEqual(validate.stdlib_lambda_ids([host]), set())
        self.assertEqual(
            validate.classify_collision([bare],
                                        validate.stdlib_lambda_ids([host])),
            validate.LEAKAGE)

    def test_the_exemption_does_not_launder_a_project_name_beside_it(self):
        from corpus import validate

        known = validate.stdlib_lambda_ids([self._HOST])
        self.assertEqual(
            validate.classify_collision([self._BARE, "re2::RE2::Match"], known),
            validate.DIFFERENT_NAMES)

    def test_without_the_evidence_set_a_lambda_is_leakage(self):
        """Callers that pass no evidence get the old, stricter answer."""
        from corpus import validate

        self.assertEqual(validate.classify_collision([self._BARE]),
                         validate.LEAKAGE)

    def test_the_32_bit_decoration_is_not_a_different_name(self):
        """_floor and floor are one function: 32-bit MinGW decorates cdecl."""
        from corpus import validate

        self.assertEqual(validate.classify_collision(["_floor", "floor"]),
                         validate.LEAKAGE)

    def test_a_std_template_instantiation_is_expected(self):
        from corpus import validate

        # As SMDA demangles it: return type first, so the symbol does not
        # start with "std::" and a startswith test alone would miss it.
        self.assertEqual(validate.classify_collision([
            "void std::vector<int, std::allocator<int>>::_M_realloc_insert"
            "<int const&>(__gnu_cxx::__normal_iterator<int*, std::vector<int, "
            "std::allocator<int>>>, int const&)"]), validate.STDLIB)

    def test_the_symbol_that_the_first_version_of_the_explainer_got_wrong(self):
        """std::__cxx11::basic_stringbuf, flagged as leakage once already."""
        from corpus import validate

        self.assertEqual(validate.classify_collision([
            "std::__cxx11::basic_stringbuf<char, std::char_traits<char>, "
            "std::allocator<char>>::~basic_stringbuf()"]), validate.STDLIB)

    def test_an_undemangled_std_symbol_is_recognised_too(self):
        """Several committed artefacts carry these unmangled; the x86 ABI
        puts one more leading underscore on them than the x64 one does."""
        from corpus import validate

        for name in ("_ZNSt9bad_allocD0Ev", "__ZNSt9bad_allocD0Ev",
                     "_ZNSsaSEPKc", "_ZN9__gnu_cxx20recursive_init_errorD0Ev",
                     "_ZN10__cxxabiv117__class_type_infoD0Ev"):
            self.assertEqual(validate.classify_collision([name]),
                             validate.STDLIB, name)

    def test_the_decoration_does_not_hide_the_namespace_either(self):
        """_same_symbol strips the 32-bit leading underscore, so the standard
        library test has to strip it too - otherwise a decorated std:: symbol
        matches its undecorated self across families and is then called
        leakage for a name the two ABIs simply spell differently."""
        from corpus import validate

        self.assertEqual(validate.classify_collision(
            ["_std::vector<int>::~vector()", "std::vector<int>::~vector()"]),
            validate.STDLIB)

    def test_a_project_function_taking_a_std_string_is_not_std(self):
        """The hole the exemption must not have.

        protobuf, abseil and re2 are all in this corpus and all link each
        other statically, so C++-into-C++ misattribution is the leakage this
        gate is most likely to meet next. Every such symbol mentions std:: in
        its arguments, and testing for "std:: appears anywhere in the name"
        would excuse the lot of them.
        """
        from corpus import validate

        self.assertEqual(validate.classify_collision([
            "google::protobuf::StringAppendF(std::__cxx11::basic_string<char, "
            "std::char_traits<char>, std::allocator<char>>*, char const*, ...)"]),
            validate.LEAKAGE)

    def test_names_that_differ_are_not_one_function(self):
        from corpus import validate

        self.assertEqual(
            validate.classify_collision(["_EVP_EncryptInit_ex",
                                         "_LZ4_compress_limitedOutput"]),
            validate.DIFFERENT_NAMES)

    def test_one_std_name_among_project_names_does_not_excuse_the_rest(self):
        """A short body shared by libstdc++ and two C projects is a
        coincidence, not an instantiation - so it is reported as differing
        names rather than laundered into the standard library bucket by the
        one std:: symbol in the set."""
        from corpus import validate

        self.assertEqual(
            validate.classify_collision(["_BIO_printf", "___mingw_fscanf",
                                         "std::ostream::flush()"]),
            validate.DIFFERENT_NAMES)

    def test_no_symbol_anywhere_cannot_be_classified(self):
        from corpus import validate

        self.assertEqual(validate.classify_collision([]), validate.UNNAMED)


class CorpusTreeCase(TempCase):
    """A temp corpus whose artefacts satisfy every check except the deep one.

    The shallow checks are not what these tests are about, and a fixture that
    trips them buries the finding under a screen of unrelated FAIL lines -
    which is the very failure mode this change exists to end. So the fixture
    writes a well-formed .mcrit and a real .7z for each family, and a family
    is only "generated" - this tooling's to answer for - when it is given the
    provenance.json that says so.
    """

    def setUp(self):
        super().setUp()
        patch = mock.patch.object(config, "REPO_ROOT", self.tmp)
        patch.start()
        self.addCleanup(patch.stop)

    def family(self, name, functions=(), generated=True, version="1.0",
               sha256=None):
        """One family holding one sample.

        ``functions`` is [(pichash, num_instructions, symbol name), ...].
        ``version`` of None writes a sample validate_mcrit_file complains
        about, which is how the pre-existing data/MSVC reports look.
        """
        sha256 = sha256 or (name.encode("utf-8").hex() + "0" * 8)
        sample = {"sha256": sha256, "family": name, "is_library": True,
                  "statistics": {"num_functions": max(len(functions), 1)}}
        if version:
            sample["version"] = version
        export = {
            "config": {"minhash": config.EXPECTED_MINHASH_CONFIG,
                       "shingler": config.EXPECTED_SHINGLER_CONFIG},
            # Uncompressed, so these tests need no mcrit import.
            "content": {"num_samples": 1, "is_compressed": False},
            "family_mapping": {"1": name},
            "sample_entries": {sha256: sample},
            "function_entries": {sha256: {
                str(index): {"pichash": pichash, "num_instructions": size,
                             "function_name": symbol}
                for index, (pichash, size, symbol) in enumerate(functions)}},
        }
        self.write(os.path.join(self.data, name, "x64", "mcrit",
                                "%s.mcrit" % name), json.dumps(export))
        self._archive(name, version)
        if generated:
            self.write(os.path.join(self.data, name, "provenance.json"), "{}")

    def _archive(self, name, version):
        """The .7z beside it, or find_unpaired_artifacts reports the pair."""
        member = self.write(os.path.join(self.tmp, "%s.smda" % name), json.dumps(
            {"metadata": {"family": name, "version": version or "1.0"},
             "status": "ok", "xcfg": {"4096": {}}}))
        archive = os.path.join(self.data, name, "x64", "smda", "%s.7z" % name)
        os.makedirs(os.path.dirname(archive), exist_ok=True)
        subprocess.run(list(package.ARCHIVE_COMMAND) + [archive, member],
                       check=True, stdout=subprocess.DEVNULL)

    def shared(self, symbol, size=40, families=("A", "B", "C"), generated=None):
        """The same PicHash in several families, under one symbol name."""
        for name in families:
            self.family(name, [("deadbeef", size, symbol)],
                        generated=name in (families if generated is None
                                           else generated))


class DeepGateTest(CorpusTreeCase):
    """--deep fails on leakage and on nothing else.

    The command reported all 79 of its findings as failures, every one of
    them benign, so it exited 1 on a corpus in the state its author intended
    and could not be used as a gate. These fix both halves of that: the
    benign kinds stop failing, and the leakage kind still does.
    """

    def test_the_same_symbol_in_three_families_fails_the_run(self):
        from corpus import validate

        self.shared("_floor")
        problems = validate.validate_all(self.data, deep=True)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("_floor", problems[0])
        self.assertIn("A, B, C", problems[0])

    def test_a_standard_library_instantiation_does_not(self):
        from corpus import validate

        notes = []
        self.shared("std::_Rb_tree<int, int>::_M_erase(int*)")
        self.assertEqual(validate.validate_all(self.data, deep=True, notes=notes),
                         [])
        self.assertIn("1 standard library instantiation", notes[0])

    def test_differing_names_do_not(self):
        from corpus import validate

        notes = []
        for name, symbol in (("A", "_a"), ("B", "_b"), ("C", "_c")):
            self.family(name, [("deadbeef", 40, symbol)])
        self.assertEqual(validate.validate_all(self.data, deep=True, notes=notes),
                         [])
        self.assertIn("1 whose symbol names differ", notes[0])

    def test_a_hash_with_no_symbol_anywhere_does_not(self):
        from corpus import validate

        notes = []
        self.shared("")
        self.assertEqual(validate.validate_all(self.data, deep=True, notes=notes),
                         [])
        self.assertIn("1 carrying no symbol", notes[0])

    def test_the_counts_are_reported_even_when_nothing_fails(self):
        """The numbers are the point of running it: a silent pass would say
        only that the check ran, not what it saw."""
        from corpus import validate

        notes = []
        self.shared("std::vector<int>::~vector()")
        validate.validate_all(self.data, deep=True, notes=notes)
        self.assertEqual(len(notes), 1)
        self.assertIn("1 cross-family PicHash(es) at >= 10 instructions: "
                      "0 leakage", notes[0])

    def test_without_deep_the_collision_is_not_looked_for_at_all(self):
        from corpus import validate

        notes = []
        self.shared("_floor")
        self.assertEqual(validate.validate_all(self.data, notes=notes), [])
        self.assertEqual(notes, [])

    def test_leakage_confined_to_families_this_tooling_does_not_own(self):
        """data/MSVC sharing a symbol with data/Golang is a real finding and
        somebody else's data: reported, not failed on, exactly like the other
        pre-existing problems in those families."""
        from corpus import validate

        notes = []
        self.shared("_floor", families=("MSVC", "Golang", "MinGW"), generated=())
        self.assertEqual(validate.validate_all(self.data, deep=True, notes=notes),
                         [])
        self.assertTrue(any("_floor" in note for note in notes), notes)

    def test_a_tree_checked_from_outside_data_is_not_excused(self):
        """A corpus staged somewhere else - a CI workspace, a build directory
        - has no data/<family> to look up, and unknown data must fail rather
        than inherit the excuse the IDA-derived families get."""
        from corpus import validate

        elsewhere = os.path.join(self.tmp, "staged")
        with mock.patch.object(config, "DATA_DIR", elsewhere):
            os.makedirs(elsewhere)
            saved, self.data = self.data, elsewhere
            try:
                self.shared("_floor", generated=())
            finally:
                self.data = saved
        # DATA_DIR is back to the empty temp corpus, so nothing in the staged
        # tree resolves to a family - which is the situation under test.
        problems = validate.validate_all(elsewhere, deep=True)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("_floor", problems[0])

    def test_but_one_generated_family_in_it_makes_it_this_tooling_s_problem(self):
        from corpus import validate

        self.shared("_floor", families=("MinGW", "Golang", "A"),
                    generated=("A",))
        problems = validate.validate_all(self.data, deep=True)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("_floor", problems[0])

    def test_explain_collisions_agrees_with_validate_on_the_same_corpus(self):
        """The two must agree, which is why there is only one classifier."""
        import explain_collisions
        from corpus import validate

        for name in ("A", "B", "C"):
            self.family(name, [("aaaa", 40, "_floor" if name != "B" else "floor"),
                               ("bbbb", 40, "std::x<int>::y()")])
        grouped = validate.group_cross_family_functions(self.data)
        self.assertEqual([h for h, _ in grouped[validate.LEAKAGE]], ["aaaa"])
        self.assertEqual([h for h, _ in grouped[validate.STDLIB]], ["bbbb"])
        with mock.patch.object(sys, "argv",
                               ["explain_collisions.py", self.data]):
            with mock.patch("sys.stdout", io.StringIO()) as out:
                exit_code = explain_collisions.main()
        # Same verdict as validate: one hash to chase, so a non-zero exit.
        self.assertEqual(exit_code, 1)
        self.assertIn("floor", out.getvalue())
        self.assertEqual(len(validate.validate_all(self.data, deep=True)), 1)


class UnownedFamilyScopeTest(CorpusTreeCase):
    """The 21 problems in data/MSVC and data/Golang, which nobody can fix here.

    They are genuine - reports with no family or version recorded, .7z files
    whose .mcrit never arrived - and they are in IDA-derived data this
    pipeline did not produce and cannot regenerate. Failing on them means
    every run of validate is red regardless of the contribution being
    checked, which is how a check stops being read. They are reported as
    notes instead, and --strict puts them back.
    """

    def test_a_problem_in_a_family_with_no_provenance_is_a_note(self):
        from corpus import validate

        notes = []
        self.family("MSVC", version=None, generated=False)
        self.assertEqual(validate.validate_all(self.data, notes=notes), [])
        self.assertIn("data/MSVC", notes[0])
        self.assertTrue(any("no version recorded" in note for note in notes), notes)

    def test_strict_puts_it_back_among_the_problems(self):
        from corpus import validate

        notes = []
        self.family("MSVC", version=None, generated=False)
        problems = validate.validate_all(self.data, strict=True, notes=notes)
        self.assertEqual(len(problems), 1, problems)
        self.assertEqual(notes, [])

    def test_the_same_problem_in_a_generated_family_still_fails(self):
        """The scoping must not excuse the data this branch actually writes."""
        from corpus import validate

        self.family("libzlib", version=None, generated=True)
        problems = validate.validate_all(self.data)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("no version recorded", problems[0])

    def test_an_unpaired_archive_is_scoped_by_its_own_family(self):
        """find_unpaired_artifacts reports a path rather than a family, and
        four of the eight pre-existing Golang problems come from it."""
        from corpus import validate

        notes = []
        self.family("libzlib")
        self.family("Golang", generated=False)
        os.remove(os.path.join(self.data, "Golang", "x64", "mcrit",
                               "Golang.mcrit"))
        self.assertEqual(validate.validate_all(self.data, notes=notes), [])
        self.assertTrue(any("Golang.7z has no matching" in note
                            for note in notes), notes)

    def test_a_duplicate_shared_with_a_generated_family_is_not_excused(self):
        """One sha256 in data/MSVC and in a generated family is this
        tooling's problem: it is the generated side that would have to go."""
        from corpus import validate

        self.family("MSVC", generated=False, sha256="aa" * 32)
        self.family("libzlib", generated=True, sha256="aa" * 32)
        problems = validate.validate_all(self.data)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("duplicate sample aaaaaaaaaaaa", problems[0])


class ValidateExitCodeTest(CorpusTreeCase):
    """What CI actually observes: the process exit code and its output."""

    def _run(self, *arguments):
        import build_corpus

        with mock.patch.object(sys, "argv",
                               ["build_corpus.py", "validate"] + list(arguments)):
            with mock.patch("sys.stdout", io.StringIO()) as out:
                return build_corpus.main(), out.getvalue()

    def test_a_clean_corpus_exits_zero_with_the_counts_printed(self):
        self.shared("std::vector<int>::~vector()")
        code, output = self._run("--deep", self.data)
        self.assertEqual(code, 0, output)
        self.assertIn("NOTE 1 cross-family PicHash(es)", output)
        self.assertNotIn("FAIL", output)
        self.assertIn("0 problem(s)", output)

    def test_leakage_exits_one(self):
        self.shared("_floor")
        code, output = self._run("--deep", self.data)
        self.assertEqual(code, 1, output)
        self.assertIn("FAIL PicHash", output)
        self.assertIn("1 problem(s)", output)

    def test_the_pre_existing_problems_do_not_decide_the_exit_code(self):
        """The whole point: a corpus whose only problems are in data nobody
        here can regenerate is a pass, and says why."""
        self.family("MSVC", version=None, generated=False)
        code, output = self._run(self.data)
        self.assertEqual(code, 0, output)
        self.assertIn("--strict fails on them too", output)
        self.assertIn("0 problem(s)", output)
        self.assertEqual(self._run("--strict", self.data)[0], 1)

    def test_the_floor_can_be_lowered_from_the_command_line(self):
        """--min-instructions is for investigating by hand, and it has to
        reach the report as well as the collection, or a hand run describes
        the same corpus differently from the gate."""
        self.shared("_floor")
        code, output = self._run("--deep", "--min-instructions", "100", self.data)
        self.assertEqual(code, 0, output)
        self.assertIn("at >= 100 instructions", output)


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


class _Instruction(object):
    def __init__(self, mnemonic="ret", operands=""):
        self.mnemonic = mnemonic
        self.operands = operands


class _Function(object):
    """Enough of an SmdaFunction for the symbol-coverage check."""

    def __init__(self, num_instructions, function_name="", offset=0,
                 instructions=None):
        self.num_instructions = num_instructions
        self.function_name = function_name
        self.offset = offset
        self._instructions = instructions or [_Instruction()]

    def getInstructions(self):
        return self._instructions


class _Report(object):
    def __init__(self, functions):
        self._functions = functions
        self.num_functions = len(functions)

    def getFunctions(self):
        return self._functions


def _thunk(offset):
    """One unnamed function that is a single direct jump, as an ILT entry is."""
    return _Function(1, "", offset, [_Instruction("jmp", "0x401000")])


class SymbolCoverageTest(unittest.TestCase):
    """The gate that refuses a build which stripped its symbols.

    Counting every function made this gate reject MSVC x86 C++ builds that
    had stripped nothing: cryptopp 8.9.0 named 7844 of 20650 functions and
    was refused at 38%, while the same source built for x64 named 66%. The
    difference was one- and two-instruction exception-handling fragments,
    which carry no symbol in any build. The tests below pin both halves of
    that: the fragments must not be able to fail a build, and a build that
    really was stripped still must.
    """

    def _check(self, functions, ratio=0.5):
        from corpus import smdaify

        smdaify.assert_symbols_survived(_Report(functions), "x.dll", ratio)

    def test_unnamed_fragments_cannot_fail_a_build_that_kept_its_symbols(self):
        # The shape nlohmann_json x86 has: every real function named, and
        # more single-instruction fragments than there are real functions.
        functions = ([_Function(40, "real_%d" % i) for i in range(10)]
                     + [_Function(1) for _ in range(30)])
        self._check(functions)

    def test_a_stripped_build_still_fails(self):
        functions = [_Function(40) for _ in range(10)]
        with self.assertRaises(Exception) as caught:
            self._check(functions)
        self.assertIn("0 of 10 functions of at least 3 instructions",
                      str(caught.exception))

    def test_the_message_reports_the_raw_counts_as_well(self):
        """So a reader can tell a stripped build from a mis-set floor."""
        functions = [_Function(40) for _ in range(10)] + [_Function(1)]
        with self.assertRaises(Exception) as caught:
            self._check(functions)
        self.assertIn("Over every function it is 0 of 11",
                      str(caught.exception))

    def test_functions_at_the_floor_are_counted(self):
        # Three instructions is the floor, so these are real functions and
        # their missing names are a stripped build.
        with self.assertRaises(Exception):
            self._check([_Function(3) for _ in range(10)])

    def test_a_ratio_of_zero_turns_the_check_off(self):
        # libtomcrypt sets this: its names come from the export table.
        self._check([_Function(40) for _ in range(10)], ratio=0)

    def test_a_report_with_nothing_above_the_floor_is_refused(self):
        """Not a division guard: a stub build has to fail, not pass.

        MIN_USEFUL_FUNCTIONS admits eight functions, so a truncated build
        whose every function is one instruction reaches here, and returning
        would turn the gate off in the case it exists for.
        """
        with self.assertRaises(Exception) as caught:
            self._check([_Function(1) for _ in range(10)])
        self.assertIn("nothing for the symbol check to measure",
                      str(caught.exception))

    def test_a_ratio_exactly_at_the_threshold_passes(self):
        """The comparison is >=, so half named is enough. Pins the boundary."""
        self._check([_Function(40, "named_%d" % i) for i in range(5)]
                    + [_Function(40) for _ in range(5)])

    def test_one_function_below_the_threshold_fails(self):
        self.assertRaises(
            Exception, self._check,
            [_Function(40, "named_%d" % i) for i in range(4)]
            + [_Function(40) for _ in range(5)])

    def test_the_check_runs_before_the_glue_is_dropped(self):
        """Dropping glue lowers the ratio, so the order is load-bearing.

        Glue is almost entirely named, so measuring after the drop would
        judge a build by how much compiler runtime it linked. Only the call
        order in smdaify enforces that, and nothing else here would notice
        if it moved.
        """
        import inspect
        from corpus import smdaify

        body = inspect.getsource(smdaify.smdaify)
        self.assertLess(body.index("assert_symbols_survived"),
                        body.index("_drop_crt_glue"))


class _CountedReport(object):
    """Enough of an SmdaReport for smdaify's own floor check.

    The floor is applied inside smdaify() rather than in a helper of its own,
    so the only way to test it is to run smdaify() over a stand-in report -
    which has the side benefit of pinning that the recipe's number actually
    reaches the comparison rather than merely being stored on the dataclass.
    """

    def __init__(self, count):
        self.status = "ok"
        self.message = ""
        self.num_functions = count
        self.bitness = 32
        self._functions = [_Function(40, "named_%d" % i) for i in range(count)]

    def getFunctions(self):
        return self._functions


class MinimumFunctionsTest(unittest.TestCase):
    """The floor that refuses a sample too small to be reference data.

    config.MIN_USEFUL_FUNCTIONS is eight because every build accident anyone
    had seen - an empty stub, the wrong artefact picked up - lands below it
    and every real project lands above. 4g3nt47/Obfuscator is the first real
    project that does not: it has seven functions and no library API, so
    nothing can raise the count. Recipe.min_functions is for that case only,
    and these tests pin what keeps it from becoming a way to wave a defective
    build through: the default does not move, an override admits exactly its
    own value, and an override admits nothing below itself.
    """

    def _run(self, count, min_functions=None):
        from corpus import smdaify

        with mock.patch.object(smdaify, "disassemble",
                               return_value=_CountedReport(count)):
            return smdaify.smdaify("x.exe", "Fam", "1", "x.exe",
                                   min_named_ratio=0, drop_crt_glue=False,
                                   min_functions=min_functions)

    def test_the_default_floor_still_refuses_seven_functions(self):
        """Nothing about adding the override may move the default."""
        from corpus import config

        self.assertEqual(config.MIN_USEFUL_FUNCTIONS, 8)
        with self.assertRaises(Exception) as caught:
            self._run(7)
        self.assertIn("only 7 functions", str(caught.exception))

    def test_the_default_floor_admits_eight(self):
        report, _ = self._run(8)
        self.assertEqual(report.num_functions, 8)

    def test_an_override_admits_exactly_its_own_value(self):
        """Obfuscator's case: seven functions, all seven of them real."""
        report, _ = self._run(7, min_functions=7)
        self.assertEqual(report.num_functions, 7)

    def test_an_override_does_not_admit_anything_below_it(self):
        """The point of the whole exercise: it is a floor, not a switch.

        A recipe that states seven and produces six has lost a function
        between the recipe being written and the build being run, which is
        exactly the accident the floor is for.
        """
        with self.assertRaises(Exception) as caught:
            self._run(6, min_functions=7)
        self.assertIn("only 6 functions", str(caught.exception))
        self.assertIn("this recipe requires 7", str(caught.exception))

    def test_an_override_above_the_default_is_used_as_given(self):
        """Not clamped to MIN_USEFUL_FUNCTIONS in either direction."""
        self.assertRaises(Exception, self._run, 20, 32)
        report, _ = self._run(32, min_functions=32)
        self.assertEqual(report.num_functions, 32)

    def test_none_means_the_shared_constant(self):
        """The default on the dataclass must not be a number of its own."""
        from corpus.recipe import Recipe

        self.assertIsNone(Recipe.min_functions)

    def test_the_recipe_value_reaches_smdaify(self):
        """pipeline.py has to pass it; a dataclass field alone does nothing."""
        import inspect
        from corpus import pipeline

        self.assertIn("min_functions=recipe.min_functions",
                      inspect.getsource(pipeline.run_recipe))


class IncrementalLinkTableTest(unittest.TestCase):
    """The check that refuses a PE linked with /INCREMENTAL.

    Seven recipes shipped an incremental link table before anyone looked:
    nlohmann_json x86 carried 2936 one-instruction jump thunks among 5205
    functions. Nothing in the pipeline reported it - the symbol-coverage
    ratio merely went quiet, and the instruction floor that ratio now uses
    would hide it completely - so it needs a check that names it.
    """

    def _check(self, functions):
        from corpus import smdaify

        smdaify.assert_not_incrementally_linked(_Report(functions), "x.dll")

    def _table(self, count, start=0x401005, stride=5):
        return [_thunk(start + i * stride) for i in range(count)]

    def test_a_table_is_refused(self):
        with self.assertRaises(Exception) as caught:
            self._check(self._table(200) + [_Function(40, "real")])
        self.assertIn("incremental link table", str(caught.exception))
        self.assertIn("/INCREMENTAL:NO", str(caught.exception))

    def test_a_run_one_short_of_the_limit_passes(self):
        from corpus import config

        self._check(self._table(config.MAX_INCREMENTAL_THUNK_RUN - 1))

    def test_a_run_exactly_at_the_limit_is_refused(self):
        from corpus import config

        self.assertRaises(Exception, self._check,
                          self._table(config.MAX_INCREMENTAL_THUNK_RUN))

    def test_scattered_thunks_are_not_a_table(self):
        """Many thunks, no run: what a tail-call-heavy image looks like."""
        self._check([_thunk(0x401000 + i * 0x40) for i in range(500)])

    def test_named_jumps_are_not_counted(self):
        """abseil's 1-instruction jumps are tail calls and carry names."""
        self._check([_Function(1, "tail_%d" % i, 0x401005 + i * 5,
                               [_Instruction("jmp", "0x401000")])
                     for i in range(200)])

    def test_import_thunks_are_not_counted(self):
        """A jump through the IAT is ordinary and is written as a memory ref."""
        self._check([_Function(1, "", 0x401005 + i * 5,
                               [_Instruction("jmp", "dword ptr [0x402000]")])
                     for i in range(200)])

    def test_a_run_broken_by_a_gap_does_not_accumulate(self):
        from corpus import config

        half = config.MAX_INCREMENTAL_THUNK_RUN - 1
        self._check(self._table(half)
                    + self._table(half, start=0x500000))

    def test_an_empty_report_is_not_a_table(self):
        self._check([])


class _Recipe(object):
    def __init__(self, toolchains, artifacts):
        self.toolchains = toolchains
        self.artifacts = artifacts


class _Artifact(object):
    def __init__(self, component, is_blob=False):
        self.component = component
        self.build_flags = None
        self.is_blob = is_blob


class ProvenanceToolchainTest(unittest.TestCase):
    """Resolving an entry to its recipe when two recipes share a version.

    Adding an MSVC recipe beside each MinGW one made (family, version)
    ambiguous for 189 of this corpus's entries, and refresh_provenance could
    then refresh none of them - it reported every one as unmatched rather
    than picking a recipe at random, which was the right refusal but left the
    script unusable. The toolchain in the slug is what separates them.
    """

    def _resolve(self, slug, entry, candidates):
        sys.path.insert(0, os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))))
        import refresh_provenance

        index = {("Fam", entry["version"]): candidates}
        return refresh_provenance._resolve(index, "Fam", slug, entry)

    def _pair(self):
        return [("Fam_1.0", _Recipe(["mingw_x86", "mingw_x64"],
                                    [_Artifact("f.dll")])),
                ("Fam_1.0_msvc", _Recipe(["msvc_x86", "msvc_x64"],
                                         [_Artifact("f.dll")]))]

    def test_the_slug_picks_the_msvc_recipe(self):
        recipe, _ = self._resolve("Fam_1.0_msvc143_x64_f.dll",
                                  {"version": "1.0", "component": "f.dll"},
                                  self._pair())
        self.assertEqual(recipe.toolchains, ["msvc_x86", "msvc_x64"])

    def test_the_slug_picks_the_mingw_recipe(self):
        recipe, _ = self._resolve("Fam_1.0_mingw13_x86_f.dll",
                                  {"version": "1.0", "component": "f.dll"},
                                  self._pair())
        self.assertEqual(recipe.toolchains, ["mingw_x86", "mingw_x64"])

    def test_a_slug_naming_no_candidate_toolchain_stays_ambiguous(self):
        """Narrowing must only ever narrow, never guess."""
        from refresh_provenance import Unmatched

        with self.assertRaises(Unmatched):
            self._resolve("Fam_1.0_gcc13_x64_f.dll",
                          {"version": "1.0", "component": "f.dll"},
                          self._pair())

    def test_a_blob_is_never_narrowed_by_its_slug(self):
        """Recipe.slug labels a blob "msvc" whatever toolchain extracted it.

        "msvc" is a real toolchain alias, so such a slug parses to msvc_x64
        and would narrow onto whichever candidate declares MSVC - reading as
        a successful match while attaching that recipe's build_flags to a
        blob it never produced. It has to stay ambiguous instead.
        """
        from refresh_provenance import Unmatched

        candidates = [
            ("Fam_1.0", _Recipe(["mingw_x64"], [_Artifact("b", is_blob=True)])),
            ("Fam_1.0_msvc", _Recipe(["msvc_x64"], [_Artifact("b")])),
        ]
        with self.assertRaises(Unmatched):
            self._resolve("Fam_1.0_msvc_x64_b",
                          {"version": "1.0", "component": "b"}, candidates)

    def test_an_unreadable_slug_stays_ambiguous(self):
        from refresh_provenance import Unmatched

        with self.assertRaises(Unmatched) as caught:
            self._resolve("something-else-entirely",
                          {"version": "1.0", "component": "f.dll"},
                          self._pair())
        self.assertIn("unreadable toolchain", str(caught.exception))

    def test_an_underscore_in_the_family_does_not_shift_the_segment(self):
        import refresh_provenance

        self.assertEqual(
            refresh_provenance._toolchain_of(
                "nlohmann_json_3.12.0_msvc143_x86_nlohmann_json.dll",
                "nlohmann_json", "3.12.0"),
            "msvc_x86")

    def test_an_underscore_in_the_component_does_not_either(self):
        import refresh_provenance

        self.assertEqual(
            refresh_provenance._toolchain_of(
                "libevent_2.1.12_mingw13_x64_event_core.dll",
                "libevent", "2.1.12"),
            "mingw_x64")

    def test_a_single_candidate_is_still_resolved_without_a_toolchain(self):
        """The unambiguous case must not start depending on the slug."""
        recipe, _ = self._resolve(
            "anything", {"version": "1.0", "component": "f.dll"},
            [("Fam_1.0", _Recipe(["mingw_x86"], [_Artifact("f.dll")]))])
        self.assertEqual(recipe.toolchains, ["mingw_x86"])

    def _linux_pair(self):
        """The shape all four string-obfuscator families now have."""
        return [("Fam_1.0", _Recipe(["mingw_x86", "mingw_x64"],
                                    [_Artifact("f.dll")])),
                ("Fam_1.0_linux", _Recipe(["linux_x86", "linux_x64"],
                                          [_Artifact("f.so")]))]

    def test_the_slug_picks_the_linux_recipe_over_the_mingw_one(self):
        """The producer segment is "gcc13" and the alias is "linux_x64".

        Nothing about those two strings relates them, so this only works
        because both sides go through corpus.toolchain.canonical_alias.
        Without it every artefact of the four families that now have a
        MinGW and a Linux recipe for one version would be unresolvable.
        """
        recipe, _ = self._resolve("Fam_1.0_gcc13_x64_f.so",
                                  {"version": "1.0", "component": "f.so"},
                                  self._linux_pair())
        self.assertEqual(recipe.toolchains, ["linux_x86", "linux_x64"])

    def test_the_mingw_slug_still_picks_the_mingw_recipe(self):
        recipe, _ = self._resolve("Fam_1.0_mingw13_x86_f.dll",
                                  {"version": "1.0", "component": "f.dll"},
                                  self._linux_pair())
        self.assertEqual(recipe.toolchains, ["mingw_x86", "mingw_x64"])

    def test_a_gcc_slug_reads_as_the_linux_alias(self):
        import refresh_provenance

        self.assertEqual(
            refresh_provenance._toolchain_of(
                "Obfuscate_2026-06-03_gcc13_x64_ay_obfuscate.so",
                "Obfuscate", "2026-06-03"),
            "linux_x64")


class ToolchainAliasTest(unittest.TestCase):
    """The three spellings of the Linux toolchain have to fold onto one.

    It is registered under its versioned id, under the version-less alias
    that id folds onto by the digit-stripping rule every slug reader uses,
    and under the alias recipes declare - which is named after the target
    rather than the compiler, so no rule over the string alone relates it to
    the other two.
    """

    def test_every_spelling_folds_onto_the_recipe_alias(self):
        from corpus.toolchain import canonical_alias

        for spelling in ("gcc13_x64", "gcc_x64", "linux_x64"):
            self.assertEqual(canonical_alias(spelling), "linux_x64", spelling)

    def test_the_windows_toolchains_are_untouched(self):
        from corpus.toolchain import canonical_alias

        self.assertEqual(canonical_alias("mingw13_x86"), "mingw_x86")
        self.assertEqual(canonical_alias("mingw_x64"), "mingw_x64")
        self.assertEqual(canonical_alias("msvc143_x64"), "msvc_x64")

    def test_an_unrecognised_id_is_returned_with_its_digits_stripped(self):
        from corpus.toolchain import canonical_alias

        self.assertEqual(canonical_alias("clang19_x64"), "clang_x64")
        self.assertEqual(canonical_alias(""), "")

    def test_the_container_follows_the_toolchain(self):
        """readme.py labels a row from this, so a blob's None must not fail."""
        from corpus.toolchain import image_format

        for spelling in ("gcc13_x64", "gcc_x86", "linux_x64"):
            self.assertEqual(image_format(spelling), "ELF", spelling)
        for spelling in ("mingw13_x64", "msvc143_x86", "", None):
            self.assertEqual(image_format(spelling), "PE", repr(spelling))


class LinuxToolchainShapeTest(unittest.TestCase):
    """What kind="linux" changes, and what it must leave alone.

    The MinGW probe command line in particular: the baseline measured with
    it is a constant the rest of this corpus was filtered against, so a
    change there silently invalidates every committed report.
    """

    def _toolchain(self, kind, arch_flag=""):
        from corpus.toolchain import Toolchain

        return Toolchain(id="t", short_id="t", arch="x64", bitness=64,
                         prefix="", cc="cc", cxx="cxx", windres="wr",
                         strip="s", ar="ar", ranlib="rl", kind=kind,
                         arch_flag=arch_flag)

    def test_the_mingw_probe_command_is_unchanged(self):
        toolchain = self._toolchain("mingw")
        self.assertEqual(toolchain.probe_command("cc", "p.c", "out", True),
                         ["cc", "-O2", "-o", "out", "p.c", "-shared"])

    def test_the_linux_probe_command_names_the_abi_and_is_position_independent(self):
        toolchain = self._toolchain("linux", "-m32")
        self.assertEqual(toolchain.probe_command("cc", "p.c", "out", True),
                         ["cc", "-m32", "-O2", "-fPIC", "-o", "out", "p.c",
                          "-shared"])

    def test_the_linux_environment_does_not_export_an_empty_windres(self):
        """An autotools build that tests for it would find it set and run ""."""
        environment = self._toolchain("linux", "-m64").build_env()
        self.assertNotIn("WINDRES", environment)
        self.assertEqual(environment["CC"], "cc -m64")
        self.assertEqual(environment["STRIP"], "true")

    def test_the_mingw_environment_still_exports_windres(self):
        self.assertEqual(self._toolchain("mingw").build_env()["WINDRES"], "wr")

    def test_the_linux_target_triple_is_not_built_from_an_empty_prefix(self):
        """{platform} expanding to "" made cargo report an unknown target."""
        placeholders = self._toolchain("linux", "-m64").placeholders()
        self.assertEqual(placeholders["platform"], "x86_64")
        self.assertEqual(placeholders["host"], "x86_64-linux-gnu")
        self.assertEqual(placeholders["archflag"], "-m64")

    def test_the_cross_compilers_still_take_their_triple_from_the_prefix(self):
        from corpus.toolchain import Toolchain

        toolchain = Toolchain(id="t", short_id="t", arch="x86", bitness=32,
                              prefix="i686-w64-mingw32-", cc="cc", cxx="cxx",
                              windres="wr", strip="s", ar="ar", ranlib="rl")
        placeholders = toolchain.placeholders()
        self.assertEqual(placeholders["platform"], "i686")
        self.assertEqual(placeholders["host"], "i686-w64-mingw32")
        self.assertEqual(placeholders["archflag"], "")


class ElfReadmeRowTest(unittest.TestCase):
    """A .so must not be offered to a reader as a PE."""

    def _entry(self, toolchain, compiler):
        return {"toolchain": toolchain, "compiler": compiler,
                "version": "1.0", "component": "f", "architecture": "x64",
                "mcrit": "data/F/x64/mcrit/f.mcrit",
                "smda": "data/F/x64/smda/f.7z"}

    def test_a_linux_row_is_labelled_elf_and_names_the_target(self):
        from corpus import readme
        from corpus.toolchain import image_format

        entry = self._entry("gcc13_x64", "gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0")
        self.assertEqual(image_format(entry["toolchain"]), "ELF")
        self.assertEqual(readme._compiler_label(entry), "GCC 13 (Linux, glibc)")

    def test_the_packaging_string_never_reaches_the_table(self):
        """A parenthesis in a markdown cell closes the link beside it early."""
        from corpus import readme

        label = readme._compiler_label(
            self._entry("gcc13_x86", "gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"))
        self.assertNotIn("(Ubuntu", label)

    def test_the_mingw_label_is_unchanged(self):
        from corpus import readme

        self.assertEqual(
            readme._compiler_label(
                self._entry("mingw13_x64", "x86_64-w64-mingw32-gcc (GCC) 13.2.0")),
            "MinGW-w64 GCC 13.2.0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
