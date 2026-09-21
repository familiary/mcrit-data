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

# Functions shorter than this are left out when judging whether a build kept
# its symbols. They are not left out of the corpus - only out of that one
# ratio.
#
# The symbol check asks "did this build strip its symbols". Counting every
# function answered a different question on MSVC x86 C++ builds, and answered
# it wrongly: nlohmann_json sat at 43% named, BlackBone at 49%, and
# cryptopp 8.9.0 was refused outright at 38% - while the same source built
# for x64 names 53%, 100% and 66% of its functions. Nothing was stripped.
#
# What separates the two architectures is one- and two-instruction compiler
# fragments. Of nlohmann_json x86's 2937 unnamed functions, every single one
# is a single instruction; of BlackBone x86's 932, 795 are two instructions
# and carry 2280 of that artefact's 93,948 instructions between them. x86
# C++ exception handling emits these per-function and the PDB records no
# symbol at their addresses; x64's table-driven unwinding emits none, which
# is why every C++ family in this corpus shows the gap (7-Zip -23 points,
# protobuf -24, abseil -14, re2 -13, nlohmann_json -9, BlackBone -51) and
# every C family shows none at all - libcurl, libxml2, libuv, liblzma,
# pcre2, libsodium and wolfSSL all name 100% on both architectures.
#
# Measured at three instructions, every artefact in this corpus names 100%
# of its functions except BlackBone x86 at 86%. That is a far sharper
# instrument than the raw ratio was: a build that really did strip its
# symbols names nothing at any floor.
#
# Those figures are measured on the committed reports, i.e. after compiler
# runtime has been dropped. The check runs before that pass, and glue is
# almost entirely named, so the ratio it sees is the higher one - the
# numbers above are a lower bound.
MIN_NAMED_SAMPLE_INSTRUCTIONS = 3


def ensure_dirs():
    for path in (DOWNLOAD_DIR, SOURCE_DIR, ARTIFACT_DIR, REPORT_DIR):
        os.makedirs(path, exist_ok=True)
