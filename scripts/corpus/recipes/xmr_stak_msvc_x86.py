"""xmr-stak 2.10.8 built with MSVC for x86, beside the MSVC x64 image
(xmr_stak_msvc.py, untouched).

Backlog issue #63. The image is built from a recipe-patched tree, so it is NOT
byte-identical to a build of unmodified upstream, and it is an UNSUPPORTED
configuration: upstream refuses to compile 32-bit (cryptonight_aesni.h:52
`#error You are trying to do a 32-bit build. This will all end in tears. I
know it.`) and has never been built or run that way. The unpatched MSVC x86
build fails in MASM on the 64-bit main loops
(`error A2006: undefined symbol : r11`, then r8, rbp, r9, ... in
cryptonight_v8_main_loop_ivybridge_win64.inc). It is kept for reference-
function coverage (the C code, the Keccak/Blake/Groestl/JH/Skein, the soft-AES
CryptoNight paths and the network/config code compile as 32-bit). It is the
counterpart of the MinGW x86 image in xmr_stak_mingw.py, which needed the same
changes.

Configuration is xmr_stak_msvc.py's: CPU backend only, OpenSSL from the pinned
source through its import libraries, NMake Release `/MD /O2 /Ob2 /DNDEBUG /Zi`,
XMR-STAK_COMPILE=generic, link `/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF
/OPT:NOICF`. Only the x86 toolchain is declared, so the x64 recipe and its data
are not touched.

Patches applied by the recipe to the build tree by
scripts/corpus/exercisers/xmr_stak_msvc_x86_patch.py (the pinned checkout is
never committed or modified in the repo):

1. cryptonight_aesni.h: the line
       #error You are trying to do a 32-bit build. This will all end in tears. I know it.
   is deleted, and the five `#ifdef _WIN64` (the Win32 includes at line 27 and
   the VirtualAlloc/VirtualProtect/FlushInstructionCache branches at
   1228-1261) become `#ifdef _WIN32`, because _WIN64 is undefined on x86.
2. The two MASM sources, asm/cryptonight_v8_main_loop.asm and
   asm/cnR/CryptonightR_template.asm, are overwritten in the build tree with
   generated stubs: `.386 / .model flat, C / .code`, then for every symbol the
   original PUBLIC-declares (directly or through its INCLUDEd *_win.inc) (3 main loops and 536 CryptonightR_*/
   CryptonightWOW_* template labels, 539 in all)
       name PROC / ret / name ENDP
   They carry no information, have no counterpart in a real build, and nothing
   runs them. CMake still assembles them with ml.exe as upstream's MSVC branch
   does.
3. xmr_stak_msvc_x86_compat.h is copied to the source root and force-included
   in C++ translation units with `/FI`. MSVC declares _umul128, _addcarry_u64,
   _subborrow_u64, _mm_cvtsi64_si128 and _mm_cvtsi128_si64 for x64 only. The
   header defines each as a plain-C xs_ function (the 128-bit multiply from
   four 32x32->64 partial products, the same product as the MinGW x86 build's)
   and points the upstream spelling at it with a macro.

Counts (CI run 42416031824): 4800 kept + 1845 removed as runtime = 6645. 539 of
the kept functions are the generated one-instruction `ret` stubs (names
containing CryptonightR_, CryptonightWOW_ or mainloop; none has ten
instructions); 1854 kept functions have ten instructions or more, 1410 distinct
PicHashes. Overlap (PicHashes of functions of ten instructions or more): 0 with
MSVC x64 (1346), 0 with MinGW x86 (637), 0 with MinGW x64 (633) and 0 with
Linux x64 (659).
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _stack_deps as deps

_FI = "/FIxs_msvc_x86_compat.h"

_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          "-DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 "
          '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi" '
          '-DCMAKE_CXX_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi ' + _FI + '" '
          '-DCMAKE_EXE_LINKER_FLAGS_RELEASE="%s" '
          "-DXMR-STAK_COMPILE=generic -DCUDA_ENABLE=OFF -DOpenCL_ENABLE=OFF "
          "-DMICROHTTPD_ENABLE=OFF -DHWLOC_ENABLE=OFF %s"
          % (deps.MSVC_LINK, deps.msvc_dep_options(uv=False)))

RECIPES = {
    "xmr-stak_2.10.8_msvc_x86": Recipe(
        family="xmr-stak",
        version="2.10.8",
        upstream="https://github.com/fireice-uk/xmr-stak",
        license="GPL-3.0",
        source=Source(git_url="https://github.com/fireice-uk/xmr-stak.git",
                      git_ref="2.10.8"),
        extra_sources=dict(deps.OPENSSL_ONLY),
        build=(deps.msvc_openssl() + [
            BuildStep("python {repo}/scripts/corpus/exercisers/xmr_stak_msvc_x86_patch.py ."),
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch}"),
            BuildStep("dir build-{arch}\\bin", allow_failure=True),
        ]),
        artifacts=[Artifact(path="build-{arch}/bin/xmr-stak.exe",
                            component="xmr-stak.exe",
                            pdb="build-{arch}/bin/xmr-stak.pdb")],
        toolchains=["msvc_x86"],
        build_flags="/MD /O2 /Ob2 /DNDEBUG /Zi (CMake Release, /Zi added); "
                    "/DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link; build tree "
                    "patched by the recipe (32-bit #error removed, _WIN64 -> _WIN32, MASM main "
                    "loops replaced by ret stubs, x86 compat header force-included)",
        notes="NOT byte-identical to a build of unmodified upstream: recipe-applied patch, see the "
              "recipe docstring. The x86 image is an unsupported configuration (upstream #errors on "
              "32-bit builds): its CryptoNight assembly is replaced by 539 one-instruction ret stubs.",
    ),
}
