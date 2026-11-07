"""xmr-stak 2.10.8 built with MSVC (x64 only), beside the Linux ELF.

Issue #63; xmr_stak.py says what is built and why there is no x86. CMake's own
MSVC Release is already `/MD /O2 /Ob2 /DNDEBUG`, so only /Zi is added; the
CMake minimum of 3.4 is lifted with CMAKE_POLICY_VERSION_MINIMUM=3.5 because a
CMake 4 refuses anything below 3.5. The CryptoNight main loops are MASM
(xmr-stak-asm), assembled by ml64. OpenSSL is built from the pinned source and
linked through its import libraries, with FindOpenSSL's MSVC cache entries
preset as in xmrig_msvc.py. 4101 functions after 1834 removed as runtime.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _stack_deps as deps


# CMake's Release for NMake is already "/MD /O2 /Ob2 /DNDEBUG"; /Zi is added.
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          "-DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 "
          '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi" '
          '-DCMAKE_CXX_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi" '
          '-DCMAKE_EXE_LINKER_FLAGS_RELEASE="%s" '
          "-DXMR-STAK_COMPILE=generic -DCUDA_ENABLE=OFF -DOpenCL_ENABLE=OFF "
          "-DMICROHTTPD_ENABLE=OFF -DHWLOC_ENABLE=OFF %s"
          % (deps.MSVC_LINK, deps.msvc_dep_options(uv=False)))

RECIPES = {
    "xmr-stak_2.10.8_msvc": Recipe(
        family="xmr-stak",
        version="2.10.8",
        upstream="https://github.com/fireice-uk/xmr-stak",
        license="GPL-3.0",
        source=Source(git_url="https://github.com/fireice-uk/xmr-stak.git",
                      git_ref="2.10.8"),
        extra_sources=dict(deps.OPENSSL_ONLY),
        build=(deps.msvc_openssl() + [
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch}"),
            BuildStep("dir build-{arch}\\bin", allow_failure=True),
        ]),
        artifacts=[Artifact(path="build-{arch}/bin/xmr-stak.exe",
                            component="xmr-stak.exe",
                            pdb="build-{arch}/bin/xmr-stak.pdb")],
        toolchains=["msvc_x64"],
        build_flags="/MD /O2 /Ob2 /DNDEBUG /Zi (CMake Release, /Zi added); "
                    "/DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF "
                    "at link",
    ),
}
