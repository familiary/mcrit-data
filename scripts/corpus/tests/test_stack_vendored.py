"""The exact-name patterns of the XMRig, xmrig-proxy and xmr-stak recipes."""

import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from corpus import recipes
from corpus.recipes import _musl_dep_symbols as symbols
from corpus.recipes import _stack_vendored as vendored

FAMILIES = ("XMRig", "xmr-stak", "xmrig-proxy")

# Identifiers that were measured and deliberately not excluded; see the
# docstring of _stack_vendored.py for why each stays.
KEPT_ED25519 = ("ge_p1p1_to_p2", "ge_p1p1_to_p3", "_slide", "_load_3", "_load_4",
                "_ge_p1p1_to_p2", "_ge_p1p1_to_p3")
KEPT_MINGW_CRT = ("_feclearexcept", "_fesetround", "___mingw_has_sse")
KEPT_ARGON2 = ("rotr64",)


def _stack_recipes():
    return {name: recipe for name, recipe in recipes.all_recipes().items()
            if recipe.family in FAMILIES}


def _all_names(category=None):
    for recipe, table in vendored.NAMES.items():
        for name_category, names in table.items():
            if category in (None, name_category):
                for name in names:
                    yield recipe, name


class ExactNamesTest(unittest.TestCase):
    PATTERN = re.compile(vendored.exact_names(
        ["llhttp_init", "_llhttp_init",
         "std::_Node_if::`scalar deleting destructor'",
         "void std::__adjust_heap<long*>(long*) [clone .isra.0]"]))

    def test_matches_exactly_the_listed_names(self):
        for name in ("llhttp_init", "_llhttp_init",
                     "std::_Node_if::`scalar deleting destructor'",
                     "void std::__adjust_heap<long*>(long*) [clone .isra.0]"):
            self.assertTrue(self.PATTERN.search(name), name)

    def test_matches_nothing_else(self):
        for name in ("llhttp_init2", "__llhttp_init", "llhttp_initx",
                     "xllhttp_init", "llhttp_", "std::_Node_if::dtor",
                     "std::_Node_if::`scalar deleting destructor'2",
                     "void std::__adjust_heap<long*>(long*)",
                     "void std::__adjust_heap<long*>(long*) [clone .isra.1]",
                     "voidstd::__adjust_heap<long*>(long*) [clone .isra.0]",
                     "", "sub_401000"):
            self.assertIsNone(self.PATTERN.search(name), name)

    def test_regular_expression_characters_are_literal(self):
        pattern = re.compile(vendored.exact_names(["a<b>(c)*d"]))
        self.assertTrue(pattern.search("a<b>(c)*d"))
        self.assertIsNone(pattern.search("a<b>(c)d"))
        self.assertIsNone(pattern.search("a<b>(ccc)*d"))


class RecipeWiringTest(unittest.TestCase):
    def test_every_stack_recipe_has_a_table_and_the_table_has_no_stranger(self):
        self.assertEqual(sorted(vendored.NAMES), sorted(_stack_recipes()))

    def test_each_pattern_compiles_and_is_anchored(self):
        for name, recipe in _stack_recipes().items():
            for pattern in recipe.exclude_functions:
                re.compile(pattern)
            # The libuv/OpenSSL rules of the musl recipes are prefix rules;
            # the ones from this module are exact.
            for pattern in vendored.patterns(name):
                self.assertTrue(pattern.startswith("^(?:"), name)
                self.assertTrue(pattern.endswith(")$"), name)

    def test_the_vendored_patterns_come_from_the_table(self):
        for name, recipe in _stack_recipes().items():
            expected = vendored.patterns(name)
            if name.endswith("_musl"):
                # The libuv/OpenSSL rules are first and unchanged.
                self.assertEqual(recipe.exclude_functions,
                                 list(symbols.EXCLUDE) + expected, name)
            else:
                self.assertEqual(recipe.exclude_functions, expected, name)

    def test_one_pattern_per_non_empty_category(self):
        for name, table in vendored.NAMES.items():
            self.assertEqual(len(vendored.patterns(name)),
                             len([c for c in table if table[c]]), name)
            self.assertTrue(set(table) <= set(vendored.CATEGORIES), name)


class TableHygieneTest(unittest.TestCase):
    def test_names_are_sorted_and_unique(self):
        for recipe, table in vendored.NAMES.items():
            for category, names in table.items():
                self.assertEqual(list(names), sorted(set(names)),
                                 (recipe, category))

    def test_llhttp_names_are_llhttp_names(self):
        for recipe, name in _all_names("llhttp"):
            self.assertRegex(name, r"^_?(llhttp|llparse)_", (recipe, name))

    def test_rapidjson_names_are_rapidjson_names(self):
        for recipe, name in _all_names("rapidjson"):
            self.assertIn("rapidjson::", name, (recipe, name))
            # A header-only library: an exclusion by name is only sound for
            # an instantiation that no miner type takes part in.
            self.assertNotRegex(name, r"xmrig|xmrstak|randomx|Xmr", (recipe, name))

    def test_stdlib_names_are_the_standard_library_and_name_no_miner_type(self):
        for recipe, name in _all_names("stdlib"):
            self.assertRegex(name, r"\bstd::|__gnu_cxx::", (recipe, name))
            self.assertNotRegex(name, r"xmrig|xmrstak|randomx|Xmr|rapidjson",
                                (recipe, name))

    def test_ed25519_is_the_three_helpers_that_pass_the_literal_pichash_rule(self):
        # PicHash-equal to a same-named function of data/OpenSSL in every
        # function of the name in the recipe's images, or not listed. Only
        # these three names, only in the recipes below; the other 26 names of
        # the bundled ed25519 set that OpenSSL lacks are never listed.
        expected = {"XMRig_6.25.0": ("slide",),
                    "XMRig_6.25.0-gpu-hwloc": ("slide",),
                    "xmrig-proxy_6.26.0": ("slide",),
                    "XMRig_6.25.0_msvc": ("load_3", "load_4"),
                    "XMRig_6.25.0-gpu-hwloc_msvc": ("load_3", "load_4"),
                    "xmrig-proxy_6.26.0_msvc": ("load_3", "load_4")}
        found = {}
        for recipe, table in vendored.NAMES.items():
            if table.get("ed25519"):
                found[recipe] = tuple(table["ed25519"])
        self.assertEqual(found, expected)

    def test_argon2_names_are_the_measured_helpers(self):
        measured = {"xor_block", "copy_block", "blake2b_init0",
                    "blake2b_increment_counter", "b64_char_to_byte",
                    "b64_byte_to_char", "decode_decimal"}
        for recipe, name in _all_names("argon2"):
            self.assertIn(name, measured, (recipe, name))

    def test_crt_is_the_one_msvc_startup_function(self):
        for recipe, name in _all_names("crt"):
            self.assertEqual(name, "__scrt_common_main_seh")
            self.assertIn("_msvc", recipe)

    def test_identifiers_kept_on_purpose_are_in_no_table(self):
        kept = set(KEPT_ED25519 + KEPT_MINGW_CRT + KEPT_ARGON2)
        for recipe, name in _all_names():
            self.assertNotIn(name, kept, (recipe, name))

    def test_the_miners_own_code_is_not_matched(self):
        for recipe in vendored.NAMES:
            matched = [re.compile(p) for p in vendored.patterns(recipe)]
            for name in ("xmrig::App::exec()", "randomx_calculate_hash",
                         "argon2_hash", "fill_segment_64", "sph_echo512",
                         "keccak_finish", "cn_hash_ctx", "main", "memcpy",
                         "ge_p1p1_to_p3", "_ge_p1p1_to_p3", "_slide", "rotr64", "fe_mul", "sc_reduce32",
                         "_feclearexcept", "llhttp_execute_extra",
                         "rapidjson::Document::Parse()",
                         "std::vector<int, std::allocator<int> >::push_back(int const&)",
                         "void xmrig::cryptonight_single_hash<(xmrig::Algorithm::Id)1>()"):
                self.assertFalse(any(rx.search(name) for rx in matched),
                                 (recipe, name))

    def test_each_category_matches_its_own_names(self):
        for recipe, table in vendored.NAMES.items():
            for category, names in table.items():
                rx = re.compile(vendored.exact_names(names))
                for name in names:
                    self.assertTrue(rx.search(name), (recipe, name))


@unittest.skipUnless(
    all(os.path.exists(os.path.join(ROOT, "data", family, "provenance.json"))
        for family in FAMILIES),
    "data/XMRig, data/xmr-stak and data/xmrig-proxy are not all checked out")
class ProvenanceCountsTest(unittest.TestCase):
    def _entries(self):
        for family in FAMILIES:
            path = os.path.join(ROOT, "data", family, "provenance.json")
            with open(path) as handle:
                for key, entry in json.load(handle).items():
                    yield key, entry

    def _recipe_of(self, key):
        # A version may carry a variant suffix (XMRig 6.25.0-gpu-hwloc).
        match = re.match(r"(.+?)_([\d.]+(?:-[a-z-]+)?)_(gcc13|mingw13|msvc143|musl11)_(x86|x64)_", key)
        family, version, toolchain, arch = match.groups()
        name = "%s_%s" % (family, version)
        if toolchain == "mingw13" and family == "xmr-stak":
            name += "_mingw"
        elif toolchain == "gcc13":
            name += "_linux" + ("_x86" if family == "xmr-stak" and arch == "x86" else "")
        elif toolchain == "msvc143":
            name += "_msvc" + ("_x86" if family == "xmr-stak" and arch == "x86" else "")
        elif toolchain == "musl11":
            name += "_musl"
        return name

    def test_kept_plus_excluded_is_the_count_before_exclusion(self):
        seen = 0
        for key, entry in self._entries():
            seen += 1
            self.assertEqual(entry["num_functions_before_exclusion"],
                             entry["num_functions"] + entry["excluded_function_count"], key)
            self.assertGreater(entry["excluded_function_count"], 0, key)
        # 21 images, then the six XMRig 6.25.0-gpu-hwloc images and the
        # xmr-stak Linux x86 image.
        self.assertEqual(seen, 28)

    def test_each_record_carries_its_recipes_patterns(self):
        for key, entry in self._entries():
            recipe = recipes.get(self._recipe_of(key))
            self.assertEqual(entry["exclude_functions"], recipe.exclude_functions, key)

    def test_the_musl_images_keep_their_dependency_exclusion(self):
        seen = 0
        for key, entry in self._entries():
            if "_musl11_" not in key:
                continue
            seen += 1
            self.assertEqual(entry["exclude_functions"][:2], symbols.EXCLUDE, key)
            self.assertGreater(entry["excluded_function_count"], 19000, key)
        self.assertEqual(seen, 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
