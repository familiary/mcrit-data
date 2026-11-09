"""SQLite 3.30.1, the reusable database dependency named by tracker 60.

The official sqlite3.c and sqlite3.h are byte-identical to the files at
rapid7/mimikatz commit 45c42c710fc3a9d7acdcd1f7acf966cc4ce07a49. Only the
official SQLite amalgamation is compiled, in family sqlite3; no consumer
program, credential module, shell or test executable is built or run.

The existing family has 3.8.11.1, 3.31.1 and 3.50.4. This pin uses SQLite's
default feature profile, without FTS/RTREE/JSON1 switches, so comparison to
the older feature-enabled reference rows changes version and profile
together. It must not be reported as a version-only experiment.

Git mirror pin 25e9591209453dc0904f8f0f1c4d5090c836e19b has VERSION 3.30.1
and manifest.uuid 18db032d058f1436ce3dea84081f4ee5a0f2259ad97301d43c426bc7f3df1b0b,
matching the amalgamation's SQLITE_SOURCE_ID. No source edits are applied.

Local measurements (SMDA 5.0.2, MCRIT 1.16.0), kept + removed = image total:
  MinGW x86 1314 + 58 = 1372; x64 1321 + 53 = 1374.
  Linux x86 1324 + 12 = 1336; x64 1278 + 4 = 1282.
No functions are excluded. Qualifying distinct PicHashes (>=10 instructions)
are 1128/1100 for MinGW x86/x64 and 1124/1077 for Linux x86/x64.
The matching Linux/MinGW architecture pairs share 89 hashes on x86 and one
on x64; all cross-architecture intersections are zero. After excluding
unnamed bodies, known runtime and the Linux x86 sqlite3Pragma fragment from
novelty, new named hashes beyond every old SQLite reference are 514/520
for MinGW and 1035/1076 for Linux. Version, default-feature profile, OS and
compiler differ together; this does not isolate one cause.

MSVC 19.44, SMDA 4.8.0/MCRIT 1.9.0, scoped run 42683286951:
  x86 2173 kept + 178 removed = 2351; x64 2164 + 164 = 2328.
Both have zero unnamed functions and no named runtime survivor at the
comparison floor. Their
qualifying distinct sets have 1755/1687 hashes and share zero. MSVC x86
shares zero with every other new axis; MSVC x64 shares one with MinGW x64
and zero with all others. New named hashes beyond all older SQLite images
are 731/790. The complete pairwise names/hashes are in the coverage record.
Actual compile/link logs confirm /MD /O2 /Zi /GL- /Brepro and /OPT:NOREF
/OPT:NOICF /Brepro /INCREMENTAL:NO, with /GL disabled and no /MT or /LTCG.
All six images total 9574 kept + 469 removed + 0 excluded = 10043.
The retained MSVC CRT imports are one-instruction thunks with PicHash
0x1165511d87767dcf: x86 __msize, __beginthreadex, __endthreadex; x64
_msize, _beginthreadex, _endthreadex. None enters the comparison floor.

Retained Linux x86 runtime: _init 0xebf7442843bf7959 (11 instructions),
deregister_tm_clones 0xa79718d3eeacec81 (18), register_tm_clones
0x35e2f6e74049cbba (26), __do_global_dtors_aux 0x4589935d0552bb3f (21),
and __x86.get_pc_thunk.bp 0x7c99608cc56520ba (2). MinGW retains unnamed
15-instruction stack-probe hashes: x86 0xdfe3cea2dbb80872 and x64
0xae8f920c3b4e652a. None is project novelty. Linux x64 has no named
runtime survivor at the comparison floor. printfFunc/printfTempBuf are
SQLite's own SQL formatting helpers, not CRT printf wrappers.

Other unnamed qualifying bodies are MinGW x86 37/45 instructions
(0x349d32cfaa300ab0 / 0x5a3b8afa141533f4) and Linux x86 423 instructions
(0x6489713230055b96). They are excluded from novelty. The Linux fragment
lies inside the ELF sqlite3Pragma symbol; both that fragment and its named
owner are excluded from novelty. No report names or baseline rules are
changed. The coverage record contains complete matrices and shared names.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_SOURCE = Source(
    url="https://www.sqlite.org/2019/sqlite-amalgamation-3300100.zip",
    sha256="adf051d4c10781ea5cfabbbc4a2577b6ceca68590d23b58b8260a8e24cc5f081",
)
_NOTES = (
    "Official SQLite 3.30.1 amalgamation; default feature profile, no "
    "FTS/RTREE/JSON1 feature defines. Git mirror commit "
    "25e9591209453dc0904f8f0f1c4d5090c836e19b, Fossil source commit "
    "18db032d058f1436ce3dea84081f4ee5a0f2259ad97301d43c426bc7f3df1b0b. "
    "sqlite3.c SHA-256 e0a86381558c57a8e1a4a80fe94e842ad4ef1804a135452e253a4962c67229a6 "
    "and sqlite3.h SHA-256 5c4e58eef24c86bcce35d09017f48e3e7f71cf1fdcfcaf7932c4cf9f72131e1b "
    "are byte-identical to the consumer files at rapid7/mimikatz commit "
    "45c42c710fc3a9d7acdcd1f7acf966cc4ce07a49. Filed separately under "
    "sqlite3, not under the consumer family. Only sqlite3.c is compiled; "
    "no source patch, consumer, CLI shell or generator. Linked and "
    "disassembled only; no resulting artifact is executed."
)


def _recipe(toolchains, build, filename, flags, pdb=""):
    return Recipe(
        family="sqlite3", version="3.30.1", source=_SOURCE,
        upstream="https://sqlite.org/", license="public domain",
        toolchains=toolchains, build=build,
        artifacts=[Artifact(path=filename, component=filename, pdb=pdb)],
        build_flags=flags, notes=_NOTES,
    )


RECIPES = {
    "sqlite3_3.30.1": _recipe(
        ["mingw_x86", "mingw_x64"],
        [BuildStep("{cc} -O2 -g -shared -o sqlite3.dll sqlite3.c "
                   "'-DSQLITE_API=__declspec(dllexport)'")],
        "sqlite3.dll", "-O2 -g -shared; SQLITE_API=__declspec(dllexport); "
                       "SQLite default feature profile",
    ),
    "sqlite3_3.30.1_linux": _recipe(
        ["linux_x86", "linux_x64"],
        [BuildStep("{cc} {archflag} -O2 -g -fPIC -fvisibility=hidden "
                   "-shared -o libsqlite3.so sqlite3.c -lpthread -ldl")],
        "libsqlite3.so", "-O2 -g -fPIC -fvisibility=hidden -shared; "
                         "SQLite default feature profile; -lpthread -ldl",
    ),
    "sqlite3_3.30.1_msvc": _recipe(
        ["msvc_x86", "msvc_x64"],
        [BuildStep('cl /nologo /O2 /MD /Zi /GL- /Brepro /c '
                   '"/DSQLITE_API=__declspec(dllexport)" '
                   '/Fdsqlite3.compiler.pdb /Fosqlite3.obj sqlite3.c'),
         BuildStep('link /nologo /DLL /DEBUG /OPT:NOREF /OPT:NOICF '
                   '/Brepro /INCREMENTAL:NO /PDB:sqlite3.pdb '
                   '/OUT:sqlite3.dll sqlite3.obj')],
        "sqlite3.dll", "/O2 /MD /Zi /GL- /Brepro; "
                       "SQLITE_API=__declspec(dllexport); default features; "
                       "/DLL /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO",
        pdb="sqlite3.pdb",
    ),
}
