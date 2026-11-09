"""MIRACL's 32-bit GCC assembly arithmetic, MinGW x86.

The existing MinGW matrix omitted this axis because lib/mingw.bat only
documents x64. This recipe uses upstream's ready 32-bit mirdef.h32 template
and the unchanged GCC inline-assembly source mrmuldv.gcc. Both int and long
are 32 bits on this target; MinGW provides the template's __int64 spelling.
The same 50 C modules and six C++ wrappers as the sibling recipes are linked
into a DLL for static analysis. No examples or sample-specific key generator
is built, and no resulting artifact is executed.

No upstream source edit is required. The configuration is a compiler axis,
not a claim about the unprovided sample's configuration.

Measured with MinGW GCC 13-posix, SMDA 5.0.2 and MCRIT 1.16.0:
862 kept + 71 runtime removals + 0 exclusions = 933 recovered functions.
There are 602 functions of at least ten instructions, with 530 distinct
PicHashes. Intersections with existing variants (all at that floor):

  previous variant / compiler      previous hashes  shared  new-only
  generic32 MinGW x86                         527     508        22
  generic32 Linux x86                         610      31       499
  asm32     Linux x86                         611      32       498
  generic32 MSVC x86                          554       0       530
  asm32     MSVC x86                          553       0       530
  generic64 Linux x64                         514       0       530
  asm64     Linux x64                         512       0       530
  generic64 MinGW x64                         509       0       530
  asm64     MinGW x64                         508       0       530
  generic64 MSVC x64                          560       0       530

Twenty-one hashes lie outside the union of all ten earlier images. Two
are a SMDA split of multi_add: named 32-instruction prefix
0x223e3f9b734b29c2 and unnamed ten-instruction continuation
0x12fed8c4dbfd7a65. Independent nm/objdump inspection places both within
one upstream multi_add body. Neither counts as a novel implementation;
the other 19 new hashes are named MIRACL arithmetic bodies, individually
listed in scripts/corpus/coverage/miracl/README.md.

Runtime/import survivors are ___gxx_personality_v0,
___register_frame_info, ___deregister_frame_info, __Unwind_Resume,
std::__istream_extract, std::__throw_bad_cast, std::__ostream_insert,
std::basic_ios::clear, std::ostream::operator<<(int), std::istream::getline,
std::istream::sync and std::ctype::_M_widen_init. All are one-instruction
import thunks with PicHash 0x1165511d87767dcf. The unnamed 15-instruction
0xdfe3cea2dbb80872 is independently named ___chkstk_ms by COFF nm; it is
shared with the checked bzip2, cJSON and Obfuscate references. The other
unnamed survivors are 113 two-instruction and four seven-instruction
stubs, plus the ten-instruction multi_add continuation above. No name was
invented in the report and no shared baseline was edited.

MIRACL's stream operators and otfloat are defined by its own wrapper
sources; their names do not make them standard-library implementations.
Retained wrapper cold fragments: operator<<(std::ostream&, EC2 const&)
0x5bb2f864da4cc32f (3 instructions), ECn 0x8577d6c547696701 (8), and ZZn
0x91bed5f78b57b2d1 (11). They add no new hash over the older family images.
Against five small control families (aPLib, bzip2, cJSON, Obfuscate,
SysWhispers), only the known unnamed stack probe matches; no project
hash matches them.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _miracl as m


RECIPES = {
    "MIRACL_2019-08-21-asm32_mingw": Recipe(
        family="MIRACL",
        version=m.DATE + "-asm32",
        upstream=m.UPSTREAM,
        license=m.LICENSE,
        source=Source(
            url="https://codeload.github.com/miracl/MIRACL/tar.gz/" + m.COMMIT,
            sha256="fbcfbfc0e245f8af74d4800dfa40f3546f7bec9e6cc12b645ca234573ef447d4",
        ),
        toolchains=["mingw_x86"],
        build=[
            BuildStep("rm -rf mb && mkdir mb && cp include/*.h mb/ && "
                      "cp include/mirdef.h32 mb/mirdef.h"),
            BuildStep("for f in " + " ".join(m.C_MODULES) + "; do "
                      "{cc} -O2 -I. -c ../source/$f.c -o $f.o || exit 1; "
                      "done", cwd="mb"),
            BuildStep("for f in " + " ".join(m.CPP_MODULES) + "; do "
                      "{cxx} -O2 -I. -c ../source/$f.cpp -o $f.o || exit 1; "
                      "done", cwd="mb"),
            BuildStep("cp ../source/mrmuldv.gcc mrmuldv.c && "
                      "{cc} -O2 -I. -c mrmuldv.c -o mrmuldv.o", cwd="mb"),
            BuildStep("{cxx} -shared -o libmiracl.dll *.o -lm", cwd="mb"),
        ],
        artifacts=[Artifact(path="mb/libmiracl.dll", component="libmiracl.dll")],
        build_flags="-O2 -shared; upstream include/mirdef.h32 with assembly "
                    "enabled; unchanged source/mrmuldv.gcc as mrmuldv.c",
        notes=m.UNKNOWN + " MinGW x86 assembly arithmetic from unchanged "
              "source/mrmuldv.gcc with upstream's mirdef.h32 template, at "
              "commit " + m.COMMIT + ". The 50 C modules and six C++ "
              "wrappers match the sibling reference builds. No upstream "
              "source patches, examples or sample-specific generator. "
              "The DLL is linked and disassembled only, never executed. "
              "Measured 862 kept + 71 runtime removals = 933 recovered "
              "functions; 530 distinct PicHashes at ten instructions. "
              "Nineteen new named arithmetic hashes remain beyond all ten "
              "previous variants after excluding both SMDA multi_add "
              "fragment hashes from novelty. Known stack-probe and import "
              "thunks remain disclosed in the recipe docstring.",
    ),
}
