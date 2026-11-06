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
  * the std::string variant (TIXML_USE_STL) is not built, as in MinGW.
  * /EHsc: both libraries throw nothing but use exception-safe C++ (new,
    STL-free); cl needs the switch to compile C++ without warning C4530.

Link line as in bzip2_msvc.py: /DLL /DEBUG /Brepro /INCREMENTAL:NO
/OPT:NOREF /OPT:NOICF, no /GL and no /LTCG, the PDB beside the DLL so SMDA can
name the non-exported functions.

PLACEHOLDER_MEASUREMENTS
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
_V1_DEF = (
    'python -c "'
    "import re,subprocess,glob;"
    "o=subprocess.check_output(['dumpbin','/symbols']+sorted(glob.glob('*.obj'))).decode();"
    "n=sorted({m.group(1) for m in re.finditer("
    r"r'SECT\w+\s+notype \(\)\s+External\s+\|\s+(\S+)',o)"
    " if m.group(1).startswith('?') and not m.group(1).startswith('??_')});"
    "open('tinyxml.def','w').write('EXPORTS\\n'+'\\n'.join(n)+'\\n');"
    "print(len(n),'exports')"
    '"')

_LINK_FLAGS = "/nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF"

_V1_LINK = ("link %s /DEF:tinyxml.def /PDB:tinyxml.pdb /OUT:tinyxml.dll %s"
            % (_LINK_FLAGS, _V1_OBJECTS))

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
            BuildStep("dir", allow_failure=True),
        ],
        artifacts=[Artifact(path="tinyxml.dll", component="tinyxml.dll",
                            pdb="tinyxml.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags=_FLAGS + ", exports from a generated .def",
        notes="Final SourceForge release, non-STL build, the same four "
              "library sources as the MinGW recipe, built by a direct cl. "
              "No export macro upstream, so the .def is generated from the "
              "objects at build time; nothing in the tree is patched.",
    ),
    "TinyXML2_6.2.0_msvc": _tinyxml2("6.2.0"),
    "TinyXML2_9.0.0_msvc": _tinyxml2("9.0.0"),
    "TinyXML2_11.0.0_msvc": _tinyxml2("11.0.0"),
}
