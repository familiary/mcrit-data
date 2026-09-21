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
# function answered a different question, and cryptopp 8.9.0 x86 was refused
# outright over it at 38% named - a build that had stripped nothing, and
# whose 7844 named functions are within 3% of what the MinGW build of the
# same tag names.
#
# Two kinds of function with no symbol to keep were being counted.
#
# The first was a defect in the recipes rather than in the check, and is
# fixed there: seven MSVC links omitted /INCREMENTAL:NO, and an
# incrementally linked image reaches each function through a table of
# one-instruction jump thunks. That table is unmistakable once looked at -
# in nlohmann_json 3.12.0 x64 it is 2866 entries, exactly five bytes apart,
# running unbroken from base+0x1005, with no other function inside its
# span. Those artefacts are being rebuilt without it.
#
# The second is real and stays: x86 C++ exception handling emits an
# __ehhandler$ or __unwindfunclet$ fragment per function - "mov eax,
# <scopetable>; jmp <handler>" or "lea ...; jmp ..." - and the PDB records
# no symbol at those addresses. BlackBone x86 has 795 of them, carrying
# 2280 of that artefact's 93,948 instructions; BlackBone x64 has none at
# all and names 1628 of 1628 functions, because x64 unwinding is
# table-driven. Counting them measures how much C++ a project contains, on
# which architecture, rather than whether this build was stripped.
#
# Three instructions is above both kinds and below anything else: measured
# over the committed reports, every artefact in the corpus names 100% of
# the functions at or above it, except BlackBone x86 at 86%. That is a
# sharper instrument than the raw ratio was, not a weaker one - a build
# that really did strip its symbols names nothing at any floor.
#
# Those figures come from the committed reports, i.e. after compiler
# runtime has been dropped. The check runs before that pass, and glue is
# almost entirely named, so the ratio it sees is the higher one - the
# numbers above are a lower bound.
MIN_NAMED_SAMPLE_INSTRUCTIONS = 3


def ensure_dirs():
    for path in (DOWNLOAD_DIR, SOURCE_DIR, ARTIFACT_DIR, REPORT_DIR):
        os.makedirs(path, exist_ok=True)
