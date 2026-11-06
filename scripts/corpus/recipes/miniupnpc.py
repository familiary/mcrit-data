"""miniupnpc - the UPnP IGD client library, used by the proxy module of
QakBot / Pinkslipbot (r0ny123/mcrit-data#62) and by a long list of P2P and
torrent software.

No coverage existed under any name. miniupnpc lives in the ``miniupnpc/``
subdirectory of miniupnp/miniupnp, so every step runs with ``cwd="miniupnpc"``.
Pinned to git tags (a tag resolves to an immutable commit and upstream
publishes no checksum files): ``miniupnpc_2_0`` 1337158f, ``miniupnpc_2_1``
bd836936, ``miniupnpc_2_2_3`` 2df81203, ``miniupnpc_2_3_3`` bf4215a7.

Which versions. The lineage of the malware's copy is not knowable from
upstream history: upstream has no tag between 2.0 (2016-04-19) and 2.1
(2018-05-07), so the two bracket the 2016-2020 period the bot was active in,
and nothing here proves which one, or a dated snapshot, a given sample was
built from. Six tags were built and their PicHash sets (functions of ten or
more instructions, MinGW x86) compared, as the share of the row's hashes that
are also in the column:

    2.0 vs 2.1 0.60    2.1 vs 2.2.3 0.75    2.2.3 vs 2.3.3 0.51
    2.2.0 vs 2.2.3 0.92    2.2.3 vs 2.2.8 0.83    2.2.8 vs 2.3.3 0.63    2.0 vs 2.3.3 0.38

x64 is the same shape within four points. 2.0, 2.1, 2.2.x and 2.3.x are four
clusters, and 2.2.0 / 2.2.3 / 2.2.8 are one - so 2.2.3 (the middle of the
2.2 line) stands for it and
2.2.0 and 2.2.8 were dropped as 0.83-0.92 redundant.

Build. Upstream's own ``Makefile.mingw``, target ``miniupnpc.dll``, with its
default ``-Os`` (``CFLAGS=-Os`` is exported because 2.3.x spells it ``?=`` and
would otherwise pick up the toolchain's ``-O2`` while the older makefiles
hardcode -Os). It is the right build rather than CMake: CMake in 2.0 and 2.2.0
puts ``upnpc.c`` - the command line client - into the library, so a CMake DLL
carries ``main`` (1210 instructions in 2.0 x64, 299 in 2.2.0 x64) and, in 2.0,
``DisplayInfos``, ``SetRedirectAndTest``, ``protofix`` and ``is_int``, none of
which are the library; and 2.1's CMake
does not configure with ``UPNPC_BUILD_STATIC=OFF``. Makefile.mingw also
exports through ``miniupnpc.def``, as upstream's published DLL does. CMake was
tried for all six tags first and is not what is recorded here.

Obstacles, all solved without touching a source file:

* ``miniupnpcstrings.h`` is generated, and on Windows by running a freshly
  built ``wingenminiupnpcstrings.exe``. 2.1 and later have the cross-compile
  branch (``sed``) in the makefile already, so the header is just named as a
  goal (``rc_version.h`` too from 2.2.3 on; 2.2.0 has none). 2.0 has only the
  Windows rule, so the same two ``sed`` expressions 2.1 uses are run first and
  ``make -o wingenminiupnpcstrings`` stops make rebuilding the header from an
  executable it cannot run.
* 2.0 hardcodes ``dllwrap --driver-name gcc`` (no ``DLLWRAP`` variable). A
  throwaway ``tools/`` directory on ``PATH`` links the cross ``dllwrap``,
  ``dlltool``, ``as`` and ``gcc`` under their unprefixed names; all four are
  needed (dlltool assembles with ``as``, and an unprefixed ``as`` produces ELF,
  which cannot represent the DLL's relocations).
* ``mkdir dll`` is the makefile's ``init`` target in 2.0 and 2.1.

Winsock and iphlpapi. miniupnpc imports ``-lws2_32 -liphlpapi`` and has no
socket glue of its own, so none of it is linked in; what is filed under the
name is import thunks. The named ones are ``GetBestRoute`` and
``GetIpAddrTable`` (2.0, 2.1) and ``GetAdaptersAddresses`` and
``GetBestInterface`` (2.2.3 and later), iphlpapi stubs of one instruction.
The ws2_32 ones come out unnamed (31-37 per x64 image) and are not removable
by name. MinGW's inline ``printf`` / ``fprintf`` / ``snprintf`` wrappers are
compiled into the library at -Os, and the baseline measures them at -O0 and
-O2 only; see the README for the survivors.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_MAKE = ("make -f Makefile.mingw CC={cc} AR={ar} WINDRES={windres} "
         "DLLWRAP={prefix}dllwrap")
_STRINGS = ("sed 's|OS_STRING \".*\"|OS_STRING \"Windows/Mingw32\"|' "
            "miniupnpcstrings.h.in | sed \"s|MINIUPNPC_VERSION_STRING "
            "\\\".*\\\"|MINIUPNPC_VERSION_STRING \\\"$(cat VERSION)\\\"|\" "
            "> miniupnpcstrings.h")


def _steps(version):
    if version == "2.0":
        return [
            BuildStep(_STRINGS, cwd="miniupnpc"),
            BuildStep("mkdir -p tools && for t in dllwrap dlltool as; do "
                      "ln -sf $(command -v {prefix}$t) tools/$t; done && "
                      "ln -sf $(command -v {cc}) tools/gcc", cwd="miniupnpc"),
            BuildStep("PATH=$PWD/tools:$PATH " + _MAKE +
                      " -o wingenminiupnpcstrings init miniupnpc.dll",
                      cwd="miniupnpc", env={"CFLAGS": "-Os"}),
        ]
    goals = "init" if version == "2.1" else "miniupnpcstrings.h rc_version.h"
    return [BuildStep(_MAKE + " " + goals + " miniupnpc.dll",
                      cwd="miniupnpc", env={"CFLAGS": "-Os"})]


def _miniupnpc(version, git_ref):
    return Recipe(
        family="miniupnpc",
        version=version,
        upstream="https://github.com/miniupnp/miniupnp",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/miniupnp/miniupnp.git",
                      git_ref=git_ref),
        build=_steps(version),
        artifacts=[Artifact(path="miniupnpc/miniupnpc.dll",
                            component="miniupnpc.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-Os (Makefile.mingw default), linked via miniupnpc.def",
        notes="Library only: upnpc.c and the other samples are not part of "
              "miniupnpc.dll. Links ws2_32 and iphlpapi dynamically.",
    )


RECIPES = {
    # Brackets the 2016-2020 period; see the docstring for what is unknown.
    "miniupnpc_2.0": _miniupnpc("2.0", "miniupnpc_2_0"),
    "miniupnpc_2.1": _miniupnpc("2.1", "miniupnpc_2_1"),
    "miniupnpc_2.2.3": _miniupnpc("2.2.3", "miniupnpc_2_2_3"),
    "miniupnpc_2.3.3": _miniupnpc("2.3.3", "miniupnpc_2_3_3"),
}
