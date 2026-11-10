"""jitasm built with MSVC, from the same exerciser as the MinGW build.

See jitasm.py for what the library is, why it is here, the -O measurement and
what the exerciser costs. MSVC is the likelier compiler behind a Windows
sighting, and it renders this header very differently: C++ name mangling, the
MSVC STL's vector, deque and map, exception tables and template instantiation
all differ from GCC's, which is why the PicHash overlap with the MinGW build
is zero at the ten-instruction floor on both architectures (x64 2516 distinct
hashes here against 312).

/O2, and an /Od leg beside it. The issue asked for the function count at
/Od and /O2; /O2 keeps 6098 functions on x64 and 5519 on x86, of which 4415
and 4230 are ten instructions or more, so optimisation does not erase the
library. The /Od build (jitasm_2018-11-24-Od_msvc, version 2018-11-24-Od) is
the expected flag for an MSVC consumer and is carried for that reason, not to
rescue anything: kept + removed = total, x86 5811 + 1408 = 7219 and x64 6547
+ 1409 = 7956, of which 5253 and 5138 are ten instructions or more (2537 and
2659 distinct PicHashes) and 4946 and 5448 carry jitasm in their name, all
named from the PDB. The function counts barely move against /O2, but the
code does: PicHash overlap with the /O2 build at the ten-instruction floor is
zero on both architectures, and zero with the MinGW -O0 build, so /Od is a
separate reference. Built on the windows-2022 runner, runs 42673036849 (x86)
and 42674358336 (x64).

Counts, kept + removed = total: x86 5519 + 1629 = 7148, x64 6098 + 1697 =
7795. Every kept function is named from the PDB. 4877 (x86) and 5311 (x64)
carry jitasm in their name, 302 and 300 are STL or runtime, and 336 and 483
are the exerciser's own scaffolding and upstream's sixty test cases
(test_*::naked_main and the ex_*, assemble_one and test_backend functions),
recognisable by name; the sixty are the largest functions in the image, up to
6242 instructions. jitasm::Backend::Assemble, Encode, EncodeALU, EncodeImm,
EncodeJMP and EncodeMOV, 3599 jitasm::Frontend members and 850
jitasm::compiler members are present on x64.

Glue survivors, by name and PicHash: __std_remove_4 (x64
13321955253556739503, 66 instructions) and __std_remove_8 (x64
12991552176196244522) are the MSVC STL's vectorised remove helpers, compiled
into the image from <algorithm> and not removed by the baseline; _wassert
(__wassert on x86) is a one-instruction import thunk, PicHash
1253497258561142223.

Build. /EHsc because the STL containers in jitasm.h throw; /bigobj because the
exerciser is one translation unit holding sixty large instruction sequences
and will otherwise exceed the object format's section limit; /MD so the MSVC
C runtime is imported and stays attributed to data/MSVC. The linker PDB is
the one declared on the Artifact; /Fd names the compiler's own separately. The
link is /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF, as the other
MSVC recipes here have it. The DLL has no entry point of its own.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_COMPILE = ("cl /nologo /c /O2 /MD /Zi /EHsc /bigobj /I. "
            "/Fdjitasm.compiler.pdb /Fojitasm.obj "
            "{repo}/scripts/corpus/exercisers/jitasm.cpp")
_LINK = ("link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF "
         "/OPT:NOICF /PDB:jitasm.pdb /OUT:jitasm.dll jitasm.obj kernel32.lib")

# The unoptimised leg the tracker issue asks for: /Od in place of /O2 and
# nothing else changed, so the two artefacts differ in the optimiser alone.
_COMPILE_OD = _COMPILE.replace(" /O2 ", " /Od ")

RECIPES = {
    "jitasm_2018-11-24_msvc": Recipe(
        family="jitasm",
        version="2018-11-24",
        upstream="https://github.com/hikaru-i/jitasm",
        license="New BSD (three-clause), Copyright (c) 2009-2011 Hikaru "
                "Inoue, Akihiro Yamasaki",
        source=Source(git_url="https://github.com/hikaru-i/jitasm.git",
                      git_ref="7cb9d72982c793374c49b804bec842deb1506d92"),
        build=[BuildStep(_COMPILE), BuildStep(_LINK)],
        artifacts=[Artifact(path="jitasm.dll", component="jitasm.dll",
                            pdb="jitasm.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi /EHsc /bigobj; /DEBUG /Brepro "
                    "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link",
        notes="The same exerciser translation unit as the MinGW build, so "
              "the two differ in the compiler. Measured at /O2: 5519 "
              "functions kept of 7148 on x86 (1629 MSVC runtime removed), "
              "6098 of 7795 on x64 (1697), 4230 and 4415 of them ten "
              "instructions or more, all named; 4877 and 5311 carry jitasm "
              "in their name. Roughly one in fourteen is not jitasm's: the "
              "sixty test_*::naked_main bodies from upstream's "
              "test/test_backend.cpp and the exerciser's own ex_*, "
              "assemble_one and test_backend functions, 336 on x86 and 483 "
              "on x64, recognisable by name. /O2 keeps the whole library; "
              "the /Od build is carried separately as version 2018-11-24-Od. "
              "PicHash overlap with the MinGW and ELF builds is "
              "zero at the ten-instruction floor on both architectures. "
              "The MSVC STL's __std_remove_4 and __std_remove_8 survive the "
              "glue filter on x64.",
    ),
    "jitasm_2018-11-24-Od_msvc": Recipe(
        family="jitasm",
        version="2018-11-24-Od",
        upstream="https://github.com/hikaru-i/jitasm",
        license="New BSD (three-clause), Copyright (c) 2009-2011 Hikaru "
                "Inoue, Akihiro Yamasaki",
        source=Source(git_url="https://github.com/hikaru-i/jitasm.git",
                      git_ref="7cb9d72982c793374c49b804bec842deb1506d92"),
        build=[BuildStep(_COMPILE_OD), BuildStep(_LINK)],
        artifacts=[Artifact(path="jitasm.dll", component="jitasm.dll",
                            pdb="jitasm.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/Od /MD /Zi /EHsc /bigobj; /DEBUG /Brepro "
                    "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link",
        notes="The /Od counterpart of jitasm_2018-11-24_msvc that the "
              "tracker issue expects for MSVC: the same commit, exerciser, "
              "compile and link lines with /Od in place of /O2, filed under "
              "its own version string. Measured: 5811 functions kept of 7219 "
              "on x86 (1408 MSVC runtime removed), 6547 of 7956 on x64 "
              "(1409), 5253 and 5138 of them ten instructions or more, all "
              "named; 4946 and 5448 carry jitasm in their name. PicHash "
              "overlap at the ten-instruction floor with the /O2 build and "
              "with the MinGW -O0 build is zero on both architectures. The "
              "sixty test_*::naked_main bodies and the exerciser's own ex_*, "
              "assemble_one and test_backend functions are consumer code "
              "recognisable by name, as in the /O2 artefact.",
    ),
}
