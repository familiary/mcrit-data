"""7-Zip built with MSVC through upstream's own nmake build.

This is the one family in the MSVC wave where the new artefact contains code
the corpus does not have **in any form**, rather than a second rendering of
code it already has. The survey claimed that; it was checked here against the
pinned trees and it holds.

The MinGW recipe has to pass ``USE_ASM=`` because 7-Zip's hand-written fast
paths are MASM and need asmc under GCC. The nmake build assembles them with
ml/ml64 straight out of the makefiles. Read at 26.03 and confirmed identical
at 23.01:

  * ``CPP/Build.mak`` sets ``MY_ML = ml64 -WX`` for PLATFORM=x64 and
    ``ml -WX`` otherwise, and ``COMPL_ASM = $(MY_ML) -c -Fo$O/ $**``.
  * ``CPP/7zip/Asm.mak`` assembles ``$(ASM_OBJS)`` from
    ``Asm/x86/$(*B).asm``.
  * ``Aes.mak``, ``Crc.mak``, ``Crc64.mak``, ``Sha1.mak``, ``Sha256.mak`` and
    ``Sort.mak`` each put their module in ASM_OBJS unless USE_C_* or
    USE_NO_ASM is defined or the platform is arm/ia64/mips; ``LzFindOpt.mak``
    and ``LzmaDec.mak`` add two more for x64 only. So an x64 build assembles
    AesOpt, 7zCrcOpt, XzCrc64Opt, LzFindOpt, LzmaDecOpt, Sha1Opt, Sha256Opt
    and Sort - eight modules - and an x86 build the same minus LzFindOpt and
    LzmaDecOpt. ``Asm/x86/`` holds exactly those nine .asm files plus the
    shared 7zAsm.asm.
  * ``LzmaDec.mak`` additionally defines ``CFLAGS_C_SPEC =
    -DZ7_LZMA_DEC_OPT`` on x64, so even the C side of the LZMA decoder is
    compiled differently from the MinGW build.

None of that code is in data/7-Zip today.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

The other things read in Build.mak, all of which shape the command below:

  * ``O=$(PLATFORM)`` when PLATFORM is defined, and ``PROGPATH = $O\\$(PROG)``
    with ``PROG = 7z.dll`` from Format7zF/makefile - so the artefact is
    ``x64\\7z.dll`` or ``x86\\7z.dll``, and "x86" is the spelling Build.mak
    itself tests for when it picks /STACK.
  * ``-MD`` is selected by MY_DYNAMIC_LINK being non-empty; otherwise the
    build is ``-MT``, which would file the whole static MSVC C runtime under
    the 7-Zip name.
  * ``CFLAGS = $(CFLAGS_COMMON) $(CFLAGS)`` - CFLAGS_COMMON is upstream's own
    hook for extra compiler flags and is defined nowhere else in the tree, so
    it is where the debug format goes.
  * ``CFLAGS = ... $(CFLAGS_WARN_LEVEL) -WX ...`` with CFLAGS_WARN_LEVEL set
    to ``-Wall`` (MSVC's "every warning", not GCC's) and ``-WX`` hardcoded.
    This is the MSVC analogue of the ``CFLAGS_WARN_WALL=`` override the MinGW
    recipe already needs; it is set to ``-W0`` rather than emptied, because
    empty leaves cl at its default /W1 with /WX still in force. Diagnostics
    do not change the emitted code, so this is a build setting; patching
    upstream to satisfy a newer compiler would not be.
  * **``LFLAGS`` must not be set on the command line.** nmake gives a
    command-line macro precedence over every makefile assignment to the same
    name, and Build.mak builds LFLAGS up over eight assignments - among them
    ``LFLAGS = $(LFLAGS) -DLL -DEF:$(DEF_FILE)``, which is the only thing
    that makes this link a DLL at all. Setting LFLAGS would silently produce
    an .exe link and fail. The link rule is
    ``link $(LFLAGS) -out:$(PROGPATH) $(OBJS) $(LIBS)``, so the linker
    switches this corpus adds ride in on ``LIBS`` instead, which is last on
    the line. LIBS is likewise replaced rather than appended to, so
    Build.mak's own ``oleaut32.lib ole32.lib`` and ``user32.lib advapi32.lib
    shell32.lib`` are restated here; nothing else in the Format7zF chain adds
    to LIBS.

Upstream's LFLAGS carry ``-OPT:REF -OPT:ICF``. The ``-OPT:NOREF -OPT:NOICF``
at the end of LIBS are there to override them - link.exe takes the last
occurrence of an option, which is documented behaviour that could not be
exercised here. If that reading is wrong the build still succeeds and simply
produces upstream's folded binary, so it is a quality risk rather than a
failure risk.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# /Z7 rather than /Zi: Build.mak compiles with -MP$(NUMBER_OF_PROCESSORS), so
# several cl processes are writing at once, and /Z7 keeps the debug info in
# each .obj instead of funnelling it through one compiler PDB. link /DEBUG
# then builds the PDB from the objects. This is the same reasoning
# cryptopp_msvc.py records, arrived at there because objects were archived in
# between and here because they are compiled in parallel.
_CFLAGS_COMMON = '"CFLAGS_COMMON=-Z7"'

# See the module docstring: these ride on LIBS because LFLAGS cannot be
# touched without losing -DLL -DEF:. The five import libraries are Build.mak's
# own, restated because a command-line macro replaces the makefile's.
#
# -DEBUG so a PDB is written at all, -Brepro so the PE carries no build
# timestamp and two runs of identical source record the same sha256, and
# -OPT:NOREF -OPT:NOICF so unreferenced and identically-compiled routines both
# survive as separate reference samples.
_LIBS = ('"LIBS=oleaut32.lib ole32.lib user32.lib advapi32.lib shell32.lib '
         '-DEBUG -PDB:{asm_arch}\\7z.pdb -Brepro -OPT:NOREF -OPT:NOICF"')

_NMAKE = ("nmake -f makefile PLATFORM={asm_arch} MY_DYNAMIC_LINK=1 "
          "CFLAGS_WARN_LEVEL=-W0 %s %s" % (_CFLAGS_COMMON, _LIBS))

_BUILD_FLAGS = ("-O1/-O2 -MD -Z7 -EHsc -Gy -GR- -GF -GS- -W0 -WX -Gr -MP "
                "(CPP/Build.mak, with -MD selected by MY_DYNAMIC_LINK and the "
                "warning level lowered); MASM fast paths assembled with "
                "ml/ml64 -WX; -DEBUG -Brepro -OPT:NOREF -OPT:NOICF appended "
                "to upstream's link line")

# DOC/License.txt is not the same document in the two versions, so neither is
# this field - the same split the MinGW recipe records, and for the same
# reason: the third-party bodies are in the artefacts, not merely in the tree.
_LICENSE_23 = ("LGPL-2.1-or-later, with unRAR restriction; "
               "CPP/7zip/Compress/LzfseDecoder.cpp BSD-3-Clause")
_LICENSE_26 = ("LGPL-2.1-or-later, with unRAR restriction; "
               "CPP/7zip/Compress/LzfseDecoder.cpp and C/ZstdDec.c "
               "BSD-3-Clause; C/Xxh64.c BSD-2-Clause")

_NOTES = (
    "Built through upstream's nmake path, which assembles the hand-written "
    "MASM LZMA/AES/CRC/SHA fast paths that the MinGW recipe has to omit for "
    "want of asmc: AesOpt, 7zCrcOpt, XzCrc64Opt, Sha1Opt, Sha256Opt and Sort "
    "on both architectures, plus LzFindOpt and LzmaDecOpt on x64, where the "
    "C decoder is additionally compiled with -DZ7_LZMA_DEC_OPT. None of that "
    "code is in data/7-Zip today, in either architecture or either version. "
    "7z.dll is "
    "the whole archiver and every codec, so it carries the third-party "
    "bodies the licence field names - Apple's LZFSE decoder in both "
    "versions, and Zstd and xxHash in 26.03 - filed under the 7-Zip name, "
    "which is upstream's arrangement rather than this recipe's and matches "
    "what the MinGW artefacts already do. Built against the DLL runtime, so "
    "the MSVC C runtime is imported rather than linked in and stays "
    "attributed to data/MSVC. No external dependencies.")


def _sevenzip_msvc(version, code, sha256, license):
    return Recipe(
        family="7-Zip",
        version=version,
        upstream="https://www.7-zip.org/",
        license=license,
        # The same tarball and the same digest the MinGW recipe pins, taken
        # from the fetched archives over HTTPS because 7-Zip publishes no
        # checksums of its own.
        source=Source(url="https://www.7-zip.org/a/7z%s-src.tar.xz" % code,
                      sha256=sha256),
        build=[
            BuildStep(_NMAKE, cwd="CPP/7zip/Bundles/Format7zF"),
            # Cheap insurance, as in xz_msvc.py: build.py reports a missing
            # artefact by the path it expected and nothing else, and this
            # puts the names the build actually wrote into the log the
            # workflow prints on failure.
            BuildStep("dir {asm_arch}", cwd="CPP/7zip/Bundles/Format7zF",
                      allow_failure=True),
        ],
        artifacts=[Artifact(
            path="CPP/7zip/Bundles/Format7zF/{asm_arch}/7z.dll",
            component="7z.dll",
            pdb="CPP/7zip/Bundles/Format7zF/{asm_arch}/7z.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_BUILD_FLAGS,
        notes=_NOTES,
    )


RECIPES = {
    # Extremely widely deployed, and the generation most Windows binaries in
    # the field carry.
    "7-Zip_23.01_msvc": _sevenzip_msvc(
        "23.01", "2301",
        "356071007360e5a1824d9904993e8b2480b51b570e8c9faf7c0f58ebe4bf9f74",
        _LICENSE_23),
    # Current. Both versions are covered because their Build.mak files were
    # diffed and are identical in every line this recipe depends on - the
    # warning-level override, the MY_DYNAMIC_LINK test, the CFLAGS_COMMON
    # hook, the LFLAGS/LIBS split and the $O layout are the same - so a
    # second version does not add a second way for the recipe to be wrong.
    # What differs (23.01 defines UNICODE, 26.03 comments it out; 26.03 adds
    # arm64 branches and a /STACK guard) does not touch any of it.
    "7-Zip_26.03_msvc": _sevenzip_msvc(
        "26.03", "2603",
        "9cbde5099c6deb73691b0579063da5827522ccbbcba3f0020fd04e8c8c16c0d4",
        _LICENSE_26),
}
