"""LayeredSyscall (White Knight Labs) - VEH call-stack spoofing over indirect syscalls.

Credited in SysWhispers4's reference table through the White Knight Labs
blog post, which links the implementation at WKL-Sec/LayeredSyscall. The
post is an article and would be skipped; the repository it links is source
and is built here.

What the project does, and what makes it worth a family of its own rather
than a variant of the gates: it does not resolve syscall numbers in order to
issue a syscall from its own pages. It sets a hardware breakpoint on a real
Win32 API's entry - via ``Dr0``-``Dr3`` and a vectored exception handler -
lets the program call that API normally, and when the breakpoint fires it
rewrites ``Rip`` in the trapped ``CONTEXT`` so execution continues into the
syscall stub with the service number it wants. The call stack that an EDR
walks at that moment is the legitimate one the real API left behind, which
is the "layered" part and the reason the technique is listed beside
WithSecure's call-stack spoofing work.

The recognisable code is ``HandlerHwBp``, the exception handler that does
that rewriting, with ``AddHwBp``, ``SetHwBp``, ``_SetHwBp``,
``IntializeHooks``, ``DestroyHooks``, ``GetSsnByName`` and
``InitializeDllInfo`` around it, plus ``RetrieveSyscallAddress`` and the
per-function wrappers in FuncWrappers.cpp.

**MSVC only, and measured rather than assumed.** Two independent obstacles
stop a mingw-w64 build, neither reachable from the command line:

* ``imports.h`` declares ``RtlQueryHeapInformation`` and
  ``RtlSetHeapInformation`` as returning ``NTSTATUS``, while mingw-w64's
  ``winnt.h`` already declares both returning ``DWORD``. Two ``extern "C"``
  declarations of one name with different types is ill-formed, and GCC
  reports "conflicting declaration of C function". The Windows SDK does not
  declare either, so MSVC sees no conflict.
* ``HookModule.cpp:95`` writes ``sizeof CONTEXT`` without parentheses, which
  is ``sizeof`` applied to a type name - an MSVC extension that GCC rejects
  outright.

Fixing either would mean editing upstream, which this corpus does not do.

**No LICENSE file** in the repository. Recorded as the fact it is.

Built as the console EXE it is - ``demo.cpp`` carries ``main`` - so the MSVC
startup glue is in the image and is subtracted by the measured baseline
rather than by this recipe. ``#pragma comment(lib, "ntdll.lib")`` in
demo.cpp supplies that import library, but nothing supplies user32, which
``demofunction``'s ``MessageBox`` call needs, so the link names it.
Nothing is run.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# /DUNICODE /D_UNICODE because HookModule.cpp:21 passes a wide literal to
# MessageBox, which is the -A form unless UNICODE is defined: without them cl
# reports C2664, "cannot convert argument 2 from 'LPCWSTR' to 'LPCSTR'".
# Upstream builds from a project file that defines it; there is none in the
# repository, so the compile line has to supply it. The same define is needed
# on the mingw side of FreshyCalls for the same reason.
_CFLAGS = ("/nologo /c /O2 /MD /Zi /EHsc /std:c++17 /DUNICODE /D_UNICODE "
           "/I. /Fdls.pdb")
_STEPS = (
    BuildStep("cl %s /Fodemo.obj demo.cpp" % _CFLAGS),
    BuildStep("cl %s /FoHookModule.obj HookModule.cpp" % _CFLAGS),
    BuildStep("cl %s /FoFuncWrappers.obj FuncWrappers.cpp" % _CFLAGS),
    BuildStep("link /nologo /DEBUG /Brepro /OPT:NOREF /OPT:NOICF "
              "/INCREMENTAL:NO /PDB:ls.pdb /OUT:layeredsyscall.exe "
              # user32.lib for MessageBoxW, which HookModule.cpp's
              # demofunction calls: upstream's #pragma comment(lib, ...)
              # covers ntdll only, so without it the link fails with
              # "unresolved external symbol __imp_MessageBoxW".
              "demo.obj HookModule.obj FuncWrappers.obj user32.lib"),
)


RECIPES = {
    "LayeredSyscall_2024-07-31": Recipe(
        family="LayeredSyscall",
        version="2024-07-31",
        upstream="https://github.com/WKL-Sec/LayeredSyscall",
        license="none stated",
        source=Source(git_url="https://github.com/WKL-Sec/LayeredSyscall.git",
                      git_ref="19364dd361056432fb63e52679a2c13645a383a9"),
        build=list(_STEPS),
        artifacts=[Artifact(path="layeredsyscall.exe",
                            component="layeredsyscall.exe",
                            pdb="ls.pdb",
                            # is_library stays true, as it is for every
                            # executable in this corpus: MCRIT keys its
                            # library-versus-malware views off that flag and
                            # validate refuses a reference sample without it.
                            # It says "this is reference material", not "this
                            # is a .dll".
                            is_library=True)],
        # x64: the technique reads and rewrites Rip and the Dr registers,
        # which exist in that form only in the 64-bit CONTEXT.
        toolchains=["msvc_x64"],
        build_flags=("cl /O2 /MD /Zi /EHsc /std:c++17 /DUNICODE /D_UNICODE, "
                     "linked /DEBUG "
                     "/Brepro /OPT:NOREF /OPT:NOICF /INCREMENTAL:NO"),
        # Eight functions in HookModule.cpp and the wrapper layer in
        # FuncWrappers.cpp; the floor is set below the project's own count
        # so a build that loses one object still fails it.
        min_functions=10,
        notes="Hardware-breakpoint and VEH based call-stack spoofing over "
              "indirect syscalls: the breakpoint fires inside a legitimate "
              "Win32 API and the handler rewrites Rip in the trapped "
              "CONTEXT, so the stack an EDR walks is the real API's. "
              "HandlerHwBp is the body worth matching. MSVC only - "
              "upstream's imports.h conflicts with mingw-w64's winnt.h on "
              "the return type of RtlQueryHeapInformation, and "
              "HookModule.cpp uses the MSVC-only unparenthesised "
              "'sizeof CONTEXT'.",
    ),
}
