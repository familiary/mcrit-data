"""MeshAgent NOKVM source build with shared third-party dependencies.

The pinned tree supplies OpenSSL 1.1.1s static archives, Duktape 2.6.0 and
zlib source. Keeping those bodies in the agent would misattribute them.
The archives are relinked as shared dependencies and Duktape is compiled as
a shared dependency. Make's OBJECTS override omits Duktape and zlib objects
from the agent, which imports them instead. No upstream file is modified.

The Linux NOKVM configuration is a coverage axis; reports do not establish
whether deployed agents enabled KVM. Windows MSVC coverage remains pending.
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
    BuildStep("if not exist corpus-deps mkdir corpus-deps"),
    BuildStep("cl /nologo /MD /O2 /Zi /Brepro /DDUK_USE_DEBUGGER_SUPPORT "
              "/DDUK_USE_INTERRUPT_COUNTER /DDUK_USE_DEBUGGER_INSPECT "
              "/DDUK_USE_DEBUGGER_PAUSE_UNCAUGHT /DDUK_USE_DEBUGGER_DUMPHEAP "
              "/c ../microscript/duktape.c /Foduktape.obj", cwd="corpus-deps"),
    BuildStep("cl /nologo /MD /O2 /Zi /Brepro /c ../meshcore/zlib/*.c", cwd="corpus-deps"),
    BuildStep(_MSVC_HELPER + " exports --arch {arch} --output corpus-deps/duktape.def "
              "corpus-deps/duktape.obj"),
    BuildStep(_MSVC_HELPER + " exports --arch {arch} --output corpus-deps/zlib.def "
              "corpus-deps/adler32.obj corpus-deps/deflate.obj corpus-deps/inffast.obj "
              "corpus-deps/inflate.obj corpus-deps/inftrees.obj corpus-deps/trees.obj "
              "corpus-deps/zutil.obj"),
    BuildStep("link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF "
              "/OUT:corpus-duktape.dll /DEF:duktape.def duktape.obj", cwd="corpus-deps"),
    BuildStep("link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF "
              "/OUT:corpus-zlib.dll /DEF:zlib.def adler32.obj deflate.obj inffast.obj "
              "inflate.obj inftrees.obj trees.obj zutil.obj", cwd="corpus-deps"),
]
_MSVC_BUILD = []
for _directory, _project, _name in (
    ("meshservice", "MeshService-2022", "MeshAgentService"),
    ("meshconsole", "MeshConsole-2022", "MeshAgentConsole"),
):
    _MSVC_BUILD += [
        BuildStep(_MSVC_HELPER + " props --project " + _directory + "/" + _project +
                  ".vcxproj --platform {msbuild_platform} --name " + _name +
                  " --ssl {openssl_source} --deps {source_root}/corpus-deps "
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
            sha256="cf3098950cb4d853ad95c0841f1f9c6d3dc102dccfcacd521d93925208b76ac8")},
        build=_MSVC_DEPS + _MSVC_BUILD,
        artifacts=[Artifact(path="corpus-out/meshservice/MeshAgentService.exe",
                            component="meshservice", is_library=False,
                            pdb="corpus-out/meshservice/MeshAgentService.pdb"),
                   Artifact(path="corpus-out/meshconsole/MeshAgentConsole.exe",
                            component="meshconsole", is_library=False,
                            pdb="corpus-out/meshconsole/MeshAgentConsole.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        requires=["msbuild", "cl", "link", "nmake", "perl", "dumpbin"],
        build_flags="upstream Release /MD /Zi /Brepro /OPT:NOREF /OPT:NOICF "
                    "/INCREMENTAL:NO; whole program optimization disabled",
        notes="OpenSSL 1.1.1w, embedded Duktape 2.6.0 and embedded zlib are "
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
                            is_library=False)],
        toolchains=["linux_x64"],
        requires=["make"],
        build_flags="-O2 -g; ARCHID=20 NOKVM; DYNAMICTLS=1; STRIP=true",
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
                            is_library=False)],
        toolchains=["linux_x86"],
        requires=["make", "dpkg-deb"],
        build_flags="-O2 -g -m32; ARCHID=19 NOKVM; DYNAMICTLS=1; STRIP=true",
        notes="OpenSSL 1.1.1s and Duktape 2.6.0 from the pinned source tree, "
              "and Debian zlib 1.3.1, are shared dependencies, excluded from agent code. "
              "The reported deployments are primarily Windows; KVM status is unknown.",
    ),
}
