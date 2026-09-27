"""libpng - found in old packers, installers and image-handling tooling.

libpng needs zlib. That dependency is fetched through the recipe's own Source
so its digest is verified and recorded, rather than curl'd inside a build
step where neither would happen.

libpng is linked against zlib's *import* library rather than libz.a. Linking
the static one pulled a whole copy of zlib into libpng16.dll - 62 of its 500
functions were zlib's, byte-identical to data/libzlib - so zlib code was
being attributed to the libpng family and any sample containing plain zlib
would have matched libpng. Importing instead leaves libpng16.dll containing
only libpng.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_ZLIB_VERSION = "1.3.1"
_ZLIB_SHA256 = "9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23"

# zlib1.dll plus its import library, so libpng imports zlib rather than
# absorbing it.
_STAGE_ZLIB = ("tar xf {zlib_archive} && mv zlib-%s zlib && "
               "make -C zlib -f win32/Makefile.gcc PREFIX={prefix} STRIP=true "
               "-j$(nproc) zlib1.dll" % _ZLIB_VERSION)

_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_RC_COMPILER={windres} "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
          "-DPNG_SHARED=ON -DPNG_STATIC=OFF -DPNG_TESTS=OFF -DPNG_TOOLS=OFF "
          # Absolute, or CMake records it as a make target and the link step
          # fails with "No rule to make target 'zlib/libz.a'".
          "-DZLIB_INCLUDE_DIR=$PWD/zlib -DZLIB_LIBRARY=$PWD/zlib/libz.dll.a")


RECIPES = {
    "libpng_1.6.50": Recipe(
        family="libpng",
        version="1.6.50",
        upstream="https://github.com/pnggroup/libpng",
        license="libpng-2.0",
        source=Source(git_url="https://github.com/pnggroup/libpng.git",
                      git_ref="v1.6.50"),
        # zlib is pinned by digest and staged before configure.
        extra_sources={"zlib_archive": Source(
            url="https://zlib.net/fossils/zlib-%s.tar.gz" % _ZLIB_VERSION,
            sha256=_ZLIB_SHA256)},
        build=[
            BuildStep(_STAGE_ZLIB),
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="build-{arch}/libpng16.dll",
                            component="libpng16.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (CMake Release)",
        notes="Imports zlib %s rather than linking it statically, so this "
              "sample contains libpng code only." % _ZLIB_VERSION,
    ),
}
