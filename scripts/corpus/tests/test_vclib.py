"""crawl_vclib: shard table and startup-object selection."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from corpus import crawl_vclib
from corpus.recipes.msvc_oldtoolsets import RECIPES, SHARDS, TOOLSETS


def test_every_recipe_shard_is_defined():
    assert set(SHARDS) <= set(crawl_vclib.SHARDS)
    for recipe in RECIPES.values():
        for artifact in recipe.artifacts:
            assert artifact.component in crawl_vclib.SHARDS


def test_shards_do_not_share_libraries():
    seen = {}
    for shard, libs in crawl_vclib.SHARDS.items():
        for lib in libs or []:
            assert lib not in seen, (lib, shard, seen[lib])
            seen[lib] = shard


def test_startup_skips_pure_twins(tmp_path):
    lib = tmp_path / "lib" / "x64"
    lib.mkdir(parents=True)
    for name in ("binmode.obj", "pbinmode.obj", "setargv.obj", "pgobootrun.obj"):
        (lib / name).write_bytes(b"")
    toolset = {"layout": "msvc", "dir": str(tmp_path), "root": str(tmp_path)}
    _, objs = crawl_vclib.shard_inputs(toolset, "x64", "startup")
    names = sorted(os.path.basename(o) for o in objs)
    assert names == ["binmode.obj", "pgobootrun.obj", "setargv.obj"]


def test_one_recipe_per_toolset():
    assert len(RECIPES) == len(TOOLSETS)
