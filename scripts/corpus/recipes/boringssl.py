"""boringssl - Google's OpenSSL fork, built standalone with its assembly.

gRPC vendors a boringssl and the gRPC recipe deliberately does not record it:
that build needs ``OPENSSL_NO_ASM=ON``, which swaps every primitive that
matters for a C fallback. This is the other route, boringssl on its own terms
with ``OPENSSL_NO_ASM`` off and the NASM output assembled into the image.

**What is pinned, and why.** boringssl has no versions in the usual sense.
Upstream cuts dated tags of the form ``0.YYYYMMDD.N`` and this is the newest
of them, ``0.20260903.0``, commit ``0ce57bbf06a35864fa39e3b9346d41e833683383``
(the annotated tag object is ``31d8e3ef``; the commit is what provenance
records). One version only, as with wolfSSL: boringssl is a moving tree whose
older snapshots differ from each other by API churn, not by anything a
corpus can tell apart, and the dated tag is the closest thing to a release
its own maintainers publish. The tree ships its generated sources in
``gen/`` - ``gen/bcm/*-win.asm`` and ``gen/crypto/*-win.asm`` are perlasm
output already run, in NASM syntax, and listed in ``gen/sources.cmake`` as
``BCM_SOURCES_NASM`` and ``CRYPTO_SOURCES_NASM`` - so neither Go nor perl is
needed to build it, only nasm. Go is what boringssl uses to *regenerate* those
files (``util/pregenerate``) and to run its tests; the recipe does neither.

**How the assembly is enabled.** ``CMakeLists.txt`` does
``enable_language(ASM_NASM)`` when ``WIN32`` and the processor is x86 or
x86_64, and adds the ``*-win.asm`` files to ``crypto``. That is all it takes:
``OPENSSL_NO_ASM`` is passed as ``OFF`` explicitly, and no compile line in
the build tree carries ``-DOPENSSL_NO_ASM`` - it appears only in
``CMakeCache.txt``, as ``OFF``. ``CMAKE_ASM_NASM_COMPILER=nasm`` names the host nasm, and
CMake picks ``-f win64`` or ``-f win32`` by itself from the target.

**The fiat adx routines are not part of a Windows boringssl, and that is what
the gRPC note got wrong.** ``fiat_p256_adx_mul``, ``fiat_p256_adx_sqr`` and the
curve25519 pair are GNU as ``.S`` files written for the SysV ABI, and at this
tag ``third_party/fiat/p256_64.h`` declares and calls them only under
``!OPENSSL_NO_ASM && (__ELF__ || __APPLE__) && OPENSSL_X86_64``, and
``crypto/curve25519/internal.h`` gates ``BORINGSSL_FE25519_ADX`` the same way.
Neither ``gen/sources.cmake``'s NASM lists nor a PE build reference them. The
snapshot gRPC 1.76.0 vendors gates them on ``__GNUC__ && __x86_64__`` alone,
which mingw gcc satisfies, so the link there died on the missing symbols and
the way out was to turn the assembly off. With the current tree that
failure does not exist: on Windows the P-256 field arithmetic is
``ecp_nistz256_*`` from ``p256-x86_64-asm-win.asm``, and there are no adx
routines to be missing. A Chrome for Windows carries exactly that set, so
nothing here is a subset "because mingw could not assemble it".

Two obstacles, both solved on the command line:

  1. **``-pthread`` reaches nasm.** Configure logs
     ``CMAKE_HAVE_LIBC_PTHREAD - Failed`` (mingw's libc has no pthread) and
     FindThreads falls back to the ``-pthread`` compiler flag, which
     ``Threads::Threads`` then puts on *every* language's compile line.
     nasm reads ``-p thread`` as a pre-include and every assembly file dies
     with ``error: unable to open include file `thread': No such file or
     directory``. ``CMAKE_HAVE_LIBC_PTHREAD=1`` is a cache variable, and
     setting it makes FindThreads stop at the first test with an empty flag
     set. That is false about mingw's libc but harmless here: on Windows
     boringssl uses Win32 threads and never calls a pthread function.
  2. **x86 needs SSE2.** ``crypto/internal.h:125`` stops the 32-bit build with
     ``error: "x86 assembly requires SSE2. Build with -msse2 (recommended),
     or disable assembly optimizations with -DOPENSSL_NO_ASM."`` and
     i686-w64-mingw32 defaults to plain i686. ``-msse2`` goes in
     ``CMAKE_C_FLAGS`` and ``CMAKE_CXX_FLAGS``. It replaces the ``-O2`` that
     ``toolchain.build_env`` exports as ``CFLAGS``, which CMake reads as its
     initial value; boringssl's Release flags come after and set ``-O3``, so
     nothing is lost, and it is a no-op for x86_64.

**Shared, not one static image.** ``BUILD_SHARED_LIBS=ON`` works as it is:
boringssl defines ``BORINGSSL_SHARED_LIBRARY`` and its ``OPENSSL_EXPORT`` is
``__declspec(dllexport)`` under ``BORINGSSL_IMPLEMENTATION``, so nothing needs
``--whole-archive`` and each library is its own artefact. libssl, libdecrepit
and libpki import libcrypto.dll, and all four import libgcc and libstdc++
(``libgcc_s_seh-1`` and ``libgcc_s_dw2-1``, ``libstdc++-6``) instead of
absorbing them; the C++ is built ``-fno-exceptions -fno-rtti`` by upstream, so
what does land in an image from libstdc++ is a handful of inline
``std::__introsort_loop``-style template instantiations. libwinpthread-1 is
imported by libcrypto through the posix-threads C++ runtime, not because
anything calls pthread. Only ``crypto ssl decrepit pki`` are built: the rest
of the tree is tests, benchmarks, fuzzers and the ``bssl`` tool, and building
``all`` also runs googletest and google-benchmark's configure.

**What is in the images, by function, and what is not boringssl's.** Counts
are SMDA's recovery of each unmodified DLL. Total = the compiler runtime the
glue filter removes (the MinGW startup, the dtoa/printf/mbrtowc pieces, and
the libc thunks behind ``memcpy`` and ``malloc``) + one-instruction import
thunks + libstdc++ instantiations + vendored Fiat (fiat-crypto's generated
field arithmetic under ``third_party/fiat``, which any real boringssl carries)
+ functions with no recovered name + boringssl's own. The thunks in libssl,
libdecrepit and libpki are ``jmp [__imp_...]`` into libcrypto.dll, one per
API function called, named after it.

    x64            total   CRT  thunks  libstdc++  fiat  unnamed    own
    libcrypto       4635   127      52         13     8       88   4347
    libssl          1778   113     407         28     0        5   1225
    libdecrepit      207    52      85          0     0        1     69
    libpki           740   110     138        116     0        8    368

    x86            total   CRT  thunks  libstdc++  fiat  unnamed    own
    libcrypto       4465   135      16         13     9       45   4247
    libssl          2314   120     396         28     0      339   1431
    libdecrepit      208    52      78          0     0        6     72
    libpki          1019   116     127        121     0      205    450

Every row sums exactly. What is recorded is the total less the CRT column.
Two of the "own" bodies in each libcrypto are not boringssl's:
``gai_strerrorA`` and ``gai_strerrorW`` are ``static inline`` in mingw-w64's
``ws2tcpip.h`` and are compiled into any translation unit that includes it,
here through boringssl's socket code. The baseline probe does not call them, so
the glue filter keeps them, and they are what ``validate --deep`` fails on
for this family: 4 leakage findings (15 and 18 instructions on x64, 13 and 16
on x86), the same bodies also sitting in OpenSSL and libevent. Own is 4345
on x64 and 4245 on x86 once they are taken out.
The unnamed column is SMDA's: it names from exported and global symbols and
not from local ones, so in x64 libcrypto 73 of the 88 are the perlasm
internal helpers (``_aesni_ctr32_6x``, ``_vpaes_encrypt_core``,
``__ecp_nistz256_mul_montq``, the ``se_handler`` unwind routines) that
do have a local symbol, and 15 are fragments with none. In x86 libssl and
libpki the unnamed are almost all such fragments - 338 of 339 and 204 of 205
have no symbol at their entry, at 2.6 instructions on average - which is
measured here and not explained. It is the same shape as poco's x86 image.

**The assembly is present, and this is how that was checked**, on the images
as built and not on the build log: 113 global symbols are declared by the
x86_64 NASM files and all 113 are in the x64 libcrypto (112 at the exact
entry SMDA recovers a function from, 36907 instructions between them;
``vpaes_cbc_encrypt`` is recovered 13 bytes in, after its register-save
prologue); 43 of 43 for the 586 files in the x86 image, 17235 instructions.
Among them ``aes_hw_encrypt``, ``aesni_gcm_encrypt``, ``gcm_ghash_clmul``,
``gcm_ghash_vpclmulqdq_avx512``, ``sha256_block_data_order_hw``/``_avx``/
``_ssse3``, ``bn_mul_mont_nohw``, ``ecp_nistz256_*_adx`` and
``chacha20_poly1305_seal_avx2``. The same tree built with ``OPENSSL_NO_ASM=ON``
and everything else identical has 4689 text symbols in libcrypto on x64
against 4880 with the assembly (219 present only with it, 28 only without:
the ``aes_nohw`` and ``sha256_block_data_order_nohw`` C bodies and libgcc's
``__udivti3``), ``.text`` of 1612136 bytes against 1782696, and SMDA finds
4431 functions and 373120 instructions against 4635 and 408764. On x86 it is
4584 against 4631 symbols, 1746836 against 1768852 bytes and 4390 against 4465
functions; the 586 output is a much smaller share of that image, since
boringssl's 32-bit assembly has no AES-GCM, SHA-NI, ADX or AVX2 paths.

**Overlap with the OpenSSL family is real, and it is ancestry.** Comparing
PicHashes at the ten-instruction floor against every OpenSSL artefact of the
same architecture, x64 libcrypto shares 52 hashes with data/OpenSSL and x86
70, mostly under an identical name (``ASN1_TYPE_cmp``, ``BN_num_bits_word``,
``bn_mul_comba4``, ``DES_encrypt3``, ``X509_pubkey_digest``,
``PEM_write_bio_PKCS8PrivateKey_nid``), and on x86 the vpaes and comba
perlasm bodies, which both projects generate from the same Cryptogams
scripts. libdecrepit shares 8 (Blowfish, CAST, RIPEMD-160); libssl and libpki
share 3 and 1 on x64 and 7 and 4 on x86, unnamed fragments and short bodies
whose names differ. This is boringssl being an OpenSSL fork, not
misattribution, and only two families are involved - ``validate --deep``
counts a PicHash from three.

License is what boringssl's own LICENSE describes: the code is under the
OpenSSL license and the original SSLeay license for what was inherited, ISC
for what Google wrote, and Apache-2.0 for the newer files.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# CMAKE_HAVE_LIBC_PTHREAD and the -msse2 flags are the two obstacles in the
# module docstring. The g++ is the posix-threads one, as everywhere else here.
# Release is boringssl's own -O3 -DNDEBUG -ggdb: it does not strip, so the
# COFF symbol table SMDA reads is intact.
_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_SYSTEM_PROCESSOR={platform} "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx}-posix "
          "-DCMAKE_RC_COMPILER={windres} -DCMAKE_ASM_NASM_COMPILER=nasm "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
          "-DBUILD_SHARED_LIBS=ON -DOPENSSL_NO_ASM=OFF "
          "-DCMAKE_HAVE_LIBC_PTHREAD=1 "
          "-DCMAKE_C_FLAGS=-msse2 -DCMAKE_CXX_FLAGS=-msse2")


RECIPES = {
    "boringssl_0.20260903.0": Recipe(
        family="boringssl",
        version="0.20260903.0",
        upstream="https://github.com/google/boringssl",
        license="Apache-2.0 AND ISC AND OpenSSL AND SSLeay",
        source=Source(git_url="https://github.com/google/boringssl.git",
                      git_ref="0.20260903.0"),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc) "
                      "--target crypto ssl decrepit pki"),
        ],
        artifacts=[
            Artifact(path="build-{arch}/libcrypto.dll",
                     component="crypto.dll"),
            Artifact(path="build-{arch}/libssl.dll", component="ssl.dll"),
            Artifact(path="build-{arch}/libdecrepit.dll",
                     component="decrepit.dll"),
            Artifact(path="build-{arch}/libpki.dll", component="pki.dll"),
        ],
        toolchains=["mingw_x86", "mingw_x64"],
        # nasm assembles the perlasm output. Go is not needed: gen/ is
        # committed, and Go only regenerates it and runs the tests.
        requires=["nasm"],
        build_flags="-O3 -DNDEBUG -ggdb (CMake Release, boringssl's own), "
                    "-msse2 on x86 as boringssl's assembly requires; "
                    "OPENSSL_NO_ASM=OFF, the NASM *-win.asm output assembled "
                    "with nasm -f win64/win32; shared build, so libssl, "
                    "libdecrepit and libpki import libcrypto.dll and all "
                    "import libstdc++ and libgcc",
        notes="boringssl 0.20260903.0 (commit 0ce57bbf, the newest dated "
              "release tag) standalone, with its assembly: 113 assembly "
              "functions in the x64 libcrypto and 43 in x86, all present in "
              "the images. Four libraries, one artefact each: libcrypto, "
              "libssl, libdecrepit and libpki. Function counts as SMDA "
              "recovers them, x64 (x86): libcrypto 4635 (4465) of which 127 "
              "(135) are MinGW runtime removed by the glue filter, 52 (16) "
              "import thunks, 13 (13) libstdc++ instantiations, 8 (9) "
              "vendored fiat-crypto, 88 (45) unnamed, mostly local labels in "
              "the assembly, and 4347 (4247) boringssl's own, two of each being mingw-w64's inline gai_strerrorA/W; libssl 1778 "
              "(2314) with 407 (396) one-instruction thunks into libcrypto "
              "and 28 (28) libstdc++; libdecrepit 207 (208) with 85 (78) "
              "thunks; libpki 740 (1019) with 138 (127) thunks and 116 (121) "
              "libstdc++. Built with OPENSSL_NO_ASM=ON instead, the x64 "
              "libcrypto loses 219 text symbols and 170560 bytes of .text "
              "and gains 28 C bodies. This is a different build from the "
              "boringssl inside gRPC, which needs OPENSSL_NO_ASM because "
              "gRPC 1.76.0's snapshot gates the ELF-only fiat adx assembly "
              "on __x86_64__ instead of the ELF and Apple check this tag "
              "has. About 50 to 70 PicHashes per architecture are shared "
              "with the OpenSSL family, almost all under the same symbol "
              "name, which is fork ancestry rather than misattribution.",
    ),
}
