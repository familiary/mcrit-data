"""zlib built with MSVC from upstream's own win32/Makefile.msc.

data/libzlib is the one family in this corpus that already carries MSVC
artefacts: 18 IDA-derived ShiftMediaProject reports for 1.2.8 / 1.2.9 /
1.2.10 / 1.2.11 under MSVC12 / MSVC14 / MSVC15. So an msvc143 recipe here is
additional rather than gap-filling, and it has to justify itself against
that. Three things do:

  * **1.2.13 and 1.3.1 have no MSVC coverage at all.** The ShiftMediaProject
    rows stop at 1.2.11, i.e. before the CVE-2018-25032 deflate rework that
    landed in 1.2.12 - which is exactly the change that makes the
    compression path of everything from 1.2.13 onwards a different body of
    code. 1.3.1 is what anything built today links against. Those two are
    the versions covered here; 1.2.8 and 1.2.11 are deliberately left to the
    ShiftMediaProject rows rather than given a fourth compiler generation.
  * zlib is the most statically linked library on Windows and essentially
    every copy in the field was built by cl, so the MinGW rows this family
    has been carrying since are the less representative half.
  * the build is minutes: upstream's makefile already does what this corpus
    wants.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

What was read rather than assumed, in win32/Makefile.msc at **all three** of
1.2.8, 1.2.13 and 1.3.1 (they are byte-identical in every line this recipe
touches, which is why one function covers both versions built here):

  * ``CFLAGS = -nologo -MD -W3 -O2 -Oy- -Zi -Fd"zlib" $(LOC)``. /MD and /Zi
    are upstream's own defaults, so nothing has to be forced on the compile
    side - this is the only family in the MSVC wave where that is true.
  * ``LDFLAGS = -nologo -debug -incremental:no -opt:ref``, i.e. a PDB is
    already asked for.
  * ``SHAREDLIB = zlib1.dll``, ``IMPLIB = zdll.lib``, and the rule is
    ``$(LD) $(LDFLAGS) -def:$(TOP)/win32/zlib.def -dll -implib:$(IMPLIB)
    -out:$@ -base:0x5A4C0000 $(OBJS) $(OBJA) zlib1.res``. The .def, -dll,
    -implib, -out and -base all come from the rule rather than from LDFLAGS,
    so replacing LDFLAGS on the command line cannot break the link - which
    is *not* true of the 7-Zip makefile, see sevenzip_msvc.py.
  * ``OBJA =`` is empty by default at every version. 1.2.8's header comment
    documents an OBJA/LOC combination that pulls in the hand-written x86 and
    x64 assembly (inffas32.obj, match686.obj, inffasx64.obj, gvmat64.obj);
    it is not used here, because the later versions no longer ship those
    files and an artefact that had them at 1.2.8 and not at 1.3.1 would not
    be comparable with itself.
  * the ``all`` target additionally builds example.exe, minigzip.exe and two
    more programs, so the target is named explicitly.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# LDFLAGS is replaced rather than added to: nmake gives a command-line macro
# precedence over the makefile's own assignment, so the makefile's
# "LDFLAGS = -nologo -debug -incremental:no -opt:ref" is ignored entirely and
# every part of it that is still wanted has to be restated here.
#
# -nologo, -debug and -incremental:no are upstream's, repeated verbatim.
# Upstream's -opt:ref is deliberately *not* repeated: identical COMDAT
# folding and unreferenced-code elimination both destroy reference samples -
# folding cost VX-API its StringConcat/StringCopy pair - so this corpus asks
# for -OPT:NOREF -OPT:NOICF the way every other MSVC recipe here does. That
# is the one intentional divergence from the binary upstream's makefile would
# produce, and it is recorded in build_flags.
#
# -Brepro drops the build timestamp MSVC stamps into the PE header, without
# which two runs over identical source record different sha256s.
#
# -pdb: is stated although link would derive zlib1.pdb from -out:zlib1.dll on
# its own, because build.py fails a build whose declared PDB is missing and
# this corpus would rather name the file than infer it.
_LDFLAGS = ('"LDFLAGS=-nologo -debug -incremental:no -Brepro '
            '-OPT:NOREF -OPT:NOICF -pdb:zlib1.pdb"')

_NMAKE = "nmake -f win32\\Makefile.msc %s zlib1.dll" % _LDFLAGS


def _zlib_msvc(version, sha256):
    return Recipe(
        family="libzlib",
        version=version,
        upstream="https://github.com/madler/zlib",
        license="zlib",
        # The same tarball and the same digest the MinGW recipe pins, so the
        # two artefacts differ only in the compiler.
        source=Source(url="https://zlib.net/fossils/zlib-%s.tar.gz" % version,
                      sha256=sha256),
        build=[
            BuildStep(_NMAKE),
            # Cheap insurance, as in xz_msvc.py: build.py reports a missing
            # artefact by the path it expected and nothing else, and this
            # puts the names the build actually wrote into the log the
            # workflow prints on failure.
            BuildStep("dir", allow_failure=True),
        ],
        artifacts=[Artifact(path="zlib1.dll", component="zlib1.dll",
                            pdb="zlib1.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="-MD -W3 -O2 -Oy- -Zi (win32/Makefile.msc defaults, "
                    "unmodified); -nologo -debug -incremental:no -Brepro "
                    "-OPT:NOREF -OPT:NOICF at link, replacing upstream's "
                    "-opt:ref",
        notes="Upstream's own MSVC makefile, with no compiler overrides at "
              "all: its CFLAGS are already -MD -Zi and its LDFLAGS already "
              "-debug. Only the link flags are replaced, to drop the build "
              "timestamp and to stop the linker folding or discarding "
              "functions this corpus wants as separate samples. No "
              "dependencies: zlib links only the CRT and Win32, and is built "
              "against the DLL runtime so the MSVC C runtime is imported "
              "rather than linked in and stays attributed to data/MSVC. No "
              "assembly: OBJA is empty at every version, as it is upstream. "
              "This joins, rather than replaces, the ShiftMediaProject "
              "MSVC12/14/15 rows this family already carries for 1.2.8 - "
              "1.2.11; those versions are not rebuilt here.",
    )


RECIPES = {
    # First release after the CVE-2018-25032 deflate rework in 1.2.12, so the
    # compression path differs from every MSVC row this family already has.
    "libzlib_1.2.13_msvc": _zlib_msvc(
        "1.2.13", "b3a24de97a8fdbc835b9833169501030b8977031bcb54b3b3ac13740f846ab30"),
    # Current release; what anything built today links against, and with no
    # MSVC coverage in this corpus before now.
    "libzlib_1.3.1_msvc": _zlib_msvc(
        "1.3.1", "9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23"),
}
