"""POCO C++ Libraries 1.15.4 with MSVC v143 (tracker issue r0ny123/mcrit-data#22).

The MinGW recipe (poco.py) gives the reasons for its shape: the component set
that builds for Windows without an external dependency, built as static
libraries and linked whole into one DLL. This is the same tag, the same CMake
switches and the same shape, compiled by cl instead of GCC, so the two images
differ in the compiler and nothing else that a recipe chooses:

  * BUILD_SHARED_LIBS=OFF and POCO_MT=OFF: Poco's static libraries against
    the DLL C runtime (/MD; DefinePlatformSpecific.cmake names them
    Poco<Component>md.lib). MSVC could build Poco's own per-component DLLs,
    where GCC cannot, but one image per architecture keeps the pair
    comparable and is what the MinGW artefact is.
  * Every Poco<Component>md.lib the build writes is linked with
    /WHOLEARCHIVE into poco.dll around a one-line anchor translation unit,
    the MSVC spelling of the MinGW recipe's --whole-archive. The list is read
    from the build directory, as the MinGW link reads build-<arch>/lib.
  * Release with /MD /O2 /Ob2 /DNDEBUG /Zi; link /DEBUG /Brepro
    /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF; no /GL, no /LTCG.
  * The bundled dependencies stay bundled (sqlite3, pcre2, expat, zlib,
    double-conversion, utf8proc), as in the MinGW image, for the same reason:
    a Poco binary contains them.

Same deliberate omissions as poco.py: Crypto, NetSSL_OpenSSL and JWT (OpenSSL),
the MySQL, ODBC and PostgreSQL connectors, FastLogger, PDF and SevenZip; the
"full" variant (poco_full.py) is where those are built.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_FLAGS = "/MD /O2 /Ob2 /DNDEBUG /Zi"
_LINK = "/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"

_OPTIONS = ("-DBUILD_SHARED_LIBS=OFF -DPOCO_MT=OFF "
            "-DENABLE_TESTS=OFF -DENABLE_SAMPLES=OFF "
            "-DENABLE_CRYPTO=OFF -DENABLE_NETSSL=OFF -DENABLE_JWT=OFF "
            "-DENABLE_DATA_MYSQL=OFF -DENABLE_DATA_ODBC=OFF "
            "-DENABLE_DATA_POSTGRESQL=OFF -DENABLE_APACHECONNECTOR=OFF "
            "-DENABLE_FASTLOGGER=OFF -DENABLE_PDF=OFF -DENABLE_SEVENZIP=OFF")

_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          "-DCMAKE_BUILD_TYPE=Release "
          '-DCMAKE_C_FLAGS_RELEASE="%s" -DCMAKE_CXX_FLAGS_RELEASE="%s" '
          "-DCMAKE_MSVC_DEBUG_INFORMATION_FORMAT=ProgramDatabase "
          % (_FLAGS, _FLAGS))

# The anchor and the whole-archive link, in Python so the list of static
# libraries can be read from the build tree on cmd.exe. The Windows
# libraries are the ones Poco's own targets link.
_LINK_STEP = (
    'python -c "'
    "import glob,subprocess,sys;"
    "a=sys.argv[1];"
    "open('anchor.cpp','w').write('int poco_corpus_anchor(){return 0;}\\n');"
    "subprocess.check_call(['cl','/nologo','/c','/MD','/O2','/Zi',"
    "'/Fdanchor.pdb','anchor.cpp']);"
    "libs=sorted(glob.glob('build-'+a+'/lib/Poco*.lib'));"
    "print('\\n'.join(libs));"
    "subprocess.check_call(['link','/nologo','/DLL','/OUT:poco.dll',"
    "'/PDB:poco.pdb','anchor.obj']+['/WHOLEARCHIVE:'+l for l in libs]"
    "+['ws2_32.lib','iphlpapi.lib','mswsock.lib','advapi32.lib',"
    "'crypt32.lib','ole32.lib','oleaut32.lib','uuid.lib','user32.lib',"
    "'shell32.lib']+sys.argv[2].split())"
    '" {arch} "%s"' % _LINK)

RECIPES = {
    "poco_1.15.4_msvc": Recipe(
        family="poco",
        version="1.15.4",
        upstream="https://github.com/pocoproject/poco",
        license="BSL-1.0",
        source=Source(git_url="https://github.com/pocoproject/poco.git",
                      git_ref="poco-1.15.4-release"),
        build=[
            BuildStep(_CMAKE + _OPTIONS),
            BuildStep("cmake --build build-{arch}"),
            BuildStep("dir build-{arch}\\lib", allow_failure=True),
            BuildStep(_LINK_STEP),
        ],
        artifacts=[Artifact(path="poco.dll", component="poco.dll",
                            pdb="poco.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="%s (CMake Release, /Zi added), static Poco<Component>md "
                    "libraries linked with /WHOLEARCHIVE into one DLL; %s"
                    % (_FLAGS, _LINK),
        notes="MSVC v143 counterpart of poco_1.15.4 (MinGW): the same tag, "
              "component set and single-DLL shape (static libraries against "
              "the /MD runtime, linked whole into poco.dll around a one-line "
              "anchor), with Poco's bundled sqlite3, pcre2, expat, zlib, "
              "double-conversion and utf8proc compiled in as a real Poco "
              "binary has them. Crypto, NetSSL_OpenSSL, JWT, the MySQL, ODBC "
              "and PostgreSQL connectors, FastLogger, PDF and SevenZip are "
              "off as in the MinGW image. No upstream file is changed.",
    ),
}
