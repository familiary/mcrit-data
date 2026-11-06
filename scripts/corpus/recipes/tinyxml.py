"""TinyXML and TinyXML2 - the small C++ XML parsers behind a great deal of
embedded and game software, and measured in two independent studies of
library reuse in malware.

Two families, because they are two code bases. TinyXML (the SourceForge
project, final release 2.6.2) is the original: a DOM of TiXmlNode subclasses,
an optional std::string build and a hand-written UTF-8 parser. TinyXML2 is
Lee Thomason's rewrite with a pooled allocator, an XMLVisitor interface and a
different parser. Measured on the two MinGW builds, counting functions of at
least 10 instructions, TinyXML 2.6.2 shares **4 PicHashes of 134 on x86 and 2
of 115 on x64** with any TinyXML2 release (2-3%). Of those, only one is
project code: ``ConvertUTF32ToUTF8``, 60 instructions on x86 and 52 on x64,
which TinyXML2 inherited verbatim; the rest are compiler and C library glue
(see "Measured baseline gaps" below). One function in common is a shared
ancestor, not a shared family - hence two recipes, not one.

TinyXML is a single version: 2.6.2 was the last release (2011) and is what
every vendored copy and distro package is. Upstream publishes no checksum
beyond the file listing, and there is no GitHub repository for it
(git ls-remote on github.com/leethomason/tinyxml finds none), so the
SourceForge zip is pinned by a sha256 computed from the download. Its Makefile builds the four
translation units tinyxml.cpp, tinyxmlerror.cpp, tinyxmlparser.cpp and
tinystr.cpp; the std::string variant (TIXML_USE_STL) is a different ABI that
is not built here.

TinyXML2 has eleven tags. Five were built (6.2.0, 8.0.0, 9.0.0, 10.0.0,
11.0.0) and compared by shared PicHashes (>= 10 instructions, x86 / x64,
percent of the smaller sample):

    6.2.0 ~ 8.0.0   84 / 79        8.0.0 ~ 9.0.0   86 / 84
    6.2.0 ~ 9.0.0   75 / 68        9.0.0 ~ 10.0.0 88 / 87
    6.2.0 ~ 11.0.0  65 / 52        9.0.0 ~ 11.0.0 85 / 66
    8.0.0 ~ 11.0.0  72 / 60        10.0.0 ~ 11.0.0 87 / 68

Three are kept. 6.2.0 (2018) and 11.0.0 (current) are the ends of the range
and share only 52-65% of their functions; 9.0.0 is the middle, shared 66-85%
with the ends, and is the version Debian 12 and Ubuntu 22.04 package. 8.0.0
and 10.0.0 are each 79-88% identical to a kept neighbour and add nothing a
match against the others would miss, so they were dropped after measuring.

Neither library has a library target in a form this pipeline can use, and
upstream's CMake would add test programs. Both are built with a one-line
``g++ -shared`` over the library sources, with -shared-libgcc so that
libstdc++ is not linked in statically and attributed to the family. Upstream
defines no dllexport macro unless asked to, so mingw auto-exports everything
and the DLL keeps every function, inline ones included.

Measured baseline gaps (reported rather than patched; the baseline is shared
tooling). The MinGW glue baseline does not remove the following, which are
not TinyXML code:

  - the C++-mangled instantiations of mingw-w64's inline stdio wrappers:
    ``printf(char const*, ...)``, ``fprintf(_iobuf*, ...)``,
    ``sscanf(...)`` and ``snprintf(...)``. The baseline has the C names
    (``printf``), and a name mismatch keeps the function. x64 PicHashes:
    printf 680774687785349816 (19 instr), snprintf 16490718028979370955 (7),
    sscanf 12953795935183878673 (8); x86: printf 9440566005262149013 (13),
    snprintf 13452334924305760106 (12), sscanf 9556021495551873692 (10).
  - ``___chkstk_ms`` (libgcc stack probe), emitted with no symbol, so the
    baseline's name-and-hash rule can never match it: 15 instructions,
    x64 PicHash 12578432865501340970, x86 16132965489037543538.
  - ``_fseeki64`` (42 instr, x64 PicHash 3387019608030333217) and
    ``_ftelli64`` (13 instr, 9289892874017894878), from libmingwex, in the
    9.0.0 and 11.0.0 builds (x64 checked).
  - operator new/delete and ``_Unwind_Resume`` thunks (1 instruction).

No MSVC recipe: not trivial to verify without cl on this host.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_BUILD_V1 = ("{cxx} -O2 -shared -o tinyxml.dll tinyxml.cpp tinyxmlerror.cpp "
             "tinyxmlparser.cpp tinystr.cpp -shared-libgcc")
_BUILD_V2 = "{cxx} -O2 -shared -o tinyxml2.dll tinyxml2.cpp -shared-libgcc"


def _tinyxml2(version):
    return Recipe(
        family="TinyXML2",
        version=version,
        upstream="https://github.com/leethomason/tinyxml2",
        license="Zlib",
        source=Source(git_url="https://github.com/leethomason/tinyxml2.git",
                      git_ref=version),
        build=[BuildStep(_BUILD_V2)],
        artifacts=[Artifact(path="tinyxml2.dll", component="tinyxml2.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2",
        notes="Single-file library compiled into a shared library by a "
              "direct g++ invocation; no upstream build system is used.",
    )


RECIPES = {
    "TinyXML_2.6.2": Recipe(
        family="TinyXML",
        version="2.6.2",
        upstream="https://sourceforge.net/projects/tinyxml/",
        license="Zlib",
        source=Source(
            url="https://downloads.sourceforge.net/project/tinyxml/tinyxml/"
                "2.6.2/tinyxml_2_6_2.zip",
            sha256="ac6bb9501c6f50cc922d22f26b02fab168db47521be5e845b83d3451a3e1d512"),
        build=[BuildStep(_BUILD_V1)],
        artifacts=[Artifact(path="tinyxml.dll", component="tinyxml.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2",
        notes="Final SourceForge release, non-STL build, compiled into a "
              "shared library from the four library sources.",
    ),
    "TinyXML2_6.2.0": _tinyxml2("6.2.0"),
    "TinyXML2_9.0.0": _tinyxml2("9.0.0"),
    "TinyXML2_11.0.0": _tinyxml2("11.0.0"),
}
