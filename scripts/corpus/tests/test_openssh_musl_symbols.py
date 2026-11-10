"""The generated exact-name tables of the static musl OpenSSH recipes."""

import re

from scripts.corpus.recipes import _openssh_musl_symbols as symbols
from scripts.corpus.recipes import openssh


def test_trie_regex_matches_exactly_its_names():
    for label, names in symbols.EXACT.items():
        rx = re.compile(symbols._trie(names))
        assert all(rx.search(n) for n in names), label
        # a prefix, an extension and a neighbour of a name are not matches
        for n in names[:200]:
            assert not rx.search(n + "x"), (label, n)
            assert not rx.search(n[:-1]) or n[:-1] in names, (label, n)


def test_collisions_are_never_excluded():
    excluded = [re.compile(p) for p in symbols.EXCLUDE]
    for label, names in symbols.COLLISIONS.items():
        for name in names:
            assert not any(rx.search(name) for rx in excluded), (label, name)


def test_a_name_is_in_one_table_only():
    seen = {}
    for label, names in symbols.EXACT.items():
        for name in names:
            assert seen.setdefault(name, label) == label, name


def test_musl_recipes_carry_the_tables_and_both_toolchains():
    for name in ("OpenSSH_9.6p1_musl", "OpenSSH_10.6p2_musl"):
        recipe = openssh.RECIPES[name]
        assert recipe.toolchains == ["musl_x86", "musl_x64"]
        assert recipe.exclude_functions == symbols.EXCLUDE
        assert recipe.exclude_functions and len(recipe.exclude_functions) == 3
