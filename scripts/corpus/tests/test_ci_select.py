"""What a push builds on the Windows runner: only the recipes it changed."""

import os
import subprocess
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")
SCRIPT = os.path.join(ROOT, "scripts", "build_corpus.py")
WORKFLOW = os.path.join(ROOT, ".github", "workflows",
                        "windows-reference-data.yml")


def listing(*args):
    return subprocess.run([sys.executable, "-W", "ignore", SCRIPT, "list"]
                          + list(args), capture_output=True, text=True,
                          cwd=ROOT)


class ListByModule(unittest.TestCase):
    def test_a_recipe_file_selects_its_own_recipes(self):
        result = listing("--toolchain", "msvc_x64", "--names-only", "--modules",
                         "scripts/corpus/recipes/lz4_msvc.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split(), ["lz4_1.10.0_msvc"])

    def test_several_files_select_the_union_and_bare_names_work(self):
        result = listing("--toolchain", "msvc_x86", "--names-only", "--modules",
                         "scripts/corpus/recipes/lz4_msvc.py", "cjson_msvc")
        self.assertEqual(result.returncode, 0, result.stderr)
        names = result.stdout.split()
        self.assertIn("lz4_1.10.0_msvc", names)
        self.assertTrue(any(n.startswith("cJSON_") for n in names))

    def test_windows_separators_are_accepted(self):
        result = listing("--toolchain", "msvc_x64", "--names-only", "--modules",
                         "scripts\\corpus\\recipes\\lz4_msvc.py")
        self.assertEqual(result.stdout.split(), ["lz4_1.10.0_msvc"])

    def test_a_file_with_nothing_for_the_toolchain_is_exit_3_not_an_error(self):
        # lz4.py is the MinGW recipe; it declares no MSVC toolchain.
        for path in ("scripts/corpus/recipes/lz4.py",
                     "scripts/corpus/recipes/__init__.py",
                     "scripts/corpus/recipes/no_such_recipe.py"):
            result = listing("--toolchain", "msvc_x64", "--names-only",
                             "--modules", path)
            self.assertEqual(result.returncode, 3, (path, result.stderr))
            self.assertEqual(result.stdout, "")

    def test_without_modules_the_whole_leg_is_still_listed(self):
        result = listing("--toolchain", "msvc_x64", "--names-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreater(len(result.stdout.split()), 10)


class WorkflowWiring(unittest.TestCase):
    def setUp(self):
        with open(WORKFLOW, encoding="utf-8") as handle:
            self.text = handle.read()

    def test_the_build_reads_the_selection_not_the_dispatch_input(self):
        self.assertIn("steps.select.outputs.recipes", self.text)
        self.assertNotIn('$requested = "${{ github.event.inputs.recipes }}"',
                         self.text)

    def test_every_step_after_the_build_honours_a_skipped_selection(self):
        for name in ("Scope the artefacts", "Validate", "Upload reference data",
                     "Show build logs", "Upload build logs"):
            start = self.text.index("- name: " + name)
            end = self.text.find("\n      - name:", start + 1)
            step = self.text[start:end if end != -1 else len(self.text)]
            self.assertIn("steps.select.outputs.skipped != 'true'", step, name)

    def test_pipeline_code_still_rebuilds_everything(self):
        for path in ("scripts/corpus/baseline.py", "scripts/corpus/smdaify.py",
                     "scripts/corpus/toolchain.py", "scripts/build_corpus.py"):
            self.assertIn('"%s"' % path, self.text)


if __name__ == "__main__":
    unittest.main()
