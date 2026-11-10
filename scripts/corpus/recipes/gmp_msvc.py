"""GMP built with MSVC (v143, /MD), beside the MinGW and Linux builds of the same release.

GMP is autotools plus GNU-assembler and m4-processed assembly, its configure
does not accept cl, and upstream documents MinGW and not MSVC for Windows
(the manual mentions `cl /MD` only for programs that use GMP). It still builds
with cl, x86 and x64, once configure and make's generating steps are done by
a script: `scripts/corpus/exercisers/gmp_msvc_build.py`, in the manner of
nettle_msvc_build.py. The portable C of mpn/generic is compiled (the
`--disable-assembly` configuration); there is no assembly and no
`--enable-fat`, so none of the CPU variants and none of the CPUID dispatch of
the Linux and MinGW images exist here.

What the exerciser does, and what was checked rather than assumed:

  * config.h is config.in with each `#undef` resolved from a table of the
    answers configure gives cl on Windows (LLP64: long is 4 bytes, so the x64
    limb is `unsigned long long` through `_LONG_LONG_LIMB`, as in the MinGW x64
    image; the x86 limb is 32 bits); gmp.h is gmp-h.in with its @SUBSTITUTIONS@
    filled (`__GMP_LIBGMP_DLL 1`, so the data and functions are
    `__declspec(dllexport)`); gmp-mparam.h is mpn/generic/gmp-mparam.h. All of
    it is written to gen/, outside the upstream files.
  * fac_table.h, sieve_table.h, fib_table.h, mp_bases.h, trialdivtab.h,
    jacobitab.h, perfsqr.h, fib_table.c and mp_bases.c come from compiling
    gen-fac.c, gen-sieve.c, gen-fib.c, gen-bases.c, gen-trialdivtab.c,
    gen-jacobitab.c and gen-psqr.c with cl and running them with the
    arguments of the rules in Makefile.in. The generating step run on a Linux
    host, with gcc standing in for cl and the 64-bit limb, produced all nine
    files byte for byte identical to the ones `./configure --disable-assembly
    && make` writes for the same limb size.
  * The source lists are read from Makefile.in (libgmp_la_SOURCES, MPZ_OBJECTS,
    MPQ_OBJECTS, MPF_OBJECTS, PRINTF_OBJECTS, SCANF_OBJECTS, RANDOM_OBJECTS,
    MPN_OBJECTS) and, for mpn, from configure.ac (gmp_mpn_functions and the
    multi-function-file table of GMP_MULFUNC_CHOICES, resolved against
    mpn/generic): 318 plain sources, 2 generated tables and 196 mpn functions,
    each compiled with `-DOPERATION_<function>` as mpn/Makefile.am does; the
    196 are the same set `./configure --disable-assembly` puts in mpn/Makefile's
    OFILES. 516 files compile with no error on both architectures.
  * Flags: /O2 /MD /Z7 (the debug information is embedded in the objects
    because the files are compiled in parallel and share no /Fd; link.exe
    writes the PDB), no /GL, no /LTCG; at link /DEBUG /Brepro /INCREMENTAL:NO
    /OPT:NOREF /OPT:NOICF. Exports are every defined external function of the
    objects (585 on both architectures), the rule MinGW's ld and
    nettle_msvc_build.py use.
  * The one thing a plain link does not accept. gmp.h gives cl `__inline` for
    the functions it declares extern inline for GCC (mpn_add, mpn_add_1,
    mpn_cmp, mpn_neg, mpn_sub, mpn_sub_1, mpn_zero_p, mpz_get_ui, mpz_neg,
    mpz_perfect_square_p). cl turns every use that it does not inline into a
    COMDAT copy, and the file that defines the function out of line
    (`__GMP_FORCE_<name>`) holds an ordinary one, so link.exe stops with, on
    x64:

        mpn_add.obj : error LNK2005: __gmpn_add already defined in mpf_add.obj
        mpn_add_1.obj : error LNK2005: __gmpn_add_1 already defined in mpf_add_ui.obj
        mpn_cmp.obj : error LNK2005: __gmpn_cmp already defined in mpf_cmp.obj
        mpn_neg.obj : error LNK2005: __gmpn_neg already defined in mpf_sub.obj
        mpn_sub.obj : error LNK2005: __gmpn_sub already defined in mpf_sub.obj
        mpn_sub_1.obj : error LNK2005: __gmpn_sub_1 already defined in mpf_sub.obj
        mpn_zero_p.obj : error LNK2005: __gmpn_zero_p already defined in mpn_gcd.obj
        mpz_get_ui.obj : error LNK2005: __gmpz_get_ui already defined in mpz_bin_ui.obj
        mpz_neg.obj : error LNK2005: __gmpz_neg already defined in mpz_bin_ui.obj
        mpz_stronglucas.obj : error LNK2005: __gmpz_perfect_square_p already defined in mpz_perfsqr.obj
        libgmp-10.dll : fatal error LNK1169: one or more multiply defined symbols found

    (x86 the same with one more underscore). Each of the ten has a single
    meaning, so the exerciser links again with /FORCE:MULTIPLE when, and only
    when, every error is LNK2005 or LNK1169, and the first definition wins
    (LNK4006 warnings, listed in the build log). That flag is the only
    deviation from the mandated link line; no source file, no generated header
    and no table is edited, and the images are NOT the product of an
    ordinary link (that link fails). The ten functions are therefore the
    COMDAT copies of the first object that defined them.

Counts, kept + removed = image total (removed is the baseline's measured MSVC
runtime: DllMain, the static vcruntime start-up, SEH and GS-cookie helpers and
import thunks for kernel32 functions):

    GMP_6.3.0_msvc143_x86_libgmp.dll   805 + 166 = 971   689 functions of 10+ instructions, 645 distinct PicHashes
    GMP_6.3.0_msvc143_x64_libgmp.dll   805 + 156 = 961   678 / 636

PicHash overlap of the 10+ instruction functions: MSVC against MinGW 0 and
against Linux 0, on both architectures (the GCC images are assembly and fat
dispatch, this one is portable C); x86 against x64 0; against Nettle
libhogweed, which carries mini-gmp, a different implementation: 3.10.2 and
4.0 MSVC x86 5 and 6, x64 2 and 2; 3.4.1 and 3.7.3 MSVC x86 4 and 5, x64 2 and
2; Nettle 3.10.2 and 4.0 MinGW x64 1, x86 0; Linux 0.

Glue survivors, by name and PicHash: thirteen one-instruction import thunks
of the C runtime (`raise`, `localeconv`, `ferror`, `fgetc`, `fputc`, `fwrite`,
`getc`, `putc`, `ungetc`, `isdigit`, `islower`, `isspace`, `isxdigit`; one
more underscore on x86), all with PicHash 1253497258561142223, the same as
`_wassert` in the Nettle MSVC images; they are below the cross-family
instruction floor and the baseline does not carry them. The other 95 names
that are not `mpn_/mpz_/mpq_/mpf_/gmp_` API are GMP's own file-local statics
(`hgcd_hook`, `block_resieve`, `findnext`, `randget_lc`, `perfpow`, ...) and
the two `DO_mpn_*` helpers.

Runner builds (windows-2022, cl 19.44): runs 42749164007 (both architectures,
stopped at the link with the LNK2005 list above), 42750806400 and 42752272041
(built; the data in the repository is from the last).

Not built: other releases, libgmpxx, and anything with assembly.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from .gmp import _VERSIONS


_BUILD = ("python {repo}/scripts/corpus/exercisers/gmp_msvc_build.py "
          "--arch {arch} --src . --work gmpbuild")


def _recipe(version):
    return Recipe(
        family="GMP",
        version=version,
        upstream="https://gmplib.org/",
        license="LGPL-3.0-or-later OR GPL-2.0-or-later (dual, licensee's choice)",
        source=Source(url="https://ftp.gnu.org/gnu/gmp/gmp-%s.tar.xz" % version,
                      sha256=_VERSIONS[version]),
        build=[BuildStep(_BUILD), BuildStep("dir gmpbuild", allow_failure=True)],
        artifacts=[Artifact(path="gmpbuild/libgmp-10.dll",
                            component="libgmp.dll",
                            pdb="gmpbuild/libgmp-10.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Z7, generic C only (no assembly, no --enable-fat), "
                    "config.h, gmp.h, gmp-mparam.h and the generated tables "
                    "produced from config.in, gmp-h.in and the gen-*.c programs; "
                    "/DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link, "
                    "plus /FORCE:MULTIPLE because a plain link stops with LNK2005 "
                    "for ten of gmp.h's extern-inline functions (see the recipe); "
                    "exports generated from the objects",
        notes="No configure run (cl is not a supported GMP compiler): "
              "gmp_msvc_build.py reproduces what configure and make produce "
              "for the no-assembly configuration and compiles the source lists "
              "of Makefile.in and configure.ac with cl, unpatched. Portable C "
              "only, so none of GMP's assembly or fat dispatch is present. "
              "Built against the DLL runtime, so the MSVC C runtime stays "
              "attributed to data/MSVC. No source file or generated table is "
              "edited, but the image is the product of a link with "
              "/FORCE:MULTIPLE (a plain link fails with LNK2005 for ten "
              "functions gmp.h declares extern inline; the first definition "
              "wins), so it is NOT the output of an ordinary link of "
              "unmodified upstream. Pinned by the sha256 of a GPG-verified "
              "release tarball.",
    )


RECIPES = {"GMP_%s_msvc" % version: _recipe(version) for version in _VERSIONS}
