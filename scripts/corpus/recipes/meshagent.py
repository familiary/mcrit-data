"""MeshAgent NOKVM source build with shared third-party dependencies.

The pinned tree supplies OpenSSL 1.1.1s static archives, Duktape 2.6.0 and
zlib source. Keeping those bodies in the agent would misattribute them.
The archives are relinked as shared dependencies and Duktape is compiled as
a shared dependency. Make's OBJECTS override omits Duktape and zlib objects
from the agent, which imports them instead. No upstream file is modified.

The Linux NOKVM configuration is a coverage axis; reports do not establish
whether deployed agents enabled KVM. Windows MSVC coverage remains pending.

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
    BuildStep('if "{arch}"=="x64" perl Configure VC-WIN64A shared no-tests no-asm '
              '"LDFLAGS=/nologo /debug /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF"',
              cwd="{openssl_source}"),
    BuildStep('if "{arch}"=="x86" perl Configure VC-WIN32 shared no-tests no-asm '
              '"LDFLAGS=/nologo /debug /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF"',
              cwd="{openssl_source}"),
    BuildStep("nmake /nologo build_libs", cwd="{openssl_source}"),
    BuildStep('nmake -f win32\\Makefile.msc '
              '"LDFLAGS=-nologo -debug -Brepro -INCREMENTAL:NO -OPT:NOREF '
              '-OPT:NOICF -pdb:zlib1.pdb" zlib1.dll', cwd="{zlib_source}"),
    BuildStep("if not exist corpus-deps mkdir corpus-deps"),
    BuildStep("cl /nologo /MD /O2 /Zi /Brepro /DDUK_USE_DEBUGGER_SUPPORT "
              "/DDUK_USE_INTERRUPT_COUNTER /DDUK_USE_DEBUGGER_INSPECT "
              "/DDUK_USE_DEBUGGER_PAUSE_UNCAUGHT /DDUK_USE_DEBUGGER_DUMPHEAP "
              "/c ../microscript/duktape.c /Foduktape.obj", cwd="corpus-deps"),
    BuildStep(_MSVC_HELPER + " exports --arch {arch} --output corpus-deps/duktape.def "
              "corpus-deps/duktape.obj"),
    BuildStep("link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF "
              "/OUT:corpus-duktape.dll /DEF:duktape.def duktape.obj", cwd="corpus-deps"),
]
_MSVC_BUILD = []
for _directory, _project, _name in (
    ("meshservice", "MeshService-2022", "MeshAgentService"),
    ("meshconsole", "MeshConsole-2022", "MeshAgentConsole"),
):
    _MSVC_BUILD += [
        BuildStep(_MSVC_HELPER + " props --project " + _directory + "/" + _project +
                  ".vcxproj --platform {msbuild_platform} --name " + _name +
                  " --ssl {openssl_source} --zlib {zlib_source} "
                  "--deps {source_root}/corpus-deps "
                  "--output corpus-deps/" + _directory + ".props"),
        BuildStep("msbuild " + _directory + "/" + _project +
                  ".vcxproj /m:2 /p:Configuration=Release /p:Platform={msbuild_platform} "
                  "/p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0.26100.0 "
                  "/p:WholeProgramOptimization=false /p:LinkIncremental=false "
                  "/p:OutDir={source_root}/corpus-out/" + _directory + "/ "
                  "/p:ForceImportBeforeCppTargets={source_root}/corpus-deps/" +
                  _directory + ".props"),
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
                            pdb="corpus-out/meshservice/MeshAgentService.pdb"),
                   Artifact(path="corpus-out/meshconsole/MeshAgentConsole.exe",
                            component="meshconsole", is_library=True,
                            pdb="corpus-out/meshconsole/MeshAgentConsole.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        requires=["msbuild", "cl", "link", "nmake", "perl", "dumpbin"],
        build_flags="upstream Release /MD /Zi /Brepro /OPT:NOREF /OPT:NOICF "
                    "/INCREMENTAL:NO; whole program optimization disabled",
        notes="OpenSSL 1.1.1w, embedded Duktape 2.6.0 and zlib 1.3.1 are "
              "linked as shared dependencies and excluded from agent code. "
              "Service and console retain upstream Windows KVM configuration.",
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
}
