"""Abseil, which also covers CCTZ (mcrit-data issue #10 lists both).

CCTZ is vendored inside Abseil as absl/time/internal/cctz, and its symbols
land in this artefact, so processing google/cctz separately would duplicate
them. Only the pre-Abseil standalone CCTZ would be distinct, and that is not
what issue #10 is pointing at.

Abseil builds as a pile of static archives, and SMDA cannot read those, so
they are linked into one DLL with --whole-archive to force every object in
rather than only what an anchor happens to reference.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx}-posix "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
          "-DCMAKE_CXX_STANDARD=17 -DBUILD_TESTING=OFF "
          "-DABSL_PROPAGATE_CXX_STD=ON")

# -shared-libgcc is deliberate: -static-libstdc++ would add roughly 13500
# libstdc++ and libgcc functions to this sample and attribute them to Abseil.
_LINK = ("echo 'int anchor(){return 0;}' > anchor.cc && "
         "{cxx}-posix -std=c++17 -O2 -shared -o abseil.dll anchor.cc "
         "-Wl,--whole-archive $(find build-{arch} -name 'libabsl_*.a' | tr '\\n' ' ') "
         "-Wl,--no-whole-archive -Wl,--start-group "
         "$(find build-{arch} -name 'libabsl_*.a' | tr '\\n' ' ') "
         "-Wl,--end-group -lbcrypt -ladvapi32 -ldbghelp -lwinpthread "
         "-shared-libgcc")


def _abseil(version, git_ref):
    return Recipe(
        family="abseil",
        version=version,
        upstream="https://github.com/abseil/abseil-cpp",
        license="Apache-2.0",
        source=Source(git_url="https://github.com/abseil/abseil-cpp.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
            BuildStep(_LINK),
        ],
        artifacts=[Artifact(path="abseil.dll", component="abseil.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        # Two flag sets, and the one that matters is the first: every
        # libabsl_*.a object - all the code that ends up in the sample - comes
        # from the CMake Release build, which is CMake's GNU default of
        # -O3 -DNDEBUG because Abseil sets no CMAKE_CXX_FLAGS_RELEASE of its
        # own. The -O2 line applies only to the three-line anchor.cc stub the
        # archives are linked around.
        build_flags="-O3 -DNDEBUG -std=c++17 (CMake Release, all Abseil code); "
                    "-O2 for the anchor.cc link stub only",
        notes="Includes the vendored CCTZ, so google/cctz is not processed "
              "separately. Built with the posix-threads compiler, because the "
              "win32-threads <mutex> and <condition_variable> are unusable.",
    )


RECIPES = {
    # Pre-C++17-default LTS.
    "abseil_20220623.1": _abseil("20220623.1", "20220623.1"),
    # Current LTS line.
    "abseil_20250127.1": _abseil("20250127.1", "20250127.1"),
}
