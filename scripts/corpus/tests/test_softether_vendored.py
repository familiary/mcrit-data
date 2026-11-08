"""The exact-name patterns of the SoftEther Windows (MSVC) recipe."""

import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from corpus import recipes
from corpus.recipes import _softether_vendored as vendored

RECIPE = "softether_vpn_stable_4.44_msvc"

# Identifiers that were measured and deliberately not excluded; see the
# docstring of _softether_vendored.py for why each stays.
KEPT_ZLIB = ("compress", "putShortMSB", "adler32_combine", "adler32_combine64",
             "crc32_combine64", "_tr_init", "_tr_flush_bits", "deflate",
             "inflate", "crc32", "deflateEnd", "inflateEnd")
KEPT_SODIUM = ("poly1305_blocks", "chacha20_encrypt_bytes",
               "crypto_onetimeauth_poly1305_init")
# Import thunks and inline helpers that share a PicHash with the OpenSSL and
# zlib DLLs without being the library's code.
THUNKS = ("Sleep", "_Sleep@4", "WSAStartup", "_WSAStartup@8", "send", "recv",
          "strcpy_s", "wcstombs", "_wcstombs", "getenv", "MarkAllocaS",
          "WspiapiGetAddrInfo", "fwrite", "_fwrite")


def _all_names(category=None):
    for name_category in vendored.CATEGORIES:
        if category in (None, name_category):
            for name in vendored.NAMES[name_category]:
                yield name_category, name


class ExactNamesTest(unittest.TestCase):
    NAMES = ["ASN1_INTEGER_new", "_ASN1_INTEGER_new", "iEnc128",
             "a<b>(c)*d", "std::x::`scalar deleting destructor'", "a", "ab"]
    PATTERN = re.compile(vendored.exact_names(NAMES))

    def test_matches_exactly_the_listed_names(self):
        for name in self.NAMES:
            self.assertTrue(self.PATTERN.search(name), name)

    def test_matches_nothing_else(self):
        for name in ("ASN1_INTEGER_new2", "__ASN1_INTEGER_new", "xASN1_INTEGER_new",
                     "ASN1_INTEGER_ne", "ASN1_INTEGER_", "_iEnc128x", "iEnc12",
                     "a<b>(c)d", "a<b>(ccc)*d", "abc", "b", "", "sub_401000",
                     "std::x::`scalar deleting destructor'2"):
            self.assertIsNone(self.PATTERN.search(name), name)

    def test_the_tree_expression_is_the_plain_alternation(self):
        plain = re.compile(r"^(?:%s)$" % "|".join(
            re.escape(name) for name in sorted(set(self.NAMES))))
        for name in self.NAMES + ["", "abc", "ab_", "_a", "iEnc1280", "aa"]:
            self.assertEqual(bool(self.PATTERN.search(name)),
                             bool(plain.search(name)), name)


class RecipeWiringTest(unittest.TestCase):
    def test_the_recipe_carries_the_patterns_of_the_table(self):
        recipe = recipes.get(RECIPE)
        self.assertEqual(recipe.exclude_functions, vendored.patterns())
        self.assertEqual(len(recipe.exclude_functions), len(vendored.CATEGORIES))

    def test_each_pattern_compiles_and_is_anchored(self):
        for pattern in vendored.patterns():
            self.assertTrue(pattern.startswith("^"))
            self.assertTrue(pattern.endswith("$"))
            re.compile(pattern)

    def test_the_linux_recipes_exclude_nothing(self):
        for name, recipe in recipes.all_recipes().items():
            if recipe.family == "SoftEtherVPN" and name != RECIPE:
                self.assertEqual(recipe.exclude_functions, [], name)

    def test_every_category_has_a_table(self):
        self.assertEqual(sorted(vendored.NAMES), sorted(vendored.CATEGORIES))
        for category in vendored.CATEGORIES:
            self.assertTrue(vendored.NAMES[category], category)


class TableHygieneTest(unittest.TestCase):
    def test_names_are_sorted_and_unique(self):
        for category, names in vendored.NAMES.items():
            self.assertEqual(list(names), sorted(set(names)), category)

    def test_no_name_is_in_two_categories(self):
        seen = {}
        for category, name in _all_names():
            self.assertNotIn(name, seen, (category, seen.get(name)))
            seen[name] = category

    def test_each_category_matches_its_own_names_and_only_those(self):
        for category in vendored.CATEGORIES:
            rx = re.compile(vendored.exact_names(vendored.NAMES[category]))
            for name in vendored.NAMES[category]:
                self.assertTrue(rx.search(name), (category, name))
            others = [n for c, n in _all_names() if c != category]
            for name in others[::7]:
                self.assertIsNone(rx.search(name), (category, name))

    def test_x86_names_carry_the_c_decoration_beside_the_x64_spelling(self):
        names = set(vendored.NAMES["openssl"])
        self.assertIn("ASN1_INTEGER_new", names)
        self.assertIn("_ASN1_INTEGER_new", names)

    def test_intel_aes_names_are_the_libintelaes_exports(self):
        rx = re.compile(r"^_?(intel_AES_(enc|dec|encdec)\d+(_CBC|_CTR)?"
                        r"|i(Enc|Dec)(ExpandKey)?\d+(_CBC|_CTR)?"
                        r"|check_for_aes_instructions)$")
        names = vendored.NAMES["intel_aes"]
        self.assertEqual(len(names), 58)
        for name in names:
            self.assertRegex(name, rx)

    def test_legacy_provider_names_use_the_reserved_prefix(self):
        names = vendored.NAMES["openssl_legacy"]
        self.assertEqual(len(names), 60)
        for name in names:
            self.assertRegex(name, r"^_?ossl_(prov_cipher_hw_|legacy_provider_init)")

    def test_zlib_is_the_eleven_identifiers_with_a_pichash_match(self):
        natural = {name.lstrip("_") for name in vendored.NAMES["zlib"]}
        self.assertEqual(natural, {
            "adler32", "crc32_combine", "deflateInit_", "fixedtables",
            "get_crc_table", "inflateInit_", "tr_static_init", "uncompress",
            "zError", "zlibCompileFlags", "zlibVersion"})

    def test_libsodium_is_the_two_identifiers_with_a_pichash_match(self):
        natural = {name.lstrip("_") for name in vendored.NAMES["libsodium"]}
        self.assertEqual(natural, {"crypto_aead_chacha20poly1305_ietf_decrypt",
                                   "poly1305_update"})

    def test_identifiers_kept_on_purpose_are_in_no_table(self):
        kept = set(KEPT_ZLIB + KEPT_SODIUM)
        for category, name in _all_names():
            self.assertNotIn(name.lstrip("_"), kept, (category, name))

    def test_import_thunks_and_inline_helpers_are_in_no_table(self):
        for category, name in _all_names():
            self.assertNotIn(name, THUNKS, (category, name))
            self.assertNotRegex(name, r"@\d+$", (category, name))
            self.assertNotRegex(name, r"^_?(Wspiapi|MarkAllocaS)", (category, name))

    def test_softethers_own_code_is_not_matched(self):
        matched = [re.compile(p) for p in vendored.patterns()]
        for name in ("main", "WinMain", "CedarPch", "AesEncrypt", "AesNewKey",
                     "AesEncryptWithIntel", "IsIntelAesNiSupported",
                     "Sha1", "Md5", "NewRpcEnumHub", "CmMain", "SiWriteConfigurationFile",
                     "json_array_add", "parse_value", "__delayLoadHelper2",
                     "__imp_load_ChangeServiceConfig2W", "_except_handler3", ""):
            self.assertFalse(any(rx.search(name) for rx in matched), name)


@unittest.skipUnless(
    os.path.exists(os.path.join(ROOT, "data", "SoftEtherVPN", "provenance.json")),
    "data/SoftEtherVPN is not checked out")
class ProvenanceCountsTest(unittest.TestCase):
    def _entries(self):
        path = os.path.join(ROOT, "data", "SoftEtherVPN", "provenance.json")
        with open(path) as handle:
            return json.load(handle)

    def test_kept_plus_excluded_is_the_count_before_exclusion(self):
        seen = 0
        for key, entry in self._entries().items():
            if "_msvc143_" not in key:
                continue
            seen += 1
            self.assertEqual(entry["num_functions_before_exclusion"],
                             entry["num_functions"] + entry["excluded_function_count"],
                             key)
            self.assertGreater(entry["excluded_function_count"], 2000, key)
        self.assertEqual(seen, 8)

    def test_each_msvc_record_carries_the_recipes_patterns(self):
        recipe = recipes.get(RECIPE)
        for key, entry in self._entries().items():
            if "_msvc143_" in key:
                self.assertEqual(entry["exclude_functions"],
                                 recipe.exclude_functions, key)

    def test_the_linux_records_carry_no_exclusion(self):
        seen = 0
        for key, entry in self._entries().items():
            if "_gcc14_" in key:
                seen += 1
                self.assertNotIn("excluded_function_count", entry, key)
                self.assertNotIn("exclude_functions", entry, key)
        self.assertEqual(seen, 7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
