"""RE2 - Google's regular expression engine.

The two versions here bracket the largest code-level split in this part of
the corpus: 2022-06-01 is the last release before RE2 took a dependency on
Abseil, so it is entirely standalone, while current RE2 is built on Abseil
throughout. They are effectively different code bases rather than adjacent
versions, and a matcher that only knows one of them recognises very little
of the other.

2022-06-01 is not built through RE2's CMake. CMake produces a static archive,
which SMDA cannot read, and compiling the library sources straight into a DLL
is both shorter and exactly what is wanted, which is every function present
rather than only those an anchor happens to reference. The source list is an
allow-list, not a filter: re2/*.cc plus the two util files the library needs,
util/rune.cc and util/strutil.cc. Nothing is excluded by name. re2/testing,
re2/fuzzing and the rest of util/ - including util/pcre.cc, a test helper
that would want PCRE - are simply never named, so they never reach the
compiler.

2025-11-05 cannot be built that way, because what it needs from Abseil is no
longer only headers. Compiling it against Abseil's include path alone leaves
hundreds of absl:: calls unresolved, and the flag that would have waved them
through does not exist here: ld ignores --unresolved-symbols on PE targets
(so does --warn-unresolved-symbols), and the link fails whatever is passed.
So Abseil is built first as shared libraries and installed into a prefix
inside the source tree, and RE2 is then built through its own CMake against
that prefix. RE2's CMakeLists does find_package(absl REQUIRED) when absl::base
is not already a target, and with BUILD_SHARED_LIBS it produces libre2.dll,
which imports from the Abseil DLLs instead of carrying their code. That is the
point of the arrangement: Abseil is a family of its own here, and linking its
archives in would file tens of thousands of Abseil functions under the re2
name. A shared build also keeps the coverage the direct compile gave, because
every object goes into the DLL rather than only what an anchor references.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_SOURCES = "re2/*.cc util/rune.cc util/strutil.cc"

_COMMON = ("{cxx}-posix -std=c++17 -O2 -I. %s -shared -o re2.dll "
           + _SOURCES + " %s -lwinpthread -shared-libgcc")

_BUILD_STANDALONE = _COMMON % ("", "")

# Cross settings every CMake configure below shares, spelled as the abseil
# recipe spells them.
_CROSS = ("-DCMAKE_SYSTEM_NAME=Windows -DCMAKE_C_COMPILER={cc} "
          "-DCMAKE_CXX_COMPILER={cxx}-posix -DCMAKE_FIND_ROOT_PATH=/usr/{host} "
          "-DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17")

# Abseil as DLLs, installed into a prefix inside the source tree so nothing
# outside the build is written and so the next architecture cannot pick up the
# previous one's libraries. CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS is what makes a
# MinGW DLL of it usable at all: Abseil marks nothing dllexport, so without it
# there would be no import libraries for RE2 to link against.
_ABSL_CONFIGURE = ("cmake -S {absl} -B absl-build-{arch} " + _CROSS + " "
                   "-DBUILD_TESTING=OFF -DABSL_PROPAGATE_CXX_STD=ON "
                   "-DABSL_ENABLE_INSTALL=ON -DBUILD_SHARED_LIBS=ON "
                   "-DCMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON "
                   "-DCMAKE_INSTALL_PREFIX={source_root}/absl-prefix-{arch}")

_ABSL_INSTALL = "cmake --build absl-build-{arch} -j$(nproc) --target install"

# CMAKE_PREFIX_PATH is how RE2's find_package(absl REQUIRED) finds the prefix
# just installed. RE2_INSTALL is off because nothing is installed from this
# tree, and -shared-libgcc is stated rather than relied on, because
# -static-libstdc++ would add roughly 13500 libstdc++ and libgcc functions to
# this sample and attribute them to re2.
_RE2_CONFIGURE = ("cmake -S . -B build-{arch} " + _CROSS + " "
                  "-DBUILD_SHARED_LIBS=ON -DCMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON "
                  "-DRE2_INSTALL=OFF -DCMAKE_SHARED_LINKER_FLAGS=-shared-libgcc "
                  "-DCMAKE_PREFIX_PATH={source_root}/absl-prefix-{arch}")


RECIPES = {
    # Last standalone release, before the Abseil dependency.
    "re2_2022-06-01": Recipe(
        family="re2",
        version="2022-06-01",
        upstream="https://github.com/google/re2",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/google/re2.git",
                      git_ref="2022-06-01"),
        build=[BuildStep(_BUILD_STANDALONE)],
        artifacts=[Artifact(path="re2.dll", component="re2.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 -std=c++17",
        notes="Standalone; no Abseil. Built with the posix-threads compiler, "
              "because the win32-threads <mutex> is unusable.",
    ),
    # Current, and Abseil-based throughout.
    "re2_2025-11-05": Recipe(
        family="re2",
        version="2025-11-05",
        upstream="https://github.com/google/re2",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/google/re2.git",
                      git_ref="2025-11-05"),
        extra_sources={
            # The release this RE2 tag's own MODULE.bazel names, which is the
            # pairing upstream builds and tests. It matters more than it did
            # when Abseil only supplied headers here: it now decides both the
            # inline code RE2 instantiates and the DLLs it imports from.
            "absl": Source(git_url="https://github.com/abseil/abseil-cpp.git",
                           git_ref="20250512.1"),
        },
        build=[
            BuildStep(_ABSL_CONFIGURE),
            BuildStep(_ABSL_INSTALL),
            BuildStep(_RE2_CONFIGURE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="build-{arch}/libre2.dll",
                            component="re2.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        # RE2 sets no CMAKE_CXX_FLAGS_RELEASE of its own, so Release is
        # CMake's GNU default of -O3 -DNDEBUG rather than the -O2 the
        # standalone build above uses. The defines are what RE2's CMakeLists
        # adds for every WIN32 target.
        build_flags="-O3 -DNDEBUG -std=c++17 -DUNICODE -D_UNICODE -DSTRICT "
                    "-DNOMINMAX -D_CRT_SECURE_NO_WARNINGS "
                    "-D_SCL_SECURE_NO_WARNINGS (CMake Release, shared build)",
        notes="Upstream's own libre2 DLL. Abseil is built alongside as DLLs "
              "and only imported, so no Abseil object code is attributed to "
              "re2; what is present is the Abseil inline and template code "
              "RE2 instantiates, as it would be in any RE2 binary. Built with "
              "the posix-threads compiler.",
    ),
}
