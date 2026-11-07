"""MeshAgent native source builds with shared third-party dependencies.

The pinned tree supplies OpenSSL 1.1.1s static archives, Duktape 2.6.0 and
zlib source. Keeping those bodies in the agent would misattribute them.
The archives are relinked as shared dependencies and Duktape is compiled as
a shared dependency. Make's OBJECTS override omits Duktape and zlib objects
from the agent, which imports them instead. No upstream file is modified.

The Linux NOKVM configuration is a coverage axis; reports do not establish
whether deployed agents enabled KVM. Windows service and console retain
upstream KVM support on both MSVC architectures.

Linux GCC 14 measurements (functions of at least ten instructions for hashes):
x64 keeps 2681 and removes 6, image total 2687; 1644 unique PicHashes.
x86 keeps 3170 and removes 7, image total 3177; 1867 unique PicHashes.
The architecture sets overlap in zero hashes, so both add coverage.
Against the existing eight OpenSSL 1.1.1w MinGW/MSVC reports (18245 unique
PicHashes) and thirty libzlib reports (1690), both agent architectures share
zero hashes at the same ten-instruction floor. This confirms the shared
dependency link excludes those reference bodies from the agent family.
The x64 baseline leaves no named startup glue. The x86 survivors are:
  _init                       9804c1d756bfb707 (11 instructions)
  _start                      2e19b20ea4a953c6 (16)
  deregister_tm_clones        7ef4698f13363aaa (18)
  register_tm_clones          31f5bc65956e291f (26)
  __do_global_dtors_aux        b829096cd918a093 (21)
  __x86.get_pc_thunk.bp        7c99608cc56520ba (2)
  __stack_chk_fail_local      82127b22b3f97bef (5)
Their GOT-relative layouts differ from the measured baseline. These are
recorded rather than removed by name, preserving the baseline contract.

The source headers identify OpenSSL 1.1.1f, but strings in both committed
Linux archives identify 1.1.1s; the archive version is recorded in provenance.
The Windows recipe substitutes shared OpenSSL 1.1.1w and zlib 1.3.1 instead
of attributing the committed static dependencies to MeshAgent.
The customized Duktape engine calls ILibDuktape_EXEC_TIMEOUT_CHECK in its
host. Windows links one Duktape DLL per executable through a generated host
import library; external props export the real callback from that executable.
This preserves the callback without source edits or unresolved relocations.

MSVC v143 measurements (same ten-instruction hash floor):
  x86 meshservice kept 3020 + removed 256 = image 3276; 1838 unique PicHashes
  x86 meshconsole kept 3140 + removed 254 = image 3394; 2021 unique PicHashes
  x64 meshservice kept 2961 + removed 229 = image 3190; 1824 unique PicHashes
  x64 meshconsole kept 3055 + removed 220 = image 3275; 1973 unique PicHashes
All fifteen image-pair intersections are zero.
Thus every compiler, architecture and component leg adds distinct coverage.

MinGW-w64 GCC 13 (msvcrt) measurements, same floor (patched build tree, see below):
  x86 meshservice kept 2702 + removed 173 = image 2875; 1865 unique PicHashes
  x86 meshconsole kept 2766 + removed 193 = image 2959; 2017 unique PicHashes
  x64 meshservice kept 3046 + removed 154 = image 3200; 1800 unique PicHashes
  x64 meshconsole kept 3033 + removed 187 = image 3220; 2068 unique PicHashes
Linux x86-64/x86 KVM (ARCHID 6 and 5, GCC 13; the NOKVM images above are GCC 14):
  x64 kvm kept 3423 + removed 6 = image 3429; 1810 unique PicHashes
  x86 kvm kept 3408 + removed 7 = image 3415; 2003 unique PicHashes
The KVM images share 25 (x64) and 130 (x86) ten-instruction hashes with the
NOKVM images of the same architecture: the agent core compiled twice, by two
GCC majors. Other measured intersections: MinGW x86 service with Linux x86 KVM 35
and with NOKVM 26 (identical small ILib functions differing only in the leading
underscore); MinGW service with console 9 on each architecture (mingw-w64 CRT
survivors below); MinGW x64 service with MSVC x64 service 1 (the 13-instruction
getter ILibWrapper_WebRTC_Connection_GetUserData). All other pairs share zero.
MinGW images keep about 385-690 one-instruction linker import thunks (jmp
through the import table, named after the OpenSSL, zlib, Duktape and Win32
symbols) because the OpenSSL headers carry no dllimport; they are counted in
kept and are below the ten-instruction floor. No OpenSSL, zlib, Duktape or
libjpeg body is in any new image; jpeg_error_handler and crc32_z are agent code
(crc32_z is also in the NOKVM images). OpenSSL/libzlib family overlap was not
re-measured for the new images (those families were not checked out).

Surviving mingw-w64 CRT names (recorded, not removed): __tmainCRTStartup (142 x64,
152 x86 instructions), _fseeki64, _ftelli64, _int_chsize_s, _int_memcpy_s,
_int_memmove_s, four _stub shims (vsprintf_s etc.), sprintf_s, and _start (service
only). Linux KVM survivors: x64 sprintf_s only (agent code); x86 also
__do_global_dtors_aux, __stack_chk_fail_local, __x86.get_pc_thunk.{bp,cx,si},
_init, _start, deregister_tm_clones, register_tm_clones.

Linux KVM: jpeglib.h comes from host libjpeg-turbo (libjpeg-dev, plus
libjpeg-turbo8-dev:i386 for x86) and the build passes NOTURBOJPEG=1, so libjpeg is a
shared library and the committed static libturbojpeg.a is not linked. X11, XTest,
XRandr, libdrm, EGL, GLES and wayland-client are headers only (the agent dlopens
them). Host packages used: libjpeg-dev libjpeg-turbo8-dev libx11-dev libxtst-dev
libxext-dev libxrandr-dev libxfixes-dev libdrm-dev libegl1-mesa-dev
libgles2-mesa-dev libwayland-dev pkg-config.

MinGW build tree patches (applied by scripts/corpus/exercisers/meshagent_mingw.py;
the images are NOT byte-identical to a build of unmodified upstream). Exact diffs:
  meshcore/wincrypto.cpp (goto 'error' at line 342 crossed the initialisation at 277)
    -	BYTE ByteData = CERT_KEY_CERT_SIGN_KEY_USAGE | CERT_OFFLINE_CRL_SIGN_KEY_USAGE | CERT_CRL_SIGN_KEY_USAGE;
    +	BYTE ByteData;
    +	ByteData = CERT_KEY_CERT_SIGN_KEY_USAGE | CERT_OFFLINE_CRL_SIGN_KEY_USAGE | CERT_CRL_SIGN_KEY_USAGE;
  microstack/ILibParsers.c (follow-on: definitions conflicted with ILibParsers.h)
    -char* ILibInet_ntop(int af, const char *src, char *dst, size_t dstsize)
    +char* ILibInet_ntop(int af, const void *src_, char *dst, size_t dstsize)
    +	const char *src = (const char*)src_;
    -int ILibInet_pton(int af, const char *src, char *dst)
    +int ILibInet_pton(int af, const char *src, void *dst_)
    +	char *dst = (char*)dst_;
Not source edits, but behavioural: a generated forced include reduces __try/__except
(GCC has no SEH) to a plain block so exception filters never run, maps
_get_timezone/_get_daylight to _timezone/_daylight (msvcrt lacks them), and sets
UNREFERENCED_PARAMETER to a cast; forwarding headers fix include-name case; the
UTF-16 resource.h is re-encoded as UTF-8; ILibDuktape_Commit.h is generated as the
makefile does. Resource scripts (.rc) are not compiled. Optimisation mirrors upstream
Release: service -O2 (x86) / -Os (x64), console -O0; -g; msvcrt, -shared-libgcc, dynamic
libstdc++. OpenSSL 1.1.1w and zlib 1.3.1 are shared DLLs; Duktape is a DLL per
executable linked against an import library for the host callback.

Actual build logs confirm service /Ox /Os /Oy on x86, /O1 on x64; console
keeps upstream /Od on both. /MD, /Zi, /Brepro, /INCREMENTAL:NO, /OPT:NOREF
and /OPT:NOICF are present, with no /GL or /LTCG activation. Console's
inherited /RTC1 and /JMC are disabled through props so their runtime helper
bodies do not enter the family. This changes no upstream source.

Windows dependency overlap: against the same eight OpenSSL 1.1.1w reports,
x64 service shares one 13-instruction getter hash, 6176721668fbcd38:
ILibWrapper_WebRTC_Connection_GetUserData versus DSA_get0_pqg. The other five
images share zero. Against thirty libzlib reports, the six
images share zero (the Microsoft header wrappers snprintf and vsnprintf that
x64 service once shared are now removed by the glue baseline). The OpenSSL
overlap is a differently named short getter coincidence, not a retained
OpenSSL/zlib project body.

Named MSVC runtime/startup survivors follow. The wide-stdio glue baseline
removes the x64 __scrt_common_main_seh, the __stdio_common_* thunks and most
printf-family wrappers; the recipe records the hashes that still survive and
does not change shared filtering code.

  x86 meshservice:
    printf, printf_s 587caf596c74b028 (11)
    snprintf c8eb018529efac28 (8)
    sprintf_s, swprintf_s cf7e4f21e266437f (9)
    sscanf_s, fprintf d4776fc60fd2074a (8)
    _snprintf_s 012a528127228513 (13)
    _start 71b38a2da443c271 (35)
    __scrt_wide_argv_policy::configure_argv 9da69b39dcb9edec (5)
    __scrt_wide_environment_policy::initialize_environment 54b22cca4dddbd08 (1)
    wmainCRTStartup bb09143500f3ee48 (2)

  x86 meshconsole:
    _vsscanf_s_l a23b580451868775 (21)
    sscanf_s aa31b8f235f67d78 (19)
    vsscanf_s 368164c84ae07cc9 (13)
    __scrt_wide_argv_policy::configure_argv 9da69b39dcb9edec (5)
    __scrt_wide_environment_policy::initialize_environment 54b22cca4dddbd08 (1)
    wmainCRTStartup bb09143500f3ee48 (2)

  x64 meshservice:
    printf, printf_s 364aa9214bbcd05f (26)
    swprintf_s 1a3b110d3925a4b7 (28)
    sscanf_s fa2811009eef6517 (25)
    fprintf 50ed5dbd2b21d420 (23)
    _start 567e7e01896399a6 (33)
    __scrt_wide_environment_policy::initialize_environment 54b22cca4dddbd08 (1)
    wmainCRTStartup 8beba34a83410580 (4)

  x64 meshconsole:
    _vsprintf_s_l 7db6bea5ed90c301 (25)
    printf 823a12839f8d8c54 (19)
    snprintf 14239a64fed105df (17)
    sprintf_s, swprintf_s c5483d3eb7105209 (19)
    vsnprintf 3d01bb1c498bdd16 (26)
    _vsscanf_s_l 82426741596f12fc (19)
    sscanf_s 648f21069203b489 (16)
    vsscanf_s b303080b6fd7d055 (11)
    fprintf 3ab248a90fc6e83d (17)
    _snprintf_s 01b56146fe77909d (20)
    _vsnprintf_s_l f6eb157f14dc3e39 (27)
    __scrt_wide_environment_policy::initialize_environment 54b22cca4dddbd08 (1)
    wmainCRTStartup 8beba34a83410580 (4)

"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_BUILD_DEPS = (
    "mkdir -p corpus-deps && "
    "{cc} -shared -Wl,--whole-archive openssl/libstatic/linux/x86-64/libcrypto.a "
    "-Wl,--no-whole-archive -ldl -lpthread -o corpus-deps/libcrypto.so && "
    "{cc} -shared -Wl,--whole-archive openssl/libstatic/linux/x86-64/libssl.a "
    "-Wl,--no-whole-archive -Lcorpus-deps -lcrypto -o corpus-deps/libssl.so && "
    "{cc} -shared -fPIC -O2 -DDUK_USE_DEBUGGER_SUPPORT "
    "-DDUK_USE_INTERRUPT_COUNTER -DDUK_USE_DEBUGGER_INSPECT "
    "-DDUK_USE_DEBUGGER_PAUSE_UNCAUGHT microscript/duktape.c "
    "-lm -o corpus-deps/libduktape.so"
)
_BUILD = (
    "env -u CFLAGS make linux ARCHID=20 DYNAMICTLS=1 STRIP=true CC={cc} "
    "'INCDIRS=-I. -Iopenssl/include -Imicrostack -Imicroscript -Imeshcore -Imeshconsole' "
    "'OBJECTS=$(filter-out microscript/duktape.o meshcore/zlib/%.o,$(patsubst %.c,%.o,$(SOURCES)))' "
    "'LDFLAGS=-L{source_root}/corpus-deps -lssl -lcrypto -lduktape -lz "
    "-lpthread -lutil -lm -ldl' -j2"
)
_BUILD_DEPS_X86 = (_BUILD_DEPS.replace("{cc}", "{cc} -m32")
                   .replace("x86-64", "x86").replace("corpus-deps", "corpus-deps32"))
_BUILD_X86 = (_BUILD.replace("ARCHID=20", "ARCHID=19")
              .replace("CC={cc}", "'CC={cc} -m32'")
              .replace("corpus-deps", "corpus-deps32"))

_MSVC_HELPER = "python {repo}/scripts/corpus/exercisers/meshagent_dependencies.py"
_MSVC_DEPS = [
    BuildStep("tar xf {openssl_source} && tar xf {zlib_source}"),
    BuildStep('if "{arch}"=="x64" perl Configure VC-WIN64A shared no-tests no-asm '
              '"LDFLAGS=/nologo /debug /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF"',
              cwd="openssl-1.1.1w"),
    BuildStep('if "{arch}"=="x86" perl Configure VC-WIN32 shared no-tests no-asm '
              '"LDFLAGS=/nologo /debug /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF"',
              cwd="openssl-1.1.1w"),
    BuildStep("nmake /nologo build_libs", cwd="openssl-1.1.1w"),
    BuildStep('nmake -f win32\\Makefile.msc '
              '"LDFLAGS=-nologo -debug -Brepro -INCREMENTAL:NO -OPT:NOREF '
              '-OPT:NOICF -pdb:zlib1.pdb" zlib1.dll', cwd="zlib-1.3.1"),
    BuildStep("if not exist corpus-deps mkdir corpus-deps"),
    BuildStep("cl /nologo /MD /O2 /Zi /Brepro /DDUK_USE_DEBUGGER_SUPPORT "
              "/DDUK_USE_INTERRUPT_COUNTER /DDUK_USE_DEBUGGER_INSPECT "
              "/DDUK_USE_DEBUGGER_PAUSE_UNCAUGHT /DDUK_USE_DEBUGGER_DUMPHEAP "
              "/c ../microscript/duktape.c /Foduktape.obj", cwd="corpus-deps"),
    BuildStep(_MSVC_HELPER + " exports --arch {arch} --output corpus-deps/duktape.def "
              "corpus-deps/duktape.obj"),
]
_MSVC_BUILD = []
for _directory, _project, _name in (
    ("meshservice", "MeshService-2022", "MeshAgentService"),
    ("meshconsole", "MeshConsole-2022", "MeshAgentConsole"),
):
    _MSVC_BUILD += [
        BuildStep(_MSVC_HELPER + " host --name " + _name + " --deps corpus-deps"),
        BuildStep('if "{arch}"=="x86" lib /nologo /MACHINE:X86 /DEF:' + _name +
                  '-host.def /OUT:' + _name + '-host.lib', cwd="corpus-deps"),
        BuildStep('if "{arch}"=="x64" lib /nologo /MACHINE:X64 /DEF:' + _name +
                  '-host.def /OUT:' + _name + '-host.lib', cwd="corpus-deps"),
        BuildStep("link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF "
                  "/OUT:corpus-duktape-" + _name + ".dll /DEF:duktape.def duktape.obj " +
                  _name + "-host.lib", cwd="corpus-deps"),
        BuildStep(_MSVC_HELPER + " props --project " + _directory + "/" + _project +
                  ".vcxproj --platform {msbuild_platform} --name " + _name +
                  " --ssl {source_root}/openssl-1.1.1w --zlib {source_root}/zlib-1.3.1 "
                  "--deps {source_root}/corpus-deps "
                  "--output corpus-deps/" + _directory + ".props"),
        BuildStep("msbuild " + _directory + "/" + _project +
                  ".vcxproj /m:2 /p:Configuration=Release /p:Platform={msbuild_platform} "
                  "/p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0.26100.0 "
                  "/p:WholeProgramOptimization=false /p:LinkIncremental=false "
                  "/p:SolutionDir={source_root}/ "
                  "/p:IntDir={source_root}/corpus-obj/" + _directory + "/ "
                  "/p:OutDir={source_root}/corpus-out/" + _directory + "/ "
                  "/p:ForceImportBeforeCppTargets={source_root}/corpus-deps/" +
                  _directory + ".props"),
    ]

_BUILD_KVM = (_BUILD.replace("ARCHID=20", "ARCHID=6")
              .replace("env -u CFLAGS make linux", "env -u CFLAGS make linux NOTURBOJPEG=1"))
_BUILD_KVM_X86 = (_BUILD_X86.replace("ARCHID=19", "ARCHID=5")
                  .replace("env -u CFLAGS make linux", "env -u CFLAGS make linux NOTURBOJPEG=1"))

_MINGW_HELPER = "python3 {repo}/scripts/corpus/exercisers/meshagent_mingw.py"
_MINGW_DUK_DEFS = ("-DDUK_USE_DATE_NOW_WINDOWS -DDUK_USE_DEBUGGER_SUPPORT "
                   "-DDUK_USE_INTERRUPT_COUNTER -DDUK_USE_DEBUGGER_INSPECT "
                   "-DDUK_USE_DEBUGGER_PAUSE_UNCAUGHT -DDUK_USE_DEBUGGER_DUMPHEAP")
_MINGW_DEPS = [
    BuildStep("tar xf {openssl_source} && tar xf {zlib_source}"),
    BuildStep("if [ {bitness} = 64 ]; then T=mingw64; else T=mingw; fi && "
              "./Configure $T --cross-compile-prefix={prefix} shared no-tests && "
              "(make -j2 build_libs || make -j2 build_libs)", cwd="openssl-1.1.1w",
              env={"CC": "gcc", "CXX": "g++", "AR": "ar", "RANLIB": "ranlib",
                   "WINDRES": "windres"}),
    BuildStep("make -f win32/Makefile.gcc PREFIX={prefix} SHARED_MODE=1 -j2",
              cwd="zlib-1.3.1"),
    BuildStep(_MINGW_HELPER + " prepare --prefix {prefix} --shim {source_root}/corpus-shim"),
]
_MINGW_BUILD = []
for _component, _name, _opt in (
    ("service", "MeshAgentService", "$([ {bitness} = 64 ] && echo -Os || echo -O2)"),
    ("console", "MeshAgentConsole", "-O0"),
):
    _MINGW_BUILD += [
        BuildStep(_MINGW_HELPER + " host --prefix {prefix} --name " + _name +
                  " --deps {source_root}/corpus-deps"),
        BuildStep("{cc} -shared -O2 -g " + _MINGW_DUK_DEFS + " ../microscript/duktape.c "
                  "-o corpus-duktape-" + _name + ".dll "
                  "-Wl,--out-implib,libcorpus-duktape-" + _name + ".dll.a "
                  "-L. -l" + _name + "-host -lws2_32", cwd="corpus-deps"),
        BuildStep(_MINGW_HELPER + " build --prefix {prefix} --component " + _component +
                  " --arch {arch} --shim {source_root}/corpus-shim "
                  "--deps {source_root}/corpus-deps --ssl {source_root}/openssl-1.1.1w "
                  "--zlib {source_root}/zlib-1.3.1 --objdir {source_root}/corpus-obj/" +
                  _component + " --output {source_root}/corpus-out/" + _name + ".exe "
                  "--optimize=" + _opt),
    ]

RECIPES = {
    "meshagent_26846b1_msvc": Recipe(
        family="MeshAgent",
        version="26846b1",
        upstream="https://github.com/Ylianst/MeshAgent",
        license="Apache-2.0",
        source=Source(git_url="https://github.com/Ylianst/MeshAgent.git",
                      git_ref="26846b1c7f0841d71938f6bebc96eef5a947d217"),
        extra_sources={"openssl_source": Source(
            url="https://github.com/openssl/openssl/releases/download/"
                "OpenSSL_1_1_1w/openssl-1.1.1w.tar.gz",
            sha256="cf3098950cb4d853ad95c0841f1f9c6d3dc102dccfcacd521d93925208b76ac8"),
            "zlib_source": Source(url="https://zlib.net/fossils/zlib-1.3.1.tar.gz",
                sha256="9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23")},
        build=_MSVC_DEPS + _MSVC_BUILD,
        artifacts=[Artifact(path="corpus-out/meshservice/MeshAgentService.exe",
                            component="meshservice", is_library=True,
                            pdb="corpus-out/meshservice/MeshAgentService.pdb",
                            build_flags="upstream Release /Ox /Os /Oy (x86), /O1 (x64); "
                                        "/MD /Zi /Brepro /OPT:NOREF /OPT:NOICF /INCREMENTAL:NO; "
                                        "no whole-program optimization or debug instrumentation"),
                   Artifact(path="corpus-out/meshconsole/MeshAgentConsole.exe",
                            component="meshconsole", is_library=True,
                            pdb="corpus-out/meshconsole/MeshAgentConsole.pdb",
                            build_flags="upstream Release /Od; /MD /Zi /Brepro /OPT:NOREF "
                                        "/OPT:NOICF /INCREMENTAL:NO; runtime checks and "
                                        "JustMyCode disabled; no whole-program optimization")],
        toolchains=["msvc_x86", "msvc_x64"],
        requires=["msbuild", "cl", "link", "nmake", "perl", "dumpbin", "tar", "lib"],
        build_flags="upstream Release /MD /Zi /Brepro /OPT:NOREF /OPT:NOICF "
                    "/INCREMENTAL:NO; whole program optimization disabled",
        notes="OpenSSL 1.1.1w, embedded Duktape 2.6.0 and zlib 1.3.1 are "
              "linked as shared dependencies and excluded from agent code. "
              "Service and console retain upstream Windows KVM configuration.",
    ),
    "meshagent_26846b1_mingw": Recipe(
        family="MeshAgent",
        version="26846b1",
        upstream="https://github.com/Ylianst/MeshAgent",
        license="Apache-2.0",
        source=Source(git_url="https://github.com/Ylianst/MeshAgent.git",
                      git_ref="26846b1c7f0841d71938f6bebc96eef5a947d217"),
        extra_sources={"openssl_source": Source(
            url="https://github.com/openssl/openssl/releases/download/"
                "OpenSSL_1_1_1w/openssl-1.1.1w.tar.gz",
            sha256="cf3098950cb4d853ad95c0841f1f9c6d3dc102dccfcacd521d93925208b76ac8"),
            "zlib_source": Source(url="https://zlib.net/fossils/zlib-1.3.1.tar.gz",
                sha256="9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23")},
        build=_MINGW_DEPS + _MINGW_BUILD,
        artifacts=[Artifact(path="corpus-out/MeshAgentService.exe", component="meshservice",
                            is_library=True,
                            build_flags="-O2 (x86) / -Os (x64), mirroring upstream Release "
                                        "/Ox and /O1; -g; two build-tree patches, see notes"),
                   Artifact(path="corpus-out/MeshAgentConsole.exe", component="meshconsole",
                            is_library=True,
                            build_flags="-O0, mirroring upstream Release /Od; -g; two "
                                        "build-tree patches, see notes")],
        toolchains=["mingw_x86", "mingw_x64"],
        requires=["perl", "make", "tar", "git"],
        build_flags="MinGW-w64 GCC, msvcrt, -g, -shared-libgcc, dynamic libstdc++; "
                    "build-tree patches to meshcore/wincrypto.cpp and "
                    "microstack/ILibParsers.c",
        notes="NOT byte-identical to a build of unmodified upstream: the recipe applies "
              "two build-tree patches. wincrypto.cpp splits 'BYTE ByteData = ...' into a "
              "declaration and an assignment (the goto to 'error' crosses the "
              "initialisation); ILibParsers.c gives ILibInet_ntop/ILibInet_pton the "
              "parameter types ILibParsers.h declares (GCC rejects conflicting types). "
              "A generated forced-include also reduces __try/__except to a plain block "
              "(the exception filter never runs) and maps _get_timezone/_get_daylight "
              "to _timezone/_daylight. Forwarding headers fix include-name case. "
              "OpenSSL 1.1.1w and zlib 1.3.1 are shared DLLs; Duktape is one DLL per "
              "executable with an import library for the host timeout callback.",
    ),
    "meshagent_26846b1_linux_nokvm": Recipe(
        family="MeshAgent",
        version="26846b1",
        upstream="https://github.com/Ylianst/MeshAgent",
        license="Apache-2.0",
        source=Source(git_url="https://github.com/Ylianst/MeshAgent.git",
                      git_ref="26846b1c7f0841d71938f6bebc96eef5a947d217"),
        build=[BuildStep(_BUILD_DEPS), BuildStep(_BUILD)],
        artifacts=[Artifact(path="meshagent_x86-64_nokvm", component="meshagent-nokvm",
                            is_library=True)],
        toolchains=["linux_x64"],
        requires=["make"],
        build_flags="-O2 -g -fstack-protector -D_FORTIFY_SOURCE=2 -fno-strict-aliasing; "
                    "ARCHID=20 NOKVM; DYNAMICTLS=1; STRIP=true",
        notes="OpenSSL 1.1.1s and Duktape 2.6.0 from the pinned source tree, "
              "and host zlib, are shared dependencies, excluded from agent code. "
              "The reported deployments are primarily Windows; KVM status is unknown.",
    ),
    "meshagent_26846b1_linux_x86_nokvm": Recipe(
        family="MeshAgent",
        version="26846b1",
        upstream="https://github.com/Ylianst/MeshAgent",
        license="Apache-2.0",
        source=Source(git_url="https://github.com/Ylianst/MeshAgent.git",
                      git_ref="26846b1c7f0841d71938f6bebc96eef5a947d217"),
        extra_sources={
            "zlib32_dev": Source(
                url="https://deb.debian.org/debian/pool/main/z/zlib/"
                    "zlib1g-dev_1.3.dfsg+really1.3.1-1+b1_i386.deb",
                sha256="b5ca31bbc301f5f8be89ef90a1935c826bf562d6f6601e9169709366e3bad263"),
            "zlib32_runtime": Source(
                url="https://deb.debian.org/debian/pool/main/z/zlib/"
                    "zlib1g_1.3.dfsg+really1.3.1-1+b1_i386.deb",
                sha256="8950c79b1ade51f53b2f37863aec532cfaca3dff315e28f0c5b53902425c41ed"),
        },
        build=[BuildStep(_BUILD_DEPS_X86),
               BuildStep("mkdir -p corpus-zlib32 && "
                         "dpkg-deb -x {zlib32_dev} corpus-zlib32 && "
                         "dpkg-deb -x {zlib32_runtime} corpus-zlib32"),
               BuildStep(_BUILD_X86, env={
                   "LIBRARY_PATH": "{source_root}/corpus-zlib32/usr/lib/i386-linux-gnu"})],
        artifacts=[Artifact(path="meshagent_x86_nokvm", component="meshagent-nokvm",
                            is_library=True)],
        toolchains=["linux_x86"],
        requires=["make", "dpkg-deb"],
        build_flags="-O2 -g -m32 -fstack-protector -D_FORTIFY_SOURCE=2 -fno-strict-aliasing; "
                    "ARCHID=19 NOKVM; DYNAMICTLS=1; STRIP=true",
        notes="OpenSSL 1.1.1s and Duktape 2.6.0 from the pinned source tree, "
              "and Debian zlib 1.3.1, are shared dependencies, excluded from agent code. "
              "The reported deployments are primarily Windows; KVM status is unknown.",
    ),
    "meshagent_26846b1_linux_kvm": Recipe(
        family="MeshAgent",
        version="26846b1",
        upstream="https://github.com/Ylianst/MeshAgent",
        license="Apache-2.0",
        source=Source(git_url="https://github.com/Ylianst/MeshAgent.git",
                      git_ref="26846b1c7f0841d71938f6bebc96eef5a947d217"),
        build=[BuildStep(_BUILD_DEPS), BuildStep(_BUILD_KVM)],
        artifacts=[Artifact(path="meshagent_x86-64", component="meshagent-kvm",
                            is_library=True)],
        toolchains=["linux_x64"],
        requires=["make", "pkg-config"],
        build_flags="-O2 -g -fstack-protector -D_FORTIFY_SOURCE=2 -fno-strict-aliasing; "
                    "ARCHID=6 KVM=1; NOTURBOJPEG=1 (system libjpeg shared); "
                    "DYNAMICTLS=1; STRIP=true",
        notes="Official Linux x86-64 KVM configuration. OpenSSL 1.1.1s and Duktape "
              "2.6.0 from the pinned source tree, host zlib and host libjpeg-turbo "
              "are shared dependencies, excluded from agent code. Needs host "
              "development headers: libjpeg-dev libx11-dev libxtst-dev libxext-dev "
              "libxrandr-dev libxfixes-dev libdrm-dev libegl1-mesa-dev "
              "libgles2-mesa-dev libwayland-dev pkg-config.",
    ),
    "meshagent_26846b1_linux_x86_kvm": Recipe(
        family="MeshAgent",
        version="26846b1",
        upstream="https://github.com/Ylianst/MeshAgent",
        license="Apache-2.0",
        source=Source(git_url="https://github.com/Ylianst/MeshAgent.git",
                      git_ref="26846b1c7f0841d71938f6bebc96eef5a947d217"),
        extra_sources={
            "zlib32_dev": Source(
                url="https://deb.debian.org/debian/pool/main/z/zlib/"
                    "zlib1g-dev_1.3.dfsg+really1.3.1-1+b1_i386.deb",
                sha256="b5ca31bbc301f5f8be89ef90a1935c826bf562d6f6601e9169709366e3bad263"),
            "zlib32_runtime": Source(
                url="https://deb.debian.org/debian/pool/main/z/zlib/"
                    "zlib1g_1.3.dfsg+really1.3.1-1+b1_i386.deb",
                sha256="8950c79b1ade51f53b2f37863aec532cfaca3dff315e28f0c5b53902425c41ed"),
        },
        build=[BuildStep(_BUILD_DEPS_X86),
               BuildStep("mkdir -p corpus-zlib32 && "
                         "dpkg-deb -x {zlib32_dev} corpus-zlib32 && "
                         "dpkg-deb -x {zlib32_runtime} corpus-zlib32"),
               BuildStep(_BUILD_KVM_X86, env={
                   "LIBRARY_PATH": "{source_root}/corpus-zlib32/usr/lib/i386-linux-gnu"})],
        artifacts=[Artifact(path="meshagent_x86", component="meshagent-kvm",
                            is_library=True)],
        toolchains=["linux_x86"],
        requires=["make", "dpkg-deb", "pkg-config"],
        build_flags="-O2 -g -m32 -fstack-protector -D_FORTIFY_SOURCE=2 -fno-strict-aliasing; "
                    "ARCHID=5 KVM=1; NOTURBOJPEG=1 (system libjpeg shared); "
                    "DYNAMICTLS=1; STRIP=true",
        notes="Official Linux x86 KVM configuration. OpenSSL 1.1.1s and Duktape "
              "2.6.0 from the pinned source tree, Debian zlib 1.3.1 and host "
              "libjpeg-turbo (i386) are shared dependencies, excluded from agent "
              "code. Needs the host development headers listed for the x64 KVM "
              "recipe plus libjpeg-turbo8-dev:i386.",
    ),
}
