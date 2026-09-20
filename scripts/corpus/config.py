"""Paths and constants shared by the corpus tooling."""

import os

# scripts/corpus/config.py -> repository root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(REPO_ROOT, "data")

# Everything that is not committed lives here (see .gitignore).
WORK_DIR = os.environ.get("MCRIT_DATA_WORK_DIR", os.path.join(REPO_ROOT, "build"))
DOWNLOAD_DIR = os.path.join(WORK_DIR, "downloads")
SOURCE_DIR = os.path.join(WORK_DIR, "sources")
ARTIFACT_DIR = os.path.join(WORK_DIR, "artifacts")
REPORT_DIR = os.path.join(WORK_DIR, "smda")

# The two configuration hashes every .mcrit file in this repository carries.
# MCRIT can only reuse minhashes across exports when these match, so a new
# export that disagrees with them is unusable and must abort the run.
EXPECTED_MINHASH_CONFIG = "d8e7556837291ca72b3e70ebf4c328286a418bc761c63385ee61b0a767fcc99d"
EXPECTED_SHINGLER_CONFIG = "7ae53d3b2514730a4d48f993a3e4cd6c6d4a5ca26f93bbed98e0f498295552de"

# GitHub refuses pushes containing blobs above 100 MB (cf. commit 8151d81).
MAX_COMMITTED_FILE_SIZE = 100 * 1024 * 1024

# A sample below this many functions is almost certainly a build accident
# (empty stub, wrong artefact picked up) rather than usable reference data.
MIN_USEFUL_FUNCTIONS = 8

# Shellcode is judged on instructions instead. Hand-tuned position-independent
# code legitimately has very few function boundaries - sRDI's loader compiles
# to two functions covering ~730 instructions, because MSVC /O1 inlines the
# rest - and a couple of large functions still carry perfectly good minhashes.
# Counting functions there would reject usable data.
MIN_USEFUL_BLOB_INSTRUCTIONS = 100

# Below this many instructions, two families sharing a PicHash says nothing.
# A three-instruction thunk that loads an import and jumps has one shape, and
# every library that calls that import compiles to it; a getter that returns a
# member is "mov eax, [ecx+N]; ret" in every code base there is. Measured over
# this corpus the floor is the difference between a check that cannot be used
# and one that can: 754 raw hits across ~281,000 functions, of which only 84
# survive at ten instructions - and those are mostly legitimate C++ template
# instantiations of the same header in different projects. The real leaks the
# filter is for (libgcc's division helpers, MSVC startup glue, ATL) all sit
# well above the floor, so raising it costs no detection.
MIN_CROSS_FAMILY_INSTRUCTIONS = 10


def ensure_dirs():
    for path in (DOWNLOAD_DIR, SOURCE_DIR, ARTIFACT_DIR, REPORT_DIR):
        os.makedirs(path, exist_ok=True)
