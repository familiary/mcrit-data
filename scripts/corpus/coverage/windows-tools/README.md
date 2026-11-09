# Historical pin and vendoring audit

This follow-up changes documentation only. No image was rebuilt or refiltered.

## WinPmem

The 1.6.2-era pin required by [issue 79](https://github.com/r0ny123/mcrit-data/issues/79)
was already used for both client and driver references:
`google/rekall` commit `cfaf02d7b4f8b9853fec38ea86e7efd22e78bf6f` (Rekall 1.2.0).
The source archive SHA-256 in all four provenance entries is
`e4ea411c282ba9239a3fe65339a500f99eb14cf26d5ff9e2248ea978f0b87e1b`.
The pinned `tools/windows/winpmem/executable/winpmem.h` independently confirms
`#define PMEM_VERSION "1.6.2"`; its SHA-256 is
`90d2ad3b426542606fb0e1d52eb696232e8ab147b6b60cbea145cf502e4cd8a1`.
No modern WinPmem HEAD substitution is involved. This establishes the
historical version, not byte identity with Meterpreter's diverged copy.

## EDRSandblast

The existing recipe and provenance already record vendored SysWhispers2,
separately from the corpus's SysWhispers v1 family. At pinned EDRSandblast
commit `0710fad92dbcdf373ed30c536b99012fcd46dbcc`, its project lists:

| Pinned source path under EDRSandblast/ | SHA-256 |
| --- | --- |
| `Utils/SW2_Syscalls.c` | `8c738eba1fb3f7b2d996efe3b07e7cda2cd2b1c5704f5c8546be3d0c9d886076` |
| `Includes/SW2_Syscalls.h` | `58b04179f39e34d2099ad8c0bf73c441ca64c726382bf848f10d13eec5a480b8` |
| `Utils/SW2_Syscalls_stubs.x64.asm` | `7b579e39bcfc1148cfa82378d5a0f69aee0f6ecb3ce145512ed9d35d3290a084` |

These are the consumer-pinned vendored files; no independent SysWhispers2
revision or byte-identical match to another family is asserted. The x86
analysis image's nine generated STATUS_NOT_IMPLEMENTED stubs are not
SysWhispers2 implementation coverage. That image is NOT byte-identical to
unmodified upstream. This audit adds no functioning replacements. The scope
question in [issue 16](https://github.com/r0ny123/mcrit-data/issues/16) remains
for the maintainer; factual vendoring is not a scope decision.

## Existing image counts

Recomputed from provenance and checked against decoded exports. Excluded
counts are zero throughout. Only functions with at least ten instructions
and a nonzero PicHash enter the last column.

| Image | Kept | Removed | Total | Distinct PicHashes |
| --- | ---: | ---: | ---: | ---: |
| `WinPmem_1.6.2_msvc143_x64_winpmem.dll` | 56 | 97 | 153 | 29 |
| `WinPmem_1.6.2_msvc143_x86_winpmem.dll` | 56 | 87 | 143 | 29 |
| `WinPmemDrv_1.6.2_msvc143_x64_winpmem.sys` | 132 | 35 | 167 | 72 |
| `WinPmemDrv_1.6.2_msvc143_x86_winpmem.sys` | 136 | 44 | 180 | 72 |
| `EDRSandblast_2024-08-30_msvc143_x64_EDRSandblast.dll` | 375 | 92 | 467 | 225 |
| `EDRSandblast_2024-08-30_msvc143_x86_EDRSandblast.dll` | 374 | 78 | 452 | 229 |

The WinPmem client architecture sets have zero shared hashes; the two driver
sets also have zero shared hashes. EDRSandblast's architecture sets have
zero shared hashes. Existing recipe docstrings retain named glue survivors
and their PicHashes. These facts do not remove the disclosed kernel-glue,
x86 toolchain or synthetic-stub limitations in PR 78.
