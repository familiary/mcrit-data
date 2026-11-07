"""Shared description of the MIRACL builds (not a recipe module).

The three recipe modules, miracl_linux.py, miracl.py (MinGW) and
miracl_msvc.py, differ only in how a compiler is driven. What is built, and
the variant names, live here so the three cannot drift apart.
"""

UPSTREAM = "https://github.com/miracl/MIRACL"
# Tip of master (merge of PR #81, 2019-08-21); the repository has no tags.
COMMIT = "b9b8fd471de253cfd6313446cb490741edb069a7"
DATE = "2019-08-21"
LICENSE = ("AGPL-3.0-or-later; the README offers a commercial licence in its "
           "place (MIRACL UK Ltd., (c) 2018)")

# The C modules upstream's lib/linux64 compiles into miracl.a (50 of them,
# mrmuldv excluded: it is compiled only by the variants that use assembly,
# and by the Win64 C variant, which is where upstream's scripts put it).
C_MODULES = (
    "mrcore mrarth0 mrarth1 mrarth2 mralloc mrsmall mrio1 mrio2 mrgcd mrjack "
    "mrxgcd mrarth3 mrbits mrrand mrprime mrcrt mrscrt mrmonty mrpower "
    "mrsroot mrcurve mrfast mrshs mrshs256 mrshs512 mrsha3 mrfpe mraes mrgcm "
    "mrlucas mrzzn2 mrzzn2b mrzzn3 mrzzn4 mrecn2 mrstrong mrbrick mrebrick "
    "mrec2m mrgf2m mrflash mrfrnd mrdouble mrround mrbuild mrflsh1 mrpi "
    "mrflsh2 mrflsh3 mrflsh4").split()
# The C++ wrappers the same scripts compile beside it: big (bn), zzn, ecn and
# ec2 (the elliptic curve classes), crt, flash. Upstream's example programs
# and source/curve/ (poly, polymod, schoof, the CM and SEA tools) are not
# built: nothing in the tracker issue names them.
CPP_MODULES = "big zzn ecn ec2 crt flash".split()

assert len(C_MODULES) == 50

# variant -> (architecture, summary). The detail of what each toolchain does
# for a variant is in the per-toolchain modules.
VARIANTS = {
    "generic32": "32-bit, portable C only (mirdef.h32, MR_NOASM)",
    "generic64": "64-bit, portable C only / no hand-written assembly",
    "asm32": "32-bit with the assembly muldiv upstream's own script uses",
    "asm64": "64-bit with the assembly muldiv upstream's own script uses",
}

UNKNOWN = (
    "The configuration of the sample this was requested for is not known. "
    "The tracker issue asks for a comparison against LockBit 3.0's "
    "keygen.exe (32-bit), and the evidence that its keygen uses MIRACL at "
    "all is by name; no verified sample, mirdef.h, word size, assembly "
    "setting or curve is available. MIRACL's mirdef.h selects the word size, "
    "whether muldiv/muldvd/muldvm are assembly, and which arithmetic paths "
    "the library compiles in, and that changes the code shape a great deal, "
    "so these variants are built side by side instead of one being guessed. "
    "Which of them, if any, matches that keygen is unknown.")
