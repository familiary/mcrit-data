"""Meterpreter (mcrit-data issue #31) - metsrv, MinGW x86/x64.

rapid7/metasploit-payloads is the build tree for the Windows Meterpreter: a
reflectively-loaded DLL payload (`metsrv`) plus a set of extension DLLs that
the server side loads into the same process. Malpedia tracks it as
`win.meterpreter`, and it is one of the most frequently re-encountered code
bases in Windows intrusion work, which is what makes it worth a reference
family rather than a signature.

One of the tree's 27 projects is built here: `metsrv`, the core server. The
issue proposes `metsrv` plus `ext_server_stdapi` as the first target, and
`ext_server_stdapi` does build cleanly by this recipe - it was built,
measured, and then deliberately left out. The reason is leakage rather than
a build problem and is recorded in the README's not-built table: it compiles
one C++ translation unit, so it links as C++, and MinGW's C++ exception
runtime then enters the image in bodies the measured baseline does not
reach. Adding it put two new leakage findings into `validate --deep`
(`__cxa_init_primary_exception` and `_Unwind_ForcedUnwind_Phase2`, 18
instructions each, under 7-Zip, Meterpreter and MinGW alike). That wants a
baseline round, which is a change to `corpus/baseline.py` and belongs in its
own PR; it is not something a recipe should paper over. The remaining 24
extensions need no change to this recipe's shape either way.

**Why MinGW and not MSVC.** The issue describes the MSVC route - `make.bat`
driving `workspace/make.msbuild` - and that is what Rapid7 ships: their
distributed binaries use the `v120_xp` toolset, and `make.bat` pins
`v141_xp`. Neither toolset exists on the `windows-2022` runner this
repository builds MSVC data on, so an MSVC artefact here would be a v143
shape rather than the distributed one. That is still worth having and is
recorded as not-yet-built rather than claimed; see the README row.

What made the MinGW axis the one to build first is that it is upstream's
own supported cross-build, not an approximation written here:
`c/meterpreter/toolsets/{i686,x86_64}-w64-mingw32.cmake` are upstream's
CMake toolchain files, `workspace/CMakeLists.txt` carries a full non-MSVC
branch, and `docker/Dockerfile` - Rapid7's own dev container - installs
`gcc-mingw-w64-{i686,x86-64}`, `g++-mingw-w64-*` and `cmake` for exactly
this path. No upstream source is modified and no flag is added: the three
`-D` options below are the ones `workspace/CMakeLists.txt` declares with
`option()`, plus `BUILD_ARCH`, which it reads from the cache on the
non-MSVC path.

**BUILD_ARCH has to be passed.** `workspace/CMakeLists.txt` sets
`BUILD_ARCH` from `CMAKE_GENERATOR_PLATFORM` only under MSVC, and then keys
`TARGET_ARCH`, the `WIN64`/`_WIN64`/`X64` defines and the output filename off
it, defaulting to x64 when it is unset. A 32-bit cross build with
`BUILD_ARCH` unset therefore compiles 64-bit defines into 32-bit code and
writes it to `metsrv.x64.dll`. `{msbuild_platform}` is the placeholder that
already spells `Win32`/`x64`, so both architectures share one command line.

**The vendored zlib is kept, deliberately.** `source/metsrv/zlib.c` is an
amalgamated zlib **1.0.4P** - `zlib.h:245` is `ZLIB_VERSION "1.0.4P"`,
`zlib.h:19` dates it to July 1996 - carrying the PPP additions
`Z_PACKET_FLUSH`, `inflateIncomp` and `deflateOutputPending`. It is a 1996
fork and not the modern zlib the `libzlib` family covers, so excluding it
would drop code that is genuinely in every metsrv ever shipped while adding
nothing to `data/libzlib`'s coverage. Verified present in the artefact:
`deflateOutputPending` is in the x64 symbol table, which is a name no
unforked zlib has. Measured against the corpus, the two do not collide:
`metsrv` shares exactly two PicHashes of ten instructions or more with
`data/libzlib`, both unnamed. It is recorded here and in `notes` so the
attribution is not mistaken for Meterpreter's own code.

**The kiwi/mimikatz submodule is not built.** `BUILD_EXT_KIWI` stays off.
mimikatz is tracked separately as issue #60 and belongs in its own family;
it is not reached by `BUILD_METSRV`. The submodule is still *fetched*,
because `corpus/fetch.py` initialises submodules recursively so that what
was built is fully pinned, and its commit is recorded in provenance along
with ReflectiveDLLInjection, COFFLoader and meterpreter-deps.

**What `USE_STATIC_MSVC_RUNTIMES` does on this path, and why it is left
alone.** The option is upstream's, defaults ON, and on the non-MSVC branch
it appends `-static-libgcc -mwindows -fms-extensions
-Wl,--enable-stdcall-fixup` to the C flags and `-static-libstdc++ -std=c++11`
to the C++ ones. The README's warning about `-static-libstdc++` pulling
~13,500 libstdc++ functions into a sample does not fire for this artefact,
and that was measured rather than assumed: `metsrv` is `project(metsrv C)`
with no C++ translation unit, 61 functions are removed as compiler runtime
on both architectures and all of them are plain MinGW C glue, and it
carries no `_Unwind_*`, no `__cxxabiv1::` and no 64-bit division helpers.
The C++ half of that option is exactly what kept `ext_server_stdapi` out,
so the flag is not harmless in general - it is harmless *here*, for a
target with no C++ in it. Turning the option off would change the shape of
the artefact away from what upstream's own build produces, for no
attribution gain.

**Measured.** kept / removed as compiler runtime / image total:

    metsrv  x86   578 / 61 / 639
    metsrv  x64   615 / 61 / 676

The two architectures share **zero** PicHashes of ten instructions or more
with each other, which is the expected result for one source through two
code generators and is worth stating because it means the x86 row is not a
near-duplicate of the x64 one. Against the rest of the corpus, the two
artefacts together share 4 such PicHashes with abseil and at most 2 with
each of the other 37 families that share any. Only the abseil ones carry a
name on either side, and the names differ - metsrv's `memcpy_s` /
`memmove_s` against abseil's `vsprintf_s`, both behind mingw-w64's `_stub`
- so they classify as short-body coincidences rather than leakage. Every
other shared hash is unnamed in both families.

The x86 and x64 `removed_runtime_functions` lists look almost disjoint and
are not: nearly all of the difference is i686's leading-underscore
decoration, `__Unwind_Backtrace` against `_Unwind_Backtrace`.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# -S workspace, because the CMake project root is c/meterpreter/workspace
# while the git root is the repository. $PWD is c/meterpreter here, so the
# toolchain file is named absolutely: CMake resolves a relative
# CMAKE_TOOLCHAIN_FILE against the build directory, not the source one.
#
# BUILD_ALL defaults ON and would build all 27 projects, among them the kiwi
# extension and the Python and PowerShell ones; it is turned off and the one
# wanted project is named instead.
_CMAKE = ("cmake -S workspace -B build-{arch} "
          "-DCMAKE_TOOLCHAIN_FILE=$PWD/toolsets/{host}.cmake "
          "-DCMAKE_BUILD_TYPE=Release "
          "-DBUILD_ALL=OFF "
          "-DBUILD_METSRV=ON "
          "-DBUILD_EXT_STDAPI=ON "
          "-DBUILD_ARCH={msbuild_platform}")

_BUILD = "cmake --build build-{arch} -j$(nproc)"


RECIPES = {
    "Meterpreter_2.0.259": Recipe(
        family="Meterpreter",
        version="2.0.259",
        upstream="https://github.com/rapid7/metasploit-payloads",
        license="BSD-3-clause, Copyright 2006-2025 Rapid7, Inc.",
        source=Source(
            git_url="https://github.com/rapid7/metasploit-payloads.git",
            git_ref="02c6032202f307926c2758fdc88827ccabe5afd2"),
        build=[BuildStep(_CMAKE, cwd="c/meterpreter"),
               BuildStep(_BUILD, cwd="c/meterpreter")],
        artifacts=[
            Artifact(path="c/meterpreter/build-{arch}/metsrv/metsrv.{arch}.dll",
                     component="metsrv.dll"),
            Artifact(path="c/meterpreter/build-{arch}/ext_server_stdapi/"
                          "ext_server_stdapi.{arch}.dll",
                     component="ext_server_stdapi.dll"),
        ],
        toolchains=["mingw_x86", "mingw_x64"],
        requires=["cmake", "make"],
        # CMake's own Release default for GNU, which is what upstream relies
        # on: workspace/CMakeLists.txt downgrades /O2 to /O1 for MSVC only
        # and leaves the GNU flags alone. The -D options are upstream's own
        # option() switches; no compiler or linker flag is added by this
        # recipe. -Wl,--exclude-all-symbols on metsrv is upstream's
        # (workspace/metsrv/CMakeLists.txt) and suppresses auto-exports, not
        # the COFF symbol table SMDA reads.
        build_flags="cmake --build Release (-O3 -DNDEBUG) for "
                    "i686-w64-mingw32 / x86_64-w64-mingw32 via upstream's "
                    "toolsets/*.cmake; upstream USE_STATIC_MSVC_RUNTIMES=ON "
                    "adds -static-libgcc -mwindows -fms-extensions "
                    "-Wl,--enable-stdcall-fixup; BUILD_ALL=OFF with "
                    "BUILD_METSRV=ON and BUILD_ARCH=Win32/x64",
        notes="Built through upstream's own MinGW cross-build (the CMake "
              "toolchain files in c/meterpreter/toolsets and the non-MSVC "
              "branch of workspace/CMakeLists.txt), which is the path "
              "Rapid7's own docker/Dockerfile provisions. It is not the "
              "toolchain Rapid7 distributes: their released binaries are "
              "MSVC v120_xp and make.bat pins v141_xp, neither of which "
              "exists on the windows-2022 runner, so no MSVC artefact is "
              "claimed here. metsrv statically contains an amalgamated zlib "
              "1.0.4P (zlib.h:245 ZLIB_VERSION \"1.0.4P\", July 1996) with "
              "the PPP additions Z_PACKET_FLUSH, inflateIncomp and "
              "deflateOutputPending, so those functions are present under "
              "this family; it is a 1996 fork and does not duplicate the "
              "modern zlib in data/libzlib, which it shares two unnamed "
              "PicHashes with and no named one, and deflateOutputPending in "
              "the symbol table is the name that distinguishes the two. "
              "metsrv is C only: 61 functions are removed as compiler "
              "runtime on each architecture and all are plain MinGW glue. "
              "The two architectures share no PicHash of ten instructions "
              "or more with each other. One of the tree's 27 projects is "
              "built: ext_server_stdapi builds by this recipe but links as "
              "C++ and brings MinGW's C++ exception runtime in under this "
              "family's name, which needs a baseline round first and is "
              "recorded in the not-built table; the kiwi extension is not "
              "built at all, mimikatz being issue #60, though fetch.py "
              "still pins its submodule commit along with "
              "ReflectiveDLLInjection, COFFLoader and meterpreter-deps.",
    ),
}
