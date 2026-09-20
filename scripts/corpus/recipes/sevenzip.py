"""7-Zip - one of the most embedded compression bodies on Windows.

7z.dll carries the archiver and every codec, including the LZMA
implementation that is among the most copy-pasted compression code in
Windows malware.

7-Zip publishes no checksums of its own; the digests recorded here were taken
from the fetched archives over HTTPS.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Three flags are all needed and none are obvious:
#   IS_MINGW=1  - the makefile infers this from $SystemDrive, absent on Linux
#   MSYSTEM=1   - otherwise it shells out to cmd.exe's del and mkdir
#   USE_ASM=    - the x64 assembly needs asmc (MASM syntax); nasm is not a
#                 drop-in substitute, so the hand-written LZMA/AES/CRC/SHA
#                 fast paths are absent from this build. Recorded in notes.
_MAKE = ("make -j$(nproc) -f ../../cmpl_gcc_{asm_arch}.mak IS_MINGW=1 "
         "MSYSTEM=1 USE_ASM= CROSS_COMPILE={prefix} RC={windres}")


def _sevenzip(version, code, sha256):
    return Recipe(
        family="7-Zip",
        version=version,
        upstream="https://www.7-zip.org/",
        license="LGPL-2.1-or-later, with unRAR restriction",
        source=Source(url="https://www.7-zip.org/a/7z%s-src.tar.xz" % code,
                      sha256=sha256),
        build=[
            BuildStep(_MAKE, cwd="CPP/7zip/Bundles/Format7zF"),
        ],
        artifacts=[Artifact(path="CPP/7zip/Bundles/Format7zF/b/g_{asm_arch}/7z.dll",
                            component="7z.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2, hand-written assembly disabled (needs asmc)",
        notes="USE_ASM= omits the assembly LZMA/AES/CRC/SHA fast paths, which "
              "need the MASM-syntax asmc assembler; nasm cannot substitute.",
    )


RECIPES = {
    # Extremely widely deployed.
    "7-Zip_23.01": _sevenzip(
        "23.01", "2301",
        "356071007360e5a1824d9904993e8b2480b51b570e8c9faf7c0f58ebe4bf9f74"),
    # Current.
    "7-Zip_26.03": _sevenzip(
        "26.03", "2603",
        "9cbde5099c6deb73691b0579063da5827522ccbbcba3f0020fd04e8c8c16c0d4"),
}
