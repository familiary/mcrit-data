"""libpng built with MSVC, beside the MinGW build of the same tag.

Image-handling code on Windows is MSVC-built, and data/libpng carries only a
MinGW artefact.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

**The whole difficulty of this family is zlib**, and this recipe is shaped
around it. data/libpng's own history is the corpus's canonical cautionary
tale: linking zlib statically put 62 of libpng16.dll's 500 functions into the
libpng family, byte-identical to data/libzlib, so any sample containing plain
zlib matched libpng. The MinGW recipe was fixed by importing zlib from a
staged DLL instead. Two MSVC-specific traps would recreate it:

  * ``projects/vstudio/`` - upstream's own Visual Studio solution - builds
    zlib into the same solution. It is not used here, and should not be.
  * ``find_package(ZLIB REQUIRED)`` on a windows runner would search the
    directories derived from PATH, where Strawberry Perl keeps a ``libz.a``
    that link.exe cannot use and vcpkg may keep a static ``zlib.lib`` that it
    very much can. Either outcome is decided by what the runner image
    happens to carry, which is not acceptable for reference data.

So zlib 1.3.1 is fetched by digest through ``extra_sources`` - the same
version and the same digest the MinGW recipe pins - built with upstream's own
``win32/Makefile.msc``, and libpng is pointed at the resulting *import*
library. ``FindZLIB.cmake`` guards its entire search with
``if(NOT ZLIB_LIBRARY)`` [read, CMake 3.28's module], so naming ZLIB_LIBRARY
on the command line is not a hint that something else can override - it
short-circuits the search altogether.

What was read rather than assumed:
  * zlib 1.3.1's ``win32/Makefile.msc``: ``CFLAGS = -nologo -MD -W3 -O2 -Oy-
    -Zi -Fd"zlib"``, ``LDFLAGS = -nologo -debug -incremental:no -opt:ref``,
    ``SHAREDLIB = zlib1.dll`` linked from ``win32/zlib.def`` with
    ``-implib:zdll.lib``. /MD, /Zi and /debug are upstream's own defaults, so
    the staging step needs no overrides at all.
  * libpng 1.6.50's ``CMakeLists.txt``: under a toolchain whose library
    prefixes are empty - i.e. MSVC - ``PNG_SHARED_OUTPUT_NAME`` is set to
    ``libpng${PNGLIB_ABI_VERSION}``, so the DLL is **libpng16.dll**, the same
    name the MinGW build produces by a different route. The target is
    ``png_shared``; ``VERSION``/``SOVERSION`` do not reach the file name on
    Windows.
  * ``cmake_minimum_required(VERSION 3.14...4.0)``, so CMP0091 is NEW and
    CMake selects the DLL runtime through CMAKE_MSVC_RUNTIME_LIBRARY. The /MD
    this recipe adds to CMAKE_C_FLAGS_RELEASE is a duplicate under that
    policy and the only source of it under an OLD one; either way the build
    is /MD.
  * ``PNG_TARGET_ARCHITECTURE`` is ``CMAKE_SYSTEM_PROCESSOR`` lower-cased,
    and on x86/amd64 ``PNG_INTEL_SSE`` defaults to **on**, which compiles
    ``intel/intel_init.c`` and ``intel/filter_sse2_intrinsics.c`` with
    ``-DPNG_INTEL_SSE_OPT=1``. Under the MinGW cross build
    CMAKE_SYSTEM_PROCESSOR is empty - a configure of this tree with the cross
    compiler prints "Building for target architecture:" and nothing - so the
    committed MinGW artefacts carry **no** SSE2 filter code and this one
    will. The default is kept rather than forced off: a libpng16.dll shipped
    on Windows has those optimisations, so this is the more representative
    build, and the difference is recorded here and in the notes rather than
    papered over.
  * ``find_program(AWK …)`` decides whether ``pnglibconf.h`` is generated
    from the DFA files or copied from ``scripts/pnglibconf.h.prebuilt``; both
    branches configure successfully, so an awk-less runner is not a failure.
    It does mean the generated header could differ slightly from the MinGW
    build's if one runner has awk and the other does not.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_ZLIB_VERSION = "1.3.1"
_ZLIB_SHA256 = "9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23"

# cmake -E rather than tar/move: CMake is already required by this recipe, so
# using it for the unpack costs nothing and avoids depending on which
# cmd.exe builtins and which tar the runner image happens to provide.
_UNPACK_ZLIB = "cmake -E tar xf {zlib_archive}"
_RENAME_ZLIB = "cmake -E rename zlib-%s zlib" % _ZLIB_VERSION

# Upstream's own MSVC makefile, with no overrides: its CFLAGS are already
# -MD -Zi and its LDFLAGS already -debug. The explicit target matters - the
# default "all" would additionally build example.exe and minigzip.exe, which
# nothing here wants. zlib1.dll's rule is what produces zdll.lib.
_BUILD_ZLIB = "nmake -f win32\\Makefile.msc zlib1.dll"

# See xz_msvc.py for why these two variables rather than CMAKE_C_FLAGS /
# CMAKE_SHARED_LINKER_FLAGS: CMake's MSVC Release default carries neither /Zi
# nor /DEBUG, so the artefact would come back with no PDB and no names, and
# overriding the per-configuration variables leaves CMake's own
# initialisation - /machine on the 32-bit leg among it - in place.
_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')

# NMake Makefiles: nmake ships with MSVC itself, the generator is
# single-configuration so the DLL lands in the build root, and the target
# architecture comes from the developer environment the workflow sets up.
#
# The zlib paths are absolute, for the reason the MinGW recipe records: a
# relative one is taken for a make target and the link fails with "No rule to
# make target". {source_root} is this tooling's own placeholder and is
# quoted for the shell by build.py, which is steadier than relying on %CD%.
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release '
          '-DPNG_SHARED=ON -DPNG_STATIC=OFF -DPNG_TESTS=OFF -DPNG_TOOLS=OFF '
          '-DZLIB_INCLUDE_DIR={source_root}/zlib '
          '-DZLIB_LIBRARY={source_root}/zlib/zdll.lib '
          '%s %s' % (_CFLAGS, _LDFLAGS))


RECIPES = {
    "libpng_1.6.50_msvc": Recipe(
        family="libpng",
        version="1.6.50",
        upstream="https://github.com/pnggroup/libpng",
        license="libpng-2.0",
        # The same tag the MinGW recipe pins.
        source=Source(git_url="https://github.com/pnggroup/libpng.git",
                      git_ref="v1.6.50"),
        # zlib is pinned by digest and staged before configure, exactly as in
        # the MinGW recipe - a dependency whose code could end up inside the
        # artefact has to be recorded even when the whole point is that it
        # does not.
        extra_sources={"zlib_archive": Source(
            url="https://zlib.net/fossils/zlib-%s.tar.gz" % _ZLIB_VERSION,
            sha256=_ZLIB_SHA256)},
        build=[
            BuildStep(_UNPACK_ZLIB),
            BuildStep(_RENAME_ZLIB),
            BuildStep(_BUILD_ZLIB, cwd="zlib"),
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} --target png_shared"),
            # Cheap insurance, as in xz_msvc.py: build.py reports a missing
            # artefact by the path it expected and nothing else, and this
            # puts the names the build actually wrote into the log the
            # workflow prints on failure.
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/libpng16.dll",
                            component="libpng16.dll",
                            pdb="build-{arch}/libpng16.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release, /Zi added), "
                    "PNG_INTEL_SSE on (upstream's default on x86/amd64); "
                    "/DEBUG /Brepro /OPT:NOREF /OPT:NOICF at link",
        notes="Imports zlib %s from an MSVC-built zdll.lib rather than "
              "linking it statically, so this sample contains libpng code "
              "only - the MinGW artefact of this family was measured "
              "carrying 62 functions of zlib before the same fix was applied "
              "there. Upstream's projects/vstudio solution is deliberately "
              "not used: it compiles zlib into the same image. The staged "
              "zlib1.dll is a build input and is not itself recorded as an "
              "artefact. Built against the DLL runtime, so the MSVC C "
              "runtime is imported rather than linked in and stays "
              "attributed to data/MSVC. Two differences from the MinGW "
              "sibling beyond the compiler: this build has libpng's Intel "
              "SSE2 filters, which upstream enables by default on x86 and "
              "amd64 and which the cross build never reached because "
              "CMAKE_SYSTEM_PROCESSOR is empty there; and it is /O2 /Ob2 "
              "from CMake's MSVC Release where the MinGW one is -O3."
              % _ZLIB_VERSION,
    ),
}
