"""MinGW-w64 port of the MeshAgent Visual Studio projects, without source edits
beyond the two recorded patches.

MeshAgent has no MinGW target; the sources come from the same .vcxproj lists
the MSVC recipe builds. This helper supplies what a case-insensitive MSVC
toolchain gives for free:

  prepare   forwarding headers for include names whose case differs from the
            mingw-w64 header (Windows.h, WinSock2.h, STDDEF.H ...), a forced
            include with the MSVC-only constructs GCC lacks (__try/__except
            reduced to a plain block, UCRT _get_timezone/_get_daylight mapped
            to the CRT's _timezone/_daylight), the SOURCE_COMMIT header the
            Visual Studio pre-build step normally writes, and two exact-match
            patches of the build tree:

            meshcore/wincrypto.cpp (line 277, jump to 'error' crosses an
            initialisation, a hard error in C++ even with -fpermissive)
              -	BYTE ByteData = CERT_KEY_CERT_SIGN_KEY_USAGE | ...;
              +	BYTE ByteData;
              +	ByteData = CERT_KEY_CERT_SIGN_KEY_USAGE | ...;

            microstack/ILibParsers.c (definitions disagree with the header
            declarations in ILibParsers.h, a hard error in GCC's C)
              -char* ILibInet_ntop(int af, const char *src, char *dst, size_t dstsize)
              -{
              +char* ILibInet_ntop(int af, const void *src_, char *dst, size_t dstsize)
              +{
              +	const char *src = (const char*)src_;
              -int ILibInet_pton(int af, const char *src, char *dst)
              -{
              +int ILibInet_pton(int af, const char *src, void *dst_)
              +{
              +	char *dst = (char*)dst_;
            UTF-16 headers (meshservice/resource.h) are re-encoded as UTF-8.
  host      the executable's export list and import library for the one host
            callback the Duktape DLL calls back into.
  build     compile and link one component.
"""

import argparse
import os
import re
import subprocess
import sys

PATCHES = {
    "meshcore/wincrypto.cpp": [(
        "BYTE ByteData = CERT_KEY_CERT_SIGN_KEY_USAGE | CERT_OFFLINE_CRL_SIGN_KEY_USAGE"
        " | CERT_CRL_SIGN_KEY_USAGE;",
        "BYTE ByteData;\n\tByteData = CERT_KEY_CERT_SIGN_KEY_USAGE | CERT_OFFLINE_CRL_SIGN_KEY_USAGE"
        " | CERT_CRL_SIGN_KEY_USAGE;")],
    "microstack/ILibParsers.c": [(
        "char* ILibInet_ntop(int af, const char *src, char *dst, size_t dstsize)\n{\n",
        "char* ILibInet_ntop(int af, const void *src_, char *dst, size_t dstsize)\n{\n"
        "\tconst char *src = (const char*)src_;\n"), (
        "int ILibInet_pton(int af, const char *src, char *dst)\n{\n",
        "int ILibInet_pton(int af, const char *src, void *dst_)\n{\n"
        "\tchar *dst = (char*)dst_;\n")],
}

COMPAT = """#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <shellscalingapi.h>
#include <time.h>
#undef UNREFERENCED_PARAMETER
#define UNREFERENCED_PARAMETER(P) (void)(P)
#define __try
#define __except(x) if (0)
#define _get_timezone(p) (*(p) = _timezone, 0)
#define _get_daylight(p) (*(p) = _daylight, 0)
"""

PROJECTS = {"service": ("meshservice", "MeshService-2022", "MeshAgentService"),
            "console": ("meshconsole", "MeshConsole-2022", "MeshAgentConsole")}


def system_include_dirs(prefix):
    text = subprocess.run([prefix + "gcc", "-E", "-xc", "-v", os.devnull],
                          capture_output=True, text=True).stderr
    dirs, active = [], False
    for line in text.splitlines():
        if line.startswith("#include <"):
            active = True
        elif line.startswith("End of search"):
            active = False
        elif active:
            dirs.append(line.strip())
    return dirs


def prepare(args):
    available = {}
    for directory in system_include_dirs(args.prefix):
        for base, _, files in os.walk(directory):
            for name in files:
                relative = os.path.relpath(os.path.join(base, name), directory)
                available.setdefault(relative.lower(), relative)
    wanted = set()
    for top in ("meshcore", "meshservice", "meshconsole", "microscript", "microstack"):
        for base, _, files in os.walk(top):
            for name in files:
                if name.endswith((".c", ".h", ".cpp")):
                    text = open(os.path.join(base, name), encoding="latin1").read()
                    for match in re.finditer(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]', text, re.M):
                        wanted.add(match.group(1).replace("\\", "/"))
    os.makedirs(args.shim, exist_ok=True)
    for name in sorted(wanted):
        real = available.get(name.lower())
        if real and real != name:
            target = os.path.join(args.shim, name)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w") as stream:
                stream.write("#include <%s>\n" % real)
    with open(os.path.join(args.shim, "meshagent_mingw_compat.h"), "w") as stream:
        stream.write(COMPAT)
    for path, edits in PATCHES.items():
        with open(path, encoding="latin1", newline="") as stream:
            text = stream.read()
        for old, new in edits:
            if text.count(old) != 1:
                raise RuntimeError("%s: expected exactly one match for %r" % (path, old))
            text = text.replace(old, new)
        with open(path, "w", encoding="latin1", newline="") as stream:
            stream.write(text)
        print("patched", path)
    # resource.h is UTF-16 with a byte order mark, which MSVC reads and GCC
    # does not; re-encode it (same text) in the build tree.
    for top in ("meshcore", "meshservice", "meshconsole", "microscript", "microstack"):
        for base, _, files in os.walk(top):
            for name in files:
                path = os.path.join(base, name)
                if name.endswith((".c", ".h", ".cpp")):
                    with open(path, "rb") as stream:
                        data = stream.read()
                    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
                        with open(path, "wb") as stream:
                            stream.write(data.decode("utf-16").encode("utf-8"))
                        print("re-encoded", path)
    # What MeshAgent's makefile and the Visual Studio pre-build step write,
    # derived the way the makefile's awk does it from `git log -1`.
    log = subprocess.run(["git", "log", "-1"], capture_output=True, text=True, env=dict(
        os.environ, LC_ALL="C", TZ="UTC")).stdout
    date = next((line.split() for line in log.splitlines() if line.startswith("Date: ")), [])
    commit = subprocess.run(["git", "log", "-1", "--format=%H"], capture_output=True,
                            text=True).stdout.strip()
    with open("microscript/ILibDuktape_Commit.h", "w") as stream:
        stream.write("// This file is auto-generated, any edits may be overwritten\n")
        if len(date) >= 7:
            stream.write('#define SOURCE_COMMIT_DATE "%s-%s-%s %s%s"\n' % (
                date[5], date[2], date[3], date[4], date[6]))
        if commit:
            stream.write('#define SOURCE_COMMIT_HASH "%s"\n' % commit)


def host(args):
    exports = "EXPORTS\nILibDuktape_EXEC_TIMEOUT_CHECK\n"
    os.makedirs(args.deps, exist_ok=True)
    with open(os.path.join(args.deps, args.name + "-host.def"), "w") as stream:
        stream.write("LIBRARY " + args.name + ".exe\n" + exports)
    with open(os.path.join(args.deps, args.name + "-exports.def"), "w") as stream:
        stream.write(exports)
    subprocess.check_call([args.prefix + "dlltool", "-d", args.name + "-host.def", "-l",
                           "lib" + args.name + "-host.a"], cwd=args.deps)


def sources(directory, project):
    text = open("%s/%s.vcxproj" % (directory, project), encoding="utf-8-sig").read()
    result = []
    for name in re.findall(r'<ClCompile Include="([^"]*)"', text):
        name = name.replace("\\", "/")
        name = name[3:] if name.startswith("../") else directory + "/" + name
        if name == "microscript/duktape.c" or name.startswith("meshcore/zlib/"):
            continue
        result.append(name)
    return result


def build(args):
    directory, project, name = PROJECTS[args.component]
    agent_id = {("console", "x86"): 1, ("console", "x64"): 2,
                ("service", "x86"): 3, ("service", "x64"): 4}[(args.component, args.arch)]
    defines = ["MESH_AGENTID=%d" % agent_id, "DUK_USE_DATE_NOW_WINDOWS", "NOLMSCOMMANDER",
               "MICROSTACK_PROXY", "_LINKVM", "_CONSOLE", "WIN32", "WINSOCK2",
               "MICROSTACK_NO_STDAFX", "MICROSTACK_TLS_DETECT",
               "ILibChain_WATCHDOG_TIMEOUT=600000", "DUK_USE_DEBUGGER_SUPPORT",
               "DUK_USE_INTERRUPT_COUNTER", "DUK_USE_DEBUGGER_INSPECT",
               "DUK_USE_DEBUGGER_PAUSE_UNCAUGHT", "DUK_USE_DEBUGGER_DUMPHEAP"]
    if args.arch == "x64":
        defines.append("WIN64")
    if args.component == "service":
        defines += ["_WINSERVICE", "NDEBUG", "_REMOTELOGGING", "_REMOTELOGGINGSERVER"]
    else:
        defines.append("_WINSOCK_DEPRECATED_NO_WARNINGS")
    flags = ["-D" + item for item in defines] + [
        args.optimize, "-g", "-include", "meshagent_mingw_compat.h", "-I" + args.shim,
        "-Iopenssl/include", "-I."]
    files = sources(directory, project)
    files += ["meshservice/ServiceMain.c", "meshservice/firewall.cpp"] if args.component == \
        "service" else ["meshconsole/main.c"]
    objects = []
    os.makedirs(args.objdir, exist_ok=True)
    for path in dict.fromkeys(files):
        compiler = args.prefix + ("g++" if path.endswith(".cpp") else "gcc")
        output = os.path.join(args.objdir, path.replace("/", "_") + ".o")
        subprocess.check_call([compiler, "-c"] + flags + [path, "-o", output])
        objects.append(output)
    libraries = ["-L" + args.deps, "-L" + args.ssl, "-L" + args.zlib,
                 "-lcorpus-duktape-" + name, "-lcrypto", "-lssl", "-lz",
                 "-lsetupapi", "-lcrypt32", "-lncrypt", "-ldbghelp", "-lgdiplus",
                 "-liphlpapi", "-lws2_32", "-lgdi32", "-luser32", "-ladvapi32",
                 "-lshell32", "-lole32", "-loleaut32", "-luuid", "-lshlwapi",
                 "-lwininet", "-lwinhttp", "-lpsapi", "-lversion", "-lwtsapi32",
                 "-lwintrust", "-lcomctl32", "-lwinpthread", "-shared-libgcc"]
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    subprocess.check_call([args.prefix + "g++", "-municode"] + objects + [
        os.path.join(args.deps, name + "-exports.def"), "-o", args.output] + libraries)


parser = argparse.ArgumentParser()
commands = parser.add_subparsers(dest="command", required=True)
for command in ("prepare", "host", "build"):
    sub = commands.add_parser(command)
    sub.add_argument("--prefix", required=True)
    if command == "prepare":
        sub.add_argument("--shim", required=True)
    if command == "host":
        sub.add_argument("--name", required=True)
        sub.add_argument("--deps", required=True)
    if command == "build":
        for option in ("component", "arch", "shim", "deps", "ssl", "zlib", "objdir",
                       "output", "optimize"):
            sub.add_argument("--" + option, required=True)
arguments = parser.parse_args()
{"prepare": prepare, "host": host, "build": build}[arguments.command](arguments)
