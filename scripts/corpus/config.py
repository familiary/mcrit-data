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
# outright over it at 38% named, with 7844 named functions - within 3% of
# what the MinGW build of the same tag names.
#
# Two kinds of function with no symbol to keep were being counted, and it is
# worth being precise about which of them was a false alarm, because only one
# was.
#
# The first was a genuine defect, in the recipes rather than in the check,
# and is fixed there: seven MSVC links omitted /INCREMENTAL:NO, and an
# incrementally linked image reaches each function through a table of
# one-instruction jump thunks. That table is unmistakable once looked at -
# in nlohmann_json 3.12.0 x64 it is 2866 entries, exactly five bytes apart,
# running unbroken from base+0x1005, with no other function inside its
# span. So this ratio was right to be unhappy; it simply could not say why,
# and it was the only thing in the pipeline that was unhappy at all.
# assert_not_incrementally_linked now says why, which is what lets this
# ratio stop trying to.
#
# The second is real and stays: x86 C++ exception handling emits an
# __ehhandler$ or __unwindfunclet$ fragment per function - "mov eax,
# <scopetable>; jmp <handler>" or "lea ...; jmp ..." - and the PDB records
# no symbol at those addresses. BlackBone x86 has 795 of them, carrying
# 1590 instructions between them; BlackBone x64 has no unnamed function at
# all and names 1628 of 1628, because x64 unwinding is table-driven. The
# same split shows everywhere the corpus has both architectures of a C++
# project: 7-Zip 26.03 has 2759 of them on x86 and none on x64, protobuf
# 21.12 has 3111 and none, abseil 482 and none. Counting them measures how
# much C++ a project contains, and on which architecture, rather than
# whether this build was stripped.
#
# Three instructions is above both kinds and below almost everything else.
# It is not a clean separator and should not be described as one: measured
# over the committed reports, the lowest a generated family reaches at that
# floor is nlohmann_json's MinGW x86 build at 78% (245 of 315) and the
# lowest MSVC artefact is protobuf 21.12 x86 at 81% (17,479 of 21,466),
# with BlackBone x86 at 86% only the fourth-worst of the MSVC set. So the
# margin above a 0.5 gate is about thirty points rather than fifty, which
# is ample but is not the uniform picture a "100% everywhere" claim would
# suggest. What the floor buys is that the gate stops varying with how much
# C++ a project contains; a build that really did strip its symbols names
# nothing at any floor.
#
# It buys that at a cost, and the cost is why the incremental link table
# above gets a check of its own rather than being left to this ratio: the
# floor hides any defect whose signature is many short unnamed functions,
# which is exactly what that defect was. bzip2 and libtomcrypt had been
# sitting within one point of failing this gate for that reason, and the
# gate was the only thing in the pipeline that had noticed.
#
# Those figures come from the committed reports, i.e. after compiler
# runtime has been dropped. The check runs before that pass, and is_glue
# can only match a function that has a name, so every function the drop
# removes is named and the ratio the check sees is the higher one - the
# numbers above are a lower bound.
MIN_NAMED_SAMPLE_INSTRUCTIONS = 3

# How long a run of one-instruction jump thunks at a uniform five-byte stride
# has to be before smdaify calls it an incremental link table and refuses the
# build. See assert_not_incrementally_linked for what that is and why it gets
# a check of its own.
#
# 32 sits between two measured populations, and the gap between them is what
# makes the check safe rather than the threshold itself. Applied to all 392
# committed reports this tooling generated, it separates them cleanly:
#
#   * 21 artefacts carry a table, and they are exactly the ones the seven
#     recipes without /INCREMENTAL:NO produced - OpenSSL and nlohmann_json
#     and sqlite3 and Lua four each, bzip2 and libtomcrypt two, cryptopp
#     x64 one. Their shortest run is 70 (cryptopp x64) and their longest
#     459 (nlohmann_json 3.11.3 x86).
#   * the other 371 have a longest run of 18, in protobuf 3.6.1 and 21.12
#     built with MinGW.
#
# So the boundary is 18 against 70 and 32 is in the middle of it. Note what
# that second line corrects: unaffected artefacts are *not* free of unnamed
# direct-jump functions - 7-Zip's MinGW x86 reports carry 265 of them,
# cryptopp's MinGW x64 241, protobuf 3.6.1 x86 107. They are scattered
# rather than packed, which is the whole point of measuring the run and not
# the count.
MAX_INCREMENTAL_THUNK_RUN = 32


def ensure_dirs():
    for path in (DOWNLOAD_DIR, SOURCE_DIR, ARTIFACT_DIR, REPORT_DIR):
        os.makedirs(path, exist_ok=True)
