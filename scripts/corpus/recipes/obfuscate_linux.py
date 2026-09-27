"""adamyaxley/Obfuscate, built for Linux and ELF.

The ELF counterpart of obfuscate.py, and the same arrangement the ``_msvc``
modules have: one family, one version, two containers. Same pinned commit,
same exerciser translation unit, same -O0; only the toolchain and the output
container differ, which is the point - a reader matching a Linux binary
against this corpus needs the ELF shape of these functions, and the PE
reports cannot supply it.

Everything obfuscate.py records about *why* -O0 applies here unchanged, and
was re-measured on this toolchain rather than assumed. GCC 13 on Linux,
x86_64, on the same exerciser:

    -O0   216 of the library's own functions - 181 ay::* members plus the 35
          per-call lambdas AY_OBFUSCATE expands into the caller's scope
    -O2   50 functions total, of which 35 are the library's and every one of
          those is a 2-instruction `endbr64; ret` ~obfuscated_data() stub;
          the constructor, decrypt() and the char* conversion are all gone

So the -O0 finding is the compiler's, not the container's, and holds on ELF
exactly as the MinGW recipe records it for PE.

A ``.so``, not a static archive and not an executable, and that choice is
worth more here than the DLL choice is on Windows. A -shared ELF object links
glibc, libstdc++ and libm dynamically, so not one of their bodies is in the
image. Measured on the x64 artefact: 227 functions, of which 216 are the
library's own, 3 the exerciser's and 8 are unnamed one- to three-instruction
lazy-binding stubs out of .plt and .plt.sec - which belong to the dynamic
linker rather than to anyone's source. There is no libstdc++ and no glibc in
it at all. A static build would instead have put the whole C++ runtime in
here under this family's name, which is the trap the nlohmann recipe records
for -static-libstdc++ and the one monomorph hit with a -static executable,
where 1393 of 1397 symbols were glibc and zlib.

The 32-bit half needs the gcc/g++ multilib packages (gcc-multilib and
g++-multilib on Debian and Ubuntu); corpus.toolchain does not register
linux_x86 at all without the first of them.

One thing the x86 artefact carries that the x64 one does not: six link glue
functions - _init, _fini, register_tm_clones, deregister_tm_clones,
__do_global_dtors_aux and __stack_chk_fail_local - that the measured baseline
does not remove. It is not a gap in the baseline. On 32-bit PIC each of those
bodies reaches the GOT through `call __x86.get_pc_thunk.bx; add ebx, <delta>`
and the delta is that image's own layout, so the body differs between any two
images and its PicHash with it. The filter matches on symbol *and* PicHash on
purpose - that is what stops it deleting a project's own strlen - so these
stay. Six of 233 functions, all named, all obviously the compiler's; the x64
artefact's six match the baseline exactly and are dropped.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# -I. because obfuscate.h sits at the repository root. {archflag} is the
# -m32/-m64 that selects the ABI, since one native gcc serves both.
#
# -fPIC is required rather than optional here: a shared object on x86_64
# cannot carry the absolute relocations a non-PIC compile emits, and ld says
# so and stops. There is no MinGW equivalent - a PE is relocated wholesale by
# its base relocation table - which is why the flag appears on this side only.
#
# -fvisibility=hidden is what makes this artefact the ELF equivalent of the
# MinGW DLL rather than a differently shaped thing. An ELF shared object
# exports every global symbol by default, and a call to an exported symbol
# from inside the same object still goes through the PLT, because another
# object is allowed to interpose it. Without the flag each of the library's
# own template instantiations was both exported and called through a
# three-instruction .plt stub. Measured on x64: 519 functions of which 300
# unnamed, and 219 of the 368 above the symbol-check floor carrying a name,
# which is 0.595 against a 0.5 gate. With the flag the object exports only
# `exercise` - which corpus_export.h marks visibility("default") for exactly
# this - the internal calls are direct, and the same source is 227 functions
# with 219 of 222 named. Nothing of the library is lost: hidden is not
# stripped, the symbols are all still in .symtab, which is what SMDA reads.
# It is also what the PE side has had all along, since a MinGW DLL with no
# .def exports only what is marked dllexport. StringObfuscatorCT, whose
# library-to-stub ratio is worse, was refused outright without it.
#
# No -shared-libgcc, unlike the MinGW recipe: on Linux g++ links libgcc_s
# dynamically already, and the flag would be a no-op claiming to do something.
_BUILD = ("{cxx} {archflag} -std=c++14 -O0 -shared -fPIC -fvisibility=hidden "
          "-I. -o ay_obfuscate.so "
          "{repo}/scripts/corpus/exercisers/ay_obfuscate.cpp")


RECIPES = {
    # Same commit as the MinGW recipe, deliberately: the two artefacts are
    # only comparable if they are the same source.
    "Obfuscate_2026-06-03_linux": Recipe(
        family="Obfuscate",
        version="2026-06-03",
        upstream="https://github.com/adamyaxley/Obfuscate",
        license="Unlicense (public domain dedication, stated at the foot of "
                "obfuscate.h and in LICENSE)",
        source=Source(git_url="https://github.com/adamyaxley/Obfuscate.git",
                      git_ref="5390a353f4e83ffd596730eab0b0e4ac629dbbbc"),
        build=[BuildStep(_BUILD)],
        artifacts=[Artifact(path="ay_obfuscate.so",
                            component="ay_obfuscate.so")],
        toolchains=["linux_x86", "linux_x64"],
        build_flags="-O0 -std=c++14 -fPIC -shared -fvisibility=hidden "
                    "(exerciser; -O0 and the visibility setting are both "
                    "load-bearing, see notes)",
        notes="The ELF build of the same commit and the same exerciser as the "
              "MinGW artefacts of this family, so the two are comparable. "
              "Built from an exerciser translation unit, since the library is "
              "header-only and constexpr; the emitted functions are the "
              "library's own. -O0 is deliberate and was re-measured on this "
              "toolchain: at -O2 GCC 13 on Linux leaves 35 of the library's "
              "functions and every one is a 2-instruction `endbr64; ret` "
              "~obfuscated_data() stub, against 216 real ones at -O0 - so an "
              "-O2 consumer of this library has nothing in it for these "
              "functions to match, on ELF exactly as on PE. A .so linking "
              "glibc and libstdc++ dynamically is what keeps the C++ runtime "
              "out of the sample: of the x64 artefact's 227 functions, 216 "
              "are the library's, 3 the exerciser's and the other 8 are "
              "unnamed one- to three-instruction .plt/.plt.sec lazy-binding "
              "stubs. The x86 artefact additionally keeps six named link glue "
              "functions (_init, _fini, the tm_clones pair, "
              "__do_global_dtors_aux, __stack_chk_fail_local): on 32-bit PIC "
              "their bodies embed this image's own GOT delta, so the "
              "measured baseline's PicHash does not match and the filter, "
              "correctly, does not remove them on a name alone. "
              "obfuscated_data is templated on "
              "<N, KEY, CHAR_TYPE> with KEY defaulting to "
              "ay::generate_key(__LINE__), so the exerciser puts every "
              "AY_OBFUSCATE on its own source line; calls sharing a line and "
              "a length collapse into a single instantiation. The 32-bit "
              "artefact needs gcc-multilib and g++-multilib installed.",
    ),
}
