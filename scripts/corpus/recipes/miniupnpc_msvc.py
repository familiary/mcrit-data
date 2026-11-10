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

Measurements (first Windows run, cl 19.44, all four tags green on both legs).

* Counts, kept + removed = image total. x64: 2.0 95 + 153 = 248, 2.1 95 + 152
  = 247, 2.2.3 98 + 154 = 252, 2.3.3 97 + 154 = 251. x86: 95 + 145 = 240,
  95 + 144 = 239, 98 + 146 = 244, 97 + 146 = 243. The removed ones are the
  CRT startup, security-cookie and castguard code and the UCRT stdio inlines
  (``fprintf``, ``snprintf``, ``vsnprintf``, ``sscanf``).
* Exports (``dumpbin /exports``): 41, 40, 40, 42 names for 2.0, 2.1, 2.2.3,
  2.3.3 on both legs. That is more than the ``.def`` lists (35, 35, 38, 38):
  the rest are functions declared ``MINIUPNP_EXPORTS`` in the headers
  (``upnpDiscoverDevice``, ``upnpDiscoverDevices``, ``upnpDiscoverAll``,
  ``getHTTPResponse``, ``ssdpDiscoverDevices``, ``UPNPIGD_IsConnected`` and,
  in 2.3.3, the two ``...Ext`` port-mapping calls). The MinGW reports name
  every one of them too, so the two artefacts export the same API.
* Named one-instruction import thunks stay in the family, as the MinGW
  iphlpapi ones do: 24-26 per x86 image, 25-27 per x64 image (ws2_32
  ``socket`` / ``bind`` / ``connect`` ...; ``GetAdaptersAddresses``,
  ``GetBestInterface``; and UCRT thunks such as ``atoi``, ``_strdup``,
  ``strtoul``, ``perror``). None has ten instructions. The MSVC images carry
  no unnamed functions.
* MinGW against MSVC, PicHashes of functions of ten or more instructions,
  same tag and architecture: x86 0 of 63-67 (MinGW) / 65-66 (MSVC) shared in
  every tag, x64 0 in 2.1, 2.2.3 and 2.3.3 and 1 in 2.0. Across all four
  tags: x86 0 of 138 / 133, x64 1 of 129 / 136. As with every earlier MSVC
  family the two code generators share essentially nothing, so these
  artefacts add a second, disjoint reference rather than duplicating one.
* Glue survivors: the first run left ``printf`` at ten or more instructions
  in 2.0 only (x86 PicHash 14739679411554417350, 17 instructions; x64
  121597203084696572, 25), reached through UCRT's inline ``printf``. The
  wide-stdio glue baseline (scripts/corpus/baseline.py) now removes both; the
  re-import against it (run 42341850811) moved them to the removed side, which
  is why the 2.0 counts above are the re-imported ones.

1.9.20150206, added for the 1.9.x window of r0ny123/mcrit-data#62 (see
miniupnpc.py: the only 1.9 git tag does not tell the snapshots apart, so this
is built from the dated release tarball miniupnpc-1.9.20150206.tar.gz, sha256
230d3ad5...). The tarball has no ``miniupnpc/`` level, so every step runs in
its root and the artefact is build-<arch>/miniupnpc.dll; the source list is the
eleven objects of that release's Makefile.mingw (minissdpc and upnpdev arrived
with the 2016 snapshots), the rest of the line is the other versions' cl and
link commands unchanged, including upstream's miniupnpc.def. Built on run
42680903937 (cl 19.44, wide-stdio glue baseline): x86 93 + 145 = 238, x64 93 +
153 = 246 (kept + removed = image; MinGW 75 + 154 = 229 / 102 + 154 = 256), no
unnamed function and none of the kept functions is glue at ten instructions or
more. PicHash overlap of the 10+ instruction functions: MinGW / MSVC / shared
61 / 63 / 0 (x86) and 59 / 62 / 1 (x64); against the other MSVC builds, 2.0
shares 32 of 63 (x86) and 29 of 62 (x64), 2.1 28 and 24, 2.2.3 24 and 21, so
it is a distinct reference in the MSVC set too.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_OBJS = ["miniwget", "minixml", "igd_desc_parse", "minisoap", "minissdpc",
         "miniupnpc", "upnpreplyparse", "upnpcommands", "upnperrors",
         "connecthostport", "portlistingparse", "receivedata", "upnpdev"]


# The 1.9.x release tarballs have no miniupnpc/ level, and 1.9.20150206's
# Makefile.mingw OBJS list is these eleven (minissdpc and upnpdev came in with
# the 2016 snapshots).
_OBJS_19 = ["miniwget", "minixml", "igd_desc_parse", "minisoap", "miniupnpc",
            "upnpreplyparse", "upnpcommands", "upnperrors", "connecthostport",
            "portlistingparse", "receivedata"]


def _steps(version):
    tarball = version.startswith("1.9")
    cwd = "." if tarball else "miniupnpc"
    old = tarball or version in ("2.0", "2.1", "2.2.0")
    srcdir = "" if old else "src\\"
    # The four dated tarballs from 1.9.20150917 on list minissdpc.o in
    # Makefile.mingw's OBJS, the earlier ones do not; 2.2.0 is flat like 2.1
    # but already has addr_is_reserved.c.
    if tarball:
        objs = list(_OBJS_19)
        if version >= "1.9.20150917":
            objs.insert(4, "minissdpc")
        if version >= "1.9.20151008":
            # upnpdev.c (freeUPNPDevlist, which miniupnpc.def exports) joins
            # Makefile.mingw's OBJS in 1.9.20151008.
            objs.append("upnpdev")
    elif version == "2.2.0":
        objs = _OBJS + ["addr_is_reserved"]
    else:
        objs = _OBJS if old else _OBJS + ["addr_is_reserved"]
    includes = "/I." if old else "/Iinclude /I."
    # 1.9.20150917's minissdpc.c includes <strings.h> and <unistd.h> before
    # its _WIN32 branch (later tarballs move them into the POSIX branch); it
    # uses nothing from either on Windows, so the build tree gets two empty
    # headers of those names. No upstream file is edited.
    shim = version == "1.9.20150917"
    if shim:
        includes += " /Icorpus-shim"
    # 2.2.3 and later write rc_version.h as well.
    genargs = "miniupnpcstrings.h.in miniupnpcstrings.h"
    if not old and version != "2.2.0":
        genargs += " rc_version.h"
    sources = " ".join(srcdir + o + ".c" for o in objs)
    compile_ = ("cl /nologo /c /MD /O2 /Ob2 /Zi /W3 /DNDEBUG "
                "/D_WIN32_WINNT=0x501 /DMINIUPNP_EXPORTS " + includes +
                " /Foobj-{arch}\\ /Fdbuild-{arch}\\miniupnpc.pdb " + sources)
    pre = [BuildStep("if not exist corpus-shim mkdir corpus-shim", cwd=cwd),
           BuildStep("type nul > corpus-shim\\strings.h", cwd=cwd),
           BuildStep("type nul > corpus-shim\\unistd.h", cwd=cwd)] if shim else []
    return pre + [
        BuildStep("if not exist obj-{arch} mkdir obj-{arch}",
                  cwd=cwd),
        BuildStep("if not exist build-{arch} mkdir build-{arch}",
                  cwd=cwd),
        # The generator is a build tool; it is not linked into the artefact.
        BuildStep("cl /nologo /W3 /Fogen-{arch}.obj "
                  "/Febuild-{arch}\\wingenminiupnpcstrings.exe "
                  "wingenminiupnpcstrings.c", cwd=cwd),
        BuildStep("build-{arch}\\wingenminiupnpcstrings.exe " + genargs,
                  cwd=cwd),
        BuildStep(compile_, cwd=cwd),
        BuildStep("link /nologo /DLL /OUT:build-{arch}\\miniupnpc.dll "
                  "/DEF:miniupnpc.def /DEBUG "
                  "/PDB:build-{arch}\\miniupnpc.pdb /INCREMENTAL:NO /Brepro "
                  "/OPT:NOREF /OPT:NOICF obj-{arch}\\*.obj "
                  "ws2_32.lib iphlpapi.lib", cwd=cwd),
        BuildStep("dumpbin /nologo /exports build-{arch}\\miniupnpc.dll",
                  cwd=cwd, allow_failure=True),
        BuildStep("dir build-{arch}", cwd=cwd, allow_failure=True),
    ]


_TARBALL_19 = {
    "1.9.20150206": "230d3ad5a3047daa77f99602503d798f720428207217ebfbfe2a4f7762b029e7",
}


def _miniupnpc_msvc(version, git_ref):
    tarball = version in _TARBALL_19
    base = "" if tarball else "miniupnpc/"
    r = Recipe(
        family="miniupnpc",
        version=version,
        upstream="https://github.com/miniupnp/miniupnp",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/miniupnp/miniupnp.git",
                      git_ref=git_ref),
        build=_steps(version),
        artifacts=[Artifact(path=base + "build-{arch}/miniupnpc.dll",
                            component="miniupnpc.dll",
                            pdb=base + "build-{arch}/miniupnpc.pdb")],
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
    if tarball:
        # A dated release tarball, not a git tag; see miniupnpc.py.
        r.source = Source(
            url="http://miniupnp.free.fr/files/miniupnpc-%s.tar.gz" % version,
            sha256=_TARBALL_19[version])
        r.notes += (" Built from upstream's dated release tarball "
                    "miniupnpc-%s.tar.gz (the same file is on "
                    "miniupnp.tuxfamily.org/files/); upstream publishes no "
                    "checksum, the sha256 is of the download." % version)
    return r


RECIPES = {
    "miniupnpc_1.9.20150206_msvc": _miniupnpc_msvc("1.9.20150206", None),
    "miniupnpc_2.0_msvc": _miniupnpc_msvc("2.0", "miniupnpc_2_0"),
    "miniupnpc_2.1_msvc": _miniupnpc_msvc("2.1", "miniupnpc_2_1"),
    "miniupnpc_2.2.3_msvc": _miniupnpc_msvc("2.2.3", "miniupnpc_2_2_3"),
    "miniupnpc_2.3.3_msvc": _miniupnpc_msvc("2.3.3", "miniupnpc_2_3_3"),
}

# The final sweep: the other dated 1.9.x tarballs and the 2.2.0 and 2.2.8 tags,
# the same sources as the MinGW recipes (miniupnpc.py _DATED).
from .miniupnpc import _DATED  # noqa: E402
_TARBALL_19.update(_DATED)
for _v in _DATED:
    RECIPES["miniupnpc_%s_msvc" % _v] = _miniupnpc_msvc(_v, None)
RECIPES["miniupnpc_2.2.0_msvc"] = _miniupnpc_msvc("2.2.0", "miniupnpc_2_2_0")
RECIPES["miniupnpc_2.2.8_msvc"] = _miniupnpc_msvc("2.2.8", "miniupnpc_2_2_8")
