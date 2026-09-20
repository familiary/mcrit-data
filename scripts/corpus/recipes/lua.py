"""PUC Lua - the reference interpreter, complementing the LuaJIT coverage.

Plenty of Lua-embedding tooling links the reference implementation rather than
LuaJIT, and the two share essentially no machine code, so both are needed to
answer issue #1's "get some LUA coverage".
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


def _lua(version, sha256, dll_name):
    return Recipe(
        family="Lua",
        version=version,
        upstream="https://www.lua.org/ftp/",
        license="MIT",
        source=Source(url="https://www.lua.org/ftp/lua-%s.tar.gz" % version,
                      sha256=sha256),
        # Upstream's mingw target hardcodes RANLIB to a strip invocation and
        # passes -s at link time; both have to be neutralised or the report
        # comes back without a single function name.
        build=[
            BuildStep("make clean", allow_failure=True),
            BuildStep('make mingw CC={cc} AR="{ar} rcu" RANLIB={ranlib} '
                      'SYSLDFLAGS=""'),
        ],
        artifacts=[Artifact(path="src/%s" % dll_name, component=dll_name)],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 (upstream default)",
    )


RECIPES = {
    # The LuaJIT-ABI twin, still the most common embedded Lua in tooling.
    "Lua_5.1.5": _lua("5.1.5",
                      "2640fc56a795f29d28ef15e13c34a47e223960b0240e8cb0a82d9b0738695333",
                      "lua51.dll"),
    # Third VM generation, widely embedded through the 2010s.
    "Lua_5.3.6": _lua("5.3.6",
                      "fc5fd69bb8736323f026672b1b7235da613d7177e72558893a0bdcd320466d60",
                      "lua53.dll"),
}
