"""Shared description of the MIRACL builds (not a recipe module).

The recipe modules miracl_linux.py, miracl.py (MinGW), miracl_msvc.py and
miracl_mingw_asm32.py differ in how a compiler is driven. The module list and
variant names live here so the compiler axes use the same library scope.

Measured (kept + removed = total; removed is the measured runtime-glue
baseline; PicHash overlap counts functions of 10 or more instructions):

  variant / artefact               kept  removed  total
  generic32 linux x86               745        6    751
  generic32 mingw x86               861       72    933
  generic32 msvc x86                759      235    994
  asm32     linux x86               744        6    750
  asm32     mingw x86               862       71    933
  asm32     msvc x86                759      234    993
  generic64 linux x64               737        6    743
  generic64 mingw x64               650       70    720
  generic64 msvc x64                724      224    948
  asm64     linux x64               729        6    735
  asm64     mingw x64               644       70    714

How much the configuration changes the code (PicHash overlap, 10+ insn
functions, within one compiler and architecture): x64 generic64 vs asm64 is
491 of 514 (96%) on gcc and 487 of 509 (96%) on MinGW, so on 64-bit the
assembly muldiv barely moves the shape; x86 generic32 vs asm32 is 196 of 610
(32%) on gcc, because the 32-bit paths inline muldvd differently, but 540 of
554 (98%) on MSVC where only mrmuldv differs. Across compilers the overlap is
essentially nil: gcc/MinGW share 32 x86 hashes (6%), and no hash is shared
between MSVC and either GCC build or between 32- and 64-bit. So the compiler
and word size dominate. The added MinGW asm32 image has 530 distinct hashes,
508 shared with generic32 (527). It adds 19 named arithmetic hashes beyond
all ten prior images; two more apparent additions are SMDA fragments of
multi_add and are excluded from novelty. See miracl_mingw_asm32.py for the
complete matrix and runtime survivor names/hashes.

Surviving glue and runtime, all named and kept deliberately: ELF x86 keeps
_init (11 insn, e54662b85aae2ecd), __do_global_dtors_aux (21,
d5b1d127777c35f3), __x86.get_pc_thunk.si/.cx/.bp (2 each, 99104660fd4df449,
769f0aed4b5feefe, 7c99608cc56520ba), which the PIC bodies keep the baseline
from matching, as obfuscate_linux.py records. Every image keeps the C++
wrappers' iostream inlines (operator<< and operator>> on Big, Flash, ZZn, ECn
and EC2, otfloat); the MSVC images also keep MSVC STL instantiations that
big.cpp's headers emit (std::use_facet, basic_istream::sentry, ...), which
are template code compiled into the image rather than imported. The MinGW x86
image keeps 118 unnamed functions, 113 of them 2-instruction import thunks
(the rest 4 of 7 instructions and 1 of 15). Linux images
compiled without -fvisibility=hidden were 1388-1409 functions of which about
650 were unnamed PLT stubs; they are not what is committed.
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
