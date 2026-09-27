# MSVC coverage for the generated corpus families — feasibility survey

Research only. Nothing under `data/` was touched, no build was run, no `refilter`,
no `validate --deep`.

Everything below is marked **[read]** when it comes from an upstream file I actually
opened at the pinned ref, **[listed]** when it comes from a directory listing of the
pinned ref (file exists, contents not read), **[measured]** when it comes from the
committed data in this repository, and **[inferred]** when it is reasoning from the
existing recipe or from general knowledge that I did not verify against a file.

---

## 0a. Corrections made to this survey after it was written

Two entries below were checked again while the recipes were being written,
and one of them was wrong.

**jemalloc is not feasible on the runner, and this survey said it was.**
Section 2 claims three overrides in a props file are all that is needed.
That is not the blocker. `msvc/ReadMe.txt` step 5 requires
`sh -c "CC=cl ./autogen.sh"` *before* the solution can be opened: at tag
5.3.0 the tree ships `configure.ac` and no `configure`, and
`include/jemalloc/` holds only `.h.in` templates and `.sh` generators. The
vcxproj includes `..\..\..\..\include`, i.e. headers that do not exist
until autoconf and configure have run. Upstream's own `.appveyor.yml`
confirms the shape - MSYS2, `autoconf`, `./configure`, `mingw32-make`, with
MSVC only selecting vcvarsall. So an MSVC jemalloc needs autoconf on
windows-2022: the same class of problem as OpenSSL needing NASM, in a
family this survey rates low-medium value. **Dropped.**

Two smaller corrections to the same entry: the Release (DynamicLibrary)
configurations do not set `RuntimeLibrary` at all - `MultiThreaded` appears
only in `Release-static`, and MSBuild's Release default is already
`MultiThreadedDLL` - and `GenerateDebugInformation` is already `true` in
every Release config. Two of the three claimed overrides are unnecessary.

**mbedTLS's open question is settled, and the answer was no.** Section 2
records that it was not verified whether mbedTLS's CMake produces usable
DLLs under MSVC. It does not on its own: there is no `__declspec(dllexport)`
anywhere in the tree and nothing sets `WINDOWS_EXPORT_ALL_SYMBOLS`. Under
MinGW `ld` auto-exports and hides this; under MSVC `mbedcrypto.dll` would
export nothing, produce no import library, and the `mbedx509` link would
fail. `-DCMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON` is what makes the build exist.

---

## 0. Corrections to the premise

Two numbers in the brief are slightly off, and the difference matters for planning.

* **155 MinGW artefacts is correct**, but they belong to **31 families, not 37**
  [measured, `data/*/provenance.json`]. 37 is the number of families carrying a
  `provenance.json` at all; of those, 3 are MSVC-only recipes (VX-API, BlackBone,
  SysWhispers) and 3 are blob-extraction recipes whose bytes were already compiled
  by MSVC upstream (donut, sRDI, pe_to_shellcode). So the coverage gap is
  **31 families / 155 artefacts**, spread over **130 `(recipe, toolchain)` builds**
  (libstdc++ excluded, see §4).

* **One of those 31 already has MSVC coverage.** `data/libzlib` carries 18
  IDA-derived ShiftMediaProject artefacts for 1.2.8 / 1.2.9 / 1.2.10 / 1.2.11 under
  MSVC12 / MSVC14 / MSVC15, alongside its 8 MinGW ones [measured]. Every other
  library family in `data/` has **zero** MSVC artefacts — verified by comparing
  `.mcrit` file counts against `provenance.json` record counts; only `Golang`,
  `MSVC`, `MinGW`, `Rust`, `aPLib`, `nim` and `libzlib` hold anything that did not
  come out of a recipe.

The headline claim of the brief survives intact and is if anything understated:
30 of 31 generated library families carry exactly one compiler, and it is the wrong
one for the likeliest sighting.

---

## 1. What an MSVC recipe has to look like here — the shared mechanics

These constraints apply to *every* family below, so they are stated once. They come
out of `recipe.py`, `build.py`, `toolchain.py`, `baseline.py` and the three existing
MSVC recipes.

### 1.1 An MSVC build needs its own `RECIPES` key, not an extra toolchain id

`Recipe` has **one** `build` list shared by all of its `toolchains` [read,
`scripts/corpus/recipe.py`], and `build.py` runs every step through
`subprocess.run(..., shell=True)` — which on a Windows runner is `cmd.exe` [read,
`scripts/corpus/build.py`]. Every existing library recipe's commands are
Linux-shell-only (`$(nproc)`, `find … | tr`, `&&` chains over POSIX paths). So
*adding `"msvc_x86", "msvc_x64"` to an existing recipe's `toolchains` list cannot
work.* Each MSVC build must be a separate registry entry, e.g.
`"libzlib_1.3.1_msvc"`, with the same `family=` and `version=` and
`toolchains=["msvc_x86", "msvc_x64"]`.

That is safe for naming: `Recipe.slug()` builds the stem from
`family_version_<toolchain.short_id>_arch_component`, and `short_id` is `msvc143`
for MSVC versus `mingw13` for GCC [read, `toolchain.py`], so an MSVC twin never
collides with its MinGW sibling and both live in the same `provenance.json`.

### 1.2 A PDB is not optional

MSVC keeps symbols in a PDB, not in a COFF symbol table. `smdaify` rejects a build
whose named-function ratio falls below `min_named_ratio` (default 0.5) [read,
`smdaify.py`], and `build.py` refuses an artefact whose declared `pdb` file is
missing [read]. So every MSVC recipe must:

* compile with `/Zi` and a shared `/Fd`,
* link with `/DEBUG` and an explicit `/PDB:`,
* declare `Artifact(pdb=…)`.

For a CMake family this is *not* the default: CMake's MSVC `Release` config is
`/MD /O2 /Ob2 /DNDEBUG` with no `/Zi` and no `/DEBUG` at link [inferred — CMake's
documented default flags; I did not read a CMake module here]. Two ways out:

* `-DCMAKE_BUILD_TYPE=RelWithDebInfo` — gets `/Zi` and `/DEBUG` for free, but drops
  to `/Ob1`, which is not what a shipped Release binary looks like; or
* `-DCMAKE_BUILD_TYPE=Release` plus explicit
  `-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"` and
  `-DCMAKE_SHARED_LINKER_FLAGS="/DEBUG /Brepro /OPT:NOICF"`.

I recommend the second and recording it verbatim in `build_flags`.

### 1.3 `/MD`, always, for a library

`cl`'s default is `/MT`, and `/LD` implies `/MT` unless `/MD` is given. The VX-API
docstring records what that cost once: 1947 of 4219 functions were MSVC C runtime,
924 of them the `__crt_stdio_output` printf machinery, filed under VX-API and
duplicating `data/MSVC`. Under `/MD` the CRT stays in `ucrtbase`/`vcruntime140` and
only import thunks appear. Nothing in this corpus wants a static CRT, so `/MD` (or
MSBuild `RuntimeLibrary=MultiThreadedDLL`) belongs in every recipe below.

Two families' upstream MSVC build systems default to `/MT` and must be overridden:
**7-Zip** (`CPP/Build.mak`: `-MD` only when `MY_DYNAMIC_LINK` is non-empty, else
`-MT`) [read] and **jemalloc** (`msvc/projects/vc2017/jemalloc/jemalloc.vcxproj`:
`<RuntimeLibrary>MultiThreaded`) [read].

### 1.4 `/Brepro` on every link

Without it MSVC stamps the PE with the build time and two runs of identical source
produce different `sha256`s — which the BlackBone x86 DLL actually did between two
green runs [read, `blackbone.py`]. Where the link line is upstream's, `/Brepro` has
to arrive through a command-line override (`LFLAGS=` for nmake,
`CMAKE_SHARED_LINKER_FLAGS` for CMake) or, for MSBuild, through the
`ForceImportBeforeCppTargets` props trick BlackBone already uses.

### 1.5 `/OPT:NOICF`, and think about `/OPT:REF`

Identical COMDAT folding is on by default in a release link and merged VX-API's
`StringConcat` and `StringCopy` into one entry [read, `vxapi.py`]. For reference
data that is straight loss. Note the interaction: **`link /DEBUG` flips the
defaults to `/OPT:NOREF /OPT:NOICF`** [inferred — documented linker behaviour, not
verified here], so a recipe that adds `/DEBUG` may already get both, but it should
still say so explicitly rather than rely on it.

### 1.6 The big one: MSVC builds static `.lib`, and SMDA cannot read `.lib`

Under MinGW these recipes lean on `CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS` or on
`ld --whole-archive` to turn an archive into a DLL. Under MSVC the equivalents are
`-DCMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON` (CMake generates a `.def` by dumping the
objects — this is primarily an MSVC feature) and `link /WHOLEARCHIVE:foo.lib`
[inferred; both are documented, neither verified against a file here]. Families
where the upstream MSVC path produces only a static library, so a wrapper DLL link
is unavoidable:

* **cryptopp** — `cryptlib.vcxproj` is the static library; `cryptdll.vcxproj` is
  upstream's FIPS-subset DLL, the same trap the GNUmakefile has [listed].
* **libtomcrypt** — `makefile.msvc` says so in its own comment: "this makefile
  builds only static libraries", target `tomcrypt.lib` [read].
* **abseil**, **protobuf 3.6.1 / 21.12**, **re2 2022-06-01** — same shape as their
  MinGW recipes.
* **bzip2** — `makefile.msc` builds `libbz2.lib` and `bzip2.exe`, no DLL rule
  [read]; upstream does ship `libbz2.def`.

### 1.7 The MSVC glue baseline is measurably incomplete — see §6

Stated here because it shapes every recipe: the probe filter removes most but not
all Microsoft runtime code, and a wave of 30 families multiplies the residue.

---

## 2. Feasibility, family by family

Ordered alphabetically. "Builds" = `(recipe version × architecture)` pairs that the
MinGW side has, which is what an MSVC mirror would cost.

### 7-Zip — 2 versions, 4 builds
* **Build system now:** upstream's own GCC makefile
  `CPP/7zip/Bundles/Format7zF/../../cmpl_gcc_{x86,x64}.mak`, with `USE_ASM=` because
  the hand-written fast paths are MASM and need `asmc` under GCC.
* **Upstream MSVC path:** `CPP/7zip/Bundles/Format7zF/makefile` → `../../7zip.mak`
  → `../../../Build.mak`, an nmake build [read, 26.03 tarball]. `Build.mak` sets
  `MY_ML = ml64 -WX` for `PLATFORM=x64` and `ml -WX` otherwise, so **the MSVC build
  assembles 7-Zip's LZMA/AES/CRC/SHA assembly that the MinGW build has to omit**.
* **Verdict: Moderate.** Real coverage gain, not a re-run.
* **Command (derived from the makefiles I read; not executed):**
  ```
  cd CPP\7zip\Bundles\Format7zF
  nmake -f makefile PLATFORM=x64 MY_DYNAMIC_LINK=1 ^
        CFLAGS_COMMON="-Zi -Fdx64\7z.pdb" CFLAGS_WARN_LEVEL= ^
        LFLAGS="-DEBUG -PDB:x64\7z.pdb -Brepro -OPT:NOICF"
  ```
  `PLATFORM` also names the output dir (`O=$(PLATFORM)`), so the artefact is
  `CPP/7zip/Bundles/Format7zF/x64/7z.dll`. `CFLAGS_WARN_LEVEL=` is the MSVC analogue
  of the `-Werror` override the MinGW recipe already needs; `Build.mak` compiles with
  `-Wall -WX` [read] and 23.01 is old enough that v143 is likely to object — same
  class of problem GCC 13 had with `ComHandler.cpp`. `MY_DYNAMIC_LINK=1` is what
  selects `-MD` over `-MT` [read].
* **Dependencies:** none external. Note `7z.dll` already contains Zstd and xxHash
  (26.03) and the LZFSE decoder — same third-party overlap the MinGW notes record;
  under MSVC the Zstd/xxHash bodies would become new cross-family neighbours of
  nothing in this corpus (no zstd family here), so no new leak.
* **Value: high.** 7z.dll and its LZMA are among the most copy-pasted compression
  bodies on Windows, and essentially every real sighting is MSVC-built with the
  assembly enabled — i.e. the MinGW artefact is the *less* representative one.

### abseil — 2 versions, 4 builds
* Now: CMake cross build, static archives linked into one DLL with `--whole-archive`.
* MSVC: same CMake, plus `/WHOLEARCHIVE` wrapper, or `-DBUILD_SHARED_LIBS=ON
  -DCMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON` (which is what the re2 recipe already does
  for Abseil under MinGW).
* **Verdict: Moderate** — configure is trivial, the packaging is the work.
* Command [inferred from the existing recipe; I did not read Abseil's CMakeLists]:
  ```
  cmake -S . -B build-x64 -G Ninja -DCMAKE_BUILD_TYPE=Release ^
    -DCMAKE_CXX_STANDARD=17 -DBUILD_TESTING=OFF -DABSL_PROPAGATE_CXX_STD=ON ^
    -DBUILD_SHARED_LIBS=ON -DCMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON ^
    -DCMAKE_CXX_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi" ^
    -DCMAKE_SHARED_LINKER_FLAGS="/DEBUG /Brepro /OPT:NOICF"
  ```
* **Dependencies:** none, but see §6 — an MSVC C++ build instantiates MSVC STL
  templates into the artefact, and Abseil is the family most likely to collide with
  protobuf and re2 on those.
* **Value: medium-high.** Abseil reaches analysts mostly *inside* protobuf/gRPC/Chrome
  derivatives, all MSVC-built.

### bzip2 — 1 version, 2 builds
* Now: hand-written `cl`-equivalent loop over seven objects, linked against upstream's
  `libbz2.def`.
* Upstream MSVC: `makefile.msc`, nmake, `CFLAGS = -DWIN32 -MD -Ox
  -D_FILE_OFFSET_BITS=64 -nologo`, targets `libbz2.lib` + `bzip2.exe` [read, local
  1.0.8 tarball]. Already `/MD`. No DLL rule, no `/Zi`.
* **Verdict: Easy.**
* Command:
  ```
  nmake -f makefile.msc CFLAGS="-DWIN32 -MD -Ox -Zi -Fdbzip2.pdb -D_FILE_OFFSET_BITS=64 -nologo" lib
  cl -nologo -MD -Ox -Zi -Fdbzip2.pdb bzip2.c libbz2.lib setargv.obj ^
     /Fe:bzip2.exe /link /DEBUG /PDB:bzip2.pdb /Brepro /OPT:NOICF
  ```
  Keep the MinGW recipe's choice of shipping the EXE (superset of the DLL by 45 of
  46 functions) rather than both.
* **Dependencies:** none. `setargv.obj` is a CRT object, not a family.
* **Value: medium-high.** bzip2 in installers and archivers is overwhelmingly
  MSVC-built; cheap to add.

### cJSON — 3 versions, 6 builds
* Now: CMake. MSVC: same, `-DENABLE_CJSON_TEST=Off -DBUILD_SHARED_AND_STATIC_LIBS=Off`.
* **Verdict: Easy.**
* **Watch:** the MinGW artefacts are shaped by cJSON's own
  `ENABLE_CUSTOM_COMPILER_FLAGS` (`-std=c89 -fstack-protector-strong
  -fvisibility=hidden`) which is GCC/Clang-only and is filtered through
  `CHECK_C_COMPILER_FLAG` [read, recipe comment]. Under MSVC that whole list drops
  out, so the MSVC artefact will differ from the MinGW one by more than the code
  generator — record that in `build_flags` rather than copying the MinGW string.
* **Dependencies:** none.
* **Value: medium-high.** Very widely vendored, and vendored copies in MSVC projects
  are compiled by the host project with MSVC.

### cryptopp — 3 versions, 6 builds
* Now: upstream `GNUmakefile` → `libcryptopp.a` → `--whole-archive` DLL.
* Upstream MSVC: `cryptlib.vcxproj` (static), `cryptdll.vcxproj` (FIPS-subset DLL),
  `cryptest.sln`, `cryptest.nmake` — present at both `CRYPTOPP_8_9_0` and
  `CRYPTOPP_5_6_5` [listed]. 5.6.5 also still ships a `CMakeLists.txt`; 8.9.0 does
  not [listed].
* **Verdict: Moderate.** Build `cryptlib.vcxproj` with MSBuild (`/p:PlatformToolset=v143`
  as BlackBone does), then wrap:
  ```
  msbuild cryptlib.vcxproj /p:Configuration=Release /p:Platform=x64 ^
          /p:PlatformToolset=v143 /p:RuntimeLibrary=MultiThreadedDLL /m /v:minimal
  echo int anchor(void){return 0;} > anchor.c
  cl /nologo /O2 /MD /Zi /Fdcryptopp.pdb /c anchor.c
  link /nologo /DLL /DEBUG /Brepro /OPT:NOREF /OPT:NOICF ^
       /WHOLEARCHIVE:x64\Output\Release\cryptlib.lib ^
       /PDB:cryptopp.pdb /OUT:cryptopp.dll anchor.obj ws2_32.lib
  ```
  (The vcxproj's output path is upstream's; confirm it from the project file before
  writing the recipe — I listed the file but did not read it.)
* **Watch:** the MinGW recipe pins `CXXFLAGS` on the command line specifically to stop
  5.6.5 appending `-march=native`. The MSVC project has its own per-file ISA settings;
  do **not** flatten them, for the same reason the MinGW recipe does not.
* **Dependencies:** vendored TweetNaCl, curve25519-donna, Botan ChaCha and Crypto++'s
  own DEFLATE — all already attributed to cryptopp under MinGW, so no *new* leak, but
  note Crypto++'s `zdeflate/zinflate/zlib.cpp` is not zlib's code and must not be
  confused with `data/libzlib` if a `validate --deep` round flags it.
* **Value: high.** Crypto++ in malware is essentially always MSVC-built.

### jemalloc — 1 version, 2 builds
* Now: autotools (`autogen.sh --host=…`).
* Upstream MSVC: `msvc/jemalloc_vc2015.sln`, `msvc/jemalloc_vc2017.sln`, with
  `msvc/projects/vc2017/jemalloc/jemalloc.vcxproj` [listed]. Read from that project:
  configurations `Debug / Debug-static / Release / Release-static`, platforms
  `Win32 / x64`, `ConfigurationType` `DynamicLibrary` for the non-static ones,
  `PlatformToolset v141`, `RuntimeLibrary MultiThreaded` (i.e. `/MT`),
  `DebugInformationFormat OldStyle` (`/Z7`) [read].
* **Verdict: Moderate** — three overrides needed: toolset `v141 → v143`,
  `/MT → /MD`, and forcing `GenerateDebugInformation` so a PDB comes out. All three
  fit in a `ForceImportBeforeCppTargets` props file, exactly as `blackbone.py` does
  for `/permissive` and `/Brepro`, so upstream source stays untouched.
* Command:
  ```
  msbuild msvc\projects\vc2017\jemalloc\jemalloc.vcxproj ^
     /p:Configuration=Release /p:Platform=x64 /p:PlatformToolset=v143 ^
     /p:ForceImportBeforeCppTargets=%CD%\msvcprops.props /m /v:minimal
  ```
* **Dependencies:** none.
* **Value: low-medium.** Firefox-derived code and some game/anti-cheat stacks; those
  *are* MSVC-built, so the MSVC build is the more representative one — but the family
  is small and rarely decisive in triage.

### Lua — 3 versions, 6 builds
* Now: `make generic` with the cross compiler; artefact is the statically linked
  `lua.exe`.
* Upstream MSVC: **5.1.5 ships `etc/luavs.bat`** — `cl /nologo /MD /O2 /W3 /c
  /D_CRT_SECURE_NO_DEPRECATE`, `link /DLL /out:lua51.dll l*.obj`, then `lua.exe`
  [read, local tarball]. **5.4.8 ships nothing of the sort**: `src/` is 30 `.c` files
  and a GNU `Makefile`, and there is no `etc/` directory at all [read, local tarball].
  5.3.6 not checked, but 5.3 dropped `etc/` too [inferred].
* **Verdict: Moderate.** 5.1.5 is upstream's own script; 5.3/5.4 need the same two
  commands written out, which is the same kind of hand-written line the sqlite3 and
  bzip2 recipes already carry — not a patch to upstream.
* Command (5.4.x, modelled directly on `luavs.bat`):
  ```
  cd src
  cl /nologo /MD /O2 /W3 /Zi /Fdlua.pdb /c /D_CRT_SECURE_NO_DEPRECATE l*.c
  del lua.obj luac.obj
  link /nologo /DEBUG /Brepro /OPT:NOICF /PDB:lua.pdb /OUT:lua.exe l*.obj
  ```
  — but note `luavs.bat` builds `lua.exe` *against the DLL*, whereas the MinGW recipe
  deliberately keeps the statically linked EXE because that is how Lua is embedded.
  Decide one and record it; I would keep the static EXE for continuity.
* **Dependencies:** none.
* **Value: medium.** Lua-embedding Windows tooling is mostly MSVC-built.

### LuaJIT — 3 versions, 6 builds
* Now: upstream `make` with `CROSS=`, `HOST_CC` matched to target pointer size.
* Upstream MSVC: **`src/msvcbuild.bat` exists at all three pinned commits**
  (`0bf80b07…` 2.0.5, `8271c643…` 2.1.0-beta3, `c6ffc141…` 2.1-rolling) — HTTP 200 for
  each [listed]. Read at 2.1.0-beta3: `cl /nologo /c /O2 /W3
  /D_CRT_SECURE_NO_DEPRECATE /D_CRT_STDIO_INLINE=__declspec(dllexport)__inline`,
  builds `minilua.exe` then `buildvm.exe` then `lua51.dll`; x86 adds `/arch:SSE2`;
  architecture is detected from the *host* `minilua` [read].
* **Verdict: Moderate** (upstream script, but a script this tooling does not use).
* Command: `cd src && msvcbuild.bat` — run under the matching `vcvarsall` arch.
  `/Zi` and a PDB are **not** in the script, so `LJCOMPILE`/`LJLINK` need a wrapper or
  the script's variables need to be re-spelled inline. That is the one real cost here.
* **Watch:** the interpreter core is DynASM assembly and is compiler-independent — but
  the *surrounding* C (the JIT, GC, FFI, library glue) is not, and that is the bulk of
  the function count.
* **Dependencies:** none.
* **Value: medium.** LuaJIT-based Windows tooling (TINN and its descendants) is
  MSVC-built, and `lua51.lib` as shipped by those projects is an MSVC artefact, so the
  MSVC build is the closer match to the thing that actually turns up.

### libcurl — 2 versions, 4 builds
* Now: CMake, Schannel backend, everything optional off.
* Upstream MSVC: the same CMake, plus `winbuild/Makefile.vc` (present at both
  `curl-8_4_0` and `curl-8_15_0`) [listed] and `projects/Windows/VC10…VC12` solutions
  [listed].
* **Verdict: Easy** — the existing configure line transfers almost verbatim; drop the
  cross variables, add the flags block from §1.2.
* Command:
  ```
  cmake -S . -B build-x64 -G Ninja -DCMAKE_BUILD_TYPE=Release ^
    -DBUILD_SHARED_LIBS=ON -DCURL_USE_SCHANNEL=ON -DCURL_USE_LIBPSL=OFF ^
    -DCURL_ZLIB=OFF -DCURL_BROTLI=OFF -DCURL_ZSTD=OFF -DUSE_LIBIDN2=OFF ^
    -DBUILD_TESTING=OFF -DBUILD_CURL_EXE=OFF ^
    -DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi" ^
    -DCMAKE_SHARED_LINKER_FLAGS="/DEBUG /Brepro /OPT:NOICF"
  cmake --build build-x64
  ```
* **Dependencies:** none — Schannel is the reason. Keeping `CURL_ZLIB=OFF` is
  load-bearing for the same reason it is under MinGW: zlib is its own family.
* **Value: very high.** libcurl inside downloaders and droppers is the archetypal
  MSVC-built statically linked dependency, and the corpus currently answers it with
  GCC code only.

### libevent — 1 version, 2 builds (2 DLLs each)
* Now: CMake. Upstream also ships `Makefile.nmake` [listed].
* **Verdict: Easy.** Same configure line minus the cross variables.
* **Dependencies:** OpenSSL backend already disabled; keep it that way.
* **Value: medium.** Older tooling, and the MSVC build is what Windows binaries carry.

### liblzma (xz) — 2 versions, 4 builds
* Now: CMake.
* **Verdict: Easy.**
* **Watch:** 5.8.1's `CMakeLists.txt` does a `string(REPLACE -O3 -O2 …)` on the
  Release flags [read, recipe comment]; that replace targets GCC spellings and will
  not fire under MSVC, so the MSVC `build_flags` string must not be copied from the
  MinGW one.
* **Dependencies:** none.
* **Value: high.** LZMA2 in installers and droppers, and 7-Zip aside, liblzma in the
  wild on Windows is MSVC-built.

### libpng — 1 version, 2 builds
* Now: CMake, linking against a *staged zlib import library* precisely so zlib's code
  does not end up inside `libpng16.dll` — the recipe records that the static link put
  62 of libpng's 500 functions' worth of zlib in the artefact.
* Upstream MSVC: CMake, plus `projects/vstudio/` (with `zlib.vcxproj` and
  `zlib.props` right next to `libpng.vcxproj`) and `projects/visualc71/` [listed].
* **Verdict: Easy, with a hard ordering constraint.**
  **Do not use `projects/vstudio/`** — it builds zlib into the same solution and would
  recreate exactly the contamination the MinGW recipe was fixed to avoid. Use CMake
  with `ZLIB_LIBRARY` pointed at an **MSVC-built `zdll.lib`**, which means the MSVC
  libzlib recipe has to land first.
* Command: stage zlib with `nmake -f win32/Makefile.msc` (see libzlib), then
  `-DZLIB_INCLUDE_DIR=%CD%\zlib -DZLIB_LIBRARY=%CD%\zlib\zdll.lib` alongside the
  standard `-DPNG_SHARED=ON -DPNG_STATIC=OFF -DPNG_TESTS=OFF -DPNG_TOOLS=OFF`.
* **Value: medium.** Real, but libpng-in-malware is mostly a transitive dependency.

### libsodium — 2 versions, 4 builds
* Now: autotools (`./configure --host=…`), plus an `autogen.sh` dance for 1.0.18.
* Upstream MSVC: `builds/msvc/` with `buildall.bat` / `buildbase.bat` and solutions
  for **vs2010–vs2019 at tag 1.0.18** [listed] and **vs2010–vs2022 in the 1.0.20
  release tarball** [listed, local tarball].
* **Verdict: Moderate.** 1.0.20 is nearly free (vs2022 solution, `v143`). 1.0.18 needs
  a `/p:PlatformToolset=v143` override on the vs2019 solution.
* Command (1.0.20):
  ```
  msbuild builds\msvc\vs2022\libsodium\libsodium.vcxproj ^
     /p:Configuration=ReleaseDLL /p:Platform=x64 /m /v:minimal
  ```
  Confirm the configuration name against `builds/msvc/properties/ReleaseDLL.props`
  before writing the recipe — the props file exists [listed] but I did not read it,
  and I also did not verify that the Release configurations set `/Zi`.
* **Dependencies:** none.
* **Value: high.** A libsodium hit is immediately meaningful in ransomware triage, and
  ransomware on Windows is MSVC-built. This is one of the clearest wins per unit work.

### libstdc++ — 1 build
* **Verdict: Pointless.** The recipe exists to fill a 32-bit gap in `data/MinGW`, and
  its whole subject is the *GCC* runtime — it deliberately links `-static-libstdc++
  -static-libgcc` and turns the glue filter off. The MSVC equivalent is the MSVC C++
  runtime, which is `data/MSVC`, already in the corpus with 22 artefacts. An "MSVC
  libstdc++" is a category error.
* Exclude from every count and every schedule.

### libtiff — 2 versions, 4 builds
* Now: CMake, all optional codecs off.
* **Verdict: Easy.**
* **Dependencies:** none, because the codecs that would pull zlib / liblzma / libjpeg
  are already disabled. Keep every one of those `-D…=OFF` — under MSVC, CMake may find
  a vcpkg-installed zlib on the runner and silently link it, which would put
  `data/libzlib` code inside a libtiff artefact.
* **Value: medium.** Long CVE history, embedded widely, and image-handling stacks on
  Windows are MSVC.

### libtomcrypt — 1 version, 2 builds
* Now: `makefile.mingw`, which **hardcodes `-s` on the DLL link**, so the committed
  artefacts are stripped, `min_named_ratio` is set to 0, and — because the glue filter
  matches on *names* — MinGW runtime code is still sitting in them
  (`removed_runtime_functions` is empty for both) [read, recipe; measured,
  provenance].
* Upstream MSVC: `makefile.msvc` [read in full]. `LTC_CFLAGS = /nologo /Isrc/headers/
  /Itests/ /D_CRT_SECURE_NO_WARNINGS /D_CRT_NONSTDC_NO_DEPRECATE /DLTC_SOURCE /W3
  $(CFLAGS)` with `CFLAGS = /Ox /DUSE_LTM /DLTM_DESC /I../libtommath`, and its own
  comment says **"this makefile builds only static libraries"**, target `tomcrypt.lib`.
  It documents the exact override this corpus needs:
  `nmake -f makefile.msvc CFLAGS="/DUSE_LTM /DLTM_DESC /Ic:\path\to\libtommath"
  EXTRALIBS=c:\path\to\libtommath\tommath.lib all`.
  LibTomMath ships its own `makefile.msvc` [inferred from that usage line; not read].
* **Verdict: Moderate** (static lib → wrapper DLL, plus an MSVC LibTomMath first).
* Command:
  ```
  nmake -f makefile.msvc -C ltm            :: LibTomMath -> tommath.lib
  nmake -f makefile.msvc CFLAGS="/Ox /Zi /Fdltc.pdb /DUSE_LTM /DLTM_DESC /Iltm" ^
        EXTRALIBS=ltm\tommath.lib
  link /nologo /DLL /DEBUG /Brepro /OPT:NOREF /OPT:NOICF ^
       /WHOLEARCHIVE:tomcrypt.lib /WHOLEARCHIVE:ltm\tommath.lib ^
       /PDB:libtomcrypt.pdb /OUT:libtomcrypt.dll anchor.obj advapi32.lib
  ```
* **Dependencies:** LibTomMath is statically linked and already accounts for ~175
  `mp_*`/`s_mp_*`/`fast_mp_*` functions in the MinGW artefact. Under MSVC the same
  holds; pin it through `extra_sources` exactly as the MinGW recipe does, and keep the
  note. There is no LibTomMath family here for it to collide with.
* **Value: high — and unusually so, because this MSVC build is strictly better data
  than the MinGW one it joins.** A PDB-symbolised, glue-filtered libtomcrypt would be
  the first properly named one in the corpus. Rank it above its raw popularity.

### libuv — 2 versions, 4 builds
* Now: CMake. Only a `CMakeLists.txt` in the tree [listed, v1.52.1].
* **Verdict: Easy.** `-DLIBUV_BUILD_TESTS=OFF -DBUILD_SHARED_LIBS=ON` plus §1.2 flags.
* **Dependencies:** none.
* **Value: medium-high.** Node.js and Electron on Windows are MSVC-built and vendor
  libuv; every one of those sightings is currently answered by GCC code.

### libxml2 — 2 versions, 4 builds
* Now: CMake, codecs off.
* Upstream MSVC: `win32/Makefile.msvc` + `win32/configure.js` at **both** `v2.9.14`
  and `v2.14.3` [listed], plus `win32/VC10/libxml2.sln` at 2.9.14 only [listed].
  `CMakeLists.txt` is present at both.
* **Verdict: Easy** via CMake; `win32/Makefile.msvc` is the historically representative
  path and would be the more faithful choice if you want to match ShiftMediaProject-era
  binaries.
* **Dependencies:** keep `LIBXML2_WITH_ZLIB=OFF`, `…_LZMA=OFF`, `…_ICONV=OFF` — all
  three would statically absorb another family or a vcpkg library.
* **Value: high.** libxml2 is vendored enormously, and the recipe's own docstring
  already flags that the MSVC side is the one that matters and that ShiftMediaProject's
  frozen MSVC builds are the alternative route.

### libzlib — 4 versions, 8 builds
* Now: `win32/Makefile.gcc`.
* Upstream MSVC: `win32/Makefile.msc` [read, 1.3.1 tarball]. It is already almost
  exactly what this corpus wants:
  `CFLAGS = -nologo -MD -W3 -O2 -Oy- -Zi -Fd"zlib"`,
  `LDFLAGS = -nologo -debug -incremental:no -opt:ref`,
  target `zlib1.dll` built from `win32/zlib.def` with an implib `zdll.lib`. `/MD`,
  `/Zi` and `/debug` are upstream defaults. Also present: `CMakeLists.txt` and
  `contrib/vstudio/{vc9,vc10,vc11,vc12,vc14,vc17}` [listed].
* **Verdict: Easy** — the easiest family in the corpus.
* Command:
  ```
  nmake -f win32\Makefile.msc LDFLAGS="-nologo -debug -incremental:no -opt:ref -Brepro -opt:noicf" zlib1.dll
  ```
  (`zlib.pdb` from `-Fd"zlib"`; declare it as the artefact's `pdb`. Older versions'
  `Makefile.msc` may differ — I read 1.3.1 only; 1.2.8's must be checked.)
* **Dependencies:** none. Produces `zdll.lib`, which **libpng needs**.
* **Value: medium as data, very high as an enabler.** 1.2.8–1.2.11 already have
  MSVC12/14/15 rows from ShiftMediaProject, so an msvc143 build there is a fourth
  compiler generation for already-covered source; 1.2.13 and 1.3.1 have **no** MSVC
  coverage at all, and 1.3.1 is what anything built today links. Do it first anyway,
  because it costs minutes and unblocks libpng.

### lz4 — 2 versions, 4 builds
* Now: `lib/Makefile` with `TARGET_OS=MINGW64`.
* Upstream MSVC: `build/cmake/CMakeLists.txt`, `build/VS2022/lz4.sln` with
  `liblz4-dll/liblz4-dll.vcxproj`, and `build/visual/generate_vs2022.cmd`, at both
  `v1.9.4` and `v1.10.0`; 1.9.4 additionally has VS2010 and VS2017 solutions [listed].
* **Verdict: Easy** (via `build/cmake`) or Moderate (via the VS2022 solution).
* Command: `cmake -S build/cmake -B build-x64 -G Ninja -DBUILD_SHARED_LIBS=ON …`
  with the §1.2 flags block. (I did not read `build/cmake/CMakeLists.txt`, so confirm
  the shared-library option name.)
* **Dependencies:** the DLL carries `xxhash.c`, as under MinGW — no xxHash family here.
* **Value: high.** lz4 in modern loaders and packers, and those are MSVC-built.

### mbedTLS — 4 versions, 8 builds, **24 artefacts**
* Now: CMake, three DLLs per build (`libmbedcrypto`, `libmbedx509`, `libmbedtls`).
* **Verdict: Easy to configure, expensive to mirror.**
* **Watch:** `USE_SHARED_MBEDTLS_LIBRARY=ON` under MSVC — I did **not** verify that
  mbedTLS's CMake produces usable DLLs with MSVC without
  `CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS`. Check before committing to the family.
  Also `MBEDTLS_FATAL_WARNINGS=OFF` is currently set because of a GCC
  `-Werror=format=` problem; under MSVC the failing warning will be a different one or
  none, so the flag string must be re-derived rather than copied.
* **Dependencies:** none.
* **Value: high per artefact, but the family is 24 artefacts and would become 48.**
  Mirror **one or two** versions (3.6.x LTS and 2.28.x LTS), not all four.

### MemoryModule — 2 versions, 4 builds
* Now: upstream GNU makefiles, `make example PLATFORM=…`, artefact
  `example/DllLoader/DllLoader.exe`.
* Upstream MSVC: at **`v0_0_4` the tree has no `CMakeLists.txt`** — only
  `example/DllMemory.sln` and two **`.vcproj`** files (VS2008 format, which MSBuild
  v143 cannot consume without a `devenv /upgrade`) [listed, full 19-file tree].
  At the master commit `5f83e41c…` a **`CMakeLists.txt` does exist** [listed, HTTP 200].
* **Verdict: Easy for the 2019 commit, Moderate for 0.0.4** (two translation units
  compiled by hand — `MemoryModule.c` plus `example/DllLoader/DllLoader.cpp` — which
  is no more bespoke than the sqlite3 recipe).
* **Dependencies:** none. Note upstream's makefiles compile `MemoryModule.c` with
  `g++`; under MSVC compile it as C++ too, or the static helpers' names change shape.
* **Value: high for triage.** MemoryModule is copy-pasted into loaders verbatim, and
  the copies are compiled by the host project — which is MSVC far more often than GCC.
  The MSVC artefact is arguably the one that should have existed first.

### nlohmann_json — 3 versions, 6 builds
* Now: header-only, so the recipe compiles
  `scripts/corpus/exercisers/nlohmann_json.cpp` into a DLL.
* **Verdict: Easy.** `cl /nologo /O2 /MD /Zi /std:c++17 /EHsc /Iinclude
  /Fdnlohmann.pdb exerciser.cpp /LD /Fe:nlohmann_json.dll /link /DEBUG /Brepro
  /OPT:NOICF /PDB:nlohmann.pdb`.
* **Dependencies:** none, **but** this is the family most exposed to §6: a header-only
  C++ library compiled by MSVC is *mostly* MSVC STL instantiations by function count,
  and the current MSVC C++ probe covers a narrow slice of the STL.
* **Value: medium.** Real — MSVC template output differs completely from GCC's, so the
  MinGW artefact matches an MSVC sighting barely at all — but the artefact is only as
  good as the exerciser, and the STL-attribution problem is worst here.

### OpenSSL — 3 versions, 6 builds, **12 artefacts**
* Now: `./Configure mingw|mingw64 --cross-compile-prefix=…`, perlasm, no nasm needed.
* Upstream MSVC: `perl Configure VC-WIN32` / `VC-WIN64A` then `nmake`, documented in
  `NOTES-WINDOWS.md` [read, tag `openssl-3.5.8`]. That document states plainly:
  **"NASM is the only supported assembler."**
* **Runner gap [read, `actions/runner-images` `images/windows/toolsets/toolset-2022.json`]:**
  windows-2022 ships Strawberry Perl 5.32.1.1, CMake 3.31.6, Ninja, 7-Zip and a
  mingw 14 (ucrt) — **it does not ship NASM.** So an OpenSSL MSVC recipe needs either
  an install step (`choco install nasm` / `ilammy/setup-nasm`) or `no-asm`. `no-asm`
  is the wrong answer: it removes the hand-written AES/SHA/bignum cores, which are a
  large and highly recognisable share of `libcrypto` and are present in every real
  OpenSSL binary.
* **Verdict: Moderate** — not hard, but the only family that needs a new tool on the
  runner.
* Command:
  ```
  perl Configure VC-WIN64A shared no-tests --debug-  ^
       /Zi                      :: or via CFLAGS
  nmake
  ```
  Exact flag plumbing for `/Zi`/`/Brepro` under OpenSSL's Configure I did **not**
  verify; OpenSSL's VC targets already produce `.pdb` files in a normal release build
  [inferred], which if true removes most of that work. Confirm before scheduling.
* **Dependencies:** none, but `libcrypto` is the largest sample in the corpus and
  `export_reports` peaked at **9.4 GB resident** for the MinGW build [read,
  `scripts/corpus/README.md`]. A standard GitHub Windows runner has 16 GB [inferred
  from GitHub's published runner specs; not verified here]. This is the one family
  with a real risk of being OOM-killed in CI.
* **Value: the highest in the corpus, and the recipe's own docstring says so**:
  "OpenSSL in the wild is overwhelmingly MSVC-built, so a MinGW reference matches
  those only weakly." Also the most expensive. That tension is the central scheduling
  decision of the whole project.

### pcre — 1 version, 2 builds
* Now: CMake (`pcre-8.45` tarball, which does ship `CMakeLists.txt` and
  `NON-AUTOTOOLS-BUILD` / `NON-UNIX-USE` notes) [listed, local tarball].
* **Verdict: Easy.** Same options, `-DPCRE_SUPPORT_JIT=ON -DPCRE_SUPPORT_UTF=ON
  -DPCRE_BUILD_PCRECPP=OFF`.
* **Watch:** sljit's JIT under MSVC — I did not verify that PCRE1's JIT compiles with
  v143. It is old code.
* **Value: medium.** Legacy Windows software carrying PCRE1 is MSVC-built.

### pcre2 — 2 versions, 4 builds
* Now: CMake. **Verdict: Easy.**
* **Dependencies:** none.
* **Value: high.** PCRE2 is everywhere in current software and the Windows copies are
  MSVC.

### protobuf — 3 versions, 6 builds
* Now: CMake; 3.6.1 and 21.12 static + `--whole-archive`; 31.1 shared with Abseil as
  separate DLLs so Abseil's objects stay out of the protobuf artefact.
* **Verdict: Moderate.** `protobuf_BUILD_SHARED_LIBS=ON` with `PROTOBUF_USE_DLLS` is
  upstream's own supported MSVC arrangement [inferred from the recipe's own notes and
  the defines it records], and it is the right one here for the same reason it is
  under MinGW: it keeps Abseil out.
* **Risk:** **3.6.1 with v143 may not compile.** It is 2018 C++11 code and MSVC's
  conformance has moved a long way; the MinGW build needed no patch but MSVC is a
  different front end. Budget a failure here and be prepared to cover 21.12 and 31.1
  only. (Not verified — I did not attempt a build.)
* **Dependencies:** Abseil (31.1) must be built as DLLs and only imported. Under MSVC
  that requires `CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS` on the Abseil side, the same
  mechanism the re2 recipe uses. `protobuf_WITH_ZLIB=OFF` stays, or zlib lands inside
  a protobuf artefact.
* **Value: very high.** Protobuf inside Windows software is overwhelmingly MSVC-built
  and statically linked, which is exactly the sighting this corpus is meant to answer.

### q3vm — 2 versions, 4 builds
* Now: upstream `make q3vm TOOLCHAIN=…`.
* Upstream MSVC: `msvc/q3vm/q3vm.sln` + `msvc/q3vm/q3vm/q3vm.vcxproj` [listed, cloned
  at `v1.3.1`].
* **Verdict: Easy/Moderate** (one MSBuild invocation with `/p:PlatformToolset=v143`).
* **This is not a duplicate build.** The existing recipe's own note records that
  "GCC builds use computed-goto dispatch; the in-tree MSVC solution produces
  switch-based dispatch, which is not covered here" [read]. The interpreter dispatch
  loop *is* q3vm's recognisable code, and the two compilers produce structurally
  different versions of it. So the MSVC build adds genuinely new code, not a second
  rendering of the same code.
* **Value: low in absolute terms** (QVM sandboxes are a narrow sighting) **but the
  marginal value is unusually high relative to the family's size**, because half the
  family's distinctive code is currently absent from the corpus in any form.

### re2 — 2 versions, 4 builds
* Now: 2022-06-01 compiled directly from `re2/*.cc`; 2025-11-05 through CMake against
  a locally installed Abseil.
* **Verdict: Moderate.** 2022-06-01 becomes a `cl` line over the same source list;
  2025-11-05 needs the Abseil-as-DLLs arrangement under MSVC.
* **Note:** the MinGW recipe's long explanation of why `--unresolved-symbols` is
  unavailable is a GNU-ld problem and does not apply to `link.exe`; but the fix that
  was adopted (build Abseil shared, import from it) transfers unchanged and is the
  right one here too.
* **Value: medium-high**, mostly as the MSVC half of the Abseil/protobuf/re2 cluster.

### sqlite3 — 3 versions, 6 builds
* Now: one `gcc -shared` line over the amalgamation.
* Upstream: **there is no build system** — the amalgamation zip is `sqlite3.c`,
  `shell.c`, `sqlite3.h`, `sqlite3ext.h` and nothing else [read, local
  `sqlite-amalgamation-3500400.zip`]. That is the point of it.
* **Verdict: Easy** — the MSVC analogue is one `cl` line:
  ```
  cl /nologo /O2 /MD /Zi /Fdsqlite3.pdb ^
     /DSQLITE_API=__declspec(dllexport) ^
     /DSQLITE_ENABLE_FTS5 /DSQLITE_ENABLE_RTREE /DSQLITE_ENABLE_JSON1 ^
     sqlite3.c /LD /Fe:sqlite3.dll ^
     /link /DEBUG /Brepro /OPT:NOICF /PDB:sqlite3.pdb
  ```
  (3.8.11.1 swaps FTS5/JSON1 for FTS4, as the MinGW recipe does.)
* **Dependencies:** none.
* **Value: very high, at the lowest cost of anything on this list.** SQLite is the
  most embedded database on Windows; `scripts/corpus/README.md` already notes that
  sqlite.org's own DLLs are MinGW-built, which means an MSVC reference covers the
  *embedded-into-an-application* case that the prebuilt route cannot. One translation
  unit, ~2 minutes per build.

### wolfSSL — 1 version, 2 builds
* Now: CMake.
* Upstream MSVC: root `wolfssl64.sln`, `wolfssl.vcxproj`, `wolfssl-VS2022.vcxproj`
  [listed, `v5.9.2-stable`]. Read from `wolfssl.vcxproj`: `ConfigurationType`
  `DynamicLibrary` *and* `StaticLibrary` configs, `RuntimeLibrary
  MultiThreadedDLL` (already `/MD`), `DebugInformationFormat ProgramDatabase`
  (already `/Zi`), `PlatformToolset v110` (override to v143) [read].
* **Verdict: Easy** either way.
* **Value: low.** The recipe's own note says wolfSSL is "genuinely uncommon in Windows
  malware compared with OpenSSL and mbedTLS". Add it last, or not at all.

### Already MSVC — no work
`VX-API`, `BlackBone`, `SysWhispers` are MSVC recipes. `donut`, `sRDI` and
`pe_to_shellcode` are blob extractions of bytes upstream compiled with MSVC and ships
verbatim; `Recipe.slug` already labels them `msvc` rather than after the extraction
host [read, `recipe.py`]. Nothing to do; a "MinGW→MSVC" pass must skip them, and the
importer must not treat their `toolchain: null` records as a defect.

---

## 3. Counts by verdict

| verdict | families | builds (version × arch) | artefacts if fully mirrored |
| --- | --- | --- | --- |
| **Easy** | 14 — libzlib, sqlite3, bzip2, cJSON, liblzma, lz4, libuv, libevent, libtiff, libxml2, pcre, pcre2, libcurl, libpng | 56 | 58 |
| **Easy, but heavy** | 2 — mbedTLS, wolfSSL | 10 | 26 |
| **Easy/Moderate** | 3 — nlohmann_json, q3vm, MemoryModule | 14 | 14 |
| **Moderate** | 11 — OpenSSL, 7-Zip, cryptopp, libtomcrypt, libsodium, jemalloc, abseil, protobuf, re2, LuaJIT, Lua | 50 | 56 |
| **Hard** | **0** | — | — |
| **Pointless** | 1 — libstdc++ | 1 | 1 |
| **totals** | **31** | **131** (130 excluding libstdc++) | **155** |

**Nothing in this corpus is Hard for MSVC.** That is the most useful single finding of
the survey and it is worth stating plainly: every one of these projects targets Windows
and therefore supports MSVC upstream, in-tree, at the pinned ref. The two families whose
current recipe uses autotools (libsodium, jemalloc) both ship Visual Studio solutions;
the two that use handwritten GNU makefiles (lz4, bzip2) both ship an MSVC makefile or
CMake; the one with no MSVC path at all for two of its three versions (Lua 5.3/5.4) is
30 C files and a two-line `cl` invocation that upstream itself demonstrates for 5.1.

The work is **not** in getting a compile. It is in (a) turning MSVC's static-`.lib`
default into a DLL SMDA can read without absorbing another family, (b) forcing a PDB
where upstream does not, and (c) the glue filter (§6) and the import (§7).

---

## 4. Ranked implementation order

Ranked by coverage gain per unit of work, with the enabler ordering respected.

| # | family | versions to do | why now |
| --- | --- | --- | --- |
| 1 | **sqlite3** | all 3 | Highest real-world frequency of anything here, one `cl` line, no deps, ~2 min a build. If only one family were ever added, this. |
| 2 | **libzlib** | 1.2.13 + 1.3.1 (skip 1.2.8/1.2.11, already MSVC-covered) | Upstream's `Makefile.msc` already does `/MD /Zi /debug`; one nmake line; and it produces the `zdll.lib` that libpng needs. Minutes. |
| 3 | **libcurl** | 8.15.0 first, 8.4.0 if cheap | The archetypal MSVC-built statically linked dependency in droppers; the CMake line transfers almost verbatim; Schannel keeps it dependency-free. |
| 4 | **liblzma** | both | Droppers and installers; trivial CMake; watch the `-O3→-O2` replace not firing under MSVC. |
| 5 | **lz4** | both | Same reasoning; `build/cmake` is already in-tree. |
| 6 | **libsodium** | 1.0.20 (vs2022 sln), then 1.0.18 | A hit is decisive in ransomware triage and ransomware is MSVC-built; upstream ships the solution. |
| 7 | **pcre2** | 10.45 first | Ubiquitous in current software; trivial CMake. |
| 8 | **libtomcrypt** | 1.18.2 | The only family where the MSVC build is **better data than the MinGW one it joins** — the MinGW artefact is stripped, unnamed and still full of MinGW glue. Costs a wrapper link and an MSVC LibTomMath. |
| 9 | **protobuf** | 21.12 and 31.1 (treat 3.6.1 as optional) | Very high real-world frequency; the Abseil-isolation arrangement is already worked out under MinGW and transfers. Budget for 3.6.1 failing on v143. |
| 10 | **7-Zip** | 26.03 first | The MSVC build assembles the MASM fast paths the MinGW build must omit, so it is not a re-run — it is code the corpus does not have at all. |

Then, in descending order and clearly below the line: **libxml2**, **MemoryModule**,
**cryptopp**, **libuv**, **cJSON**, **libtiff**, **libpng** (after libzlib),
**libevent**, **pcre**, **abseil**, **re2**, **LuaJIT**, **Lua**, **mbedTLS**
(one or two versions only), **q3vm**, **jemalloc**, **wolfSSL**.

**OpenSSL is deliberately not in the top ten**, and that needs saying out loud because
it is the highest-value family in the corpus. It is excluded from the first wave for
three reasons, all verified: it is the only family needing a tool the runner does not
have (NASM), it is the only family with a measured OOM risk (9.4 GB export peak
against a 16 GB runner), and at three versions × two architectures × two artefacts it
is 12 of the 155 artefacts on its own. Do it **as its own workflow job**, after the
cheap wave has proved the recipe pattern and the importer, and consider covering
3.5.8 and 1.1.1w only.

**Drop entirely from any MSVC pass:** `libstdc++` (category error), and the three
already-MSVC recipes plus the three blob recipes.

---

## 5. CI cost

### What is actually measured

* The existing job is ~7 minutes for three recipes (5 artefacts), per architecture,
  as two parallel matrix legs [given in the brief; not independently verified].
* Fixed per-job overhead is checkout + `setup-python` + `pip install -r
  scripts/requirements.txt` (SMDA, MCRIT and their dependencies) + `msvc-dev-cmd` +
  `list`. I estimate **~3 minutes** of that 7, leaving ~4 minutes of real work for
  VX-API (766 functions x64 after filtering), BlackBone (1759) and SysWhispers (29).
* Per-family build durations on the **Linux** side, from the mtime deltas between
  consecutive build logs in `scratchpad/work/` (whole pipeline: fetch + build + SMDA +
  export + package), on a many-core machine that was running other work:
  * tiny (zlib, q3vm, cJSON, lz4, bzip2): **10–30 s**
  * medium (liblzma, libuv, pcre2, mbedTLS per version, libsodium, LuaJIT, Lua,
    libxml2, libtiff): **30–120 s**
  * large (libcurl ~130 s, abseil ~120 s, 7-Zip ~240–400 s, cryptopp ~260–390 s,
    protobuf 31.1 ~340–440 s, re2 2025 ~400 s)
  * **OpenSSL 3.x: 420–460 s per architecture**

### The extrapolation

A windows-2022 runner has 4 vCPU against the Linux host's much larger core count, NTFS
is slower for the many-small-files compile pattern, and MSBuild/nmake parallelism is
worse than `make -j$(nproc)`. I apply a **2×** factor. Both halves of that are
estimates, not measurements.

| scope | builds | estimated runner-minutes |
| --- | --- | --- |
| Top-ten families, one or two versions each (~24 builds, ~30 artefacts) | 24 | **150–230 min** total, i.e. 75–115 min per architecture |
| Top-ten families, **all** their versions (~40 builds) | 40 | **240–360 min** |
| **Full mirror of all 130 MinGW builds** | 130 | **650–950 min (11–16 h)** |
| OpenSSL alone, 3 versions × 2 arch | 6 | **90–150 min**, plus a NASM install step |

### The hard constraint this exposes

A full pass split only by architecture is **5.5–8 hours per job**, which exceeds
**GitHub Actions' 6-hour per-job limit** [inferred from GitHub's published limits; not
verified here]. So `all-msvc` cannot stay a single job. The workflow must gain a
**family (or family-group) dimension in the matrix**, alongside `arch`. That also
fixes a second problem: today a single failing recipe in the middle of a long list
loses the whole job's output, because the upload step is `if: success()`.

Recommended shape: `strategy.matrix: {arch: [x86, x64], group: [small, crypto, cpp,
openssl]}` — eight jobs, none longer than about 45 minutes, each uploading its own
artifact.

---

## 6. The glue baseline — yes, the probe needs extending, and here is the measurement

`baseline.py` builds five probes for MSVC: the C DLL probe, the C++ DLL probe, the C
EXE probe, the C++ EXE probe and `_PROBE_ATL`. The `-static-libstdc++` style extras are
stripped for MSVC (`… and toolchain.kind != "msvc"`), and `probe_command` emits
`cl /nologo /O2 /Zi /Fd:… /LD … /link /DEBUG /PDB:…` [read].

**Finding 1 — the probe is `/MT` while every recipe is `/MD`, and it does not matter
for startup glue.** `cl` defaults to `/MT` and `/LD` implies `/MT`, so the probe links
the static CRT while VX-API and BlackBone are `/MD`. I expected that to break PicHash
matching on the startup stubs. It does not: `_DllMainCRTStartup`, `__security_init_cookie`,
the whole `__scrt_*` set, `__chkstk`, `__GSHandlerCheck*`, `_RTC_Initialize`,
`__isa_available_init` and the `dllmain_*` family are all in
`removed_runtime_functions` for both VX-API architectures and BlackBone x64
[measured]. The startup objects are evidently identical between the two CRT flavours.
Worth recording so nobody "fixes" the probe to `/MD` and changes the baseline for no
reason.

**Finding 2 — the filter is measurably incomplete, and the residue is Microsoft's
code wearing a family's name.** Counting functions whose recovered name matches
`ATL::`, `std::`, `__scrt`, `__std_`, `__security_check_cookie`, `_RTC`, `memcpy`,
`memset`, `__acrt`, `__isa_`, `_guard`, `chkstk`, `__GS` in the **committed, already
filtered** artefacts [measured, from the `.7z` reports in `data/`]:

| artefact | functions | residual Microsoft runtime | share |
| --- | --- | --- | --- |
| VX-API x64 | 766 | **45** (26 ATL, 2 std, 9 `__scrt_*`/`__std_*`, `__security_check_cookie`, `memcpy`, `memset`, `__acrt_iob_func`) | 5.9% |
| VX-API x86 | 755 | **49** (28 ATL, 6 std, …) | 6.5% |
| BlackBone x64 | 1759 | **29** (16 std, 3 ATL, …) | 1.6% |
| BlackBone x86 | 1953 | **28** (17 std, 3 ATL, …) | 1.4% |

The specific survivors fall into four buckets, and each suggests a concrete probe
extension:

1. **ATL beyond the module object.** `_PROBE_ATL` instantiates `CComCriticalSection`
   and `CSimpleArray<int>`, which removed 68 ATL functions from VX-API x64 — but 26
   remain: `CComBSTR`, `CComVariant`, `CAtlException`, `AtlWinModuleInit` and the
   `dynamic initializer for '_AtlComModule'`. Adding `CComBSTR`, `CComVariant`,
   `CComPtr`, `CRegKey` and `ATL::CAtlException` to the probe would take most of them.
2. **MSVC STL instantiations.** BlackBone x64's residue is 16 `std::` entries:
   `std::vector<unsigned char>::_Tidy` / `_Assign_counted_range` / `_Xlength`,
   `std::_Tree_val<…<int>>::_Insert_node` / `_Erase_tree`,
   `std::_Allocate<16,std::_Default_allocate_traits>`, `std::_Xlen_string`,
   `std::_Throw_tree_length_error`, `std::_Hash_vec<…>` destructors,
   `std::operator+<wchar_t,…>`. This is the exact MSVC analogue of the libstdc++
   template-instantiation class that makes up 26 of the corpus's 58 surviving
   cross-family PicHashes — and it is the bucket that **will grow fastest** when
   cryptopp, protobuf, abseil, re2 and nlohmann_json arrive as MSVC C++ artefacts.
   The C++ probe should be widened: `std::vector<unsigned char>`, `std::set<int>`,
   `std::list`, `std::unordered_map`, `std::wstring` and `std::deque` at minimum.
3. **Termination and RTTI stubs.** `__std_terminate`, `__std_exception_copy`,
   `__std_exception_destroy`, `__std_type_info_destroy_list`,
   `__scrt_uninitialize_type_info`, `__scrt_stub_for_acrt_initialize`,
   `__scrt_stub_for_is_c_termination_complete`, `__scrt_dllmain_exception_filter`,
   `__scrt_dllmain_uninitialize_critical`, `std::bad_alloc::bad_alloc`. A probe that
   throws and catches across a DLL boundary and registers an `atexit` handler would
   pull these in.
4. **`memcpy`, `memset` and `__security_check_cookie` in every single artefact.**
   These appear in all four MSVC artefacts and in none of the removed lists. The probe
   calls `memcpy`, `memset` and is compiled with `/GS` on by default, so they *should*
   be in the baseline. **I could not determine why they are not** — candidate
   explanations are that the probe's `-O2` turns them into intrinsics so no body is
   linked, or that the `/MT` and `/MD` bodies genuinely differ for these three (unlike
   the startup stubs). Measuring this is a small, well-defined experiment and it should
   be done **before** the wave, because three functions × 30 families × 2 architectures
   is ~180 mis-attributed functions and `memcpy` is exactly the kind of body that
   generates cross-family PicHash hits.

**So: yes, extend the probe, and do it before the second family lands, not after.**
Under MinGW this class of defect cost two `refilter` rounds and 425 functions; the
MSVC side is starting from a narrower probe and is about to get thirty new customers.

---

## 7. What the importer will have to handle

The importer is someone else's work, but these are the requirements the highly-ranked
families impose. All are consequences of code I read.

1. **Merge, never replace, `provenance.json`.** The scoping step in
   `windows-reference-data.yml` prunes `provenance.json` to only the records this run
   produced and writes the same pruned dict to `provenance.<arch>.json` [read]. For
   VX-API/BlackBone/SysWhispers that is harmless because those families are MSVC-only.
   For **every family in this survey it is not**: the uploaded
   `provenance.x64.json` will contain *only* the MSVC records, and blindly copying it
   over `data/libcurl/provenance.json` would delete four MinGW records. The importer
   must load the committed file and update it key-by-key.
2. **Two architecture legs, one family.** Each family's records arrive split across
   `reference-data-x86` and `reference-data-x64`; both must be merged, and the
   per-arch files are named `provenance.x86.json` / `provenance.x64.json` precisely so
   one leg cannot clobber the other [read]. Do not import `provenance.json` from the
   archive — the upload already excludes it via `!data/*/provenance.json`.
3. **The workflow's family list is hardcoded.** `"VX-API", "BlackBone",
   "SysWhispers"` appears three times in the workflow (scoping, validate, upload
   paths) and `all-msvc` expands to a literal recipe list [read]. Adding families
   means editing all four places, or — better — deriving them from the registry by
   filtering `recipes.all_recipes()` for entries whose `toolchains` contain `msvc_`.
   The importer should not assume a fixed family set.
4. **Multi-artefact recipes.** mbedTLS produces three DLLs per build (six files per
   version per arch); libevent two; OpenSSL two. The importer must key on the slug,
   not on "one artefact per family per arch".
5. **The 100 MB guard.** `config.MAX_COMMITTED_FILE_SIZE` is enforced by
   `package.commit_artifacts` before a file reaches `data/` [read]. An OpenSSL
   `libcrypto` MSVC `.mcrit` is the realistic candidate to trip it. That failure
   happens on the runner, not in the importer — but the importer must not silently
   import a family that is missing one of its declared artefacts.
6. **`readme --update` afterwards.** The README tables are generated from provenance
   [read, `scripts/corpus/README.md`], and 30 new families' worth of MSVC rows will
   not appear until it is run. The `toolchain` column will read `msvc143`.
7. **Idempotency.** A re-import of the same run must overwrite the same slugs and
   leave the MinGW siblings untouched. Since only `timestamp`/`execution_time` differ
   between runs of identical source [read], a re-import will show as a binary diff of
   every `.7z` even when nothing changed — the importer should say so rather than
   look like it regenerated data.
8. **Blob families are not candidates.** `donut`, `sRDI` and `pe_to_shellcode` records
   carry `"toolchain": null` and `"compiler": "MSVC (upstream, exact version
   unknown)"` by design [read, `pipeline.py`]. An importer that infers "needs an MSVC
   build" from a null toolchain would queue six families that are already MSVC.

---

## 8. Risks, in order

1. **The incomplete MSVC glue filter (§6).** Measured at 1.4–6.5% of functions in the
   four artefacts that exist today, concentrated in ATL and MSVC STL instantiations —
   the two buckets that grow with exactly the families this project would add. Left
   alone it reproduces, at larger scale, the misattribution the MinGW side spent two
   `refilter` rounds fixing, and it will manufacture new cross-family PicHash
   collisions between every MSVC C++ family. **Fix the probe first.** This is the
   single biggest risk.
2. **Dependency absorption under MSVC's static-by-default builds.** libpng's own
   `projects/vstudio/` solution compiles zlib into the same image [listed] — using it
   would recreate, function for function, the `libpng16.dll`/`data/libzlib` overlap
   that is the corpus's canonical cautionary tale. The same shape lurks in cryptopp
   (`cryptlib.lib` → wrapper), libtomcrypt (+LibTomMath), abseil/protobuf/re2, and in
   any CMake configure that finds a vcpkg zlib on the runner. Every recipe needs its
   dependency story stated explicitly, as the MinGW ones do.
3. **Job-length and memory ceilings.** A full pass is 11–16 hours and cannot run as one
   job per architecture; OpenSSL's export peaked at 9.4 GB on a 15 GB machine and the
   runner has 16 GB.
4. **NASM is not on windows-2022** [read, toolset manifest], so OpenSSL needs a new
   install step, and `no-asm` is not an acceptable substitute.
5. **Old versions against a new toolset.** protobuf 3.6.1, cryptopp 5.6.5, pcre 8.45's
   JIT, mbedTLS 2.16.12, libtiff 4.0.10 and 7-Zip 23.01 are all old enough that v143
   may reject them. The corpus's own rule — no patching upstream — means a failure
   there is a "cover the newer version only" decision, not a fixable one. Budget for
   losing two or three of them.
6. **Every family added multiplies the import cost**, and there is no importer yet.
   That argues for the shape of the ranking above: prove the pattern on
   sqlite3 + libzlib + libcurl (three families, eight builds, under 30 minutes of CI),
   make the importer work on those, and only then open the tap.
