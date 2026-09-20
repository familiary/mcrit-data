"""SQLite - almost certainly the most widely embedded database on Windows.

Built from the official amalgamation, which is a single sqlite3.c and is how
essentially every application that embeds SQLite consumes it. Three versions
spanning the FTS5 boundary: FTS5 landed in 3.9.0, so a 3.8.x build has a
materially different function set from anything after it.

Upstream publishes a SHA3-256 per file on its download page; the SHA-256
recorded here was taken from the fetched archive.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# The amalgamation ships no build system, which is the point of it: one
# translation unit compiled straight into the consuming project. Building it
# as a DLL with the default feature set is the closest analogue.
_BUILD = ("{cc} -O2 -shared -o sqlite3.dll sqlite3.c "
          "'-DSQLITE_API=__declspec(dllexport)' "
          "-DSQLITE_ENABLE_FTS5 -DSQLITE_ENABLE_RTREE -DSQLITE_ENABLE_JSON1")

# 3.8.x predates FTS5, so asking for it would fail the build.
_BUILD_LEGACY = ("{cc} -O2 -shared -o sqlite3.dll sqlite3.c "
                 "'-DSQLITE_API=__declspec(dllexport)' "
                 "-DSQLITE_ENABLE_FTS4 -DSQLITE_ENABLE_RTREE")


_FLAGS = "-O2, FTS5/RTREE/JSON1 enabled"
# 3.8.x predates FTS5 and its build line asks for neither FTS5 nor JSON1, so
# the family cannot state one feature set: the pre-FTS5 build genuinely has a
# different function set, which is the reason it is covered at all.
_FLAGS_LEGACY = "-O2, FTS4/RTREE enabled (no FTS5, no JSON1)"


def _sqlite(version, year, code, sha256, build=_BUILD, build_flags=_FLAGS):
    return Recipe(
        family="sqlite3",
        version=version,
        upstream="https://sqlite.org/",
        license="public domain",
        source=Source(
            url="https://sqlite.org/%s/sqlite-amalgamation-%s.zip" % (year, code),
            sha256=sha256),
        build=[BuildStep(build)],
        artifacts=[Artifact(path="sqlite3.dll", component="sqlite3.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags=build_flags,
        notes="Compile-time feature flags change the emitted function set more "
              "than minor versions do, so one profile is held constant across "
              "the post-FTS5 builds; 3.8.11.1 predates FTS5 and is built with "
              "FTS4 and RTREE only.",
    )


RECIPES = {
    # Pre-FTS5, the long tail of embedded SQLite from the mid-2010s.
    "sqlite3_3.8.11.1": _sqlite(
        "3.8.11.1", "2015", "3081101",
        "a3b0c07d1398d60ae9d21c2cc7f9be6b1bc5b0168cd94c321ede9a0fce2b3cd7",
        build=_BUILD_LEGACY, build_flags=_FLAGS_LEGACY),
    # The generated-columns/UPSERT era, very widely shipped.
    "sqlite3_3.31.1": _sqlite(
        "3.31.1", "2020", "3310100",
        "f3c79bc9f4162d0b06fa9fe09ee6ccd23bb99ce310b792c5145f87fbcc30efca"),
    # Current.
    "sqlite3_3.50.4": _sqlite(
        "3.50.4", "2025", "3500400",
        "1d3049dd0f830a025a53105fc79fd2ab9431aea99e137809d064d8ee8356b032"),
}
