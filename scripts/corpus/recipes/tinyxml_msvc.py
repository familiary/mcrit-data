"""TinyXML and TinyXML2 built with MSVC, beside the MinGW builds of the same
versions.

Both libraries are vendored into Windows software that is compiled with cl far
more often than with gcc, and data/TinyXML and data/TinyXML2 held MinGW
artefacts only. MinGW and MSVC lay out the same source differently, so a
cl-built sample was answered by GCC code (see jansson_msvc.py for the pilot
that measured the effect); hence this axis.

Same pins as tinyxml.py: the SourceForge zip with its sha256 for TinyXML
2.6.2, and tags 6.2.0, 9.0.0 and 11.0.0 for TinyXML2. A separate registry
entry rather than another toolchain on the MinGW recipe, for the reason in
sqlite3_msvc.py: one Recipe has one build list and these steps are cmd.exe.

Why a direct cl and not CMake. The MinGW recipes are one g++ line over the
library sources, and so are these: the two sets of artefacts then differ by
compiler and nothing else. TinyXML 2.6.2 has only a Makefile and Visual Studio
projects (it predates CMake support), and TinyXML2's CMakeLists.txt asks for
cmake 2.6 at 6.2.0 (refused by CMake 4) and builds test programs by default.
Reading the files rather than assuming:

  * TinyXML2 exports through its own macro: tinyxml2.h defines TINYXML2_LIB as
    __declspec(dllexport) when TINYXML2_EXPORT is defined, at all three tags,
    and CMake's DEFINE_SYMBOL "TINYXML2_EXPORT" is the same switch. Passing
    /DTINYXML2_EXPORT is what upstream's own shared build does, so no .def is
    needed there and nothing is patched.
  * TinyXML 2.6.2 has no export macro at all. The exports come from a .def
    that the first build step generates from the compiled objects (dumpbin
    /symbols, external defined C++-mangled functions, minus the compiler's
    ``??_`` vtable and deleting-destructor helpers; the C-linkage external
    COMDATs of the CRT's inline stdio wrappers are left out - exporting them
    fails the x86 link with LNK2001 on _fprintf, _sscanf_s and the like). It lives in the build tree beside the
    objects; no upstream file is touched. This is what the MinGW DLL's
    auto-export gives: every function, inline ones included.
  * upstream's own Release configuration (tinyxml_lib.vcxproj) is MaxSpeed
    with WIN32;NDEBUG, which is what /O2 /DWIN32 /DNDEBUG says here. The MinGW
    builds carry no -DNDEBUG, so the v1 assert() calls (tinyxml.cpp and
    tinyxmlparser.cpp use them) are compiled in there and not here: a real
    release difference between the two sets, kept deliberately because a
    cl-built sample would be a release build. The vcxproj asks for /MT, which
    the corpus does not use: /MD, so the CRT is imported and stays attributed
    to data/MSVC.
  * the std::string variant (-DTIXML_USE_STL) is a second artefact of the
    same recipe (tinyxml_stl.dll), objects in stl\\ and its own .def, as in
    MinGW.
  * /EHsc: both libraries throw nothing but use exception-safe C++ (new,
    STL-free); cl needs the switch to compile C++ without warning C4530.

Link line as in bzip2_msvc.py: /DLL /DEBUG /Brepro /INCREMENTAL:NO
/OPT:NOREF /OPT:NOICF, no /GL and no /LTCG, the PDB beside the DLL so SMDA can
name the non-exported functions.

Read back from the runner's build output (windows-2022, MSVC 19.44, v143):
the TinyXML2 builds link with no warning that matters, and the TinyXML v1 x86
link first failed with LNK2001 on nine inline-CRT symbols (see the .def note
above), fixed by the C++-only filter; x64 had linked cleanly either way.

Counted on the runner, kept + removed = image total (removed is the
baseline's compiler-runtime filter):

                    kept    removed    image
    TinyXML 2.6.2   x86  260   172   432      x64  315   179   494
    TinyXML2 6.2.0  x86  463   185   648      x64  470   191   661
    TinyXML2 9.0.0  x86  483   185   668      x64  492   189   681
    TinyXML2 11.0.0 x86  485   185   670      x64  494   189   683

What the baseline removed is MSVC runtime glue (DllMain, _DllMainCRTStartup,
the __scrt_* and __castguard_* families, __GSHandlerCheck and so on). What
survives, by name and PicHash: no unnamed function in any artefact. The named
non-TinyXML survivors are the UCRT's inline stdio wrappers, compiled into the
DLL because the headers define them inline, plus import thunks:
  - one-instruction thunks, all PicHash 1253497258561142223: fopen_s, ferror,
    fputc, fgetc, fwrite, isalpha, isdigit, isspace, isalnum, tolower, atof,
    atoi and, at x64, _fseeki64/_ftelli64 (the x86 names carry a leading
    underscore). Below the 10-instruction floor.
  - 10+ instruction wrappers, in TinyXML v1 only: the _snprintf_s<N> templates
    (N=32/64/256; 29 instructions at x64, 16 at x86) and three operator+
    (TiXmlString concatenation, real project code, 33-97 instructions).
    Reported, not patched: the baseline is shared tooling.
  - removed by the wide-stdio glue baseline, so absent from every artefact
    built with it: vsnprintf_s, _vsnprintf_s, _vsnprintf_s_l, _vsscanf_s_l,
    sscanf_s, vsscanf_s, __stdio_common_vsnprintf_s, and in TinyXML2 printf
    and vfprintf.

MinGW against MSVC, PicHash overlap over functions of 10+ instructions (same
version, same arch; mingw / msvc counts):

    TinyXML 2.6.2   x86 134 / 147   x64 115 / 148     shared 0 and 0
    TinyXML2 6.2.0  x86 171 / 202   x64 146 / 209     shared 0 and 0
    TinyXML2 9.0.0  x86 179 / 211   x64 153 / 218     shared 0 and 0
    TinyXML2 11.0.0 x86 181 / 213   x64 156 / 220     shared 0 and 0

The pair shares no exact function body, which is the case for holding the
MSVC axis at all.

Added later (backlog #24): the TIXML_USE_STL build and TinyXML2 2.0.2,
counted on the runner as above (kept + removed = image):

    TinyXML 2.6.2 tinyxml_stl  x86  296 + 1532 = 1828   x64  372 + 1538 = 1910
    TinyXML2 2.0.2             x86  397 +  185 =  582   x64  405 +  192 =  597

The STL build removes about 1.5k functions because every std::basic_string
and iostream instantiation the .def exports is in the baseline's list of
runtime functions; what stays is 321 TiXml* functions (x64), the
operator<< / operator>> stream operators, and, as a measured baseline gap
reported rather than patched, 20 ``std::basic_string<char,...>`` member
instantiations (11 to 108 instructions), ``std::operator==``,
``std::_Traits_find_ch``, ``__std_minmax_element_impl<1/2/3>`` (135 to 218
instructions) and ``__std_remove_4`` / ``_8`` (66), which are Microsoft's
STL and not TinyXML. PicHash overlap, 10+ instructions (x86 / x64): STL with
the default build 26 / 20 (of 147 / 148 distinct), 0 against its MinGW
counterpart; TinyXML2 2.0.2 with 6.2.0 36 / 37, 9.0.0 34 / 36 and 11.0.0 29 /
29, with either TinyXML build 1 / 2 (x86 / x64), 0 against the MinGW 2.0.2.
FOSSIL's "tinyXML 2.0.2" has no SourceForge release; it is the TinyXML2 tag
2.0.2, see tinyxml.py on the MinGW branch. validate --deep (these families plus cJSON, lz4, q3vm,
aPLib, bzip2): 0 problems apart from README links to families outside the
sparse checkout; no leakage.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_COMMON = "/nologo /c /O2 /MD /Zi /EHsc /DWIN32 /DNDEBUG /D_CRT_SECURE_NO_WARNINGS"

_V1_SOURCES = "tinyxml.cpp tinyxmlerror.cpp tinyxmlparser.cpp tinystr.cpp"
_V1_OBJECTS = _V1_SOURCES.replace(".cpp", ".obj")

_V1_COMPILE = "cl %s /Fdtinyxml.pdb %s" % (_COMMON, _V1_SOURCES)

# Export list from the objects. No % anywhere: cmd.exe would try to expand it.
# A function line of dumpbin /symbols reads
#   00B 00000000 SECT4 notype ()    External     | ?name@@...
# data symbols lack the "()" and undefined ones say UNDEF rather than SECTn.
def _v1_def(objects, out):
    return (
    'python -c "'
    "import re,subprocess,glob;"
    "o=subprocess.check_output(['dumpbin','/symbols']+sorted(glob.glob('%s'))).decode();" % objects +
    "n=sorted({m.group(1) for m in re.finditer("
    r"r'SECT\w+\s+notype \(\)\s+External\s+\|\s+(\S+)',o)"
    " if m.group(1).startswith('?') and not m.group(1).startswith('??_')});"
    "open('%s','w').write('EXPORTS\\n'+'\\n'.join(n)+'\\n');" % out +
    "print(len(n),'exports')"
    '"')


_V1_DEF = _v1_def("*.obj", "tinyxml.def")
_V1_STL_DEF = _v1_def("stl/*.obj", "tinyxml_stl.def")

_LINK_FLAGS = "/nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF"

_V1_LINK = ("link %s /DEF:tinyxml.def /PDB:tinyxml.pdb /OUT:tinyxml.dll %s"
            % (_LINK_FLAGS, _V1_OBJECTS))

# The TIXML_USE_STL build: objects in stl\ so they do not overwrite the default
# ones, its own PDB, .def and DLL.
_V1_STL_COMPILE = ("cl %s /DTIXML_USE_STL /Fostl\\ /Fdtinyxml_stl.pdb %s"
                   % (_COMMON, _V1_SOURCES))
_V1_STL_LINK = ("link %s /DEF:tinyxml_stl.def /PDB:tinyxml_stl.pdb "
                "/OUT:tinyxml_stl.dll stl\\*.obj" % _LINK_FLAGS)

_V2_COMPILE = ("cl %s /DTINYXML2_EXPORT /Fdtinyxml2.pdb tinyxml2.cpp" % _COMMON)
_V2_LINK = ("link %s /PDB:tinyxml2.pdb /OUT:tinyxml2.dll tinyxml2.obj"
            % _LINK_FLAGS)

_FLAGS = ("/O2 /MD /Zi /EHsc, -DWIN32 -DNDEBUG -D_CRT_SECURE_NO_WARNINGS; "
          "/DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link")


def _tinyxml2(version):
    return Recipe(
        family="TinyXML2",
        version=version,
        upstream="https://github.com/leethomason/tinyxml2",
        license="Zlib",
        source=Source(git_url="https://github.com/leethomason/tinyxml2.git",
                      git_ref=version),
        build=[
            BuildStep(_V2_COMPILE),
            BuildStep(_V2_LINK),
            BuildStep("dir", allow_failure=True),
        ],
        artifacts=[Artifact(path="tinyxml2.dll", component="tinyxml2.dll",
                            pdb="tinyxml2.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS + ", -DTINYXML2_EXPORT",
        notes="Same tag as the MinGW recipe. Single translation unit built "
              "by a direct cl, exported through upstream's own "
              "TINYXML2_EXPORT macro; the MSVC C runtime is imported and "
              "stays attributed to data/MSVC.",
    )


RECIPES = {
    "TinyXML_2.6.2_msvc": Recipe(
        family="TinyXML",
        version="2.6.2",
        upstream="https://sourceforge.net/projects/tinyxml/",
        license="Zlib",
        source=Source(
            url="https://downloads.sourceforge.net/project/tinyxml/tinyxml/"
                "2.6.2/tinyxml_2_6_2.zip",
            sha256="ac6bb9501c6f50cc922d22f26b02fab168db47521be5e845b83d3451a3e1d512"),
        build=[
            BuildStep(_V1_COMPILE),
            BuildStep(_V1_DEF),
            BuildStep(_V1_LINK),
            BuildStep("mkdir stl"),
            BuildStep(_V1_STL_COMPILE),
            BuildStep(_V1_STL_DEF),
            BuildStep(_V1_STL_LINK),
            BuildStep("dir", allow_failure=True),
        ],
        artifacts=[
            Artifact(path="tinyxml.dll", component="tinyxml.dll",
                     pdb="tinyxml.pdb"),
            Artifact(path="tinyxml_stl.dll", component="tinyxml_stl.dll",
                     pdb="tinyxml_stl.pdb",
                     build_flags=_FLAGS + ", -DTIXML_USE_STL, exports from a "
                                 "generated .def"),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS + ", exports from a generated .def",
        notes="Final SourceForge release, the same four library sources as "
              "the MinGW recipe, built by a direct cl: tinyxml.dll is the "
              "default non-STL build, tinyxml_stl.dll the std::string build "
              "(-DTIXML_USE_STL). "
              "No export macro upstream, so the .def is generated from the "
              "objects at build time; nothing in the tree is patched.",
    ),
    "TinyXML2_6.2.0_msvc": _tinyxml2("6.2.0"),
    "TinyXML2_9.0.0_msvc": _tinyxml2("9.0.0"),
    "TinyXML2_11.0.0_msvc": _tinyxml2("11.0.0"),
    "TinyXML2_2.0.2_msvc": _tinyxml2("2.0.2"),
}


# --- Every other TinyXML release, and TinyXML2 8.0.0 and 10.0.0: the MSVC
# counterparts of the recipes added to tinyxml.py (see there for the list
# and the sha256 values). The same command lines as the 2.6.2 recipe, with
# the per-object .def; 1.2.4 has no tinystr.cpp and no TIXML_USE_STL. Old
# sources that call strchr/strstr without <string.h> (1.2.4) get
# /FIstring.h, and the 2.1.x STL builds that use std::istream with only
# forward declarations get /FIiostream, the cl spellings of the MinGW
# recipes' -include; nothing is patched.
from .tinyxml import (TINYXML_RELEASES, tinyxml_has_stl, tinyxml_source,
                      tinyxml_sources)


def _old_fi(version, stl):
    if version == "1.2.4":
        return "/FIstring.h"
    if version.startswith("2.1.") and stl:
        return "/FIiostream"
    return ""


def _tinyxml_old_msvc(version):
    srcs = " ".join(tinyxml_sources(version))
    objs = srcs.replace(".cpp", ".obj")
    fi = _old_fi(version, False)
    steps = [
        BuildStep("cl %s %s /Fdtinyxml.pdb %s" % (_COMMON, fi, srcs)),
        BuildStep(_V1_DEF),
        BuildStep("link %s /DEF:tinyxml.def /PDB:tinyxml.pdb "
                  "/OUT:tinyxml.dll %s" % (_LINK_FLAGS, objs)),
    ]
    artifacts = [Artifact(path="tinyxml.dll", component="tinyxml.dll",
                          pdb="tinyxml.pdb",
                          build_flags=_FLAGS + (", " + fi if fi else "") +
                          ", exports from a generated .def")]
    if tinyxml_has_stl(version):
        fis = _old_fi(version, True)
        steps += [
            BuildStep("mkdir stl"),
            BuildStep("cl %s /DTIXML_USE_STL %s /Fostl\\ /Fdtinyxml_stl.pdb %s"
                      % (_COMMON, fis, srcs)),
            BuildStep(_V1_STL_DEF),
            BuildStep(_V1_STL_LINK),
        ]
        artifacts.append(Artifact(
            path="tinyxml_stl.dll", component="tinyxml_stl.dll",
            pdb="tinyxml_stl.pdb",
            build_flags=_FLAGS + ", -DTIXML_USE_STL" +
            (", " + fis if fis else "") + ", exports from a generated .def"))
    steps.append(BuildStep("dir", allow_failure=True))
    return Recipe(
        family="TinyXML",
        version=version,
        upstream="https://sourceforge.net/projects/tinyxml/",
        license="Zlib",
        source=tinyxml_source(version),
        build=steps,
        artifacts=artifacts,
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS + ", exports from a generated .def",
        notes="SourceForge release %s, the same library sources as the "
              "MinGW recipe (%s), built by a direct cl with the 2.6.2 MSVC "
              "recipe's command lines; the .def is generated from the "
              "objects at build time; nothing in the tree is patched."
              % (version, srcs),
    )


for _v in TINYXML_RELEASES:
    RECIPES["TinyXML_%s_msvc" % _v] = _tinyxml_old_msvc(_v)
RECIPES["TinyXML2_8.0.0_msvc"] = _tinyxml2("8.0.0")
RECIPES["TinyXML2_10.0.0_msvc"] = _tinyxml2("10.0.0")
