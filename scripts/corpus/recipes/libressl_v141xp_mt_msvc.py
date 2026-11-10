"""LibreSSL 3.1.0, v141_xp, with the static C runtime (/MT) and sleep() removed.

Tracker r0ny123/mcrit-data#61 describes LibreSSL 3.1.0 as it is linked
statically by the consumer the issue is about: static libraries (crypto-46,
ssl-48, tls-20 .lib) built with the v141_xp toolset, with two changes to
the upstream tree - USE_STATIC_MSVC_RUNTIMES (/MT) in CMakeLists.txt and
the sleep() function taken out of crypto/compat/posix_win.c.
libressl_v141xp_msvc.py is the stock build of that version and toolset (/MD,
sleep() kept); this recipe adds the configuration with both changes, beside
it, as the components libcrypto-mt, libssl-mt and libtls-mt. Library code
only: no consumer project is fetched, built or included. Source pin, toolset
install, generator and CMake version are those of libressl_v141xp_msvc.py
(its docstring has the details); what differs is below.

NOT byte-identical to a build of unmodified upstream. The recipe edits the
unpacked tree before configuring, two deletions and nothing else, each
guarded by the sha256 of the file as shipped:

    --- crypto/compat/posix_win.c   (sha256 b81e7077...b382c -> a25395da...dbc17)
    @@ -242,10 +242,4 @@
     	return 0;
     }
     
    -unsigned int sleep(unsigned int seconds)
    -{
    -	Sleep(seconds * 1000);
    -	return seconds;
    -}
    -
     #endif

    --- crypto/CMakeLists.txt       (sha256 2655c6b6...b8fd9 -> 3b53b65c...644bd)
    @@ -808,7 +808,6 @@
     	set(EXTRA_EXPORT ${EXTRA_EXPORT} posix_write)
     	set(EXTRA_EXPORT ${EXTRA_EXPORT} posix_getsockopt)
     	set(EXTRA_EXPORT ${EXTRA_EXPORT} posix_setsockopt)
    -	set(EXTRA_EXPORT ${EXTRA_EXPORT} sleep)
     endif()

The first is the change the issue names. The second exists only because the
image is a DLL: that line puts sleep into the .def file, and with the
function gone the link stops at "crypto_p.def : error LNK2001: unresolved
external symbol sleep" / "fatal error LNK1120: 1 unresolved externals" (run
42767147671, both architectures). A static library has no .def file. The
declaration in include/compat/unistd.h is left alone, and nothing in
crypto/, ssl/ or tls/ calls sleep().

/MT without touching CMakeLists.txt. The stock 3.1.0 tree has no
USE_STATIC_MSVC_RUNTIMES option, so passing it would do nothing; what the
option stands for is /MT in place of /MD, and that is given on the command
line: CMAKE_C_FLAGS_RELEASE="/MT /O2 /Ob2 /DNDEBUG /Zi /Urestrict", the
stock recipe's string with one letter changed (cmake_minimum_required is
3.0, so CMP0091 is OLD and the runtime flag is taken from there). Read back
from the build logs of run 42768243092: every cl line carries /MT and none
/MD; 0 errors on the three targets of both architectures; ml64 assembles
the same 15 modules on x64 and x86 is C only (OPENSSL_NO_ASM), as in the
stock build; link /INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF /DLL
/SUBSYSTEM:CONSOLE,"5.01" (x86) or "5.02" (x64); no /GL, no /LTCG. /MT is an
exception to this corpus's /MD rule, made because it is the configuration
the issue asks for; the /MD build stays beside it.

The image is a DLL, not the .lib. SMDA reads PE images, not COFF archives,
so the /MT-compiled objects are linked into crypto-46.dll, ssl-48.dll and
tls-20.dll exactly as the stock recipe links them (BUILD_SHARED_LIBS=ON; the
tree compiles one set of objects either way and uses no dllexport or
*_EXPORTS definition). What a DLL adds to the objects is its import thunks:
libssl and libtls reach libcrypto through one-instruction jumps, as in the
stock images.

The C runtime is not counted as LibreSSL. /MT links the static UCRT
(10.0.10240, what the XP toolset selects) and vcruntime 14.16 into each of
the three DLLs: 2985 to 3806 functions per image beside the library's own.
Two filters remove them. The glue baseline (name and PicHash both equal to
a probe's) takes 1216 to 1466 per image; its probes are measured against
UCRT 10.0.26100 and do not link all of the runtime, so the rest passes it.
That rest goes by name, Recipe.exclude_functions with the patterns of
_libressl_static_crt.py, whose docstring states the rule and its evidence:
the /MD image of the same tarball, compiler and flags imports the runtime,
so a name the /MD image lacks is not LibreSSL's. Measured on the imported
images:

  * kept + removed (baseline) + excluded (by name) = image total, x86 | x64:

        libcrypto-mt  5122+1466+2340=8928 | 5146+1446+2330=8922
        libssl-mt     1256+1219+1791=4266 | 1267+1216+1769=4252
        libtls-mt      321+1270+1991=3582 |  322+1261+1975=3558

    against the stock /MD images' kept counts 5145, 1258, 327 | 5168, 1271,
    328. The patterns match no function name of the six /MD images except
    26 x64 names that are import thunks of the C runtime there.
  * Kept names the /MD image of the same component does not have: the
    kernel32 import thunks GetFullPathNameW and GetModuleFileNameA (one
    instruction each, one or two per image; each is LibreSSL's own import in
    one component and the runtime's in the others, so they are not in the
    pattern) and, in the x64 libcrypto, general_allocate_string
    (crypto/ui/ui_lib.c, 53 instructions), which is LibreSSL's. Nothing
    else. No unnamed function on x86; the 35 on x64 are libcrypto's MASM
    routines, 35 in the /MD image too.
  * Against data/MSVC (2015, 2017 and 2019 Pro images): of the kept
    functions of 10 or more instructions, 15 of 4417 on x86 and 0 of 3770
    on x64 share a PicHash with it; the 15 are LibreSSL functions of 10 to
    12 instructions (ASN1_item_i2d, ssl3_read ...) and the same 15 match
    from the /MD images. data/MSVC does not identify the removed runtime
    either (of the 1704 named functions of 10+ instructions that only
    the /MT x86 libcrypto has, 1 has a hash in it), so the exclusion rests
    on names, not on hashes.
  * Not kept, for comparison with /MD: sleep (removed at source), and the
    import thunks of the C runtime (_strerror, __read ...), which no longer
    exist.

PicHash overlap with the stock /MD images of this version, functions of 10
or more instructions, distinct hashes, /MT | /MD | shared:

    x86  libcrypto 3040 | 3046 | 2425   libssl 698 | 696 | 577   libtls 131 | 131 | 85
    x64  libcrypto 2786 | 2787 | 2123   libssl 616 | 616 | 481   libtls 110 | 110 | 63
    union of the three: x86 3860 | 3864 | 3079, x64 3508 | 3509 | 2664

So about a fifth of the bodies (781 of 3860 hashes on x86, 844 of 3508 on
x64) differ from the /MD build although the source differs by one function:
under /MD a call into the runtime is an indirect call through the import
table, under /MT a direct one, and every function that calls malloc, free,
memcpy or a stdio routine changes with it. None of the six images is
PicHash-identical to its /MD sibling.

Runs. 42767147671: the LNK2001 above (nothing built). 42768243092: built,
no exclusion yet; the measurement the name lists come from (kept 7462,
3047, 2312 | 7476, 3036, 2297). 42770252734: the imported one, same
binaries filtered. Each run exits non-zero with every artefact built, for
the three baseline probes that cannot build with cl 19.16
(libressl_v141xp_msvc.py). Two recipes rather than one because the x86
pattern also drops unnamed functions and the x64 one must not.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._libressl_static_crt import STATIC_CRT_X64, STATIC_CRT_X86
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

_BUILD_FLAGS = (
    "v141_xp platform toolset (MSVC 14.16.27023, cl 19.16.27054; Windows 7.1A "
    "SDK, UCRT 10.0.10240) through the Visual Studio 15 2017 generator; /MT "
    "/O2 /Ob2 /DNDEBUG /Zi /Urestrict, /W4 /MP /GS from upstream and MSBuild, "
    "/Oy- on x86 added by MSBuild; /INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF "
    "/OPT:NOICF at link, /SUBSYSTEM 5.01 (x86) / 5.02 (x64); no /GL, no "
    "/LTCG; x64 MASM assembly (generator name Win64), x86 C only; build-tree "
    "edit: sleep() removed from crypto/compat/posix_win.c and its export "
    "line from crypto/CMakeLists.txt")

_NOTES = (
    "The configuration tracker #61 describes for the static LibreSSL 3.1.0 "
    "libraries: static C runtime (/MT, what USE_STATIC_MSVC_RUNTIMES=ON "
    "selects) and sleep() removed from crypto/compat/posix_win.c. The image "
    "is NOT byte-identical to a build of unmodified upstream: the recipe "
    "deletes that function (87 bytes of source) and, because the image is a "
    "DLL, the line of crypto/CMakeLists.txt that exports it; nothing else in "
    "the tree is touched and no consumer project is fetched or built. SMDA "
    "cannot read a .lib archive, so the image is a DLL (crypto-46, ssl-48, "
    "tls-20) carrying the /MT-compiled objects, not the .lib itself. The "
    "statically linked C runtime is not counted as LibreSSL: the glue "
    "baseline removes what its probes link and the rest is removed by name "
    "(exclude_functions; kept + removed + excluded = image total, see the "
    "recipe docstring). The stock /MD build of the same tarball is the "
    "libcrypto/libssl/libtls row of this version.")

_CMAKE_X64 = ('cmake -S . -B build-x64 -G "Visual Studio 15 2017 Win64" '
              + _COMMON)
_CMAKE_X86 = ('cmake -S . -B build-x86 -G "Visual Studio 15 2017" -A Win32 '
              + _COMMON)


def _recipe(arch, exclude):
    return Recipe(
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
            BuildStep(_CMAKE_X64 if arch == "x64" else _CMAKE_X86),
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
        toolchains=["msvc141_%s" % arch],
        exclude_functions=list(exclude),
        build_flags=_BUILD_FLAGS,
        notes=_NOTES,
    )


RECIPES = {
    "LibreSSL_3.1.0_msvc_v141xp_mt_x86": _recipe("x86", STATIC_CRT_X86),
    "LibreSSL_3.1.0_msvc_v141xp_mt_x64": _recipe("x64", STATIC_CRT_X64),
}
