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
tinystr.cpp. The std::string variant (``-DTIXML_USE_STL``) is a different ABI
and a different body for every parser routine, so it is built as a second
artefact of recipe ``TinyXML_2.6.2`` (component ``tinyxml_stl.dll``)
rather than replacing the default one. Measured, counting functions of at least 10 instructions, the STL build shares **15 PicHashes of
134 (x86) and 13 of 115 (x64)** with the non-STL build; it keeps 263 / 223
functions (x86 / x64) after removing 159 / 156 of runtime glue (image totals
422 / 379), against 225 / 193 kept in the default build. A sample compiled
either way is recognised by only one of the two, which is why both are
shipped.

FOSSIL's reference build (Table III) is named "tinyXML 2.0.2". No such
release exists on SourceForge (the file listing has 1.2.4, 2.1.1 ... 2.6.2,
and ``tinyxml_2_0_2.zip`` returns 404), whereas leethomason/tinyxml2 has an
annotated tag ``2.0.2`` (commit b59ac45131eab3ad1f53b0d3ec60a98e8a96230a). That
tag is built as ``TinyXML2_2.0.2`` and is the likeliest referent; this is
stated as an inference, not a fact. Kept 221 / 220, removed 156 / 152 (totals
377 / 372, x86 / x64). It shares 30 / 19 PicHashes with 11.0.0, 31 / 23 with
6.2.0 and 31 / 23 with 9.0.0, and 4 / 2 with either TinyXML build, so it is a
distinct enough release to keep alongside the three existing ones.

TinyXML2 has eleven tags. Five were built (6.2.0, 8.0.0, 9.0.0, 10.0.0,
11.0.0) and compared by shared PicHashes (>= 10 instructions, x86 / x64,
percent of the smaller sample):

    6.2.0 ~ 8.0.0   84 / 79        8.0.0 ~ 9.0.0   86 / 84
    6.2.0 ~ 9.0.0   75 / 68        9.0.0 ~ 10.0.0 88 / 87
    6.2.0 ~ 11.0.0  65 / 52        9.0.0 ~ 11.0.0 85 / 66
    8.0.0 ~ 11.0.0  72 / 60        10.0.0 ~ 11.0.0 87 / 68

Three are kept (a fourth, 2.0.2, was added later for the FOSSIL reference
build; see above). 6.2.0 (2018) and 11.0.0 (current) are the ends of the range
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

The two new builds carry the same gaps (``printf``/``snprintf``/``sscanf``/
``fprintf`` instantiations, ``___chkstk_ms`` unnamed, ``_Unwind_Resume``).

No MSVC recipe: not trivial to verify without cl on this host.

Second pass: every other TinyXML release on SourceForge and the TinyXML2
tags 8.0.0 and 10.0.0, as versions of their own (flags per release in the
comment above TINYXML_RELEASES; nothing patched). Kept + removed = total (no
exclusions):

    1.2.4        tinyxml.dll            x86 121 + 123 = 244, x64 111 + 121 = 232
    2.1.1        tinyxml.dll            x86 163 + 64 = 227, x64 123 + 64 = 187
    2.1.1        tinyxml_stl.dll        x86 177 + 127 = 304, x64 148 + 123 = 271
    2.1.2        tinyxml.dll            x86 163 + 64 = 227, x64 123 + 64 = 187
    2.1.2        tinyxml_stl.dll        x86 165 + 124 = 289, x64 136 + 120 = 256
    2.1.3        tinyxml.dll            x86 167 + 64 = 231, x64 124 + 64 = 188
    2.1.3        tinyxml_stl.dll        x86 174 + 124 = 298, x64 140 + 120 = 260
    2.1.4        tinyxml.dll            x86 172 + 64 = 236, x64 124 + 64 = 188
    2.1.4        tinyxml_stl.dll        x86 177 + 124 = 301, x64 140 + 120 = 260
    2.1.5        tinyxml.dll            x86 172 + 62 = 234, x64 124 + 63 = 187
    2.1.5        tinyxml_stl.dll        x86 177 + 124 = 301, x64 140 + 120 = 260
    2.2.0-beta   tinyxml.dll            x86 179 + 155 = 334, x64 141 + 152 = 293
    2.2.0-beta   tinyxml_stl.dll        x86 194 + 158 = 352, x64 162 + 154 = 316
    2.2.1        tinyxml.dll            x86 179 + 155 = 334, x64 141 + 152 = 293
    2.2.1        tinyxml_stl.dll        x86 194 + 158 = 352, x64 162 + 154 = 316
    2.3.0-beta   tinyxml.dll            x86 179 + 156 = 335, x64 147 + 154 = 301
    2.3.0-beta   tinyxml_stl.dll        x86 190 + 158 = 348, x64 165 + 155 = 320
    2.3.1-beta   tinyxml.dll            x86 201 + 156 = 357, x64 162 + 154 = 316
    2.3.1-beta   tinyxml_stl.dll        x86 223 + 158 = 381, x64 186 + 155 = 341
    2.3.2        tinyxml.dll            x86 201 + 156 = 357, x64 162 + 154 = 316
    2.3.2        tinyxml_stl.dll        x86 223 + 158 = 381, x64 186 + 155 = 341
    2.3.3        tinyxml.dll            x86 211 + 156 = 367, x64 172 + 154 = 326
    2.3.3        tinyxml_stl.dll        x86 232 + 158 = 390, x64 197 + 155 = 352
    2.3.4        tinyxml.dll            x86 205 + 156 = 361, x64 170 + 154 = 324
    2.3.4        tinyxml_stl.dll        x86 234 + 157 = 391, x64 199 + 154 = 353
    2.4.0        tinyxml.dll            x86 206 + 157 = 363, x64 171 + 154 = 325
    2.4.0        tinyxml_stl.dll        x86 237 + 157 = 394, x64 198 + 154 = 352
    2.4.1        tinyxml.dll            x86 211 + 157 = 368, x64 173 + 154 = 327
    2.4.1        tinyxml_stl.dll        x86 237 + 157 = 394, x64 198 + 154 = 352
    2.4.2        tinyxml.dll            x86 210 + 157 = 367, x64 172 + 154 = 326
    2.4.2        tinyxml_stl.dll        x86 236 + 157 = 393, x64 197 + 154 = 351
    2.4.3        tinyxml.dll            x86 241 + 157 = 398, x64 194 + 154 = 348
    2.4.3        tinyxml_stl.dll        x86 276 + 158 = 434, x64 225 + 155 = 380
    2.5.0-beta   tinyxml.dll            x86 246 + 157 = 403, x64 200 + 154 = 354
    2.5.0-beta   tinyxml_stl.dll        x86 278 + 158 = 436, x64 226 + 155 = 381
    2.5.1        tinyxml.dll            x86 219 + 158 = 377, x64 189 + 155 = 344
    2.5.1        tinyxml_stl.dll        x86 271 + 159 = 430, x64 224 + 156 = 380
    2.5.3        tinyxml.dll            x86 223 + 158 = 381, x64 190 + 155 = 345
    2.5.3        tinyxml_stl.dll        x86 272 + 159 = 431, x64 224 + 156 = 380
    2.6.0        tinyxml.dll            x86 223 + 158 = 381, x64 192 + 155 = 347
    2.6.0        tinyxml_stl.dll        x86 262 + 159 = 421, x64 221 + 156 = 377
    2.6.1        tinyxml.dll            x86 223 + 158 = 381, x64 191 + 155 = 346
    2.6.1        tinyxml_stl.dll        x86 261 + 159 = 420, x64 221 + 156 = 377
    8.0.0        tinyxml2.dll           x86 279 + 156 = 435, x64 272 + 152 = 424
    10.0.0       tinyxml2.dll           x86 283 + 156 = 439, x64 293 + 155 = 448

Against the nearest other TinyXML image of the same architecture, between 6%
(2.3.4 x64, 7 of 118) and 97% (2.4.2 x86, 130 of 134) of the PicHashes of ten
instructions or more are shared, never the whole image. 2.5.2 is not
committed: PicHash-identical to 2.5.1, default and STL, both architectures.
TinyXML2 8.0.0 and 10.0.0 were dropped from the first revision for 79 to 88%
overlap with a kept neighbour; an overlap below 100% is committed.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_BUILD_V1 = ("{cxx} -O2 -shared -o tinyxml.dll tinyxml.cpp tinyxmlerror.cpp "
             "tinyxmlparser.cpp tinystr.cpp -shared-libgcc")
_BUILD_V1_STL = ("{cxx} -O2 -DTIXML_USE_STL -shared -o tinyxml_stl.dll "
                 "tinyxml.cpp tinyxmlerror.cpp tinyxmlparser.cpp tinystr.cpp "
                 "-shared-libgcc")
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
        build=[BuildStep(_BUILD_V1), BuildStep(_BUILD_V1_STL)],
        artifacts=[
            Artifact(path="tinyxml.dll", component="tinyxml.dll"),
            Artifact(path="tinyxml_stl.dll", component="tinyxml_stl.dll",
                     build_flags="-O2 -DTIXML_USE_STL"),
        ],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2",
        notes="Final SourceForge release compiled into a shared library "
              "from the four library sources: tinyxml.dll is the default "
              "non-STL build, tinyxml_stl.dll the std::string build "
              "(-DTIXML_USE_STL).",
    ),
    "TinyXML2_2.0.2": _tinyxml2("2.0.2"),
    "TinyXML2_6.2.0": _tinyxml2("6.2.0"),
    "TinyXML2_9.0.0": _tinyxml2("9.0.0"),
    "TinyXML2_11.0.0": _tinyxml2("11.0.0"),
}


# --- Every other TinyXML release on SourceForge, and the two TinyXML2 tags
# that were measured and dropped. The issue's "TinyXML 2.0.2" does not exist
# (no 2.0.2 folder under tinyxml/tinyxml/ and tinyxml_2_0_2.zip answers 404),
# so it is not built; every release that does exist is. The tarballs carry no
# published checksum; the sha256 values below were computed from the
# SourceForge downloads. SourceForge folder -> file: "<v>" or "<v> Beta" or
# "Beta <v>" -> tinyxml_<v with underscores>.tar.gz.
#
# Old sources against GCC 13, with compiler flags only (no source edit):
#   1.2.4   tinyxml.cpp/tinyxmlparser.cpp call strchr/strstr without
#           <string.h>: "'strchr' was not declared in this scope"; built with
#           -include string.h. It has no tinystr.cpp and no TIXML_USE_STL.
#   2.1.x   "extra qualification 'TiXmlDeclaration::' on member" (tinyxml.h)
#           and "cannot convert 'bool' to 'const char*' in return"
#           (tinyxmlparser.cpp, `return false;` from a const char* function,
#           valid C++98); built with -std=gnu++98 -fpermissive. The STL
#           build also uses std::istream/std::ostream after including only
#           <iosfwd>-level headers ("invalid use of incomplete type
#           'std::istream'"), so it adds -include iostream.
#   2.2.0+  compile as shipped, with the 2.6.2 recipe's command line.
TINYXML_RELEASES = {
    # version: (SourceForge folder, sha256 of the .tar.gz)
    "1.2.4": ("1.2.4", "5834783220ecdd118158ddccd6e21c88f929bd2edee3a12d16d904933e76db10"),
    "2.1.1": ("2.1.1", "effed167a0f37bcdeaacdabf51f48f108a954e8ff8fc0aa2ab7100514b141157"),
    "2.1.2": ("2.1.2", "1a5928da4a4cceb08d30944cbe042e5365e0664f473b9fe4e569882aeabd1536"),
    "2.1.3": ("2.1.3", "45612ab220f4307694c0f254bc236a49c5b83581d92e4a79ff4b8589cf6d36da"),
    "2.1.4": ("2.1.4", "4dbf7a4859447c9f7be3cd675ffdb64abbbf799a74e5c90873a93d5bbb17fe3f"),
    "2.1.5": ("2.1.5", "3d594d06f71d87751a30deff28c49c677b4cc5e0c0157ce7dbabbd4a1400225e"),
    "2.2.0-beta": ("Beta%202.2.0", "217d910a49da9152cdfc0abeb55a041c81aea35ef296ef9383931dc8ebbf9d18"),
    "2.2.1": ("2.2.1", "8b6c9cc3d5f4c2737ee98aaa618b4b685ee82fa41a1ba3cbd9c7d4b6230cd054"),
    "2.3.0-beta": ("2.3.0%20Beta", "01a47a96267b23e9944c3c6db184bf3790ac6e7d1425c5984aadcadd3199a88c"),
    "2.3.1-beta": ("2.3.1%20Beta", "115e2c480eaeae500af10c320c74d579289cdec3d95760fe003041b0ed9dceb4"),
    "2.3.2": ("2.3.2", "673724eacd4604c22d509ba6c16d2f779cd902f19d6d308550c1e3b50776b21c"),
    "2.3.3": ("2.3.3", "7a96bf547359d4b5ea6f2fdf4bd25e14252ba45cad3e409eb39193996dca357f"),
    "2.3.4": ("2.3.4", "75f0f4a9ba6e617519189761f7d196f6891ad8404ba5d09a0610f4c0a4db3139"),
    "2.4.0": ("2.4.0", "5f100316df96639008e668dad8918bdebe952168d25fa2632c50c2c680d30ad6"),
    "2.4.1": ("2.4.1", "c4861790c157a7d9ed230de7f82f5c6e3c861a67eb92c719dffea05d573a0dee"),
    "2.4.2": ("2.4.2", "873ddec4e4490c7923981714d3980cbd44e4879d882e55268878be1bfb801fce"),
    "2.4.3": ("2.4.3", "756aadcb378d5deb56003d6970a665de9f91386c5ba3a253684bea51c5bdc094"),
    "2.5.0-beta": ("2.5.0%20Beta", "93f74d103f155b993ada1a6aa966e9bb8735857901a0e3f4521fd4f033ef36f3"),
    "2.5.1": ("2.5.1", "7ba53c7eab44035d60beab1759310784a57f90820b42dbff09ebdfb988e5b78c"),
    "2.5.2": ("2.5.2", "a185a7728cc23279cfeeeb15b1bb3d410e8d3986cf81fd05de4d4841b4e07d1c"),
    "2.5.3": ("2.5.3", "c0b88bc5413e41ed566dab9f7a192e0e9e6060cc13ebdeab4766168559620d2b"),
    "2.6.0": ("2.6.0", "326971cd9d0f1cd12cfb9bcb3150848625506fb2c168765b8a3a88a9c7b084f2"),
    "2.6.1": ("2.6.1", "c9b85047fb3f5b86a0e313a4f2a21bdf7bdada32ba2df580cffb170029b27214"),
}


def tinyxml_source(version):
    folder, sha = TINYXML_RELEASES[version]
    number = version.split("-")[0]
    return Source(url="https://downloads.sourceforge.net/project/tinyxml/"
                      "tinyxml/%s/tinyxml_%s.tar.gz"
                      % (folder, number.replace(".", "_")), sha256=sha)


def tinyxml_sources(version):
    files = ["tinyxml.cpp", "tinyxmlerror.cpp", "tinyxmlparser.cpp"]
    return files if version == "1.2.4" else files + ["tinystr.cpp"]


def tinyxml_has_stl(version):
    return version != "1.2.4"


def _old_flags(version, stl):
    if version == "1.2.4":
        return "-include string.h"
    if version.startswith("2.1."):
        return "-std=gnu++98 -fpermissive" + (" -include iostream" if stl
                                              else "")
    return ""


def _tinyxml_old(version):
    srcs = " ".join(tinyxml_sources(version))
    steps, artifacts = [], []
    variants = [False, True] if tinyxml_has_stl(version) else [False]
    for stl in variants:
        dll = "tinyxml_stl.dll" if stl else "tinyxml.dll"
        flags = " ".join(f for f in ("-O2", "-DTIXML_USE_STL" if stl else "",
                                     _old_flags(version, stl)) if f)
        steps.append(BuildStep("{cxx} %s -shared -o %s %s -shared-libgcc"
                               % (flags, dll, srcs)))
        artifacts.append(Artifact(path=dll, component=dll, build_flags=flags))
    return Recipe(
        family="TinyXML",
        version=version,
        upstream="https://sourceforge.net/projects/tinyxml/",
        license="Zlib",
        source=tinyxml_source(version),
        build=steps,
        artifacts=artifacts,
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags=_old_flags(version, False) and
        "-O2 " + _old_flags(version, False) or "-O2",
        notes="SourceForge release %s (tinyxml_%s.tar.gz; sha256 computed "
              "from the download, none is published), compiled into a "
              "shared library from its library sources (%s) the way the "
              "2.6.2 recipe builds 2.6.2: tinyxml.dll is the default non-STL "
              "build%s. Any extra flag is a compiler option for GCC 13 over "
              "unmodified source and is in the artefact's build_flags; "
              "nothing is patched."
              % (version, version.split("-")[0].replace(".", "_"), srcs,
                 ", tinyxml_stl.dll the std::string build (-DTIXML_USE_STL)"
                 if tinyxml_has_stl(version) else
                 " (this release has no TIXML_USE_STL)"),
    )


# 2.5.2 is left out: its images, default and STL, both architectures, are
# PicHash-identical to 2.5.1's under MinGW and under MSVC, so they would add
# nothing.
for _v in TINYXML_RELEASES:
    if _v != "2.5.2":
        RECIPES["TinyXML_%s" % _v] = _tinyxml_old(_v)

# Measured and dropped in the first revision for overlapping a kept
# neighbour by 79 to 88%; an overlap below 100% is committed.
RECIPES["TinyXML2_8.0.0"] = _tinyxml2("8.0.0")
RECIPES["TinyXML2_10.0.0"] = _tinyxml2("10.0.0")
