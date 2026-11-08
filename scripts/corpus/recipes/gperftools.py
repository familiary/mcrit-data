"""gperftools tcmalloc_minimal - thread-caching malloc (mcrit-data issue #10).

This family was in the "investigated but not built" table, excluded because
"its Windows port targets MSVC; `src/windows/port.h` clashes with mingw's
`nanosleep` linkage and needs a source patch". **That row was stale.** It was
written against a version whose only Windows build was autotools plus the
checked-in Visual Studio projects. Modern gperftools ships a top-level
`CMakeLists.txt` with explicit `if(MINGW OR MSVC)` branches, and the
nanosleep question is settled by a CMake feature probe rather than by a header
clash: configuring the cross-build prints

    -- Looking for nanosleep - not found

and carries on. The MinGW cross-build then completes with **no patch of any
kind**, which is what this recipe does.

Worth having because tcmalloc is one of the allocators that genuinely ends up
statically linked into Windows binaries, so its bodies turn up wearing the
host program's name. 736 functions and 45,720 instructions on x64, 95.2% of
them named, and a symbol ratio of 1.00 over functions of three instructions or
more.

`tcmalloc_minimal` rather than the full `tcmalloc`: the minimal variant is the
one projects actually link, it needs no stack-trace or profiler machinery, and
the heap-profiler half of the full library pulls in libunwind support that
does not cross-build. `--target` names it explicitly so the test and benchmark
executables are never built at all.

Upstream's own CMakeLists ends with

    note: gperftools' cmake support is incomplete and is best-effort only

which is recorded here rather than argued with: it is upstream's warning about
feature coverage, and what this recipe needs from it - one shared library,
cross-compiled, optimised, with symbols - it delivers. Nothing in the tree is
patched and no compiler or linker flag is added; the `-D` options are
upstream's own `option()` switches plus the standard CMake cross-compilation
variables that every other MinGW CMake recipe here passes.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx} "
          "-DCMAKE_RC_COMPILER={windres} "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} "
          "-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON "
          "-DBUILD_TESTING=OFF -Dgperftools_build_benchmark=OFF")

_BUILD = "cmake --build build-{arch} --target tcmalloc_minimal -j$(nproc)"


RECIPES = {
    "gperftools_2.19.2": Recipe(
        family="gperftools",
        version="2.19.2",
        upstream="https://github.com/gperftools/gperftools",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/gperftools/gperftools.git",
                      git_ref="gperftools-2.19.2"),
        build=[BuildStep(_CMAKE), BuildStep(_BUILD)],
        artifacts=[
            Artifact(path="build-{arch}/libtcmalloc_minimal.dll",
                     component="tcmalloc_minimal.dll"),
        ],
        toolchains=["mingw_x86", "mingw_x64"],
        requires=["cmake", "make"],
        build_flags="-O3 -DNDEBUG (CMake Release)",
        notes="tcmalloc_minimal only: the variant projects actually link, and "
              "the one that needs no stack-trace or profiler machinery. Built "
              "from upstream's own CMakeLists with no patch - the "
              "mingw/nanosleep problem that kept this family out of the "
              "corpus was in the autotools path of a much older release, and "
              "CMake settles it with a feature probe. Upstream's CMakeLists "
              "warns that its cmake support is best-effort; it produces the "
              "shared library this recipe asks for.",
    ),
}
