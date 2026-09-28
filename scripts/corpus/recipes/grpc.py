"""gRPC - the C core and the C++ layer (mcrit-data issue #10).

``scripts/corpus/README.md`` recorded this as investigated and not built:
"cross-building needs a full native build first to obtain ``protoc`` and
``grpc_cpp_plugin``, plus boringssl (which needs Go); 45-90 minutes for two
architectures". All of that is true and the build is still the most expensive
in this corpus, but none of it is a blocker, so it is built.

Four artefacts on each of x64 and x86. The symbol counts are x64's:

    libgrpc.dll             10525 text symbols - the C core
    libgrpc++.dll            1345 - the C++ layer over it
    libgpr.dll                394 - gRPC's portability layer
    libaddress_sorting.dll     73 - RFC 6724 destination address sorting

**Most of what else it builds is imported, not absorbed, and that is the
whole reason this is worth having, but not all of it.** gRPC vendors abseil,
protobuf, re2, zlib, c-ares and upb. With ``BUILD_SHARED_LIBS=ON`` abseil,
re2 and most of upb become DLLs of their own and ``libgrpc.dll`` links against
them: its import table names ``libabsl_*``, ``libupb_*``, ``libre2``,
``libgpr`` and ``libaddress_sorting``. zlib, c-ares and two of the upb
libraries (json and textformat) are static libraries on the link line instead,
so their code is inside ``libgrpc.dll``: 637 c-ares, 69 zlib and 21 upb
functions of the 25598 in the x86 image, and 604 functions with ``ares_`` in
the name in the x64 report. Of the x64 image's 10525 symbols, 8787 carry a
grpc name; the 1555 ``absl`` ones are inline and template code instantiated
into gRPC's own translation units, which is the accepted case that
``protobuf_31.1`` already documents, not linked-in abseil object code. The 153
``EVP_``/``X509_``/``SSL_`` entries are one-instruction import thunks into
boringssl, which the import table confirms.

**The x86 libgrpc.dll has a run of 69 unnamed jumps that is not a link
table.** SMDA recovers 69 one-instruction ``jmp rel32`` functions at a
five-byte stride from 0x69c8e9df (image base 0x69c00000), which is past
``config.MAX_INCREMENTAL_THUNK_RUN`` and looks like an ``/INCREMENTAL`` table.
It is GCC's exception landing-pad stubs. The run is the last 0x159 bytes of
``GlobalSubchannelPool::UnregisterSubchannel``, inside that function's
unwind range; its 69 entries are 69 of the 69 distinct landing pads in the
function's LSDA, and each jumps into the function's own ``.cold`` part, which
GCC splits off under ``-freorder-blocks-and-partition``. ``-fno-reorder-
blocks-and-partition`` removes the run (the longest is then 20) and 4724
functions, 18% of the image, but it changes code generation to something no
default x86 gRPC binary carries, and would have to apply to the whole x86
build, where libgrpc++, libgpr and libaddress_sorting hold 243, 46 and 4
further ``.cold`` parts. It is not used. What tells the
run from a table is that none of the 69 jumps to a function entry and that
the 1318 unnamed direct jumps are 5.1% of the functions; see
``smdaify._is_landing_pad_island``. The 25598 functions split as 12873 named
gRPC code, 8041 unnamed fragments in gRPC's translation units, 1807 ``std::``
and 1512 ``absl`` instantiations there, 616 import thunks, 727 static
c-ares, zlib and upb, 6 mingw runtime remnants, and 16 stretches of data at
the end of ``.text`` that SMDA read as code.

**boringssl is built here and recorded elsewhere.** This build produces
``libcrypto.dll`` (3055 symbols) and ``libssl.dll`` (1457), and neither is
filed under grpc. ``OPENSSL_NO_ASM=ON`` is required for the copy gRPC 1.76.0
vendors: its ``third_party/fiat/p256_64.h`` declares and calls
``fiat_p256_adx_mul`` and ``fiat_p256_adx_sqr`` under ``__GNUC__ &&
__x86_64__``, which mingw gcc satisfies, while its CMake lists the two ``.S``
files only among the GNU as sources and not in ``CRYPTO_SOURCES_NASM``, so the
link dies on both. With the assembly off, every primitive that matters - the
field arithmetic, AES, the hashes - is a C fallback rather than the code a
real boringssl carries, and recording it under gRPC would put bodies in the
corpus that no Chrome or Android binary contains. The assembly is not
unbuildable for mingw, though: the current boringssl tree gates those adx
routines on ELF and Apple only, and ``recipes/boringssl.py`` builds it
standalone with ``OPENSSL_NO_ASM`` off and the NASM output assembled, as the
``boringssl`` family.

The build has three stages and the first is native:

  1. ``protoc`` and ``grpc_cpp_plugin`` are built for the *host*, because gRPC
     generates its own protos during the build and a cross-built protoc cannot
     run. This is why the whole thing is expensive: it compiles the vendored
     protobuf twice, once for the host and once for the target. The native
     compiler has to be named explicitly here, because
     ``toolchain.build_env`` exports ``CC`` and ``CXX`` as the cross
     compilers and CMake would otherwise configure the host stage with
     mingw.
  2. The target is configured with ``gRPC_BUILD_CODEGEN=OFF``, so the plugins
     are not built again for Windows, and pointed at the host protoc.
  3. Only ``grpc`` and ``grpc++`` are built, rather than everything. That is
     not merely a saving: building ``all`` fails on two targets neither
     artefact needs. ``third_party/re2``'s ``testing`` target compiles
     ``util/pcre.cc``, re2's optional PCRE compatibility wrapper, which does
     not build under GCC 13 - ``'hit_limit_' was not declared in this scope``
     and ``'int32_t' does not name a type``. And ``grpc_unsecure`` fails to
     link on ``grpc_core::ParsePemCertificateChain`` and
     ``IsRootCertInfoEmpty``. Naming the two targets avoids both without
     patching or disabling anything.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Stage 1, host. The native compiler is named explicitly and that is not
# redundant: toolchain.build_env exports CC and CXX as the cross compilers, so
# without this CMake configures the host stage with mingw, try_compile emits a
# Windows .exe and check_type_size fails on "Cannot copy output executable ''"
# in third_party/zlib before anything is built. This stage's output runs on
# the build machine, never on the target. Only the C++ plugin is wanted, so
# the other language plugins are off.
_HOST_CMAKE = ("cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Release "
               "-DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ "
               "-DgRPC_BUILD_TESTS=OFF "
               "-DgRPC_BUILD_GRPC_CSHARP_PLUGIN=OFF "
               "-DgRPC_BUILD_GRPC_NODE_PLUGIN=OFF "
               "-DgRPC_BUILD_GRPC_OBJECTIVE_C_PLUGIN=OFF "
               "-DgRPC_BUILD_GRPC_PHP_PLUGIN=OFF "
               "-DgRPC_BUILD_GRPC_PYTHON_PLUGIN=OFF "
               "-DgRPC_BUILD_GRPC_RUBY_PLUGIN=OFF")

# Stage 2, target. OPENSSL_NO_ASM is not optional; see the module docstring.
# The protoc path is the one CMake names it, which carries the protobuf
# version.
_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_SYSTEM_PROCESSOR={platform} "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx}-posix "
          "-DCMAKE_RC_COMPILER={windres} "
          "-DCMAKE_FIND_ROOT_PATH=/usr/{host} -DCMAKE_BUILD_TYPE=Release "
          "-DBUILD_SHARED_LIBS=ON -DOPENSSL_NO_ASM=ON "
          "-DgRPC_BUILD_TESTS=OFF -DgRPC_BUILD_CODEGEN=OFF "
          "-DgRPC_BUILD_GRPC_CSHARP_PLUGIN=OFF "
          "-DgRPC_BUILD_GRPC_NODE_PLUGIN=OFF "
          "-DgRPC_BUILD_GRPC_OBJECTIVE_C_PLUGIN=OFF "
          "-DgRPC_BUILD_GRPC_PHP_PLUGIN=OFF "
          "-DgRPC_BUILD_GRPC_PYTHON_PLUGIN=OFF "
          "-DgRPC_BUILD_GRPC_RUBY_PLUGIN=OFF "
          "-D_gRPC_PROTOBUF_PROTOC_EXECUTABLE=$PWD/build-host/third_party/"
          "protobuf/protoc-31.1.0")


_BUILD = [
    BuildStep(_HOST_CMAKE),
    BuildStep("cmake --build build-host -j$(nproc) "
              "--target protoc grpc_cpp_plugin"),
    BuildStep(_CMAKE),
    # gpr and address_sorting come along as dependencies of these two.
    BuildStep("cmake --build build-{arch} -j$(nproc) --target grpc grpc++"),
]

_FLAGS = ("-O3 -DNDEBUG (CMake Release, GNU default), shared build so the "
          "vendored abseil, protobuf, re2, zlib, c-ares and upb are imported "
          "rather than linked in; OPENSSL_NO_ASM because the vendored "
          "boringssl declares adx assembly that its Windows build never "
          "assembles; gRPC_BUILD_CODEGEN=OFF with a "
          "host-built protoc")

_NOTES = (
    "The C core, the C++ layer, the portability layer and the address sorter. "
    "gRPC vendors abseil, protobuf, re2, zlib, c-ares and upb. The shared "
    "build imports abseil, re2 and most of upb as DLLs of their own "
    "(libgrpc.dll imports libabsl_*, libupb_*, libre2, libgpr and "
    "libaddress_sorting), but zlib, c-ares and the upb json and textformat "
    "libraries are static and are inside libgrpc.dll: 727 of the 25598 "
    "functions in the x86 image, and 604 c-ares ones in the x64 report. Of "
    "the x64 image's 10525 text symbols 8787 carry a grpc name; the 1555 "
    "absl ones are inline and template code instantiated into gRPC's own "
    "translation units, the same accepted case protobuf_31.1 records, and "
    "the 153 EVP_/X509_/SSL_ entries are one-instruction import thunks into "
    "boringssl. boringssl itself is built here but not recorded under "
    "grpc: the vendored snapshot needs OPENSSL_NO_ASM to link under mingw, "
    "which replaces every primitive that matters with a C fallback, so its "
    "bodies would match no real boringssl. It is a family of its own, built "
    "standalone with its assembly. protoc and grpc_cpp_plugin are built for "
    "the host first because gRPC generates its own protos during the build, "
    "which is what makes this the most expensive recipe here. Only the grpc "
    "and grpc++ targets are built: building everything also fails on re2's "
    "testing target, whose util/pcre.cc does not compile under GCC 13, and "
    "on grpc_unsecure, and neither is needed for these artefacts.")

_GRPC = Artifact(path="build-{arch}/libgrpc.dll", component="grpc.dll")
_REST = [
    Artifact(path="build-{arch}/libgrpc++.dll", component="grpc++.dll"),
    Artifact(path="build-{arch}/libgpr.dll", component="gpr.dll"),
    Artifact(path="build-{arch}/libaddress_sorting.dll",
             component="address_sorting.dll"),
]


RECIPES = {
    "grpc_1.76.0": Recipe(
        family="grpc",
        version="1.76.0",
        upstream="https://github.com/grpc/grpc",
        license="Apache-2.0",
        source=Source(git_url="https://github.com/grpc/grpc.git",
                      git_ref="v1.76.0"),
        build=_BUILD,
        artifacts=[_GRPC] + _REST,
        toolchains=["mingw_x64", "mingw_x86"],
        # Go is needed by boringssl's build, which generates sources with it.
        requires=["go"],
        build_flags=_FLAGS,
        notes=_NOTES,
    ),
}
