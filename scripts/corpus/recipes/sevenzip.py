"""7-Zip - one of the most embedded compression bodies on Windows.

7z.dll carries the archiver and every codec, including the LZMA
implementation that is among the most copy-pasted compression code in
Windows malware.

7-Zip publishes no checksums of its own; the digests recorded here were taken
from the fetched archives over HTTPS.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Five settings are all needed and none are obvious:
#   IS_MINGW=1        - the makefile infers this from $SystemDrive, absent here
#   MSYSTEM=1         - otherwise it shells out to cmd.exe's del and mkdir
#   USE_ASM=          - the x64 assembly needs asmc (MASM syntax); nasm is not
#                       a drop-in substitute, so the hand-written
#                       LZMA/AES/CRC/SHA fast paths are absent. See notes.
#   LFLAGS_STRIP=     - 7zip_gcc.mak links with -s, which throws away the COFF
#                       symbol table this corpus depends on. 26.03 built
#                       cleanly that way and came back 16 of 5505 functions
#                       named.
#   CFLAGS_WARN_WALL= - the same file compiles with -Werror -Wall -Wextra, and
#                       GCC 13 rejects 23.01 outright over a -Wconversion
#                       warning in ComHandler.cpp that 26.03 later fixed.
#                       Diagnostics do not change the emitted code, so turning
#                       them off is a build setting; patching upstream to
#                       satisfy a newer compiler would not be.
_MAKE = ("make -j$(nproc) -f ../../cmpl_gcc_{asm_arch}.mak IS_MINGW=1 "
         "MSYSTEM=1 USE_ASM= CROSS_COMPILE={prefix} RC={windres} "
         "LFLAGS_STRIP= CFLAGS_WARN_WALL= %s")

# 23.01 spells five of the Windows import libraries with capitals -
# -lUser32, -lOle32, -lGdi32, -lComctl32, -lComdlg32, -lShell32 - which
# only resolve on a case-insensitive filesystem. mingw-w64 ships them
# lowercase, so the link fails on Linux. 26.03 lowercased them upstream,
# which is why only this version needs the list restated.
_LIB2_LOWERCASE = ('LIB2="-loleaut32 -luuid -ladvapi32 -luser32 -lole32 '
                   '-lgdi32 -lcomctl32 -lcomdlg32 -lshell32"')


def _sevenzip(version, code, sha256, extra=""):
    return Recipe(
        family="7-Zip",
        version=version,
        upstream="https://www.7-zip.org/",
        license="LGPL-2.1-or-later, with unRAR restriction",
        source=Source(url="https://www.7-zip.org/a/7z%s-src.tar.xz" % code,
                      sha256=sha256),
        build=[
            BuildStep(_MAKE % extra, cwd="CPP/7zip/Bundles/Format7zF"),
        ],
        artifacts=[Artifact(path="CPP/7zip/Bundles/Format7zF/b/g_{asm_arch}/7z.dll",
                            component="7z.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2, hand-written assembly disabled (needs asmc)",
        notes="USE_ASM= omits the assembly LZMA/AES/CRC/SHA fast paths, which "
              "need the MASM-syntax asmc assembler; nasm cannot substitute. "
              "Upstream's makefile strips the binary and compiles with "
              "-Werror; both are turned off, neither changes the emitted "
              "code.",
    )


RECIPES = {
    # Extremely widely deployed.
    "7-Zip_23.01": _sevenzip(
        "23.01", "2301",
        "356071007360e5a1824d9904993e8b2480b51b570e8c9faf7c0f58ebe4bf9f74",
        extra=_LIB2_LOWERCASE),
    # Current.
    "7-Zip_26.03": _sevenzip(
        "26.03", "2603",
        "9cbde5099c6deb73691b0579063da5827522ccbbcba3f0020fd04e8c8c16c0d4"),
}
