"""The zlib name patterns of the UltraVNC and TightVNC recipes."""

import re
import unittest

from corpus import recipes
from corpus.recipes._vendored_zlib import zlib_functions


class ZlibPatternTest(unittest.TestCase):
    PATTERN = re.compile(zlib_functions(["deflate", "_tr_init", "crc32_z"]))

    def test_matches_exact_names_with_x86_and_gcc_decoration(self):
        for name in ("deflate", "_deflate", "_tr_init", "__tr_init",
                     "crc32_z", "_crc32_z", "crc32_z.constprop.0"):
            self.assertTrue(self.PATTERN.search(name), name)

    def test_matches_nothing_else(self):
        for name in ("deflate_fast", "deflateEnd", "ZSTD_deflate",
                     "lzma_crc32_z", "Foo::deflate(int)", "deflate@4",
                     "", "sub_401000"):
            self.assertIsNone(self.PATTERN.search(name), name)


class RecipePatternsTest(unittest.TestCase):
    def test_the_vnc_recipes_carry_one_compiling_pattern_each(self):
        found = {name: recipe for name, recipe in recipes.all_recipes().items()
                 if recipe.family in ("UltraVNC", "TightVNC")}
        self.assertEqual(len(found), 11)
        for name, recipe in found.items():
            self.assertEqual(len(recipe.exclude_functions), 1, name)
            re.compile(recipe.exclude_functions[0])

    def test_a_pattern_spares_the_programs_own_and_other_libraries_code(self):
        pattern = re.compile(
            recipes.get("UltraVNC_1.8.3.1_msvc").exclude_functions[0])
        for name in ("ClientConnection::Run(void)", "vncMenu::vncMenu",
                     "ZSTD_compress", "lzma_lz_decoder_init",
                     "crypto_generichash_blake2b_update", "main",
                     "std::vector<int>::push_back"):
            self.assertIsNone(pattern.search(name), name)
        for name in ("deflate", "_inflate_table", "_tr_flush_block"):
            self.assertTrue(pattern.search(name), name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
