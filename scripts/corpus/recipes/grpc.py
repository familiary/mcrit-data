"""gRPC - the C core and the C++ layer (mcrit-data issue #10).

``scripts/corpus/README.md`` recorded this as investigated and not built:
"cross-building needs a full native build first to obtain ``protoc`` and
``grpc_cpp_plugin``, plus boringssl (which needs Go); 45-90 minutes for two
architectures". All of that is true and the build is still the most expensive
in this corpus, but none of it is a blocker, so it is built.

Four artefacts on x64 and three on x86, all of them gRPC's own code:

    libgrpc.dll             10525 text symbols - the C core
    libgrpc++.dll            1345 - the C++ layer over it
    libgpr.dll                394 - gRPC's portability layer
    libaddress_sorting.dll     73 - RFC 6724 destination address sorting

**Everything else it builds is imported, not absorbed, and that is the whole
reason this is worth having.** gRPC vendors abseil, protobuf, re2, zlib,
c-ares and upb, and five of those six are families of their own here. With
``BUILD_SHARED_LIBS=ON`` each becomes its own DLL and ``libgrpc.dll`` merely
links against them: its import table names ``libabsl_*``, ``libupb_*``,
``libgpr`` and ``libaddress_sorting``, so what is inside it is gRPC's. Of its
10525 symbols, 8787 carry a grpc name; the 1555 ``absl`` ones are inline and
template code instantiated into gRPC's own translation units, which is the
accepted case that ``protobuf_31.1`` already documents, not linked-in abseil
object code. The 153 ``EVP_``/``X509_``/``SSL_`` entries are one-instruction
import thunks into boringssl, which the import table confirms.

**boringssl is deliberately not recorded**, although this build produces
``libcrypto.dll`` (3055 symbols) and ``libssl.dll`` (1457). It has no family
here and it is a genuinely valuable target, but not as built here:
``OPENSSL_NO_ASM=ON`` is required, because boringssl's x86-64 assembly is not
assembled for mingw and the link dies on ``fiat_p256_adx_mul`` and
``fiat_p256_adx_sqr``. With the assembly off, every primitive that matters -
the field arithmetic, AES, the hashes - is a C fallback rather than the code a
real boringssl carries, so recording it would put bodies in the corpus that no
Chrome or Android binary contains. It should be built on its own terms, with
its assembly, if it is wanted.

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
          "rather than linked in; OPENSSL_NO_ASM because boringssl's x86-64 "
          "assembly is not assembled for mingw; gRPC_BUILD_CODEGEN=OFF with a "
          "host-built protoc")

_NOTES = (
    "The C core, the C++ layer, the portability layer and the address sorter "
    "- all gRPC's own code. gRPC vendors abseil, protobuf, re2, zlib, c-ares "
    "and upb, five of which are families of their own here, and the shared "
    "build keeps every one of them out: libgrpc.dll imports libabsl_*, "
    "libupb_*, libgpr and libaddress_sorting rather than absorbing them. Of "
    "its 10525 text symbols 8787 carry a grpc name; the 1555 absl ones are "
    "inline and template code instantiated into gRPC's own translation "
    "units, the same accepted case protobuf_31.1 records, and the 153 "
    "EVP_/X509_/SSL_ entries are one-instruction import thunks into "
    "boringssl. boringssl itself is built here but deliberately not "
    "recorded: it needs OPENSSL_NO_ASM to link at all under mingw, which "
    "replaces every primitive that matters with a C fallback, so its bodies "
    "would match no real boringssl. protoc and grpc_cpp_plugin are built for "
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


def _recipe(toolchains, artifacts, extra=""):
    return Recipe(
        family="grpc",
        version="1.76.0",
        upstream="https://github.com/grpc/grpc",
        license="Apache-2.0",
        source=Source(git_url="https://github.com/grpc/grpc.git",
                      git_ref="v1.76.0"),
        build=_BUILD,
        artifacts=artifacts,
        toolchains=toolchains,
        # Go is needed by boringssl's build, which generates sources with it.
        requires=["go"],
        build_flags=_FLAGS,
        notes=_NOTES + extra,
    )


# Split by architecture for one reason only: libgrpc.dll is recorded on x64
# and not on x86. See the module docstring for what the x86 image does and why
# it is left out rather than forced through.
RECIPES = {
    "grpc_1.76.0": _recipe(["mingw_x64"], [_GRPC] + _REST),
    "grpc_1.76.0_x86": _recipe(
        ["mingw_x86"], list(_REST),
        extra=" libgrpc.dll is not recorded on x86: its image trips the "
              "incremental-link-table check with a 69-entry run of unnamed "
              "one-instruction jumps, a pattern that check was not written "
              "for and that has not been identified, so the artefact is left "
              "out rather than the check relaxed."),
}
