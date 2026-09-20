"""libstdc++ - filling a gap in the existing MinGW coverage.

data/MinGW carries libstdc++ and libsupc++ on x64 (the r38 x64 report has
9806 functions, around 4700 of which demangle into std) but not on x86: the
r38 x86 report is 2818 functions, mostly Win32 import thunks, with no _ZN or
_ZSt symbols, no _Unwind_* and no libgcc helpers at all. So 32-bit libstdc++
is covered nowhere in the corpus.

This does not replace reprocessing the MinGW x86 inputs, which is the real
fix and is a question for the maintainer. It does give the corpus a 32-bit
libstdc++ reference in the meantime.

x86 only, for that reason: the gap is the whole point of the recipe. An x64
build here would be a second reference for code data/MinGW r38 x64 already
carries, and a duplicate reference sample is exactly what this corpus is
meant to avoid.

Uniquely among these recipes, the runtime is linked statically on purpose:
elsewhere -static-libstdc++ would be contamination, here it is the subject.
The C runtime is not, though - a bare -static would have dragged mingw-w64's
own startup code and libmingwex in beside it, which are neither libstdc++
nor this recipe's business.

Version coverage is limited to whatever GCC the host toolchain provides;
spreading it would need other mingw-w64 GCC builds.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# A DLL, not an EXE. The exerciser exports one function and defines no main,
# so an executable link has no entry point and mingw's startup object asks for
# WinMain instead. It also drops the bare -static, which pulled mingw-w64's
# own CRT, libmingwex and the startup code into a sample that is supposed to
# be libstdc++: -static-libstdc++ -static-libgcc bring in the subject, and the
# C runtime stays where it belongs, imported from msvcrt.
_BUILD = ("{cxx} -std=c++17 -O2 -shared -o libstdcxx_exerciser.dll "
          "{repo}/scripts/corpus/exercisers/libstdcxx.cpp "
          "-static-libstdc++ -static-libgcc")


RECIPES = {
    "libstdcxx_gcc13": Recipe(
        family="libstdc++",
        version="GCC 13.2 (mingw-w64)",
        upstream="https://gcc.gnu.org/",
        license="GPL-3.0 with GCC Runtime Library Exception",
        # The runtime ships with the toolchain, so there is nothing to fetch;
        # zlib is used only as a trivial, digest-pinned stand-in source tree
        # so the recipe still goes through the same fetch and provenance path.
        source=Source(url="https://zlib.net/fossils/zlib-1.3.1.tar.gz",
                      sha256="9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23"),
        build=[BuildStep(_BUILD)],
        artifacts=[Artifact(path="libstdcxx_exerciser.dll",
                            component="libstdcxx_exerciser.dll")],
        toolchains=["mingw_x86"],
        build_flags="-O2 -std=c++17 -static-libstdc++ -static-libgcc",
        # The runtime is what is being collected, so the glue filter must not
        # strip it back out.
        drop_crt_glue=False,
        notes="Built from an exerciser that instantiates a broad slice of the "
              "standard library; the exerciser only selects which functions "
              "are pulled in, the code is libstdc++'s. libgcc helpers and the "
              "unwinder are in the sample too and are not libstdc++'s "
              "strictly, but they are the same GCC runtime and belong with "
              "it. The glue filter is off, because the probe it measures "
              "against is itself linked -static-libstdc++ and would delete "
              "exactly the code this recipe exists to collect.",
    ),
}
