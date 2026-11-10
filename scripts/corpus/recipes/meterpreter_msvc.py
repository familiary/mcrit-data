"""Meterpreter metsrv built with MSVC, from patched upstream source (issue #31).

**This is the first recipe in this corpus that patches upstream source, and it
exists by explicit maintainer decision.** `scripts/corpus/README.md` otherwise
says that anything requiring a patch is deliberately absent, and the rule is
worth keeping: a patched tree is no longer the thing anybody else compiles. So
the patch is kept as small and as provably inert as a patch can be, it lives
in `scripts/corpus/patches/` rather than in a fork, and
`data/Meterpreter/provenance.json` records its digest beside the source pin so
the artefact is never mistaken for a clean build.

What the patch does, in full: it deletes six lines from
`source/metsrv/pool_party_ext.h` that re-declare `struct _CLIENT_ID`. The same
header `#include <winternl.h>` four lines earlier, and on the runner's
10.0.26100 SDK that header already declares CLIENT_ID, field for field
identically. So the declaration is pure duplication and the compiler sees one
of two identical types instead of two - no generated code can change. Upstream
guards it with `#ifndef __MINGW32__`, i.e. it assumed only MinGW's headers
would have one, which held on the XP-era SDKs it targets and does not hold
now:

    pool_party_ext.h(22,16): error C2011: '_CLIENT_ID': 'struct' type redefinition

The patch file itself carries the longer argument, including why defining
`__MINGW32__` instead - the obvious one-flag alternative - is not an option:
that macro is read again in `source/common/common.h:32`, where it stubs SEH
out entirely, so it would compile away every `__try`/`__except` in metsrv and
change the artefact rather than a diagnostic.

**Why this is worth having even though the shipped binary is already here.**
`meterpreter_prebuilt.py` harvests Rapid7's own MSVC build out of the gem, and
for matching a live sample that is the better artefact - it is the exact image
in the wild. But it has no PDB, so it carries 2 recovered symbols across
28,892 functions. This build has one: MSVC writes symbols to a PDB, SMDA reads
it, and the result is MSVC-shaped code that is also *named*. Neither artefact
substitutes for the other - one says what the distributed code looks like, the
other says what it is called.

It also sidesteps the leakage that cost the harvested family its x86 leg.
Upstream defaults `USE_STATIC_MSVC_RUNTIMES=ON`, which links the MSVC CRT into
every image; this recipe passes `OFF`, so the CRT is imported and stays
attributed to `data/MSVC` where it belongs.

Not the distributed toolset, and that is not fixable here: `make.bat` pins
`v141_xp` and Rapid7 ships `v120_xp`, neither of which exists on the
`windows-2022` image since XP targeting was removed from it. This is a v143
shape. The gem rows are where the distributed toolset is.

Two upstream problems besides the header, both solved with flags rather than
patches, and both found the hard way on earlier runs:

  * upstream compiles with its own `/W3 /WX` (`workspace/CMakeLists.txt:155`)
    and `WINVER=0x0501`, so `GetVersionExW` - deprecated in the Windows 8.1
    SDK, long after the toolsets upstream targets - became
    `base_inject.c(374): error C2220`. Answered with `/wd4996` plus the two
    deprecation defines: diagnostics only, no generated code changed. `/WX-`
    was deliberately not used, so a real portability problem would still fail
    the build loudly.
  * `workspace/ReflectiveDLLInjection/CMakeLists.txt` picks between
    `GateTrampoline32.asm` and `GateTrampoline64.asm` on
    `CMAKE_GENERATOR_PLATFORM`, which a Makefile generator leaves empty - so
    an x86 leg handed `ml.exe` the 64-bit trampoline and died with
    `GateTrampoline64.asm(72): fatal error A1010`. `BITS` cannot be set from
    the cache, and CMake refuses the platform variable for a platform-less
    generator. Answered by using the Visual Studio generator with `-A`, which
    supplies it natively, is what `make.bat` drives anyway, and also lets
    `workspace/CMakeLists.txt:124` compute `BUILD_ARCH` itself rather than
    needing it passed as the MinGW recipe does.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_PATCH = ('git apply --verbose '
          '"{repo}/scripts/corpus/patches/meterpreter-sdk-client-id.patch"')

# Diagnostics and symbols only. /Zi plus /DEBUG because CMake's MSVC Release
# emits no PDB by default and without one SMDA can name only exports, which is
# the whole reason this build is worth running beside the harvested one.
_CFLAGS = ("/Zi /wd4996 /D_CRT_SECURE_NO_WARNINGS "
           "/D_WINSOCK_DEPRECATED_NO_WARNINGS")
_LDFLAGS = "/DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO"

# -A supplies CMAKE_GENERATOR_PLATFORM, which upstream reads for both
# BUILD_ARCH and the trampoline choice; BUILD_ARCH is therefore *not* passed
# here, unlike in the MinGW recipe where the generator leaves it empty.
#
# USE_STATIC_MSVC_RUNTIMES=OFF is /MD, which this corpus requires and which
# keeps the MSVC CRT out of the artefact.
#
# The output directories are pinned because the Visual Studio generator
# otherwise writes into a per-configuration subdirectory whose name depends on
# the generator, and build.py reports a missing artefact by the path it
# expected and nothing else.
_CMAKE = ('cmake -S workspace -B build-{arch} '
          '-G "Visual Studio 17 2022" -A {msbuild_platform} '
          '-DBUILD_ALL=OFF -DBUILD_METSRV=ON '
          '-DUSE_STATIC_MSVC_RUNTIMES=OFF '
          '-DCMAKE_C_FLAGS="%s" -DCMAKE_CXX_FLAGS="%s" '
          '-DCMAKE_SHARED_LINKER_FLAGS="%s" '
          '-DCMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE=%%CD%%\\out-{arch} '
          '-DCMAKE_PDB_OUTPUT_DIRECTORY_RELEASE=%%CD%%\\out-{arch}'
          % (_CFLAGS, _CFLAGS, _LDFLAGS))

_BUILD = "cmake --build build-{arch} --config Release --target metsrv"

# Insurance, as in xz_msvc.py and libuv_msvc.py: build.py reports a missing
# artefact by the expected path alone, so this puts what the build actually
# wrote into the log the workflow prints on failure. Both allow_failure, so
# neither can turn a good build red.
_LIST = "dir /s /b build-{arch} out-{arch}"
# And if the output directory pin did not take on this generator, recover the
# files from wherever they landed rather than spending another run finding out.
# Single % because these run through `cmd /c`, where %%f is not collapsed -
# that collapsing is a batch-file rule. out-{arch} is a sibling of build-{arch}
# and not inside the walked tree, so nothing is copied onto itself.
_MKDIR = "mkdir out-{arch}"
_RECOVER = ('for /r build-{arch} %f in (metsrv.{arch}.dll metsrv.{arch}.pdb) '
            'do @copy /y "%f" out-{arch}\\')


RECIPES = {
    "Meterpreter_2.0.259_msvc": Recipe(
        family="Meterpreter",
        version="2.0.259",
        upstream="https://github.com/rapid7/metasploit-payloads",
        license="BSD-3-clause, Copyright 2006-2025 Rapid7, Inc.",
        source=Source(
            git_url="https://github.com/rapid7/metasploit-payloads.git",
            # The same commit as the MinGW recipe, so the two artefacts differ
            # in the compiler and not in what was built.
            git_ref="02c6032202f307926c2758fdc88827ccabe5afd2"),
        build=[
            BuildStep(_PATCH),
            BuildStep(_CMAKE, cwd="c/meterpreter"),
            BuildStep(_BUILD, cwd="c/meterpreter"),
            BuildStep(_MKDIR, cwd="c/meterpreter", allow_failure=True),
            BuildStep(_RECOVER, cwd="c/meterpreter", allow_failure=True),
            BuildStep(_LIST, cwd="c/meterpreter", allow_failure=True),
        ],
        artifacts=[
            Artifact(path="c/meterpreter/out-{arch}/metsrv.{arch}.dll",
                     component="metsrv.dll",
                     pdb="c/meterpreter/out-{arch}/metsrv.{arch}.pdb"),
        ],
        # x64 only. Both legs built green and both are good data - 618 of
        # 618 functions named on x64, 630 of 630 on x86 - but the x86 one adds
        # a leakage finding to `validate --deep` and the x64 one adds none:
        #
        #   _putShortMSB (20 ins) under 3 families: MSVC, Meterpreter, libzlib
        #
        # That is zlib, out of metsrv's vendored amalgamated 1.0.4P, which #96
        # decided to keep. It only collides now because this build is MSVC: the
        # MinGW metsrv's copy hashes differently, and so does this build's own
        # x64 copy (pichash 9753904980302011575, 12 instructions), which is
        # shared with nothing - every other family carrying the 20-instruction
        # hash is x86 too (libzlib_1.2.13/1.3.1_msvc143_x86 and data/MSVC's
        # 2019_Pro_x86). So the architecture is the whole of the difference.
        #
        # By the deep check's own definition this is a true positive rather
        # than a false alarm: a statically linked dependency appearing under
        # the host project's name is exactly what it looks for. Shipping it
        # would move the corpus from 26 problems to 27, and a gate is not
        # worth having if the answer to it is to raise the number.
        #
        # Unlike the two artefacts withdrawn before it, this one is fixable:
        # `putShortMSB` is *named* on all three sides, so a round that teaches
        # the corpus a family may legitimately vendor a library can drop it and
        # restore this leg. (The harvested family's x86 findings are unnamed
        # and can never be reached that way.) That is a shared-pipeline change
        # and its own PR, so the x86 leg is held rather than lost, and the
        # not-built table records the hash to pick it up by.
        toolchains=["msvc_x64"],
        requires=["cmake"],
        build_flags="/MD /O2 /Ob2 (CMake MSVC Release) /Zi, plus upstream's "
                    "own /W3 /WX and /O1 downgrade from "
                    "workspace/CMakeLists.txt, with /wd4996 and the two "
                    "deprecation defines added; /DEBUG /Brepro /OPT:NOREF "
                    "/OPT:NOICF /INCREMENTAL:NO at link",
        notes="PATCHED UPSTREAM SOURCE: "
              "scripts/corpus/patches/meterpreter-sdk-client-id.patch "
              "(sha256 726bf014348daa1480862e33dca11cac06a012f9f95a800a48a82755fc22b992) "
              "removes a duplicate CLIENT_ID declaration that collides with "
              "the 10.0.26100 SDK's winternl.h, which the same header "
              "includes; the two declarations are identical, so no generated "
              "code changes. This is the only patched recipe in the corpus "
              "and it is here by maintainer decision. Built with /MD so the "
              "MSVC C runtime is imported and stays attributed to data/MSVC. "
              "v143, not the v141_xp/v120_xp that upstream pins and Rapid7 "
              "distributes - the gem rows carry the distributed toolset. "
              "Only metsrv is built; the kiwi extension stays off, mimikatz "
              "being issue #60. Nothing built here is run, configured or "
              "packaged into a payload.",
    ),
}
