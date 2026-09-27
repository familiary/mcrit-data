"""4g3nt47/Obfuscator - a standalone string-obfuscating file patcher
(lib2smda#1).

This is the smallest project in the corpus and the first one that needed
``Recipe.min_functions``. It has seven functions and that is all it has:
obfs_encode, obfs_decode, obfs_find_offset, obfs_filecpy,
obfs_read_until_null, obfs_run and main. There is no library API to drive, so
no exerciser can raise that number the way one does for a header-only
library - the "library" is a .c file compiled straight into the launcher.

Why it was refused once and is built now
----------------------------------------

Measured through corpus.smdaify with the glue drop on, the artefact used to
report 15 functions on x86 and 28 on x64, which clears MIN_USEFUL_FUNCTIONS
of 8 - but it cleared it on MinGW C runtime the baseline did not classify.
The named survivors were feof, fgetc, printf twice, rewind and (on x64) atoi,
none of which _PROBE_DLL ever calls. Passing a sample on runtime residue is
precisely the misattribution drop_crt_glue exists to prevent, so lowering the
floor on its own would have been the wrong fix and was not made.

What was done instead is in baseline.py: _PROBE_STDIO calls the
character-at-a-time half of stdio, so those names are measured like every
other runtime function. After it, the committed artefacts are:

    mingw x86   10 functions   7 this project's, 3 residue, 0 named residue
    mingw x64   22 functions   7 this project's, 15 residue, 0 named residue

Every named function in both artefacts is now one of the seven. What is left
is unnamed, and no name-matching filter can reach it: MinGW's ___chkstk_ms,
two bodies SMDA splits out of the mingwthr and dtoa lock code on x86, and on
x64 fourteen one-instruction kernel32 import thunks that SMDA recovers
without a symbol. That is the limitation libtomcrypt records too.

So min_functions=7 is not what makes this build pass - 10 and 22 both clear
the default floor of 8 on their own. It is set because 7 is what this
project contains, counted in src/obfuscator.h plus main(), and because the
number that admits this family should be its own function count rather than
a total that includes runtime the filter cannot name. If SMDA ever stops
recovering those unnamed thunks the artefact becomes exactly seven
functions, and that is a correct artefact, not a defective one.

Why the sources are compiled directly rather than with make
-----------------------------------------------------------

Upstream's Makefile has three defects, all confirmed against the pinned
commit:

  * the link line is ``gcc -Os -s ...``. -s strips every symbol, and nm
    reports none on the result, which makes the artefact worthless as
    reference data;
  * ``bin/main.o`` and ``bin/obfuscator.o`` are written into bin/ and no
    rule creates that directory, so a clean checkout fails on the first
    compile;
  * ``make install`` copies ``bin/main``, which no rule ever builds - the
    link target is ``bin/obfuscator``.

Invoking the compiler directly is the established way round a broken
upstream build here and is not a source modification: the translation units
are upstream's, unedited.

Why -O0 and not upstream's -Os
------------------------------

obfs_decode is byte-for-byte obfs_encode - the cipher XORs, so encode and
decode are the same routine - and GCC's identical-code folding notices. At
-Os and at -O2, measured on x64, obfs_decode comes out as a single
instruction, a tail jump into obfs_encode, and the project loses a seventh of
itself. At -O0 it is a distinct body: 140 bytes and 49 instructions on x86,
163 bytes and 52 on x64.

-O0 is also the reason _PROBE_STDIO is registered a second time at -O0 in
baseline.py. mingw-w64's stdio.h defines printf as a static inline wrapper
compiled from each translation unit that calls it, so its PicHash follows the
optimisation level - 25 instructions here against 19 at -O2 - and this is the
only recipe in the corpus that does not build optimised.

Why there is no Linux build
---------------------------

This is upstream's native target and it builds, so it was tried and
measured rather than assumed unsuitable. It does not produce usable
reference data, for a reason the container makes unavoidable: this is an
executable, not a shared object, so every call into glibc goes through a
.plt stub that carries no symbol, and there is no -fvisibility=hidden to
avoid it the way the header-only families on this side do. GCC 13, -O0:

    linux x64   52 functions, 7 glue dropped, 45 left - 7 this project's and
                38 unnamed .plt stubs. Refused outright by
                assert_symbols_survived at 13 of 31 functions above the
                instruction floor named, 42% against a 0.5 gate.
    linux x86   58 functions, 4 glue dropped, 54 left - 7 this project's, 6
                more of GCC's own that the baseline does not match by
                PicHash, and 41 unnamed .plt stubs. It passes the symbol
                gate, but on the same shape of sample the x64 half is
                refused for.

Seven functions among 38 or 41 unnamed stubs is the reverse of what the
MinGW artefacts look like, and half a family admitted on a gate the other
half fails would be worse than none, so this stays MinGW-only. It is worth
revisiting if the Linux side ever grows a glibc baseline; nothing else about
it is hard.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# One command per translation unit, mirroring the compile lines upstream's
# Makefile has, with -Os replaced by -O0 and -s dropped from the link.
_BUILD = [
    BuildStep("{cc} -O0 -Wall -c src/obfuscator.c -o obfuscator.o"),
    BuildStep("{cc} -O0 -Wall -c src/main.c -o main.o"),
    BuildStep("{cc} -O0 -Wall -o obfuscator.exe main.o obfuscator.o"),
]


_NOTES = (
    "Seven functions, which is what this project has: obfs_encode, "
    "obfs_decode, obfs_find_offset, obfs_filecpy, obfs_read_until_null, "
    "obfs_run and main. There is no library API to drive, so the recipe sets "
    "min_functions=7 rather than naming a total that includes runtime "
    "residue - see the module docstring and the _PROBE_STDIO baseline probe "
    "added for it, which is what took the named residue in these artefacts "
    "(feof, fgetc, printf twice, rewind, atoi) to zero. Be clear about what "
    "this family is worth: nothing from this project is ever linked into a "
    "protected program. It is a standalone command-line patcher that XORs "
    "marked byte ranges in an "
    "already-built file, and the only part of it that propagates downstream "
    "is a copy-pasted ten-line obfs_decode(), which the upstream README asks "
    "you to paste into your own source and which therefore appears in "
    "whatever shape your own compiler gives it. The reference value here is "
    "identifying the tool binary itself, not recognising protected programs. "
    "Compiled directly rather than through upstream's Makefile, which "
    "hardcodes -s on the link line (nm reports no symbols at all on the "
    "result), never creates the bin/ directory its object files are written "
    "to, and whose install rule copies a bin/main that no rule builds. "
    "Built at -O0 rather than upstream's -Os because obfs_decode is "
    "byte-identical to obfs_encode and identical-code folding reduces it to "
    "a one-instruction tail jump at -Os and -O2; at -O0 it is a 140-byte "
    "(x86) / 163-byte (x64) body. MinGW runtime that carries no symbol "
    "remains in the sample - ___chkstk_ms and, on x64, fourteen unnamed "
    "kernel32 import thunks - because the glue filter matches on symbol "
    "name and cannot act on an unnamed function."
)


RECIPES = {
    "Obfuscator4g3nt47_2023-02-26": Recipe(
        family="Obfuscator4g3nt47",
        version="2023-02-26",
        upstream="https://github.com/4g3nt47/Obfuscator",
        license="GPL-3.0-or-later (Copyright (C) 2022 Umar Abdul)",
        # No tags upstream, so the pin is the full commit. 2023-02-26 is that
        # commit's author date and is what the version records.
        source=Source(git_url="https://github.com/4g3nt47/Obfuscator.git",
                      git_ref="f759d28cf6c2bc17377d4ee7373ff248cf8a8072"),
        build=_BUILD,
        # is_library stays true, as it is for every executable in this corpus
        # (q3vm.exe, lua.exe, bzip2.exe): MCRIT keys its library-versus-malware
        # views off that flag, and validate refuses a reference sample without
        # it. It says "this is reference material", not "this is a .dll".
        artifacts=[Artifact(path="obfuscator.exe", component="obfuscator.exe")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O0 -Wall (sources compiled directly; upstream's "
                    "Makefile is -Os -s and does not build, see notes)",
        notes=_NOTES,
        # Seven is the whole project, counted in src/obfuscator.h plus main().
        # Not a floor lowered to make a build pass - the artefacts come out at
        # 10 and 22 and clear the default 8 without it. It states the count
        # this family is admitted on, which is its own code and not the
        # unnamed MinGW thunks the glue filter cannot reach.
        min_functions=7,
    ),
}
