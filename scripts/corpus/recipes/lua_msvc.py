"""PUC Lua built with MSVC, beside the MinGW builds of the same tarballs.

data/Lua carries only MinGW artefacts, and Lua-embedding tooling on Windows
is mostly MSVC-built, so the compiler the corpus answers a Lua sighting with
is currently the less likely one.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

Lua is the one family here with no MSVC build file in the tree at the version
that matters most - but upstream demonstrates the compile itself. 5.1.5 ships
``etc/luavs.bat`` [read, from the pinned tarball]:

    set MYCOMPILE=cl /nologo /MD /O2 /W3 /c /D_CRT_SECURE_NO_DEPRECATE
    set MYLINK=link /nologo
    cd src
    %MYCOMPILE% /DLUA_BUILD_AS_DLL l*.c
    del lua.obj luac.obj
    %MYLINK% /DLL /out:lua51.dll l*.obj
    %MYCOMPILE% /DLUA_BUILD_AS_DLL lua.c
    %MYLINK% /out:lua.exe lua.obj lua51.lib

5.4.8 ships no such script and has no ``etc/`` directory at all - src/ is 30
.c files and a GNU Makefile [read, from the pinned tarball] - so the same two
commands are written out for it. That is the same kind of hand-written line
the sqlite3 recipe already carries, not a patch to upstream: no file in the
source tree is touched.

Where this deliberately departs from luavs.bat: that script builds lua51.dll
and then links a thin lua.exe against it, so its lua.exe holds a few hundred
bytes of frontend and nothing else. The MinGW recipe's artefact is the
statically linked ``src/lua.exe`` from ``make generic`` - the whole
interpreter in one image, which is also how Lua is embedded in real tooling -
and the point of an MSVC twin is that it pairs with that artefact. So the
compile drops /DLUA_BUILD_AS_DLL and every object but luac.obj is linked
straight into lua.exe.

Both Windows configurations are upstream's own and need no help: 5.1.5's
luaconf.h defines LUA_WIN from _WIN32 and 5.4.8's defines LUA_USE_WINDOWS
the same way, with lprefix.h defining _CRT_SECURE_NO_WARNINGS for itself
[read, both tarballs].

5.3.6 is left out: it is the third of three versions and adds no new build
question, only build time.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# The flags are luavs.bat's, plus /Zi and a shared /Fd. MSVC keeps symbols in
# a PDB rather than in a COFF symbol table, so without one SMDA would recover
# ~600 anonymous functions and smdaify would reject the build; build.py fails
# a recipe whose declared PDB is missing, which is what makes that a build
# error rather than a silently poor artefact.
#
# /MD is upstream's own choice here and is kept for the reason vxapi.py
# records: cl's default /MT links the CRT in, and that build came back 46%
# MSVC C runtime by function count, all of it duplicating data/MSVC.
#
# cl expands the l*.c wildcard itself - that is what luavs.bat relies on - and
# writes one .obj per source into the working directory.
_COMPILE = ('cl /nologo /c /O2 /MD /W3 /Zi /Fdlua.pdb '
            '/D_CRT_SECURE_NO_DEPRECATE l*.c')

# luac.c carries its own main(); it is the compiler frontend, not part of the
# interpreter. luavs.bat deletes the same object for the same reason. lua.obj
# is kept, unlike in luavs.bat, because it is this executable's entry point.
_DROP_LUAC = "del luac.obj"

# link.exe expands wildcards in file names as well (documented, and luavs.bat
# links "l*.obj" this way).
#
# /Brepro drops the build timestamp MSVC stamps into the PE header, without
# which two runs over identical source record different sha256s. /OPT:NOREF
# keeps routines nothing references and /OPT:NOICF keeps two routines that
# compiled to identical bodies apart - folding them cost VX-API its
# StringConcat/StringCopy pair. link /DEBUG is documented to imply both, but
# the corpus says what it wants rather than relying on that.
#
# The link's PDB is named the same as the compile's /Fd, which is what
# vxapi.py does over 251 translation units and what produced its two green
# artefacts.
_LINK = ('link /nologo /DEBUG /Brepro /OPT:NOREF /OPT:NOICF '
         '/PDB:lua.pdb /OUT:lua.exe l*.obj')

_FLAGS = ("/O2 /MD /W3 /Zi (etc/luavs.bat's flags plus /Zi); "
          "/DEBUG /Brepro /OPT:NOREF /OPT:NOICF at link; statically linked "
          "interpreter, not linked against lua51.dll")


def _lua_msvc(version, sha256):
    return Recipe(
        family="Lua",
        version=version,
        upstream="https://www.lua.org/ftp/",
        license="MIT",
        # The same tarball and digest the MinGW recipe pins, so the two
        # artefacts differ in the compiler and nothing else.
        source=Source(url="https://www.lua.org/ftp/lua-%s.tar.gz" % version,
                      sha256=sha256),
        build=[
            BuildStep(_COMPILE, cwd="src"),
            BuildStep(_DROP_LUAC, cwd="src"),
            BuildStep(_LINK, cwd="src"),
            # A missing artefact is reported by build.py with the path it
            # expected and nothing else. This costs a second and puts the
            # names the build actually produced into the log the workflow
            # prints on failure.
            BuildStep("dir", cwd="src", allow_failure=True),
        ],
        artifacts=[Artifact(path="src/lua.exe", component="lua.exe",
                            pdb="src/lua.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS,
        notes="The same artefact the MinGW recipe produces - the statically "
              "linked interpreter executable, not upstream luavs.bat's "
              "lua51.dll plus a frontend - so the pair differs only in the "
              "compiler. Built against the DLL runtime, so the MSVC C runtime "
              "is imported rather than linked in and stays attributed to "
              "data/MSVC; the MinGW artefact, by contrast, carries mingw's "
              "own runtime, which the glue filter removes by name. No "
              "dependencies: Lua links only the CRT.",
    )


RECIPES = {
    # The LuaJIT-ABI twin, still the most common embedded Lua in tooling, and
    # the one version whose MSVC compile upstream itself demonstrates.
    "Lua_5.1.5_msvc": _lua_msvc(
        "5.1.5",
        "2640fc56a795f29d28ef15e13c34a47e223960b0240e8cb0a82d9b0738695333"),
    # Current series, and the direct counterpart of the newest MinGW artefact.
    "Lua_5.4.8_msvc": _lua_msvc(
        "5.4.8",
        "4f18ddae154e793e46eeab727c59ef1c0c0c2b744e7b94219710d76f530629ae"),
}
