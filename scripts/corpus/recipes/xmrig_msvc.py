"""XMRig 6.25.0 built with MSVC. DRAFT."""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _stack_deps as deps


_OPT = "/MD /O2 /Oi /DNDEBUG /Zi"

# Build type Corpus: XMRig's flags.cmake replaces CMAKE_C/CXX_FLAGS_RELEASE
# outright with "/MP /MT /O2 /Oi /DNDEBUG /GL", i.e. the static CRT and
# whole-program optimisation, both of which this corpus excludes. It touches
# no other configuration's flags, so a configuration of our own carries
# exactly what the corpus wants.
_CONFIG = ('-DCMAKE_BUILD_TYPE=Corpus -DCMAKE_C_FLAGS_CORPUS="%s" '
           '-DCMAKE_CXX_FLAGS_CORPUS="%s" '
           '-DCMAKE_EXE_LINKER_FLAGS_CORPUS="%s" '
           "-DWITH_HWLOC=OFF -DWITH_OPENCL=OFF -DWITH_CUDA=OFF"
           % (_OPT, _OPT, deps.MSVC_LINK))

_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" ' + _CONFIG + " "
          + deps.msvc_dep_options())

RECIPES = {
    "XMRig_6.25.0_msvc": Recipe(
        family="XMRig",
        version="6.25.0",
        upstream="https://github.com/xmrig/xmrig",
        license="GPL-3.0-or-later (SPDX identifier in src/version.h)",
        source=Source(git_url="https://github.com/xmrig/xmrig.git",
                      git_ref="v6.25.0"),
        extra_sources=dict(deps.EXTRA_SOURCES),
        build=(deps.msvc_openssl() + deps.msvc_libuv() + [
            # randomx.cmake adds jit_compiler_x86_static.asm under MSVC with
            # no check on pointer size, and ml.exe cannot assemble it for a
            # 32-bit target, so the 32-bit leg turns WITH_ASM off - after which
            # randomx.cmake and asm.cmake both fall through to the portable
            # sources they use for any 32-bit build.
            BuildStep('if "{arch}"=="x64" ' + _CMAKE),
            BuildStep('if "{arch}"=="x86" ' + _CMAKE + " -DWITH_ASM=OFF"),
            BuildStep("cmake --build build-{arch}"),
            BuildStep("dir build-{arch}", allow_failure=True),
        ]),
        artifacts=[Artifact(path="build-{arch}/xmrig.exe",
                            component="xmrig.exe",
                            pdb="build-{arch}/xmrig.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Oi /DNDEBUG /Zi (build type Corpus, without "
                    "XMRig's /MT and /GL); /DEBUG /Brepro /INCREMENTAL:NO "
                    "/OPT:NOREF /OPT:NOICF at link",
    ),
}
