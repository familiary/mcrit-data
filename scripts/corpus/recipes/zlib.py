"""zlib - the most widely statically linked compression library on Windows.

data/libzlib already covers 1.2.8 - 1.2.11 built with MSVC 12/14/15, taken
from ShiftMediaProject. These recipes stay in the same corpus family so the
data groups together in MCRIT, and add the MinGW/GCC side: a different code
generator for the same sources rather than more of the same. Two of the
versions deliberately overlap the MSVC coverage, which is what makes a
compiler-to-compiler comparison possible for identical upstream code.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


def _zlib(version, sha256):
    return Recipe(
        family="libzlib",
        version=version,
        upstream="https://github.com/madler/zlib",
        license="zlib",
        source=Source(url="https://zlib.net/fossils/zlib-%s.tar.gz" % version,
                      sha256=sha256),
        # win32/Makefile.gcc is upstream's own MinGW build. STRIP has to be
        # overridden on the command line rather than in the environment,
        # because the makefile assigns it itself; without that the COFF symbol
        # table is discarded and the report carries no function names at all.
        build=[
            BuildStep("make -f win32/Makefile.gcc clean", allow_failure=True),
            BuildStep("make -f win32/Makefile.gcc PREFIX={prefix} STRIP=true "
                      "-j$(nproc) zlib1.dll"),
        ],
        artifacts=[Artifact(path="zlib1.dll", component="zlib1.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (win32/Makefile.gcc default)",
    )


RECIPES = {
    # Overlaps the existing MSVC12/MSVC14 coverage of the same source.
    "libzlib_1.2.8": _zlib(
        "1.2.8", "36658cb768a54c1d4dec43c3116c27ed893e88b02ecfcb44f2166f9c0b7f2a0d"),
    # The long-lived release the bulk of existing binaries were built against;
    # also covered for MSVC12/14/15, so all four compilers line up here.
    "libzlib_1.2.11": _zlib(
        "1.2.11", "c3e5e9fdd5004dcb542feda5ee4f0ff0744628baf8ed2dd5d66f8ca1197cb1a1"),
    # First release after the CVE-2018-25032 deflate rework in 1.2.12, so the
    # compression path differs from everything above it.
    "libzlib_1.2.13": _zlib(
        "1.2.13", "b3a24de97a8fdbc835b9833169501030b8977031bcb54b3b3ac13740f846ab30"),
    # Current release; what anything built today links against.
    "libzlib_1.3.1": _zlib(
        "1.3.1", "9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23"),
}
