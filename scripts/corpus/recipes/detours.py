"""Microsoft Detours - the transaction core and the instruction copiers, MinGW.

Detours rewrites the first bytes of a function with a jump to a replacement,
and keeps the displaced instructions in a trampoline. Two halves of the
library are what an analyst meets inside a sample: the transaction core in
detours.cpp (DetourTransactionBegin, DetourUpdateThread, DetourAttach,
DetourDetach, DetourTransactionCommit/CommitEx), and the instruction copiers
in disasm.cpp, which decode just enough x86/x64 to relocate a prologue into
the trampoline (CDetourDis, with its per-opcode tables). modules.cpp and
image.cpp walk PE headers and import tables; creatwth.cpp is the
DetourCreateProcessWithDll family and uimports.cpp, which it includes, edits
a module's import table.

Upstream builds a static detours.lib from src/Makefile (nmake). SMDA has no
COFF archive loader, so the objects are compiled here and linked straight
into a DLL, which is the same end state the --whole-archive route gives
cryptopp and the MSVC mbedTLS build, without an archive in the middle. No
upstream file is edited.

"MinGW compatibility is unverified" was the state of knowledge when this was
queued; it is verified now: i686-w64-mingw32-g++ 13 and x86_64-w64-mingw32-g++
13 compile detours.cpp, disasm.cpp, modules.cpp, image.cpp and creatwth.cpp
with no error. The only diagnostic is a macro-redefinition note, because
detours.h defines ERROR_DYNAMIC_CODE_BLOCKED, which mingw-w64's winerror.h
already carries.

Which objects, and which are left out. src/Makefile links ten:
detours, modules, disasm, image, creatwth and one disol*.cpp per
architecture (x86, x64, ia64, arm, arm64), each of which is a two-line file
defining DETOURS_<ARCH>_OFFLINE_LIBRARY and including disasm.cpp. Built here:
the five core objects plus disolx86 and disolx64 - the two copiers a Windows
sample can carry. disolia64, disolarm and disolarm64 are not linked: they
would put an ARM and an Itanium instruction decoder into an x86 image, which
no x86 sample's Detours has any use for.

Pinned to a commit rather than v4.0.1. The tag (2018-04-06) is MIT already,
but upstream has since moved on by 133 commits, among them x64 and ARM64
instruction-copier fixes, and the issue asks for a post-4.0.1 pin.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_OBJS = ("detours modules disasm image creatwth disolx86 disolx64").split()

# -fno-lto is not needed (no LTO is on); -O2 because Detours is C++ that a
# consumer compiles with the usual release flags. WIN32_LEAN_AND_MEAN and
# _WIN32_WINNT=0x501 are the Makefile's own. The DLL has no DllMain: mingw's
# startup object supplies the entry point. -shared-libgcc so no libgcc is
# pulled in statically.
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
                    "-D_WIN32_WINNT=0x501 -DDETOUR_DEBUG=0",
        notes="Placeholder.",
    ),
}
