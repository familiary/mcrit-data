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

The 1.9 line, added for the window issue #62 suggests (1.9.x to 2.1.x).
Upstream has no git tag that tells the 1.9.x snapshots apart: ``miniupnpc_1_9``
(ce56baf8) is the only one, and VERSION reads "1.9" from 2014-01-31 (b72a782)
until 2.0, tarballs included. What is dated is the release tarballs that
miniupnp.free.fr/files/ and miniupnp.tuxfamily.org/files/ serve, from
miniupnpc-1.9.20140401.tar.gz to miniupnpc-1.9.20160209.tar.gz (twenty-one
files). ``miniupnpc_1.9.20150206`` is built from miniupnpc-1.9.20150206.tar.gz
(76864 bytes, sha256 230d3ad5...), the example the issue names, with the same
Makefile.mingw route as 2.0 (it has the same hardcoded ``dllwrap --driver-name
gcc`` and Windows-only ``miniupnpcstrings.h`` rule); the archive has no
``miniupnpc/`` level, so the steps run in its root and the DLL is ./miniupnpc.dll.
Pinned by sha256 of the download; the file is byte for byte what both mirrors
serve (HTTP 200, same size from each).

kept + removed = total: x86 75 + 154 = 229, x64 102 + 154 = 256. Of the kept,
the x86 image has one unnamed function and the x64 image 31 (ws2_32 import
thunks, as for the other versions); the iphlpapi thunks GetBestRoute and
GetIpAddrTable are the named ones, one instruction each. 61 (x86) and 59 (x64)
distinct PicHashes of functions with 10 or more instructions. Overlap with
the neighbouring builds (x86 / x64, share of the 1.9.20150206 column): 2.0 54%
/ 53%, 2.1 44% / 42%. So it is a separate cluster in the same sense as the four
above.

1.9.20160209, the last 1.9 snapshot, was built too and dropped: it has the
same 63 (x86) and 61 (x64) PicHashes as 2.0, exactly (100% each way), because
2.0 was cut from it two months later. 1.9.20140401 and the other twenty
snapshots were not built.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_MAKE = ("make -f Makefile.mingw CC={cc} AR={ar} WINDRES={windres} "
         "DLLWRAP={prefix}dllwrap")
_STRINGS = ("sed 's|OS_STRING \".*\"|OS_STRING \"Windows/Mingw32\"|' "
            "miniupnpcstrings.h.in | sed \"s|MINIUPNPC_VERSION_STRING "
            "\\\".*\\\"|MINIUPNPC_VERSION_STRING \\\"$(cat VERSION)\\\"|\" "
            "> miniupnpcstrings.h")


def _steps(version, cwd="miniupnpc"):
    if version == "2.0" or version.startswith("1.9"):
        return [
            BuildStep(_STRINGS, cwd=cwd),
            BuildStep("mkdir -p tools && for t in dllwrap dlltool as; do "
                      "ln -sf $(command -v {prefix}$t) tools/$t; done && "
                      "ln -sf $(command -v {cc}) tools/gcc", cwd=cwd),
            BuildStep("PATH=$PWD/tools:$PATH " + _MAKE +
                      " -o wingenminiupnpcstrings init miniupnpc.dll",
                      cwd=cwd, env={"CFLAGS": "-Os"}),
        ]
    # 2.2.0 has the cross-compiling sed rule for miniupnpcstrings.h but no
    # rc_version.h rule yet (2.2.3 has both).
    goals = ("init" if version == "2.1" else
             "miniupnpcstrings.h" if version == "2.2.0" else
             "miniupnpcstrings.h rc_version.h")
    return [BuildStep(_MAKE + " " + goals + " miniupnpc.dll",
                      cwd=cwd, env={"CFLAGS": "-Os"})]


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


def _miniupnpc_tarball(version, sha256):
    """A dated 1.9.x release tarball. Upstream publishes these as files, not
    as git tags: the only 1.9 tag, ``miniupnpc_1_9``, carries VERSION "1.9"
    for the whole 2014-01 to 2016-04 span, and the tarballs (which have no
    ``miniupnpc/`` level, so cwd is the unpacked root) are what carries the
    dated names that distributions and vendored copies cite."""
    r = _miniupnpc(version, None)
    r.source = Source(url="http://miniupnp.free.fr/files/miniupnpc-%s.tar.gz"
                      % version, sha256=sha256)
    r.build = _steps(version, cwd=".")
    r.artifacts = [Artifact(path="miniupnpc.dll", component="miniupnpc.dll")]
    r.notes += (" Built from upstream's dated release tarball "
                "miniupnpc-%s.tar.gz (the same file is on "
                "miniupnp.tuxfamily.org/files/); upstream publishes no "
                "checksum, the sha256 is of the download." % version)
    return r


RECIPES = {
    # The 1.9 line: dated tarball releases, see _miniupnpc_tarball.
    "miniupnpc_1.9.20150206": _miniupnpc_tarball(
        "1.9.20150206",
        "230d3ad5a3047daa77f99602503d798f720428207217ebfbfe2a4f7762b029e7"),
    # Brackets the 2016-2020 period; see the docstring for what is unknown.
    "miniupnpc_2.0": _miniupnpc("2.0", "miniupnpc_2_0"),
    "miniupnpc_2.1": _miniupnpc("2.1", "miniupnpc_2_1"),
    "miniupnpc_2.2.3": _miniupnpc("2.2.3", "miniupnpc_2_2_3"),
    "miniupnpc_2.3.3": _miniupnpc("2.3.3", "miniupnpc_2_3_3"),
}

# The final sweep: every other dated 1.9.x release tarball upstream lists
# (http://miniupnp.free.fr/files/), and the two tags that were built and left
# out as redundant with 2.2.3. An image whose PicHash set (10+ instructions)
# is identical to one already carried is not committed; the recipe docstring
# lists which those were. sha256 is of the download (no upstream checksum).
_DATED = {
    "1.9.20140401": "d02670112125300f7a3d61421714d99105edd90190bf12542d16785f16f017aa",
    "1.9.20140610": "31beffe44a5d7b7bbad3729cdd6f9f85844b9e5771aebb56550f87cbedcf5d3b",
    "1.9.20140701": "26f3985bad7768b8483b793448ae49414cdc4451d0ec83e7c1944367e15f9f07",
    "1.9.20140906": "e16f3381f22ecd08aa54fb8b51b5e483e9c9472dcb2883c15a0054a843c9435c",
    "1.9.20140911": "7435bebfdd8c76127136f733979ad2ab56999d204176a1044293536f2e20b21c",
    "1.9.20141027": "763a3ebed0c3267b8605247b38f46e99bfe54c96a9ca2882aa9abb5485407540",
    "1.9.20141108": "8456172f333ac4b73d4378e8a5ae1d7676dbc47092fa77848c533126fb87e5cd",
    "1.9.20141113": "efeaa8d688657bed3ea561f528acd206162a20d7f4edc013611c2c4dfd32c284",
    "1.9.20141117": "1573e5c7248930107bdf6e80e98cc4a7adf6152f465e4268e3b4b4843c79af9d",
    "1.9.20141128": "754419d9fec75deefa2c630a90eaf156bb008db5dbcdb662377715b7c1662e26",
    "1.9.20150427": "b3207ddc0b0001887d6a29260e8d609d0ad2c35bec99a2358281bb8951919837",
    "1.9.20150430": "76d707434833bd1114a17e339dfe89515feb80d648028d7cfd5750a0e8df7647",
    "1.9.20150522": "a77c34a1020f908342de2d32f730c1f49771648817382216513ef6c998bf5571",
    "1.9.20150609": "86e6ccec5b660ba6889893d1f3fca21db087c6466b1a90f495a1f87ab1cd1c36",
    "1.9.20150721": "60b52654e780f9091a5ae472c5c17a5f37797d204639865d98635d67e4e86bb3",
    "1.9.20150730": "1d64fab1fd3b4c8545139341ba197f19329a863f4f21b578fc2a228ab586a604",
    "1.9.20150917": "3087c32929c1e9db4947d6a184694e06ec604bca29449b75daec295a5d8f11da",
    "1.9.20151008": "e444ac3b587ce82709c4d0cfca1fe71f44f9fc433e9f946b12b9e1bfe667a633",
    "1.9.20151026": "f3cf9a5a31588a917d4d9237e5bc50f84d00c5aa48e27ed50d9b88dfa6a25d47",
    "1.9.20160209": "572171eacc1d72537ce47b6f4571260757ab7bcfdaf54c3a55c7f88594d94b6f",
}
for _v, _sha in _DATED.items():
    RECIPES["miniupnpc_%s" % _v] = _miniupnpc_tarball(_v, _sha)
RECIPES["miniupnpc_2.2.0"] = _miniupnpc("2.2.0", "miniupnpc_2_2_0")
RECIPES["miniupnpc_2.2.8"] = _miniupnpc("2.2.8", "miniupnpc_2_2_8")
