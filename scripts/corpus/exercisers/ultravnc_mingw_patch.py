"""Build-tree patches for the UltraVNC MinGW-w64 recipe.

Usage: ultravnc_mingw_patch.py <UltraVNC source root>
(run by scripts/corpus/recipes/ultravnc_mingw.py; every change is listed in that
recipe's docstring).

Each entry is (file, old, new, count); `old` must occur exactly `count` times
(or one of the counts when a tuple is given: the 1.8.3.1 source no longer has
the MSVC-only construct that 1.8.2.9 and 1.8.3.0 have in ClientConnectionTLS.cpp) or the script stops, so a pin that moves cannot be patched silently.
"""
import sys

root = sys.argv[1]

PATCHES = [
    # goto over initialisations (see the FileTransfer.cpp entries below); GCC
    # rejects these even under -fpermissive.
    ("repeater/socket_functions.cpp",
     "\tDWORD start=0;\n\tDWORD stop=0;\n\tint measure_counter=0;\n\tlong temp_bytes=0;\n",
     "\tDWORD start; start=0;\n\tDWORD stop; stop=0;\n\tint measure_counter; measure_counter=0;\n"
     "\tlong temp_bytes; temp_bytes=0;\n", 1),
    ("uvnckeyboardhelper/uvnckeyboardhelper/uvnckeyboardhelper.cpp",
     "DWORD dwEvent = WaitForMultipleObjects(1,Events_ini,FALSE,5000);",
     "DWORD dwEvent; dwEvent = WaitForMultipleObjects(1,Events_ini,FALSE,5000);", 1),
    ("uvnckeyboardhelper/uvnckeyboardhelper/uvnckeyboardhelper.cpp",
     "int counter=0;", "int counter; counter=0;", 1),
    # windmc keywords are case-sensitive: `MessageId`, not `MessageID`
    # (`In messages.mc at line 13: parser: syntax error.`).
    ("addon/eventMessageLogger/messages.mc", "MessageID=", "MessageId=", 3),
    # cmake/ still lists the Info-ZIP libraries that the tree no longer has
    # (zipunzip_src/ was removed when MiniZipNG.cpp replaced them).
    ("cmake/CMakeLists.txt", "add_subdirectory(libzip32)\n", "", 1),
    ("cmake/CMakeLists.txt", "add_subdirectory(libzipunzip)\n", "", 1),
    ("cmake/vncviewer/CMakeLists.txt", "    libzip32\n", "", 1),
    ("cmake/vncviewer/CMakeLists.txt", "    libzipunzip\n", "", 1),
    # CredentialManager.cpp is in vncviewer.vcxproj and missing from the list.
    ("cmake/vncviewer/CMakeLists.txt", "    Daemon.cpp\n", "    CredentialManager.cpp\n    Daemon.cpp\n", 1),
    # windres on Linux does not turn the backslash of a resource path into a
    # directory separator.
    ("vncviewer/res/vncviewer.rc", '"stat\\\\chat.bmp"', '"stat/chat.bmp"', 1),
    ("vncviewer/res/vncviewer.rc", '"stat\\\\FT.bmp"', '"stat/FT.bmp"', 1),
    # SEH __try/__finally -> a scope guard that leaves the section.
    ("vncviewer/ClientConnection.cpp",
     "\t__try {\n\t\tEnterCriticalSection(&crit);\n"
     "\t\tWriteTransformed(buf, bytes, msgType, false);\n\t}\n"
     "\t__finally {\n\t\tLeaveCriticalSection(&crit);\n\t}\n",
     "\tEnterCriticalSection(&crit);\n"
     "\tstruct CritLeave { CRITICAL_SECTION *c; ~CritLeave() { LeaveCriticalSection(c); } } critLeave = { &crit };\n"
     "\tWriteTransformed(buf, bytes, msgType, false);\n", 1),
    # MSVC binds a temporary to a non-const lvalue reference.
    ("vncviewer/ClientConnectionTLS.cpp",
     "Handshake(DynBuffer(), outbuf)", "Handshake(uvnc_lvalue(DynBuffer()), outbuf)", (0, 1)),
    # goto over initialisations (MSVC allows it): split declaration and
    # initialisation, which keeps the values the jump sees.
    ("vncviewer/FileTransfer.cpp",
     "\tchar szSavedParentPath[MAX_PATH] = {0};\n\tbool bDirectPath = false;\n",
     "\tchar szSavedParentPath[MAX_PATH]; memset(szSavedParentPath, 0, sizeof(szSavedParentPath));\n"
     "\tbool bDirectPath; bDirectPath = false;\n", 1),
    ("vncviewer/FileTransfer.cpp",
     "\tbool bDirectPath = false;\n", "\tbool bDirectPath; bDirectPath = false;\n", 1),
    ("vncviewer/FileTransfer.cpp",
     "\tWCHAR ofDirStrippedW[MAX_PATH] = {0};",
     "\tWCHAR ofDirStrippedW[MAX_PATH]; memset(ofDirStrippedW, 0, sizeof(ofDirStrippedW));", 1),
    ("vncviewer/FileTransfer.cpp",
     "\tint nIndex = SendDlgItemMessage(hWnd, IDC_LOCAL_DRIVECB, CB_GETCURSEL, 0, 0L);",
     "\tint nIndex; nIndex = SendDlgItemMessage(hWnd, IDC_LOCAL_DRIVECB, CB_GETCURSEL, 0, 0L);", 1),
    ("vncviewer/FileTransfer.cpp",
     "\tint nIndex = SendDlgItemMessage(hWnd, IDC_REMOTE_DRIVECB, CB_GETCURSEL, 0, 0L);",
     "\tint nIndex; nIndex = SendDlgItemMessage(hWnd, IDC_REMOTE_DRIVECB, CB_GETCURSEL, 0, 0L);", 1),
]

for rel, old, new, n in PATCHES:
    p = "%s/%s" % (root, rel)
    s = open(p, encoding="latin-1", newline="").read()
    crlf = "\r\n" in s
    o = old.replace("\n", "\r\n") if crlf else old
    nw = new.replace("\n", "\r\n") if crlf else new
    allowed = n if isinstance(n, tuple) else (n,)
    if s.count(o) not in allowed:
        sys.exit("%s: expected %s occurrence(s) of %r, found %d" % (rel, allowed, old[:50], s.count(o)))
    open(p, "w", encoding="latin-1", newline="").write(s.replace(o, nw))
    print("patched", rel)

# The vcxproj builds the viewer as a Unicode program against minizip-ng and
# libsodium; the CMake file is the ANSI one with neither. Appended, so the
# other CMake projects (which are ANSI programs) keep their upstream flags.
# UVNC_COMPAT (the force-included header) and UVNC_DEPS_LIB (the directory of
# the pinned static dependencies) are passed to cmake by the recipe.
with open("%s/cmake/vncviewer/CMakeLists.txt" % root, "a") as f:
    f.write("""
target_compile_definitions(${PROJECT_NAME} PRIVATE UNICODE _UNICODE SODIUM_STATIC)
target_compile_options(${PROJECT_NAME} PRIVATE -fpermissive "SHELL:-include ${UVNC_COMPAT}")
target_link_options(${PROJECT_NAME} PRIVATE -municode)
target_link_directories(${PROJECT_NAME} PRIVATE ${UVNC_DEPS_LIB})
target_link_libraries(${PROJECT_NAME} PRIVATE ${UVNC_DEPS_LIB}/libminizip-ng.a ${UVNC_DEPS_LIB}/libsodium.a bcrypt crypt32)
""")
print("appended cmake/vncviewer/CMakeLists.txt")

# Case-folded include names. The sources were written on Windows and include
# `ldapauth.h`, `resource.h`, `DSMPlugin.h`, `../../../winvnc/winvnc/localization.h`
# while the files in git are ldapAuth.h, Resource.h, dsmplugin.h and
# Localization.h; a case-sensitive file system cannot open them. For every
# quoted include that does not resolve but resolves ignoring case, a symbolic
# link with the spelled name is created next to the real file (no file is
# edited).
import os
import re

CASE_DIRS = ["addon/ms-logon", "uvnckeyboardhelper", "uvnc_settings"]


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
for d in CASE_DIRS:
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

# Stand-in forwarding headers for system headers the sources include with
# another case than mingw-w64 spells them (<Dsgetdc.h> -> dsgetdc.h,
# <SDKDDKVer.h> -> sdkddkver.h). The directory is put on CPATH by the recipe.
os.makedirs("%s/casefold-inc" % root, exist_ok=True)
for name, real in [("Dsgetdc.h", "dsgetdc.h"), ("SDKDDKVer.h", "sdkddkver.h")]:
    with open("%s/casefold-inc/%s" % (root, name), "w") as f:
        f.write("#include <%s>\n" % real)
    print("stand-in header", name)

# Per-target additions, appended so that upstream's own lines stay as they are.
# UVNC_SEH is the force-included try/finally header (ultravnc_mingw_seh.h).
SEH = 'target_compile_options(${PROJECT_NAME} PRIVATE "SHELL:-include ${UVNC_SEH}")\n'
for rel, text in [
    ("authSSP", SEH),
    ("MSLogonACL", SEH),
    ("workgrpdomnt4", SEH),
    # 32-bit only: i686 msvcrt.dll has no _ltoa_s (undefined reference to
    # `_imp___ltoa_s`); UVNC_REPEATER_X86 is set by the recipe on x86 only.
    # uvnc_settings: the _com_util conversion functions (UVNC_COMSUPP, the
    # recipe-generated extract of ReactOS's comsupp.cpp) and iphlpapi, which
    # upnp.cpp asks for with `#pragma comment(lib, "iphlpapi")`, ignored by GCC
    # (`undefined reference to `GetAdaptersInfo'`). upstream's own
    # target_link_libraries uses the plain signature, so this one does too.
    ("uvnc_settings", "target_sources(${PROJECT_NAME} PRIVATE ${UVNC_COMSUPP})\n"
     "target_link_libraries(${PROJECT_NAME} iphlpapi)\n"),
    ("repeater", 'if(UVNC_REPEATER_X86)\n  target_compile_options(${PROJECT_NAME} PRIVATE "SHELL:-include ${UVNC_REPEATER_X86}")\nendif()\n'),
]:
    with open("%s/cmake/%s/CMakeLists.txt" % (root, rel), "a") as f:
        f.write("\n" + text)
    print("appended cmake/%s/CMakeLists.txt" % rel)
