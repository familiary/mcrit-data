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
`-O2` 873 KB on both architectures. Symbols survive because
nothing strips (STRIP is `true` in the toolchain environment and the compile
line has no `-s`): 942 of 962 x64 functions and 967 of 969 x86 are named.

Glue the baseline once missed. The DLL links a few C library bodies
statically that the probes did not reach at first: `snprintf`, `sprintf`,
`sscanf` (mingw inline wrappers, 7 to 14 instructions), `cbrt` (113 to 119
instructions), `log2` (24 to 31) and a one-instruction `_setjmp`/`__setjmp3`.
Duktape uses them for number formatting and Math.cbrt/log2. The MinGW libc
baseline now probes them and the refilter removed them (4 per x64 artefact,
6 per x86; `sprintf` and `sscanf` are not separate functions on x64), so the
artefacts hold 962 and 961 functions on x64 and 969 on x86.

The -O2 variant (backlog #87). The tracker asks for 2.6.0 at -O2, so the
2.6.0 recipe builds a second DLL from the same translation unit,
`duktape-O2.dll` (`-O2 -std=c99`, nothing else changed), filed beside
`duktape.dll`; 2.7.0 has no -O2 build. Kept + removed = image total: x86
1239 + 181 = 1420, x64 868 + 176 = 1044 (the -Os images are 969 + 184 = 1153
and 962 + 179 = 1141). The x86 count is higher because GCC at -O2 splits the
error paths out: 380 of its functions are `.cold` fragments of two to five
instructions, which the x64 image does not carry as separate functions. All
but 2 (x86) and 20 (x64) kept functions are named. PicHash overlap with the
-Os sibling, functions of 10+ instructions: x86 1 shared of 720 (-O2) and 796
(-Os) distinct hashes, x64 6 of 709 and 720; at any size 6 and 42. The level
changes nearly every function body, so the two builds are separate data.

Versions: 2.6.0 is what MeshAgent vendors. 2.7.0 is added because it measurably
differs: identical function names, but about a fifth of the PicHashes change.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


def _duktape(version, sha256, notes="", with_o2=False):
    build = [BuildStep("{cc} -Os -std=c99 -shared -o duktape.dll src/duktape.c")]
    artifacts = [Artifact(path="duktape.dll", component="duktape.dll")]
    if with_o2:
        # The level backlog #87 names. Same translation unit, same -std, only
        # the optimisation level differs from duktape.dll.
        build.append(BuildStep(
            "{cc} -O2 -std=c99 -shared -o duktape-O2.dll src/duktape.c"))
        artifacts.append(Artifact(
            path="duktape-O2.dll", component="duktape-O2.dll",
            build_flags="-O2 -std=c99 (the level backlog #87 names; "
                        "duktape.dll is upstream's -Os), default "
                        "duk_config.h"))
    return Recipe(
        family="Duktape",
        version=version,
        upstream="https://github.com/svaarala/duktape",
        license="MIT",
        source=Source(
            url="https://github.com/svaarala/duktape/releases/download/"
                "v%s/duktape-%s.tar.xz" % (version, version),
            sha256=sha256),
        build=build,
        artifacts=artifacts,
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-Os -std=c99 (upstream Makefile.cmdline), default duk_config.h",
        notes=notes or "Built from the upstream release tarball's pre-generated "
                       "src/duktape.c; no configure step is needed or run.",
    )


RECIPES = {
    # The version MeshAgent vendors.
    "Duktape_2.6.0": _duktape(
        "2.6.0", "96f4a05a6c84590e53b18c59bb776aaba80a205afbbd92b82be609ba7fe75fa7",
        with_o2=True),
    # Latest 2.x release. Same function names as 2.6.0 (969 x86 / 961 x64
    # against 969 / 962), but 200 of 895 x86 and 199 of 857 x64 distinct
    # PicHashes are new (695 and 658 shared), so it is not a near-duplicate.
    "Duktape_2.7.0": _duktape(
        "2.7.0", "90f8d2fa8b5567c6899830ddef2c03f3c27960b11aca222fa17aa7ac613c2890"),
}


# The final sweep.
#
# 2.7.0 at -O2, the level backlog #87 names, as its own recipe so that the
# committed -Os duktape.dll of 2.7.0 is not rebuilt.
def _o2_only(version, sha256):
    recipe = _duktape(version, sha256, with_o2=True)
    recipe.build = recipe.build[1:]
    recipe.artifacts = recipe.artifacts[1:]
    # Its own version slug: refresh_provenance.py tells recipes apart by
    # (version, toolchain), and the -Os recipe of 2.7.0 already holds that.
    recipe.version = version + "-O2"
    return recipe


# MeshAgent's vendored copy (Ylianst/MeshAgent microscript/duktape.c, which
# defines DUK_VERSION 20600L, at the commit the MeshAgent recipes pin). Its
# duktape.h adds DUK_USE_EXEC_TIMEOUT_CHECK ILibDuktape_EXEC_TIMEOUT_CHECK, a
# callback the agent executable defines, so a standalone DLL has one
# unresolved import. As in MeshAgent's own Windows build (one Duktape DLL per
# executable, see meshagent.py) it is resolved through an import library of
# the host, generated from a two-line .def, so no stub code enters the image:
# the DLL imports the callback from MeshAgent.exe. The defines are the ones
# the MeshAgent recipes compile the engine with; -O2 as there. Nothing in the
# tree is edited.
MESHAGENT_REF = "26846b1c7f0841d71938f6bebc96eef5a947d217"
MESHAGENT_DUK_DEFS = ("-DDUK_USE_DATE_NOW_WINDOWS -DDUK_USE_DEBUGGER_SUPPORT "
                      "-DDUK_USE_INTERRUPT_COUNTER -DDUK_USE_DEBUGGER_INSPECT "
                      "-DDUK_USE_DEBUGGER_PAUSE_UNCAUGHT -DDUK_USE_DEBUGGER_DUMPHEAP")
HOST_DEF = ("printf 'LIBRARY MeshAgent.exe\\nEXPORTS\\n"
            "ILibDuktape_EXEC_TIMEOUT_CHECK\\n' > corpus-host.def")


def _meshagent_vendored():
    return Recipe(
        family="Duktape",
        version="2.6.0-meshagent",
        upstream="https://github.com/Ylianst/MeshAgent (vendored "
                 "https://github.com/svaarala/duktape 2.6.0)",
        license="MIT (Duktape); MeshAgent is Apache-2.0",
        source=Source(git_url="https://github.com/Ylianst/MeshAgent.git",
                      git_ref=MESHAGENT_REF),
        build=[BuildStep(HOST_DEF),
               BuildStep("{prefix}dlltool -d corpus-host.def -l libcorpus-host.a"),
               BuildStep("{cc} -shared -O2 " + MESHAGENT_DUK_DEFS +
                         " microscript/duktape.c -o duktape.dll -L. -lcorpus-host")],
        artifacts=[Artifact(path="duktape.dll", component="duktape.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 and MeshAgent's DUK_USE_* defines (" + MESHAGENT_DUK_DEFS +
                    "); ILibDuktape_EXEC_TIMEOUT_CHECK imported from MeshAgent.exe "
                    "through a generated import library",
        notes="MeshAgent's vendored Duktape 2.6.0 (microscript/duktape.c and its "
              "customised duktape.h/duk_config.h) at the MeshAgent commit the "
              "MeshAgent recipes pin, compiled on its own as a DLL. The agent's "
              "exec-timeout callback is imported from the host executable as "
              "MeshAgent's own per-executable Duktape DLL does; no source is "
              "edited.",
    )


RECIPES["Duktape_2.7.0_O2"] = _o2_only(
    "2.7.0", "90f8d2fa8b5567c6899830ddef2c03f3c27960b11aca222fa17aa7ac613c2890")
RECIPES["Duktape_2.6.0_meshagent"] = _meshagent_vendored()

