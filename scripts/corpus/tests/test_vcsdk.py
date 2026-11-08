"""Tests for the SDK-CAB crawler behind the MSVC_VC10 recipe."""

import os
import re
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from corpus import crawl_vcsdk, recipes


def _compile3(machine, fe, be, producer=b"Microsoft (R) Optimizing Compiler"):
    payload = struct.pack("<H", 0x113C) + struct.pack(
        "<IHHHHHHHHH", 1, machine, fe[0], fe[1], fe[2], 0,
        be[0], be[1], be[2], 0) + producer + b"\x00"
    return struct.pack("<H", len(payload)) + payload


class KeyMappingTest(unittest.TestCase):
    def map(self, key):
        for pattern, ext in crawl_vcsdk.KEY_PATTERNS:
            match = pattern.match(key)
            if match:
                return "%s.%s" % (match.group("name"), ext or match.group("ext"))
        return None

    def test_installer_keys_map_to_file_names(self):
        guid = ".3643236F_FC70_11D3_A536_0090278A1BB8"
        self.assertEqual(self.map(
            "FL_libcmt_lib_74650_74650_amd64_ln" + guid), "libcmt.lib")
        self.assertEqual(self.map("FL_libcpmt_lib_x64"), "libcpmt.lib")
        self.assertEqual(self.map("FL_nohetoc_obj_amd64_ln"), "nohetoc.obj")
        self.assertEqual(self.map("F_CENTRAL_msvcr100_x64"), "msvcr100.dll")
        self.assertEqual(self.map("F_PDB_msvcp100d_x64"), "msvcp100d.pdb")
        self.assertIsNone(self.map("FL_link_exe_105145_105145_amd64_ln" + guid))


class CompilerRecordTest(unittest.TestCase):
    def test_reads_machine_and_versions(self):
        data = b"junk" + _compile3(0xD0, (16, 0, 30319), (16, 0, 30319)) * 2
        counts = crawl_vcsdk.compiler_records(data)
        self.assertEqual(counts, {("x64 (AMD64)", "16.0.30319", "16.0.30319"): 2})


class RecipeTest(unittest.TestCase):
    def test_recipe_pins_the_image_and_keeps_the_runtime(self):
        recipe = recipes.all_recipes()["MSVC_VC10_10.0.30319"]
        self.assertFalse(recipe.drop_crt_glue)
        self.assertTrue(recipe.dedupe_functions)
        self.assertEqual(recipe.toolchains, ["msvc_x64"])
        self.assertTrue(re.fullmatch(r"[0-9a-f]{64}",
                                     crawl_vcsdk_recipe_sha()))
        components = [a.component for a in recipe.artifacts]
        self.assertEqual(len(components), len(set(components)))
        self.assertIn("libcmt", components)
        self.assertIn("msvcr100", components)


def crawl_vcsdk_recipe_sha():
    from corpus.recipes import msvc_vc10
    return msvc_vc10.ISO_SHA256


if __name__ == "__main__":
    unittest.main()
