"""zlib 1.0.x - the pre-1.2 inflate, in two forms, for MinGW and Linux ELF.

data/libzlib carried 1.2.8 - 1.3.1 (and the ShiftMediaProject 1.2.x rows). zlib
rewrote inflate at 1.2.0, so the five inflate files of 1.0.4 (infblock,
infcodes, inffast, inftrees, infutil) exist in no 1.2 release, and a binary
carrying the old decompressor - Meterpreter's metsrv is the reported case -
matched nothing here. Measured on the artefacts rather than assumed: of the
62 - 76 functions per artefact at or above the corpus's ten-instruction
floor, 0 - 3 share a PicHash with any other libzlib artefact of the same
architecture (1.2.8 through 1.3.1, every compiler).

Two sources, because they are not the same code:

  * ``1.0.4-ppp2.4.9``: common/zlib.c from ppp-project/ppp at v2.4.9
    (4fb3190), the single-file zlib 1.0.4 derivative that carries a
    ``FILEVERSION 971210`` marker and the five functions Paul Mackerras added.
    It was removed from ppp later, so it is pinned by commit. It is one
    translation unit and has no gzio. 79 functions on MinGW x64.
  * ``1.0.4``: the zlib-1.0.4 tarball from zlib.net/fossils, fourteen files
    (every .c except example.c and minigzip.c). 97 functions on MinGW x64.

The two share only 13 - 17 PicHashes at the floor on any one compiler, so each
is worth having.

No source is modified and the only build settings are command-line options:

  * ``-Dlocal=`` (``/Dlocal=``). Both sources declare their internal routines
    ``local``, which is ``static`` unless defined otherwise - zutil.h and
    zlib.c both say "compile with -Dlocal if your debugger can't find static
    symbols". Without it the routines are inlined or merged and the artefact
    holds a fraction of the library. crc32.c redefines ``local`` itself, so a
    compiler warns (C4005 on cl) and its tables stay static; harmless.
  * Nothing for the dialect. GCC 13 compiles the K&R definitions and implicit
    ints of both as they are, with no -std=gnu89 or -fcommon, and cl does too;
    the only diagnostic either gave was the ``local`` redefinition above.
  * ``-DNO_DUMMY_DECL`` is not needed: ppp's file defines it itself.
  * The Linux build of 1.0.4 links with ``-nostdlib``. zutil.h declares
    ``extern int errno;``, which is a plain data reference, and glibc's errno
    is a TLS symbol, so the link stops with "TLS definition ... mismatches
    non-TLS reference". Every call site compiles identically either way; the
    flag only drops the libc link, which a .so that is never run does not
    need, and with it the crt glue (no _init/_fini noise).
  * The ELF builds use ``-fPIC -fvisibility=hidden`` so that calls between the
    library's own functions are direct rather than through the PLT, as the
    other ELF recipes here do.

No hand-written assembly: neither source ships any (ASMV is not defined).

ELF is built because the ppp file is Linux code - the marker comment names
"the Linux installation script" - and because it adds nothing the PE builds
duplicate: the ELF artefacts share no PicHash with any other family in the
corpus. It is the least evidenced axis; no malware sample is known to the
issue that is an ELF. They are small, 77 - 124 functions, and cost nothing.

On cross-family sharing, measured against MSVC, MinGW, libstdc++, liblzma,
bzip2, libpng, libtiff, libcurl, lz4, OpenSSL, libxml2 and mbedTLS: the ELF and
MSVC artefacts share nothing. The MinGW ones share one unnamed 15-instruction
body with every MinGW-built family - a linker stub the baseline cannot name.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_PPP_URL = "https://github.com/ppp-project/ppp.git"
_PPP_COMMIT = "4fb319056f168bb8379865b91b4fd3e1ada73f1e"

_SOURCES = ("adler32.c compress.c crc32.c deflate.c gzio.c infblock.c "
            "infcodes.c inffast.c inflate.c inftrees.c infutil.c trees.c "
            "uncompr.c zutil.c")

_PPP_MINGW = "{cc} -O2 -shared -Dlocal= -o ppp_zlib.dll common/zlib.c"
_PPP_LINUX = ("{cc} {archflag} -O2 -shared -fPIC -fvisibility=hidden "
              "-Dlocal= -o ppp_zlib.so common/zlib.c")
_Z104_MINGW = "{cc} -O2 -shared -Dlocal= -o zlib1.dll " + _SOURCES
_Z104_LINUX = ("{cc} {archflag} -O2 -shared -nostdlib -fPIC -fvisibility=hidden "
               "-Dlocal= -o libz.so " + _SOURCES)

_Z104_SOURCE = Source(
    url="https://zlib.net/fossils/zlib-1.0.4.tar.gz",
    sha256="e5c260cd3db1370fb3e0c193e9cbd9f127a9bd055d622b3fb55b82747f6e5b24")
_PPP_SOURCE = Source(git_url=_PPP_URL, git_ref=_PPP_COMMIT)


def _r(version, source, command, artifact, toolchains, upstream, flags, notes):
    return Recipe(
        family="libzlib", version=version, upstream=upstream, license="zlib",
        source=source, build=[BuildStep(command)], artifacts=[artifact],
        toolchains=toolchains, build_flags=flags, notes=notes)


_NOTE_PPP = ("common/zlib.c from ppp-project/ppp at v2.4.9, pinned by commit: "
             "the single-file zlib 1.0.4 derivative (FILEVERSION 971210) "
             "removed from ppp later. Built with -Dlocal= so its internal "
             "routines are kept as functions; no other source-level option "
             "was needed. See the module docstring.")
_NOTE_Z104 = ("The zlib 1.0.4 tarball, every .c file except example.c and "
              "minigzip.c, built with -Dlocal= so internal routines are kept "
              "as functions. The pre-1.2 inflate (infblock, infcodes, "
              "inffast, inftrees, infutil) exists in no other libzlib "
              "version here. The ELF build links -nostdlib because zutil.h "
              "declares errno as a plain extern, which glibc's TLS errno "
              "refuses at link time. See the module docstring.")


RECIPES = {
    "libzlib_1.0.4-ppp2.4.9": _r(
        "1.0.4-ppp2.4.9", _PPP_SOURCE, _PPP_MINGW,
        Artifact(path="ppp_zlib.dll", component="ppp_zlib.dll"),
        ["mingw_x86", "mingw_x64"], "https://github.com/ppp-project/ppp",
        "-O2 -Dlocal=", _NOTE_PPP),
    "libzlib_1.0.4-ppp2.4.9_linux": _r(
        "1.0.4-ppp2.4.9", _PPP_SOURCE, _PPP_LINUX,
        Artifact(path="ppp_zlib.so", component="ppp_zlib.so"),
        ["linux_x86", "linux_x64"], "https://github.com/ppp-project/ppp",
        "-O2 -fPIC -fvisibility=hidden -Dlocal=", _NOTE_PPP),
    "libzlib_1.0.4": _r(
        "1.0.4", _Z104_SOURCE, _Z104_MINGW,
        Artifact(path="zlib1.dll", component="zlib1.dll"),
        ["mingw_x86", "mingw_x64"], "https://github.com/madler/zlib",
        "-O2 -Dlocal=", _NOTE_Z104),
    "libzlib_1.0.4_linux": _r(
        "1.0.4", _Z104_SOURCE, _Z104_LINUX,
        Artifact(path="libz.so", component="libz.so"),
        ["linux_x86", "linux_x64"], "https://github.com/madler/zlib",
        "-O2 -fPIC -fvisibility=hidden -nostdlib -Dlocal=", _NOTE_Z104),
}
