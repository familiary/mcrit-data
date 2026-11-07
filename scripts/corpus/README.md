# Reference data generation

`scripts/build_corpus.py` builds reference data from unmodified upstream
source, for cases where the IDA Pro / [lib2smda](https://github.com/danielplohmann/lib2smda)
route is not available. It follows the same pipeline the repository README
describes, with the IDA stage replaced by a direct SMDA pass over PE and ELF
images:

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
it improve after a family has been committed. It has four times - twice
for MinGW and twice more when the MSVC artefacts arrived - and every round
was found the same way: by running `validate --deep` over the whole corpus
and asking what the surviving cross-family PicHashes actually were.

`refilter` can only re-apply a baseline this host can measure, so the two
MSVC rounds were applied by rebuilding on the Windows runner rather than in
place.

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

Those two rounds together returned **425 functions** of compiler runtime,
and took the cross-family PicHashes `validate --deep` reported from **76 to
58**. Run `refilter --dry-run` first to see the scale of any future round.

**Rounds three and four, the MSVC C runtime.** Importing 99 MSVC artefacts
put 20 leakage findings into the deep check at once, all of them Microsoft's
code under a library's name, and two of them sharing a hash with `data/MSVC`
itself. Round three added six probe translation units covering `_allshr`,
`` `vector constructor iterator' ``, `__EH_prolog`/`_EH_prolog2`, `sprintf`
and `_vsprintf_l`, and the `std::string` reallocation lambdas. Round four
was one line: the same conversion probe compiled a second time with
`/arch:IA32`, because at the default `/arch:SSE2` cl spills a double return
value to memory and reloads it into XMM, so every conversion reached the
`_ftol3` family the baseline already had rather than the `_ftol2` family
that was leaking. 34 MSVC probe compilations became 45.

Two more probes were found by the gate that reports a probe which will not
compile, added at the same time: `probe_msvcrt.c` had never built at all
(cl rejects a cast function pointer as a file-scope initializer) and neither
had `probe_atl_typeinfo.cpp`. Both had been failing silently on every run
since they were written.

**The fifth round.** Adding
4g3nt47/Obfuscator turned up a whole half of stdio that `_PROBE_DLL` never
calls - it formats, seeks and reads blocks, and never once calls `printf`,
`puts`, `fgetc`, `feof`, `ferror`, `clearerr`, `rewind`, `remove` or `atoi`.
`_PROBE_STDIO` now measures that surface, registered three ways on the MinGW
side: as a DLL, as an EXE, and as an EXE a second time at `-O0`, because
mingw-w64's `stdio.h` defines `printf` and its relatives as static inline
wrappers compiled from each calling translation unit, so their PicHash
follows the optimisation level (25 instructions at `-O0`, 19 at `-O2`, 18 at
`-Os` for x64 `printf`). The baselines went from 3101 to 3126 symbols on x86
and 2900 to 2926 on x64.

`refilter --dry-run` over the committed corpus with that baseline reports
**67 artefacts in 14 families, 510 functions**: mbedTLS 14, OpenSSL 9, Lua
and LuaJIT 6 each, abseil, libcurl, libtiff and libxml2 4 each, q3vm 4,
libevent and libuv 3, bzip2, cryptopp and libpng 2. `printf` is much the
largest share (106 bodies across 14 artefacts, one per translation unit that
calls it), then `fprintf`, `ferror`, `fgets`, `feof`, `remove` and
`clearerr`. Every name in the list is a C library name; no project code is
in it.

It was applied, in commit `4bf28b5`, after the dry run above had been read:
67 artefacts corrected, 510 functions, `refresh_provenance --check` clean
across all 51 families afterwards and `validate` at 0 problems.

One thing it did not do, which is worth stating because the opposite was
expected: it did not move the cross-family census. None of those 510
functions could have been in it. `ferror`, `feof`, `clearerr`, `rewind` and
the import thunks are a handful of instructions each and sit below the
ten-instruction floor the census counts at. A refilter round corrects
misattribution; it is not a collision fix, and the two numbers move for
different reasons.

**The sixth round, and `__scrt_common_main_seh`.** That finding is the one
the paragraph above left open, and what it needed was MSVC in front of it
rather than more reasoning. The probe had the name all along: `probe_md_exe.c`
emits `__scrt_common_main_seh` at 95 instructions, PicHash
`470324384558745095`, which is none of the three bodies in the corpus - so the
filter, which matches on symbol *and* PicHash, correctly kept the artefacts'
copies. Only the body disagreed.

The cause is the link line. Every MSVC recipe here passes `/INCREMENTAL:NO`
and no probe did, because `link /DEBUG` implies `/INCREMENTAL` - so every
probe image in `baseline.py` was incrementally linked while no artefact is,
and an incrementally linked image reaches each function through a table of
five-byte jump thunks. The same translation unit relinked
`/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF` emits
`11855707620856894801` at 99 instructions, which is exactly the leaking body,
while the incremental registration beside it still emits 95. That is proof by
elimination rather than a story: one source, two link lines, two hashes.
`__scrt_common_main_seh` is the only function in the startup chain carrying an
`__except`, so it is the only one whose recovered extent follows the layout
rather than the bytes, which is why its fourteen neighbours matched and it did
not. On x86 the two links agree - `14520804967954049952`, 112 instructions -
and no x86 artefact carries the name, consistent with the funclet being an
x64 shape.

The same round measures the half of `<stdio.h>` that writes to a stream it was
not handed. `printf`, `vprintf` and `vfprintf` are `_CRT_STDIO_INLINE`
definitions under `/MD`, so a body is compiled into every object that calls
one, and no MSVC probe had ever called one: `_PROBE_MSVCRT_PRINTF` covers the
buffer-filling half and `_PROBE_DLL` calls `fprintf`, which is where the
`_vfprintf_l` chain below them came from. The new probe emits each of the six
bodies the committed reports carry, hash for hash - `printf` at
`121597203084696572` (25 instructions) on x64 and `14739679411554417350`
(17) on x86, `vfprintf` at `18319647447110778407` (19) and
`15763949986211485148` (10), `vprintf` at `3515039425838154103` (21) and
`7807335352819369265` (13).

Four probe registrations, taking the MSVC run to 52 probe compilations on x64
and 53 on x86 - the count `crt_glue` now reports, which includes the four
sources it shares with the MinGW side: the stdio source as a DLL and as an
EXE, a plain console `main` that
prints linked the recipes' way, and `probe_md_exe.c`'s source relinked the
same way so the broad EXE surface is measured non-incrementally as well. The
MinGW and Linux baselines do not move - 3133 symbols on x86 and 2944 on x64,
the same name-to-PicHash map before and after, measured both ways. With the
round in, the MSVC baselines measure 10,946 symbols and 12,672 PicHashes on
x64 and 10,649 and 12,975 on x86. `crt_glue` now says that in one `INFO`
line per toolchain, because the failure this file is most afraid of is a
baseline that quietly got smaller and nothing in a fifty-thousand-line log
said so.

The sixteen artefacts of Lua, LuaJIT, MemoryModule, bzip2 and q3vm were
rebuilt on the runner to measure what it costs them. 14 of the 16 change and
38 functions leave, 13,498 kept becoming 13,460: `printf` from 8 artefacts -
all four LuaJIT, both MemoryModule and both q3vm x64 - `vprintf` and
`vfprintf` from the four LuaJIT, `__scrt_common_main_seh` from Lua 5.1.5 x64,
Lua 5.4.8 x64, MemoryModule x64 and bzip2 x64, and `fflush` and `fputs` from
ten and eight of them as thunks. Over those five families plus Hidden,
CallObfuscator, libtiff and mbedTLS, `validate --deep` goes from 12
cross-family hashes with one leakage finding - `__scrt_common_main_seh` across
Hidden, Lua, MemoryModule and bzip2 - to 9 with none.

The whole MSVC side was then rebuilt, 54 recipes per architecture and 114
artefacts, and that run is the measurement to quote. 38 of the 114 change and
**78 functions** leave them, 199,384 kept becoming 199,306, across 15
families: `printf` 15 bodies in LuaJIT, MemoryModule, libxml2, mbedTLS,
protobuf and q3vm; `vfprintf` 10 in LuaJIT, libtiff and libxml2; `vprintf` 4
in LuaJIT; `__scrt_common_main_seh` 5 in Hidden, Lua, MemoryModule and bzip2 -
which is every family the failing hash spanned, so the finding goes rather
than shrinks; and `fflush` and `fputs` 45 thunks between them across eleven
families. One more name changed and this round does not explain it:
`std::basic_stringbuf<char,...>::pbackfail` in protobuf 31.1 x86, one body.
No probe added here can emit it - all four are C - so the honest reading is a
difference in protobuf's own rebuild rather than in the baseline, and it is
recorded rather than claimed.

The two artefacts that do not change in the five families above are q3vm x86,
and they are the honest edge of this round: q3vm builds with whole-program optimisation, its `printf` bodies are 23
and 20 instructions where every other x86 artefact's is 17, and a probe built
at `/O2` emits none of them. Those two bodies are single-family and were never
leakage. The same is true of the 98-instruction `__scrt_common_main_seh` in
q3vm x64 and the 109-instruction one in CallObfuscator, which is `wmain`'s
startup object.

Two things this round does not do, stated because the numbers above would
otherwise be read as more than they are. It does not correct the committed
MSVC artefacts, and the measurement above is a measurement rather than an
import: `refilter` can only re-apply a baseline this host can measure, and
`msvc143_x86`/`msvc143_x64` do not exist on a Linux checkout, so it skips
every MSVC family there - `refilter --dry-run` says so per toolchain - and the
correction has to come from a rebuild of all 54 MSVC recipes per architecture
on the runner, which is what a push touching `baseline.py` triggers. Nothing
in `refilter` itself is MSVC-hostile; what it lacks is a host.

And it leaves the rest of the surface LuaJIT instantiates: its images carry
the whole UCRT inline set, where `printf_s`,
`wprintf`, `wprintf_s`, `_printf_p` and `_wprintf_p` share `printf`'s body and
`vfprintf_s`, `vfwprintf_s`, `vfscanf`, `vfwscanf`, `_vfprintf_p` and
`_vfwprintf_p` share `vfprintf`'s, so both hashes stay in the cross-family
census under LuaJIT's name. That is forty-odd names, half of them wide, and a
measurement of its own.

**The seventh round: the wide and secure stdio wrappers.** That measurement is
this one. `validate --deep` on the whole corpus still failed on PicHash
`10336305819058912646`, 28 instructions, named `swprintf_s` and shared by
BlackBone, EDRSandblast and al-khaser, and the #78 families carry a wider tail
of the same kind - `wprintf`, `_vfprintf_l`/`_vfwprintf_l`, `fwprintf`,
`_vswprintf_s_l`, `vwprintf` - none of which a probe emitted with the body the
artefacts have.

`swprintf_s` was not a missing name. `_PROBE_MSVCRT_WIDE` has called it since
the third round and, measured on the runner, emits one at 28 instructions on
x64 too - PicHash `13530071051526633694`. Same name, same length, another
hash: exactly what the symbol-and-PicHash filter is for, and it kept the
artefacts' copies correctly. What differs is the flags. The same wrapper,
taken by address and built `/sdl`, emits `10336305819058912646` and nothing
else does; BlackBone's x64 configuration is documented as `/sdl`. The rest of
the tail came apart the same way, one flag at a time, and each was found by
building the wrappers under every candidate flag set and comparing against the
committed reports rather than by reading recipes:

* `/sdl` on x64 (and `/sdl` with `/Oy-` on x86, for al-khaser's `/O2`
  `swprintf_s` and `fwprintf`).
* `/Oy-` on x86 only: keeping the frame pointer adds `push ebp`, `mov ebp,
  esp` and `pop ebp` to a wrapper, which is exactly the difference between the
  20-instruction `printf`/`wprintf` in DiskCryptor and al-khaser
  (`12296465484064796685`, `0xaaa5d2355288b00d`) and the 17 every default build
  emits. BlackBone's x86 `fprintf` (14 against 11) is the same effect.
* `/Od`, because al-khaser is built twice: its `/Od` image carries
  `printf`/`wprintf` (22 instructions on x86, 25 on x64 with `/sdl`),
  `_vfprintf_l`/`_vfwprintf_l`, `fwprintf`, `swprintf_s`, `_vsnwprintf`,
  `_vsnwprintf_l`, `_vswprintf_s_l`, `localtime_s` and
  `__local_stdio_printf_options` un-inlined.
* `/Gs0` and `/O1` (x64), and C++ under `/std:c++20` (x64): tried against the
  survivors nothing above reproduced, and they were OpenSSL's `sprintf`,
  `fprintf` and `_vsnprintf` family, libzlib's `snprintf`/`vsnprintf` and the
  22-instruction `printf`/`wprintf` in protobuf and VX-API.

The measurement is the CI log, not a guess. Four dispatches of the Windows
workflow on a scratch branch, each building `cJSON_1.6.0_msvc` on both
architectures with a temporary per-probe log of every stdio-shaped function
and its PicHash and instruction count (runs 42276319638, 42277298368,
42278735210, 42280017368); the last one ran the registrations in this commit,
and nothing is registered that it did not emit a body for that an artefact
carries. The log is not committed.

What the probes now emit, hash for hash, among the names the task started
from (instructions in brackets):

| name | arch | PicHash | carried by |
| --- | --- | --- | --- |
| `swprintf_s` | x64 | `10336305819058912646` (28) | BlackBone, EDRSandblast, al-khaser `/O2` |
| `wprintf` | x64 | `121597203084696572` (25) | EDRSandblast, DiskCryptor, WinPmem, al-khaser `/O2`, LuaJIT |
| `printf`, `wprintf` | x86 | `12296465484064796685` (20) | DiskCryptor, al-khaser `/O2` |
| `wprintf`, `vwprintf` | x86 | `14739679411554417350` (17), `7807335352819369265` (13) | WinPmem |
| `vwprintf` | x64 | `3515039425838154103` (21) | WinPmem |
| `swprintf_s`, `fwprintf` | x86 | `6949881716872909772` (19), `5147500236835420388` (15) | al-khaser `/O2` |
| `wscanf` | x64, x86 | `5430873308725790042` (25), `15708648133356572057` (20) | DiskCryptor |
| `_snwprintf` | x86 | `16701398180549986368` (20) | DiskCryptor |
| `fprintf` | x86 | `8972144503159668082` (14) | BlackBone |
| `printf`, `wprintf` | x64, x86 `/Od` | `9388650845780074387` (25), `807282956642728980` (22) | al-khaser |
| `_vfprintf_l`, `_vfwprintf_l` | x64, x86 `/Od` | `11988831538536686101` (15), `8707119721426719415` (19) | al-khaser |
| `swprintf_s` | x64, x86 `/Od` | `3201430126001659171` (25), `333673324085173386` (22) | al-khaser |

`printf` at `121597203084696572` was already removed by the sixth round; it is
the same body as `wprintf`'s and only the name was missing. 354 distinct
(architecture, name, PicHash) bodies in the committed reports are now
reproduced. Added registrations: 28 on x64 and 33 on x86, taking
`crt_glue`'s probe count to 80 and 86; every one is `/MD`, linked the way the
recipes link, a DLL except one EXE (the two print groups, whose bodies are the
DLL's hash for hash). The groups are the UCRT's whole inline `printf` and
`scanf` families - narrow, wide, `_s`, `_p`, `_l` and `v*` - because LuaJIT
instantiates all of them and its names are the bulk of the effect.

What it costs the artefacts, counted from the committed reports against the
measured bodies rather than from a rebuild: **705 functions across 15
families**, of which LuaJIT is 619 (about 155 UCRT wrappers in each of its four
images, thunks included) and the families this round was opened for are
BlackBone 2, EDRSandblast 2, al-khaser 27 (both images, both architectures),
DiskCryptor 9 and WinPmem 4. The count is of name-and-PicHash matches that the
sixth-round baseline did not already make; `is_glue` does the removal. The
MinGW and Linux baselines do not move: the name-to-PicHash map is
byte-identical before and after for both MinGW toolchains (3133 symbols on x86
and 2944 on x64), measured with the same dump as the sixth round.

What is not reproduced, and so is not registered:

* BlackBone x86 `swprintf_s` (`15224987278223994096`, 14) and
  `_vswprintf_s_l` (`13343053050147212994`, 19). The artefact passes
  arguments to `_vswprintf_s_l` in `ecx` and `edx`, which looks like a
  link-time-code-generation calling convention (`/GL`, `/LTCG`). Probes built `/Ox /Ob2 /Ot /GS- /GL`,
  with and without `/Oy-` and `/LTCG /OPT:REF /OPT:ICF`, emit the same
  functions with stack arguments and 15/14 or 18/17 instructions.
* WinPmem `asprintf` and `aswprintf` (63 to 66 instructions, both
  architectures): the UCRT has no such functions, so these are the project's
  own, not glue.
* OpenSSL x64 `_snwprintf`, `_vsnwprintf`, `_vsnwprintf_l`, `sscanf` and
  `_vsscanf_l`: `/Gs0` reproduces the narrow `sprintf`/`fprintf` family and
  was not tried on the wide and scan groups; this is one more measurement,
  not an obstacle.
* libzlib x86 `_snprintf` and `_vsnprintf`, q3vm v1.3.1 x86 `printf` and
  `fprintf` - q3vm builds `/GL` - and wowGrail x86 `printf` (33): no
  flavour tried reproduces them; the 2026-03-06 q3vm x86 pair did leave in the
  rebuild, which is what put that image below the function floor. LuaJIT x86 `_vwscanf_s_l` (8 instructions) is
  a fragment of a wrapper rather than the wrapper.
* The startup bodies, which are not stdio: DiskCryptor's x86
  `__scrt_common_main_seh$+0x124` (`0xb6f9895ed1a726a6`) and the
  `__scrt_common_main_seh` of dcinst x64/x86 (92 and 110 instructions) and
  al-khaser x64 (109). They belong with the entry-point round.
* The kernel-mode glue (`memcpy`, `memset`, `__security_init_cookie`, ...) is
  the eighth round, below.

What the seventh round did to the corpus, measured by an all-msvc wave on
this branch (run 42333283878, with the sixth round's data as the baseline to
compare against): 20 of the 114 MSVC images change and 653 functions move
from kept to removed, with no kept count rising anywhere. LuaJIT accounts for
619 of them (the count includes one-instruction thunks), then OpenSSL 9,
Lua 6, cJSON 4, libzlib 4, NTTITONHeavensGate 3, and BlackBone, VX-API and q3vm
2 each, protobuf and wowGrail 1. The 2026-03-06 q3vm x86 image is the one that
matters beyond the numbers: its `printf` and `fprintf` leave it and it keeps
six functions of its own, below the default floor of eight, so that recipe
sets `min_functions` to the six it has. v1.3.1 x86 is unchanged. The #78
families (EDRSandblast, al-khaser, DiskCryptor, WinPmem, EDRSilencer) were
rebuilt on their own branches against this baseline and are imported there.

**The eighth round: kernel-mode glue, for drivers only.** Everything above
measures a user-mode image. A `.sys` has no ucrt or vcruntime; what the WDK
links into it instead is a few static libraries and whatever `ntstrsafe.h`
and `ntintsafe.h` compile into the calling unit, and none of that was in the
baseline, so each of the five driver images in the repository carried 10 to 22
functions of it under its own family's name. They were counted from the
committed reports before anything was built: `memcpy` (152 instructions),
`memset` (65), `__cpu_features_init` (59), `__memset_query`,
`__memset_repmovs`, the `__castguard_*_os_handled` trio,
`__GSHandlerCheckCommon`, `GsDriverEntry`, `__security_init_cookie`, the
`__report_*` failure reporters, `RtlFailFast`, and the `ntstrsafe` inlines
(`RtlUnicodeStringPrintf`, `RtlStringCchPrintfW`, ...).

`baseline.kernel_glue` measures them the way the other baselines are measured,
and keeps them apart: `is_glue(function, toolchain, kernel=True)` consults it
only for an image whose file name ends in `.sys` (`smdaify` and `refilter` both
decide that from the name), on top of the user-mode set and never instead of
it, so a user-mode image cannot gain or lose a function from this round - the
only call that changes is the one a driver makes. x64 only: WDK 10.0.26100 has
no x86 kernel target (see `wdk-driver-playbook.md`), so there is no x86 `.sys`
and `kernel_glue` is empty there by construction.

Three flavours of probe, because the survivors came from three link lines.
Each is the 103 translation units `_kernel_sources` writes - a `DriverEntry`,
one unit of SEH, a page-sized frame and variable-length `memcpy`/`memset`/
`memmove`/`memcmp` calls, and one unit per name taken by address (the C
runtime names, `RtlFailFast`, the whole `RtlString{Cb,Cch}*` and
`RtlUnicodeString*` families and twelve `ntintsafe` helpers, taken by address
for the reason the wide-stdio round gave: a call can be expanded in line and
an address cannot) - and a unit that will not compile costs itself, not the
flavour:

* `wdm`: the WDK's own msbuild driver project, WDM, Release x64, TargetVersion
  Windows10, the forced props the driver recipes use. Hidden, BlackBoneDrv and
  APICallProxy are built this way; it links `BufferOverflowFastFailK.lib`.
* `wdm_nogs`: the same with `BufferSecurityCheck` off and `/O2`, DiskCryptorDrv's
  build.
* `cl_link`: `cl /kernel /Zl /GS` and `link /NODEFAULTLIB` against
  `BufferOverflowK.lib`, WinPmemDrv's line. Its `__security_init_cookie` and
  `__report_rangecheckfailure` are different bodies from the FastFail ones.

The measurement is the CI log: two dispatches of the Windows workflow on a
scratch branch, each building the five driver recipes with a temporary
per-probe log (runs 42402246098 and 42403085859). The second ran the code in
this branch plus the five names below, kept in only so that the log would carry
their compiler errors. The result is 162 symbols and 246 PicHashes. The
rebuilt images came out exactly as the committed reports predicted when
re-filtered with those entries (counted locally, then confirmed by the
rebuild): **76 functions, 2462 instructions, across the five images** - Hidden
17 (507 to 490), BlackBoneDrv 22 (321 to 299), APICallProxy 14 (183 to 169),
DiskCryptorDrv 10 (356 to 346), WinPmemDrv 13 (145 to 132) - and `HiddenCLI.exe`,
the one user-mode image in the wave, is 523 functions before and after.

What the entries are, hash for hash, among the survivors in the committed
images (instructions in brackets; every one is x64):

| name | PicHash | carried by |
| --- | --- | --- |
| `memcpy` | `729628813605614666` (152) | all five |
| `memset` | `9661683141091972025` (65) | all five |
| `__cpu_features_init` | `13091074222736779356` (59) | all five |
| `__memset_query`, `__memset_repmovs` | `16342713605483745002` (16), `6643742553189302072` (21) | all five |
| `__castguard_check_failure_os_handled` (16), `_wrapper` (9), `__castguard_slow_path_check_os_handled` (23) | `2138725727597589620`, `8132465082075151443`, `14106821896220680570` | all five |
| `__GSHandlerCheckCommon` | `10950584254824723265` (30) | all but DiskCryptorDrv |
| `GsDriverEntry` | `17538726983033257291` (13) | BlackBoneDrv, Hidden, WinPmemDrv |
| `__security_init_cookie` | `374977537579870673` (12) | APICallProxy, BlackBoneDrv, Hidden |
| `__security_init_cookie` | `2877408483180583694` (22) | WinPmemDrv |
| `__report_gsfailure`, `__report_securityfailure`, `__report_rangecheckfailure` | `14537609155102306236`, `6588078908701986747`, `16800067082027224991` (3 each) | APICallProxy, BlackBoneDrv, Hidden |
| `__report_rangecheckfailure` | `7481953668246422650` (4) | WinPmemDrv |
| `RtlFailFast` | `12325927464713800029` (3) | APICallProxy, BlackBoneDrv, Hidden |
| `RtlUnicodeStringPrintf` | `7519792502405545790` (51) | BlackBoneDrv, Hidden |
| `RtlUnicodeStringCat`, `CatString`, `Copy`, `Init` | `6233312765464530417` (75), `691161227449751944` (59), `7265331077103111775` (69), `9624075325316981261` (38) | BlackBoneDrv |
| `RtlStringCchPrintfW` | `12776501659978149984` (45) | DiskCryptorDrv |
| `RtlULongAdd` | `7595675468641775940` (8) | WinPmemDrv |
| `__chkstk`, `_vsnwprintf` | `1253497258561142223` (1 each) | BlackBoneDrv; BlackBoneDrv, DiskCryptorDrv, Hidden |

The one-instruction rows are import thunks into ntoskrnl, and the baseline
keeps those only when the name is in the runtime's namespace (no capital
letter: `__chkstk`, `_vsnwprintf`, `strlen`), not the kernel API's
(`ZwClose`, `RtlInitUnicodeString`). A thunk to `ZwCreateFile` is a driver
using an API, and putting it in the baseline would take it out of every driver
that imports it; the probes also reference nothing from the Ex/Ke/Mm/Zw/Rtl
export families, so none was measured. String-literal COMDATs (`??_C@_`) the
probes emit are dropped from the baseline for the same reason.

What survives, and why:

* WinPmemDrv `__report_gsfailure` (`786151766786688416`) and
  `__report_securityfailure` (`15435519476439815878`), 9 instructions each. The
  `cl_link` probe emits both from the same `BufferOverflowK.lib` at the same
  length with other hashes (`808649142088531034`, `2807459272347353473`). The
  committed bodies contain `call qword ptr [rip + 0x8f9]` into the import table
  and two rip-relative loads of the cookie, and the likely cause - not
  separately confirmed - is that those displacements follow the image layout;
  the three-instruction FastFail versions have none and match, and so do the
  22- and 4-instruction `BufferOverflowK.lib` bodies. A probe cannot be given
  another image's layout, so these two stay.
* The API thunks (`Zw*`, `Rtl*` imports: 1 instruction each: 123 in
  DiskCryptorDrv, 108 in BlackBoneDrv, 81 in APICallProxy, 76 in Hidden, 43 in
  WinPmemDrv), on purpose. Also the thunks `_local_unwind` (Hidden) and
  `_snwprintf` (WinPmemDrv), which no probe references.
* KMDF and WDF glue (`FxDriverEntry`, `WdfVersionBind`, ...): no committed
  image is a KMDF driver, so there is nothing to measure it against and no
  probe for it. A first KMDF driver would need a fourth flavour.
* The 32-bit and ARM64 kernel targets: not buildable by this WDK.
* Five names that did not compile, and are not in the baseline:
  `memchr`, `wcslen`, `wcscmp`, `wcscpy`, `wcscat`, each `error C2099:
  initializer is not a constant` - they are intrinsics under `/kernel`, so
  their address is not a constant expression. Only their import thunks would
  have been measured, so they were left out rather than reworked.

The images affected, which a re-import has to rebuild because `refilter` can
only apply a baseline this host can measure and there is no MSVC here:
Hidden, BlackBoneDrv and APICallProxy on `claude/msvc-baseline-wide-stdio`'s
data, and DiskCryptorDrv and WinPmemDrv on `claude/fix-diskcryptordrv`. Nothing
else in the repository is a `.sys`.

The deep check fails on one kind of collision only - the kind every round
above was found by, one symbol name repeated across every family sharing the
hash - and reports the rest as `NOTE` lines with their counts. `validate`,
`validate --deep` and `explain_collisions.py` agree because they share one
classifier, `corpus.validate.classify_collision`.

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

Today the corpus has **571** cross-family PicHashes at the ten-instruction
floor, split **349** standard-library instantiations, **164** whose names
differ between the families sharing them, **57** carrying no symbol in any
family, and the **one** leakage finding the sixth round answers. The totals grew
with the corpus - they were 58 when it was MinGW-only, and 546 before the
lib2smda#1 wishlist families arrived - so they are a measure of how much
C++ it now contains rather than of anything getting worse.

Re-measured after the fifth glue round, and the round did not move the
number down. None of the 510 functions it removed can have been in this
census: a body carrying the same C library name across three families is
exactly what the leakage bucket is, and that bucket held one finding before
the round as well as after. `ferror`, `feof`, `clearerr`, `rewind` and the
import thunks are a handful of instructions each and sit below the floor
counted here. A refilter round is a misattribution fix, not a collision
fix, and the two are measured separately on purpose. What did move since
this paragraph was last written is three hashes, all of them in the
differing-names bucket. The leakage count did not: it is the same single
`__scrt_common_main_seh`, unchanged through the last imports and through 510
functions leaving 67 artefacts - though the family list it spans has since
grown to Hidden, Lua, MemoryModule and bzip2, and the whole-corpus run the
sixth round was measured against reports it across five. Both numbers are
before that round; it empties the bucket only once the MSVC families are
rebuilt with the new baseline, which is a Windows job and not a `refilter`
one.

That last step is the useful control. It added six MSVC families and eight
ELF artefacts, among them five separate implementations of the same WOW64
transition, sitting beside BlackBone's vendored copy of rewolf-wow64ext.
Five implementations of one technique is where new leakage would be
expected if the filter were weak, and the leakage count did not move: all
twenty of the new shared hashes classify as standard-library instantiation,
differing names, or unnamed.

A hash counts as standard-library code only when every name sharing it is
one; an earlier rule accepted a hash as soon as *one* of the names was, and
filed seven short-body coincidences under the wrong heading.

MSVC needs one more rule than libstdc++ did. It names an unnamed lambda
`<lambda_HEX>` from the lambda's source, so the same id in two projects
means the same source - but says nothing about *whose*. The id is resolved
by what else names it: a lambda is standard-library code when an internal
`std::` member that no caller can hand a lambda to carries it in its own
name, which today means `std::basic_string::_Reallocate_grow_by`. Keying it
on the namespace alone was tried and is wrong - `std::invoke`, `std::move`,
`std::forward` and `std::remove_if` are instantiated over whatever they are
handed, and keyed on those the rule excused 707 ids, 589 of which also
carry a project host name, among them abseil's own lambda over its own
type.

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

31 families and 96 artefacts are built by
`.github/workflows/windows-reference-data.yml` on `windows-2022` runners,
one job per architecture. 28 of those families now carry an MSVC artefact
beside their MinGW one, from the same upstream tag; the other three -
VX-API, BlackBone and SysWhispers - are MSVC-only and always were, because
ATL, the DIA SDK and MASM have no GCC equivalent. SysWhispers is x64 only,
by its own declaration.

The reason is the one the section below on prebuilts turns on: a MinGW
reference matches a MinGW-built binary well and an MSVC-built one only
weakly, and most Windows software an analyst meets is MSVC-built. For C
that gap is narrow - the same source, two code generators - but for C++ it
is most of the signal, because name mangling, exception tables, vtable and
thunk shapes and template instantiation all differ. cryptopp, protobuf,
abseil, re2, nlohmann_json and 7-Zip were the families this mattered most
for, and they were MinGW-only until now.

**No step of the workflow names a recipe or a family.** Each job asks
`build_corpus.py list --toolchain msvc_<arch> --names-only` which recipes
declare the toolchain it has, and `--families-only` which corpus
directories those recipes file into, so adding a recipe under
`corpus/recipes/` is the whole change. A recipe that fails costs itself and
not the wave: the build step records its exit code and lets the rest run,
and a final step re-prints every failure and fails the job.

Artefacts are uploaded rather than committed by CI, and come back in with:

    python scripts/import_ci_artifacts.py --run <id>

which checks each one before it touches `data/` and merges the two jobs'
provenance per architecture. What it can check end to end is the download:
the zip is verified against the sha256 GitHub records for it. The binary
itself is not in the artefact, so its digest cannot be recomputed; what is
checked instead is that the provenance record, the report inside the `.7z`
and the sample entry inside the `.mcrit` all name the same digest, the same
`num_functions` and the same family, version and component - which is what
a mixed-up or truncated upload breaks - and that the export carries the
corpus minhash and shingler config hashes. The module's own docstring lists
all of it. Nothing about an artefact is taken on trust because it arrived
from CI.

**The glue baseline is measured for MSVC too**, by `corpus/baseline.py`,
and it has to be: under `/MD` the CRT is imported rather than linked, but
the C++ half of the runtime - STL template instantiations, ATL, the EH
machinery - is compiled into every artefact that uses it and would
otherwise be filed under a library's name. The MSVC probe set grew from 5
compilations to 34 over two rounds for exactly that - 19 distinct
translation units, seven of which are built three ways - and both rounds
were found the same way the MinGW ones were: by asking `validate --deep`
what the surviving cross-family hashes were called. What made the MSVC
rounds harder than the MinGW ones is that MSVC instantiates a member
template on the *argument's* category and width, so a probe calling
`emplace(wstring, 2u)` emits a different symbol than a library calling
`emplace(wstring, someUnsignedLong)`, and `is_glue` matches on the symbol
name as well as the PicHash. Of the 124 names in BlackBone x64's residue
that a probe could reach at all, 121 turned out never to have been emitted
by the first probe.

**`/INCREMENTAL:NO` on every MSVC link that does not already inherit
it**, which the first round of these recipes did not have and needed. `link /DEBUG` implies `/INCREMENTAL`, and
the `/OPT:NO*` forms these recipes pass do not suppress it - only
`/OPT:REF`, `/OPT:ICF` and `/OPT:ORDER` are documented to. An incrementally
linked image reaches each function through a table of one-instruction jump
thunks, and SMDA recovers every one of those as a function of its own,
unnamed. The table is unmistakable once looked at: nlohmann_json 3.12.0
x64 carries 2866 of them, starting at `base+0x1005` and spaced five bytes
apart - `E9 rel32` - with nothing but thunks inside its span. What the
check keys on is the *run*, not the count: those 2866 fall into 68
consecutive runs, the longest 212 entries and the first only 14, and a
threshold on the count would have to be a different number for every
artefact.

Seven recipes were affected - nlohmann_json, bzip2, libtomcrypt, OpenSSL,
cryptopp, Lua and sqlite3 - and at the worst of them roughly half of what
the corpus was calling a function was a thunk: 4882 of libcrypto x86's
12,861, 2936 of nlohmann_json x86's 5205, 978 of libtomcrypt x86's 2030.
Nothing else was: the CMake recipes inherit `/INCREMENTAL:NO` from CMake's
own Release default, the MSBuild ones get it from their project files,
VX-API's `/FORCE:UNRESOLVED` makes link.exe ignore `/INCREMENTAL`
altogether, SysWhispers passes no `/DEBUG` so nothing is implied, and
7-Zip's nmake build already carries `-INCREMENTAL:NO` on the `LFLAGS` line
its recipe deliberately does not touch (`CPP/Build.mak:133`). The
unaffected artefacts are not free of unnamed direct-jump functions - 7-Zip's
MinGW x86 reports carry 265, cryptopp's MinGW x64 241 - but they are
scattered rather than packed, and the longest consecutive five-byte run
anywhere outside an incrementally linked image is 18, against a threshold
of 32. The one-instruction jumps those artefacts carry are mostly named,
and are import thunks jumping through the IAT or ordinary tail calls - 185
in VX-API x64, 211 in abseil x64, 149 in libcurl 8.15.0 x64, of which 1, 68
and 14 respectively
are direct.

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

## The Linux half

Four families - `Obfuscate`, `StringObfuscatorCT`, `StringObfuscator` and
`obfstr` - also carry ELF artefacts, built by the host's own `gcc`/`g++`
through the `linux_x86` and `linux_x64` toolchains. They are the corpus's
only non-PE reference data. All four are portable libraries used on Linux as
well as Windows, and the recipes are `*_linux.py` modules beside the
existing ones: same pinned commit, same exerciser or driver crate, same
optimization level, so an ELF row and a PE row of the same family differ in
the container and nothing else.

The toolchain is registered as `gcc13_x64`, with the version-less aliases
`gcc_x64` and `linux_x64`. Two aliases rather than one because the id is
named after the compiler and the alias recipes declare is named after the
target, which is the thing that is actually different: the same GCC the
mingw-w64 cross compilers are built from, aimed at glibc and ELF.
`corpus.toolchain.canonical_alias` owns that correspondence and everything
that has to read a toolchain out of a filename goes through it.
`linux_x86` is only registered when `gcc -print-multi-lib` reports a 32-bit
multilib; the C++ recipes additionally need `g++-multilib`, which no cheap
probe can test for and which fails at the compile step with the compiler's
own message.

Three things about this side are worth knowing before adding to it.

**Build a `.so`, not an executable.** A `-shared` ELF object links glibc,
libstdc++ and libm dynamically, so none of their bodies are in the image at
all - every call to them is an unnamed `.plt` stub. The measured glue
baseline is therefore 28 symbols on x64 and 37 on x86, against 2893 for
MinGW x64, and of those only 7 and 18 are link glue; the rest are libstdc++
templates the headers instantiate into the probe's own translation unit. A
static build would put the whole C runtime into the sample under a library's
name, which is what `-static` did to monomorph: 1393 of 1397 symbols glibc
and zlib.

**Build `-fvisibility=hidden`.** This is the one that is easy to miss and
expensive to miss. An ELF shared object exports every global symbol by
default, and a call to an exported symbol from inside the same object goes
through a three-instruction `.plt` stub, because another object is allowed to
interpose it. Without the flag a header-only C++ library's own template
instantiations are all exported and all called through stubs:
`StringObfuscatorCT` x64 came out at 385 functions of which 271 were unnamed
stubs, and was refused by the symbol-coverage gate at 113 of 256. With it the
same source is 137 functions with 133 named. It is also what the PE side has
had all along - a MinGW DLL with no `.def` exports only what is marked
`dllexport` - so the flag makes the two comparable rather than making the ELF
one special. The entry point is exempted through
`corpus/exercisers/corpus_export.h`, which is one macro spelling
`__declspec(dllexport)` on Windows and `visibility("default")` elsewhere so
that one exerciser serves both platforms.

**A handful of x86 link glue survives the filter**, on every 32-bit ELF
artefact: `_init`, `_fini`, `register_tm_clones`, `deregister_tm_clones`,
`__do_global_dtors_aux`, and `__stack_chk_fail_local` in the three C++ ones
(obfstr's Rust driver does not use the stack protector) - six functions of
233, 137 and 71 respectively, five of obfstr's 55. Not a gap in the
baseline. On 32-bit PIC each of those bodies reaches the GOT through
`call __x86.get_pc_thunk.bx; add ebx, <delta>` and the delta is that image's
own layout, so the body - and its PicHash - differs between any two images.
The filter matches on symbol *and* PicHash deliberately, which is what stops
it deleting a project's own `strlen`, so these stay. The x64 artefacts have
no such problem and their glue is removed in full.

## Adding a recipe

Recipes are declarative (`corpus/recipes/*.py`) and carry no logic, so every
project goes through the same code path. Pin sources by SHA-256 for a release
tarball or by tag/commit for a clone; never by a moving branch.

An exerciser keyed on the preprocessor deserves one more check than the
pipeline can make. `ay_obfuscate.cpp` instantiates on
`ay::generate_key(__LINE__)`, so adding an `#include` above its call sites
changes every key, every mangled name and every function body while leaving
the function count exactly as the provenance record says - nothing fails and
nothing notices. Compare the recovered symbol names of a rebuild against the
committed report, not just the counts, whenever an exerciser is edited.

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
| DavidBuchanan314/monomorph | [lib2smda#1](https://github.com/familiary/lib2smda/issues/1) | Linux x86-64 ELF only. That alone is no longer the obstacle it was when this row was written - `linux_x86` and `linux_x64` exist now - but the reason that mattered does not move: its own code is four functions, `get_bit`, `decode_buf`, `inflate_buf` and `main`, 679 bytes between them, against a floor of eight. The committed artefact carries 1397 function symbols, but 1393 of them are statically linked glibc and zlib, and with no glibc baseline to subtract them they would enter under monomorph's name and duplicate `data/libzlib`. What is distinctive about the project is the 4 MB array of MD5 collision blocks, which is data rather than code; upstream points at a collision detector for identifying it |

VX-API (#4), BlackBone (#8) and SysWhispers v1 (#9) were on this list and are
not any more: they need ATL, the DIA SDK or MASM, none of which exists for
GCC, so they are built with MSVC on a `windows-2022` runner by
`.github/workflows/windows-reference-data.yml` rather than approximated.
Crypto++ (#10) has also left it - upstream's own `cryptopp.dll` target
exports only the FIPS subset, but its GNUmakefile builds `libcryptopp.a`
cleanly and that is linked into a DLL with `--whole-archive`.

BlackBone's kernel driver (#8) is the most recent departure, and it left for
neither of those reasons. Its row said the driver needed a WDK the runner did
not have; the probe on run 35855463795 reported `WDK-PROBE` PRESENT on all
five paths, APICallProxy then proved a `.sys` goes through this pipeline, and
what was left was that nobody had written a recipe. `blackbonedrv.py` is that
recipe: `Win10Release|x64` of `src/BlackBoneDrv/BlackBoneDrv.sln`, which is
upstream's own CI command line. It built: 321 functions reported, of which 58
are MSVC string-literal COMDATs and 112 are thunks of three instructions or
fewer, leaving 144 of ten instructions or more against the 139 counted in the
source. It is
a separate family from the user-mode library rather than a second component
of it - the two share no code, and two recipes on one `(family, version)` key
is exactly the ambiguity `refresh_provenance.py` narrows by toolchain alias
and could not resolve here, both declaring `msvc_x64`.

4g3nt47/Obfuscator (lib2smda#1) has left it too, and it is the one entry here
that left because the tooling changed rather than because the project was
looked at again. It has seven functions against a floor of eight, but the
count was never what kept it out: measured through `smdaify` it reported 15
functions on x86 and 28 on x64, so it *cleared* the floor already - on
`feof`, `fgetc`, `printf`, `rewind` and `atoi`, MinGW runtime the baseline
did not classify because `_PROBE_DLL` never calls any of them. Clearing a
floor on misattributed runtime is what made it unbuildable, not failing one,
and lowering the floor would not have touched that. Two changes fixed it
between them. `_PROBE_STDIO` measures the character-at-a-time half of stdio,
so those names are now runtime like every other runtime function - the
artefacts are 10 and 22 functions and every named one of them is the
project's. And `Recipe.min_functions` lets a recipe state the count a
project genuinely has, so what admits this family is its own seven rather
than a total that includes the unnamed thunks no name-matching filter can
reach. Neither is a threshold moved to let something through, and nothing
was hand-added to the baseline. Its reference value is still thin and the
recipe says so: nothing from this project is ever linked into a protected
program.

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
