"""Tests for the MSVC_TOOLSETS recipes and the crawl_vclibs shard rules."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from corpus import crawl_vclibs, recipes


class ClassifyTest(unittest.TestCase):
    def check(self, kind, expected):
        for name, shard in expected.items():
            self.assertEqual(crawl_vclibs.classify(name, kind), shard, name)

    def test_crt(self):
        self.check("crt", {
            "libcmt.lib": "crt_mt", "LIBVCRUNTIME.lib": "crt_mt",
            "libcpmt.lib": "crt_mt", "libcpmt1.lib": "crt_mt",
            "libconcrt.lib": "crt_mt", "oldnames.lib": "crt_mt",
            "legacy_stdio_definitions.lib": "crt_mt", "chkstk.obj": "crt_mt",
            "libcmtd.lib": "crt_mt_debug", "libcpmtd1.lib": "crt_mt_debug",
            "libvcruntimed.lib": "crt_mt_debug",
            "msvcrt.lib": "crt_md", "msvcprt.lib": "crt_md",
            "vcomp.lib": "crt_md", "vcruntime.lib": "crt_md",
            "msvcrtd.lib": "crt_md_debug", "msvcprtd.lib": "crt_md_debug",
            "vcompd.lib": "crt_md_debug"})

    def test_atlmfc(self):
        self.check("atlmfc", {
            "atls.lib": "atl", "atlthunk.lib": "atl", "atlsd.lib": "atl_debug",
            "nafxcw.lib": "mfc_ansi", "nafxcwd.lib": "mfc_ansi_debug",
            "uafxcw.lib": "mfc_unicode", "uafxcwd.lib": "mfc_unicode_debug",
            "mfc140u.lib": "mfc_dll", "mfcs140u.lib": "mfc_dll",
            "mfc140ud.lib": "mfc_dll_debug", "mfcm140d.lib": "mfc_dll_debug"})

    def test_every_assignment_is_a_declared_shard_of_its_directory(self):
        for kind, names in (("crt", ["libcmt.lib", "libcmtd.lib", "msvcrt.lib",
                                     "msvcrtd.lib", "x.obj", "foo.lib"]),
                            ("atlmfc", ["atls.lib", "nafxcw.lib", "foo.lib",
                                        "uafxcwd.lib"])):
            for name in names:
                shard = crawl_vclibs.classify(name, kind)
                self.assertEqual(crawl_vclibs.SHARDS[shard][0], kind)

    def test_sanitizer_runtimes_are_excluded(self):
        self.assertTrue(crawl_vclibs.is_excluded(
            "clang_rt.fuzzer_MD-x86_64.lib"))
        self.assertTrue(crawl_vclibs.is_excluded("clang_rt.asan-i386.lib"))
        self.assertIsNone(crawl_vclibs.is_excluded("libcmt.lib"))

    def test_import_descriptors_are_not_code(self):
        self.assertEqual(crawl_vclibs.code_members(
            ["VCRUNTIME140.dll", "a.obj", "B.OBJ", "msvcp140.DLL"]),
            ["a.obj", "B.OBJ"])


class RecipeTest(unittest.TestCase):
    def found(self):
        return {n: r for n, r in recipes.all_recipes().items()
                if n.startswith("MSVC_TOOLSETS_")}

    def test_one_recipe_per_toolset_and_shard(self):
        found = self.found()
        self.assertEqual(len(found), 3 * len(crawl_vclibs.SHARDS))
        for name, recipe in found.items():
            self.assertEqual(recipe.family, "MSVC_TOOLSETS")
            self.assertFalse(recipe.drop_crt_glue)
            self.assertTrue(recipe.dedupe_functions)
            self.assertEqual(len(recipe.artifacts), 1)
            artifact = recipe.artifacts[0]
            self.assertTrue(name.endswith("_" + artifact.component))
            self.assertTrue(name.startswith("MSVC_TOOLSETS_" + recipe.version))
            self.assertIn("--toolset " + recipe.version, recipe.build[0].command)
            self.assertIn(artifact.component, recipe.build[0].command)

    def test_slugs_are_usable_filenames(self):
        from corpus.toolchain import Toolchain  # noqa: F401  (import check)
        for recipe in self.found().values():
            artifact = recipe.artifacts[0]
            stem = "_".join([recipe.family, recipe.version, "msvc143", "x64",
                             artifact.component])
            self.assertFalse(set(stem) & set(' ()[]<>"\'`|#?%'))


if __name__ == "__main__":
    unittest.main()
