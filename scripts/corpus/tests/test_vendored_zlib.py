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
            # The UltraVNC MinGW recipes carry a second pattern, for the two
            # ReactOS comsupp functions compiled into uvnc_settings.
            expected = 2 if recipe.family == "UltraVNC" and name.endswith("_mingw") else 1
            self.assertEqual(len(recipe.exclude_functions), expected, name)
            for pattern in recipe.exclude_functions:
                re.compile(pattern)

    def test_the_comsupp_pattern_names_only_the_two_conversion_functions(self):
        pattern = re.compile(
            recipes.get("UltraVNC_1.8.3.1_mingw").exclude_functions[1])
        for name in ("_com_util::ConvertStringToBSTR(char const*)",
                     "_com_util::ConvertBSTRToString(wchar_t*)@4",
                     "_com_util::ConvertBSTRToString(wchar_t*) (.part.0)"):
            self.assertTrue(pattern.search(name), name)
        for name in ("UPnP::OpenPorts(bool)", "_com_raise_error(long, IErrorInfo*)",
                     "_bstr_t::Data_t::Data_t(char const*)", "deflate",
                     "x_com_util::ConvertStringToBSTR(char const*)"):
            self.assertIsNone(pattern.search(name), name)

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
