"""xmrig-proxy 6.26.0 built with MSVC, beside the MinGW and Linux builds.

Issue #84; xmrig_proxy.py says what the family is. As for XMRig, the proxy's
flags.cmake replaces the MSVC Release flags with `/MT /O2 /Oi /DNDEBUG /GL`
(static CRT and whole-program optimisation), so the build type is `Corpus`
with `/MD /O2 /Oi /DNDEBUG /Zi` and the corpus link switches. libuv and
OpenSSL are built from pinned sources and linked through import libraries,
with FindOpenSSL's MSVC cache entries preset as in xmrig_msvc.py.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _stack_deps as deps
from . import _stack_vendored as vendored


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
        exclude_functions=vendored.patterns("xmrig-proxy_6.26.0_msvc"),
        build_flags="/MD /O2 /Oi /DNDEBUG /Zi (build type Corpus, without "
                    "xmrig-proxy's /MT and /GL); /DEBUG /Brepro "
                    "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link",
        notes="llhttp, rapidjson and C++ standard library functions that other families "
              "also carry, and __scrt_common_main_seh, are removed by exact name "
              "(exclude_functions, excluded_function_count; see _stack_vendored.py); the "
              "images were re-derived from the committed archives, not rebuilt. libuv and "
              "OpenSSL are linked as DLL import libraries and are not in the image.",
    ),
}
