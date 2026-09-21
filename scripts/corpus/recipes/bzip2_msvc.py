"""bzip2 built with MSVC, beside the MinGW build of the same tarball.

bzip2 on Windows lives in installers, archivers and update tooling, and all
of those are MSVC-built; data/bzip2 carries only MinGW artefacts.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

What was read rather than assumed, in the 1.0.8 tarball:
  * ``makefile.msc`` is upstream's own MSVC build. Its flags are
    ``-DWIN32 -MD -Ox -D_FILE_OFFSET_BITS=64 -nologo``, its targets are
    ``libbz2.lib`` (a static library, which SMDA cannot read) and
    ``bzip2.exe``, and there is no DLL rule at all - upstream ships
    ``libbz2.def`` but never links it on this path.
  * that makefile's inference rule is ``$(CC) $(CFLAGS) -c $*.c -o $*.obj``.
    ``cl -o`` is a VC6 spelling that current cl only accepts under a
    deprecation warning, and a makefile whose every object depends on it is
    not worth the cycle. So this recipe writes the two commands out by hand,
    exactly as the MinGW recipe does - that one does not use upstream's
    ``Makefile`` either - and keeps upstream's own ``-DWIN32`` and
    ``-D_FILE_OFFSET_BITS=64``.
  * ``bzlib.h`` defines ``BZ_EXPORT`` unless ``BZ_IMPORT`` is set, and under
    ``_WIN32`` that makes every library entry point ``WINAPI``, i.e.
    ``__stdcall``. Nothing here has to ask for that and nothing may switch it
    off: it is the same decoration the MinGW artefact carries.
  * ``bzip2.c`` selects its ``BZ_LCCWIN32`` branch on ``_WIN32``, which cl
    defines; that branch uses ``setmode``, ``fileno`` and ``struct _stati64``
    from ``<io.h>``/``<sys/stat.h>``. The UCRT still declares all three, under
    a deprecation warning that ``_CRT_NONSTDC_NO_DEPRECATE`` and
    ``_CRT_SECURE_NO_WARNINGS`` silence. Neither is a code-generation switch.

The artefact is ``bzip2.exe``, not a DLL, and that is deliberate: the MinGW
recipe measured that the EXE statically links the same objects as the DLL and
is a superset of it by 45 of the DLL's 46 functions, so it ships the EXE
alone. An MSVC build that shipped a DLL instead would not be comparable with
its MinGW sibling, which is the whole point of adding it. SMDA reads a PE
image either way; what it cannot read is the static ``.lib``, and this recipe
never produces one.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# The seven library translation units plus the driver, in the order the MinGW
# recipe compiles them. bzip2.c has to be in the same cl invocation as the
# rest because /Fd is per-invocation: one shared compiler PDB is what the
# linker later turns into bzip2.pdb, and MSVC keeps symbols there rather than
# in a COFF symbol table.
_SOURCES = ("blocksort.c huffman.c crctable.c randtable.c compress.c "
            "decompress.c bzlib.c bzip2.c")

_OBJECTS = _SOURCES.replace(".c", ".obj")

# /MD, not cl's default /MT: a static CRT put 1947 of VX-API's 4219 functions
# into that artefact as MSVC C runtime, duplicating data/MSVC. Upstream's own
# makefile.msc already asks for -MD, so this is not a deviation from it.
#
# /O2 rather than upstream's /Ox: the MinGW sibling is -O2, the other MSVC
# recipes here are /O2, and /O2 additionally implies /Gy, which puts each
# function in its own COMDAT - that is what makes /OPT:NOREF below able to
# keep routines nothing calls. Recorded in build_flags as what it is.
_COMPILE = ('cl /nologo /c /O2 /MD /Zi /Fdbzip2.pdb '
            '/DWIN32 /D_FILE_OFFSET_BITS=64 '
            '/D_CRT_SECURE_NO_WARNINGS /D_CRT_NONSTDC_NO_DEPRECATE '
            + _SOURCES)

# The same link flags sqlite3_msvc.py explains: /DEBUG so a PDB is written at
# all, /Brepro so the PE carries no build timestamp and two runs over
# identical source record the same sha256, and /OPT:NOREF /OPT:NOICF so
# unreferenced and identically-compiled routines both survive as separate
# reference samples. setargv.obj, which upstream's makefile.msc links for
# wildcard expansion, is left out: it is CRT code, it is not needed for
# reference data, and the MinGW artefact does not carry it either.
_LINK = ('link /nologo /DEBUG /Brepro /OPT:NOREF /OPT:NOICF '
         '/PDB:bzip2.pdb /OUT:bzip2.exe ' + _OBJECTS)


RECIPES = {
    "bzip2_1.0.8_msvc": Recipe(
        family="bzip2",
        version="1.0.8",
        upstream="https://sourceware.org/pub/bzip2/",
        license="bzip2-1.0.6 (BSD-like)",
        # The same tarball and the same digest the MinGW recipe pins.
        source=Source(
            url="https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz",
            sha256="ab5a03176ee106d3f0fa90e381da478ddae405918153cca248e682cd0c4a2269"),
        build=[
            BuildStep(_COMPILE),
            BuildStep(_LINK),
            # Cheap insurance, as in xz_msvc.py: build.py reports a missing
            # artefact by the path it expected and nothing else, and this
            # puts the names the build actually wrote into the log the
            # workflow prints on failure.
            BuildStep("dir", allow_failure=True),
        ],
        artifacts=[Artifact(path="bzip2.exe", component="bzip2.exe",
                            pdb="bzip2.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi, -DWIN32 -D_FILE_OFFSET_BITS=64; "
                    "/DEBUG /Brepro /OPT:NOREF /OPT:NOICF at link",
        notes="The same seven library objects plus bzip2.c that the MinGW "
              "recipe links, so this artefact and its MinGW sibling differ "
              "only in the compiler. No dependencies: bzip2 links the CRT and "
              "nothing else, and this is built against the DLL runtime so the "
              "MSVC C runtime is imported rather than linked in and stays "
              "attributed to data/MSVC. Upstream's makefile.msc is not used - "
              "its inference rule spells the output as 'cl -o', which current "
              "cl only accepts under a deprecation warning - but its flags "
              "are, with /Ox replaced by /O2 to match the MinGW sibling.",
    ),
}
