"""Zydis and Zycore - the x86/x86-64 decoder, built with MinGW.

What it is. Zydis (zyantific/zydis) is a fast, allocation-free x86 and x86-64
instruction decoder and formatter in C; Zycore is the C support library it
sits on - ZyanString, ZyanVector, ZyanList, ZyanBitset, the allocator and the
argument parser - and Zydis's only dependency. Zycore is a git submodule that
each Zydis tag pins by commit, and the pipeline's fetch stage initialises it,
so its commit is recorded in provenance beside Zydis's own.

Why it is here. Issue 45 of the tracker. data/Hidden vendors Zydis 3.1.0 and
Zycore 1.0.0 under Hidden/Disasm and compiles them into Hidden.sys with
ZYCORE_STATIC_DEFINE, ZYDIS_STATIC_DEFINE and ZYAN_NO_LIBC, so 103 of the
507 functions the Hidden family reports for Hidden.sys are Zydis or Zycore
under the wrong name (the committed notes say 101; 103 carry a Zydis, Zyan or
Zycore name, 91 of them ten instructions or more). This is a
de-duplication and attribution family, not a new sighting: the chain is
ValleyRAT to Hidden, which Check Point Research publishes at roughly 175 of
about 200 driver functions, and Hidden to Zydis, which this corpus measures.
No published function-level match between Zydis and a ValleyRAT sample
exists, and none is claimed.

Measured against the Hidden family, on the x64 artefacts (Hidden is x64 only,
because the WDK has no x86 kernel libraries): every one of those 103 symbol
names is present in the MSVC build of Zydis 3.1.0 (103 of 103, with and
without ZYAN_NO_LIBC), against 83 in the MinGW and ELF builds and 95 in
4.1.1 MSVC, so the vendored copy is confirmed as 3.1.0 by name. Exact PicHash
agreement is much thinner: 3 of the 91 substantial ones
(ZydisFormatterBufferGetString, ZydisFormatterTokenNext and
ZydisIsFeatureEnabled, same name and same hash) with the 3.1.0 MSVC builds, 2
with 4.1.1 MSVC and none with MinGW or ELF. The driver is compiled by the
WDK's kernel-mode toolset with its own flags, which is a different code
generator configuration from the user-mode cl line used here, and the other 88
differ in encoding, not in what they are. So Hidden.sys's copy is not an
exact duplicate of this one, and fuzzy matching, not PicHash, is what will
link them. The functions are still carried inside data/Hidden/x64 under the
Hidden name: moving them out would rewrite committed Hidden data, which needs
a name-based removal this tooling does not have (refilter removes by baseline
symbol and PicHash only), so that is left as a decision and recorded in
hidden.py.

Zycore is not a family of its own. It cannot be built into a PE by itself
without becoming a second copy of the same functions: a Zycore DLL and a Zydis
DLL that links it statically both carry ZyanString and ZyanVector under two
family names, which is what validate --deep fails on. It is part of the Zydis
image here, and its functions are the Zyan* names (144 to 176 of an x64
image).

How it is built. Zydis's CMake builds libZydis and libZycore as static
archives, and SMDA cannot read an archive, so one DLL is linked from both with
the whole of each archive included (--whole-archive, /WHOLEARCHIVE), the route
cryptopp and the MSVC mbedTLS take. The two together are the library: Zydis's
decoder tables, decoder, formatters (Intel, AT&T), and the whole of Zycore.
Zydis's own CMake builds a shared library with ZYDIS_BUILD_SHARED_LIB, and
that path is not used because on Windows it unconditionally adds
resources/VersionInfo.rc, which is UTF-16 and which windres refuses
("syntax error" on the first line), so no MinGW DLL would link; the static
route needs no change to upstream. Examples and tools are switched off, and
-DCMAKE_POLICY_VERSION_MINIMUM=3.5 lets CMake 4 configure the 3.x projects'
old minimum.

Two versions. 3.1.0 is what Hidden vendors and the issue's first priority.
4.1.1 is the current release (4.x adds an encoder and has 194 Zydis* functions
in the MSVC x64 image against 3.1.0's 132). The
PicHash overlap at the ten-instruction floor between them on one toolchain is
110 of 198 distinct hashes (MinGW x64), 115 of 236 (MSVC x64), 113 of 205
(ELF x64) and under a third on x86, so each is a reference of its own.

MinGW specifics. Counts, kept + removed = total, with ten instructions or more
in brackets: 3.1.0 x86 262 + 114 = 376 (225), x64 282 + 109 = 391 (200); 4.1.1
x86 269 + 114 = 383 (231), x64 293 + 109 = 402 (206). The removed functions
are MinGW startup and runtime, libgcc and libc wrappers. 255 of 282 (3.1.0
x64) and 260 of 262 (3.1.0 x86) kept functions are named; 27 of the 282
x64 functions of 3.1.0 are unnamed. The
MinGW build shares 4 hashes with the MSVC build on x64 and none on x86, and
none with the ELF build on x64 (51 of 219 on x86). No glue survives the
filter on these four artefacts.

No ZYAN_NO_LIBC build with MinGW: the configuration exists to match Hidden's
kernel build, which is MSVC, and nothing here measured a reason to carry it
twice. It is built with MSVC, see zydis_msvc.py.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

# Static archives, then one DLL from both with every object forced in. The
# toolchain file is given as variables rather than a toolchain file so the
# recipe names nothing outside the tree. CMAKE_FIND_ROOT_PATH is the sysroot
# the cross compiler uses; the other recipes here pass it for the same
# reason. The project declares C and CXX languages, so both compilers are
# named, or CMake cannot determine the target architecture at all.
_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_POLICY_VERSION_MINIMUM=3.5 "
          "-DCMAKE_SYSTEM_NAME=Windows -DCMAKE_C_COMPILER={cc} "
          "-DCMAKE_CXX_COMPILER={cxx} -DCMAKE_RC_COMPILER={windres} "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
          "-DZYDIS_BUILD_EXAMPLES=OFF -DZYDIS_BUILD_TOOLS=OFF")
_LINK = ("{cc} -shared -o zydis.dll -Wl,--whole-archive "
         "build-{arch}/libZydis.a build-{arch}/zycore/libZycore.a "
         "-Wl,--no-whole-archive")


def _zydis(version, tag, notes):
    return Recipe(
        family="Zydis",
        version=version,
        upstream="https://github.com/zyantific/zydis",
        license="MIT, Copyright (c) Florian Bernd, Joel Hoener",
        source=Source(git_url="https://github.com/zyantific/zydis.git",
                      git_ref=tag),
        build=[BuildStep(_CMAKE),
               BuildStep("cmake --build build-{arch} -j$(nproc)"),
               BuildStep(_LINK)],
        artifacts=[Artifact(path="zydis.dll", component="zydis.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (CMake Release) static archives, linked into one "
                    "DLL with --whole-archive",
        notes=notes,
    )


_COMMON = ("Zydis and its Zycore submodule built as static archives and "
           "linked into one DLL with --whole-archive, so the whole of "
           "Zycore is in the image under the Zydis name; Zydis's own shared "
           "target is not used because its VersionInfo.rc is UTF-16 and "
           "windres rejects it. Hidden vendors Zydis 3.1.0 and compiles it "
           "into Hidden.sys, 103 of whose functions carry Zydis or Zycore "
           "names: all 103 are present here by name at 3.1.0 for the MSVC "
           "builds and 83 for MinGW, with exact PicHash agreement on only 3 "
           "of the 91 substantial ones, in the MSVC builds, because Hidden "
           "is compiled by the WDK. ")

RECIPES = {
    "Zydis_3.1.0": _zydis(
        "3.1.0", "v3.1.0",
        _COMMON + "Tag v3.1.0 with the Zycore commit it pins, 3435866. "
        "Measured: x86 262 functions kept of 376, x64 282 of 391, 225 and "
        "200 of them ten instructions or more; no glue survives the filter."),
    "Zydis_4.1.1": _zydis(
        "4.1.1", "v4.1.1",
        _COMMON + "Tag v4.1.1 with the Zycore commit it pins, 0b2432c. "
        "Measured: x86 269 functions kept of 383, x64 293 of 402, 231 and "
        "206 of them ten instructions or more; no glue survives the filter. "
        "110 of 198 distinct x64 hashes of 3.1.0 are also in this build."),
}

# Hidden's vendored copy, identified by content rather than by its version
# macro (see the "Hidden's commit" paragraph of zydis_msvc.py).
RECIPES["Zydis_3.1.0-6a17c48"] = _zydis(
    "3.1.0-6a17c48", "6a17c48576e1b016ce098c4bdbd001a1403b6a0a",
    _COMMON + "Master at commit 6a17c48 (2021-07-29, \"Update `Zycore` "
    "submodule\") with the Zycore commit it pins, 4f3746f: the commit whose "
    "sources Hidden/Disasm vendors (its ZYDIS_VERSION still reads 3.1.0). "
    "MEASURED_PLACEHOLDER")
