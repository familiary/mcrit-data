# Reference data generation

`scripts/build_corpus.py` builds reference data from unmodified upstream
source, for cases where the IDA Pro / [lib2smda](https://github.com/danielplohmann/lib2smda)
route is not available. It follows the same pipeline the repository README
describes, with the IDA stage replaced by a direct SMDA pass over PE images:

    fetch -> build -> smdaify -> export -> package -> validate

    pip install -r scripts/requirements.txt
    python scripts/build_corpus.py list
    python scripts/build_corpus.py build libzlib_1.3.1
    python scripts/build_corpus.py validate            # --deep also looks for
                                                       # PicHashes shared across
                                                       # families, above a
                                                       # --min-instructions floor
                                                       # --strict also fails on
                                                       # the IDA-derived data
    python scripts/build_corpus.py readme --update     # rewrite the README
                                                       # tables from provenance

Three more commands exist for correcting what is already committed, so that a
change which alters no disassembly does not cost an hours-long rebuild. All
are idempotent, and none is a substitute for regenerating when a build
actually changes:

    python scripts/build_corpus.py reprocess    # recompute the statistics block
    python scripts/build_corpus.py refilter     # re-apply the runtime filter,
                                                # for when the measured baseline
                                                # has improved since a build
    python scripts/refresh_provenance.py        # re-derive licence, build flags,
                                                # upstream and notes from recipes

`refilter` exists because the glue baseline is measured rather than
hardcoded, which keeps it from rotting with the next compiler but also lets
it improve after a family has been committed. It has twice, and both rounds
were found the same way: by running `validate --deep` over the whole corpus
and asking what the surviving cross-family PicHashes actually were.

**Round one, libgcc's division helpers.** The x86 probe gained 64-bit
division, and with it `__divdi3`, `__moddi3`, `__udivdi3`, `__umoddi3`,
`__divmoddi4` and `__udivmoddi4` - which 44 of the 154 committed MinGW
artefacts were carrying under a library's name, one to six functions each,
148 in all. `__udivmoddi4` is the same code in every x86 binary that divides
a 64-bit integer, and at 122 to 175 instructions each carries a full minhash
(MCRIT's floor is ten), so they distorted fuzzy similarity as well as exact
matching.

**Round two, the builtin trap.** The probe already *called* `floor`, `sin`
and `localtime`, and it made no difference: GCC knows them as builtins and at
`-O2` folds the call or emits an instruction, so the libmingwex bodies were
never linked into the probe and never entered the baseline - while a library
calling `floor()` on a value the compiler cannot see does link it. `floor`
was sitting in Lua, libpng, libxml2 *and in `data/MinGW` itself*, which is as
plain a demonstration of misattribution as this corpus offers. Taking the
functions' addresses and calling through a volatile pointer defeats the
builtin. The same round added both `time_t` widths of `gmtime_s` and
`localtime_s` - MinGW's default is 64-bit, so a probe calling only `gmtime_s`
never links the 32-bit pair that libraries built against older headers call
by name - and `_vscprintf`, behind which sit `_emu_vscprintf` and
`_init_vscprintf`. That round removed 277 functions from 37 artefacts and
took the baselines from 3054 to 3101 symbols on x86, 2857 to 2900 on x64.

Together: **425 functions** of compiler runtime, and the cross-family
PicHashes `validate --deep` reports fell from **76 to 58**. Run
`refilter --dry-run` first to see the scale of any future round.

The 58 that remain are the measured floor rather than an outstanding defect,
and `validate --deep` no longer fails on them. It fails on one kind of
collision only - the kind both rounds above were found by, one symbol name
repeated across every family sharing the hash - and reports the rest as
`NOTE` lines with their counts. The two commands agree because they share
one classifier, `corpus.validate.classify_collision`.

For the same reason, the 21 pre-existing problems in `data/MSVC` and
`data/Golang` described below are reported without failing the run: they are
in IDA-derived families that carry no `provenance.json`, which this pipeline
neither produced nor can regenerate. `--strict` fails on them too, for
whoever is actually repairing that data. Everything in a generated family
still fails as it always did.

**Where the deep check belongs in CI.** Not in
`.github/workflows/windows-reference-data.yml`, which is the only workflow
here today. That job prunes `data/` down to the artefacts it has just built
before it validates, so a whole-corpus run there would be measuring a corpus
with most of three families deliberately removed - and would fail on the
README links pointing at the files it removed. Its per-family
`validate data/<family>` calls cannot host `--deep` either: a shared PicHash
needs three families to be one, so a single-family root can never report
anything. The check wants a Linux job over the whole committed corpus,
triggered by changes to `data/**` or to the code that decides what
artefacts contain (`corpus/baseline.py`, `corpus/smdaify.py`,
`corpus/refilter.py`, `corpus/validate.py`), running
`python scripts/build_corpus.py validate --deep`. Budget about twenty
minutes: it extracts every `.7z` and decompresses every `.mcrit`.

`scripts/explain_collisions.py` sorts the survivors into the two kinds:

* **C++ standard library template instantiations** - `std::vector<T>::_M_realloc_insert`,
  `std::_Rb_tree`, `std::basic_string` constructors. These compile to
  identical code for any pointer-sized `T`, so every C++ project using a
  `vector` genuinely contains those bytes. Calling that misattribution would
  mean claiming libstdc++ header code cannot appear in a library that uses
  libstdc++.
* **Short-body coincidences** - ten- to seventeen-instruction functions whose
  names differ entirely between the families sharing them (`_EVP_EncryptInit_ex`
  against `_LZ4_compress_limited`). Those are not the same function; they are
  small bodies that happen to hash alike, which is what the instruction floor
  bounds rather than eliminates.

Today that split is 21 standard-library instantiations, 32 short-body
coincidences and 5 hashes that carry no symbol in any family, with nothing
in the leakage bucket. (It was recorded here as 26 / 27; that count came
from a rule which called a hash standard-library code as soon as *one* of
the names sharing it was a `std::` one, so seven short-body coincidences
that happened to include a libstdc++ symbol were filed under the wrong
heading. A hash is standard-library code now only when every name sharing
it is - which changes no verdict, since the leakage test needs all the
names to be equal anyway.)

Measured four ways, that bucket is empty on merit rather than by
construction: with the standard-library exemption keyed on any name or on
every name, and testing "the symbol is declared in `std::`" or the looser
"`std::` occurs anywhere in the name", all four combinations put zero
hashes in it. The tight test is the one in the code, because the loose one
excuses `google::protobuf::StringAppendF(std::__cxx11::basic_string<...>*,
...)` - protobuf's own code, in a corpus where protobuf, abseil and re2
link each other statically, which is the next leakage this gate is likely
to meet.

Patching in place rather than rebuilding is only sound if it produces what a
rebuild would, and that was measured, not assumed: re-exporting a committed
report and diffing against the committed `.mcrit` leaves one difference, the
`timestamp` inside each `function_labels` entry that MCRIT writes when it
records a label. Labels, minhashes, PicHashes, sample entries and the export
config are identical, and a rebuild would move that timestamp too. The
archive holds the same functions, statistics and binweight the pipeline's own
filter would write, and parses equal - though not always byte for byte, since
the pipeline sorts integer keys numerically and this sorts the stored string
keys lexicographically. Nothing reads them by key order.

What it does *not* reproduce is anything describing the disassembly, because
it does not re-run SMDA: the report's `timestamp` and `execution_time`, and
provenance's `generated`, `smda_version` and `compiler`, are left as the
build wrote them. The binary is not rebuilt, so the recorded `sha256` stays
correct. The README tables render version, toolchain, component and paths -
never function counts - so nothing needs re-rendering afterwards.

Three ways this command could quietly do nothing, or quietly do damage, are
refused rather than reported as success: a baseline that comes back empty
because the probes did not build; a toolchain this host cannot measure at all
(the MSVC families on a Linux checkout, which is skipped rather than failed);
and a re-export that lost minhashes the committed file had, which MCRIT's
hashing job can do without raising. That last one would be unrecoverable - a
second pass finds no glue in the already-filtered archive and skips - so it
is checked before the committed file is touched.

Generated files land in `data/<Family>/<arch>/{smda,mcrit}/` under the naming
scheme the `libzlib` family already uses,
`<family>_<version>_<toolchain>_<arch>_<component>`. Everything that does not
fit in the SMDA metadata block - source URL and digest or pinned commit,
compiler, build flags, and any functions removed - is recorded in
`data/<Family>/provenance.json`, so an artefact stays traceable to the exact
upstream source it came from.

## What this pipeline can and cannot do

SMDA has no COFF/`ar` loader, so static `.lib`/`.a` archives remain out of
reach without IDA. Recipes therefore build a **DLL or EXE**. That covers only
the functions the linker actually pulled in, rather than every object in an
archive, which is a real coverage difference from the IDA-derived families
and is why the MinGW rows are described separately in the README.

Two things matter enough to be enforced in code rather than left to care:

* **Symbols.** MinGW writes a COFF symbol table into unstripped output and
  SMDA reads it, which gets these reports to roughly the symbol quality of
  the IDA-with-symbols path (zlib 1.3.1: 195 of 198 functions named). Several
  upstream build systems strip by default and do it from inside the makefile,
  where an environment variable cannot reach - zlib's `win32/Makefile.gcc`
  and Lua's `mingw` target both do. A report whose functions are mostly
  anonymous is treated as a build failure, not as data.
* **Attribution.** Every MinGW-linked binary carries compiler runtime code -
  startup and unwind glue, and whatever of libmingwex the project happens to
  pull in, such as the `dtoa` helpers behind `gzprintf`. Left in place it
  would be attributed to the library's family and duplicate `data/MinGW`.
  `corpus/baseline.py` measures that code instead of hardcoding it, by
  building probe DLLs with the same toolchain; a function is dropped only
  when its symbol **and** its PicHash match the probe, so a project that
  ships its own version of a runtime symbol keeps it.

There is a third trap that the pipeline cannot catch for you, because it is a
link-line choice rather than a build outcome: linking a C++ sample with
`-static-libstdc++ -static-libgcc` pulls roughly 13,500 libstdc++ and libgcc
functions into it, which would then be attributed to whatever family is being
built. Build C++ samples with `-shared-libgcc`, and use `-static` only when
libstdc++ itself is the intended subject.

The export is produced by a real MCRIT `MinHashIndex` against the in-memory
storage backend, and the writer refuses to emit a file whose minhash and
shingler configuration hashes do not match the ones every `.mcrit` in this
repository already carries - an export that disagrees would import but never
match anything.

In-memory is also the cost: exporting OpenSSL 3.5.8's `libcrypto.dll`, the
largest sample here, peaked at 9.4 GB resident and was OOM-killed on a 15 GB
machine that was running two other builds at the same time. The largest
families are worth building on their own.

## How reproducible this is, measured

Two independent Windows CI runs of the same commit produce **byte-identical
binaries**: same `sha256` for every VX-API, BlackBone and SysWhispers
artefact. That needs `/Brepro` on the link, without which MSVC stamps the PE
with the build time; the MinGW side gets the same property from `7z
-mtm=off -mtc=off -mta=off`, since the stored file times were otherwise the
only thing that changed when a report did not.

What is *not* reproducible, stated precisely, because the useful version of
this claim is the narrow one:

* The `.smda` report's own content differs between runs in exactly two
  fields, `timestamp` and `execution_time`, which SMDA writes about its own
  run. Every report already in this repository carries those, so they stay.
* Those fields sit inside the compressed payload, so the `.7z` is a wholly
  different blob even though the report is otherwise identical. git records
  it as a binary change, not a two-line diff.
* The `.mcrit` carries a third timestamp of its own, in the MCRIT sample
  entry.
* `provenance.json` records a `generated` date, which changes when a
  regeneration crosses a day boundary.

So: the *binaries* are reproducible and their recorded digests are stable,
which is what provenance rests on. The files around them are not
byte-stable, and a regeneration of unchanged data still shows up as a diff.

## The MSVC half

Every library family that can be built with MSVC now carries an MSVC
artefact beside its MinGW one, from the same upstream tag. That is 31
families and 96 artefacts, built by
`.github/workflows/windows-reference-data.yml` on `windows-2022` runners,
one job per architecture.

The reason is the one the section below on prebuilts opens with: a MinGW
reference matches a MinGW-built binary well and an MSVC-built one only
weakly, and most Windows software an analyst meets is MSVC-built. For C
that gap is narrow - the same source, two code generators - but for C++ it
is most of the signal, because name mangling, exception tables, vtable and
thunk shapes and template instantiation all differ. cryptopp, protobuf,
abseil, re2, nlohmann_json and 7-Zip were the families this mattered most
for, and they were MinGW-only until now.

**Nothing in the workflow names a recipe or a family.** Each job asks
`build_corpus.py list --toolchain msvc_<arch> --names-only` which recipes
declare the toolchain it has, and `--families-only` which corpus
directories those recipes file into, so adding a recipe under
`corpus/recipes/` is the whole change. A recipe that fails costs itself and
not the wave: the build step records its exit code and lets the rest run,
and a final step re-prints every failure and fails the job.

Artefacts are uploaded rather than committed by CI, and come back in with:

    python scripts/import_ci_artifacts.py --run <id>

which verifies each one three ways before it touches `data/` - the
downloaded zip against the sha256 GitHub records for it, each `.smda`
report against the sha256 it states for its own binary, and each `.mcrit`
export against the report it was made from - and merges the two jobs'
provenance per architecture. Nothing about an artefact is taken on trust
because it arrived from CI.

**The glue baseline is measured for MSVC too**, by `corpus/baseline.py`,
and it has to be: under `/MD` the CRT is imported rather than linked, but
the C++ half of the runtime - STL template instantiations, ATL, the EH
machinery - is compiled into every artefact that uses it and would
otherwise be filed under a library's name. The probe set grew from 15
translation units to 34 over two rounds for exactly that, and both rounds
were found the same way the MinGW ones were: by asking `validate --deep`
what the surviving cross-family hashes were called. What made the MSVC
rounds harder than the MinGW ones is that MSVC instantiates a member
template on the *argument's* category and width, so a probe calling
`emplace(wstring, 2u)` emits a different symbol than a library calling
`emplace(wstring, someUnsignedLong)`, and `is_glue` matches on the symbol
name as well as the PicHash. 121 of BlackBone's 124 residual names turned
out never to have been emitted by the first probe at all.

**`/INCREMENTAL:NO` on every MSVC link**, which the first round of these
recipes did not have and needed. `link /DEBUG` implies `/INCREMENTAL`, and
the `/OPT:NO*` forms these recipes pass do not suppress it - only
`/OPT:REF`, `/OPT:ICF` and `/OPT:ORDER` are documented to. An incrementally
linked image reaches each function through a table of one-instruction jump
thunks, and SMDA recovers every one of those as a function of its own,
unnamed. The table is unmistakable once looked at: in nlohmann_json 3.12.0
x64 it is 2866 entries exactly five bytes apart, running unbroken from
`base+0x1005`, with no other function inside its span.

Seven recipes were affected - nlohmann_json, bzip2, libtomcrypt, OpenSSL,
cryptopp, Lua and sqlite3 - and at the worst of them roughly half of what
the corpus was calling a function was a thunk: 4882 of libcrypto x86's
12,861, 2936 of nlohmann_json x86's 5205, 978 of libtomcrypt x86's 2030.
Nothing else was: the CMake recipes inherit `/INCREMENTAL:NO` from CMake's
own Release default, the MSBuild ones get it from their project files,
VX-API's `/FORCE:UNRESOLVED` makes link.exe ignore `/INCREMENTAL`
altogether, and SysWhispers passes no `/DEBUG` so nothing is implied. The
one-instruction jumps that remain in the unaffected artefacts are ordinary
tail calls and are named - 185 in VX-API, 211 in abseil, 149 in libcurl.

mbedTLS is the one family whose MSVC shape differs from its MinGW one. It
cannot be linked as three DLLs by MSVC out of unmodified 3.6.7 source -
four cross-library references are to *data*, and a CMake-generated export
table supplies only `__imp_` for those, which needs a `__declspec(dllimport)`
mbedTLS does not have anywhere in its tree. Upstream has had the issue open
since 2016 and its own MSVC build is a static library. So this recipe builds
the three static archives and links them whole into one DLL, the way
cryptopp is built here: component separation is lost, the whole TLS layer is
kept, and the recipe's docstring records what was read to establish all of
it.

## A gap in the existing MinGW coverage

Worth recording because it affects data that is already committed. The
`data/MinGW` x64 reports contain libstdc++ and libsupc++ (r38 x64: 9,806
functions, of which 4,714 demangle into `std`, plus `__gnu_cxx`, `__cxxabiv1`
and the unwinder). The x86 reports do not: r38 x86 has 2,818 functions, 692 of
them `Name@N` stdcall import thunks and the remainder import-library entries,
with no `_ZN`/`_ZSt` symbols, no `_Unwind_*` and no libgcc helpers at all.

So 32-bit libstdc++ is not covered anywhere in the corpus, and the x86 MinGW
family looks under-processed relative to its x64 counterpart rather than
merely smaller. That is a question for the maintainer about how the x86
MinGW inputs were crawled, not something a new contribution should paper
over by adding a separate libstdc++ family.

## Adding a recipe

Recipes are declarative (`corpus/recipes/*.py`) and carry no logic, so every
project goes through the same code path. Pin sources by SHA-256 for a release
tarball or by tag/commit for a clone; never by a moving branch.

## Targets investigated but not built

Recorded here so the analysis is not repeated:

| project | issue | why not |
| --- | --- | --- |
| sRDI, pe_to_shellcode, donut loaders | #3, #5, #6 | not rebuilt: upstream commits the MSVC-compiled shellcode, and those exact bytes are what ships in the releases and the PyPI packages. They are extracted and disassembled as buffers instead. A MinGW port would be a code shape nobody runs |
| donut generator | #5 | statically links the vendored `lib/aplib64.lib`, and aPLib is already a family here - the generator would duplicate it under donut's name. It is also built with no `-O` |
| SysWhispers2_x86 | #9 | pre-generated MASM shipping no licence file of any kind; a maintainer decision rather than a technical one |
| SysWhispers2, SysWhispers3 | #9 | cross-build cleanly, but the generated stubs are 2-15 instructions differing by one immediate - a large, low-value cluster. v1, whose stubs carry a full PEB version ladder, is covered instead |
| sc4cpp | #14 | upstream repository and the owning GitHub account are both gone (404); the surviving derivative needs clang-cl |
| BlackLotus | #15 | not an open-source project: leaked bootkit source with no licence, and the UEFI half does not build from the repository as published (it references `global/` and `gnu-efi/` directories that are not there) |
| gperftools (tcmalloc) | #10 | its Windows port targets MSVC; `src/windows/port.h` clashes with mingw's `nanosleep` linkage and needs a source patch |
| google/tcmalloc | #10 | Bazel-only and Linux-only - it cannot produce a PE at all. Issue #10's "tcmalloc" is almost certainly gperftools |
| gRPC | #10 | cross-building needs a full native build first to obtain `protoc` and `grpc_cpp_plugin`, plus boringssl (which needs Go); 45-90 minutes for two architectures, and its statically-linked-into-Windows-malware rate is close to zero |
| BlackBone kernel driver | #8 | a separate solution needing the WDK; the user-mode library is built |

VX-API (#4), BlackBone (#8) and SysWhispers v1 (#9) were on this list and are
not any more: they need ATL, the DIA SDK or MASM, none of which exists for
GCC, so they are built with MSVC on a `windows-2022` runner by
`.github/workflows/windows-reference-data.yml` rather than approximated.
Crypto++ (#10) has also left it - upstream's own `cryptopp.dll` target
exports only the FIPS subset, but its GNUmakefile builds `libcryptopp.a`
cleanly and that is linked into a DLL with `--whole-archive`.

None of the three MSVC builds patches upstream source. BlackBone needs one
compiler switch that its project file does not set (`/permissive`, because
`/std:c++latest` on v143 implies `/permissive-` and `ProcessModules.cpp`
omits a `typename`), and it arrives through an `ItemDefinitionGroup` imported
with `ForceImportBeforeCppTargets`, which leaves the tree untouched.

Anything requiring upstream source to be patched is deliberately absent:
reference data is only worth having if it describes code that upstream
actually ships.

## Prefer a prebuilt where upstream publishes one

This tooling builds two flavours - GCC 13.2 with msvcrt and mingw-w64
headers, and MSVC v143 with the DLL runtime - but still only two, each at
one version, and only for the release configuration a recipe pins. A
reference matches a binary built the same way well and one built another
way weakly, so what is here is coverage rather than a substitute for the
real thing. Where upstream or a trusted rebuilder ships Windows binaries,
harvesting those is both cheaper and closer to what is encountered:

* **sqlite.org** retains `sqlite-dll-win-{x86,x64}-*.zip` back about fifteen
  years and publishes a SHA3-256 for every file. These are MinGW-built (no
  Rich header, linker 2.25), but they are the exact bytes redistributed
  inside a great deal of commodity software.
* **ShiftMediaProject** publishes MSVC builds with PDBs across msvc12-msvc17
  for, among others, libxml2 - the same provenance route the existing
  `data/libzlib` family came from. Note the organisation was archived in
  2026, so it is a frozen source: its OpenSSL stops at 1.1.0i and it will
  never cover newer releases.

Harvesting a prebuilt still belongs in a recipe, so the digest and source URL
land in `provenance.json` like everything else.
