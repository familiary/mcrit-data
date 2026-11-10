"""LibreSSL 3.1.0, v141_xp, static runtime (/MT), sleep() removed. DRAFT.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from .libressl_v141xp_msvc import _CHECK, _NORMALISE, _SHA256, _VERSION

_POSIX_WIN_SHA256 = "b81e707758abf8db73410f07aed7c916fbec80116147614c289cf6ab108b382c"

# The one build-tree edit: sleep() is cut out of crypto/compat/posix_win.c,
# from its signature up to the #endif that closes the file. The file is
# checked against its upstream sha256 first, so the step fails on any other
# input (including a second run over an already edited tree, which no leg
# does: each architecture unpacks its own tree).
_DROP_SLEEP = (
    'python -c "'
    "import hashlib;"
    "p='crypto/compat/posix_win.c';"
    "b=open(p,'rb').read();"
    "h=hashlib.sha256(b).hexdigest();"
    "print('posix_win.c before',h,len(b));"
    "assert h=='%s',h;"
    "a=b.index(b'unsigned int sleep(unsigned int seconds)');"
    "e=b.index(b'#endif',a);"
    "print('removing',b[a:e]);"
    "n=b[:a]+b[e:];"
    "assert n.count(b'sleep')==0 and len(b)-len(n)==87,(len(b)-len(n));"
    "open(p,'wb').write(n);"
    "print('posix_win.c after',hashlib.sha256(n).hexdigest(),len(n))"
    '"' % _POSIX_WIN_SHA256)

_CRYPTO_CMAKE_SHA256 = "2655c6b64e263ee2f975dbc5b87a154d65c67fd3a7011c4ea7b4c20ae4fb8fd9"

# The export that goes with it. crypto/CMakeLists.txt appends sleep to the
# list the DLL's .def file is written from (EXTRA_EXPORT), so with the
# function gone the link stops at "crypto_p.def : error LNK2001: unresolved
# external symbol sleep" (run 42767147671). The static library the issue
# describes has no .def file; this line only matters because the image here
# is a DLL.
_DROP_SLEEP_EXPORT = (
    'python -c "'
    "import hashlib;"
    "p='crypto/CMakeLists.txt';"
    "b=open(p,'rb').read();"
    "h=hashlib.sha256(b).hexdigest();"
    "print('crypto/CMakeLists.txt before',h,len(b));"
    "assert h=='%s',h;"
    "l=b.split(b'\\n');"
    "d=[x for x in l if x.rstrip().endswith(b' sleep)')];"
    "print('removing',d);"
    "assert len(d)==1 and b'EXTRA_EXPORT' in d[0],d;"
    "n=b'\\n'.join(x for x in l if x is not d[0]);"
    "open(p,'wb').write(n);"
    "print('crypto/CMakeLists.txt after',hashlib.sha256(n).hexdigest(),len(n))"
    '"' % _CRYPTO_CMAKE_SHA256)

_COMMON = ('-T v141_xp -DCMAKE_GENERATOR_INSTANCE=C:/BT/vs15 '
           '-DBUILD_SHARED_LIBS=ON -DLIBRESSL_APPS=OFF -DLIBRESSL_TESTS=OFF '
           '-DLIBRESSL_SKIP_INSTALL=ON -DENABLE_ASM=ON '
           '-DCMAKE_C_FLAGS_RELEASE="/MT /O2 /Ob2 /DNDEBUG /Zi /Urestrict" '
           '-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
           '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

_CMAKE_X64 = ('cmake -S . -B build-x64 -G "Visual Studio 15 2017 Win64" '
              + _COMMON)
_CMAKE_X86 = ('cmake -S . -B build-x86 -G "Visual Studio 15 2017" -A Win32 '
              + _COMMON)

RECIPES = {
    "LibreSSL_3.1.0_msvc_v141xp_mt": Recipe(
        family="LibreSSL",
        version=_VERSION,
        upstream="https://www.libressl.org/",
        license="ISC (new code) over OpenSSL/SSLeay-licensed code, see COPYING",
        source=Source(
            url="https://ftp.openbsd.org/pub/OpenBSD/LibreSSL/libressl-%s.tar.gz"
                % _VERSION,
            sha256=_SHA256),
        build=[
            BuildStep(_CHECK),
            BuildStep(_DROP_SLEEP),
            BuildStep(_DROP_SLEEP_EXPORT),
            BuildStep('if "{arch}"=="x64" ' + _CMAKE_X64),
            BuildStep('if "{arch}"=="x86" ' + _CMAKE_X86),
            BuildStep("cmake --build build-{arch} --config Release "
                      "--target crypto ssl tls -- /m /v:n"),
            BuildStep(_NORMALISE),
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[
            Artifact(path="build-{arch}/libcrypto.dll", component="libcrypto-mt",
                     pdb="build-{arch}/libcrypto.pdb"),
            Artifact(path="build-{arch}/libssl.dll", component="libssl-mt",
                     pdb="build-{arch}/libssl.pdb"),
            Artifact(path="build-{arch}/libtls.dll", component="libtls-mt",
                     pdb="build-{arch}/libtls.pdb"),
        ],
        toolchains=["msvc141_x86", "msvc141_x64"],
        build_flags="DRAFT /MT",
        notes="DRAFT: /MT-compiled objects linked into DLLs; sleep() removed "
              "from crypto/compat/posix_win.c by the recipe; NOT byte-identical "
              "to a build of unmodified upstream.",
    ),
}
