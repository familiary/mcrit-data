"""PUC Lua - the reference interpreter, complementing the LuaJIT coverage.

Plenty of Lua-embedding tooling links the reference implementation rather than
LuaJIT, and the two share essentially no machine code, so both are needed to
answer issue #1's "get some LUA coverage".

Built through the `generic` target rather than `mingw`. The `mingw` target
re-invokes make with `SYSLDFLAGS=-s` and `RANLIB=strip --strip-unneeded` as
its own command-line overrides, which beat anything passed from outside, so
it always strips; the resulting DLL came back with 17% of functions named.
`generic` does not strip, and its statically linked lua.exe is in any case
closer to how Lua is embedded in real tooling than a DLL is.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


def _lua(version, sha256):
    return Recipe(
        family="Lua",
        version=version,
        upstream="https://www.lua.org/ftp/",
        license="MIT",
        source=Source(url="https://www.lua.org/ftp/lua-%s.tar.gz" % version,
                      sha256=sha256),
        build=[
            BuildStep("make clean", allow_failure=True),
            BuildStep('make generic CC={cc} AR="{ar} rcu" RANLIB={ranlib}'),
        ],
        artifacts=[Artifact(path="src/lua.exe", component="lua.exe")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 (upstream default)",
    )


RECIPES = {
    # The LuaJIT-ABI twin, still the most common embedded Lua in tooling.
    "Lua_5.1.5": _lua("5.1.5",
                      "2640fc56a795f29d28ef15e13c34a47e223960b0240e8cb0a82d9b0738695333"),
    # Third VM generation, widely embedded through the 2010s.
    "Lua_5.3.6": _lua("5.3.6",
                      "fc5fd69bb8736323f026672b1b7235da613d7177e72558893a0bdcd320466d60"),
    # Current series.
    "Lua_5.4.8": _lua("5.4.8",
                      "4f18ddae154e793e46eeab727c59ef1c0c0c2b744e7b94219710d76f530629ae"),
}
