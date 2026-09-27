"""LuaJIT - the runtime behind the Lua coverage asked for in issue #1.

Issue #1 points at TINN because Sandman/LuaDream tooling was built on it, but
TINN itself is Lua source plus a thin frontend: the reusable machine code an
analyst meets is the LuaJIT interpreter and JIT core that gets statically
linked in. TINN cannot be rebuilt here anyway (MSVC-only build script, no
LuaJIT source in tree), so LuaJIT is built directly instead.

Upstream carries no git tags and the release tarballs are gone from
luajit.org, so versions are pinned by the commit that set the version string.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


def _luajit(version, git_ref):
    return Recipe(
        family="LuaJIT",
        version=version,
        upstream="https://github.com/LuaJIT/LuaJIT",
        license="MIT",
        source=Source(git_url="https://github.com/LuaJIT/LuaJIT.git", git_ref=git_ref),
        # HOST_CC has to match the target pointer size because the build runs
        # its own buildvm on the host. TARGET_STRIP=@: disables the default
        # strip, which otherwise cuts recovered symbols from ~4400 to ~90.
        build=[
            BuildStep("make clean", allow_failure=True),
            BuildStep('make -j$(nproc) HOST_CC="{hostcc}" CROSS={prefix} '
                      'TARGET_SYS=Windows BUILDMODE=dynamic TARGET_STRIP=@:'),
        ],
        artifacts=[Artifact(path="src/lua51.dll", component="lua51.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 -fomit-frame-pointer (upstream default)",
        requires=["gcc"],
        notes="The interpreter core is hand-written DynASM assembly and is "
              "unaffected by CFLAGS, so no optimization sweep is worthwhile.",
    )


RECIPES = {
    # The most widely redistributed LuaJIT of the last decade, and what TINN's
    # own committed lua51.lib turns out to contain.
    "LuaJIT_2.1.0-beta3": _luajit(
        "2.1.0-beta3", "8271c643c21d1b2f344e339f559f2de6f3663191"),
    # Last stable 2.0; a different interpreter core rather than a near-duplicate.
    "LuaJIT_2.0.5": _luajit("2.0.5", "0bf80b07b0672ce874feedcc777afe1b791ccb5a"),
    # Rolling head, covering everything built since upstream dropped releases.
    "LuaJIT_2.1-rolling-2026-09-08": _luajit(
        "2.1-rolling-2026-09-08", "c6ffc141a8762b41703f9287d63d93622a13dd8f"),
}
