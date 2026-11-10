"""Info-ZIP zip 3.0 / 3.1c and unzip 6.0 / funzip 6.0 built with MSVC, beside the
MinGW builds.

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

    zip.exe 3.0    x86  344 + 211 = 555    x64  343 + 218 = 561
    unzip.exe 6.0  x86  236 + 197 = 433    x64  227 + 200 = 427

(MinGW: zip 245 + 208 = 453 / 317 + 204 = 521, unzip 130 + 154 = 284 /
213 + 149 = 362.) About a hundred of the kept functions in each x86 image are
one-instruction import thunks (``_CreateFileA@28`` and the like) that the
DLL runtime and kernel32/advapi32 imports leave behind; they are what the
kept count has more of than MinGW's.

Overlap with the MinGW artefacts of the same program and architecture, exact
PicHash, functions of ten instructions or more (MinGW / MSVC / shared):

    zip.exe    x86  189 / 222 / 0      x64  185 / 218 / 0
    unzip.exe  x86  106 / 142 / 0      x64  107 / 137 / 0

As with every other MSVC pass here, the same source compiled by the two
compilers shares no hash at that size, so the MSVC build is new data for
MSVC-built malware rather than a duplicate of the MinGW one.

Glue survivors at ten instructions or more: none in the four images. The MSVC
CRT startup routine ``__scrt_common_main_seh`` (99 instructions on x64,
PicHash 11855707620856894801), which the x64 images carried before the
wide-stdio glue baseline, is removed by it in zip.exe and unzip.exe. No
unnamed function reaches ten instructions in any of the four images.

Added for r0ny123/mcrit-data#23: zip 3.1c and funzip. zip 3.1 was never
released (see infozip.py for the evidence); `infozip_zip_3.1c_msvc` builds the
last public beta, SourceForge's zip31c.zip (sha256 fda6d053..., "3.1c BETA",
22 June 2010), over the 3.0 translation units plus zbz2err.c (which 3.1c's
makefiles list; an empty stub without BZIP2_SUPPORT), with /DNO_ASM
/DNO_ASM_CRC as its makefile.w32 passes. USE_ZLIB is not defined (neither is
USEZLIB, which would replace deflate.c), so the image carries Info-ZIP's own
deflate. funzip.exe is a second artefact of `infozip_unzip_6.0_msvc`: win32/
Makefile's OBJF list (funzip crc32 crypt globals inflate ttyio win32
win32i64), compiled with /DFUNZIP into its own object directory so nothing
overwrites unzip.exe's objects, same flags. unzip.exe is rebuilt by that recipe
unchanged (run 42680903937: identical function names, PicHashes and instruction
counts, 236 + 197 and 227 + 200 as before), so its committed images are kept.

Measured on run 42680903937 (cl 19.44, wide-stdio glue baseline, kept +
removed = image):

    zip.exe 3.1c   x86  347 + 212 = 559    x64  346 + 218 = 564
    funzip.exe 6.0 x86   28 + 166 = 194    x64   28 + 168 = 196

(MinGW: zip 3.1c 247 + 209 = 456 / 321 + 205 = 526, funzip 22 + 134 = 156 /
42 + 130 = 172.) No unnamed function in any of the four images, and none of
the kept functions is glue at ten instructions or more. PicHash overlap, 10+
instruction functions, MinGW / MSVC / shared: zip 3.1c x86 193 / 222 / 0, x64
189 / 218 / 0; funzip x86 16 / 17 / 0, x64 18 / 17 / 0, so the MSVC images are
new data against the MinGW ones, as for the other programs. MSVC zip 3.0
against MSVC 3.1c: 194 of 222 (x86) and 177 of 218 (x64) shared. funzip against
unzip.exe 6.0 (both MSVC): 8 of 17 on each architecture (inflate.c, crc32).
Against every libzlib and every 7-Zip image of the same architecture: zip 3.1c
x64 shares one hash, bi_reverse (11 instructions, deflate's trees.c routine
that zlib inherited), and nothing else; funzip and the x86 images share none.
Added later for #23: `infozip_zip_3.1a_msvc` and `infozip_zip_3.1b_msvc`, the
other two public zip betas (zip31a.zip, sha256 b68a8d1b...; zip31b.zip, sha256
44e931c1...; SourceForge unreleased Betas/Zip betas, digests equal to those
SourceForge lists; ftp.info-zip.org was unreachable from the build host). Same
translation units, defines and flags as `infozip_zip_3.1c_msvc`; their
makefile.w32 lists the same objects. Measured on run 42683496249 (cl 19.44,
wide-stdio glue baseline, kept + removed = image):

    zip.exe 3.1a   x86  344 + 211 = 555    x64  343 + 218 = 561
    zip.exe 3.1b   x86  343 + 211 = 554    x64  342 + 218 = 560

PicHash overlap, MSVC zip.exe, 10+ instruction functions (x86 / x64; the
diagonal is the number of such PicHashes in the image): 3.0 222 / 218, 3.1a
222 / 218, 3.1b 220 / 216, 3.1c 222 / 218. Shared: 3.0-3.1a 217 / 213,
3.0-3.1b 198 / 181, 3.0-3.1c 194 / 177, 3.1a-3.1b 200 / 183, 3.1a-3.1c 195 /
178, 3.1b-3.1c 207 / 189. Under cl the 3.1a beta is almost the same code as
3.0 (217 of 222 on x86), where the MinGW builds share only 127 of 191 (the
MinGW 3.1 makefile builds at -O3 and 3.0's at -O2). Against the MinGW images of
the same program and architecture the MSVC images again share no hash.

Second pass: the other programs and the x86 assembler builds (scoped run
42775805495, windows-2022, v143), as separate versions so the images above
are unchanged. Measured, glue baseline applied (kept + removed = total, no
exclusions; x86 / x64):

    zipcloak.exe 3.0   154 + 185 = 339 / 154 + 190 = 344   (3.1a the same counts)
    zipnote.exe  3.0   147 + 183 = 330 / 147 + 188 = 335
    zipsplit.exe 3.0   152 + 186 = 338 / 152 + 190 = 342
    zipcloak.exe 3.1b  151 + 185 = 336 / 151 + 190 = 341
    zipnote.exe  3.1b  144 + 183 = 327 / 144 + 188 = 332
    zipsplit.exe 3.1b  149 + 186 = 335 / 149 + 190 = 339
    zipcloak.exe 3.1c  156 + 185 = 341 / 156 + 190 = 346
    zipnote.exe  3.1c  149 + 183 = 332 / 149 + 188 = 337
    zipsplit.exe 3.1c  154 + 186 = 340 / 154 + 190 = 344
    unzipsfx.exe 6.0   183 + 191 = 374 / 177 + 195 = 372
    unzip32.dll  6.0   253 + 169 = 422 / 245 + 174 = 419
    zip.exe -asm, x86: 3.0 and 3.1a 345 + 211 = 556, 3.1b 344 + 211 = 555,
                       3.1c 348 + 212 = 560
    unzip.exe -asm, x86 236 + 197 = 433; funzip.exe -asm, x86 28 + 166 = 194

Overlap at ten instructions or more: the -DUTIL objects are not zip.exe's
(zipnote 3.0 x64 shares 84 of its 99 hashes with zip.exe 3.0), unzipsfx
shares 61 of 95 (x64) with unzip.exe and unzip32.dll 37 of 145; each utility
shares 93 to 99 of its 97 to 103 hashes with the same utility of the
neighbouring version, never all of them. The assembler builds differ from
the C builds of the same version by the CRC and longest_match routines:
zip.exe 216 of 222 (3.0, 3.1a, 3.1c) and 214 of 220 (3.1b) shared, unzip.exe
139 of 142, funzip.exe 16 of 17. No image is PicHash-identical to another.
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


# zip 3.1c adds zbz2err.c to the translation units (an empty stub without
# BZIP2_SUPPORT; makefile.gcc and makefile.w32 both list it) and its
# makefile.w32 passes -DNO_ASM_CRC beside -DNO_ASM.
_ZIP31_SOURCES = _ZIP_SOURCES + ["zbz2err.c"]

# funzip, from win32/Makefile's OBJF list: funzip.c plus the same sources
# crc32, crypt, globals, inflate, ttyio and the two win32 files compiled with
# -DFUNZIP (the nmake file names those objects crc32f, cryptf, globalsf,
# inflatef, ttyiof, win32f, win32i64f). They go into their own object
# directory so they cannot overwrite unzip.exe's objects of the same name.
_FUNZIP_SOURCES = ("funzip.c crc32.c crypt.c globals.c inflate.c ttyio.c "
                   "win32\\win32.c win32\\win32i64.c").split()


def _funzip_steps(defs):
    objs = " ".join("funzip_obj\\" + s.split("\\")[-1].replace(".c", ".obj")
                    for s in _FUNZIP_SOURCES)
    return [
        BuildStep("if not exist funzip_obj mkdir funzip_obj"),
        BuildStep("cl /nologo /c /O2 /MD /Zi /I. %s /DFUNZIP /Fofunzip_obj\\ "
                  "/Fdfunzip.pdb %s" % (defs, " ".join(_FUNZIP_SOURCES))),
        BuildStep(_LINK % ("funzip", "funzip", objs)),
    ]


def _recipe(version, url, sha256, name, sources, defs, upstream, notes,
            funzip=False):
    extra = _funzip_steps(defs) if funzip else []
    return Recipe(
        family="Info-ZIP",
        version=version,
        upstream=upstream,
        license="Info-ZIP",
        source=Source(url=url, sha256=sha256),
        build=[
            BuildStep(_CL % (defs, name, " ".join(sources))),
            BuildStep(_LINK % (name, name, _objs(sources))),
        ] + extra + [
            BuildStep("dir", allow_failure=True),
        ],
        artifacts=[Artifact(path=name + ".exe", component=name + ".exe",
                            pdb=name + ".pdb")] + (
            [Artifact(path="funzip.exe", component="funzip.exe",
                      pdb="funzip.pdb")] if funzip else []),
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
    # Info-ZIP's last public zip beta; a final 3.1 was never released (see
    # infozip.py). Source is SourceForge's zip31c.zip.
    "infozip_zip_3.1c_msvc": _recipe(
        "3.1c", "https://downloads.sourceforge.net/project/infozip/"
                "unreleased%20Betas/Zip%20betas/zip31c.zip",
        "fda6d0532c201597ea13ccdbcdc6f39b4a4ce666df0048e19f6b0f969aff398b",
        "zip", _ZIP31_SOURCES, _DEFS + " /DNO_ASM /DNO_ASM_CRC",
        "https://infozip.sourceforge.net/Zip.html",
        "zip.exe only (3.1c BETA, 22 June 2010: no final 3.1 exists), over the "
        "translation units the MinGW recipe links. Upstream's "
        "win32/makefile.w32 is not used: it defaults to a static CRT and this "
        "corpus builds /MD. USE_ZLIB is not set, so the image carries "
        "Info-ZIP's own deflate. Assembler fast paths disabled."),
    # The two earlier public zip betas, same translation units, defines and
    # makefile.w32 as 3.1c (diffed: only dates, the DLL targets and a
    # /OPT:NOWIN98 link switch differ in 3.1a).
    "infozip_zip_3.1a_msvc": _recipe(
        "3.1a", "https://downloads.sourceforge.net/project/infozip/"
                "unreleased%20Betas/Zip%20betas/zip31a.zip",
        "b68a8d1b3c759622cf9f9c01fa9823b041ed18a89c2e78eafc37991ab5428acf",
        "zip", _ZIP31_SOURCES, _DEFS + " /DNO_ASM /DNO_ASM_CRC",
        "https://infozip.sourceforge.net/Zip.html",
        "zip.exe only (3.1a BETA, 21 September 2008: an earlier public beta, "
        "no final 3.1 exists), over the translation units the MinGW recipe "
        "links. Upstream's win32/makefile.w32 is not used: it defaults to a "
        "static CRT and this corpus builds /MD. USE_ZLIB is not set, so the "
        "image carries Info-ZIP's own deflate. Assembler fast paths "
        "disabled."),
    "infozip_zip_3.1b_msvc": _recipe(
        "3.1b", "https://downloads.sourceforge.net/project/infozip/"
                "unreleased%20Betas/Zip%20betas/zip31b.zip",
        "44e931c10b1748cb43e4ea4fb7d58f134551a478f5f8afaf0f2cfb613adc25bb",
        "zip", _ZIP31_SOURCES, _DEFS + " /DNO_ASM /DNO_ASM_CRC",
        "https://infozip.sourceforge.net/Zip.html",
        "zip.exe only (3.1b BETA, 9 April 2009: an earlier public beta, no "
        "final 3.1 exists), over the translation units the MinGW recipe "
        "links. Upstream's win32/makefile.w32 is not used: it defaults to a "
        "static CRT and this corpus builds /MD. USE_ZLIB is not set, so the "
        "image carries Info-ZIP's own deflate. Assembler fast paths "
        "disabled."),
    "infozip_unzip_6.0_msvc": _recipe(
        "6.0", "https://downloads.sourceforge.net/infozip/unzip60.tar.gz",
        "036d96991646d0449ed0aa952e4fbe21b476ce994abc276e49d30e686708bd37",
        "unzip", _UNZIP_SOURCES, _DEFS + " /DIZ_CRCOPTIM_UNFOLDTBL",
        "https://infozip.sourceforge.net/UnZip.html",
        "unzip.exe and funzip.exe, over the translation units the MinGW "
        "recipe links. Upstream's win32/Makefile is not used: it defaults to "
        "a static CRT and this corpus builds /MD. Assembler CRC disabled.",
        funzip=True),
}


# --- The other programs upstream's nmake files build, and the x86 assembler
# fast paths: the MSVC counterparts of the "<v>-utils", "6.0-sfxdll" and
# "<v>-asm" recipes in infozip.py. Translation units and per-object defines
# are those of win32/makefile.w32 (zip) and win32/Makefile (unzip); the
# makefiles themselves are not used for the reason given above (static CRT
# by default). Separate versions so the shipped images are unchanged.
#
# zip utilities, makefile.w32 OBJU/OBJN/OBJC/OBJS: zipfile, fileio, util,
# crc32, crypt and win32/win32 again with -DUTIL (the *_.obj objects);
# globals, ttyio and win32/win32i64 as for zip.exe; each utility's own main.
_UTIL_SRC = "zipfile.c fileio.c util.c crc32.c crypt.c win32\\win32.c"
_UTIL_MAIN = ("globals.c ttyio.c win32\\win32i64.c zipcloak.c zipnote.c "
              "zipsplit.c")
_OBJU = ("u\\zipfile.obj u\\fileio.obj u\\util.obj u\\crc32.obj "
         "m\\globals.obj u\\win32.obj m\\win32i64.obj")
_UTIL_LINKS = {
    "zipnote": "m\\zipnote.obj " + _OBJU,
    "zipcloak": "m\\zipcloak.obj u\\crypt.obj m\\ttyio.obj " + _OBJU,
    "zipsplit": "m\\zipsplit.obj " + _OBJU,
}


def _zip_utils_msvc(base):
    import dataclasses
    recipe = RECIPES[base]
    defs = recipe.build_flags.split(", ", 1)[1].split(";")[0]
    steps = [
        BuildStep("if not exist u mkdir u"),
        BuildStep("if not exist m mkdir m"),
        BuildStep("cl /nologo /c /O2 /MD /Zi /I. %s /DUTIL /Fou\\ "
                  "/Fdutils.pdb %s" % (defs, _UTIL_SRC)),
        BuildStep("cl /nologo /c /O2 /MD /Zi /I. %s /Fom\\ /Fdutils.pdb %s"
                  % (defs, _UTIL_MAIN)),
    ]
    for name, objs in _UTIL_LINKS.items():
        steps.append(BuildStep(_LINK % (name, name, objs)))
    steps.append(BuildStep("dir", allow_failure=True))
    return dataclasses.replace(
        recipe, version=recipe.version + "-utils", build=steps,
        artifacts=[Artifact(path=n + ".exe", component=n + ".exe",
                            pdb=n + ".pdb")
                   for n in ("zipcloak", "zipnote", "zipsplit")],
        notes="zipcloak.exe, zipnote.exe and zipsplit.exe over the "
              "translation units of win32/makefile.w32's OBJC, OBJN and OBJS "
              "(zipfile, fileio, util, crc32, crypt and win32/win32 compiled "
              "with -DUTIL; globals, ttyio and win32/win32i64 as for "
              "zip.exe), with the zip.exe recipe's flags. The makefile is "
              "not used because it defaults to a static CRT. USE_ZLIB is not "
              "set. Assembler fast paths disabled.")


for _base in ("infozip_zip_3.0_msvc", "infozip_zip_3.1a_msvc",
              "infozip_zip_3.1b_msvc", "infozip_zip_3.1c_msvc"):
    RECIPES[_base.replace("_msvc", "-utils_msvc")] = _zip_utils_msvc(_base)


# unzipsfx (win32/Makefile OBJX, -DSFX) and unzip32.dll (OBJD, -DWINDLL
# -DDLL, exports from upstream's windll/windll32.def).
_SFX_SRC = ("unzip.c crc32.c crypt.c extract.c fileio.c globals.c inflate.c "
            "match.c process.c ttyio.c ubz2err.c win32\\win32.c "
            "win32\\win32i64.c win32\\nt.c").split()
_DLL_SRC = ("api.c crc32.c crypt.c explode.c extract.c fileio.c globals.c "
            "inflate.c list.c match.c process.c ubz2err.c unreduce.c "
            "unshrink.c zipinfo.c win32\\win32.c win32\\win32i64.c "
            "win32\\nt.c windll\\windll.c").split()
_UNZIP_DEFS = _DEFS + " /DIZ_CRCOPTIM_UNFOLDTBL"


def _in(directory, sources):
    return " ".join(directory + "\\" + s.split("\\")[-1].replace(".c", ".obj")
                    for s in sources)


RECIPES["infozip_unzip_6.0-sfxdll_msvc"] = Recipe(
    family="Info-ZIP",
    version="6.0-sfxdll",
    upstream="https://infozip.sourceforge.net/UnZip.html",
    license="Info-ZIP",
    source=RECIPES["infozip_unzip_6.0_msvc"].source,
    build=[
        BuildStep("if not exist sfx mkdir sfx"),
        BuildStep("cl /nologo /c /O2 /MD /Zi /I. %s /DSFX /Fosfx\\ "
                  "/Fdunzipsfx.pdb %s" % (_UNZIP_DEFS, " ".join(_SFX_SRC))),
        BuildStep(_LINK % ("unzipsfx", "unzipsfx", _in("sfx", _SFX_SRC))),
        BuildStep("if not exist dll mkdir dll"),
        BuildStep("cl /nologo /c /O2 /MD /Zi /I. %s /DWINDLL /DDLL "
                  "/Fodll\\ /Fdunzip32.pdb %s"
                  % (_UNZIP_DEFS, " ".join(_DLL_SRC))),
        BuildStep("link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO "
                  "/OPT:NOREF /OPT:NOICF /DEF:windll\\windll32.def "
                  "/PDB:unzip32.pdb /OUT:unzip32.dll %s user32.lib "
                  "advapi32.lib" % _in("dll", _DLL_SRC)),
        BuildStep("dir", allow_failure=True),
    ],
    artifacts=[Artifact(path="unzipsfx.exe", component="unzipsfx.exe",
                        pdb="unzipsfx.pdb"),
               Artifact(path="unzip32.dll", component="unzip32.dll",
                        pdb="unzip32.pdb")],
    toolchains=["msvc_x86", "msvc_x64"],
    build_flags="/O2 /MD /Zi, %s, /DSFX (unzipsfx) or /DWINDLL /DDLL "
                "(unzip32.dll, exports from windll/windll32.def); /DEBUG "
                "/Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link"
                % _UNZIP_DEFS,
    notes="unzipsfx.exe and unzip32.dll over the translation units of "
          "win32/Makefile's OBJX and OBJD with its per-target defines, from "
          "the unzip 6.0 tarball. The makefile is not used because it "
          "defaults to a static CRT. unzip does not use zlib. Assembler CRC "
          "disabled.",
)


# x86 assembler fast paths, upstream's x86 default: crc32 from
# win32/crc_i386.c (inline assembly, ASM_CRC) and, for zip, longest_match
# from win32/match32.asm (ASMV, which win32/osdep.h defines when NO_ASM is
# not), assembled with makefile.w32's own "ml -nologo -c -coff -Cx".
def _zip_asm_msvc(base, sources):
    import dataclasses
    recipe = RECIPES[base]
    defs = _DEFS + " /DASMV /DASM_CRC"
    srcs = [s for s in sources] + ["win32\\crc_i386.c"]
    return dataclasses.replace(
        recipe, version=recipe.version + "-asm",
        build=[BuildStep("ml /nologo /c /coff /Cx win32\\match32.asm"),
               BuildStep(_CL % (defs, "zip", " ".join(srcs))),
               BuildStep(_LINK % ("zip", "zip", _objs(srcs) + " match32.obj")),
               BuildStep("dir", allow_failure=True)],
        toolchains=["msvc_x86"],
        build_flags="/O2 /MD /Zi, %s, "
                    "win32/crc_i386.c, win32/match32.asm assembled with ml "
                    "/c /coff /Cx; /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF "
                    "/OPT:NOICF at link" % defs,
        notes="zip.exe with upstream's default x86 assembler fast paths "
              "(win32/makefile.w32 without NOASM): crc32 from the inline "
              "assembly in win32/crc_i386.c and longest_match from "
              "win32/match32.asm, over the translation units of the C-only "
              "MSVC recipe. x86 only. USE_ZLIB is not set.")


RECIPES["infozip_zip_3.0-asm_msvc"] = _zip_asm_msvc(
    "infozip_zip_3.0_msvc", _ZIP_SOURCES)
for _b in ("3.1a", "3.1b", "3.1c"):
    RECIPES["infozip_zip_%s-asm_msvc" % _b] = _zip_asm_msvc(
        "infozip_zip_%s_msvc" % _b, _ZIP31_SOURCES)

_UNZIP_ASM_DEFS = _UNZIP_DEFS + " /DASM_CRC"
_UNZIP_ASM_SRC = _UNZIP_SOURCES + ["win32\\crc_i386.c"]
_FUNZIP_ASM_SRC = _FUNZIP_SOURCES + ["win32\\crc_i386.c"]
RECIPES["infozip_unzip_6.0-asm_msvc"] = Recipe(
    family="Info-ZIP",
    version="6.0-asm",
    upstream="https://infozip.sourceforge.net/UnZip.html",
    license="Info-ZIP",
    source=RECIPES["infozip_unzip_6.0_msvc"].source,
    build=[
        BuildStep(_CL % (_UNZIP_ASM_DEFS, "unzip", " ".join(_UNZIP_ASM_SRC))),
        BuildStep(_LINK % ("unzip", "unzip", _objs(_UNZIP_ASM_SRC))),
        BuildStep("if not exist funzip_obj mkdir funzip_obj"),
        BuildStep("cl /nologo /c /O2 /MD /Zi /I. %s /DFUNZIP /Fofunzip_obj\\ "
                  "/Fdfunzip.pdb %s"
                  % (_UNZIP_ASM_DEFS, " ".join(_FUNZIP_ASM_SRC))),
        BuildStep(_LINK % ("funzip", "funzip", _in("funzip_obj",
                                                   _FUNZIP_ASM_SRC))),
        BuildStep("dir", allow_failure=True),
    ],
    artifacts=[Artifact(path="unzip.exe", component="unzip.exe",
                        pdb="unzip.pdb"),
               Artifact(path="funzip.exe", component="funzip.exe",
                        pdb="funzip.pdb")],
    toolchains=["msvc_x86"],
    build_flags="/O2 /MD /Zi, %s, win32/crc_i386.c; /DEBUG /Brepro "
                "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link"
                % _UNZIP_ASM_DEFS,
    notes="unzip.exe and funzip.exe with upstream's default x86 assembler "
          "CRC (win32/Makefile's APPLY_ASMCRC default: the inline assembly "
          "in win32/crc_i386.c, -DASM_CRC). x86 only. unzip does not use "
          "zlib.",
)
