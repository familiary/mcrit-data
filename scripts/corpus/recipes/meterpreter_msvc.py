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

**`BUILD_ARCH` has to be passed here too, for a different reason than on the
MinGW side.** `workspace/CMakeLists.txt` sets it from
`CMAKE_GENERATOR_PLATFORM` under MSVC - but the `NMake Makefiles` generator
this corpus uses has no generator platform, so the variable comes back empty
and `TARGET_ARCH` falls through to its x64 default. That would compile the
x86 leg with `WIN64`/`_WIN64`/`X64` defined and write it to `metsrv.x64.dll`.
`{msbuild_platform}` already spells `Win32`/`x64`, so one command line serves
both legs, exactly as in `meterpreter.py`.

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
_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
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
_CMAKE = ('cmake -S workspace -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release '
          '-DBUILD_ALL=OFF '
          '-DBUILD_METSRV=ON '
          '-DUSE_STATIC_MSVC_RUNTIMES=OFF '
          '-DBUILD_ARCH={msbuild_platform} '
          '%s %s' % (_CFLAGS, _LDFLAGS))

_BUILD = "cmake --build build-{arch} --target metsrv"

# Cheap insurance, as in xz_msvc.py and libuv_msvc.py: build.py reports a
# missing artefact by the path it expected and nothing else, so this puts the
# names the build actually wrote into the log the workflow prints on failure.
_DIR = "dir build-{arch}\\metsrv"


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
            Artifact(path="c\\meterpreter\\build-{arch}\\metsrv\\metsrv.{arch}.dll",
                     component="metsrv.dll",
                     pdb="c\\meterpreter\\build-{arch}\\metsrv\\metsrv.{arch}.pdb"),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O1 /Ob1 /DNDEBUG /Zi with /W3 /WX - the recipe "
                    "passes /O2 /Ob2 and workspace/CMakeLists.txt rewrites "
                    "both down for MSVC Release, which is upstream's own "
                    "intent; /INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF "
                    "/OPT:NOICF at link, plus upstream's own /ignore:4070, "
                    "/safeseh:no and /DEF:metsrv.def. CMake NMake Makefiles "
                    "with BUILD_ALL=OFF, BUILD_METSRV=ON, "
                    "USE_STATIC_MSVC_RUNTIMES=OFF and BUILD_ARCH=Win32/x64",
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
