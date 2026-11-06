"""miniupnpc built with MSVC, beside the MinGW builds of the same tags.

The MinGW recipe (miniupnpc.py) covers the same four tags with GCC. MSVC and
GCC compile one source to different machine code, and Windows software that
carries miniupnpc - torrent clients, game launchers, the QakBot / Pinkslipbot
proxy module - is mostly built with cl, so a sighting was answered only by
GCC code. Same pins as the MinGW recipe, git tags that resolve to immutable
commits: ``miniupnpc_2_0`` 1337158f, ``miniupnpc_2_1`` bd836936,
``miniupnpc_2_2_3`` 2df81203, ``miniupnpc_2_3_3`` bf4215a7. Upstream
publishes no checksums. No source file is patched.

Build: direct ``cl /c`` of the library's source list, then ``link /DLL`` with
upstream's own ``miniupnpc.def``. That is the MinGW build's shape (the
makefile's OBJS list, ``-DMINIUPNP_EXPORTS``, ``-DNDEBUG``,
``-D_WIN32_WINNT=0x501``, ``miniupnpc.def``), with the code generator the only
intended difference, and it avoids the problem that made the MinGW recipe
reject CMake: CMake in 2.0 and 2.2.0 compiles ``upnpc.c`` - the command line
client, ``main`` and all - into the library, and 2.1's CMake does not
configure with ``UPNPC_BUILD_STATIC=OFF``. The shipped ``msvc/`` solutions
were not used either: they target Visual Studio 2010 / 2015 toolsets. The
``.def`` is read from the upstream tree and never changed, so the export
table is the one upstream's published DLL has, and no export macro is needed
(``MINIUPNP_EXPORTS`` is nevertheless defined, as in the MinGW build, so the
declspec agrees with the def).

What the MinGW build has that this one does not: ``winres.o`` (2.2.3 and
later), the version-information resource from ``miniupnpc.rc``. It holds no
code and is left out rather than compiled with ``rc``.

``miniupnpcstrings.h`` (and ``rc_version.h`` from 2.2.3) are generated, on
Windows by running a freshly built ``wingenminiupnpcstrings.exe`` exactly as
upstream's makefile does under ``OS=Windows_NT``; here it is built with cl
into ``build-<arch>``, not into the artefact. It only fills the OS and version
strings, which are data.

Flags. The compile line is ``/c /MD /O2 /Ob2 /Zi /DNDEBUG`` (CMake's Release
set, plus /Zi for the PDB), ``/Fd`` naming the PDB; the link line is ``/DLL
/DEF:miniupnpc.def /DEBUG /INCREMENTAL:NO /Brepro /OPT:NOREF /OPT:NOICF``.
No /GL and no /LTCG. These are the flags as written in the steps below; the
build prints each command, which is where to read them back. /MD means the C
runtime is imported, so it stays attributed to data/MSVC.

Winsock and iphlpapi. The DLL links ``ws2_32.lib`` and ``iphlpapi.lib``
dynamically, as the MinGW one does with ``-lws2_32 -liphlpapi``, and has no
socket glue of its own; what is filed under the name for those imports is
thunks (see the README's treatment of glue). A ``dumpbin /exports`` step
prints the export table to the log so the count can be compared with the
MinGW artefact.

Measurements: see the end of this docstring (filled in after the first run).
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_OBJS = ["miniwget", "minixml", "igd_desc_parse", "minisoap", "minissdpc",
         "miniupnpc", "upnpreplyparse", "upnpcommands", "upnperrors",
         "connecthostport", "portlistingparse", "receivedata", "upnpdev"]


def _steps(version):
    old = version in ("2.0", "2.1")
    srcdir = "" if old else "src\\"
    objs = _OBJS if old else _OBJS + ["addr_is_reserved"]
    includes = "/I." if old else "/Iinclude /I."
    # 2.2.3 and later write rc_version.h as well.
    genargs = "miniupnpcstrings.h.in miniupnpcstrings.h"
    if not old:
        genargs += " rc_version.h"
    sources = " ".join(srcdir + o + ".c" for o in objs)
    compile_ = ("cl /nologo /c /MD /O2 /Ob2 /Zi /W3 /DNDEBUG "
                "/D_WIN32_WINNT=0x501 /DMINIUPNP_EXPORTS " + includes +
                " /Foobj-{arch}\\ /Fdbuild-{arch}\\miniupnpc.pdb " + sources)
    return [
        BuildStep("if not exist obj-{arch} mkdir obj-{arch}",
                  cwd="miniupnpc"),
        BuildStep("if not exist build-{arch} mkdir build-{arch}",
                  cwd="miniupnpc"),
        # The generator is a build tool; it is not linked into the artefact.
        BuildStep("cl /nologo /W3 /Fogen-{arch}.obj "
                  "/Febuild-{arch}\\wingenminiupnpcstrings.exe "
                  "wingenminiupnpcstrings.c", cwd="miniupnpc"),
        BuildStep("build-{arch}\\wingenminiupnpcstrings.exe " + genargs,
                  cwd="miniupnpc"),
        BuildStep(compile_, cwd="miniupnpc"),
        BuildStep("link /nologo /DLL /OUT:build-{arch}\\miniupnpc.dll "
                  "/DEF:miniupnpc.def /DEBUG "
                  "/PDB:build-{arch}\\miniupnpc.pdb /INCREMENTAL:NO /Brepro "
                  "/OPT:NOREF /OPT:NOICF obj-{arch}\\*.obj "
                  "ws2_32.lib iphlpapi.lib", cwd="miniupnpc"),
        BuildStep("dumpbin /nologo /exports build-{arch}\\miniupnpc.dll",
                  cwd="miniupnpc", allow_failure=True),
        BuildStep("dir build-{arch}", cwd="miniupnpc", allow_failure=True),
    ]


def _miniupnpc_msvc(version, git_ref):
    return Recipe(
        family="miniupnpc",
        version=version,
        upstream="https://github.com/miniupnp/miniupnp",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/miniupnp/miniupnp.git",
                      git_ref=git_ref),
        build=_steps(version),
        artifacts=[Artifact(path="miniupnpc/build-{arch}/miniupnpc.dll",
                            component="miniupnpc.dll",
                            pdb="miniupnpc/build-{arch}/miniupnpc.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi /DNDEBUG /D_WIN32_WINNT=0x501 "
                    "/DMINIUPNP_EXPORTS; link /DEF:miniupnpc.def /DEBUG "
                    "/INCREMENTAL:NO /Brepro /OPT:NOREF /OPT:NOICF",
        notes="Library only: upnpc.c and the other samples are not part of "
              "miniupnpc.dll, and the version resource is left out. Same "
              "tags as the MinGW recipe, exported through upstream's "
              "miniupnpc.def. Links ws2_32 and iphlpapi dynamically; the C "
              "runtime is imported (/MD).",
    )


RECIPES = {
    "miniupnpc_2.0_msvc": _miniupnpc_msvc("2.0", "miniupnpc_2_0"),
    "miniupnpc_2.1_msvc": _miniupnpc_msvc("2.1", "miniupnpc_2_1"),
    "miniupnpc_2.2.3_msvc": _miniupnpc_msvc("2.2.3", "miniupnpc_2_2_3"),
    "miniupnpc_2.3.3_msvc": _miniupnpc_msvc("2.3.3", "miniupnpc_2_3_3"),
}
