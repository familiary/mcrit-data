"""LibreSSL 3.1.0 built with the Visual Studio 2017 XP toolset (v141_xp).

Tracker r0ny123/mcrit-data#61 evidences LibreSSL 3.1.0 (crypto-46, ssl-48,
tls-20) linked into Meterpreter's ext_server_python.dll, built with the
v141_xp toolset. The other MSVC LibreSSL recipes (libressl_msvc.py) are v143
builds of four other versions; this one is the evidenced version on the
evidenced toolset, on both architectures (v141_xp has an x64 target: the
Windows 7.1A SDK carries x64 libraries, subsystem 5.02).

Source. libressl-3.1.0.tar.gz from ftp.openbsd.org (the same file is on
cdn.openbsd.org), sha256 f91aad0c8fb9cbc67c910ad6dcffb401a819b4fd122007ea7f978638db044cf6,
which equals the entry in the server's SHA256 file. crypto/VERSION 46:1:0,
ssl/VERSION 48:1:0, tls/VERSION 20:1:0, so the DLLs are crypto-46.dll,
ssl-48.dll and tls-20.dll, the names the issue quotes for the .lib files.

Stock build, not Meterpreter's. The issue names two upstream modifications
in meterpreter-deps: USE_STATIC_MSVC_RUNTIMES (/MT) added to CMakeLists.txt
and the sleep() function removed from crypto/compat/posix_win.c. Neither is
applied: the runtime is /MD (corpus rule; the C runtime stays attributed to
data/MSVC), and posix_win.c is compiled as shipped, so this image carries
LibreSSL's own sleep() which ext_server_python.dll does not. Shared
libraries rather than the static .lib files Meterpreter links, because SMDA
needs a PE image; the DLLs export what crypto.sym/ssl.sym/tls.sym list.
Nothing in the tree is patched.

Toolset. The windows-2022 image has no VS 2017 (vswhere lists only VS 2022
Enterprise before the install), so the Build Tools are installed on the runner from the pinned VS 2017 bootstrapper (sha256
79166ebaee58c28f280a7d810af3557a8a3e3f7d2ac298e20504d36d6bf6b3ae, the one
PR #120's MSVC_oldtoolsets recipes use) into C:\\BT\\vs15 with
--add Microsoft.VisualStudio.Workload.VCTools,
Microsoft.VisualStudio.Component.VC.CoreBuildTools,
Microsoft.VisualStudio.Component.VC.Tools.x86.x64 (MSVC 14.16.27023),
Microsoft.VisualStudio.Component.WinXP (the v141_xp platform toolsets for
Win32 and x64 and the Windows 7.1A SDK) and
Microsoft.VisualStudio.Component.VC.ATL (only so the glue baseline's ATL probes build). The two components alone,
without the VC Tools workload, are not enough: that install has no VC core
build tools, so its vcvarsall.bat put no cl on PATH
(Common7\\Tools\\vsdevcmd\\ext held only netfxsdk.bat and roslyn.bat; scratch
runs 42674927927 and 42678836328) and MSBuild stopped at configure with
MSB4019 on the missing VCTargets\\Microsoft.Cpp.Default.props (run
42682829582). With the workload the install took 76 and 102 s in the two
probe jobs, ext\\vcvars.bat and Microsoft.Cpp.Default.props are present,
and a gating probe job (run 42686111161) built a hello.c through this
generator with -T v141_xp on both architectures (subsystem/OS version 5.01 x86, 5.02
x64; 6.00 with -T v141). The build job then runs inside that install's own
vcvarsall.bat (cl 19.16.27054), so corpus.toolchain registers msvc141, the
glue baseline is measured with that compiler, and the file names say
msvc141. The recipe declares msvc141_x86/msvc141_x64, so a runner whose
developer environment is VS 2022 skips it as "toolchain absent" instead of
building it with the wrong compiler (and a run asked to build only this
recipe there exits non-zero, having produced nothing). The installer step
and that environment live in the scratch workflow job (build-v141xp on
scratch/libressl-v141xp) that produced the artefacts, not in this branch's
workflow; the payloads the bootstrapper downloads are not pinned.

The other route was measured too: adding Microsoft.VisualStudio.Component.VC.v141.x86.x64
and Microsoft.VisualStudio.Component.WinXP to the preinstalled VS 2022 with
vs_installer.exe modify works (exit 0 after 367 s, hello.c builds with
"Visual Studio 17 2022" -A Win32 -T v141_xp), but that generator name has no
"Win64" spelling, so 3.1.0 would lose its x64 assembly (below).

Generator. "Visual Studio 15 2017 Win64" on x64 and "Visual Studio 15 2017"
-A Win32 on x86, with -T v141_xp and CMAKE_GENERATOR_INSTANCE=C:/BT/vs15.
The generator name matters: 3.1.0's CMakeLists.txt selects the MASM sources
only when CMAKE_GENERATOR matches "Win64" (it does not look at
CMAKE_GENERATOR_PLATFORM, unlike 3.3 and later), and CMake 4.0 removed the
platform-in-name spelling, so the job installs CMake 3.31.6 from PyPI and
the first step refuses any other major version rather than silently
building x64 without assembly. Read back from the log: ml64 assembles 15
modules on x64 (aes, bsaes, vpaes, aesni, aesni-sha1, cmll, md5, ghash, rc4,
rc4-md5, sha1, sha256, sha512, wp and cpuid -masm-x86_64; no bignum module);
x86 defines OPENSSL_NO_ASM. The x64 libcrypto carries 35 unnamed functions,
the MASM routines (no PDB symbols); nothing else in the six images is
unnamed. Both libcrypto images carry LibreSSL's sleep().

Flags, read back from the log. Compile /Zi /W4 /MP /O2 /Ob2 /MD /GS
/fp:precise /Zc:inline /TC /D _USING_V110_SDK71_ (the XP toolset's marker)
plus upstream's definitions, /Oy- on x86 (added by MSBuild, not by the
recipe). The toolset's include and library paths, printed by the probe
job's /v:d build of hello.c, are the 7.1A SDK and UCRT 10.0.10240.
CMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi /Urestrict" (CMake's
Release default plus /Zi; /Urestrict cancels the -Drestrict that 3.1.0's
CMakeLists.txt adds for WIN32, which turns the UCRT's __declspec(restrict)
into __declspec(1), C2485, exactly as at 2.8.3 and 3.3.6 - no source in the
tree uses the word). Link /INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF
/OPT:NOICF /DLL /DYNAMICBASE /NXCOMPAT /SUBSYSTEM:CONSOLE,"5.01" (x86) or
"5.02" (x64) and the .def file CMake writes. No /GL, no /LTCG. Apps and
tests off. 0 errors on all three targets.

Glue baseline. Measured with cl 19.16 against the UCRT of the newest
Windows 10 SDK (10.0.26100, what vcvarsall picks) while the images compile
against UCRT 10.0.10240, which the XP toolset selects. Three probes cannot
build with this compiler and install, so the run exits non-zero with every
artefact built: probe_stl_func_20.cpp and probe_stl_throw_20.cpp (cl 19.16
ignores /std:c++20, D9002, and <optional> is then empty) and
probe_atl_metahost.cpp (C1083, metahost.h is in the .NET Framework SDK, not
in this install). All three measure C++ STL/ATL/CLR-hosting code, which
LibreSSL, a C library, does not contain. Adding the ATL component between
run 42686111161 and run 42688397427 (the imported one) restored the other
six ATL probes and changed no count and no PicHash in any image. No MSVC
runtime function survives by name: the kept names that look like it are
LibreSSL's own (BIO_printf, asprintf, vasprintf from its compat layer) or
one-instruction import thunks (mbstowcs_s, wcstombs_s,
_InterlockedCompareExchange@12).

Counts, kept + removed = image (x86 | x64):

    libcrypto  5145+154=5299 | 5168+154=5322
    libssl     1258+120=1378 | 1271+126=1397
    libtls      327+117=444  |  328+124=452

PicHash overlap, 10+ instructions, union of the three components (x86 |
x64): 3864 | 3509 hashes, of which 1592 | 2459 are in no other LibreSSL or
OpenSSL image here. Against the v143 builds: 3.3.6 2170 | 1027, 2.8.3
1873 | 834, 3.9.2 824 | 485, 4.4.0 634 | 362. Against MinGW and Linux of
any version 0 | at most 14. Against OpenSSL 1.1.1w MSVC 21 | 38, any
OpenSSL MinGW 0 | at most 11.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_VERSION = "3.1.0"
_SHA256 = "f91aad0c8fb9cbc67c910ad6dcffb401a819b4fd122007ea7f978638db044cf6"

# Refuses CMake 4 (no "Win64" generator spelling, so x64 would lose its
# assembly) and a developer environment that is not MSVC 14.16.
_CHECK = (
    'python -c "'
    "import subprocess,sys;"
    "v=subprocess.run(['cmake','--version'],capture_output=True,text=True).stdout.split()[2];"
    "b=subprocess.run(['cl'],capture_output=True,text=True);"
    "b=(b.stderr or b.stdout).splitlines()[0];"
    "print('cmake',v);print(b);"
    "sys.exit(0 if v.startswith('3.') and 'Version 19.16.' in b else "
    "'needs CMake 3.x and the VS 2017 14.16 developer environment')"
    '"')

_COMMON = ('-T v141_xp -DCMAKE_GENERATOR_INSTANCE=C:/BT/vs15 '
           '-DBUILD_SHARED_LIBS=ON -DLIBRESSL_APPS=OFF -DLIBRESSL_TESTS=OFF '
           '-DLIBRESSL_SKIP_INSTALL=ON -DENABLE_ASM=ON '
           '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi /Urestrict" '
           '-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
           '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

_CMAKE_X64 = ('cmake -S . -B build-x64 -G "Visual Studio 15 2017 Win64" '
              + _COMMON)
_CMAKE_X86 = ('cmake -S . -B build-x86 -G "Visual Studio 15 2017" -A Win32 '
              + _COMMON)

_NORMALISE = (
    'python -c "'
    "import glob,shutil;"
    "[shutil.copy(sorted(glob.glob('build-{arch}/'+d+'/**/'+d+'*'+e, "
    "recursive=True))[0], 'build-{arch}/lib'+d+e) "
    "for d in ('crypto','ssl','tls') for e in ('.dll','.pdb')]"
    '"')

RECIPES = {
    "LibreSSL_3.1.0_msvc_v141xp": Recipe(
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
            BuildStep('if "{arch}"=="x64" ' + _CMAKE_X64),
            BuildStep('if "{arch}"=="x86" ' + _CMAKE_X86),
            BuildStep("cmake --build build-{arch} --config Release "
                      "--target crypto ssl tls -- /m /v:n"),
            BuildStep(_NORMALISE),
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[
            Artifact(path="build-{arch}/libcrypto.dll", component="libcrypto",
                     pdb="build-{arch}/libcrypto.pdb"),
            Artifact(path="build-{arch}/libssl.dll", component="libssl",
                     pdb="build-{arch}/libssl.pdb"),
            Artifact(path="build-{arch}/libtls.dll", component="libtls",
                     pdb="build-{arch}/libtls.pdb"),
        ],
        toolchains=["msvc141_x86", "msvc141_x64"],
        build_flags="v141_xp platform toolset (MSVC 14.16.27023, cl 19.16.27054; "
                    "Windows 7.1A SDK, UCRT 10.0.10240) through the Visual Studio "
                    "15 2017 generator; /MD /O2 /Ob2 /DNDEBUG /Zi /Urestrict, /W4 "
                    "/MP /GS from upstream and MSBuild, /Oy- on x86 added by "
                    "MSBuild; /INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF "
                    "at link, /SUBSYSTEM 5.01 (x86) / 5.02 (x64); no /GL, no "
                    "/LTCG; x64 MASM assembly (generator name Win64), x86 C only",
        notes="The version and toolset tracker #61 evidences for Meterpreter's "
              "ext_server_python.dll, built stock: Meterpreter's /MT change "
              "and its removal of sleep() from crypto/compat/posix_win.c are "
              "not applied, and the libraries are DLLs rather than the "
              "static crypto-46/ssl-48/tls-20 .lib files it links. VS 2017 "
              "Build Tools (VC Tools workload, 14.16, WinXP and ATL "
              "components) installed on the runner from the pinned VS 2017 "
              "bootstrapper; the downloaded payload is not pinned. Named "
              "libcrypto/libssl/libtls as in the other LibreSSL rows; the "
              "DLLs are crypto-46, ssl-48 and tls-20.",
    ),
}
