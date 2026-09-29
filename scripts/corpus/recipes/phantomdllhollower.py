"""Phantom DLL hollowing - Forrest Orr's proof of concept, MinGW, both
architectures.

The PoC for the "Malicious Memory Artifacts Part I: DLL Hollowing" post, and
the reference implementation of the variant the technique is named for. DLL
hollowing maps a real system DLL as an image section and writes a payload into
the hole in its ``.text``, so the region an analyst sees is ``MEM_IMAGE``
backed by a legitimate file rather than the private ``RWX`` allocation a
VirtualAlloc loader leaves behind. The phantom variant removes the last
artefact that gives the classic one away: instead of mapping the file and then
writing through it - which turns the touched pages private and copy-on-write -
it opens the DLL inside an NTFS transaction with ``CreateFileTransactedW``,
writes the payload into the *transacted* file contents, and creates the
``SEC_IMAGE`` section from that handle. The transaction is never committed, so
the file on disk is untouched and the mapped view is a clean image section
that happens to contain the payload.

What is in the repository, measured
-----------------------------------

Two translation units and nothing else: ``PhantomDllHollower/
PhantomDllHollower.cpp`` (365 lines) and ``MemSweep/MemSweep.cpp`` (295
lines), one Visual Studio 2019 solution with the two projects in it, four
``Platform x Configuration`` combinations, ``PlatformToolset`` v142. No
headers of the project's own, no vendored third-party code anywhere in the
tree, no submodules, and nothing statically linked: neither ``.vcxproj``
carries an ``AdditionalDependencies`` entry and neither source file has a
``#pragma comment(lib, ...)``. Each project's entry point is ``wmain``.
Upstream's Release is ``/O2`` plus ``WholeProgramOptimization`` (``/GL``) and
``MultiThreaded`` (``/MT``), character set MultiByte, subsystem Console.

So the two artefacts here are the whole project, and every function in them
that is not compiler runtime is Forrest Orr's.

Licensed GNU GPLv3: ``LICENSE`` at the repository root is the verbatim GPLv3
text and both source files carry "Forrest Orr - 2019 ... Licensed under GNU
GPLv3" in their header comment. Neither states "or later", so this is
recorded as GPL-3.0-only.

Two obstacles, and they are the only two
----------------------------------------

**MSVC's include capitalisation.** Both translation units open with
``#include <Windows.h>`` and MemSweep additionally includes ``<Tlhelp32.h>``;
mingw-w64 ships those headers lowercase, so a cross-build stops at the first
line of each file:

    PhantomDllHollower.cpp:7:10: fatal error: Windows.h: No such file or
    directory

This is solved by putting a directory on the include path that holds two
forwarding headers - a ``Windows.h`` whose whole content is
``#include <windows.h>``, and a ``Tlhelp32.h`` likewise. The names differ from
the real headers on a case-sensitive filesystem, so there is no recursion, and
the compiler ends up reading mingw-w64's own header. It is an added ``-I``
directory and not a source patch: no file in the fetched tree is touched,
which is the line this corpus does not cross. ``callobfuscator.py`` records
the same include-case problem in d35ha/CallObfuscator and says "correct the
include case", which would have been a patch; this is the way round it that
is not.

**``wmain`` needs ``-municode``.** MSVC picks ``wmainCRTStartup`` when a
translation unit defines ``wmain``; mingw-w64 does not, and links the ANSI
startup object, which then cannot find an entry point:

    libmingw32.a(lib64_libmingw32_a-crtexewin.o): in function `main':
    crtexewin.c:70: undefined reference to `WinMain'

``-municode`` selects the wide startup and both projects link.

That is the whole list, which is worth stating because this is a Windows-only
MSVC project and the expected obstacles did not appear. The three NT routines
it uses - ``NtCreateSection``, ``NtMapViewOfSection``,
``NtCreateTransaction`` - are declared as the project's own function-pointer
typedefs and resolved with ``GetProcAddress``, so no header has to supply
them and there is nothing for mingw-w64's ``winternl.h`` to collide with;
``OBJECT_ATTRIBUTES`` and ``PUNICODE_STRING`` come from that header and are
present; ``CreateFileTransactedW`` and ``TRANSACTION_ALL_ACCESS`` are in
mingw-w64's ``winbase.h`` and ``ktmtypes.h`` and kernel32 is linked by
default. No SEH, no MSVC-only intrinsic, no ``__declspec`` beyond what GCC
accepts. Neither ``_WIN32_WINNT`` nor ``-fms-extensions`` is needed - unlike
``foliage.py`` and sc4cpp, whose defines exist because their trees supply
structures the SDK also declares.

What is the technique and what is furniture
-------------------------------------------

Say this plainly, because the distinctive part of this project is an API
sequence rather than a distinctive function body.

``HollowDLL`` is the technique, and it is the only function that is. Both
variants are inside it, selected by its ``bTxF`` argument, and it is 428
instructions on x64 and 491 on x86 - by far the largest body in either
artefact. The sequence it performs is what an analyst should key on:
``GetSystemDirectoryW`` and ``FindFirstFileW`` over ``*.dll`` to find a module
that is not already loaded and whose ``.text`` is big enough, then either
``NtCreateTransaction`` -> ``CreateFileTransactedW`` -> zero the data
directories that overlap ``.text`` -> ``WriteFile`` the payload into the
transacted contents -> ``NtCreateSection(SEC_IMAGE)`` ->
``NtMapViewOfSection``, or, for the classic path, ``CreateFileW`` ->
``NtCreateSection(SEC_IMAGE)`` -> ``NtMapViewOfSection`` ->
``VirtualProtect(PAGE_READWRITE)`` -> ``memcpy`` -> ``VirtualProtect`` back.
A body match on ``HollowDLL`` is strong evidence of *this code*; it is not
evidence of the technique, which anyone reimplementing in fifty lines of their
own will produce a body that matches nothing here.

The other three functions in that project are PE-parsing furniture.
``GetContainerSectHdr`` (26/47 instructions) walks the section table for the
one containing an RVA and ``GetPAFromRVA`` (32/57) converts an RVA to a file
offset through it - every PE parser ever written contains both, and a hit on
either is not evidence of this project. ``CheckRelocRange`` (43/45) is the
most interesting of the three because it exists for a phantom-specific
reason - the payload has to land in a range of ``.text`` that carries no
base relocations, or the loader would rewrite it - but what it actually
contains is a generic walk over ``IMAGE_BASE_RELOCATION`` blocks, and it is
45 instructions. ``wmain`` is argument parsing, the three ``GetProcAddress``
calls and a file read.

That distinction is not hypothetical. Mandiant's write-up of PRIVATELOG and
STASHLOG - the CLFS-log-hiding loader pair - cites this repository by name and
describes a loader that opens a transacted handle to ``dbghelp.dll``,
overwrites the transacted contents, creates a ``SEC_IMAGE`` section from that
handle and maps it: the same five-call sequence ``HollowDLL`` performs. It is
also that malware's own code, written independently, so it will not match
``HollowDLL``'s body and this family will not name it. What this artefact is
for is recognising Forrest Orr's PoC and anything built from it; recognising
the technique itself is a job for a rule over the call sequence, and reference
data that pretended otherwise would be worse than none.

``MemSweep.exe`` is the defensive half of the same repository and is recorded
as such: a ``VirtualQueryEx`` enumerator (``QueryProcessMem``), a printer
(``EnumProcessMem``) and a class that tallies region counts per memory type
and protection into a ``std::map`` (``MemoryPermissionRecord::UpdateMap`` and
``::ShowRecords``), driven over one PID or over a ``CreateToolhelp32Snapshot``
walk of all of them. It is the tool the blog post uses to *show* the
difference between a hollowed image and a private allocation. Nothing in it
is offensive and none of it is the technique; what this artefact buys is
naming the scanner binary if it turns up somewhere.

Function counts
---------------

Measured through ``corpus.smdaify`` with the glue filter on, and the four
partitions add up to the report total exactly.

``PhantomDllHollower.exe`` x64, 44 functions:

    5   this project's: HollowDLL 428, wmain 147, CheckRelocRange 43,
        GetPAFromRVA 32, GetContainerSectHdr 26
    34  import thunks of one instruction - 32 unnamed (kernel32 and msvcrt,
        `jmp *__imp_X`) plus operator new[] and operator delete[] into
        libstdc++-6.dll
    5   MinGW runtime the filter did not remove: __tmainCRTStartup 142,
        printf 19, an unnamed ___chkstk_ms 15, _wsetargv 2, __wgetmainargs 1

``PhantomDllHollower.exe`` x86, 16 functions:

    5   this project's: HollowDLL 491, _wmain 165, GetPAFromRVA 57,
        GetContainerSectHdr 47, CheckRelocRange 45
    2   import thunks: operator new[], operator delete[]
    9   MinGW runtime: ___tmainCRTStartup 152, printf 13, __wsetargv 2,
        ___register_frame_info 1, ___deregister_frame_info 1,
        ___wgetmainargs 1, and three unnamed bodies of 29, 15 and 14
        instructions which are a fragment of ___w64_mingwthr_add_key_dtor,
        __chkstk_ms and a fragment of the dtoa lock code

``MemSweep.exe`` x64, 50 functions:

    5   this project's: wmain 397, MemoryPermissionRecord::UpdateMap 267,
        ::ShowRecords 140, EnumProcessMem 106, QueryProcessMem 52
    7   libstdc++ template instantiations compiled into the image from the
        headers: four std::_Rb_tree bodies (57, 84, 57, 120), two
        _M_emplace_hint_unique (138, 58) and _List_base::_M_clear (18)
    33  import thunks of one instruction - 20 unnamed, 10 named into
        libstdc++-6.dll and libgcc (operator new, operator delete,
        std::_Rb_tree_insert_and_rebalance, std::__throw_out_of_range,
        std::_Rb_tree_increment twice, std::_Rb_tree_decrement,
        std::__detail::_List_node_base::_M_hook, __gxx_personality_seh0,
        _Unwind_Resume) and 3 into kernel32 (Process32FirstW,
        Process32NextW, CreateToolhelp32Snapshot)
    5   MinGW runtime: __tmainCRTStartup 142, printf 19, an unnamed
        ___chkstk_ms 15, _wsetargv 2, __wgetmainargs 1

``MemSweep.exe`` x86, 42 functions:

    13  this project's: _wmain 439, ::UpdateMap 295, ::ShowRecords 134,
        EnumProcessMem 105, QueryProcessMem 56, three named `.cold` clones
        (5, 4, 4) and five unnamed fragments SMDA splits out of those cold
        regions and out of the two enumerators (16, 14, 3, 2, 2)
    7   libstdc++ template instantiations: the same seven as x64, at 53, 76,
        53, 130, 146, 59 and 19 instructions
    13  import thunks of one instruction: the same 10 into libstdc++-6.dll
        and libgcc, and 3 into kernel32
    9   MinGW runtime: ___tmainCRTStartup 152, printf 13, __wsetargv 2,
        ___register_frame_info 1, ___deregister_frame_info 1,
        ___wgetmainargs 1, and three unnamed bodies of 29, 15 and 14 in the
        same places the hollower's x86 artefact has them

A fifth bucket would be vendored third-party code and it is zero in all four:
there is none in the tree.

``min_functions`` is deliberately not set. All four artefacts clear
``config.MIN_USEFUL_FUNCTIONS`` on their own, and the field is for a project
that genuinely contains fewer functions than the floor - not for restating a
count that a docstring can state. The project's own totals are 5 functions in
the hollower and 7 in MemSweep (of which the constructor and the empty
destructor are defined in-class, so they are inline and ``-O2`` emits neither).

``printf``, and a gap it exposes
--------------------------------

``printf`` survives the glue filter in all four artefacts, and it should not.
``corpus.baseline`` measures it - ``crt_glue("mingw_x64")["printf"]`` contains
this exact PicHash - but ``is_glue`` matches on the symbol name as well, and
the baseline probes are C while these are C++. mingw-w64's ``stdio.h``
defines ``printf`` as an inline wrapper compiled from each translation unit
that calls it, and in a C++ translation unit g++ emits it as
``_Z6printfPKcz``, which SMDA demangles to ``printf(char const*, ...)``. Same
code, same PicHash, different name, so the lookup misses.

Left here as a measurement rather than worked around: it is one function per
artefact, the fix belongs in ``baseline.py`` next to the ``_PROBE_STDIO``
round that `obfuscator4g3nt47.py` describes, and it affects every C++ MinGW
family in this corpus and not just this one. Nothing about it is specific to
this project, and papering over it with ``-D__USE_MINGW_ANSI_STDIO=0`` - which
does remove the body, by turning ``printf`` into an msvcrt import - would have
been a build flag chosen to hide a filter gap.

How this differs from what upstream builds
------------------------------------------

Upstream is MSVC v142, ``/O2 /GL /MT``. Three differences matter:

* ``/MT`` links the MSVC C runtime statically, which under this pipeline
  would put all of it into the sample under this family's name - the effect
  ``callobfuscator.py`` records for VX-API, 1947 of 4219 functions. The MinGW
  build imports msvcrt instead, so what is left of the runtime here is the
  five to nine startup and helper functions listed above.
* ``/GL`` has nothing to do in either project: whole-program optimisation
  works across translation units and each project is a single one. So the
  function granularity of these artefacts is not an artefact of dropping it.
  The three PE helpers have external linkage, which is what keeps them as
  separate bodies under any non-LTO compiler; ``-flto`` is deliberately not
  passed, for the reason ``foliage.py`` records after the fact - it inlined
  the one function that was the technique.
* MemSweep's ``std::list`` and ``std::map`` instantiations are libstdc++'s
  here and would be Microsoft's STL in an MSVC build: different code, so the
  seven instantiated bodies above are the only part of either artefact that
  an MSVC-built MemSweep would not match at all. The hollower's five
  functions use no standard library container and are the same source either
  way.

An MSVC artefact is worth adding through
``.github/workflows/windows-reference-data.yml`` later, with ``/MT`` replaced
by ``/MD`` the way ``callobfuscator.py`` does it. It is not needed to record
the family, so it is not in this recipe.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Two forwarding headers in a directory of their own, put on the include path
# by the two compile steps below. See the docstring: the sources spell
# <Windows.h> and <Tlhelp32.h> with MSVC's capitalisation and mingw-w64 ships
# them lowercase. The shim is written into the build tree rather than into the
# upstream files, the same way callobfuscator.py writes its props file, so the
# fetched source stays byte-identical to what upstream published.
_SHIM = ('mkdir -p corpus-case && '
         'printf "#include <windows.h>\\n" > corpus-case/Windows.h && '
         'printf "#include <tlhelp32.h>\\n" > corpus-case/Tlhelp32.h')

# One compile-and-link per project, which is all either of them is.
#
# -municode selects wmainCRTStartup; without it the link fails on an
# undefined WinMain, because MSVC infers the wide entry point from the
# presence of wmain and mingw-w64 does not.
#
# -O2 is this corpus's default and matches upstream's /O2. Nothing is passed
# to make the runtime static: mingw's g++ links libstdc++ and libgcc
# dynamically by default here, which is what the README asks for - measured,
# operator new and _Unwind_Resume come out as one-instruction import thunks
# rather than bodies, so none of libstdc++ is attributed to this family.
_HOLLOWER = ("{cxx} -O2 -municode -Icorpus-case -o PhantomDllHollower.exe "
             "PhantomDllHollower/PhantomDllHollower.cpp")

_MEMSWEEP = ("{cxx} -O2 -municode -Icorpus-case -o MemSweep.exe "
             "MemSweep/MemSweep.cpp")

_FLAGS = ("-O2 -municode, each project compiled and linked as the single "
          "translation unit it is, with -Icorpus-case added: that directory "
          "holds two generated forwarding headers, Windows.h and "
          "Tlhelp32.h, each a one-line #include of mingw-w64's lowercase "
          "spelling, because the sources use MSVC's capitalisation and a "
          "case-sensitive cross-build cannot resolve it. No upstream file is "
          "modified. -municode is what makes wmain the entry point; without "
          "it the link fails on an undefined WinMain. Upstream's own build is "
          "MSVC v142, Release, /O2 /GL /MT")


_NOTES = (
    "Forrest Orr's proof of concept for phantom DLL hollowing, the variant "
    "that backs injected code with a transacted section so the region reads "
    "as a clean MEM_IMAGE mapping of a real system DLL rather than as private "
    "RW memory. Two translation units are the whole repository - "
    "PhantomDllHollower.cpp (365 lines) and MemSweep.cpp (295) - with no "
    "project headers, no submodules, no vendored third-party code and nothing "
    "statically linked, so everything in these artefacts that is not compiler "
    "runtime is this project's. GPL-3.0-only: LICENSE is the verbatim GPLv3 "
    "text and both files carry a 'Licensed under GNU GPLv3' header. "
    "Be precise about what is matchable. HollowDLL is the technique and is "
    "the only function that is: 428 instructions on x64, 491 on x86, with "
    "both the classic and the phantom path inside it selected by a bool "
    "argument. What identifies the technique is the API sequence it performs "
    "- NtCreateTransaction, CreateFileTransactedW, WriteFile into the "
    "transacted contents, NtCreateSection with SEC_IMAGE, NtMapViewOfSection, "
    "against the classic path's NtCreateSection/NtMapViewOfSection/"
    "VirtualProtect/memcpy/VirtualProtect - not this body, so a match here is "
    "evidence of this code and not of the technique, which a reimplementation "
    "will not match at all - Mandiant's PRIVATELOG loader cites this "
    "repository and performs that same five-call sequence in its own code, "
    "and this family will not name it. The other three functions are "
    "PE-parsing "
    "furniture: GetContainerSectHdr and GetPAFromRVA are the section walk and "
    "RVA-to-file-offset conversion every PE parser contains, and a hit on "
    "either is not evidence of this project; CheckRelocRange exists for a "
    "phantom-specific reason - the payload must land in a relocation-free "
    "range of .text - but is 45 instructions of generic "
    "IMAGE_BASE_RELOCATION walking. MemSweep.exe is the repository's "
    "defensive half, a VirtualQueryEx enumerator and a per-type/per-"
    "protection tally, and is recorded to name the scanner rather than any "
    "technique. Two command-line settings make this tree cross-build and "
    "neither patches it: an -I directory holding forwarding Windows.h and "
    "Tlhelp32.h headers, because the sources use MSVC's capitalisation and "
    "mingw-w64 ships those lowercase ('fatal error: Windows.h: No such file "
    "or directory'), and -municode, without which the link fails on an "
    "undefined WinMain because mingw-w64 does not infer the wide entry point "
    "from wmain. Nothing else was needed - the three Nt routines are the "
    "project's own typedefs resolved by GetProcAddress, so no NT header "
    "collides, and CreateFileTransactedW and TRANSACTION_ALL_ACCESS are both "
    "present in mingw-w64. Function partitions, which add up exactly: the "
    "hollower is 5 own functions of 44 on x64 (34 one-instruction import "
    "thunks, 5 MinGW runtime) and 5 of 16 on x86 (2 thunks, 9 runtime); "
    "MemSweep is 5 own of 50 on x64 and 13 of 42 on x86, plus 7 libstdc++ "
    "std::_Rb_tree and std::list instantiations compiled in from the headers "
    "in each, the rest thunks and MinGW runtime. printf survives the glue "
    "filter in all four artefacts and that is a filter gap rather than this "
    "project's code: the baseline has its PicHash under the name 'printf', "
    "but g++ emits mingw-w64's inline stdio wrapper as _Z6printfPKcz from a "
    "C++ translation unit, so the name-keyed lookup misses it. Upstream "
    "builds MSVC v142 /O2 /GL /MT; /GL has nothing to do here because each "
    "project is one translation unit, and /MT would have put the whole static "
    "MSVC runtime into the sample under this family's name."
)


RECIPES = {
    # No tags in the repository, so pinned by full commit and versioned by its
    # date, the convention MemoryModule_2019-02-24 and Foliage_2021-03-14
    # already use here. HEAD is 57c6aa2056163e6ab31cd5f151a284c52d7722a1,
    # 2020-07-17, which only deleted a saved HTML copy of the blog post; the
    # last commit to touch either source file is f4f2033, 2020-03-13, so the
    # code recorded here is that of the earlier commit and the pin names the
    # repository as published.
    "PhantomDllHollower_2020-07-17": Recipe(
        family="PhantomDllHollower",
        version="2020-07-17",
        upstream="https://github.com/forrest-orr/phantom-dll-hollower-poc",
        license="GPL-3.0-only (Copyright (c) 2019 Forrest Orr)",
        source=Source(
            git_url="https://github.com/forrest-orr/phantom-dll-hollower-poc.git",
            git_ref="57c6aa2056163e6ab31cd5f151a284c52d7722a1"),
        build=[BuildStep(_SHIM), BuildStep(_HOLLOWER), BuildStep(_MEMSWEEP)],
        artifacts=[
            # is_library stays true, as it is for every executable in this
            # corpus - see the note in obfuscator4g3nt47.py: validate refuses
            # a reference sample without it, and it means "this is reference
            # material" rather than "this is a .dll".
            Artifact(path="PhantomDllHollower.exe",
                     component="PhantomDllHollower.exe"),
            Artifact(path="MemSweep.exe", component="MemSweep.exe"),
        ],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags=_FLAGS,
        notes=_NOTES,
    ),
}
