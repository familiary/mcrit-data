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
Version coverage is limited to whatever GCC the host toolchain provides;
spreading it would need other mingw-w64 GCC builds.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_BUILD = ("{cxx} -std=c++17 -O2 -o libstdcxx_exerciser.exe "
          "{repo}/scripts/corpus/exercisers/libstdcxx.cpp "
          "-static-libstdc++ -static-libgcc -static")


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
        artifacts=[Artifact(path="libstdcxx_exerciser.exe",
                            component="libstdcxx_exerciser.exe")],
        toolchains=["mingw_x86"],
        build_flags="-O2 -std=c++17, statically linked runtime",
        # The runtime is what is being collected, so the glue filter must not
        # strip it back out.
        drop_crt_glue=False,
        notes="Built from an exerciser that instantiates a broad slice of the "
              "standard library. Most of the sample is libstdc++ and libsupc++ "
              "code, but the link is -static with the CRT-glue filter disabled, "
              "so mingw-w64 CRT startup code, libmingwex and libgcc helpers are "
              "retained as well and are not libstdc++'s.",
    ),
}
