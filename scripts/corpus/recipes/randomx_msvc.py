"""RandomX built with MSVC, beside the MinGW and Linux builds of the same tags.

Issue #18; see randomx.py for what the family is, why upstream's tree and what
the instruction-set baseline is. Upstream's CMake builds a static randomx.lib
under MSVC, with the x64 JIT's MASM source (jit_compiler_x86_static.asm,
assembled by ml64 after a PowerShell step turns configuration.h into
configuration.asm) and /arch:AVX2 on the AVX2 Argon2 unit; the 32-bit target
has neither the JIT nor the assembly. SMDA cannot read a .lib, so the archive
is linked whole into a DLL (/WHOLEARCHIVE), which exports nothing: the PDB
supplies every name. advapi32.lib is named explicitly because the library's
large-page allocator calls OpenProcessToken, AdjustTokenPrivileges and
LookupPrivilegeValueA and nothing else on the link line provides them - the
first attempt failed on exactly those three unresolved imports on both
architectures.

/MD, no /GL, /OPT:NOREF /OPT:NOICF /INCREMENTAL:NO /Brepro and /Zi with a
PDB, as every MSVC recipe in the corpus.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _stack_deps as deps


_UPSTREAM = "https://github.com/tevador/RandomX"

# CMake's Release for NMake is "/MD /O2 /Ob2 /DNDEBUG"; /Zi is added so a PDB
# exists, since MSVC keeps symbols there.
_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_CXXFLAGS = '-DCMAKE_CXX_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'

_LINK = ("link /nologo /DLL /OUT:build-{arch}\\randomx.dll "
         "/PDB:build-{arch}\\randomx.pdb " + deps.MSVC_LINK + " "
         "/WHOLEARCHIVE:build-{arch}\\randomx.lib build-{arch}\\randomx.lib "
         "advapi32.lib")


def _randomx(version, tag):
    return Recipe(
        family="RandomX",
        version=version,
        upstream=_UPSTREAM,
        license="BSD-3-Clause",
        source=Source(git_url=_UPSTREAM + ".git", git_ref=tag),
        build=[
            BuildStep('cmake -S . -B build-{arch} -G "NMake Makefiles" '
                      "-DCMAKE_BUILD_TYPE=Release -DARCH=default "
                      + _CFLAGS + " " + _CXXFLAGS),
            BuildStep("cmake --build build-{arch} --target randomx"),
            BuildStep(_LINK),
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/randomx.dll",
                            component="randomx.dll",
                            pdb="build-{arch}/randomx.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Zi (CMake Release, /Zi added), ARCH=default "
                    "(/arch:AVX2 on the AVX2 Argon2 unit, x64 only); "
                    "/DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at "
                    "link",
    )


RECIPES = {
    "RandomX_1.2.1_msvc": _randomx("1.2.1", "v1.2.1"),
    "RandomX_2.0.1_msvc": _randomx("2.0.1", "v2.0.1"),
}
