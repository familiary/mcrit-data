"""libxml2 - the XML stack vendored into an enormous amount of software.

Two picks either side of the parser rework: 2.9.14 is the last of the very
long-lived 2.9 series that most vendored copies still are, and 2.14.x is
current.

ShiftMediaProject publishes MSVC builds of libxml2 with PDBs across
msvc12-msvc17, which would be closer to what is met in the wild than a MinGW
build; that route is worth adding separately rather than instead, since the
two compilers produce genuinely different code.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_RC_COMPILER={windres} "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
          "-DBUILD_SHARED_LIBS=ON -DLIBXML2_WITH_PYTHON=OFF "
          "-DLIBXML2_WITH_ZLIB=OFF -DLIBXML2_WITH_LZMA=OFF "
          "-DLIBXML2_WITH_ICONV=OFF -DLIBXML2_WITH_TESTS=OFF "
          "-DLIBXML2_WITH_PROGRAMS=OFF")


def _libxml2(version, git_ref, dll):
    return Recipe(
        family="libxml2",
        version=version,
        upstream="https://gitlab.gnome.org/GNOME/libxml2",
        license="MIT",
        source=Source(git_url="https://github.com/GNOME/libxml2.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="build-{arch}/%s" % dll, component=dll)],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (CMake Release), optional codecs disabled",
    )


RECIPES = {
    # Last of the 2.9 series; what most vendored copies are.
    "libxml2_2.9.14": _libxml2("2.9.14", "v2.9.14", "libxml2.dll"),
    # Current series, after the parser rework.
    "libxml2_2.14.3": _libxml2("2.14.3", "v2.14.3", "libxml2.dll"),
}
