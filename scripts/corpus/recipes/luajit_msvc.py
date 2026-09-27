"""LuaJIT built with MSVC, beside the MinGW builds of the same commits.

The lua51.dll and lua51.lib that LuaJIT-based Windows tooling ships - TINN
and its descendants, which is what issue #1 points at - are MSVC artefacts,
so for this family the MSVC build is the closer match to the thing that
actually turns up. data/LuaJIT carries only MinGW builds.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

This calls upstream's own ``src/msvcbuild.bat`` rather than hand-rolling the
build, which matters more here than elsewhere: the interpreter core is
DynASM assembly generated at build time by a host minilua and buildvm that
the script builds first, and re-spelling that chain by hand would be a
second, unsupported build system for this corpus to own. Running upstream's
script is not a patch to upstream.

Read in msvcbuild.bat at both pinned commits (they differ in three lines
only, all noted below):

  * ``LJCOMPILE=cl /nologo /c /O2 /W3 /D_CRT_SECURE_NO_DEPRECATE
    /D_CRT_STDIO_INLINE=__declspec(dllexport)__inline``, and the DLL path
    compiles with ``/MD /DLUA_BUILD_AS_DLL`` on top of that - so the release
    build is already /MD and needs no override.
  * the ``debug`` argument appends ``/Zi`` to the compile and ``/debug`` to
    the link, and changes nothing else. It is not a debug build: /O2 and /MD
    stay. That is the whole reason it is passed here - it is upstream's own
    way of asking for the PDB this corpus requires.
  * the target architecture is detected by running the freshly built host
    ``minilua`` and testing errorlevel 8, so the same command line serves the
    x86 and x64 legs; x86 additionally gets ``/arch:SSE2``.
  * the default build produces ``lua51.dll`` in src/ from lj_*.obj and
    lib_*.obj, then links luajit.exe against lua51.lib. The link passes no
    ``/PDB:``, so the linker names the PDB after the output - ``lua51.pdb``,
    next to the DLL - and luajit.exe's own PDB is luajit.pdb and does not
    collide with it.
  * the script ends with ``del *.obj *.manifest minilua.exe buildvm.exe``,
    which leaves the DLL and the PDBs in place.

What the script does not do is /Brepro, and on the 2.1.0-beta3 path it asks
for ``/opt:ref /opt:icf``, which is the folding this corpus spends effort
avoiding. Both are corrected through ``_LINK_`` rather than by editing the
script: link.exe "prepends the options and arguments defined in the LINK
environment variable and appends the options and arguments defined in the
_LINK_ environment variable to the command line arguments before
processing", and "if an option is repeated with different arguments, the
last one processed takes precedence" [Microsoft, "MSVC linker reference"].
Appended therefore beats upstream's own /opt:icf. ``@setlocal`` at the top
of the script scopes the variables the script sets; it does not drop ones it
inherited.

2.1-rolling is left out. Its msvcbuild.bat sets /Zi and /DEBUG
unconditionally, so it would need no ``debug`` argument, but it also runs
``git show -s --format=%ct`` (or reads ``.relver``) and then
``minilua host\\genversion.lua`` before it can compile - a build-time
dependency on the checkout's git metadata that the other two commits do not
have, and one more thing to be wrong about on a first CI cycle.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Appended after msvcbuild.bat's own link options, so these win where they
# disagree:
#   /DEBUG      - restated; already there from the "debug" argument, and the
#                 one flag whose absence build.py turns into a hard failure.
#   /Brepro     - without it MSVC stamps the PE with the build time and two
#                 runs over identical source record different sha256s; the
#                 BlackBone x86 DLL did exactly that between two green runs.
#   /OPT:NOREF  - keeps routines nothing references, which is what the MinGW
#                 build (no --gc-sections) also keeps.
#   /OPT:NOICF  - keeps two routines that compiled to identical bodies apart;
#                 folding them cost VX-API its StringConcat/StringCopy pair.
#   /INCREMENTAL:NO - /INCREMENTAL is the default once /DEBUG is given, and an
#                 incremental link routes calls through jump thunks. beta3's
#                 script passes /incremental:no itself, 2.0.5's does not.
# These also reach the minilua.exe and buildvm.exe links, which is harmless:
# those are host tools that the script deletes when it is done.
_LINK_ENV = {"_LINK_": "/DEBUG /Brepro /OPT:NOREF /OPT:NOICF /INCREMENTAL:NO"}

_FLAGS = ("/O2 /W3 /MD /Zi (upstream src/msvcbuild.bat, \"debug\" argument - "
          "the release build plus /Zi, not a debug CRT); /DEBUG /Brepro "
          "/OPT:NOREF /OPT:NOICF /INCREMENTAL:NO at link, appended through "
          "_LINK_ over upstream's own link options")


def _luajit_msvc(version, git_ref, notes):
    return Recipe(
        family="LuaJIT",
        version=version,
        upstream="https://github.com/LuaJIT/LuaJIT",
        license="MIT",
        # The same commits the MinGW recipe pins - upstream carries no git
        # tags and the release tarballs are gone from luajit.org, so a
        # version is the commit that set the version string.
        source=Source(git_url="https://github.com/LuaJIT/LuaJIT.git",
                      git_ref=git_ref),
        build=[
            BuildStep("msvcbuild.bat debug", cwd="src", env=_LINK_ENV),
            # msvcbuild.bat's failure path echoes a banner and falls off the
            # end, and @echo resets errorlevel, so a failed build can still
            # exit 0. build.py's missing-artefact check is what catches that;
            # this listing puts what src/ actually holds into the log the
            # workflow prints, so a failure is one cycle to diagnose.
            BuildStep("dir", cwd="src", allow_failure=True),
        ],
        artifacts=[Artifact(path="src/lua51.dll", component="lua51.dll",
                            pdb="src/lua51.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS,
        notes=notes,
    )


_SHARED_NOTES = (
    "Built by upstream's own src/msvcbuild.bat, so the DynASM interpreter "
    "core is generated exactly as upstream generates it. That core is "
    "hand-written assembly and is the same code the MinGW artefact carries; "
    "what differs between the two is the surrounding C - the JIT, GC, FFI "
    "and library glue - which is the bulk of the function count. Built "
    "against the DLL runtime (/MD, upstream's own setting on this path), so "
    "the MSVC C runtime is imported rather than linked in and stays "
    "attributed to data/MSVC. No dependencies.")


RECIPES = {
    # The most widely redistributed LuaJIT of the last decade, and what TINN's
    # own committed lua51.lib turns out to contain.
    "LuaJIT_2.1.0-beta3_msvc": _luajit_msvc(
        "2.1.0-beta3", "8271c643c21d1b2f344e339f559f2de6f3663191",
        _SHARED_NOTES + " Upstream's script asks for /opt:ref /opt:icf here; "
        "this recipe overrides both through _LINK_ so that unreferenced and "
        "identically-compiled routines survive as separate reference "
        "samples."),
    # Last stable 2.0; a different interpreter core rather than a
    # near-duplicate. Its msvcbuild.bat differs from beta3's only in having
    # no gc64 option, no /arch:SSE2 on x86, and a bare /debug with no /opt or
    # /incremental settings.
    "LuaJIT_2.0.5_msvc": _luajit_msvc(
        "2.0.5", "0bf80b07b0672ce874feedcc777afe1b791ccb5a",
        _SHARED_NOTES + " Upstream's script passes only /debug on this "
        "commit, so /INCREMENTAL:NO, /OPT:NOREF and /OPT:NOICF all come from "
        "this recipe's _LINK_ rather than from upstream."),
}
