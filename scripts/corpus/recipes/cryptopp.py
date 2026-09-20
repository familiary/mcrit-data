"""Crypto++ - the C++ crypto toolkit, and a regular guest in malware.

Three releases, picked where the library was actually restructured rather
than by recency. 5.6.5 is the last of the 5.6 line and still the Crypto++
most often found embedded in older software: it predates the C++11 move of
6.0 and ships 136 source files, none of them a separate SIMD translation
unit. 7.0.0 is the middle generation, after the SIMD implementations were
split into their own *-simd.cpp files and after Simon, Speck, SM3, SM4,
Kalyna, Threefish, scrypt, Poly1305 and TweetNaCl were added. 8.9.0 is the
current release and adds another wave on top - LSH, CHAM, HIGHT, LEA,
Rabbit, HC-128/256, SHAKE, XTS, ChaCha-AVX and the donna x25519/ed25519
code. Any two of these overlap far less than their version numbers suggest,
and intermediate point releases would add little next to them.

The library is built through its own GNUmakefile. Crypto++ assigns ISA flags
per source file (-msse4.1 for blake2s_simd.cpp, -mavx2 for chacha_avx.cpp,
and so on), so compiling the sources here with one flag set would emit
different code from every real Crypto++ binary. The makefile only offers a
static archive on MinGW - its own cryptopp.dll target exports the FIPS DLL
subset, which is a fraction of the library - and SMDA cannot read a static
archive, so libcryptopp.a is linked into a DLL with --whole-archive to force
every object in rather than only what an anchor happens to reference.

License is the arrangement Wei Dai describes in License.txt: the compilation
is under the Boost Software License 1.0, while the individual files are
placed in the public domain by their authors.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# CXXFLAGS is handed to make on the command line, which also pins it against
# the makefile's own `CXXFLAGS +=` lines - 5.6.5 would otherwise append
# -march=native and make the artefact depend on whichever host built it.
# Upstream's per-file ISA flags live in CRYPTOPP_CXXFLAGS and are unaffected.
_MAKE = ('make -f GNUmakefile -j$(nproc) static '
         'CXX={cxx}-posix AR={ar} RANLIB={ranlib} CXXFLAGS="%s"')

# -shared-libgcc, and no -static-libstdc++: linking the C++ runtime in would
# add thousands of libstdc++ functions to this sample under the cryptopp
# name. ws2_32 is what upstream's LDLIBS adds for MinGW, for winpipes.cpp.
_LINK = ("echo 'int anchor(){return 0;}' > anchor.cpp && "
         "{cxx}-posix -O2 -shared -o cryptopp.dll anchor.cpp "
         "-Wl,--whole-archive libcryptopp.a -Wl,--no-whole-archive "
         "-lws2_32 -lwinpthread -shared-libgcc")


def _cryptopp(version, git_ref, cxxflags="-O2 -DNDEBUG"):
    return Recipe(
        family="cryptopp",
        version=version,
        upstream="https://github.com/weidai11/cryptopp",
        license="Boost-1.0 (compilation); individual files public domain",
        source=Source(git_url="https://github.com/weidai11/cryptopp.git",
                      git_ref=git_ref),
        build=[
            BuildStep(_MAKE % cxxflags),
            BuildStep(_LINK),
        ],
        artifacts=[Artifact(path="cryptopp.dll", component="cryptopp.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="%s, plus the per-file ISA flags (-msse4.1, -mavx2, "
                    "-msha, ...) upstream's makefile assigns" % cxxflags,
        notes="Whole library, not upstream's FIPS DLL subset. Crypto++ carries "
              "third-party code that lands in this sample under the cryptopp "
              "name: TweetNaCl (tweetnacl.cpp, 7.0 and later), Andrew Moon's "
              "curve25519-donna (donna_*.cpp, 8.x), Botan's ChaCha SSE2/AVX "
              "and Crypto++'s own DEFLATE implementation in zdeflate/zinflate/"
              "zlib.cpp, which is not zlib's code. Built with the posix-threads "
              "compiler, because the win32-threads <mutex> is unusable.",
    )


RECIPES = {
    # Last of the 5.6 line, and the one still embedded in older software.
    # 5.6.5 puts `byte` in the global namespace, which C++17 made ambiguous
    # against std::byte - 6.0 moved it into the CryptoPP namespace for exactly
    # that reason. GCC 13 defaults to gnu++17, so the standard this release
    # was written against is named explicitly instead of patching the source.
    "cryptopp_5.6.5": _cryptopp("5.6.5", "CRYPTOPP_5_6_5",
                                cxxflags="-O2 -DNDEBUG -std=c++11"),
    # Middle generation: C++11, SIMD split into its own translation units.
    "cryptopp_7.0.0": _cryptopp("7.0.0", "CRYPTOPP_7_0_0"),
    # Current release.
    "cryptopp_8.9.0": _cryptopp("8.9.0", "CRYPTOPP_8_9_0"),
}
