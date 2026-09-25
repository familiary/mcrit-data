# Adding a Windows kernel-mode driver family

Written after `apicallproxy.py`, `blackbonedrv.py` and `hidden.py`, so that the
fourth driver does not rediscover what those three cost. Everything here is
about `.sys` targets and the projects that ship alongside them; for an ordinary
user-mode MSVC family, `README.md` in this directory is still the document you
want.

Read this next to an existing recipe rather than instead of one:

- `recipes/apicallproxy.py` came first and paid for most of the lessons below -
  `/p:DriverType=WDM`, and InfVerif rejecting a package before anything compiled.
- `recipes/blackbonedrv.py` is the simple case - one project, one architecture,
  one msbuild line over a single-project `.sln`.
- `recipes/hidden.py` is the awkward one - a kernel project and user-mode
  projects in the same solution, needing opposite toolset treatment, so it
  builds `.vcxproj` files individually.

## The short version

1. The `windows-2022` runner already has a WDK. There is no install step and
   you do not need to add one.
2. Write `recipes/<name>.py`. Dropping the file in is the whole registration -
   there is no list to edit anywhere.
3. Add a `### <Family>` section to the top-level `README.md` with an **empty**
   generated fence, and a TOC entry. Ship that in the same commit as the recipe.
4. Push. CI builds it. This container has no MSVC and no WDK, so CI is always
   the recipe's first execution.
5. Import the artefacts in a second commit, then regenerate the fence with
   `build_corpus.py readme <Family>`.

### Iterate with `workflow_dispatch`, not with pushes

A push rebuilds the entire corpus and takes about fifty minutes. A new driver
recipe will not be right first time, so do not spend that on every attempt.
The workflow already takes a `recipes` input - space separated recipe keys, or
`all-msvc` - so a single recipe can be built on its own in a few minutes:

```
gh workflow run windows-reference-data.yml \
   --ref <branch> -f recipes=<Family>_<version>
```

or the equivalent `actions_run_trigger` / `run_workflow` MCP call with
`inputs: {"recipes": "<Family>_<version>"}`. The scoping step then uploads only
that family's data, which is exactly what the import wants. Use the full push
run to confirm nothing else regressed, and dispatch runs to iterate.

This does not remove the need to be right before you push: a dispatch run still
costs minutes, and the checks under "Open risks are part of the recipe" below
are cheaper than any of them.

## What the runner actually has

`.github/workflows/windows-reference-data.yml` contains no WDK setup. It runs
`ilammy/msvc-dev-cmd@v1`, which puts `cl`, `link`, `ml`/`ml64`, `rc` and
`msbuild` on PATH for one target architecture, and it takes the WDK as
preinstalled on the image.

There is a probe step, `continue-on-error`, that reports what it finds and never
fails the job. On the BlackBoneDrv round it reported:

- `WindowsKernelModeDriver10.0` platform toolset: PRESENT
- KMDF import libraries: 1.15 through 1.21
- `ntoskrnl.lib`, `hal.lib`, `wmilib.lib`, `netio.lib` under `Lib\10.0.26100.0\km\x64`

So the WDK on that image was **10.0.26100**. The probe does not cover every
import library - `fltmgr.lib`, which any minifilter needs, is not on its list.
If your driver links something unusual, add a line to the probe rather than
finding out from a link error.

**The WDK version is almost never pinned by the project.** Neither BlackBoneDrv
nor Hidden declares `WindowsTargetPlatformVersion` on its kernel projects, so
the build takes whatever the image carries. That means the build is not
reproducible across runner images from the recipe alone. Read the resolved
version out of the build log and put it in `notes`.

### x86 kernel drivers cannot be built. Declare `msvc_x64` and move on

This is the single rule most likely to save you a red round. WDK 10.0.26100 -
the kit on `windows-2022` - **does not support Win32 kernel-mode targets at
all**. A driver recipe declaring `msvc_x86` fails during msbuild target
evaluation, before any compiler runs:

```
C:\Program Files (x86)\Windows Kits\10\build\10.0.26100.0\WindowsDriver.common.targets(271,5):
  error :  'Win32' is not a valid architecture for Kernel mode drivers or UMDF drivers
```

The kit's import libraries confirm it: `Lib\10.0.26100.0\km\` contains `arm64`
and `x64` and **no `x86` directory whatsoever**. So this is not something a
property, a retarget or a source fix can work around.

It holds regardless of what the project offers. Hidden's five projects all
declare `Release|Win32` and no source refuses x86, and it still cannot build -
`hidden.py` declares both legs in round 1 and paid a red CI job for it. So:

> For the driver artefact, declare `toolchains=["msvc_x64"]`. Do not infer the
> architecture from the `.vcxproj`.

BlackBoneDrv reaching the same place from the project's side (all eight of its
configurations are x64, and its header `#error`s on `_M_IX86`) hid this for a
while - it looked like a property of that project rather than of the kit.

**Do not trust the probe on this point.** It reports the
`WindowsKernelModeDriver10.0` toolset PRESENT and lists a `Platforms\Win32`
directory for it, because that directory genuinely exists. The targets file and
the import libraries still refuse x86. PRESENT means installed, not buildable.

**Watch the blast radius when you narrow.** `toolchains` is declared per
*recipe*, not per artefact, so narrowing a recipe that also builds user-mode
binaries drops their x86 builds too, and those would usually have compiled
fine. If the user-mode half is worth an x86 build, give it its own family on the
BlackBone/BlackBoneDrv pattern rather than dragging it down to the driver's
architecture - remembering that two recipes must not share a
`(family, version)` key. Do that once the user-mode half is known to build; a
speculative split just risks two red recipes instead of one.

## Writing the recipe

### Do not retarget the kernel toolset

A driver project names `WindowsKernelModeDriver10.0`. That is the WDK's own
toolset, not a Visual C++ version, so the `v142 -> v143` retarget that
`blackbone.py` and `heavensgate2.py` need has no counterpart - there is no
older-toolset string to replace. Passing `/p:PlatformToolset=v143` to a driver
project is wrong and will not do what you want.

User-mode projects in the same repository are a different matter: `v142` is
VS2019 and `windows-2022` does not carry it, so those **do** need the retarget.
When one solution contains both, you cannot express that in a single msbuild
invocation - see "Two projects, opposite properties".

### Properties every driver build should pass

```
/p:Configuration=<config> /p:Platform={msbuild_platform}
/p:TargetVersion=Windows10
/p:SignMode=Off
/p:SkipPackageVerification=true
/p:WholeProgramOptimization=false
/p:OutDir=%CD%\out\ /p:IntDir=%CD%\obj\
/p:ForceImportBeforeCppTargets=%CD%\corpus-msvc.props
/m /v:minimal
```

- `TargetVersion=Windows10` because driver configurations often leave the
  element empty.
- `SignMode=Off` and `SkipPackageVerification=true` because InfVerif can reject
  a package **before a single file compiles**. That is exactly how APICallProxy
  failed its first round. They never reach the compiler or the linker.
- `OutDir` pinned because upstream driver projects commonly commit a prebuilt
  `.sys` into the default output directory, and because the default often
  differs between `Win32` and `x64` (`$(SolutionDir)$(Config)\` versus
  `$(SolutionDir)$(Platform)\$(Config)\`), which would need two artefact paths.
- `{msbuild_platform}` is substituted to `x64` or `Win32` by `toolchain.py`.
- `%CD%` is literal for `cmd.exe`. Only write `%%CD%%` if the surrounding Python
  string is `%`-formatted, as `blackbonedrv.py`'s is.

### The forced props file

Never edit an upstream project file. Write a props file as a build step and
force-import it:

```python
_PROPS = ('python -c "'
          "open('corpus-msvc.props','w').write('<Project>...</Project>')"
          '"')
```

It must set, at minimum:

| Setting | Why |
|---|---|
| `DebugInformationFormat` = `ProgramDatabase` | no PDB, no names |
| `ProgramDataBaseFileName` (compiler PDB, under `$(IntDir)`) | must not collide with the linker's |
| `ProgramDatabaseFile` = `$(OutDir)$(TargetName).pdb` (linker PDB) | this is the one `Artifact(pdb=...)` names |
| `GenerateDebugInformation` = `true` | full `/DEBUG` |
| `OptimizeReferences` / `EnableCOMDATFolding` = `false` | `/OPT:NOREF /OPT:NOICF`; ICF folds identical functions and loses coverage |
| `WholeProgramOptimization` = `false` and `LinkTimeCodeGeneration` = `Default` | LTCG rewrites the code you are trying to fingerprint |
| `TreatWarningAsError` = `false` | driver sources under `/WX` routinely fail on deprecated pool APIs |
| `/Brepro /INCREMENTAL:NO` in `AdditionalOptions` | see below |

**`/INCREMENTAL:NO` is not optional.** `/DEBUG` implies `/INCREMENTAL`, and
`/OPT:NOREF`/`/OPT:NOICF` do **not** suppress it. An incremental link fills the
image with jump-table thunks, and `assert_not_incrementally_linked`
(`smdaify.py`, threshold `MAX_INCREMENTAL_THUNK_RUN = 32`) will fail the build.
That check applies to drivers exactly as it does to DLLs; it is skipped only for
blobs.

**If one props file serves two projects**, name the compiler PDB
`$(IntDir)$(ProjectName).compiler.pdb` rather than a fixed stem, and give each
msbuild step its own `IntDir`. `hidden.py` does this; `blackbonedrv.py` could
afford a fixed name because it builds one project.

### Two projects, opposite properties

When a solution holds a driver and user-mode consumers, build the `.vcxproj`
files separately rather than the `.sln`:

- only the user-mode step passes `/p:PlatformToolset=v143`
- building the solution would also build any packaging project

A packaging project (`ConfigurationType=Utility`, `DriverType=Package`) runs
`Inf2Cat` to emit a `.cat` catalogue. **It produces no code.** Upstream READMEs
often tell you to build it - that advice is for people installing the driver,
not fingerprinting it. Skip it, and say in `notes` that you did.

### Check for a ProjectReference before assuming msbuild builds dependencies

Static-library projects are not collected: `.lib` is an archive, not a PE, and
the pipeline wants PEs. Build an executable that links the library instead, and
record in `notes` that a match on that executable may be a match on the library.

But "not collected" is not "not built", and conflating the two cost `hidden.py`
a red round. Building `App.vcxproj` builds its dependency **only if the project
declares a `ProjectReference`**. Many solutions do not: they name the import
library as a bare linker input and rely on the solution's build order to have
produced it. Build such a `.vcxproj` on its own and you get:

```
LINK : fatal error LNK1181: cannot open input file 'HiddenLib.lib'
```

after every translation unit has compiled perfectly. Note it is **LNK1181**
("cannot open input file" - nothing ever produced it), not LNK1104, which is
what you would see if the file existed somewhere the linker was not looking.
The two point at different bugs and it is worth reading the number.

So before writing the build steps, grep the consumer's `.vcxproj` for
`ProjectReference`. If there is none, give the library its own msbuild step
ahead of the consumer, into the same pinned `OutDir`, and add that directory to
the linker's search path from the shared props file:

```xml
<AdditionalLibraryDirectories>$(OutDir);%(AdditionalLibraryDirectories)</AdditionalLibraryDirectories>
```

Use `$(OutDir)`, not a literal path: a props file cannot see cmd's `%CD%`, and
`OutDir` is pinned to the same place for every step anyway. Give the library its
own `IntDir` so its compiler PDB does not collide with the consumer's - and note
that a `StaticLibrary` target takes `<Lib>` rather than `<Link>`, so the props
file's `<Link>` half is simply ignored for it. The `<ClCompile>` half still
applies, which is the part that matters: it puts the library's debug information
where the consumer's linker can fold it into the final PDB.

### Recipe fields

- `toolchains`: declare what the **project** declares. BlackBoneDrv is
  `["msvc_x64"]` because all eight of its configurations are x64 and its header
  `#error`s on `_M_IX86`. Hidden declares both because all five of its projects
  offer `Win32` and `x64`. Recipes are matched on what they declare, not on host
  availability, because an MSVC dev environment targets one architecture at a
  time; the x64 CI leg only ever sees recipes naming `msvc_x64`.
- `is_blob`: **`False`**. A `.sys` is a real PE. Blob mode would skip the
  incremental-link check and gate on instruction count instead of functions.
- `min_functions`: leave `None` (floor 8) unless the project genuinely has
  fewer. It is used exactly as given and never clamped. Never raise or lower it
  to make a defective build pass.
- `min_named_ratio`: leave `0.5`. With a forced PDB a C driver should come in
  near 1.0. C++ with exception handling on x86 is the risky case -
  `blackbone.py`'s x86 leg lands at 0.523.
- `drop_crt_glue`: leave `True`. It is a user-mode ucrt/vcruntime baseline, so
  it will recognise little kernel runtime - it removed 21 symbols from
  BlackBoneDrv (`__security_check_cookie`, `__C_specific_handler`, the
  `__castguard_*` and `_guard_*` families, `RtlCaptureContext`, `strcmp`).
  Leaving it on asserts nothing and cannot mismatch, because `is_glue` requires
  the symbol name *and* the PicHash to match.
- `pdb`: name the **linker** PDB only. If the path is set it must exist or the
  build fails.
- Add `BuildStep("dir /s out", allow_failure=True)` as the last step. `build.py`
  reports a missing artefact by the expected path and nothing else, and `/s`
  catches a WDK that put the output one directory down.

## There is no driver-specific code in this repo

Worth knowing before you go looking for it. A `.sys` goes down the identical
path as a `.dll`: no extension special-casing anywhere, architecture is derived
from the disassembly rather than the toolchain, and SMDA's PE loader only tests
for `MZ`. Grepping `scripts/corpus/` for `driver|kernel|wdk|\.sys` finds the
recipes, the probe in the workflow, and two unrelated uses of the word "driver".

Everything driver-specific lives in the recipe, expressed as msbuild properties.
Keep it that way.

## Registration and documentation

Registration is automatic: `recipes/__init__.py` walks the package with
`pkgutil.iter_modules`, skips `_`-prefixed names, and harvests each module's
`RECIPES` dict, raising on a duplicate key. The workflow names no recipe and no
family - it asks `build_corpus.py list --toolchain msvc_<arch>` - and the push
path filter is already the whole-directory glob `scripts/corpus/recipes/**`.

Two things are manual, both in the top-level `README.md`:

- a `### <Family><a id='<anchor>'></a>` section and a TOC entry
- a fence pair, which `readme.py` rewrites from provenance:

```
<!-- generated: <Family> -->
<!-- /generated -->
```

Ship these with the recipe, leaving the fence empty. That is safe: the README
checks (`find_broken_readme_links`, `find_undocumented_families`) run only when
`validate_all` is called with `root is None`, and CI validates per family with
`validate data/<Family>`. Do not run `build_corpus.py readme <Family>` until
provenance exists - a fence naming a family with no provenance is an error, not
a no-op.

One trap worth stating: `refresh_provenance.py` indexes on
`(family, version)`. Two recipes sharing that key collide and every record
reports Unmatched. That is the mechanical reason BlackBoneDrv is its own family
rather than a second component of BlackBone - both declare `msvc_x64`, so the
toolchain alias cannot separate them. A driver that shares no code with its
user-mode sibling should be its own family anyway; if it shares a repository but
not a binary, give it a distinct `family`.

## Licence and provenance

An absent licence is not a reason to skip a project, and it is not something to
paper over. The corpus already carries artefacts at `license: "none"`
(CallObfuscator, HeavensGate2, NTTITONHeavensGate), and BlackBoneDrv's entry is
a paragraph naming the four Windows Research Kernel functions and four
uncredited `Mi*` AVL routines compiled into it. House phrasing:

> No licence of any kind: no LICENSE or COPYING file and no copyright or licence
> line in the README or in any source file.

Then name each vendored third-party component separately, with its version and
licence, and say whether it contributes code to **this** artefact. Vendored code
in drivers is common and it matters: Hidden compiles Zydis 3.1.0 and Zycore
1.0.0 into `Hidden.sys`, so a share of that artefact's functions are Zydis's,
and `ZYAN_NO_LIBC` means they will not necessarily match a Zydis built the
ordinary way. Record that, and prefer adding the library as its own family over
reading it through the tool that vendored it.

Say in `notes` that the driver is linked and disassembled, never packaged,
signed, installed or loaded. For unsigned kernel-mode code that is the honest
and relevant fact.

## Counting functions honestly

A driver's reported function count will overstate its own code, and by a lot.
BlackBoneDrv has 139 functions in source and reports 321:

- 58 are MSVC string-literal COMDAT symbols (`??_C@_...`) sitting in code
  sections, disassembled as one- to six-instruction fragments
- a further 112 are three instructions or fewer, almost all import thunks into
  `ntoskrnl`
- the 144 of ten instructions or more are the real code, and agree with the 139
  counted by hand

Count the source before the build so you have something to check against, say in
`notes` where the excess comes from, and tell the reader which number to judge
coverage on. A recipe that reports 321 functions without that paragraph is
overstating its own coverage by a factor of two.

## Open risks are part of the recipe

Both driver recipes end their module docstring with a numbered "Open risks"
list, in the order the risks would bite. That is not decoration - `apicallproxy.py`
named `/p:DriverType=WDM` before its first round and was right. Write yours
before the first CI run, and when a build comes back, fix the recipe and correct
the list rather than deleting it.

When a leg fails, narrow the recipe and record why. Never lower a gate to make a
red build go green.
