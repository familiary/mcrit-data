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

Pinned to a commit and not to v4.0.1 in this recipe. The tag (2018-04-06) is
MIT already, and the MSVC recipes build it, but it does not compile under
GCC: v4.0.1's detours.h guards its LONG_PTR, ULONG_PTR, SYMBOL_INFO and
IMAGEHLP_MODULE64 typedefs on _MSC_VER < 1299, which is true of any compiler
that does not define _MSC_VER, and each one is a "conflicting declaration"
against mingw-w64's own. Defining _MSC_VER on the command line would make GCC
claim to be something it is not, so that leg is not built. Checked on both
architectures.

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
              "Detours'. v4.0.1 is not built with MinGW because its "
              "detours.h redeclares LONG_PTR, ULONG_PTR, SYMBOL_INFO and "
              "IMAGEHLP_MODULE64 whenever _MSC_VER is undefined, and the "
              "only way past that is to pretend to be MSVC. The PicHash "
              "overlap with the MSVC builds of the same commit is zero at "
              "the ten-instruction floor on both architectures. Evidence "
              "behind the family is structural only: Kaspersky names "
              "Detours and DetourTransactionCommitEx in the SharkLoader "
              "chain and publishes no matched function.",
    ),
}
