"""Duktape - the embeddable ECMAScript engine, third script engine here after
Lua and LuaJIT (backlog issue #87).

2.6.0 is the release MeshAgent vendors: its `microscript/duktape.h` opens with
"Duktape public API for Duktape 2.6.0" and defines `DUK_VERSION 20600L`.
MeshAgent compiles that duktape.c into the agent next to its own bindings, so
the engine bytes an analyst meets in the field are the ones built here.

No configure step. Issue #87 expected one, because the git tree needs
`tools/configure.py` to produce a duktape.c, but the *release tarball* is the
output of that step already: `src/duktape.c`, `duktape.h` and `duk_config.h`
(default configuration, platform autodetected) ship inside it, which is also
what MeshAgent copied. Running configure.py over `src-input/` again would
produce the same combined file from the same inputs, and this tarball is the
distribution upstream tells embedders to use, so it is compiled as shipped.
Nothing is patched.

Shape: one shared library, `duktape.dll`, from the single translation unit
with no flags beyond the optimisation level. The tarball has no driver (the
`examples/cmdline` `duk` shell needs four `extras/` modules and pulls stdio
glue the corpus would then have to subtract), and a lone duktape.c has no
`main`, so a DLL is the same way sqlite3 and zlib are covered. It needs no
`__declspec` or export list: `DUK_EXTERNAL` is plain `extern` on GCC, MinGW's
default of exporting every global applies, and the DLL exports all of the
`duk_*` API plus the internals.

Flags: `-Os`, because that is what upstream's own `Makefile.cmdline` and
`Makefile.sharedlibrary` use, with `-std=c99` as there. Duktape's code is
dispatch-heavy (the bytecode executor is one very large function), so the
level changes the emitted shape: for the 2.6.0 DLL `-Os` gives 711 KB and
`-O2` 873 KB on both architectures. `-O2` is not built as a second variant;
the corpus's `-O2` convention is not upstream's here. Symbols survive because
nothing strips (STRIP is `true` in the toolchain environment and the compile
line has no `-s`): 946 of 966 x64 functions and 973 of 975 x86 are named.

Glue the baseline does not catch. The DLL links a few C library bodies
statically that the probes never reach, and they sit under this family's name:
`snprintf`, `sprintf`, `sscanf` (mingw inline wrappers, 7 to 14 instructions),
`cbrt` (113 to 119 instructions) and `log2` (24 to 31), plus a one-instruction
`_setjmp`. Duktape uses them for number formatting and Math.cbrt/log2. They
are left in rather than hand-removed, because the baseline is a shared measured
constant; they number six or fewer per artefact.

Versions: 2.6.0 is what MeshAgent vendors. 2.7.0 is added because it measurably
differs: identical function names, but about a fifth of the PicHashes change.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


def _duktape(version, sha256, notes=""):
    return Recipe(
        family="Duktape",
        version=version,
        upstream="https://github.com/svaarala/duktape",
        license="MIT",
        source=Source(
            url="https://github.com/svaarala/duktape/releases/download/"
                "v%s/duktape-%s.tar.xz" % (version, version),
            sha256=sha256),
        build=[BuildStep("{cc} -Os -std=c99 -shared -o duktape.dll src/duktape.c")],
        artifacts=[Artifact(path="duktape.dll", component="duktape.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-Os -std=c99 (upstream Makefile.cmdline), default duk_config.h",
        notes=notes or "Built from the upstream release tarball's pre-generated "
                       "src/duktape.c; no configure step is needed or run.",
    )


RECIPES = {
    # The version MeshAgent vendors.
    "Duktape_2.6.0": _duktape(
        "2.6.0", "96f4a05a6c84590e53b18c59bb776aaba80a205afbbd92b82be609ba7fe75fa7"),
    # Latest 2.x release. Same function names as 2.6.0 (975 x86 / 965 x64
    # against 975 / 966), but 200 of 900 x86 and 199 of 860 x64 distinct
    # PicHashes are new (700 and 661 shared), so it is not a near-duplicate.
    "Duktape_2.7.0": _duktape(
        "2.7.0", "90f8d2fa8b5567c6899830ddef2c03f3c27960b11aca222fa17aa7ac613c2890"),
}
