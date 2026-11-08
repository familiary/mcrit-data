"""Build-tree patches that enable winvnc.exe in UltraVNC's CMake tree.

Usage: ultravnc_mingw_winvnc_patch.py <UltraVNC source root>
(run by scripts/corpus/recipes/ultravnc_mingw.py after ultravnc_mingw_patch.py;
every change is listed in that recipe's docstring, patches 14 onward).

Each entry is (file, old, new, count); `old` must occur exactly `count` times
or the script stops, so a pin that moves cannot be patched silently.
"""
import os
import re
import sys

root = sys.argv[1]

PATCHES = [
    # Upstream comments winvnc out of the CMake tree.
    ("cmake/CMakeLists.txt", "#add_subdirectory(winvnc)", "add_subdirectory(winvnc)", 1),
    # libudtcloud: the UdtCloudlib sources are not in the UltraVNC repository
    # and winvnc.vcxproj neither compiles nor links them (_CLOUD is defined
    # nowhere, CloudDialog.cpp is not a ClCompile item).
    ("cmake/winvnc/CMakeLists.txt", "    libudtcloud\n", "", 1),
    ("cmake/winvnc/CMakeLists.txt", "    CloudDialog.cpp\n", "", 1),
    # The CMake source list is stale against winvnc.vcxproj: inifile.cpp moved
    # to common/, initipp.cpp is gone, and seven ClCompile items are missing.
    ("cmake/winvnc/CMakeLists.txt", "    inifile.cpp\n", "", 1),
    ("cmake/winvnc/CMakeLists.txt", "    initipp.cpp\n", "", 1),
    ("cmake/winvnc/CMakeLists.txt", "    ../../common/win32_helpers.cpp\n",
     "    ../../common/win32_helpers.cpp\n    ../../common/inifile.cpp\n"
     "    ../loadmemory/MemoryModule.c\n    ../loadmemory/loadDllFromMemory.cpp\n"
     "    DlgChangePassword.cpp\n    RulesListView.cpp\n    ScSelect.cpp\n"
     "    SchannelTLS.cpp\n", 1),
    # libzip32 / libzipunzip no longer exist (patch 1); minizip-ng is linked.
    ("cmake/winvnc/CMakeLists.txt", "    libzip32\n", "", 1),
    ("cmake/winvnc/CMakeLists.txt", "    libzipunzip\n", "", 1),
    # GCC's __FUNCTION__ is a variable, not a string literal, so MSVC's
    # string-literal concatenation `__FUNCTION__ " : " s` does not compile
    # (`error: expected ')' before string constant`, ~400 sites). The prefix
    # is dropped from the log text; the argument is used as written.
    ("winvnc/winvnc/stdhdrs.h", '#define VNCLOG(s)\t(__FUNCTION__ " : " s)', "#define VNCLOG(s)\t(s)", 1),
    ("winvnc/winvnc/benchmark.cpp", '#define VNCLOG(s)\t(__FUNCTION__ " : " s)', "#define VNCLOG(s)\t(s)", 1),
    ("DSMPlugin/DSMPlugin.cpp", '#define VNCLOG(s)\t(__FUNCTION__ " : " s)', "#define VNCLOG(s)\t(s)", 1),
    # SEH __try/__except(EXCEPTION_EXECUTE_HANDLER) around one call: GCC has
    # no __try/__except. The call is made without the guard, so a hardware
    # exception inside UnZipDirectory is no longer swallowed (it would end the
    # process).
    ("winvnc/winvnc/vncclient.cpp",
     "\t\t__try\n\t\t{\n\t\t\tbUnzipOk = m_pZipUnZip->UnZipDirectory(szPathW, szFileNameW);\n\t\t}\n"
     "\t\t__except(EXCEPTION_EXECUTE_HANDLER)\n\t\t{\n\t\t\tbUnzipOk = false;\n\t\t}\n",
     "\t\tbUnzipOk = m_pZipUnZip->UnZipDirectory(szPathW, szFileNameW);\n", 1),
    # The Windows headers define min() as a macro for MSVC; mingw-w64's do not
    # in C++.
    ("winvnc/winvnc/SchannelTLS.cpp", '#include "vnclog.h"\n',
     '#include "vnclog.h"\n#include <algorithm>\nusing std::min;\n', 1),
    # MSVC's 64-bit integer literal suffix (`unable to find numeric literal
    # operator 'operator""ui64'`).
    ("winvnc/winvnc/Dtwinver.cpp", "ui64", "ULL", 4),
]

for rel, old, new, n in PATCHES:
    p = "%s/%s" % (root, rel)
    s = open(p, encoding="latin-1", newline="").read()
    crlf = "\r\n" in s
    o = old.replace("\n", "\r\n") if crlf else old
    nw = new.replace("\n", "\r\n") if crlf else new
    if s.count(o) != n:
        sys.exit("%s: expected %d occurrence(s) of %r, found %d" % (rel, n, old[:50], s.count(o)))
    open(p, "w", encoding="latin-1", newline="").write(s.replace(o, nw))
    print("patched", rel)

# Appended to the winvnc target (as vncviewer's): the vcxproj Release defines
# (_CRT_SECURE_NO_WARNINGS; _X64 is already defined by cmake/CMakeLists.txt), C++17, the libraries it links, and
# the force-included compat header. UVNC_COMPAT, UVNC_SEH, UVNC_DEPS_LIB and
# are passed by the recipe.
with open("%s/cmake/winvnc/CMakeLists.txt" % root, "a") as f:
    f.write("""
target_compile_definitions(${PROJECT_NAME} PRIVATE _CRT_SECURE_NO_WARNINGS SODIUM_STATIC)
target_compile_options(${PROJECT_NAME} PRIVATE -fpermissive -std=gnu++17 "SHELL:-include ${UVNC_COMPAT}" "SHELL:-include ${UVNC_WINVNC_COMPAT}" "SHELL:-include ${UVNC_SEH}")
target_link_directories(${PROJECT_NAME} PRIVATE ${UVNC_DEPS_LIB})
target_link_libraries(${PROJECT_NAME} PRIVATE ${UVNC_DEPS_LIB}/libminizip-ng.a winmm d3d11 dxgi bcrypt ncrypt crypt32 secur32)
""")
print("appended cmake/winvnc/CMakeLists.txt")

# Case-folded include names, as in ultravnc_mingw_patch.py (symbolic links
# next to the real file; no file is edited), for the winvnc sources
# (`vncEncoder.h` is vncencoder.h in git).
def _resolve_ci(start, name):
    cur = start
    for part in name.split("/"):
        if part == "..":
            cur = os.path.dirname(cur)
        elif part != ".":
            if not os.path.isdir(cur):
                return None
            hit = [e for e in os.listdir(cur) if e.lower() == part.lower()]
            if not hit:
                return None
            cur = os.path.join(cur, hit[0])
    return cur


links = []
for d in ["winvnc/winvnc", "winvnc/loadmemory", "DSMPlugin", "common", "rfb"]:
    for dp, _, fs in os.walk(os.path.join(root, d)):
        for f in sorted(fs):
            if not f.lower().endswith((".cpp", ".c", ".h", ".rc")):
                continue
            for line in open(os.path.join(dp, f), encoding="latin-1"):
                m = re.match(r'\s*#\s*include\s*"([^"]+)"', line)
                if not m:
                    continue
                name = m.group(1).replace("\\", "/")
                want = os.path.normpath(os.path.join(dp, name))
                if os.path.lexists(want):
                    continue
                real = _resolve_ci(dp, name)
                if real and os.path.exists(real) and real != want:
                    os.symlink(os.path.relpath(real, os.path.dirname(want)), want)
                    links.append(os.path.relpath(want, root))
for l in sorted(set(links)):
    print("case-fold link", l)

# Stand-in forwarding headers (as ultravnc_mingw_patch.py generates Dsgetdc.h):
# for every <system header> the winvnc sources include that mingw-w64 only has
# in another case, a file with the spelled name containing
# `#include <real-name>`, in <source root>/casefold-inc (on CPATH).
import glob

sysdirs = glob.glob("/usr/*-w64-mingw32/include")
have = {}
for d in sysdirs:
    for e in os.listdir(d):
        have.setdefault(e.lower(), e)
os.makedirs("%s/casefold-inc" % root, exist_ok=True)
seen = set()
for d in ["winvnc/winvnc", "winvnc/loadmemory", "DSMPlugin", "common", "rfb"]:
    for dp, _, fs in os.walk(os.path.join(root, d)):
        for f in sorted(fs):
            if not f.lower().endswith((".cpp", ".c", ".h")):
                continue
            for line in open(os.path.join(dp, f), encoding="latin-1"):
                m = re.match(r'\s*#\s*include\s*<([^>]+)>', line)
                if not m:
                    continue
                name = m.group(1).replace("\\", "/")
                real = have.get(name.lower())
                if real and real != name and "/" not in name and name not in seen:
                    seen.add(name)
                    with open("%s/casefold-inc/%s" % (root, name), "w") as o:
                        o.write("#include <%s>\n" % real)
for name in sorted(seen):
    print("stand-in header", name)
