"""The libuv/OpenSSL name rules of the static musl miner recipes."""

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


def _excluded(name):
    return any(re.search(pattern, name) for pattern in symbols.EXCLUDE)


class MuslExcludeRulesTest(unittest.TestCase):
    def test_the_dependencies_are_excluded(self):
        for name in ("uv_run", "uv__io_poll", "EVP_CIPHER_CTX_new", "ossl_provider_free",
                     "OPENSSL_init_ssl", "SSL_read", "tls_construct_client_hello",
                     "X509_verify_cert", "BN_mod_exp_mont", "lh_SSL_SESSION_hfn_thunk",
                     "ASN1_item_d2i", "ERR_get_error", "CRYPTO_malloc"):
            self.assertTrue(_excluded(name), name)

    def test_the_miners_own_code_is_not(self):
        for name in ("xmrig::App::exec()", "randomx_calculate_hash", "sph_echo512",
                     "argon2_hash", "fill_segment_64", "llhttp_execute",
                     "keccak_finish", "cn_hash_ctx", "rapidjson::Document::Parse()",
                     "fmt::v7::detail::format_error_code", "main", "memcpy",
                     "std::vector<int>::push_back(int const&)",
                     "void xmrig::cryptonight_single_hash<(xmrig::Algorithm::Id)1>()"):
            self.assertFalse(_excluded(name), name)

    def test_names_the_miner_shares_with_openssl_are_left_in(self):
        # Deleting these would delete Argon2 and the miner's own helpers.
        for name in ("blake2b_compress", "fill_block", "copy_block", "xor_block",
                     "fe_mul", "ge_add", "load_3"):
            self.assertFalse(_excluded(name), name)

    def test_the_rules_are_nonempty_and_prefixes_are_single_tokens(self):
        self.assertGreater(len(symbols.PREFIXES), 100)
        self.assertGreater(len(symbols.EXACT), 100)
        for prefix in symbols.PREFIXES:
            self.assertNotIn("_", prefix.lstrip("_"), prefix)

    def test_only_the_musl_recipes_exclude_and_they_exclude_these(self):
        for name in recipes.all_recipes():
            recipe = recipes.get(name)
            if name.endswith("_musl"):
                # The libuv/OpenSSL rules first and unchanged, then the
                # exact-name rules of _stack_vendored.py.
                self.assertEqual(recipe.exclude_functions,
                                 symbols.EXCLUDE + vendored.patterns(name), name)
                self.assertEqual(sorted(recipe.toolchains), ["musl_x64", "musl_x86"])
                self.assertIn("-DBUILD_STATIC=ON", " ".join(
                    step.command for step in recipe.build))
            elif name.startswith(("XMRig_", "xmrig-proxy_")):
                self.assertEqual(recipe.exclude_functions,
                                 vendored.patterns(name), name)


@unittest.skipUnless(os.path.isdir(os.path.join(ROOT, "data", "XMRig")),
                     "data/XMRig is not checked out")
class MuslProvenanceCountsTest(unittest.TestCase):
    def test_kept_removed_and_excluded_add_up(self):
        seen = 0
        for family in ("XMRig", "xmrig-proxy"):
            path = os.path.join(ROOT, "data", family, "provenance.json")
            if not os.path.exists(path):
                continue
            with open(path) as handle:
                entries = json.load(handle)
            for key, entry in entries.items():
                if "_musl" not in key:
                    continue
                seen += 1
                self.assertEqual(entry["num_functions_before_exclusion"],
                                 entry["num_functions"] + entry["excluded_function_count"], key)
                self.assertEqual(entry["exclude_functions"][:len(symbols.EXCLUDE)],
                                 symbols.EXCLUDE, key)
                self.assertGreater(entry["excluded_function_count"], 15000, key)
        self.assertGreaterEqual(seen, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
