"""Meterpreter metsrv built with MSVC, beside the MinGW build of the same commit.

`meterpreter.py` records why the MinGW axis was built first: it is upstream's
own supported cross-build and it needs no Windows runner. It also records why
that is not the whole story, and this recipe is the other half of it.

**Why this matters more than the usual MinGW/MSVC pairing.** Rapid7 ships
MSVC-built binaries - their distributed `metsrv` uses the `v120_xp` toolset -
and `c/meterpreter/make.bat` pins `v141_xp`. Every `win.meterpreter` sample an
analyst meets is therefore MSVC code, and a MinGW reference answers it only
weakly. For C the gap is narrower than for C++, since it is the same source
through two code generators, but it is still the difference between the
shipped shape and an approximation.

**This is a v143 artefact and not the distributed one.** Neither `v120_xp` nor
`v141_xp` exists on the `windows-2022` image: it carries VS2022 and v143, and
XP targeting was removed from VS2022 altogether. So this is the right source
compiled by the wrong toolset, which is worth having and is worth saying
plainly rather than letting the family table imply otherwise. The MinGW
artefact, the v143 artefact and the distributed `v120_xp` binary are three
different shapes of one program.

**`/MD` is this recipe's one deliberate departure from upstream.**
`workspace/CMakeLists.txt` declares `option(USE_STATIC_MSVC_RUNTIMES "Use /MT
instead of /MD in MSVC" ON)`, so upstream's own default is `/MT` and that is
what Rapid7 ships. This corpus mandates `/MD`, and for a good reason the
`Hidden` family already records: under `/MT` the CRT and the STL are linked
into the image and would be attributed to this family, where under `/MD` they
stay in `ucrtbase` and `vcruntime140` and remain `data/MSVC`'s. It is
upstream's own option, set from the command line, so no source is touched -
but it does mean this artefact's CRT surface differs from the distributed
binary's, on top of the toolset difference.

**What upstream's own Release settings do to the flags, read rather than
assumed.** `workspace/CMakeLists.txt` runs, for MSVC Release only:

    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} /W3 /WX")
    string(REPLACE "O2" "O1" CMAKE_C_FLAGS_RELEASE "${CMAKE_C_FLAGS_RELEASE}")
    string(REPLACE "Ob2" "Ob1" CMAKE_C_FLAGS_RELEASE "${CMAKE_C_FLAGS_RELEASE}")

Two consequences. First, the `/MD /O2 /Ob2 /DNDEBUG /Zi` this recipe passes
is rewritten by upstream into `/MD /O1 /Ob1 /DNDEBUG /Zi`, so the artefact is
**/O1**, not the `/O2` every other MSVC recipe here produces. That is
upstream's intent and is left alone; `build_flags` records the result rather
than the input. Second, `/WX` is in effect: upstream promotes warnings to
errors, on a toolset three generations newer than any it claims to support
(its README names VS2013, VS2017 and VS2019). Nothing is passed to suppress
that. If v143 warns where v141 did not, this build fails on `/WX` and the
exact message belongs in the README's not-built table, because "upstream's
own settings do not compile on v143" is a finding and not something to paper
over with `/WX-`.

**This uses the Visual Studio generator, not the `NMake Makefiles` one every
other MSVC recipe here uses, and that is the whole reason the first attempt
failed.** Run 42412811010 was dispatched on NMake Makefiles and both legs
failed, in two different places:

    x64  base_inject.c(374): error C2220: the following warning is treated
         as an error
         base_inject.c(374): warning C4996: 'GetVersionExW': was declared
         deprecated

    x86  GateTrampoline64.asm(72): fatal error A1010: unmatched block
         nesting : DoSyscall
         ... Hostx86\x86\ml.exe ... GateTrampoline64.asm

The x86 failure is the informative one: the 32-bit assembler was handed the
**64-bit** trampoline. `workspace/ReflectiveDLLInjection/CMakeLists.txt`
chooses between `GateTrampoline32.asm` and `GateTrampoline64.asm` with

    set(BITS "64")
    if(MSVC AND "${CMAKE_GENERATOR_PLATFORM}" STREQUAL "Win32")
        set(BITS "32")

and a Makefile generator has no `CMAKE_GENERATOR_PLATFORM`, so `BITS` stayed
at its 64 default on both legs. That is the same gap that makes
`workspace/CMakeLists.txt` compute `BUILD_ARCH` wrongly, which the first
attempt had already worked around by passing `-DBUILD_ARCH` explicitly -
treating one symptom of a cause with two.

`BITS` cannot be fixed the same way: it is a plain `set()` at the top of the
file, so a cache entry is overwritten before the `if` reads it. Nor can the
platform variable simply be supplied - CMake rejects it outright for a
generator that has no platform, verified locally rather than guessed:

    CMake Error at CMakeLists.txt:2 (project):
      Generator

        Unix Makefiles

      does not support platform specification, but platform

        Win32

So the generator itself has to supply it. `-G "Visual Studio 17 2022"` with
`-A {msbuild_platform}` sets `CMAKE_GENERATOR_PLATFORM` natively, which fixes
`BITS` and `BUILD_ARCH` together and at their source - and it is closer to
what upstream does anyway, since `make.bat` drives MSBuild. `BUILD_ARCH` is
therefore no longer passed: upstream's own `set(BUILD_ARCH
${CMAKE_GENERATOR_PLATFORM})` now computes it correctly.

The cost is that the Visual Studio generator is multi-configuration, so the
artefact lands under a `Release/` subdirectory rather than in the target
directory, and the build needs `--config Release`. Both are reflected below.

**`/wd4996` and the two deprecation defines are passed, and nothing else.**
The x64 failure above is upstream's `/WX` meeting a 2026 SDK: `GetVersionExW`
was deprecated in the Windows 8.1 SDK, long after the XP-era toolsets
upstream targets, and this tree compiles with `WINVER=0x0501`. `/wd4996`,
`_CRT_SECURE_NO_WARNINGS` and `_WINSOCK_DEPRECATED_NO_WARNINGS` are the three
documented ways to say "this is XP-era code on a modern SDK", they cover the
whole C4996 deprecation class that 32 translation units of it will raise, and
**none of them changes a byte of generated code** - C4996 is a diagnostic.
What is deliberately *not* passed is `/WX-`: upstream's promotion of warnings
to errors stays in force, so a genuine portability problem on v143 - the kind
that would change behaviour rather than just emit a notice - still fails this
build loudly instead of being silently absorbed.

**What is and is not in the image.** Only `metsrv` is built:
`BUILD_ALL=OFF` with `BUILD_METSRV=ON`, so the 25 extensions and the kiwi
submodule are not reached. `ReflectiveDLLInjection` is, as metsrv links it,
and on this path its `GateTrampoline{32,64}.asm` goes through MASM rather
than GNU as - `workspace/ReflectiveDLLInjection/CMakeLists.txt` calls
`enable_language(ASM_MASM)` under MSVC. The vendored zlib 1.0.4P is here as
it is in the MinGW artefact, for the reason `meterpreter.py` argues at
length; `deflateOutputPending` remains the name that tells that 1996 PPP fork
from the modern zlib in `data/libzlib`.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason `sqlite3_msvc.py` spells out: one `Recipe` has one build list,
and these steps run under the developer command prompt the workflow sets up,
not under `sh`.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# The corpus mandate: /MD, never /MT; /Zi so the link writes a PDB, which is
# the only way MSVC symbols reach a report. Upstream rewrites O2->O1 and
# Ob2->Ob1 for MSVC Release, so what cl actually receives is /O1 /Ob1 - see
# the docstring. /INCREMENTAL:NO is restated on the link because setting the
# variable replaces CMake's Release default, and an incrementally linked
# image reaches every function through a jump thunk that SMDA counts as a
# function of its own.
_CFLAGS = ('-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi '
           '/wd4996 /D_CRT_SECURE_NO_WARNINGS '
           '/D_WINSOCK_DEPRECATED_NO_WARNINGS"')
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

# NMake Makefiles for the reason libuv_msvc.py records: nmake ships with MSVC,
# the generator is single-configuration so the DLL lands where the MinGW
# recipe finds it rather than under a Release/ subdirectory, and the target
# architecture comes from the developer environment the workflow sets up.
#
# -S workspace because the CMake project root is c/meterpreter/workspace while
# the git root is the repository. The four -D options after the generator are
# upstream's own option() switches plus BUILD_ARCH; see the docstring for why
# each is needed.
_CMAKE = ('cmake -S workspace -B build-{arch} '
          '-G "Visual Studio 17 2022" -A {msbuild_platform} '
          '-DBUILD_ALL=OFF '
          '-DBUILD_METSRV=ON '
          '-DUSE_STATIC_MSVC_RUNTIMES=OFF '
          '%s %s' % (_CFLAGS, _LDFLAGS))

_BUILD = "cmake --build build-{arch} --target metsrv --config Release"

# Cheap insurance, as in xz_msvc.py and libuv_msvc.py: build.py reports a
# missing artefact by the path it expected and nothing else, so this puts the
# names the build actually wrote into the log the workflow prints on failure.
_DIR = "dir build-{arch}\\metsrv\\Release"


RECIPES = {
    "Meterpreter_2.0.259_msvc": Recipe(
        family="Meterpreter",
        version="2.0.259",
        upstream="https://github.com/rapid7/metasploit-payloads",
        license="BSD-3-clause, Copyright 2006-2025 Rapid7, Inc.",
        source=Source(
            git_url="https://github.com/rapid7/metasploit-payloads.git",
            git_ref="02c6032202f307926c2758fdc88827ccabe5afd2"),
        build=[BuildStep(_CMAKE, cwd="c\\meterpreter"),
               BuildStep(_BUILD, cwd="c\\meterpreter"),
               BuildStep(_DIR, cwd="c\\meterpreter", allow_failure=True)],
        artifacts=[
            Artifact(path="c\\meterpreter\\build-{arch}\\metsrv\\Release\\metsrv.{arch}.dll",
                     component="metsrv.dll",
                     pdb="c\\meterpreter\\build-{arch}\\metsrv\\Release\\metsrv.{arch}.pdb"),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O1 /Ob1 /DNDEBUG /Zi with /W3 /WX - the recipe "
                    "passes /O2 /Ob2 and workspace/CMakeLists.txt rewrites "
                    "both down for MSVC Release, which is upstream's own "
                    "intent; /INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF "
                    "/OPT:NOICF at link, plus upstream's own /ignore:4070, "
                    "/safeseh:no and /DEF:metsrv.def. plus /wd4996, "
                    "_CRT_SECURE_NO_WARNINGS and "
                    "_WINSOCK_DEPRECATED_NO_WARNINGS for the C4996 "
                    "deprecation class, which are diagnostics only; /WX- is "
                    "NOT passed. CMake Visual Studio 17 2022 generator with "
                    "-A Win32/x64 and --config Release, BUILD_ALL=OFF, "
                    "BUILD_METSRV=ON, USE_STATIC_MSVC_RUNTIMES=OFF",
        notes="The MSVC half of the Meterpreter family, same commit as the "
              "MinGW artefacts, so the two differ in the compiler rather "
              "than in what was built. Read this as the right source "
              "compiled by the wrong toolset: Rapid7 distributes v120_xp "
              "and make.bat pins v141_xp, while the windows-2022 image "
              "carries only v143 and VS2022 dropped XP targeting entirely, "
              "so the MinGW artefact, this one and the shipped binary are "
              "three shapes of one program. Built /MD rather than "
              "upstream's default /MT (its own "
              "USE_STATIC_MSVC_RUNTIMES option, set from the command line), "
              "which is this corpus's mandate and keeps the CRT and STL in "
              "ucrtbase and vcruntime140 under data/MSVC instead of under "
              "this family - the reason the Hidden family records for the "
              "same choice; it does mean the CRT surface differs from the "
              "distributed binary's. The artefact is /O1 /Ob1, not the /O2 "
              "every other MSVC recipe here produces, because "
              "workspace/CMakeLists.txt rewrites O2 to O1 and Ob2 to Ob1 "
              "for MSVC Release. Upstream also promotes warnings to errors "
              "there with /W3 /WX on a toolset three generations newer than "
              "any its README claims (VS2013/2017/2019); nothing is passed "
              "to suppress that, so if v143 warns where v141 did not this "
              "recipe fails and the message belongs in the not-built table. "
              "BUILD_ARCH must be passed because the NMake Makefiles "
              "generator has no CMAKE_GENERATOR_PLATFORM for "
              "workspace/CMakeLists.txt to read, so the x86 leg would "
              "otherwise compile 64-bit defines and write metsrv.x64.dll. "
              "Only metsrv is built; the 25 extensions and the kiwi "
              "submodule are not reached. ReflectiveDLLInjection is linked "
              "in and its GateTrampoline asm goes through MASM on this path "
              "rather than GNU as. The vendored zlib 1.0.4P is present as "
              "it is in the MinGW artefact.",
    ),
}
