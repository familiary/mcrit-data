# Go 1.27.3 runtime references

Go 1.27.3 was [released on 2026-10-19](https://go.dev/doc/devel/release#go1.27.3). The source tag is pinned to `2aae1000ea1d4b28923b96db28acf4e3b99d6aff`; the official Linux amd64 SDK archive is pinned to SHA-256 `65efbc80fdc1fa2cd2631cad5b481777a68e8725f34e89f50fc6ac714e379b40`. Its standard-library sources are unchanged.

These references use the existing [`scripts/golang`](../../../scripts/golang/) pipeline, with SMDA 5.0.2 and MCRIT 1.16.0. They belong to the compiler/runtime family, so runtime and standard-library bodies are deliberately retained. Only the generated coverage driver's `main.*` functions are removed before export, with statistics recomputed. No reference executable was run or committed.

The version-scoped [provenance manifest](provenance.json) records source/SDK pins, generated-source hashes, effective Go settings, reproduced binary hashes, report/export hashes, counts and removed driver names/PicHashes. Historical `Golang` references use the standalone runtime pipeline without corpus recipes; this manifest does not reclassify or rewrite those older records.

## Counts

Image total means functions recovered by SMDA before the driver pass, not a guarantee that every machine-code body was recovered. Named entry addresses were checked against `go tool nm -size`. A zero entry mismatch does not prove every recovered body boundary is correct.

| Target | Kept | Driver removed | Image total | Named | Unnamed | SMDA failed functions | Unrepresented text entries | Reports |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| windows/386 | 20674 | 1 | 20675 | 20134 | 540 | 130 | 2 | [SMDA](../x86/smda/golang_1.27.3_x86.7z) / [MCRIT](../x86/mcrit/golang_1.27.3_x86.mcrit) |
| windows/amd64 | 20122 | 1 | 20123 | 20107 | 15 | 51 | 22 | [SMDA](../x64/smda/golang_1.27.3_x64.7z) / [MCRIT](../x64/mcrit/golang_1.27.3_x64.mcrit) |
| linux/386 | 20618 | 1 | 20619 | 20044 | 574 | 135 | 2 | [SMDA](../x86/smda/golang_1.27.3_linux_x86.7z) / [MCRIT](../x86/mcrit/golang_1.27.3_linux_x86.mcrit) |
| linux/amd64 | 20583 | 1 | 20584 | 19973 | 610 | 55 | 49 | [SMDA](../x64/smda/golang_1.27.3_linux_x64.7z) / [MCRIT](../x64/mcrit/golang_1.27.3_linux_x64.mcrit) |

Total: **81997 kept + 4 driver functions removed = 82001 recovered image functions**. Every export has `is_library=true`; each archive contains exactly one `.smda`. All four binaries reproduced their SHA-256 on a second build. They are not distributed.

## PicHash coverage

Only named functions with at least ten instructions enter these sets; driver functions and unnamed bodies are excluded. The comparison covers 49 Go runtime exports on main plus 16 Linux exports in [PR 114](https://github.com/familiary/mcrit-data/pull/114) at `00032044b5acb234466cab696f8bcd9c397837a4`, whose union has 395977 qualifying hashes including unnamed functions. Axis uniqueness also subtracts unnamed qualifying hashes from the other new images; it does not count a named body as unique merely because its counterpart has no name. Earlier Windows reports were produced with different SMDA versions (Windows 1.26.8 records 4.5.0, while PR 114 uses 5.0.2); differences therefore cannot be attributed solely to the Go compiler or source revision.

| Target | Qualifying distinct hashes | Outside all earlier exports | Unique among these four targets |
| --- | ---: | ---: | ---: |
| windows/386 | 15565 | 11322 | 15482 |
| windows/amd64 | 13956 | 8741 | 1903 |
| linux/386 | 15553 | 11310 | 15470 |
| linux/amd64 | 13944 | 8665 | 1891 |

The four-target union contains **46882** hashes, including **32596** outside the earlier exports. Every retained target contributes hashes absent from the other three.

| Pair | Shared hashes | First target only | Second target only |
| --- | ---: | ---: | ---: |
| windows/386 vs windows/amd64 | 0 | 15565 | 13956 |
| windows/386 vs linux/386 | 83 | 15482 | 15470 |
| windows/386 vs linux/amd64 | 0 | 15565 | 13944 |
| windows/amd64 vs linux/386 | 0 | 13956 | 15553 |
| windows/amd64 vs linux/amd64 | 12053 | 1903 | 1891 |
| linux/386 vs linux/amd64 | 0 | 15553 | 13944 |

Named overlap examples:

- windows/386 vs linux/386: PicHash 39055368368977348, `sync/atomic.CompareAndSwapPointer` / `sync/atomic.CompareAndSwapPointer`.
- windows/amd64 vs linux/amd64: PicHash 36013691927746, `io.(*teeReader).Read` / `io.(*teeReader).Read`.

## Removed driver functions

These are scaffolding rather than standard-library bodies. Counts and hashes describe the unfiltered image.

| Target | Name | Instructions | PicHash |
| --- | --- | ---: | ---: |
| windows/386 | `main.main` | 28 | 9431134986526002895 |
| windows/amd64 | `main.main` | 61 | 14431951123364073089 |
| linux/386 | `main.main` | 27 | 9411578800943819104 |
| linux/amd64 | `main.main` | 61 | 14431951123364073089 |

## Reproduction

Use the pinned SDK above, with `GOTOOLCHAIN=local`, `GOENV=off`, `CGO_ENABLED=0`, `GOAMD64=v1` or `GO386=sse2`, and the effective settings recorded in provenance. For each target:

1. Run `go run scripts/golang/gogen_stdlib_coverage.go -goos <os> -goarch <arch>` into a fresh directory's `main.go`. The generator runs on the build host; the resulting coverage executable does not run.
2. Write `go.mod` containing `module stdcov`, a blank line and `go 1.27`. Run `GOOS=<os> GOARCH=<arch> CGO_ENABLED=0 go build -trimpath -o <binary> .`. Repeat the build and compare SHA-256. `GOFLAGS=-p=2`, `GOMAXPROCS=2` and `GOMEMLIMIT=2GiB` limit build resources.
3. Run `python scripts/golang/run_smda.py <binary> <raw.smda> <version-label> <filename-label>`; use `1.27.3 x86/x64` for Windows and `1.27.3 linux x86/x64` for Linux, as recorded in the exports. Require report status `ok`.
4. Load with `SmdaReport.fromDict`, remove only functions whose `function_name.startswith("main.")`, clear `report._sorted_functions`, and call the existing `corpus.smdaify._recompute_statistics(report)` before serializing. Record every removed name, size and PicHash. Check named function entry VAs against `go tool nm -size`.
5. Run `python scripts/golang/smda2mcrit.py <output.mcrit> <filtered.smda>`, then archive exactly that filtered report. The manifest records the archive encoder: Windows amd64 used py7zr 1.1.4 default filters; subsequent targets use native 7-Zip with `-t7z -m0=lzma2 -mx=3`. Compression changes archive bytes, not report contents.

The generated source SHA-256 values and API-reference summaries in provenance check that the same driver was produced. The SDK and compiler/runtime sources are not patched. Temporary binaries, SDK copies, build trees and caches are deleted after conversion.

## Coverage limits

The generator retains exported non-generic functions and methods from importable standard-library packages, together with code they reach. It skips generic declarations/receivers, interfaces, aliases and inaccessible/internal/vendor packages as direct API targets; generic and internal code reached transitively remains present. Its skip list excludes cgo, race/msan/asan runtimes, plugins and wasm-only `syscall/js`. A zero generator-error count applies after those exclusions.

This is the default, non-cgo, non-race build for PE/ELF x86/x64. It does not claim every Go build mode, generic instantiation, CPU tuning level or platform. Only one compiler version is added; existing versions are not rebuilt. Unnamed bodies are retained without assigning a source identity.

The manifest enumerates positive-sized `nm` text entries absent from the retained report (excluding intentionally removed driver entries). These compiled symbols are not claimed as recovered functions. SMDA reports analysis failures listed above. SMDA 5.0.2 contains the upstream mask-bound fix for [smda#363](https://github.com/danielplohmann/smda/issues/363), merged in [smda#380](https://github.com/danielplohmann/smda/pull/380). Older Windows reports still await regeneration; the presence of that fix does not establish perfect recovery of this version. Entry-name agreement is checked separately from body accuracy. No analyzer gap is hidden or fixed by modifying source.

## cgo and race variants

The coverage limits above name cgo and the race runtime. Both are built here from the same generated driver, Go 1.27.3 tarball and flags, with `scripts/golang/build_variant.sh` on an ubuntu-24.04 runner (run 42779778768): `CGO_ENABLED=1` (gcc 13 for Linux, the mingw-w64 gcc 13 for Windows), and `CGO_ENABLED=1 -race` on the two targets with a race runtime, linux/amd64 and windows/amd64. The coverage driver's `main.main` is removed before export as in the default references, with the statistics recomputed by `corpus.smdaify._recompute_statistics` (`scripts/golang/drop_driver.py`). Records with binary, report and export digests: [variants.json](variants.json).

| Target | Kept | Driver removed | Recovered image total | Distinct PicHashes (10+) | Shared with the default 1.27.3 image |
| --- | ---: | ---: | ---: | ---: | ---: |
| cgo windows/386 | 20674 | 1 | 20675 | 15566 | 15565 |
| cgo windows/amd64 | 20123 | 1 | 20124 | 13965 | 13964 |
| cgo linux/386 | 20834 | 1 | 20835 | 15710 | 5886 |
| cgo linux/amd64 | 20840 | 1 | 20841 | 14125 | 13963 |
| race windows/amd64 | 21419 | 1 | 21420 | 15536 | 1821 |
| race linux/amd64 | 22230 | 1 | 22231 | 15993 | 1881 |

On Windows no standard-library package of this driver has a cgo implementation, so the cgo images differ from the default ones only by one PicHash (and their binary digests); they are filed because they are not identical. On Linux cgo links `runtime/cgo` and the cgo halves of `net` and `os/user`; the 32-bit Linux PicHashes follow the image layout, which is why that pair shares fewer. The race images instrument every function and share about an eighth with the default build. Plugins, msan/asan and wasm stay out of scope as above.

