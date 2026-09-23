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

The phnt commit is 4bd2da2537532fe78d49517755dbdb906b80a4b9, 2020-12-22 - the
last commit before nt_wrapper's own 2021-02-02 pin, i.e. the state of those
headers on the day this library was last touched. It was cloned and read rather
than assumed: phnt.h and phnt_windows.h are both at the tree root, phnt.h
defines PHNT_19H1 as 107, and every NT routine and constant the exercisers
reach through nt_wrapper is present in it (NtCreateThreadEx, NtGetNextThread,
NtQueueApcThreadEx, APC_FORCE_THREAD_SIGNAL, NtIsProcessInJob,
NtMakePermanentObject, SystemModuleInformationEx, SystemPoolTagInformation and
the rest). phnt carries its own licence, CC BY 4.0, which is why the licence
field below is not simply Apache-2.0.

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
# that staying true. /EHsc and /D_SCL_SECURE_NO_WARNINGS are upstream's own
# MSVC test settings.
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
_COMPILE = ('cl /nologo /c /Od /MD /Zi /EHsc /bigobj /std:c++20 /permissive- '
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


def _compile(unit):
    return BuildStep("%s || echo NTW-TU-FAILED %s.cpp"
                     % (_COMPILE % unit, unit),
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
# other, so a missing one leaves nothing unresolved, and /FORCE would also make
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
                "4bd2da2537532fe78d49517755dbdb906b80a4b9, which are CC BY "
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
                           git_ref="4bd2da2537532fe78d49517755dbdb906b80a4b9"),
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
                    "/D_SCL_SECURE_NO_WARNINGS; /DEBUG /Brepro "
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
              "on the Process Hacker native API headers (phnt), pinned to the "
              "commit contemporary with this library's own pin and fetched "
              "through extra_sources rather than vcpkg; they are declarations "
              "and contribute no code to the artefact. Upstream's own CMake is "
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
