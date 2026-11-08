"""Tests for the MSVC_TOOLSETS recipes and the crawl_vclibs shard rules."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from corpus import crawl_vclibs, recipes


class ClassifyTest(unittest.TestCase):
    def check(self, kind, expected, siblings=()):
        for name, shard in expected.items():
            self.assertEqual(crawl_vclibs.classify(name, kind, siblings),
                             shard, name)

    def test_crt(self):
        names = ["libcmt.lib", "libcmtd.lib", "libcpmt.lib", "libcpmt1.lib",
                 "libcpmtd.lib", "libcpmtd0.lib", "libcpmtd1.lib", "msvcrt.lib",
                 "msvcrtd.lib", "msvcprtd.lib", "comsupp.lib", "comsuppwd.lib",
                 "vcompd.lib", "chkstk.obj"]
        self.check("crt", {
            "libcmt.lib": "crt_mt", "LIBVCRUNTIME.lib": "crt_mt",
            "libcpmt.lib": "crt_mt", "libconcrt.lib": "crt_mt",
            "oldnames.lib": "crt_mt", "chkstk.obj": "crt_mt",
            "legacy_stdio_definitions.lib": "crt_mt",
            "libcpmt1.lib": "crt_mt_idl1", "libconcrt1.lib": "crt_mt_idl1",
            "libcmtd.lib": "crt_mt_debug", "libcpmtd.lib": "crt_mt_debug",
            "libcpmtd0.lib": "crt_mt_debug_idl0",
            "libconcrtd1.lib": "crt_mt_debug_idl1",
            "msvcrt.lib": "crt_md", "msvcprt.lib": "crt_md",
            "comsupp.lib": "crt_md", "vcomp.lib": "crt_md",
            "msvcrtd.lib": "crt_md_debug", "msvcprtd.lib": "crt_md_debug",
            "comsuppwd.lib": "crt_md_debug", "vcompd.lib": "crt_md_debug"},
            siblings=["comsuppw.lib", "vcomp.lib", "msvcrt.lib", "msvcprt.lib"])

    def test_atlmfc(self):
        self.check("atlmfc", {
            "atls.lib": "atl", "nafxcw.lib": "mfc_ansi",
            "nafxcwd.lib": "mfc_ansi_debug", "uafxcw.lib": "mfc_unicode",
            "uafxcwd.lib": "mfc_unicode_debug", "mfc140u.lib": "mfc_dll",
            "mfcs140u.lib": "mfc_dll", "mfc140ud.lib": "mfc_dll_debug",
            "MFCM140Ud.lib": "mfc_dll_debug", "afxnmcd.lib": "mfc_dll",
            "afxnmcdd.lib": "mfc_dll_debug"})

    def test_every_assignment_is_a_declared_shard_of_its_directory(self):
        for kind, names in (("crt", ["libcmt.lib", "libcmtd.lib", "msvcrt.lib",
                                     "msvcrtd.lib", "x.obj", "foo.lib",
                                     "libcpmt1.lib", "libcpmtd0.lib"]),
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

    def test_managed_and_pure_objects_are_excluded(self):
        self.assertTrue(crawl_vclibs.is_excluded("msvcurt.lib"))
        self.assertTrue(crawl_vclibs.is_excluded("msvcmrtd_netcore.lib"))
        self.assertTrue(crawl_vclibs.is_excluded(
            "pbinmode.obj", ["binmode.obj", "pbinmode.obj"]))
        self.assertIsNone(crawl_vclibs.is_excluded("pgort.lib", ["pgort.lib"]))

    def test_archive_unpacking_skips_import_objects(self):
        import tempfile
        coff = b"\x64\x86" + b"\x00" * 40
        imp = b"\x00\x00\xff\xff\x00\x00" + b"\x00" * 20

        def member(name, body):
            header = ("%-16s%-12s%-6s%-6s%-8s%-10d`\n" % (
                name, "0", "0", "0", "0", len(body))).encode()
            return header + body + (b"\n" if len(body) & 1 else b"")

        data = (b"!<arch>\n" + member("/", b"\x00" * 8) +
                member("//", b"long_member_name.obj/\n") +
                member("a.obj/", coff) + member("/0", coff) +
                member("MSVCP140.dll/", imp))
        with tempfile.TemporaryDirectory() as tmp:
            lib = os.path.join(tmp, "x.lib")
            with open(lib, "wb") as handle:
                handle.write(data)
            members, objects = crawl_vclibs.unpack_archive(lib)
            self.assertEqual((members, len(objects)), (3, 2))
            dest = os.path.join(tmp, "o")
            os.mkdir(dest)
            members, objects = crawl_vclibs.unpack_archive(lib, dest)
            self.assertEqual(sorted(os.listdir(dest)),
                             sorted(os.path.basename(o) for o in objects))
            self.assertTrue(any("long_member_name" in o for o in objects))


class RecipeTest(unittest.TestCase):
    def found(self):
        return {n: r for n, r in recipes.all_recipes().items()
                if n.startswith("MSVC_TOOLSETS_")}

    def test_one_recipe_per_toolset_and_shard(self):
        found = self.found()
        expected = sum(len(crawl_vclibs.shards_for(t))
                       for t in ("14.29", "14.44", "14.51"))
        self.assertEqual(len(found), expected)
        self.assertNotIn("MSVC_TOOLSETS_14.29_atl", found)
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
