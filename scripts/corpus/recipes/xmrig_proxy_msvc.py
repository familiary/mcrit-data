"""xmrig-proxy 6.26.0 built with MSVC. DRAFT."""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _stack_deps as deps


_OPT = "/MD /O2 /Oi /DNDEBUG /Zi"

_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Corpus -DCMAKE_C_FLAGS_CORPUS="%s" '
          '-DCMAKE_CXX_FLAGS_CORPUS="%s" '
          '-DCMAKE_EXE_LINKER_FLAGS_CORPUS="%s" %s'
          % (_OPT, _OPT, deps.MSVC_LINK, deps.msvc_dep_options()))

RECIPES = {
    "xmrig-proxy_6.26.0_msvc": Recipe(
        family="xmrig-proxy",
        version="6.26.0",
        upstream="https://github.com/xmrig/xmrig-proxy",
        license="GPL-3.0-or-later (SPDX identifier in src/version.h)",
        source=Source(git_url="https://github.com/xmrig/xmrig-proxy.git",
                      git_ref="v6.26.0"),
        extra_sources=dict(deps.EXTRA_SOURCES),
        build=(deps.msvc_openssl() + deps.msvc_libuv() + [
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch}"),
            BuildStep("dir build-{arch}", allow_failure=True),
        ]),
        artifacts=[Artifact(path="build-{arch}/xmrig-proxy.exe",
                            component="xmrig-proxy.exe",
                            pdb="build-{arch}/xmrig-proxy.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Oi /DNDEBUG /Zi (build type Corpus, without "
                    "xmrig-proxy's /MT and /GL); /DEBUG /Brepro "
                    "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link",
    ),
}
