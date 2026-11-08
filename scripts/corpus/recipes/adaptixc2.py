"""AdaptixC2 beacon loader stub - the committed blob (mcrit-data issue #80).

In scope by maintainer decision. The beacon agent itself is **not** buildable
as upstream ships it, for three independent reasons read out of the tree at
``a4b80bf370f704d6843e69433bfb5c06274f57df`` and recorded in
``scripts/corpus/README.md``: all 178 lines of ``src_beacon/Makefile`` compile
with ``-c`` and there is no link rule, the link that does happen is performed
by the Go teamserver and needs a generated operator payload configuration
(``-DPROFILE='"<serialised agent profile>"'``, which ``files/config.tpl``
provides no fallback for), and upstream's own link line is
``-Os -s -Wl,-s,--gc-sections``, which strips the symbol table.

What *is* reachable is the loader shellcode upstream commits and
``pl_main.go`` prepends to every built DLL: ``files/stub.x86.bin`` and
``files/stub.x64.bin``, 1023 bytes each. That blob is what lands first on a
target, so it is worth matching, and it needs no link, no configuration and
no build - it is already compiled and already in the repository, the same
situation as sRDI's and donut's committed blobs.

It was measured and left out once before, for one reason only: ``Recipe.slug``
hardcoded ``msvc`` as the producer of every blob. That is right for the three
blob families already here and wrong for this one, so the stem would have
carried a false claim about the compiler. ``Artifact.producer`` is what fixes
that, and this is the recipe it was added for.

**Why ``producer="mingw"`` and not a version.** Upstream publishes no source
and no build script for the stub, so the exact compiler cannot be pinned -
but the family can be, from two independent readings:

  * the blobs pad with GCC's nops and not MSVC's. x64 carries
    ``66 2e 0f 1f 84 00`` (``nopw %cs:0x0(%rax,%rax,1)``) and x86 carries
    ``66 90`` (``xchg %ax,%ax``); neither blob contains a single ``cc cc cc
    cc`` run, which is what MSVC leaves between functions.
  * ``src_beacon/Makefile`` sets ``CXX_X64 := x86_64-w64-mingw32-g++`` and
    ``CXX_X86 := i686-w64-mingw32-g++``, so everything upstream compiles for
    Windows in this tree is compiled with MinGW.

So the producer segment says ``mingw`` with no version digits, which is a
statement about the compiler family and deliberately not about any toolchain
this corpus registers. Guessing ``mingw13`` would claim a version nobody
published; leaving it to default would have printed ``msvc``, which the
padding contradicts.

``min_functions=7``: the measured count, and the whole of each blob. Seven is
below ``config.MIN_USEFUL_FUNCTIONS`` (8) for the same reason 4g3nt47's
Obfuscator is - the thing genuinely contains that many - and not because a
build came out short. There is nothing truncated here: both blobs are
committed upstream at their full 1023 bytes and both clear
``MIN_USEFUL_BLOB_INSTRUCTIONS`` comfortably, at 356 instructions on x86 and
314 on x64.

``min_named_ratio=0``: raw position-independent code has no symbol table of
any kind to recover a name from.
"""

from ..recipe import Artifact, Recipe, Source


_FILES = "AdaptixServer/extenders/beacon_agent/src_beacon/files"


RECIPES = {
    "AdaptixC2_2026-03-04": Recipe(
        family="AdaptixC2",
        version="2026-03-04",
        upstream="https://github.com/Adaptix-Framework/AdaptixC2",
        license="GPL-3.0",
        source=Source(
            git_url="https://github.com/Adaptix-Framework/AdaptixC2.git",
            git_ref="a4b80bf370f704d6843e69433bfb5c06274f57df"),
        # Nothing to do: the blobs are committed, so the artefacts are read
        # straight out of the checkout. sRDI and donut need an extraction step
        # only because their blobs are buried in a Python literal and a C
        # array respectively; these two are plain files.
        build=[],
        artifacts=[
            Artifact(path="%s/stub.x86.bin" % _FILES, component="stub_x86",
                     is_blob=True, bitness=32, producer="mingw"),
            Artifact(path="%s/stub.x64.bin" % _FILES, component="stub_x64",
                     is_blob=True, bitness=64, producer="mingw"),
        ],
        # Selects which machine reads the blobs out of the checkout, nothing
        # more; the bitness is stated per artefact because raw bytes carry no
        # container header to read it from. The component repeats the
        # architecture, as sRDI's ShellcodeRDI_x86/_x64 do, because
        # refresh_provenance resolves a committed entry back to its artefact
        # by component alone and two artefacts may not share one.
        toolchains=["mingw_x64"],
        build_flags="MinGW GCC, flags not published (committed upstream)",
        min_functions=7,
        min_named_ratio=0,
        notes="The loader shellcode upstream commits and its Go teamserver "
              "prepends to every built beacon DLL, taken as committed. The "
              "beacon agent itself is not built: src_beacon/Makefile has no "
              "link rule, the link needs a generated operator payload "
              "configuration, and upstream's link line strips symbols. "
              "Nothing is executed and no payload is configured.",
    ),
}
