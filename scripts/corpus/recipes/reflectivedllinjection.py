"""Stephen Fewer's ReflectiveDLLInjection, and dismantl's improved fork of it
(mcrit-data issue #15).

The reference reflective loader: a DLL carries its own PE loader in an
exported ``ReflectiveLoader`` function, finds kernel32 by walking the PEB,
resolves LoadLibraryA / GetProcAddress / VirtualAlloc / NtFlushInstructionCache
by ROR-13 hash, maps itself, applies its relocations and calls its own
DllMain. Copied, with the hash constants, into Metasploit's stage DLLs and a
long list of implants, so the loader body is what turns up in samples.

Two pins, bracketing what is encountered:

  * stephenfewer/ReflectiveDLLInjection at 178ba2a, 2013-09-05 - the
    upstream head; the repository has no tags. Three own functions in the DLL
    (``caller``, ``ReflectiveLoader``, ``DllMain``) and six in ``inject.exe``
    (``main``, ``LoadLibraryR``, ``LoadRemoteLibraryR``,
    ``GetReflectiveLoaderOffset``, ``Rva2Offset``, ``GetProcAddressR``).
  * dismantl/ImprovedReflectiveDLLInjection at 8b1bdbb, 2016-06-28 - the
    variant that adds a bootstrap shellcode and lets the loader call a chosen
    export (ExitThread / RtlExitUserThread added, ``MyFunction`` as the
    example payload). Filed under the same family with a distinct version
    string, as the tracker issue proposed; the recipe's ``upstream`` names
    which repository each version comes from.

Function counts are tiny by this corpus's standards and that is the project:
the DLL is one 350-line body plus two small functions. ``min_functions``
states the DLL's measured count; see the recipe for the figure. The inject
executables are the larger half and are built so the project is not
represented by a single artefact.

No upstream source is touched. Three obstacles to a GCC build were found and
each is solved by a flag or by a file generated beside the tree:

  * ReflectiveLoader.h does ``#include <Winsock2.h>``, which mingw-w64 spells
    in lower case and a Linux host does not fold. ``corpus-shim/Winsock2.h``
    forwards to ``<winsock2.h>``. The header is included and never used.
  * ``_ReturnAddress`` is an MSVC intrinsic that mingw-w64's <intrin.h>
    declares and does not implement, so ``caller()`` fails to link.
    ``corpus-shim/intrin.h`` is found first through ``-I``, includes the real
    header with ``#include_next``, and defines the macro as
    ``__builtin_return_address(0)``. ``caller`` is declared noinline upstream,
    which is what the intrinsic's contract needs.
  * ``__try`` / ``__except`` in inject.exe (GetProcAddressR, LoadLibraryR).
    GCC has no SEH, so ``-D__try=if(1)`` and ``-D__except(x)=if(0)`` reduce
    them to the protected block alone. Only the exception handler's body,
    which sets a NULL return, is dropped; the happy path is unchanged.

The reflective DLL is built with upstream's Release defines
(WIN_X86 or WIN_X64, REFLECTIVE_DLL_EXPORTS,
REFLECTIVEDLLINJECTION_VIA_LOADREMOTELIBRARYR and, for the 2013 pin,
REFLECTIVEDLLINJECTION_CUSTOM_DLLMAIN so ReflectiveDll.c's DllMain is the one
linked), at -O2 for upstream's /O2 /Oi.

Measured (kept + removed by the MinGW glue baseline = image total; built on
the runner's twin recipe for MSVC, see reflectivedllinjection_msvc.py):

                        reflective_dll          inject.exe
  2013 MinGW x86        4 + 48 = 52             8 + 128 = 136
  2013 MinGW x64       14 + 49 = 63            39 + 125 = 164
  dismantl MinGW x86    8 + 57 = 65             9 + 129 = 138
  dismantl MinGW x64   20 + 53 = 73            50 + 126 = 176

The project's own functions in those artefacts are 3 per DLL and 6 (2013) or
7 (dismantl, which adds inject_via_remotethread_wow64) per inject.exe; the
rest of each kept count is residue the baseline cannot name. No artefact
reaches the floor of eight on its own project code in the DLL, hence
``min_functions=3``: the number of functions the DLL actually contains
(caller, ReflectiveLoader, DllMain; ReflectiveLoader, DllMain, MyFunction for
dismantl). The injectors clear eight regardless.

Glue survivors, by name and PicHash. Unnamed in these reports and so out of
reach of a name-and-hash filter: ``___chkstk_ms`` (15 instructions; the
unnamed 15-instruction function in every MinGW artefact here, equal to
``___chkstk_ms`` in data/MinGW x64) and the one-instruction import thunks on
x64. Named: ``strstr`` (a thunk) in inject.exe, and in the dismantl DLLs
``sprintf_s``, ``vsprintf_s``, ``_int_vsprintf_s`` and ``_stub`` - libmingwex's
secure-printf, pulled in by MyFunction's sprintf_s and not in the baseline.
Four functions in each dismantl DLL; they are not hidden from the counts above.

PicHash overlap, functions of 10+ instructions: 2013 against dismantl shares
9 (x86) / 8 (x64), which is the injector and DllMain code the fork inherited;
the loaders themselves differ. MinGW against MSVC shares 0 of 9/11 (2013) and
13/14 (dismantl) on both architectures, the case for the MSVC axis. Against
the other loaders already in the corpus nothing project-specific is shared
(sRDI, donut and pe_to_shellcode are shellcode blobs; MemoryModule shares only
``printf`` and ``__scrt_common_main_seh``, both MSVC runtime).
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_SHIM = [
    BuildStep("mkdir -p corpus-shim"),
    BuildStep("printf '#include <winsock2.h>\\n' > corpus-shim/Winsock2.h"),
    BuildStep("printf '#include_next <intrin.h>\\n#undef _ReturnAddress\\n"
              "#define _ReturnAddress() __builtin_return_address(0)\\n' "
              "> corpus-shim/intrin.h"),
]
_ARCH_DEF = "-DWIN_$(echo {arch} | tr a-z A-Z)"
_SEH = "'-D__try=if(1)' '-D__except(x)=if(0)'"


def _rdi(name, version, upstream, git_url, git_ref, license, dll_sources,
         dll_defs, notes, min_functions):
    return Recipe(
        family="ReflectiveDLLInjection",
        version=version,
        upstream=upstream,
        license=license,
        source=Source(git_url=git_url, git_ref=git_ref),
        build=_SHIM + [
            BuildStep("{cc} -O2 -g -shared -Icorpus-shim %s "
                      "-DREFLECTIVE_DLL_EXPORTS %s %s -luser32 "
                      "-o reflective_dll.dll" % (_ARCH_DEF, dll_defs, dll_sources)),
            BuildStep("{cc} -O2 -g %s %s inject/src/*.c -ladvapi32 "
                      "-o inject.exe" % (_ARCH_DEF, _SEH)),
        ],
        artifacts=[
            Artifact(path="reflective_dll.dll", component="reflective_dll.dll"),
            Artifact(path="inject.exe", component="inject.exe"),
        ],
        toolchains=["mingw_x86", "mingw_x64"],
        min_functions=min_functions,
        build_flags="-O2 -g, upstream Release defines; corpus-shim/ for "
                    "Winsock2.h and _ReturnAddress; -D__try/-D__except for "
                    "inject.exe (upstream builds with MSVC /O2 /Oi)",
        notes=notes,
    )


RECIPES = {
    "ReflectiveDLLInjection_2013-09-05": _rdi(
        "ReflectiveDLLInjection_2013-09-05", "2013-09-05",
        "https://github.com/stephenfewer/ReflectiveDLLInjection",
        "https://github.com/stephenfewer/ReflectiveDLLInjection.git",
        "178ba2a6a9feee0a9d9757dcaa65168ced588c12",
        "BSD-3-Clause",
        "dll/src/ReflectiveLoader.c dll/src/ReflectiveDll.c",
        "-DREFLECTIVEDLLINJECTION_VIA_LOADREMOTELIBRARYR "
        "-DREFLECTIVEDLLINJECTION_CUSTOM_DLLMAIN",
        "The reflective DLL and the injector, from upstream's Release "
        "configuration. The x64 reflective_dll is compiled as C++ by upstream "
        "(CompileAsCpp) and as C here. Not rebuilt from the shipped "
        "bin/*.dll, which are v110 /MT builds.",
        min_functions=3),
    "ReflectiveDLLInjection_2016-06-28-dismantl": _rdi(
        "ReflectiveDLLInjection_2016-06-28-dismantl", "2016-06-28-dismantl",
        "https://github.com/dismantl/ImprovedReflectiveDLLInjection",
        "https://github.com/dismantl/ImprovedReflectiveDLLInjection.git",
        "8b1bdbbc3c95174dda1591d66b5882942b527f94",
        "BSD-3-Clause",
        "dll/src/ReflectiveLoader.c dll/src/ReflectiveDll.c "
        "dll/src/MyFunction.c",
        "",
        "dismantl's fork, a different repository from the upstream head and "
        "filed under the same family: a bootstrap shellcode lets the loader "
        "call a chosen export, and the loader gained ExitThread / "
        "RtlExitUserThread handling.",
        min_functions=3),
}
