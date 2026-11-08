"""Tests for the local-source and dedupe support behind the MSVC_UCRT recipes."""

import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from corpus import config, fetch, recipes, smdaify
from corpus.recipe import Source


class LocalSourceTest(unittest.TestCase):
    def test_local_source_is_an_empty_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(config, "SOURCE_DIR", tmp), \
                    mock.patch.object(config, "ensure_dirs"):
                root, provenance = fetch.fetch_source(
                    Source(local="Windows SDK"), "x")
            self.assertTrue(os.path.isdir(root))
            self.assertEqual(os.listdir(root), [])
            self.assertEqual(provenance, {"local": "Windows SDK"})


class DedupeTest(unittest.TestCase):
    def test_collapses_equal_hash_and_name_only(self):
        def fn(h, name):
            return SimpleNamespace(pic_hash=h, function_name=name)
        report = SimpleNamespace(xcfg={0x10: fn(1, "a"), 0x20: fn(1, "a"),
                                       0x30: fn(1, "b"), 0x40: fn(2, "a")},
                                 _sorted_functions=object())
        with mock.patch.object(smdaify, "_recompute_statistics"):
            dropped = smdaify._dedupe_functions(report)
        self.assertEqual(dropped, ["a"])
        self.assertEqual(sorted(report.xcfg), [0x10, 0x30, 0x40])


class RecipeTest(unittest.TestCase):
    def test_ucrt_recipes_declare_both_flavours_and_no_glue_filter(self):
        found = [r for n, r in recipes.all_recipes().items()
                 if n.startswith("MSVC_UCRT_")]
        self.assertTrue(found)
        for recipe in found:
            self.assertFalse(recipe.drop_crt_glue)
            self.assertEqual([a.component for a in recipe.artifacts],
                             ["libucrt", "libucrtd"])


if __name__ == "__main__":
    unittest.main()
