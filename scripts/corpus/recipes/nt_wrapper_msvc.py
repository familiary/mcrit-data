"""JustasMasiulis/nt_wrapper - a C++20 wrapper over the native NT API.

The second of the WinAPI-obfuscation projects from the lib2smda wishlist, and
the one most likely to be seen in the wild: it wraps NtCreateFile,
NtQuerySystemInformation, NtAllocateVirtualMemory and the rest of ntdll behind
RAII objects and builder chains, and upstream names obfuscated imports and
direct syscalls among its reasons to exist.

Header-only - a CMake INTERFACE library whose only build output is a set of
Catch2 test executables - so nothing of it exists in a binary until a
translation unit uses it. scripts/corpus/exercisers/nt_wrapper/ holds five
translation units that do; the functions that land in the DLL are the
library's own.

Five rather than one, and compiled the way vxapi.py compiles VX-API's sources:
each with allow_failure=True, then link whatever object files were produced.
An exerciser of this size over twenty-seven headers is written without a
compiler in front of it - MSVC does not exist in the container these recipes
come from - and one bad spelling in one translation unit should cost one slice
of coverage, not the whole family. The link step is what decides whether
enough was produced, and MIN_USEFUL_FUNCTIONS is the backstop under that: if
too little compiles the artefact is refused rather than quietly thinned.
Which translation units failed is in the build log, as NTW-TU-FAILED lines and
as the object inventory printed before the link.

That split is safe for this library in particular. Every function nt_wrapper
provides is inline - detail/config.hpp defines NTW_INLINE as __forceinline -
and the only two definitions in the tree that omit it, ntw::sys::load_driver
and ntw::sys::unload_driver, are declared NTW_INLINE in sys/driver.hpp before
sys/impl/driver_loader.inl is included, so they are inline functions too. No
translation unit emits an external definition another one could collide with.
The contrast is winapi_obfuscator_msvc.py, whose header carries two genuinely
non-inline free functions and whose exerciser must therefore stay a single
translation unit.

CMake is not used at all here, and not out of preference. Upstream's
CMakeLists.txt does exactly three things that matter: it sets cxx_std_20, it
does find_path(PHNT_INCLUDE_DIR phnt.h) and puts the result on the include
path, and it adds test/ when BUILD_TESTING is on. The first two are one
compiler flag and one /I each. The third is a trap: test/CMakeLists.txt begins
with add_subdirectory(Catch2). Driving cl and link directly is both shorter and
free of that, and it is what makes the per-translation-unit tolerance above
possible.

The phnt dependency, and why it is not vcpkg. ntw/detail/common.hpp is
"#define PHNT_VERSION PHNT_19H1", "#include <phnt_windows.h>", "#include
<phnt.h>" - Process Hacker's native API headers, which upstream's README says
to install with "vcpkg install phnt". vcpkg is not a pin: it resolves a port to
whatever the registry says today, which is neither reproducible nor recorded.
The headers are fetched through extra_sources instead, at a full commit hash,
so they are pinned and end up in provenance.json like any other dependency.

The phnt commit is df94006275bb26ed739785556c1200496b78b1a2, 2024-08-06
("Sync latest"), and it is NOT the commit contemporary with nt_wrapper's
own pin. That was the first choice - 4bd2da2537532fe78d49517755dbdb906b80a4b9,
2020-12-22, the last commit before nt_wrapper's 2021-02-02 pin - and CI run
35858415869 proved it unusable. All five translation units failed, on both
legs, with the same three errors and no others:

    .../nt_wrapper-...-phnt/ntioapi.h(756): error C2011:
        '_FILE_STAT_INFORMATION': 'struct' type redefinition
    .../Windows Kits/10/include/10.0.26100.0/um/winnt.h(15457): note:
        see declaration of '_FILE_STAT_INFORMATION'

(paths written with forward slashes here; the log has backslashes, and a
backslash in a Python docstring is an escape.)

and the same pair again for _FILE_STAT_LX_INFORMATION and
_FILE_CASE_SENSITIVE_INFORMATION. The runner's Windows SDK has caught up with
phnt: those three structures are private NT types that phnt published years
before the SDK did, and winnt.h now ships them itself.

There is no compile flag that resolves this, and that was checked rather than
assumed. The SDK's own headers were fetched (Microsoft.Windows.SDK.CPP
10.0.26100) and read: all three definitions sit at winnt.h:15088, :15121 and
:15193 with no _WIN32_WINNT or NTDDI_VERSION guard around them at all - the
only enclosing conditional in the file is "#ifndef _WINNT_" at line 18. So
lowering the target version, which is the usual way out of a collision like
this, cannot work: winnt.h defines them whatever NTDDI_VERSION says, and the
2020 phnt defines them unconditionally too.

phnt fixed it on its own side, in 2b70847be7f731126fba453568e2cfbf560614bf
(2024-06-24, "Update to 24H2"): ntioapi.h there wraps all three in
"#if !defined(NTDDI_WIN11_GE) || (NTDDI_VERSION < NTDDI_WIN11_GE)", and
sdkddkver.h in this SDK defines NTDDI_WIN11_GE as 0x0A000010 with
NTDDI_VERSION defaulting to it, so phnt stands down and the SDK's definitions
are used. A corollary worth stating because it is a trap: NTDDI_VERSION must
NOT be lowered now either, or the guard opens and the collision comes back
from the other direction. That guard is intact at the commit pinned above,
which is the one immediately after it.

Why the pin is 2024-08-06 and not 2024-06-24: ntwmi.h. Pinning 2b70847 fixed
ntioapi.h and CI run 35867402146 then failed all five translation units, on
both legs, identically, somewhere else entirely. The first error of every
translation unit, byte for byte the same on x86 and x64:

    .../nt_wrapper-...-phnt/ntwmi.h(482): error C3646: 'ClientContext':
        unknown override specifier
    .../nt_wrapper-...-phnt/ntwmi.h(482): error C4430: missing type specifier
        - int assumed. Note: C++ does not support default-int

This one is worth reading carefully, because its census looks like something
it is not. Forty C4430, thirty C3646, twenty-five "C2369: '__C_ASSERT__':
redefinition; different subscripts", twenty C2118 negative subscript and
twenty C2148 read like a C_ASSERT firing - like phnt asserting a struct layout
that no longer holds against this SDK. It is not that. Every one of those is
downstream of the two errors above.

ntwmi.h:482 is

    ETW_BUFFER_CONTEXT                 ClientContext;      // LoggerId/...

and ETW_BUFFER_CONTEXT is not a phnt type at all: at 2b70847 it appears in
exactly one place in the whole phnt tree, that line. It belongs to the Windows
SDK, shared/evntrace.h:1357. So do the other two names that fail: ntwmi.h:2991
and five more lines spell EVENT_TRACE_HEADER (shared/evntrace.h:955) and
ntwmi.h:5236 spells WNODE_HEADER (shared/wmistr.h:54, which evntrace.h
includes). C3646 "unknown override specifier" is what MSVC says when the thing
before a member name is not a type; C4430 is the same event again. MSVC then
drops the member, so ntwmi.h:507 "C_ASSERT(FIELD_OFFSET(WMI_BUFFER_HEADER,
ClientContext) == 0x28)" is C2039 "is not a member", and the four offsets
after it - State, Offset, BufferFlag, BufferType - each come out four bytes
short of what is asserted, which is what C2118 negative subscript means. The
whole cascade is one missing declaration.

And nothing declares it. phnt_windows.h at 2b70847 includes windows.h,
windowsx.h, ntstatus.h and winioctl.h and nothing else, and windows.h never
reaches evntrace.h: in SDK 10.0.26100 exactly two headers include it, um/tdh.h
and um/evntcons.h, and neither is in windows.h's closure with or without
WIN32_LEAN_AND_MEAN (which phnt_windows.h defines). System Informer, whose
tree phnt is cut from, includes the ETW headers in its own prologue; a
consumer that does what ntw/detail/common.hpp does - phnt_windows.h then
phnt.h, nothing else - does not.

The reason this arrived with the ntioapi fix rather than before it is that
ntwmi.h is new. It does not exist at the 2020-12-22 pin - the tree there has
thirty-four files and ntwmi.h is not one of them - and 2b70847 is the commit
that both adds it and adds "#include <ntwmi.h>" to phnt.h. The ntioapi fix and
the ntwmi regression are the same commit.

phnt fixed this on its own side too, in the very next commit, which is the one
pinned above: df94006 adds "#include <evntrace.h>" to phnt_windows.h (along
with COM_NO_WINDOWS_H and <ole2.h>). common.hpp includes phnt_windows.h before
phnt.h, so by the time ntwmi.h is parsed the three types are declared by the
SDK. With a real ETW_BUFFER_CONTEXT - a two-byte union plus a USHORT LoggerId,
four bytes - the ten offset assertions do hold, and hold on both legs: union1
is eight-aligned by its ULONGLONG bitfield and union2 by ETW_REF_CLOCK's
LARGE_INTEGERs, so ClientContext lands at 0x28, State at 0x2c, Offset at 0x30,
BufferFlag at 0x34, BufferType at 0x36 and sizeof at 0x48 on x86 exactly as on
x64. That is a hand computation from the two struct definitions, not a
compilation.

The bump is 3.5 years of drift, so what it costs was measured rather than
hoped for, and the measurement was redone against df94006. Every Nt*/Rtl*/Zw*
routine and every *Information identifier that nt_wrapper's 64 headers and
inline files and these five exercisers name - 80 identifiers - was extracted
and looked up in both trees: 79 are present at 2b70847 and the same 79 at
df94006, nothing lost and nothing gained between them. (Relative to the 2020
pin the one gained is still NtAllocateVirtualMemoryEx.) The eightieth,
NtDeviceIoControl, is in neither tree and never was: it is a doc-comment
spelling in nt_wrapper's own io/file.hpp:46 and :54, not an ntdll routine.
phnt.h and phnt_windows.h are still both at the tree root, PHNT_19H1 is still
107, and PHNT_MODE still defaults to PHNT_MODE_USER, so the three lines in
ntw/detail/common.hpp that consume phnt still mean what they meant.

Twice now the failure has been a name phnt and the SDK both own, so that class
was swept rather than waited for. All 1604 struct/union/enum tags phnt defines
at df94006 were compared against all 23138 the SDK defines: 74 tags overlap,
but only um/winnt.h among the SDK files holding them is unconditionally in
windows.h's closure - winternl.h, ntdef.h, SubAuth.h, MSChapp.h, NTSecAPI.h,
delayloadhandler.h, relogger.h and NetSh.h are not included by anything this
build reaches. df94006 adds exactly three tags that winnt.h also defines, and
all three are already guarded on the phnt side: _FILE_NOTIFY_INFORMATION
behind "#if !defined(NTDDI_WIN10_RS5) || (NTDDI_VERSION < NTDDI_WIN10_RS5)",
and _SERVERSILO_DIAGNOSTIC_INFORMATION and
_JOBOBJECT_NETWORK_ACCOUNTING_INFORMATION behind the NTDDI_WIN11_GE form
above. sdkddkver.h puts NTDDI_WIN10_RS5 at 0x0A000006 and NTDDI_WIN11_GE at
0x0A000010 and defaults NTDDI_VERSION to the latter, so all three guards are
false and the SDK wins - the same mechanism as the ntioapi fix, and one more
reason NTDDI_VERSION must not be lowered. One further overlap is created by
the new include rather than by phnt: _EVENT_DESCRIPTOR is defined by phnt's
ntwmi.h and by the SDK's shared/evntprov.h, which evntrace.h pulls in. Both
sides wrap it in "#ifndef EVENT_DESCRIPTOR_DEF" and evntrace.h is included
first, so phnt stands down there as well.

What is still not measured, and cannot be from a container with no MSVC: that
the offset arithmetic above is what cl actually computes; that <ole2.h>,
arriving in this consumer for the first time, collides with nothing; and
whether 2024 phnt and 2021 nt_wrapper agree on every struct field the wrapper
touches.

phnt carries its own licence, CC BY 4.0, which is why the licence field below
is not simply Apache-2.0.

Version "2021-02-02", the pinned commit's date, because the project's own
version strings disagree: CMakeLists.txt says "project(nt_wrapper VERSION
3.2)", the README badge says 0.2, and there are no tags at all. A date is the
one label that is true.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# /Od, not the corpus default of /O2, and this is not a close call here.
#
# ntw/detail/config.hpp line 19 is "#define NTW_INLINE __forceinline", and
# NTW_INLINE appears 958 times across 56 of the library's headers. Essentially
# every function in the library is __forceinline. At /O2 cl honours that and
# folds nearly the whole library into its caller: the artefact could come back
# with as few as one to five distinct functions, against
# MIN_USEFUL_FUNCTIONS = 8. At /Od, which implies /Ob0, cl does not honour
# __forceinline and emits each instantiated function separately.
#
# Upstream reached the same conclusion for its own binaries:
# test/CMakeLists.txt sets COMPILE_OPTIONS
# "$<$<CXX_COMPILER_ID:MSVC>:/EHsc;$<$<CONFIG:Release>:/Od>>", forcing /Od even
# in a Release build, which is not something a project does casually.
#
# The honest consequence, repeated in the notes because it goes verbatim into
# provenance.json: this sample describes an unoptimised consumer of
# nt_wrapper. An /O2 consumer has hardly any nt_wrapper functions left to
# match. The alternative was to lower a gate so an /O2 build could pass, which
# this corpus does not do. The real function count lands in the first CI run.
#
# /std:c++20 because target_compile_features(... INTERFACE cxx_std_20) is
# upstream's, and the library uses <span>, concepts-era syntax and class
# template argument deduction throughout. /permissive- is implied by
# /std:c++20 on v143 and is passed explicitly so the mode does not depend on
# that staying true - for four of the five translation units; nt_wrapper_ob.cpp
# gets /permissive instead, for the measured reason set out above _compile.
# /EHsc and /D_SCL_SECURE_NO_WARNINGS are upstream's own MSVC test settings.
#
# The first two CI runs also settled a question this recipe could not answer
# from the container, and settled it the same way both times. Nothing
# compiled, so obj\ was empty, and the link step then reported it as
#
#   LINK : warning LNK4001: no object files specified; libraries used
#   LINK : error LNK2001: unresolved external symbol _DllMainCRTStartup
#   nt_wrapper.dll : fatal error LNK1120: 1 unresolved externals
#
# That is the intended floor doing its job - a build that compiled nothing
# must not be reported as a build - but it is worth recording that the
# unresolved symbol in that case is the CRT entry point and says nothing
# about ntdll. Whether ntdll.lib actually resolves every Nt*/Rtl* routine
# these exercisers reach is still unmeasured: no translation unit has yet
# reached the linker.
#
# /bigobj because at /Od every instantiated NTW_INLINE function becomes its own
# COMDAT with its own debug information; the 65279-section object limit is a
# real ceiling for that shape, as it is for nlohmann_json_msvc.
#
# /MD rather than cl's default: /LD implies /MT, and a static CRT put 1947 of
# VX-API's 4219 functions into that artefact as MSVC C runtime, duplicating
# data/MSVC.
#
# One /Fd for all five compilations, so every translation unit's debug
# information lands in one compiler PDB - and a different file from the
# linker's /PDB:, which is the one SMDA is handed. Pointing both at one path
# would have link.exe write the file it is reading its type information from.
_COMPILE = ('cl /nologo /c /Od /MD /Zi /EHsc /bigobj /std:c++20 %s '
            '/D_SCL_SECURE_NO_WARNINGS /Iinclude /I{phnt} '
            '/Fdnt_wrapper.compiler.pdb /Fo:obj\\ '
            '{repo}/scripts/corpus/exercisers/nt_wrapper/%s.cpp')

# Compiled one at a time rather than with a for-loop over the directory, so
# that a failure names the translation unit that failed. The "|| echo" is what
# puts that name in the log even though cl has already written its diagnostics
# there: a reader scanning a long log for NTW-TU-FAILED finds the summary
# without reading the diagnostics first.
_TRANSLATION_UNITS = (
    "nt_wrapper_core",  # status, result, unicode_string, access, attributes
    "nt_wrapper_ob",    # object, process, thread, token, job, object_info
    "nt_wrapper_io",    # file, registry key, file/pipe/registry options
    "nt_wrapper_vm",    # protection, allocation, the free operations, memory
    "nt_wrapper_sys",   # chrono, se (SID/ACE/ACL/descriptor), sys enumeration
)


# nt_wrapper_ob.cpp, and only it, is compiled /permissive rather than
# /permissive-, and the reason is measured rather than defensive.
#
# The header comment in that exerciser lists four pieces of ntw::ob that are
# broken as published and are therefore never called. Three of them were
# diagnosed anyway in CI run 35858415869, with the translation unit never
# naming them:
#
#   ...\ntw\ob\impl/thread.inl(255): error C2039: 'get': is not a member
#       of '_OBJECT_ATTRIBUTES'
#   ...\ntw\ob\impl/thread.inl(373): error C2039: 'details': is not a
#       member of 'ntw'
#   ...\ntw\ob\impl/thread.inl(400): error C2039: 'details': is not a
#       member of 'ntw'
#
# That is two-phase lookup, which /permissive- turns on. Both defects are
# non-dependent expressions inside an uninstantiated template body, so a
# conforming compiler must diagnose them at definition time, the moment the
# header is parsed: thread.inl:255 is "OBJECT_ATTRIBUTES attr = attr.get();",
# where OBJECT_ATTRIBUTES is a concrete type and .get() therefore resolvable
# immediately, and :373 and :400 spell a fully qualified "::ntw::details::"
# for what is "::ntw::detail::". Nothing the exerciser does or avoids doing
# can prevent it - the errors arrive with <ntw/ob/thread.hpp>.
#
# The fourth defect confirms the reading rather than merely fitting it. It is
# basic_token<H>::open calling "thread->get()" on a type with no operator->,
# and it was NOT diagnosed, because there the object is a template parameter
# and the expression is dependent, so the check is deferred to an
# instantiation that never happens. Dependent defect silent, non-dependent
# defects fatal, is exactly what two-phase lookup predicts, and MSVC's own
# notes print the enclosing function as "basic_thread<Handle>" with Handle
# unsubstituted - a definition-time diagnosis, not an instantiation.
#
# /permissive restores MSVC's older model, in which a template body is not
# checked until it is instantiated, and these three are never instantiated.
# It is the adjustment blackbone.py already makes for the same class of
# problem: upstream source through a newer compiler, no upstream file
# touched.
#
# Applying it to this one translation unit rather than all five is the point.
# The other four carry no such defect and compile conformantly, and
# /permissive is a weaker mode that could plausibly cost them something; if
# it costs ob.cpp instead, ob.cpp is a unit that does not build today anyway,
# so the change cannot lose anything that is not already lost. This is the
# per-unit tolerance in the module docstring being used for what it is for.
_PERMISSIVE_UNITS = frozenset({"nt_wrapper_ob"})


def _compile(unit):
    conformance = "/permissive" if unit in _PERMISSIVE_UNITS else "/permissive-"
    return BuildStep("%s || echo NTW-TU-FAILED %s.cpp"
                     % (_COMPILE % (conformance, unit), unit),
                     allow_failure=True)


# A DLL, not a .lib: SMDA cannot read a static library. Each translation unit
# has its own extern "C" __declspec(dllexport) entry point, so the image has a
# real export table without a .def file - and losing one translation unit
# costs one export rather than all of them.
#
# obj\*.obj rather than five named objects, because the point of the
# allow_failure compilations above is that some of them may not be there. If
# none of them is, this step fails and the recipe fails with it, which is the
# intended floor: a build that compiled nothing must not be reported as a
# build.
#
# ntdll.lib is what every one of upstream's own tests names in a
# #pragma comment(lib, "ntdll.lib"); the whole library is calls into ntdll, so
# without it the link is a wall of unresolved Nt* externals. There is
# deliberately no /FORCE here: the five translation units do not reference each
# other, so a missing one leaves nothing unresolved - still an argument from
# the sources rather than a measurement, because the first CI run compiled
# none of them and so never reached a link with a partial object set - and
# /FORCE would also make
# link.exe ignore the /INCREMENTAL:NO below.
#
# /Brepro, /OPT:NOREF and /OPT:NOICF for the reasons spelled out in
# nlohmann_msvc.py. /OPT:NOICF matters more than usual here: a library of
# builder methods that each set one flag on one member produces a great many
# instantiations with identical bodies.
#
# /INCREMENTAL:NO because /DEBUG implies /INCREMENTAL and the /OPT:NO* forms
# above do not suppress it - only /OPT:REF, /OPT:ICF and /OPT:ORDER are
# documented to. An incrementally linked image reaches each function through a
# table of one-instruction jump thunks that SMDA recovers as unnamed functions,
# and smdaify.assert_not_incrementally_linked refuses a build with a run of
# more than MAX_INCREMENTAL_THUNK_RUN of them.
_LINK = ('link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO '
         '/OPT:NOREF /OPT:NOICF '
         '/PDB:nt_wrapper.pdb /OUT:nt_wrapper.dll obj\\*.obj ntdll.lib')


RECIPES = {
    "nt_wrapper_2021-02-02_msvc": Recipe(
        family="nt_wrapper",
        version="2021-02-02",
        upstream="https://github.com/JustasMasiulis/nt_wrapper",
        license="Apache-2.0 (full text in LICENSE, per-file \"Copyright 2020 "
                "Justas Masiulis\" headers). Builds against the Process "
                "Hacker native API headers, winsiderss/phnt at "
                "df94006275bb26ed739785556c1200496b78b1a2, which are CC BY "
                "4.0; those are declarations only and contribute no code to "
                "the artefact, but they are a pinned input and are recorded "
                "as one.",
        source=Source(
            git_url="https://github.com/JustasMasiulis/nt_wrapper.git",
            git_ref="34405005ecd949fd75cb586ee0976aa7e3a7ef65"),
        # Not vcpkg. See the module docstring: a vcpkg port resolves to
        # whatever the registry serves on the day, which is neither
        # reproducible nor recorded, and phnt's headers decide what every NT
        # call in this library compiles to.
        extra_sources={
            "phnt": Source(git_url="https://github.com/winsiderss/phnt.git",
                           git_ref="df94006275bb26ed739785556c1200496b78b1a2"),
        },
        build=(
            [BuildStep("md obj", allow_failure=True)]
            + [_compile(unit) for unit in _TRANSLATION_UNITS]
            # The inventory, immediately before the link, so the log says
            # which translation units survived without anyone having to
            # reconstruct it from the diagnostics above. allow_failure because
            # dir over an empty directory exits non-zero, and that case is the
            # link's to report.
            + [BuildStep("dir obj\\*.obj", allow_failure=True),
               BuildStep(_LINK)]
        ),
        artifacts=[Artifact(path="nt_wrapper.dll",
                            component="nt_wrapper.dll",
                            pdb="nt_wrapper.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/Od /MD /Zi /EHsc /bigobj /std:c++20 /permissive- "
                    "/D_SCL_SECURE_NO_WARNINGS, except that the ntw::ob "
                    "translation unit is compiled /permissive because three "
                    "defects in upstream's impl/thread.inl are non-dependent "
                    "expressions in uninstantiated template bodies and a "
                    "conforming two-phase lookup diagnoses them at parse time "
                    "even though nothing calls them; /DEBUG /Brepro "
                    "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF and ntdll.lib at "
                    "link. /Od rather than the corpus default /O2 on purpose: "
                    "detail/config.hpp defines NTW_INLINE as __forceinline and "
                    "uses it 958 times across 56 headers, so at /O2 cl folds "
                    "almost the entire library into its caller and the "
                    "artefact can fall to a handful of functions. Upstream's "
                    "own test/CMakeLists.txt forces /Od even in Release for "
                    "the same reason. This sample therefore describes an "
                    "unoptimised consumer of nt_wrapper.",
        notes="Built from five exerciser translation units, since the library "
              "is header-only and the upstream build emits only Catch2 test "
              "executables; the emitted functions are the library's own and "
              "the exercisers only select which ones, across its header "
              "groups - status/result, unicode_string, access, chrono, ob, io, "
              "vm, info, se and sys. Each translation unit is compiled "
              "separately and tolerated if it fails, and whatever object files "
              "resulted are linked, so a translation unit that does not "
              "compile costs one slice of coverage rather than the family; "
              "the build log names any that failed, and the eight-function "
              "floor is the backstop if too little was produced. Compiled at "
              "/Od: see build_flags for why, and read the sample as reference "
              "for an unoptimised consumer rather than for an /O2 one. Depends "
              "on the Process Hacker native API headers (phnt), fetched "
              "through extra_sources rather than vcpkg and pinned to "
              "df94006275bb26ed739785556c1200496b78b1a2 (2024-08-06); they are "
              "declarations and contribute no code to the artefact. That is "
              "deliberately not the phnt commit contemporary with this "
              "library's 2021 pin: the contemporary one defines "
              "FILE_STAT_INFORMATION, FILE_STAT_LX_INFORMATION and "
              "FILE_CASE_SENSITIVE_INFORMATION unconditionally, the Windows "
              "SDK on the build machine (10.0.26100) now defines all three in "
              "winnt.h with no version guard of any kind, and every "
              "translation unit failed with C2011 type redefinition until the "
              "pin was moved forward to the phnt release that guards them "
              "behind NTDDI_WIN11_GE. That release, 2b70847 (2024-06-24), is "
              "also the one that first adds ntwmi.h and includes it from "
              "phnt.h, and ntwmi.h names three types it does not define - "
              "ETW_BUFFER_CONTEXT, EVENT_TRACE_HEADER and WNODE_HEADER, all "
              "from the SDK's evntrace.h and wmistr.h, which nothing in "
              "windows.h's include closure reaches. Every translation unit "
              "then failed again, with C3646 at ntwmi.h:482 and a long "
              "downstream cascade of C_ASSERT errors that look like a struct "
              "layout mismatch and are not one. The pin is therefore the next "
              "commit, df94006, which adds the missing #include <evntrace.h> "
              "to phnt_windows.h; the module docstring has the full reading. "
              "Upstream's own CMake is "
              "not used, because its test/ subdirectory needs the Catch2 "
              "submodule and everything else it does is one flag and one "
              "include path. Seven pieces of the public API are not exercised "
              "because they do not compile or link as published - "
              "concepts.hpp, thread::open, the process-taking overloads of "
              "thread::first and thread::next, token::open and open_as_self "
              "for threads, the typed device_io_control/fs_control overloads, "
              "result_ref's only value-carrying constructor, and "
              "object::wait_until and object::name, which are declared and "
              "never defined. Those are named in the exercisers with the file "
              "and line; upstream source is not patched. Built against the DLL "
              "runtime, so the MSVC C runtime is imported rather than linked "
              "in and stays attributed to data/MSVC.",
    ),
}
