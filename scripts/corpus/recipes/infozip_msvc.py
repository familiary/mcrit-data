"""Info-ZIP zip 3.0 and unzip 6.0 built with MSVC, beside the MinGW builds.

The same two tarballs, the same two sha256 values and the same two EXEs as
infozip.py (zip.exe, unzip.exe; zipcloak/zipnote/zipsplit, funzip, unzipsfx
and unzip32.dll are left out for the reasons given there). The deflate and
inflate code in Info-ZIP is the reusable part, and it is carried by
Windows-side tooling that is overwhelmingly cl-built.

A separate registry entry rather than another toolchain on the MinGW recipe:
one Recipe has one build list and these steps are cmd.exe, not sh.

What was read rather than assumed, in the two tarballs:
  * zip's own MSVC makefile is ``win32/makefile.w32``, with ``makenoas.w32``
    as its no-assembler twin; unzip's is ``win32/Makefile``. Both are nmake
    files that drive cl one translation unit at a time, and both default to a
    static CRT: zip picks ``-ML``/``-MT`` and unzip does the same unless zlib
    or bzip2 is requested. That default is the conflict with this corpus'
    mandate, which is ``/MD``; under /MT a static CRT puts the C runtime into
    the artefact where it would be filed under Info-ZIP. Neither makefile is
    used. This recipe writes the cl and link lines out directly, over exactly
    the translation units the MinGW recipe links, and so the only things that
    differ between this artefact and its MinGW sibling are the compiler and
    the C runtime.
  * translation units. zip.exe: zip crypt ttyio zipfile zipup fileio util
    crc32 globals deflate trees plus win32/win32, win32/win32zip,
    win32/win32i64 and win32/nt. unzip.exe: unzip crc32 crypt envargs explode
    extract fileio globals inflate list match process ttyio ubz2err unreduce
    unshrink zipinfo plus win32/win32, win32/win32i64 and win32/nt. The
    resource scripts (zip.rc, winapp.rc) contain no code and are not linked.
  * the assembler fast paths are off, as in the MinGW recipe: ``-DNO_ASM`` for
    zip, and for unzip simply no ``-DASM_CRC``. ``win32/crc_i386.c`` (what
    makenoas.w32 would still build with ASM_CRC) is 32-bit inline assembly
    that cl does not accept for x64, and match32.asm/gvmat64.asm are separate
    assembler files. So x86 and x64 are the same C and deflate.c's
    longest_match is the C one.
  * the defines are the MinGW makefiles' own: ``-DWIN32
    -DFORCE_WIN32_OVER_UNIX`` and, for unzip, ``-DIZ_CRCOPTIM_UNFOLDTBL``.
    unzip's ``UNICODE_SUPPORT`` is enabled by default in win32/w32cfg.h
    (line 216), so its nmake makefile's ``-DUNICODE_SUPPORT`` changes
    nothing. ``-W3``, ``-J`` and ``-D_MBCS`` from upstream's nmake files are
    not code-generation switches that the MinGW build has an equivalent for
    and are left out; ``-J`` (unsigned char) would be a real difference and
    is deliberately not used.
  * ``-DWIN32`` is passed as upstream does. cl also defines ``_WIN32``.
  * ``/FIwindows.h`` is the MSVC spelling of the MinGW recipe's ``-include
    windows.h`` and is needed for the same reason. A first attempt without it
    failed on all four builds in winnt.h of the 10.0.26100.0 SDK (line 21730,
    C2143/C2059): both programs ``#define CR 13`` before they include
    <windows.h>, and winnt.h declares an ARM64 struct with a bitfield named
    ``CR``. Including windows.h first lets its include guard stop it being
    read again once the macro exists.
  * osdep.h and w32cfg.h already define ``_CRT_SECURE_NO_DEPRECATE`` and
    ``_CRT_NONSTDC_NO_DEPRECATE`` for _MSC_VER >= 1400; they are repeated on
    the command line only so the build does not depend on include order.

Flags: ``/O2 /MD /Zi``, no /GL, no /LTCG. /O2 matches the -O2 the MinGW
sibling is built with and implies /Gy, which gives each function its own
COMDAT so that /OPT:NOREF below can keep routines nothing calls. Link:
``/DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF`` (a PDB so SMDA can
name functions, a build without a timestamp, and no jump-thunk table: see
bzip2_msvc.py for why /INCREMENTAL:NO has to be stated). user32.lib and
advapi32.lib are the two libraries both upstream makefiles add. The flags are
as written in this file; the build log echoes the cl line but not a flag
readback. cl 19.44.35229 (VS 2022 v143), SDK 10.0.26100.0.

Measured, glue baseline applied (kept + removed = image):

    zip.exe 3.0    x86  348 + 207 = 555    x64  348 + 213 = 561
    unzip.exe 6.0  x86  238 + 195 = 433    x64  230 + 197 = 427

(MinGW: zip 245 + 208 = 453 / 317 + 204 = 521, unzip 130 + 154 = 284 /
213 + 149 = 362.) About a hundred of the kept functions in each x86 image are
one-instruction import thunks (``_CreateFileA@28`` and the like) that the
DLL runtime and kernel32/advapi32 imports leave behind; they are what the
kept count has more of than MinGW's.

Overlap with the MinGW artefacts of the same program and architecture, exact
PicHash, functions of ten instructions or more (MinGW / MSVC / shared):

    zip.exe    x86  189 / 223 / 0      x64  185 / 220 / 0
    unzip.exe  x86  106 / 142 / 0      x64  107 / 138 / 0

As with every other MSVC pass here, the same source compiled by the two
compilers shares no hash at that size, so the MSVC build is new data for
MSVC-built malware rather than a duplicate of the MinGW one.

Glue survivors at ten instructions or more: none on x86. On x64 one,
``__scrt_common_main_seh`` (99 instructions, PicHash 11855707620856894801) in
both zip.exe and unzip.exe - the MSVC CRT startup routine already recorded
in the README as the one finding the MSVC baseline does not remove. No
unnamed function reaches ten instructions in any of the four images.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_DEFS = ("/FIwindows.h /DWIN32 /DFORCE_WIN32_OVER_UNIX "
         "/D_CRT_SECURE_NO_DEPRECATE /D_CRT_NONSTDC_NO_DEPRECATE")

# One cl invocation so /Fd names one compiler PDB for the linker to start
# from. win32\*.c need -I. to find the top-level headers, as upstream's rules
# pass; it is harmless for the others.
_CL = "cl /nologo /c /O2 /MD /Zi /I. %s /Fd%s.pdb %s"

_LINK = ("link /nologo /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF "
         "/PDB:%s.pdb /OUT:%s.exe %s user32.lib advapi32.lib")


def _objs(sources):
    return " ".join(s.split("\\")[-1].replace(".c", ".obj") for s in sources)


_ZIP_SOURCES = ("zip.c crypt.c ttyio.c zipfile.c zipup.c fileio.c util.c "
                "crc32.c globals.c deflate.c trees.c win32\\win32.c "
                "win32\\win32zip.c win32\\win32i64.c win32\\nt.c").split()

_UNZIP_SOURCES = ("unzip.c crc32.c crypt.c envargs.c explode.c extract.c "
                  "fileio.c globals.c inflate.c list.c match.c process.c "
                  "ttyio.c ubz2err.c unreduce.c unshrink.c zipinfo.c "
                  "win32\\win32.c win32\\win32i64.c win32\\nt.c").split()


def _recipe(version, url, sha256, name, sources, defs, upstream, notes):
    return Recipe(
        family="Info-ZIP",
        version=version,
        upstream=upstream,
        license="Info-ZIP",
        source=Source(url=url, sha256=sha256),
        build=[
            BuildStep(_CL % (defs, name, " ".join(sources))),
            BuildStep(_LINK % (name, name, _objs(sources))),
            BuildStep("dir", allow_failure=True),
        ],
        artifacts=[Artifact(path=name + ".exe", component=name + ".exe",
                            pdb=name + ".pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi, %s; /DEBUG /Brepro /INCREMENTAL:NO "
                    "/OPT:NOREF /OPT:NOICF at link" % defs,
        notes=notes,
    )


RECIPES = {
    "infozip_zip_3.0_msvc": _recipe(
        "3.0", "https://downloads.sourceforge.net/infozip/zip30.tar.gz",
        "f0e8bb1f9b7eb0b01285495a2699df3a4b766784c1765a8f1aeedf63c0806369",
        "zip", _ZIP_SOURCES, _DEFS + " /DNO_ASM",
        "https://infozip.sourceforge.net/Zip.html",
        "zip.exe only, over the translation units the MinGW recipe links. "
        "Upstream's win32/makefile.w32 is not used: it defaults to a static "
        "CRT and this corpus builds /MD. Assembler fast paths disabled."),
    "infozip_unzip_6.0_msvc": _recipe(
        "6.0", "https://downloads.sourceforge.net/infozip/unzip60.tar.gz",
        "036d96991646d0449ed0aa952e4fbe21b476ce994abc276e49d30e686708bd37",
        "unzip", _UNZIP_SOURCES, _DEFS + " /DIZ_CRCOPTIM_UNFOLDTBL",
        "https://infozip.sourceforge.net/UnZip.html",
        "unzip.exe only, over the translation units the MinGW recipe links. "
        "Upstream's win32/Makefile is not used: it defaults to a static CRT "
        "and this corpus builds /MD. Assembler CRC disabled."),
}
