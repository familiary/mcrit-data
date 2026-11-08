# Go implants coverage

Pinned Go source-reference coverage for Pantegana and Sliver, with separate attribution counts for retained dependency code.

This snapshot contains **16 report/export pairs: 100644 kept + 102531 removed = 203175 image functions**. Counts describe retained functions, including documented residues; they are not a count of unique project implementations. Each export is marked `is_library=true`.

PE and ELF x86/x64 are covered for both Pantegana components and both Sliver revisions. These are unconfigured analysis images. Source revision and compiler version change together between Sliver revisions; PicHash differences cannot be attributed to either factor alone. Mach-O, ARM and configured startup variants are not part of this matrix.

## Committed matrix

Each row links the retained SMDA report and MCRIT export. Source pins, build flags, compiler banners and binary SHA-256 values are in the linked family provenance. `gcc14` is the target wrapper ID for ELF Go images; the compiler named in their version is the actual Go compiler.

| Family / component | Version | Target | Kept | Removed | Image total | Reports |
| --- | --- | --- | ---: | ---: | ---: | --- |
| [Pantegana](../../../../data/Pantegana/provenance.json) / client-analysis | 0.1.0-go1.24.13-client-analysis | gcc14_x64 | 41 | 6233 | 6274 | [SMDA](../../../../data/Pantegana/x64/smda/Pantegana_0.1.0-go1.24.13-client-analysis_gcc14_x64_client-analysis.7z) / [MCRIT](../../../../data/Pantegana/x64/mcrit/Pantegana_0.1.0-go1.24.13-client-analysis_gcc14_x64_client-analysis.mcrit) |
| [Pantegana](../../../../data/Pantegana/provenance.json) / client-analysis | 0.1.0-go1.24.13-client-analysis | gcc14_x86 | 42 | 6236 | 6278 | [SMDA](../../../../data/Pantegana/x86/smda/Pantegana_0.1.0-go1.24.13-client-analysis_gcc14_x86_client-analysis.7z) / [MCRIT](../../../../data/Pantegana/x86/mcrit/Pantegana_0.1.0-go1.24.13-client-analysis_gcc14_x86_client-analysis.mcrit) |
| [Pantegana](../../../../data/Pantegana/provenance.json) / client-analysis | 0.1.0-go1.24.13-client-analysis | mingw13_x64 | 24 | 6097 | 6121 | [SMDA](../../../../data/Pantegana/x64/smda/Pantegana_0.1.0-go1.24.13-client-analysis_mingw13_x64_client-analysis.7z) / [MCRIT](../../../../data/Pantegana/x64/mcrit/Pantegana_0.1.0-go1.24.13-client-analysis_mingw13_x64_client-analysis.mcrit) |
| [Pantegana](../../../../data/Pantegana/provenance.json) / client-analysis | 0.1.0-go1.24.13-client-analysis | mingw13_x86 | 28 | 6238 | 6266 | [SMDA](../../../../data/Pantegana/x86/smda/Pantegana_0.1.0-go1.24.13-client-analysis_mingw13_x86_client-analysis.7z) / [MCRIT](../../../../data/Pantegana/x86/mcrit/Pantegana_0.1.0-go1.24.13-client-analysis_mingw13_x86_client-analysis.mcrit) |
| [Pantegana](../../../../data/Pantegana/provenance.json) / fingerprint | 0.1.0-go1.24.13-fingerprint | gcc14_x64 | 20 | 2469 | 2489 | [SMDA](../../../../data/Pantegana/x64/smda/Pantegana_0.1.0-go1.24.13-fingerprint_gcc14_x64_fingerprint.7z) / [MCRIT](../../../../data/Pantegana/x64/mcrit/Pantegana_0.1.0-go1.24.13-fingerprint_gcc14_x64_fingerprint.mcrit) |
| [Pantegana](../../../../data/Pantegana/provenance.json) / fingerprint | 0.1.0-go1.24.13-fingerprint | gcc14_x86 | 22 | 2491 | 2513 | [SMDA](../../../../data/Pantegana/x86/smda/Pantegana_0.1.0-go1.24.13-fingerprint_gcc14_x86_fingerprint.7z) / [MCRIT](../../../../data/Pantegana/x86/mcrit/Pantegana_0.1.0-go1.24.13-fingerprint_gcc14_x86_fingerprint.mcrit) |
| [Pantegana](../../../../data/Pantegana/provenance.json) / fingerprint | 0.1.0-go1.24.13-fingerprint | mingw13_x64 | 6 | 2148 | 2154 | [SMDA](../../../../data/Pantegana/x64/smda/Pantegana_0.1.0-go1.24.13-fingerprint_mingw13_x64_fingerprint.7z) / [MCRIT](../../../../data/Pantegana/x64/mcrit/Pantegana_0.1.0-go1.24.13-fingerprint_mingw13_x64_fingerprint.mcrit) |
| [Pantegana](../../../../data/Pantegana/provenance.json) / fingerprint | 0.1.0-go1.24.13-fingerprint | mingw13_x86 | 6 | 2217 | 2223 | [SMDA](../../../../data/Pantegana/x86/smda/Pantegana_0.1.0-go1.24.13-fingerprint_mingw13_x86_fingerprint.7z) / [MCRIT](../../../../data/Pantegana/x86/mcrit/Pantegana_0.1.0-go1.24.13-fingerprint_mingw13_x86_fingerprint.mcrit) |
| [Sliver](../../../../data/Sliver/provenance.json) / implant-analysis | 1.5.42-go1.20.14-analysis | gcc14_x64 | 12860 | 7873 | 20733 | [SMDA](../../../../data/Sliver/x64/smda/Sliver_1.5.42-go1.20.14-analysis_gcc14_x64_implant-analysis.7z) / [MCRIT](../../../../data/Sliver/x64/mcrit/Sliver_1.5.42-go1.20.14-analysis_gcc14_x64_implant-analysis.mcrit) |
| [Sliver](../../../../data/Sliver/provenance.json) / implant-analysis | 1.5.42-go1.20.14-analysis | gcc14_x86 | 12864 | 7891 | 20755 | [SMDA](../../../../data/Sliver/x86/smda/Sliver_1.5.42-go1.20.14-analysis_gcc14_x86_implant-analysis.7z) / [MCRIT](../../../../data/Sliver/x86/mcrit/Sliver_1.5.42-go1.20.14-analysis_gcc14_x86_implant-analysis.mcrit) |
| [Sliver](../../../../data/Sliver/provenance.json) / implant-analysis | 1.5.42-go1.20.14-analysis | mingw13_x64 | 12941 | 7935 | 20876 | [SMDA](../../../../data/Sliver/x64/smda/Sliver_1.5.42-go1.20.14-analysis_mingw13_x64_implant-analysis.7z) / [MCRIT](../../../../data/Sliver/x64/mcrit/Sliver_1.5.42-go1.20.14-analysis_mingw13_x64_implant-analysis.mcrit) |
| [Sliver](../../../../data/Sliver/provenance.json) / implant-analysis | 1.5.42-go1.20.14-analysis | mingw13_x86 | 12884 | 7896 | 20780 | [SMDA](../../../../data/Sliver/x86/smda/Sliver_1.5.42-go1.20.14-analysis_mingw13_x86_implant-analysis.7z) / [MCRIT](../../../../data/Sliver/x86/mcrit/Sliver_1.5.42-go1.20.14-analysis_mingw13_x86_implant-analysis.mcrit) |
| [Sliver](../../../../data/Sliver/provenance.json) / implant-analysis | 4c2e8d4-go1.27.3-analysis | gcc14_x64 | 12927 | 8811 | 21738 | [SMDA](../../../../data/Sliver/x64/smda/Sliver_4c2e8d4-go1.27.3-analysis_gcc14_x64_implant-analysis.7z) / [MCRIT](../../../../data/Sliver/x64/mcrit/Sliver_4c2e8d4-go1.27.3-analysis_gcc14_x64_implant-analysis.mcrit) |
| [Sliver](../../../../data/Sliver/provenance.json) / implant-analysis | 4c2e8d4-go1.27.3-analysis | gcc14_x86 | 12120 | 10791 | 22911 | [SMDA](../../../../data/Sliver/x86/smda/Sliver_4c2e8d4-go1.27.3-analysis_gcc14_x86_implant-analysis.7z) / [MCRIT](../../../../data/Sliver/x86/mcrit/Sliver_4c2e8d4-go1.27.3-analysis_gcc14_x86_implant-analysis.mcrit) |
| [Sliver](../../../../data/Sliver/provenance.json) / implant-analysis | 4c2e8d4-go1.27.3-analysis | mingw13_x64 | 12118 | 8520 | 20638 | [SMDA](../../../../data/Sliver/x64/smda/Sliver_4c2e8d4-go1.27.3-analysis_mingw13_x64_implant-analysis.7z) / [MCRIT](../../../../data/Sliver/x64/mcrit/Sliver_4c2e8d4-go1.27.3-analysis_mingw13_x64_implant-analysis.mcrit) |
| [Sliver](../../../../data/Sliver/provenance.json) / implant-analysis | 4c2e8d4-go1.27.3-analysis | mingw13_x86 | 11741 | 8685 | 20426 | [SMDA](../../../../data/Sliver/x86/smda/Sliver_4c2e8d4-go1.27.3-analysis_mingw13_x86_implant-analysis.7z) / [MCRIT](../../../../data/Sliver/x86/mcrit/Sliver_4c2e8d4-go1.27.3-analysis_mingw13_x86_implant-analysis.mcrit) |

## Attribution before import

Sliver retains its statically linked dependency closure. Across its eight exports, **100455 kept = 17191 named first-party functions excluding startup + 74723 dependency-namespace functions + 3051 generated helpers outside the project + 2220 startup functions + 3270 unnamed functions**. A match against a dependency function does not establish Sliver-specific reuse. Counts are function instances across images, not distinct PicHashes.

| Revision / target | First-party namespace, excluding startup | Dependency namespace | Generated outside project | Startup / adapted init | Unnamed | Kept |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1.5.42-go1.20.14-analysis / gcc14_x64 | 2178 | 9618 | 412 | 204 | 448 | 12860 |
| 1.5.42-go1.20.14-analysis / gcc14_x86 | 2178 | 9633 | 406 | 204 | 443 | 12864 |
| 1.5.42-go1.20.14-analysis / mingw13_x64 | 2396 | 9526 | 376 | 173 | 470 | 12941 |
| 1.5.42-go1.20.14-analysis / mingw13_x86 | 2391 | 9512 | 360 | 157 | 464 | 12884 |
| 4c2e8d4-go1.27.3-analysis / gcc14_x64 | 1906 | 9705 | 408 | 400 | 508 | 12927 |
| 4c2e8d4-go1.27.3-analysis / gcc14_x86 | 1906 | 8975 | 363 | 396 | 480 | 12120 |
| 4c2e8d4-go1.27.3-analysis / mingw13_x64 | 2119 | 9256 | 390 | 353 | 0 | 12118 |
| 4c2e8d4-go1.27.3-analysis / mingw13_x86 | 2117 | 8498 | 336 | 333 | 457 | 11741 |

The categories are disjoint. Startup is classified before project/dependency namespace: `main.main`, `main.corpusOriginalMain`, `runner.Main`, renamed explicit initializers (`corpusDisabledInit`) and names matching `(?:^|\.)init(?:[.$]|$)`. Named functions in `github.com/bishopfox/sliver/` or package `main` are first-party unless classified as startup. Remaining `type:` names are generated; other named functions are dependency namespace, and empty names are unnamed. Namespace classification is an audit aid, not a proof of source origin or a deletion rule.

Project novelty uses named first-party functions of at least ten instructions and excludes startup. Old Sliver ELF x86/x64 have 1380/1061 qualifying hashes; PE has 1553/1231. New Sliver has 1670/1374 and 1848/1534 respectively. New hashes outside the union of all old references are 1612/1374 for ELF and 1848/1534 for PE. The complete pairwise intersections and symbol names are in the recipes.

Primitive/anonymous array equality/hash helpers survive the current Go filter and remain explicitly identified in the docstrings. For example, Pantegana's `type:.eq.[4]string` is retained in PE: x86 PicHash 12437469830097930878, x64 112253892832525255, both 50 instructions. Such generated helpers are not project novelty. Unnamed bodies are not assigned to a project by inference.

## Boundaries and closure conditions

| Item | Current reference | What would close the remaining gap |
| --- | --- | --- |
| [Pantegana](https://github.com/r0ny123/mcrit-data/issues/71) | Unchanged client source with a nil `Asset` function variable plus the earlier fingerprint references | Authentic generated source tied to the pinned release is absent: direct compilation reports `client/client.go:47:17: undefined: Asset`; `cert.go` and `server.crt` are missing. The nil variable changes the call site and cannot stand in for an authentic loader body. Do not invent a loader and count it as upstream coverage. |
| [Sliver](https://github.com/r0ny123/mcrit-data/issues/37) | Two pinned source revisions, each with four analysis images | The newer source has an unexpanded `func {{.}} ()` wrapper: `main.go:38:6: expected 'IDENT', found '{'` and `main.go:38:12: missing parameter name`. Generated exports, explicit init and configuration-selected startup differ from releases. A future static reference must identify those differences and its authentic input provenance. |
| Go compiler-generated helpers | Full survivor names, sizes and PicHashes recorded in recipes | A separate shared-tooling change to `baseline.is_go_runtime_symbol` must recognize primitive/anonymous array helpers while retaining project-defined named types, with regression cases for both. Recheck all affected exports and preserve removed counts. No such filter patch is included here. |
| Sliver dependency attribution | Counts and project-only novelty reported separately | [Function exclusion support](https://github.com/familiary/mcrit-data/pull/94) can support a reviewed first-party namespace policy after integration; [vendored-library support](https://github.com/familiary/mcrit-data/pull/110) removes only exact symbol/PicHash matches against existing dependency families. Neither automatically identifies all 74723 dependency functions. Unknown and generated bodies need an explicit retention policy before refiltering. |
| Go 1.27 runtime family | Name-based runtime removal is already applied to Sliver | Go 1.27 runtime reference data was not added to `Golang`. That is a separate runtime-family expansion, not another Sliver source build; coordinate with [the Go group](https://github.com/familiary/mcrit-data/pull/76) rather than duplicating its ownership. |

The surviving Pantegana module ZIP is pinned by SHA-256 rather than an invented Git SHA. Sliver is pinned by exact commits. Full pins and compiler banners are in provenance. All original errors, compatibility adaptations and overlap evidence remain in [the recipe contract](../../README.md#targets-investigated-but-not-built) and recipe docstrings.

## Integration and validation

[PR 105](https://github.com/familiary/mcrit-data/pull/105) carries these sixteen pairs. Its [branch check](https://github.com/familiary/mcrit-data/actions/runs/42477669637) passed; selection logs show no MSVC recipes because these Go recipes declare no MSVC legs. No existing Windows corpus was rebuilt.

Local corpus tests passed (186 tests); family validation and provenance checks reported zero problems. Each archive contains exactly one `.smda`. The last full deep scan covered 546 archives and reproduced exactly the same 26 findings as the pinned base, with no additions. Its nonzero baseline result is not a claim that the entire ecosystem is clean. Existing fixes and their review dependencies are linked in the [Windows coverage record](https://github.com/familiary/mcrit-data/blob/codex/corpus-windows-implants/scripts/corpus/coverage/windows-implants/README.md#integration-and-validation).

Shared pipeline files are deliberately unchanged in this contribution. After the independent tooling PRs integrate, regenerate affected reference exports, run provenance checks and corpus tests, and compare a full deep scan before closing attribution gaps. Reports and exports are retained; temporary project builds, downloaded SDK copies and artifact ZIPs were removed. No configured program was executed or committed.
