# Reference data generation

`scripts/build_corpus.py` builds reference data from unmodified upstream
source, for cases where the IDA Pro / [lib2smda](https://github.com/danielplohmann/lib2smda)
route is not available. It follows the same pipeline the repository README
describes, with the IDA stage replaced by a direct SMDA pass over PE images:

    fetch -> build -> smdaify -> export -> package -> validate

    pip install -r scripts/requirements.txt
    python scripts/build_corpus.py list
    python scripts/build_corpus.py build libzlib_1.3.1
    python scripts/build_corpus.py validate
    python scripts/build_corpus.py readme libzlib

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
| sRDI shellcode | #3 | needs MSVC `/ORDER:@…` and `/ENTRY:LoadDLL`; a MinGW port would be a code shape nobody ships |
| VX-API | #4 | needs ATL and `__try/__except`; ~14 of 251 sources cannot be built here, and real-world use is MSVC |
| pe_to_shellcode stubs | #6 | need `cl` + `ml`/`ml64` + the external `masm_shc`; the tools additionally need source patches |
| BlackBone | #8 | library needs three source patches plus the DIA SDK and ATL; the driver needs the WDK |
| SysWhispers 1, SysWhispers2_x86 | #9 | MASM-only output, rejected by both nasm and GAS; SysWhispers2_x86 also ships no licence |
| SysWhispers2, SysWhispers3 | #9 | cross-build cleanly, but need a hand-written harness to link, and the generated stubs are 2-15 instructions - the reference value is in the `SW2_`/`SW3_` helper routines |
| sc4cpp | #14 | upstream repository and the owning GitHub account are both gone (404); the surviving derivative needs clang-cl |
| BlackLotus | #15 | not an open-source project: leaked bootkit source with no licence, and the UEFI half does not build from the repository as published (it references `global/` and `gnu-efi/` directories that are not there) |
| Crypto++ | #10 | the `cryptopp.dll` target is broken for GCC cross-builds upstream; the only working artefact is an 18 MB `cryptest.exe` with ~28k functions, which is a corpus-sizing decision rather than a build one |
| gperftools (tcmalloc) | #10 | its Windows port targets MSVC; `src/windows/port.h` clashes with mingw's `nanosleep` linkage and needs a source patch |
| google/tcmalloc | #10 | Bazel-only and Linux-only - it cannot produce a PE at all. Issue #10's "tcmalloc" is almost certainly gperftools |
| gRPC | #10 | cross-building needs a full native build first to obtain `protoc` and `grpc_cpp_plugin`, plus boringssl (which needs Go); 45-90 minutes for two architectures, and its statically-linked-into-Windows-malware rate is close to zero |

Anything requiring upstream source to be patched is deliberately absent:
reference data is only worth having if it describes code that upstream
actually ships.

## Prefer a prebuilt where upstream publishes one

Everything this tooling builds is one flavour - GCC 13.2, msvcrt, mingw-w64
headers - while most Windows software analysts meet is MSVC-compiled. A
MinGW reference matches MinGW-built binaries well and MSVC-built ones only
weakly, so it is additional coverage, not a substitute. Where upstream or a
trusted rebuilder ships Windows binaries, harvesting those is both cheaper
and closer to what is encountered:

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
