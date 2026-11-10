"""Build-tree preparation for the SoftEther VPN 5.x MinGW recipe.

softether_vpn5.py's MinGW recipes call this once, after the source is
cloned and before CMake runs. It changes nothing in the repository and
nothing upstream publishes; it edits the freshly cloned build tree and
writes a header directory next to it, and every change is listed here, in
the recipe docstring, in provenance and in the README row. Because of them
the images are NOT byte-identical to a build of unmodified upstream.

1. ``src/CMakeLists.txt``: four lines are deleted. Under ``if(WIN32)``
   upstream appends MSVC switches whatever the compiler::

       set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} /Qspectre")
       set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} /guard:cf")
       set(CMAKE_EXE_LINKER_FLAGS  "${CMAKE_EXE_LINKER_FLAGS} /guard:cf /DYNAMICBASE")
       set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} /CETCOMPAT")

   With GCC they are file names, and the first configure failed on them in
   CMake's own compiler check ("x86_64-w64-mingw32-ld: cannot find
   /guard:cf: No such file or directory", then "CMake will not be able to
   correctly generate this project" at src/Cedar/CMakeLists.txt:5). GCC has
   no Control Flow Guard or Spectre mitigation switch to put in their place;
   ld already marks the image dynamic-base by default. The rest of the
   ``if(WIN32)`` block (the WIN32/_WINDOWS/OS_WIN32 defines) is kept.

2. A header directory, first on the include path of every C and C++
   compilation, holding only what a Windows SDK build gets from the SDK or a
   case-insensitive file system and mingw-w64 11 does not provide:

   * case aliases: upstream includes ``<WinSock2.h>``, ``<DbgHelp.h>``,
     ``<ShlObj.h>`` and the like, which mingw-w64 spells in lower case; each
     alias is one ``#include`` of the lower-case header. ``<cfg.h>``
     (included by mingw's cfgmgr32.h) resolves to Mayaqua's own ``Cfg.h``,
     which is what MSVC does on NTFS and what Microsoft.c's comment
     ("Mayaqua's one gets included instead") relies on, because Microsoft.c
     then defines PNP_VETO_TYPE itself.
   * ``prsht.h``: ``PSWIZBF_ELEVATIONREQUIRED`` (0x00000001), the
     ``PSTMSG(hwnd, msg, wParam, lParam)`` macro (``(BOOL)SNDMSG(...)``, as
     in the Windows SDK; Cedar/WinUi.c calls it) and the
     ``PROPSHEETHEADERA_V2``/``PROPSHEETHEADERW_V2`` names, which in the
     Windows SDK are the full PROPSHEETHEADER structures mingw already has.
   * ``fwpmu.h``: ``FWPM_SESSION_FLAG_DYNAMIC`` (0x00000001),
     ``FWPM_FILTER_FLAG_PERMIT_IF_CALLOUT_UNREGISTERED`` (0x00000008) and
     the two layer GUIDs ``FWPM_LAYER_INBOUND_IPPACKET_V4`` and ``_V6``,
     with the values the Windows SDK's fwpmu.h gives them.
   * ``natupnp.h``, which mingw-w64 does not ship: the IStaticPortMapping,
     IStaticPortMappingCollection and IUPnPNAT interfaces in the method
     order of the published type library (as in Wine's natupnp.idl), plus
     CLSID_UPnPNAT and IID_IUPnPNAT. Only Cedar/Win32Com.cpp uses it.
   * three compiler-dialect shims in the ``WinSock2.h`` alias, which every
     SoftEther file includes first through Mayaqua/MayaType.h and nothing
     else spells that way: ``__forceinline`` is redefined without the
     ``extern`` that mingw's C definition carries, because CMInner.h writes
     ``__forceinline static`` ("multiple storage classes in declaration
     specifiers"); ``__try``/``__except`` become ``if (1)``/``else if (0)``
     because GCC has no structured exception handling in C, which leaves
     Win32.c's SetThreadName-by-exception (MsSetThreadName) without its
     handler; and for C++ only the three-value ``CRYPTO_KEY_TYPE`` enum of
     Mayaqua/Crypto/Key.h is declared before Mayaqua/Crypto/Types.h's
     forward ``typedef enum CRYPTO_KEY_TYPE``, which MSVC accepts and g++
     rejects ("use of enum 'CRYPTO_KEY_TYPE' without previous declaration")
     in Cedar/WinJumpList.cpp and Win32Com.cpp.

3. Two symlinks in the build tree, src/PenCore/pencore.c -> PenCore.c and
   pencore.rc -> PenCore.rc: src/PenCore/CMakeLists.txt names the files in
   lower case, which NTFS resolves and ext4 does not ("Cannot find source
   file: pencore.c" at src/PenCore/CMakeLists.txt:5 stops CMake's generate
   step even though PenCore is not built here).

4. A library directory of case aliases for the import libraries
   src/Mayaqua/CMakeLists.txt names in mixed case (``DbgHelp.Lib``,
   ``Psapi.Lib``, ``Secur32.Lib``, ``WtsApi32.Lib``), which CMake hands to
   ld as ``-lDbgHelp.Lib``: symlinks named ``libDbgHelp.Lib.a`` etc. to
   mingw-w64's lower-case import libraries.

Usage: softether5_mingw.py <source_root> <shim_dir> <mingw_lib_dir>
"""

import os
import sys


_CMAKE_LINES = (
    'set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} /Qspectre")',
    'set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} /guard:cf")',
    'set(CMAKE_EXE_LINKER_FLAGS  "${CMAKE_EXE_LINKER_FLAGS} /guard:cf /DYNAMICBASE")',
    'set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} /CETCOMPAT")',
)

# upstream spelling -> mingw-w64 spelling
_CASE_ALIASES = {
    "AclAPI.h": "aclapi.h",
    "CommCtrl.h": "commctrl.h",
    "DbgHelp.h": "dbghelp.h",
    "Dbghelp.h": "dbghelp.h",
    "IcmpAPI.h": "icmpapi.h",
    "MsHtmHst.h": "mshtmhst.h",
    "Msi.h": "msi.h",
    "NTSecAPI.h": "ntsecapi.h",
    "Psapi.h": "psapi.h",
    "SetupAPI.h": "setupapi.h",
    "ShObjIdl.h": "shobjidl.h",
    "ShlObj.h": "shlobj.h",
    "SoftPub.h": "softpub.h",
    "WS2tcpip.h": "ws2tcpip.h",
    "Ws2tcpip.h": "ws2tcpip.h",
    "Windows.h": "windows.h",
    "WtsApi32.h": "wtsapi32.h",
}

_WINSOCK2 = """\
#include <winsock2.h>
/* SoftEther on mingw-w64: see scripts/corpus/softether5_mingw.py */
#undef __forceinline
#define __forceinline __inline__ __attribute__((__always_inline__))
#ifndef __cplusplus
#define __try if (1)
#define __except(filter) else if (0)
#else
enum CRYPTO_KEY_TYPE
{
	KEY_UNKNOWN,
	KEY_X25519,
	KEY_X448
};
#endif
"""

_PRSHT = """\
#include_next <prsht.h>
#ifndef PSWIZBF_ELEVATIONREQUIRED
#define PSWIZBF_ELEVATIONREQUIRED 0x00000001
#endif
#ifndef PSTMSG
#define PSTMSG(hwndDlg, msg, wParam, lParam) \\
	(BOOL)SNDMSG(hwndDlg, msg, (WPARAM)(wParam), (LPARAM)(lParam))
#endif
typedef PROPSHEETHEADERA PROPSHEETHEADERA_V2;
typedef PROPSHEETHEADERW PROPSHEETHEADERW_V2;
"""

_FWPMU = """\
#include_next <fwpmu.h>
#ifndef FWPM_SESSION_FLAG_DYNAMIC
#define FWPM_SESSION_FLAG_DYNAMIC 0x00000001
#endif
#ifndef FWPM_FILTER_FLAG_PERMIT_IF_CALLOUT_UNREGISTERED
#define FWPM_FILTER_FLAG_PERMIT_IF_CALLOUT_UNREGISTERED 0x00000008
#endif
DEFINE_GUID(FWPM_LAYER_INBOUND_IPPACKET_V4, 0xc86fd1bf, 0x21cd, 0x497e, 0xa0, 0xbb, 0x17, 0x42, 0x5c, 0x88, 0x5c, 0x58);
DEFINE_GUID(FWPM_LAYER_INBOUND_IPPACKET_V6, 0xf52032cb, 0x991c, 0x46e7, 0x97, 0x1d, 0x26, 0x01, 0x45, 0x9a, 0x91, 0xca);
"""

_NATUPNP = """\
#ifndef SE_MINGW_NATUPNP_H
#define SE_MINGW_NATUPNP_H
#include <oaidl.h>
#ifdef __cplusplus
struct IDynamicPortMappingCollection;
struct INATEventManager;
struct IStaticPortMapping : public IDispatch
{
	virtual HRESULT STDMETHODCALLTYPE get_ExternalIPAddress(BSTR *value) = 0;
	virtual HRESULT STDMETHODCALLTYPE get_ExternalPort(long *value) = 0;
	virtual HRESULT STDMETHODCALLTYPE get_InternalPort(long *value) = 0;
	virtual HRESULT STDMETHODCALLTYPE get_Protocol(BSTR *value) = 0;
	virtual HRESULT STDMETHODCALLTYPE get_InternalClient(BSTR *value) = 0;
	virtual HRESULT STDMETHODCALLTYPE get_Enabled(VARIANT_BOOL *value) = 0;
	virtual HRESULT STDMETHODCALLTYPE get_Description(BSTR *value) = 0;
	virtual HRESULT STDMETHODCALLTYPE EditInternalClient(BSTR client) = 0;
	virtual HRESULT STDMETHODCALLTYPE Enable(VARIANT_BOOL enable) = 0;
	virtual HRESULT STDMETHODCALLTYPE EditDescription(BSTR description) = 0;
	virtual HRESULT STDMETHODCALLTYPE EditInternalPort(long port) = 0;
};
struct IStaticPortMappingCollection : public IDispatch
{
	virtual HRESULT STDMETHODCALLTYPE get__NewEnum(IUnknown **value) = 0;
	virtual HRESULT STDMETHODCALLTYPE get_Item(long port, BSTR protocol, IStaticPortMapping **mapping) = 0;
	virtual HRESULT STDMETHODCALLTYPE get_Count(long *value) = 0;
	virtual HRESULT STDMETHODCALLTYPE Remove(long port, BSTR protocol) = 0;
	virtual HRESULT STDMETHODCALLTYPE Add(long external, BSTR protocol, long internal, BSTR client,
		VARIANT_BOOL enabled, BSTR description, IStaticPortMapping **mapping) = 0;
};
struct IUPnPNAT : public IDispatch
{
	virtual HRESULT STDMETHODCALLTYPE get_StaticPortMappingCollection(IStaticPortMappingCollection **collection) = 0;
	virtual HRESULT STDMETHODCALLTYPE get_DynamicPortMappingCollection(IDynamicPortMappingCollection **collection) = 0;
	virtual HRESULT STDMETHODCALLTYPE get_NATEventManager(INATEventManager **manager) = 0;
};
static const CLSID CLSID_UPnPNAT = {0xae1e00aa, 0x3fd5, 0x403c, {0x8a, 0x27, 0x2b, 0xbd, 0xc3, 0x0c, 0xd0, 0xe1}};
static const IID IID_IUPnPNAT = {0xb171c812, 0xcc76, 0x485a, {0x94, 0xd8, 0xb6, 0xb3, 0xa2, 0x79, 0x4e, 0x99}};
#endif
#endif
"""

# upstream's spelling in target_link_libraries -> mingw-w64's import library
# CMake passes the mixed-case ".Lib" names through as "-lDbgHelp.Lib" etc.
# (it strips only a lower-case ".lib"), and ld then looks for
# libDbgHelp.Lib.a: "cannot find -lDbgHelp.Lib: No such file or directory"
# (likewise Psapi, Secur32 and WtsApi32) was the first link's only error.
_LIB_ALIASES = {
    "libDbgHelp.Lib.a": "libdbghelp.a",
    "libPsapi.Lib.a": "libpsapi.a",
    "libSecur32.Lib.a": "libsecur32.a",
    "libWtsApi32.Lib.a": "libwtsapi32.a",
}


# build-tree file upstream's CMake names -> the file as it is spelled on disk
_SOURCE_ALIASES = {
    "src/PenCore/pencore.c": "PenCore.c",
    "src/PenCore/pencore.rc": "PenCore.rc",
}


def _edit_cmake(source_root):
    path = os.path.join(source_root, "src", "CMakeLists.txt")
    with open(path, "rb") as handle:
        lines = handle.read().split(b"\n")
    wanted = {line.encode() for line in _CMAKE_LINES}
    kept = [line for line in lines if line.strip() not in wanted]
    removed = len(lines) - len(kept)
    if removed != len(_CMAKE_LINES):
        raise SystemExit("src/CMakeLists.txt: expected to delete %d lines, matched %d"
                         % (len(_CMAKE_LINES), removed))
    with open(path, "wb") as handle:
        handle.write(b"\n".join(kept))


def _write(path, text):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def main(argv):
    source_root, shim_dir, mingw_lib = argv[1:4]
    _edit_cmake(source_root)
    for name, target in _SOURCE_ALIASES.items():
        link = os.path.join(source_root, name)
        if not os.path.exists(os.path.join(os.path.dirname(link), target)):
            raise SystemExit("missing %s next to %s" % (target, name))
        if not os.path.lexists(link):
            os.symlink(target, link)
    include = os.path.join(shim_dir, "include")
    lib = os.path.join(shim_dir, "lib")
    os.makedirs(include, exist_ok=True)
    os.makedirs(lib, exist_ok=True)
    for name, target in _CASE_ALIASES.items():
        _write(os.path.join(include, name), "#include <%s>\n" % target)
    _write(os.path.join(include, "cfg.h"), '#include "Mayaqua/Cfg.h"\n')
    _write(os.path.join(include, "WinSock2.h"), _WINSOCK2)
    _write(os.path.join(include, "prsht.h"), _PRSHT)
    _write(os.path.join(include, "fwpmu.h"), _FWPMU)
    _write(os.path.join(include, "natupnp.h"), _NATUPNP)
    for name, target in _LIB_ALIASES.items():
        real = os.path.join(mingw_lib, target)
        if not os.path.exists(real):
            raise SystemExit("missing import library %s" % real)
        link = os.path.join(lib, name)
        if os.path.lexists(link):
            os.remove(link)
        os.symlink(real, link)


if __name__ == "__main__":
    main(sys.argv)
