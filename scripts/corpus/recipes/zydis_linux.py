"""Zydis and Zycore built for Linux.

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

Linux specifics. Zydis is a portable C library used on Linux as much as on
Windows, which is why an ELF reference exists at all; it is no evidence for
the ValleyRAT chain, and the Hidden comparison above is why the ELF builds
share no PicHash with Hidden.sys. Built as a shared object, -fPIC and
-fvisibility=hidden, as every ELF artefact in this corpus is (README, "The
Linux half"): a -shared object links glibc dynamically so none of it enters
the image, and hidden visibility keeps calls inside the object direct. The
whole of both archives is included with --whole-archive. Zydis 3.1.0 and 4.1.1
both configure under CMake with no change to upstream.

The PE and ELF builds share no PicHash on x64 (System V against the Windows
x64 convention changes every body) and 51 of 219 on x86 for 3.1.0, 55 of 226
for 4.1.1, so the ELF artefact is a reference of its own.

Counts, kept + removed = total, ten instructions or more in brackets: 3.1.0
x86 329 + 5 = 334 (245), x64 313 + 6 = 319 (207); 4.1.1 x86 341 + 5 = 346
(255), x64 328 + 6 = 334 (216). Unnamed functions are PLT stubs for libc.

Glue survivors, by name and PicHash, on x86 only, as the README describes for
every 32-bit ELF artefact: _init, _fini, register_tm_clones,
deregister_tm_clones, __do_global_dtors_aux, __stack_chk_fail_local and the
__x86.get_pc_thunk.bp, .cx and .si helpers. 3.1.0: _init
12404726299444768590, _fini 7777538043399287326, register_tm_clones
12546449489698028162, deregister_tm_clones 15216951980277319870,
__do_global_dtors_aux 10903772813783125782, __stack_chk_fail_local
3050345796936069158; 4.1.1: _init 12745444033352437030, _fini
12697929591629197172, register_tm_clones 2042002748446341906,
deregister_tm_clones 14631725823459865394, __do_global_dtors_aux
16850122468125795564, __stack_chk_fail_local 15162959745759183679. The three
get_pc_thunk helpers are the same body in both (8978313489863221434,
8547562632060595966, 11029392869810893897). The GOT delta is baked into the
others, so their PicHash moves between images, which is why a filter matching
symbol and PicHash leaves them.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_POLICY_VERSION_MINIMUM=3.5 "
          "-DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON "
          '-DCMAKE_C_FLAGS="{archflag} -fvisibility=hidden" '
          '-DCMAKE_CXX_FLAGS="{archflag} -fvisibility=hidden" '
          "-DZYDIS_BUILD_EXAMPLES=OFF -DZYDIS_BUILD_TOOLS=OFF")
_LINK = ("{cc} {archflag} -shared -o libzydis.so -Wl,--whole-archive "
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
        artifacts=[Artifact(path="libzydis.so", component="libzydis.so")],
        toolchains=["linux_x86", "linux_x64"],
        build_flags="-O3 -fPIC -fvisibility=hidden (CMake Release) static "
                    "archives, linked into one shared object with "
                    "--whole-archive",
        notes=notes,
    )


_COMMON = ("The ELF build of the same tag as the PE artefacts of this "
           "family: Zydis and its Zycore submodule as static archives, "
           "linked into one shared object with --whole-archive. A portable "
           "library built for a platform it is used on, not evidence for "
           "the Windows sample chain. ")

RECIPES = {
    "Zydis_3.1.0_linux": _zydis(
        "3.1.0", "v3.1.0",
        _COMMON + "Measured: x86 329 functions kept of 334, x64 313 of 319, "
        "245 and 207 of them ten instructions or more. The x86 image keeps "
        "the 32-bit PIC link glue the filter cannot match by PicHash."),
    "Zydis_4.1.1_linux": _zydis(
        "4.1.1", "v4.1.1",
        _COMMON + "Measured: x86 341 functions kept of 346, x64 328 of 334, "
        "255 and 216 of them ten instructions or more. The x86 image keeps "
        "the 32-bit PIC link glue the filter cannot match by PicHash."),
}
