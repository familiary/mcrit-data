"""SQLite built with MSVC, beside the MinGW builds of the same amalgamation.

data/sqlite3 carries only MinGW artefacts, and for this family that is the
wrong compiler for the likeliest sighting: sqlite.org's own DLLs are
MinGW-built, but almost every application that embeds SQLite on Windows
compiles the amalgamation into itself with cl. These recipes cover that case
at the same versions the MinGW ones use, so the two can be compared directly.

The MSVC build cannot share the MinGW recipe's entry: recipe.Recipe has one
``build`` list for all of its toolchains, build.py runs every step through
``shell=True`` - cmd.exe on the runner - and the MinGW steps are sh. So this
is a separate registry entry with the same family and version; Recipe.slug
distinguishes them by toolchain (msvc143 against mingw13) and both land in
data/sqlite3/provenance.json.

Only 3.31.1 and 3.50.4 are covered. 3.8.11.1 is left for a later wave: it is
the pre-FTS5 build and adds a second feature profile to verify at the same
time as the toolchain itself is being proved.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# The amalgamation ships no build system - it is sqlite3.c, shell.c and two
# headers - so this is the MSVC analogue of the MinGW recipe's single gcc
# line, not a port of an upstream build file.
#
# The switch is quoted as a whole because cmd.exe treats parentheses as
# grammar; cl's own argument parser strips the quotes again, so what the
# compiler sees is the same -DSQLITE_API=__declspec(dllexport) the MinGW
# recipe passes. The feature defines are copied from that recipe verbatim:
# compile-time features change the emitted function set more than minor
# versions do, so an MSVC/MinGW comparison is only meaningful if both sides
# were asked for the same ones.
#
# /MD, not cl's default /MT: a static CRT put 1947 of VX-API's 4219 functions
# into that artefact as MSVC C runtime, duplicating data/MSVC. /Zi with an
# explicit /Fd is what gives the linker something to build a PDB from; MSVC
# keeps symbols there rather than in a COFF symbol table, and without one
# SMDA would recover ~2000 anonymous functions and smdaify would reject the
# build. The PDB is named the same as the link's, which is what vxapi.py
# does and what produced its two green artefacts.
_COMPILE = ('cl /nologo /c /O2 /MD /Zi /Fdsqlite3.pdb '
            '"/DSQLITE_API=__declspec(dllexport)" '
            '/DSQLITE_ENABLE_FTS5 /DSQLITE_ENABLE_RTREE /DSQLITE_ENABLE_JSON1 '
            '/Fosqlite3.obj sqlite3.c')

# A DLL, not a .lib: SMDA cannot read a static library, and MSVC's default
# for a lone translation unit would be an object file.
#
# /Brepro drops the build timestamp MSVC stamps into the PE header, without
# which two runs over identical source record different sha256s.
# /OPT:NOREF keeps routines nothing references, and /OPT:NOICF keeps two
# routines that compiled to identical bodies apart - folding them cost VX-API
# its StringConcat/StringCopy pair. link /DEBUG is documented to imply both,
# but the corpus says what it wants rather than relying on that. Together
# they also keep this build comparable with the MinGW one, which has no
# --gc-sections and folds nothing.
#
# /INCREMENTAL:NO because /DEBUG implies /INCREMENTAL and the /OPT:NO* forms do
# not suppress it - only /OPT:REF, /OPT:ICF and /OPT:ORDER are documented to.
# An incrementally linked image reaches each function through a jump table, and
# SMDA recovers every one of those one-instruction thunks as a function of its
# own, unnamed. That was measured on the artefacts this omission produced: 388
# of sqlite3 3.50.4 x86's 3730 functions. It is not what a released binary
# looks like, and it inflates the function count of the family it is filed
# under.
_LINK = ('link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO '
         '/OPT:NOREF /OPT:NOICF '
         '/PDB:sqlite3.pdb /OUT:sqlite3.dll sqlite3.obj')

_FLAGS = ("/O2 /MD /Zi, FTS5/RTREE/JSON1 enabled; "
          "/DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link")


def _sqlite_msvc(version, year, code, sha256):
    return Recipe(
        family="sqlite3",
        version=version,
        upstream="https://sqlite.org/",
        license="public domain",
        source=Source(
            url="https://sqlite.org/%s/sqlite-amalgamation-%s.zip" % (year, code),
            sha256=sha256),
        build=[BuildStep(_COMPILE), BuildStep(_LINK)],
        artifacts=[Artifact(path="sqlite3.dll", component="sqlite3.dll",
                            pdb="sqlite3.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS,
        notes="The same amalgamation and the same feature defines as the "
              "MinGW recipe for this version, so the two artefacts differ "
              "only in the compiler. Built against the DLL runtime, so the "
              "MSVC C runtime is imported rather than linked in and stays "
              "attributed to data/MSVC. No dependencies: the amalgamation is "
              "one translation unit and links only the CRT and Win32.",
    )


RECIPES = {
    # The generated-columns/UPSERT era, very widely shipped and still the
    # version a lot of vendored copies sit at.
    "sqlite3_3.31.1_msvc": _sqlite_msvc(
        "3.31.1", "2020", "3310100",
        "f3c79bc9f4162d0b06fa9fe09ee6ccd23bb99ce310b792c5145f87fbcc30efca"),
    # Current, and the direct counterpart of the newest MinGW artefact.
    "sqlite3_3.50.4_msvc": _sqlite_msvc(
        "3.50.4", "2025", "3500400",
        "1d3049dd0f830a025a53105fc79fd2ab9431aea99e137809d064d8ee8356b032"),
}
