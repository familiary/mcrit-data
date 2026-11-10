import re

from scripts.corpus.recipes import _win32openssh_zlib as zlib_table
from scripts.corpus.recipes import get


def test_pattern_is_exact():
    pattern = re.compile(zlib_table.zlib_functions())
    assert pattern.search("deflate") and pattern.search("_tr_align")
    assert not pattern.search("deflate_foo")
    assert not pattern.search("ssh_deflate")
    assert not pattern.search("_deflate")


def test_tiers_cover_every_name():
    for arch in ("x64", "x86"):
        assert set(zlib_table.TIERS[arch]) == set(zlib_table.NAMES)
        assert set(zlib_table.TIERS[arch].values()) <= {"P", "W", "N"}


def test_recipe_uses_the_table():
    recipe = get("OpenSSH_Win32_10.4.0.0_msvc")
    assert recipe.exclude_functions == [zlib_table.zlib_functions()]
