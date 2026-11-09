"""Boost - the compiled libraries, one DLL per library (mcrit-data issue #10).

Most of Boost is headers, and header code reaches a sample as template
instantiations compiled into the consumer under the consumer's own flags,
which no reference build can capture. What can be captured is the part Boost
itself compiles and ships: the libraries under ``libs/*/build`` that produce a
binary. That is what this recipe covers, and it is the whole of what "Boost
coverage" can mean here.

Every library is its own DLL rather than one image holding all of them, which
differs from the abseil and cryptopp recipes and is deliberate. Real software
links individual ``boost_filesystem`` / ``boost_regex`` / ``boost_thread``
binaries, so per-library artefacts are the shape an analyst meets, and the
component name then says which library a match landed in. The one-big-DLL
trick those recipes use is also not available: ``boost_prg_exec_monitor`` and
``boost_test_exec_monitor`` both define a program entry point and would
collide on the first link.

``link=shared runtime-link=shared`` is what keeps foreign code out. Each DLL
imports ``libstdc++-6.dll`` and ``libgcc_s_seh-1.dll`` rather than linking
them, so no standard-library body is attributed to Boost - the mistake that
would otherwise add roughly 13500 libstdc++ and libgcc functions per artefact,
as the protobuf, abseil and GpuDecryptShellcode recipes record. It keeps the
inter-library dependencies honest too: ``boost_filesystem`` imports from
``boost_atomic`` instead of swallowing it, so each artefact holds one
library's code and a match names the right one.

What is not built, and why - in each case because building it would record
something other than Boost:

  * ``python`` needs a Python development install for the target, and what it
    produces is glue against one CPython ABI.
  * ``mpi`` and ``graph_parallel`` need an MPI implementation for Windows.
  * ``iostreams`` is built ``NO_ZLIB`` / ``NO_BZIP2`` / ``NO_LZMA`` /
    ``NO_ZSTD``, so the artefact is the streams framework without the four
    codec filters. zlib, bzip2 and liblzma are families of their own here and
    linking them in would duplicate them under the Boost name; the filter
    classes compile to nothing without a backend, the way protobuf's
    ``gzip_stream.cc`` does with zlib off.
  * ``locale`` is built with ICU and iconv off, leaving the Windows API and
    std backends. ICU is not available for mingw, and an ICU-backed build
    would be megabytes of somebody else's Unicode tables.
  * ``stacktrace``'s ``windbg`` and ``windbg_cached`` backends need the
    DbgEng COM headers, which mingw does not carry; b2's own configuration
    check turns them off. The ``basic``, ``dump``, ``noop`` and
    ``from_exception`` backends do build and are here.

Two libraries ship static-only and are wrapped rather than skipped, because
the alternative is losing them entirely:

  * ``exception`` compiles exactly one function,
    ``clone_current_exception_non_intrusive``. One function is worth recording
    - it is a real Boost library with a real body - so the archive goes into a
    DLL with ``--whole-archive``, the way abseil's do.
  * ``test_exec_monitor`` will not link without a ``test_main``, which is its
    documented contract with the test author, so the anchor supplies an empty
    one. Read its artefact knowing that 932 of its 945 text symbols also
    appear in ``boost_unit_test_framework.dll``: what is only here is 13
    bodies, among them ``boost::unit_test::unit_test_main``,
    ``framework::init`` and the ``test_main`` dispatch glue. It is included
    for those 13 and the duplication is stated rather than hidden.

``cxxstd=20`` rather than something lower, because ``cobalt`` requires C++20
and is skipped entirely below it. The standard changes what inline and
template code every other library instantiates, so it is recorded in
``build_flags`` rather than left implicit.

``linkflags=-lws2_32`` exists for ``cobalt`` alone, whose Jamfile does not
name winsock and whose Asio dependency needs it - the link fails on
``__imp_WSACleanup`` without it. An import library contributes nothing for
symbols no object references, and that was checked rather than assumed:
``boost_date_time`` built with and without the flag has a byte-identical
import table, ``KERNEL32.dll`` and ``msvcrt.dll`` both times. So the flag
rescues one library and leaves the other forty-three as they were. It is a
link flag rather than a Jamfile edit because this corpus does not patch
upstream.

Two acceptance thresholds are overridden, both from counts measured across
all 44 artefacts on both architectures rather than from a guess.

``min_functions=1``, because one floor across this recipe is meaningless: it
spans libraries from one function to 1783. The extreme is real and worth
knowing about - **Boost.DateTime's compiled library is a stub.** Its only
named body is ``boost::gregorian::date_time_dummy_exported_function()``, one
instruction long, and the name is upstream's own. The library exists so there
is something to link against; the real Boost.DateTime is headers. Its x64
artefact is that one function plus nine 1-instruction import thunks and one
15-instruction unnamed body, and its x86 artefact keeps 5 functions in total.
It is recorded anyway, but nothing will ever match it: at one instruction the
only named body sits far below the ten-instruction census floor. An analyst
wondering why a date_time hit never appears has the answer here.

``min_named_ratio=0.05``, lowered from the default 0.5 for three x64 artefacts
- date_time at 0.09, stacktrace_dump at 0.27 and stacktrace_noop at 0.44.
That check exists to catch a build that stripped its symbols, and this is not
one: the other 39 x64 artefacts sit at 0.57 or above, every x86 artefact at
0.60 or above, and stacktrace_noop's own eight bodies are all named. What
drags those three down is that they are small, so the unnamed 1-instruction
import thunks MinGW x64 emits in quantity - which the COFF symbol table does
not name, as MinHook's mingw x64 artefacts already show - outnumber the code.
The threshold is lowered rather than switched off, so a genuinely stripped
artefact with no names at all still fails.

``threadapi=win32`` is b2's default for ``target-os=windows`` and is kept:
Boost.Thread then uses the Win32 primitives directly, which is what a Boost
built on Windows by any toolchain does. The compiler is still the
posix-threads variant, for the reason the rest of this corpus uses it - the
win32-threads ``<mutex>`` is unusable, and several of these libraries reach
for it through the standard library rather than through Boost.Thread.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# b2 is built with the host compiler and only ever runs on the host. It is a
# build tool, never an artefact.
#
# B2_DONT_EMBED_MANIFEST is not optional here, and the reason is this corpus
# rather than Boost. toolchain.build_env exports WINDRES pointing at the cross
# resource compiler, for the autotools builds that need it. Boost's
# tools/build/src/engine/build.sh only sets WINDRES itself when the host
# compiler's -dumpmachine says Windows, but it then tests `[ -n "${WINDRES}" ]`
# - which an inherited value satisfies - and compiles res.rc into a PE object
# that it links into the native b2. ld rejects that with "dangerous
# relocation: R_AMD64_IMAGEBASE with __ImageBase undefined" and bootstrap
# fails before any Boost code is compiled. This switch is build.sh's own, it
# skips the manifest for a tool that has no use for one, and it leaves WINDRES
# alone for the libraries that follow.
_BOOTSTRAP_ENV = {"B2_DONT_EMBED_MANIFEST": "1"}
_BOOTSTRAP = "./bootstrap.sh --with-toolset=gcc"

# b2 picks a cross compiler through a named toolset in user-config.jam rather
# than through CC/CXX, so the file is written here instead of the compiler
# being passed on the command line.
_CONFIG = ("printf 'using gcc : mingw : %s : <archiver>%s <ranlib>%s "
           "<rc>%s ;\\n' {cxx}-posix {ar} {ranlib} {windres} > user-config.jam")

_B2 = ("./b2 --user-config=user-config.jam toolset=gcc-mingw "
       "target-os=windows address-model={bitness} architecture=x86 "
       "link=shared runtime-link=shared variant=release threading=multi "
       "cxxstd=20 --layout=system --build-dir=bin.{arch} "
       "--stagedir=stage-{arch} "
       "--without-python --without-mpi --without-graph_parallel "
       "-sNO_ZLIB=1 -sNO_BZIP2=1 -sNO_LZMA=1 -sNO_ZSTD=1 "
       "boost.locale.icu=off boost.locale.iconv=off "
       "linkflags=-lws2_32 -j$(nproc) -d1 stage")

# The anchor for the two static-only archives. test_main is Boost.Test's
# link-time contract with the test author and has to come from outside the
# library; an empty one is the smallest thing that satisfies it.
_ANCHOR = ("printf 'int test_main(int, char**){return 0;}\\n"
           "int anchor(){return 0;}\\n' > anchor.cc")

_WRAP = ("{cxx}-posix -std=c++20 -O2 -shared -o boost_%s.dll anchor.cc "
         "-Wl,--whole-archive stage-{arch}/lib/libboost_%s.a "
         "-Wl,--no-whole-archive -shared-libgcc")

# Every library b2 stages as a DLL, in the order it names them. Spelled out
# rather than globbed because a recipe that globs its own output cannot tell a
# library that stopped building from one that was never there.
_SHARED = [
    "atomic", "charconv", "chrono", "cobalt", "cobalt_io", "container",
    "context", "contract", "coroutine", "date_time", "fiber", "filesystem",
    "graph", "iostreams", "json", "locale", "log", "log_setup",
    "math_c99", "math_c99f", "math_c99l", "math_tr1", "math_tr1f",
    "math_tr1l", "nowide", "prg_exec_monitor", "process", "program_options",
    "random", "regex", "serialization", "stacktrace_basic",
    "stacktrace_dump", "stacktrace_from_exception", "stacktrace_noop",
    "thread", "timer", "type_erasure", "unit_test_framework", "url", "wave",
    "wserialization",
]

# Static-only, wrapped into DLLs by the steps above.
_WRAPPED = ["exception", "test_exec_monitor"]


RECIPES = {
    "boost_1.92.0": Recipe(
        family="boost",
        version="1.92.0",
        upstream="https://www.boost.org/",
        license="BSL-1.0",
        source=Source(
            url="https://archives.boost.io/release/1.92.0/source/"
                "boost_1_92_0.tar.bz2",
            sha256="5c1d40cb8e19adbf740a4ec2da35b3e58f3f5804b1dce44deb53df"
                   "72193cbc6c"),
        build=[
            BuildStep(_BOOTSTRAP, env=_BOOTSTRAP_ENV),
            BuildStep(_CONFIG),
            BuildStep(_B2),
            BuildStep(_ANCHOR),
        ] + [BuildStep(_WRAP % (name, name)) for name in _WRAPPED],
        artifacts=[
            Artifact(path="stage-{arch}/lib/libboost_%s.dll" % name,
                     component="boost_%s.dll" % name)
            for name in _SHARED
        ] + [
            Artifact(path="boost_%s.dll" % name,
                     component="boost_%s.dll" % name)
            for name in _WRAPPED
        ],
        toolchains=["mingw_x86", "mingw_x64"],
        # Both measured across all 44 artefacts on both architectures; see the
        # module docstring for the counts and for why neither is a build
        # accident.
        min_functions=1,
        min_named_ratio=0.05,
        build_flags="-std=c++20 -O3 -finline-functions -Wno-inline -Wall "
                    "-fvisibility=hidden -fvisibility-inlines-hidden "
                    "-DBOOST_ALL_NO_LIB=1 -DNDEBUG plus a per-library "
                    "-DBOOST_<LIB>_DYN_LINK=1 (b2 variant=release, "
                    "link=shared runtime-link=shared, threadapi=win32, "
                    "--layout=system); -O2 for the two-line anchor.cc the "
                    "exception and test_exec_monitor archives are linked "
                    "around",
        notes="The compiled half of Boost, one artefact per library b2 "
              "stages: 14865 functions across the x64 set and 18619 across "
              "the x86 one after compiler runtime is dropped, per library "
              "from 11 (date_time) to 1783 (log_setup). Header-only Boost is "
              "absent by nature: it exists in a "
              "sample only as template code instantiated into the consumer. "
              "date_time is a special case worth knowing: its compiled "
              "library is a stub whose one named body is upstream's own "
              "date_time_dummy_exported_function, one instruction long, so "
              "the artefact exists for completeness and cannot match "
              "anything. "
              "libstdc++ and libgcc are imported rather than linked, so no "
              "standard-library body is filed under this name, and the "
              "libraries import from each other rather than absorbing each "
              "other, so each artefact is one library's code. iostreams "
              "carries no zlib, bzip2, lzma or zstd filter, because those are "
              "families of their own here. locale carries the Windows API and "
              "std backends, not ICU. stacktrace carries the basic, dump, noop "
              "and from_exception backends; the two windbg ones need DbgEng "
              "headers mingw does not have. python, mpi and graph_parallel are "
              "not built. exception and test_exec_monitor ship static-only and "
              "are linked into DLLs with --whole-archive; 932 of "
              "test_exec_monitor's 945 text symbols also appear in "
              "boost_unit_test_framework.dll, so it contributes 13 bodies of "
              "its own. Built with the posix-threads compiler for the reason "
              "the rest of this corpus uses it, though Boost.Thread itself "
              "uses the Win32 API here.",
    ),
}
