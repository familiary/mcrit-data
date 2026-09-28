"""gperftools - tcmalloc, issue #10's "tcmalloc" entry.

Issue #10 asks for tcmalloc. Two projects answer to that name and only one of
them can produce a PE: ``google/tcmalloc`` is Bazel-only and Linux-only, so
what the issue is pointing at is gperftools, whose ``tcmalloc_minimal`` is the
allocator that has been embedded in Windows software for twenty years.

``scripts/corpus/README.md`` recorded this as investigated and not built,
because "its Windows port targets MSVC; ``src/windows/port.h`` clashes with
mingw's ``nanosleep`` and needs a source patch". **That is no longer true, and
the patch was never necessary.** The clash is a wrong configure result rather
than a source incompatibility. ``CMakeLists.txt`` probes with

    check_symbol_exists("nanosleep" "time.h" HAVE_DECL_NANOSLEEP)

and mingw-w64 declares ``nanosleep`` in ``pthread_time.h``, not ``time.h``, so
the probe fails, the generated ``config.h`` says ``#define
HAVE_DECL_NANOSLEEP 0``, and ``port.h`` then supplies its own inline
``nanosleep`` that collides with the real declaration - "conflicting
declaration of 'int nanosleep(const timespec*, timespec*)' with 'C' linkage".
``check_symbol_exists`` skips its probe when the result variable is already
in the cache, so passing ``-DHAVE_DECL_NANOSLEEP=1`` is enough: ``config.h``
comes out with 1, ``port.h`` leaves the declaration alone and the build
completes. No upstream file is touched.

Only ``tcmalloc_minimal`` is built, because that is all gperftools offers on
Windows: the heap checker, the heap profiler and the CPU profiler are Unix-only
and the build does not produce them for this target. ``tcmalloc_minimal`` is
also the variant that gets embedded - it is the allocator without the
profiling machinery.

``CMAKE_CXX_STANDARD_LIBRARIES=-lsynchronization`` is the second setting, and
it is an ordering fix rather than a missing library. gperftools already asks
for the library - ``target_link_libraries(common PUBLIC psapi synchronization
shlwapi)`` - but what references ``WaitOnAddress``, ``WakeByAddressAll`` and
``WakeByAddressSingle`` is libwinpthread, and where CMake places ``-lpthread``
relative to ``-lsynchronization`` is not fixed. With
``CFLAGS``/``CXXFLAGS`` set in the environment, as this pipeline sets them,
CMake emits ``-lpsapi -lsynchronization -lshlwapi -lpthread`` instead of
``-lpthread -lpsapi -lsynchronization -lshlwapi``, and ld resolves archives
left to right, so the undefined references libwinpthread introduces have
nothing after them to satisfy. ``CMAKE_CXX_STANDARD_LIBRARIES`` is appended
last on the link line, which resolves them wherever ``-lpthread`` lands. This
was caught because a hand build linked and the pipeline build did not, from
nothing but the order of those four flags.

Built shared, so libstdc++ and libgcc are imported rather than linked and no
standard-library body is attributed here; the DLL imports ``libstdc++-6.dll``
and ``libgcc_s_seh-1.dll`` and nothing else beyond kernel32, msvcrt and psapi.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# HAVE_DECL_NANOSLEEP is the whole trick; see the module docstring. The
# benchmark and the tests are off because they are host programs, not the
# allocator.
_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_SYSTEM_PROCESSOR={platform} "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx}-posix "
          "-DCMAKE_RC_COMPILER={windres} "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
          "-DBUILD_SHARED_LIBS=ON -DHAVE_DECL_NANOSLEEP=1 "
          "-DCMAKE_CXX_STANDARD_LIBRARIES=-lsynchronization "
          "-Dgperftools_build_benchmark=OFF -DBUILD_TESTING=OFF")


RECIPES = {
    "gperftools_2.18.1": Recipe(
        family="gperftools",
        version="2.18.1",
        upstream="https://github.com/gperftools/gperftools",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/gperftools/gperftools.git",
                      git_ref="gperftools-2.18.1"),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="build-{arch}/libtcmalloc_minimal.dll",
                            component="tcmalloc_minimal.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 -DNDEBUG (CMake Release, GNU default; gperftools sets "
                    "no CMAKE_CXX_FLAGS_RELEASE of its own), shared build, "
                    "-DHAVE_DECL_NANOSLEEP=1 to skip a configure probe that "
                    "looks for nanosleep in the wrong header on mingw, and "
                    "-lsynchronization appended last so libwinpthread's "
                    "WaitOnAddress references resolve whatever order CMake "
                    "emits -lpthread in",
        notes="tcmalloc_minimal, which is the only gperftools library that "
              "builds for Windows - the heap checker, heap profiler and CPU "
              "profiler are Unix-only - and also the variant that actually "
              "gets embedded, being the allocator without the profiling "
              "machinery. issue #10's 'tcmalloc' means this project rather "
              "than google/tcmalloc, which is Bazel-only and Linux-only and "
              "cannot produce a PE at all. Built shared, so libstdc++ and "
              "libgcc are imported rather than linked and no standard-library "
              "body is filed under this name. The mingw obstacle recorded "
              "earlier in scripts/corpus/README.md was a wrong configure "
              "result, not a source incompatibility: CMake probes for "
              "nanosleep in time.h, mingw-w64 declares it in pthread_time.h, "
              "and the failed probe made port.h define a colliding inline. "
              "Pre-seeding the cache variable skips the probe and no source "
              "file is modified.",
    ),
}
