# MIRACL MinGW x86 assembly coverage

This extends [PR 92](https://github.com/familiary/mcrit-data/pull/92) for
[tracker 29](https://github.com/r0ny123/mcrit-data/issues/29). It adds one
compiler/configuration axis to the existing library family. The real-sample
comparison remains open: no verified keygen.exe sample was supplied and none
was sourced. No key generator or other operational program is built.

Source commit: `b9b8fd471de253cfd6313446cb490741edb069a7`.
Source archive SHA-256: `fbcfbfc0e245f8af74d4800dfa40f3546f7bec9e6cc12b645ca234573ef447d4`.
Compiler: `i686-w64-mingw32-gcc (GCC) 13-posix`.
Analysis: Python 3.12, SMDA 5.0.2, MCRIT 1.16.0.
Recipe: `MIRACL_2019-08-21-asm32_mingw`.
Configuration: upstream mirdef.h32, unchanged mrmuldv.gcc, -O2, shared DLL;
the same 50 C modules and six C++ wrappers as the sibling variants.
No upstream source is patched and no resulting program is executed.

## Counts and overlap

| New image | Kept | Runtime removed | Excluded | Recovered image total |
| --- | ---: | ---: | ---: | ---: |
| MIRACL_2019-08-21-asm32_mingw13_x86_libmiracl.dll | 862 | 71 | 0 | 933 |

The family now has eleven images: 8214 kept + 1000 removed + 0 excluded =
9214 recovered functions. Counts are recovered-function counts, not source
function counts. Of the new retained instances, 119 are unnamed; 602 have
at least ten instructions, with 530 distinct PicHashes.

| Earlier image | Earlier distinct hashes | Shared with new | New outside earlier |
| --- | ---: | ---: | ---: |
| `MIRACL_2019-08-21-asm32_gcc13_x86_libmiracl.so` | 611 | 32 | 498 |
| `MIRACL_2019-08-21-asm32_msvc143_x86_libmiracl.dll` | 553 | 0 | 530 |
| `MIRACL_2019-08-21-asm64_gcc13_x64_libmiracl.so` | 512 | 0 | 530 |
| `MIRACL_2019-08-21-asm64_mingw13_x64_libmiracl.dll` | 508 | 0 | 530 |
| `MIRACL_2019-08-21-generic32_gcc13_x86_libmiracl.so` | 610 | 31 | 499 |
| `MIRACL_2019-08-21-generic32_mingw13_x86_libmiracl.dll` | 527 | 508 | 22 |
| `MIRACL_2019-08-21-generic32_msvc143_x86_libmiracl.dll` | 554 | 0 | 530 |
| `MIRACL_2019-08-21-generic64_gcc13_x64_libmiracl.so` | 514 | 0 | 530 |
| `MIRACL_2019-08-21-generic64_mingw13_x64_libmiracl.dll` | 509 | 0 | 530 |
| `MIRACL_2019-08-21-generic64_msvc143_x64_libmiracl.dll` | 560 | 0 | 530 |

Twenty-one new hashes lie outside the union of all ten earlier images.
Two arise from an SMDA split of one multi_add implementation and are excluded
from novelty. The remaining nineteen are named arithmetic bodies:

| Symbol | Instructions | PicHash |
| --- | ---: | --- |
| `_mr_pmul` | 122 | `0xc41d43efbca17ef6` |
| `_mr_sdiv` | 85 | `0x1a05ef00c45c1a3d` |
| `_normalise` | 65 | `0xf8d39082b1775b01` |
| `_multiply` | 375 | `0x90334fca89b5db4b` |
| `_divide` | 698 | `0xed127f8f42c731bc` |
| `_mr_dif_fft` | 120 | `0x567b6a2bae9e2bfa` |
| `_mr_dit_fft` | 116 | `0xc2eea982cf2047aa` |
| `_mr_poly_rem` | 498 | `0x194df7bed16bf51c` |
| `_mr_polymod_set` | 283 | `0xd4d6a6ee96456549` |
| `_mr_ps_zzn_mul` | 297 | `0x7648b71ac06d5574` |
| `_mr_ps_big_mul` | 443 | `0x8647efefc7164c21` |
| `_mr_poly_sqr` | 238 | `0x479acf5e440fb86d` |
| `_mr_poly_mul` | 301 | `0xf7b3e4c57e981fba` |
| `_fft_mult` | 579 | `0xaee07aa76c5e9803` |
| `_redc` | 211 | `0x2c33d0b3d22c5415` |
| `_muldiv` | 14 | `0x6614de202e8d672f` |
| `_muldvm` | 12 | `0x792cfa29c3b5ee94` |
| `_muldvd` | 13 | `0xdbd72e239f60fb4d` |
| `_scrt` | 166 | `0x3ea4ae7a2beadb62` |

## SMDA boundary limitation

The upstream COFF symbol `__Z9multi_addiP3ECnS0_` starts at 0x68703650;
objdump shows one body through 0x687036d4. SMDA ends the named prefix after
the call at 0x687036b3 and starts an unnamed continuation at 0x687036b8.
The prefix has 32 instructions / PicHash 0x223e3f9b734b29c2; the continuation
has 10 / 0x12fed8c4dbfd7a65. These are preserved as reported and neither
hash counts as a new implementation. No threshold, report name or shared
analysis code was changed to hide the limitation.

## Retained glue and other-family comparisons

The unnamed 15-instruction PicHash 0xdfe3cea2dbb80872 is independently
labelled ___chkstk_ms by COFF nm at 0x6873a198. At ten instructions the
comparison against aPLib, bzip2, cJSON, Obfuscate and SysWhispers matches only
this stack probe: bzip2 x86, three cJSON x86 images and Obfuscate x86. No
project hash matches those controls. This pre-existing unnamed-runtime
residue is not project novelty and no shared baseline was edited.

Twelve named runtime/import stubs are one instruction each, all with
PicHash 0x1165511d87767dcf: ___gxx_personality_v0, ___register_frame_info,
___deregister_frame_info, __Unwind_Resume, std::__istream_extract,
std::__throw_bad_cast, std::__ostream_insert, std::basic_ios::clear,
std::ostream::operator<<(int), std::istream::getline, std::istream::sync,
and std::ctype::_M_widen_init. Full surviving names/hashes, including the
wrapper cold fragments, are in the recipe docstring. MIRACL's stream
operators and otfloat are defined in its own C++ sources and are not
standard-library implementation bodies simply because they mention streams.

The remaining unnamed instances are 113 two-instruction stubs, four
seven-instruction stubs and the ten-instruction multi_add continuation.
The new export remains is_library=true. The archive contains one .smda;
no compiled DLL is committed.
