# Unix reference overlap audit

This is a static comparison of existing reports, not a new build. It closes
the Azazel/Medusa overlap question in [issue 55](https://github.com/r0ny123/mcrit-data/issues/55).
Azazel/TinySHell are from PR 101 base head `1ada483e2beb9569afa19639e876fca100a1b190`;
Medusa/Reptile are from [PR 102](https://github.com/familiary/mcrit-data/pull/102)
head `83fb65b7593931d1c6c530d5cf51381ca60e5dcc`.

Only functions with at least ten instructions and a nonzero PicHash enter
the comparison. Counts below are recomputed from provenance and checked
against the decoded exports. There are no excluded functions in these images.

| Image | Kept | Removed | Total | Distinct hashes at floor | Export SHA-256 |
| --- | ---: | ---: | ---: | ---: | --- |
| `Azazel_2020-07-14_gcc13_x64_libselinux.so` | 170 | 6 | 176 | 48 | `409602347bd7adc96403dac7db630d3f2159ebc5643ec6c79ead03cee157a06e` |
| `Azazel_2020-07-14_gcc13_x86_libselinux.so` | 176 | 4 | 180 | 53 | `e09cd61da3d531f963919375e5693cac273731a4405365f6e8081dc569e43f3d` |
| `TinySHell_0.7_gcc13_x64_tsh` | 111 | 6 | 117 | 20 | `6bb9bd41e63f469ef833399da9500d7fde59536a90ad0eb0e22c77d74da9ccd0` |
| `TinySHell_0.7_gcc13_x64_tshd` | 106 | 6 | 112 | 21 | `ebc3139ef3905ce3b6419094beda49b26f0b2d2779e13481ee33cf42baf8d154` |
| `TinySHell_0.7_gcc13_x86_tsh` | 122 | 4 | 126 | 23 | `e2ca5977348921dc955d72bda5d8d3a94fc409365950c794d65f33eb440337c0` |
| `TinySHell_0.7_gcc13_x86_tshd` | 118 | 4 | 122 | 25 | `bd3e1071adb3bb1eebea230051c93eed120edd5e9b994c09d87cfdc3933fb2d8` |
| `Medusa_2025-04-05_gcc13_x64_rkld.so` | 214 | 5 | 219 | 68 | `0ae3cf7c3fa618306c71c68a1150fa3895bed9526eae94f4e9563307aba27602` |
| `Medusa_2025-04-05_gcc13_x86_rkld.so` | 216 | 4 | 220 | 78 | `24527cb702ff8afca7a91f1c6489da6fb4ae1711b91c11c97aedb32908eb8364` |
| `Reptile_2026-08-17_gcc13_x64_listener` | 152 | 6 | 158 | 33 | `0c78620f4a7088684433b04ed21a28e133c099e24eba44dc628daeee81e8da65` |
| `Reptile_2026-08-17_gcc13_x64_packet` | 57 | 7 | 64 | 7 | `e3edcd24ef5608ad5fdb27695664a0258da7643bddeb40808e2c9488e5bc586f` |
| `Reptile_2026-08-17_gcc13_x64_shell` | 108 | 6 | 114 | 20 | `57719c84d29d3b81f594c5cc6048e1e050bbb00e473891e6f5c942f8909a85e3` |
| `Reptile_2026-08-17_gcc13_x86_listener` | 152 | 4 | 156 | 40 | `d5586c0cf7f53acba7c5f1235a885ac7dac1265fd463aa4a1052e8bc3fc32c79` |
| `Reptile_2026-08-17_gcc13_x86_packet` | 67 | 3 | 70 | 14 | `1d008040487cac7ab4cadd522edf674e2ead2baa62990655c656de103c2f28ae` |
| `Reptile_2026-08-17_gcc13_x86_shell` | 120 | 4 | 124 | 24 | `cf788df5242076837b4a016fbc14c6882f8755bef1644517567db04dddd07d7c` |

Azazel x86/x64 have 53/48 distinct hashes, union 101. Medusa x86/x64 have
78/68, union 146. All four architecture pairings have zero shared hashes.
Medusa is a userland LD_PRELOAD library; the previous description of it as a
kernel module was incorrect. Shared hook names are not matched bodies.

Reptile and TinySHell have unions of 121 and 72 hashes, sharing eight.
Seven correspond to Devine's vendored AES/SHA1 implementation; the eighth
is retained `_init` glue. The seven code hashes represent six symbol names,
since `sha1_process` has two matching bodies:

| PicHash | Name in both families |
| --- | --- |
| `0x16ca30e924a795a2` | `aes_decrypt` |
| `0x5ee0d76db25d35a8` | `_init` |
| `0x82d9e771b65dcfb0` | `sha1_process` |
| `0x9208e7e28a432b66` | `sha1_starts` |
| `0xc7beae46e1873732` | `sha1_process` |
| `0xe4244a6cce0db915` | `aes_encrypt` |
| `0xfd0e27e28ba3fb85` | `aes_set_key` |
| `0xfe7fcc039a384dae` | `sha1_finish` |

No rootkit installer, botnet program or covert backdoor was compiled in this
audit. Mirai and LOKI2 stopped at the audit stage under safeguards; there is
no new compiler error or partial build to report. Licences remain provenance
facts and are not a reason for the stop. Existing data and source build
recipes are preserved.
