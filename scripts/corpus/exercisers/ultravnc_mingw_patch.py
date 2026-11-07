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
