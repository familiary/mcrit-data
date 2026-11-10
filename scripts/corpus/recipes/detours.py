"""Microsoft Detours - the transaction core and the instruction copiers, MinGW.

Detours rewrites the first bytes of a function with a jump to a replacement
and keeps the displaced instructions in a trampoline. Two halves of the
library are what an analyst meets inside a sample. The transaction core in
detours.cpp is DetourTransactionBegin, DetourUpdateThread, DetourAttach,
DetourDetach and DetourTransactionCommit/CommitEx. The instruction copiers in
disasm.cpp decode just enough x86/x64 to relocate a prologue into the
trampoline (CDetourDis and its per-opcode copy tables). modules.cpp and
image.cpp walk PE headers and import tables; creatwth.cpp is the
DetourCreateProcessWithDll family and uimports.cpp, which it includes, edits
a module's import table.

Why it is here. Issue 12 of the tracker: Kaspersky's 2026-06-24 report on the
SharkLoader chain names Detours and DetourTransactionCommitEx in the
SyncRes.dat stage that delivers Cobalt Strike Beacon. The evidence is
structural - the vendor names the project and an export, and publishes no
function bodies - so the reference data is what lets that be tested rather
than repeated. MinHook (data/MinHook) is the other hooking library from the
same chain and shares no code with this one.

What was built. Upstream produces a static detours.lib from src/Makefile with
nmake, and SMDA has no COFF archive loader. The objects are therefore compiled
here and linked straight into a DLL, which is the same end state the
--whole-archive route gives cryptopp and the MSVC mbedTLS build, minus the
archive in the middle. No upstream file is edited. Seven of the ten objects
src/Makefile links are built: detours, modules, disasm, image, creatwth, and
disolx86 and disolx64 (two-line files that define DETOURS_<ARCH>_OFFLINE_LIBRARY
and include disasm.cpp, so both copiers are present in every image whichever
architecture it targets). disolia64, disolarm and disolarm64 are left out:
they would put Itanium and ARM decoders into an x86 or x64 image, and no
Windows x86/x64 sample's Detours has any use for them.

MinGW compatibility was listed as unverified when the issue was filed. It is
verified here at the pinned commit: i686-w64-mingw32-g++ 13 and
x86_64-w64-mingw32-g++ 13 compile all seven objects with no error, the only
diagnostic being a macro redefinition because detours.h defines
ERROR_DYNAMIC_CODE_BLOCKED, which mingw-w64's winerror.h already carries.

Two recipes. Detours_2026-09-29 is the pinned commit and builds with no
change to upstream. Detours_4.0.1 is the last tagged release (2018-04-06, MIT)
and does not compile under GCC as shipped, so it is built with a generated
shim header plus four recipe-time edits to the build tree. The image is
therefore NOT byte-identical to a build of unmodified upstream, and the
maintainer authorised that for this target. What was tried, in order:

1. The recorded failure. v4.0.1's detours.h guards its LONG_PTR, ULONG_PTR,
   SYMBOL_INFO and IMAGEHLP_MODULE64 typedefs on _MSC_VER < 1299, which is
   true of any compiler that does not define _MSC_VER, and each is a
   "conflicting declaration" against mingw-w64's own. Solved without touching
   the header: a force-included shim (-include detours_mingw_shim.h) includes
   windows.h, imagehlp.h, strsafe.h, intsafe.h and crtdbg.h first and then
   defines _MSC_VER as 1299 for the duration of one #include "src/detours.h",
   and undefines it again. At 1299 the guard is false, and every other
   _MSC_VER test in the sources (>= 1310, >= 1900, > 1400) gives the answer it
   gives with the macro undefined, which is what the commit's MinGW build
   sees. Every mingw-w64 header is included before the define, and the .cpp
   files see the macro undefined; only the text of detours.h itself is
   parsed with it set.
2. SEH. v4.0.1 has no GCC support for __try/__except (20 uses, detours.cpp
   and modules.cpp); the pinned commit handles that in detours.h with
   "#define __try" and "#define __except(x) if (0)". The shim carries the same
   two lines, after detours.h, so the guarded bodies are compiled and the
   handlers are not. This is the same rendering the pinned commit's MinGW
   build has.
3. Command-line defines: -DDETOURS_INTERNAL (the .cpp files define it just
   before including detours.h, which the force-include has already read) and
   -D_CRT_STDIO_ARBITRARY_WIDE_SPECIFIERS=1 (detours.h otherwise #errors
   because windows.h pulled in stdio.h first), -fpermissive, and
   -Isrc. The shim also forward-declares Detour::CImageImportName, which
   image.cpp names in a friend declaration before defining it; GCC does not
   treat that as a declaration, MSVC does.
4. creatwth.cpp: GCC 13 rejects "goto Cleanup" jumping over initialised
   locals ("jump to label 'Cleanup' ... crosses initialization of ..."), a
   hard error that -fpermissive does not downgrade. The one patch to
   upstream source is a sed that splits seven declarations into a
   declaration and an assignment on the same line (line numbers unchanged):
       959  HANDLE hProcess = OpenProcess(...)  ->  HANDLE hProcess; hProcess = OpenProcess(...)
       968  DWORD cSize = ...                   ->  DWORD cSize; cSize = ...
       969  DWORD cOffset = 0;                  ->  DWORD cOffset; cOffset = 0;
       1043 DWORD cSize = 4;                    ->  DWORD cSize; cSize = 4;
       1065 _Field_range_(0, cSize - 4) DWORD cOffset = 0;
                                                ->  ... DWORD cOffset; cOffset = 0;
       1167 DWORD nLen = GetEnvironmentVariableA(...)
       1263 DWORD nLen = GetEnvironmentVariableW(...)
   The step greps the result and fails if fewer than seven lines changed.
   The object code is the same program; only where the stores are is a
   source-level matter.

Measured, on the pinned commit (kept + removed = total):
x86 266 + 53 = 319, x64 272 + 54 = 326, of which 188 and 163 are ten
instructions or more. The removed functions are MinGW startup and runtime
glue. 265 of 266 (x86) and 263 of 272 (x64) kept functions are named.
Against the MSVC builds of the same commit the PicHash overlap at the
ten-instruction floor is zero on both architectures (x64: 117 distinct
hashes here, 164 in the /O2 build, none shared), so this is a separate
rendering and not a duplicate. Detours' own code is the CDetourDis*,
CImage*, Detour* and detour_* functions; what else is in the image is
one-instruction import thunks into kernel32 and the strsafe.h inline
wrappers StringCchPrintfA/W.

Glue survivors, by name and PicHash, none of which the measured baseline
removes: StringCchPrintfA (x64 14085129435439527288, x86
7892978127956841229) and StringCchPrintfW (x64 12930795469493728535, x86
4477995129465285485) are Windows SDK inline functions compiled into
detours.cpp's translation unit, so any consumer of Detours carries them and
any other strsafe.h user does too. __gxx_personality_seh0 (x64) and
___cxa_throw_bad_array_new_length, ___register_frame_info and
___deregister_frame_info (x86) are one-instruction import thunks, PicHash
1253497258561142223 like every other one-instruction thunk in the corpus.
Measured, on v4.0.1 (kept + removed = total): x86 198 + 53 = 251, x64
245 + 54 = 299, of which 168 and 147 are ten instructions or more. 197 of 198
(x86) and 195 of 245 (x64) kept functions are named; the 50 unnamed x64
functions are one-instruction kernel32 import thunks, PicHash
1253497258561142223. PicHash overlap at the ten-instruction floor: 0 with the
v4.0.1 MSVC /O2 build and with the other MSVC builds on both architectures; 32
of 115 distinct x86 hashes and 29 of 106 distinct x64 hashes are shared with the
MinGW build of the 2026-09-29 commit (the same compiler over the code the two
versions have in common). Survivors the baseline does not remove: the strsafe
inline wrappers StringCchPrintfA/W as in the commit build (x64 14085129435439527288
and 12930795469493728535, x86 7892978127956841229 and 4477995129465285485) and
one-instruction import thunks (operator new/delete, __gxx_personality_seh0,
___cxa_throw_bad_array_new_length, ___register_frame_info,
___deregister_frame_info), all PicHash 1253497258561142223.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_OBJS = "detours modules disasm image creatwth disolx86 disolx64".split()

# -O2 because Detours is C++ that a consumer compiles with ordinary release
# flags; upstream's Makefile is /Od, and the MSVC "-nmake" recipe records what
# that gives. WIN32_LEAN_AND_MEAN, _WIN32_WINNT=0x501 and DETOUR_DEBUG=0 are
# the Makefile's own. The DLL has no DllMain, so mingw's startup object
# supplies the entry point, and -shared-libgcc keeps libgcc out of the image.
_COMPILE = " && ".join(
    "{cxx} -O2 -DWIN32_LEAN_AND_MEAN -D_WIN32_WINNT=0x501 -DDETOUR_DEBUG=0 "
    "-c src/%s.cpp -o %s.o" % (o, o) for o in _OBJS)
_LINK = ("{cxx} -shared -shared-libgcc -o detours.dll %s"
         % " ".join(o + ".o" for o in _OBJS))

# v4.0.1 (see the docstring): the shim is written by the recipe, the sed
# splits seven initialised declarations in creatwth.cpp, and the grep makes
# the step fail loudly if upstream's text is not what this expects.
_SHIM_LINES = [
    "#ifndef DETOURS_MINGW_SHIM_H",
    "#define DETOURS_MINGW_SHIM_H",
    "#define _ARM_WINAPI_PARTITION_DESKTOP_SDK_AVAILABLE 1",
    "#include <windows.h>",
    "#include <imagehlp.h>",
    "#include <strsafe.h>",
    "#include <intsafe.h>",
    "#include <crtdbg.h>",
    "#define _MSC_VER 1299",
    '#include "src/detours.h"',
    "#undef _MSC_VER",
    "#define __try",
    "#define __except(x) if (0)",
    "namespace Detour { class CImageImportName; }",
    "#endif",
]
_WRITE_SHIM = "printf '%s\\n' " + " ".join(
    "'%s'" % line for line in _SHIM_LINES) + " > detours_mingw_shim.h"
_SPLIT = [
    ("HANDLE hProcess = ", "HANDLE hProcess; hProcess = "),
    ("DWORD cSize = ", "DWORD cSize; cSize = "),
    ("DWORD cOffset = ", "DWORD cOffset; cOffset = "),
    ("DWORD nLen = ", "DWORD nLen; nLen = "),
]
_PATCH = ("sed -i " + " ".join(
    "-e 's/%s/%s/'" % (a, b) for a, b in _SPLIT)
    + " src/creatwth.cpp && test \"$(grep -c "
    "'; hProcess = \\|; cSize = \\|; cOffset = \\|; nLen = ' "
    "src/creatwth.cpp)\" = 7")
_COMPILE_401 = " && ".join(
    "{cxx} -O2 -fpermissive -Isrc -include detours_mingw_shim.h "
    "-DWIN32_LEAN_AND_MEAN -D_WIN32_WINNT=0x501 -DDETOUR_DEBUG=0 "
    "-DDETOURS_INTERNAL -D_CRT_STDIO_ARBITRARY_WIDE_SPECIFIERS=1 "
    "-c src/%s.cpp -o %s.o" % (o, o) for o in _OBJS)

RECIPES = {
    "Detours_2026-09-29": Recipe(
        family="Detours",
        version="2026-09-29",
        upstream="https://github.com/microsoft/Detours",
        license="MIT, Copyright (c) Microsoft Corporation",
        source=Source(git_url="https://github.com/microsoft/Detours.git",
                      git_ref="1dbd4ea281d73d478aa8d09a8b83fbd265f715f7"),
        build=[BuildStep(_COMPILE), BuildStep(_LINK)],
        artifacts=[Artifact(path="detours.dll", component="detours.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 -shared -shared-libgcc; -DWIN32_LEAN_AND_MEAN "
                    "-D_WIN32_WINNT=0x501 -DDETOUR_DEBUG=0 (the src/Makefile "
                    "defines)",
        notes="Commit 1dbd4ea of microsoft/Detours, 2026-09-29, which is 133 "
              "commits past the v4.0.1 tag and carries the EVEX and REX2 "
              "copiers v4.0.1 does not. Built as seven objects linked into "
              "one DLL, since upstream's static detours.lib cannot be read: "
              "detours, modules, disasm, image, creatwth and the x86 and x64 "
              "offline copiers; the Itanium, ARM and ARM64 copiers are not "
              "linked. Measured: x86 266 functions kept of 319 (53 MinGW "
              "runtime removed), x64 272 of 326 (54 removed), 188 and 163 of "
              "them ten instructions or more. The transaction core "
              "(DetourTransactionBegin, DetourUpdateThread, DetourAttach, "
              "DetourDetach, DetourTransactionCommitEx) and CDetourDis, "
              "CDetourDisX86 and CDetourDisX64 with every Copy* member are "
              "present. The rest of the image is one-instruction kernel32 "
              "import thunks and the strsafe.h inline wrappers "
              "StringCchPrintfA/W, which are Windows SDK code rather than "
              "Detours'. v4.0.1 builds with MinGW only from a patched "
              "tree, as the separate Detours_4.0.1 recipe. The PicHash "
              "overlap with the MSVC builds of the same commit is zero at "
              "the ten-instruction floor on both architectures. Evidence "
              "behind the family is structural only: Kaspersky names "
              "Detours and DetourTransactionCommitEx in the SharkLoader "
              "chain and publishes no matched function.",
    ),
    "Detours_4.0.1": Recipe(
        family="Detours",
        version="4.0.1",
        upstream="https://github.com/microsoft/Detours",
        license="MIT, Copyright (c) Microsoft Corporation",
        source=Source(git_url="https://github.com/microsoft/Detours.git",
                      git_ref="v4.0.1"),
        build=[BuildStep(_WRITE_SHIM), BuildStep(_PATCH),
               BuildStep(_COMPILE_401), BuildStep(_LINK)],
        artifacts=[Artifact(path="detours.dll", component="detours.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 -fpermissive -shared -shared-libgcc; -DWIN32_LEAN_AND_MEAN "
                    "-D_WIN32_WINNT=0x501 -DDETOUR_DEBUG=0 -DDETOURS_INTERNAL "
                    "-D_CRT_STDIO_ARBITRARY_WIDE_SPECIFIERS=1; force-included "
                    "generated shim detours_mingw_shim.h (windows.h first, "
                    "then detours.h with _MSC_VER=1299 for that include only, "
                    "then #define __try / __except(x) if (0)); sed on "
                    "creatwth.cpp splitting 7 initialised declarations that "
                    "goto Cleanup crosses",
        notes="The v4.0.1 tag (2018-04-06, MIT), built with MinGW as seven "
              "objects linked into one DLL. PATCHED BUILD: this image is NOT "
              "byte-identical to a build of unmodified upstream. v4.0.1 does "
              "not compile under GCC as shipped; the recipe generates a shim "
              "header that is force-included (it includes the mingw-w64 "
              "headers, then detours.h with _MSC_VER defined as 1299 for that "
              "one include so its LONG_PTR, ULONG_PTR, SYMBOL_INFO and "
              "IMAGEHLP_MODULE64 typedefs, guarded on _MSC_VER < 1299, are "
              "skipped; it then defines __try as nothing and __except(x) as "
              "if (0), as the later upstream commit does for MinGW) and edits "
              "the build tree once: a sed in creatwth.cpp splits seven "
              "initialised declarations (hProcess, cSize x2, cOffset x2, "
              "nLen x2) into declaration plus assignment because GCC 13 "
              "rejects goto Cleanup across them. SEH handlers are compiled "
              "out, so the guarded bodies are present and the __except "
              "paths are not. Measured: x86 198 functions kept of 251 (53 "
              "MinGW runtime removed), x64 245 of 299 (54 removed), 168 and "
              "147 of them ten instructions or more; 197 of 198 and 195 of "
              "245 named, the rest one-instruction import thunks. PicHash "
              "overlap at the ten-instruction floor: zero with every MSVC "
              "build; 32 (x86) and 29 (x64) distinct hashes shared with the "
              "MinGW build of the 2026-09-29 commit.",
    ),
}


# All ten objects src/Makefile links into detours.lib: the seven above plus
# the Itanium, ARM and ARM64 offline copiers (disolia64, disolarm, disolarm64,
# each disasm.cpp under DETOURS_<ARCH>_OFFLINE_LIBRARY, a host-side decoder).
# These are separate versions ("-allcopiers") so the seven-object images
# above stay as they are.
_OBJS_ALL = _OBJS + "disolia64 disolarm disolarm64".split()
_COMPILE_ALL = " && ".join(
    "{cxx} -O2 -DWIN32_LEAN_AND_MEAN -D_WIN32_WINNT=0x501 -DDETOUR_DEBUG=0 "
    "-c src/%s.cpp -o %s.o" % (o, o) for o in _OBJS_ALL)
_COMPILE_401_ALL = " && ".join(
    "{cxx} -O2 -fpermissive -Isrc -include detours_mingw_shim.h "
    "-DWIN32_LEAN_AND_MEAN -D_WIN32_WINNT=0x501 -DDETOUR_DEBUG=0 "
    "-DDETOURS_INTERNAL -D_CRT_STDIO_ARBITRARY_WIDE_SPECIFIERS=1 "
    "-c src/%s.cpp -o %s.o" % (o, o) for o in _OBJS_ALL)
_LINK_ALL = ("{cxx} -shared -shared-libgcc -o detours.dll %s"
             % " ".join(o + ".o" for o in _OBJS_ALL))

_ALL_NOTE = (" ALL-COPIERS VARIANT: all ten objects of upstream's "
             "src/Makefile are linked, the seven of the base build plus the "
             "Itanium, ARM and ARM64 offline copiers (disolia64, disolarm, "
             "disolarm64: disasm.cpp under DETOURS_<ARCH>_OFFLINE_LIBRARY, "
             "exporting DetourCopyInstructionIA64/ARM/ARM64), which is the "
             "whole of what detours.lib carries. A separate version so the "
             "seven-object images are unchanged.")

RECIPES["Detours_2026-09-29-allcopiers"] = Recipe(
    family="Detours",
    version="2026-09-29-allcopiers",
    upstream=RECIPES["Detours_2026-09-29"].upstream,
    license=RECIPES["Detours_2026-09-29"].license,
    source=RECIPES["Detours_2026-09-29"].source,
    build=[BuildStep(_COMPILE_ALL), BuildStep(_LINK_ALL)],
    artifacts=[Artifact(path="detours.dll", component="detours.dll")],
    toolchains=["mingw_x86", "mingw_x64"],
    build_flags=RECIPES["Detours_2026-09-29"].build_flags
    + "; all ten src/Makefile objects linked (adds disolia64, disolarm, "
      "disolarm64)",
    notes="Commit 1dbd4ea of microsoft/Detours, 2026-09-29, built with "
          "MinGW exactly as the Detours_2026-09-29 recipe." + _ALL_NOTE,
)
RECIPES["Detours_4.0.1-allcopiers"] = Recipe(
    family="Detours",
    version="4.0.1-allcopiers",
    upstream=RECIPES["Detours_4.0.1"].upstream,
    license=RECIPES["Detours_4.0.1"].license,
    source=RECIPES["Detours_4.0.1"].source,
    build=[BuildStep(_WRITE_SHIM), BuildStep(_PATCH),
           BuildStep(_COMPILE_401_ALL), BuildStep(_LINK_ALL)],
    artifacts=[Artifact(path="detours.dll", component="detours.dll")],
    toolchains=["mingw_x86", "mingw_x64"],
    build_flags=RECIPES["Detours_4.0.1"].build_flags
    + "; all ten src/Makefile objects linked (adds disolia64, disolarm, "
      "disolarm64)",
    notes="The v4.0.1 tag built with MinGW from the same patched tree as "
          "the Detours_4.0.1 recipe. PATCHED BUILD: this image is NOT "
          "byte-identical to a build of unmodified upstream (generated "
          "force-included shim detours_mingw_shim.h and the seven-line sed "
          "on creatwth.cpp described for Detours_4.0.1)." + _ALL_NOTE,
)
