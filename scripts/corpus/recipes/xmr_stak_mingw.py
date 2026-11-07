"""xmr-stak 2.10.8 built with MinGW-w64, x64 and x86, beside the Linux ELF and
the MSVC x64 image.

Backlog issue #63. xmr_stak.py says what is built. These two images need a
recipe-applied patch of the build tree, so they are NOT byte-identical to a
build of unmodified upstream. The x86 image is also an UNSUPPORTED
configuration: upstream refuses to compile 32-bit (`#error You are trying to
do a 32-bit build. This will all end in tears.`, cryptonight_aesni.h:52) and
has never been built or run that way. It is kept for reference-function
coverage (the C code, the Keccak/Blake/Groestl/JH/Skein, the soft-AES
CryptoNight paths and the network/config code compile as 32-bit).

Configuration is the Linux recipe's: CPU backend only (CUDA, OpenCL,
libmicrohttpd and hwloc off), OpenSSL 3.5.8 from the pinned source linked as
a DLL import library, XMR-STAK_COMPILE=generic (no -march=native), CMake
Release (-O3 -DNDEBUG). CMAKE_LINK_STATIC is off upstream, so no link wrapper
is needed.

No-source-change shims. `deps-<arch>/stakhdr` is passed with -isystem. It holds
lower-case aliases for <WinSock2.h> (home_dir.hpp) and <Shlobj.h>, which a
case-sensitive cross-build cannot resolve, and a three-line <byteswap.h>
(bswap_32/64 as __builtin_bswap32/64): jext.hpp falls through to
`#include <byteswap.h>`, a glibc header, for every compiler that is not MSVC,
Apple, Sun or a BSD.

Patches applied by the recipe to the build tree (the pinned checkout is never
committed or modified in the repo):

1. Both architectures, cryptonight_aesni.h: the local function is renamed.
       -static inline uint64_t _umul128(uint64_t a, uint64_t b, uint64_t* hi)
       +static inline uint64_t xs_umul128(uint64_t a, uint64_t b, uint64_t* hi)
       -		lo = _umul128(idx0, cl, &hi);
       +		lo = xs_umul128(idx0, cl, &hi);
   (`sed 's/\b_umul128(/xs_umul128(/g'`; those are the only two occurrences.)
   Reason: mingw-w64 declares `_umul128` extern, upstream defines it static,
   so GCC stops with "declared 'extern' and later 'static'". A define does not
   remove the prototype and would rename it too. The body is unchanged.
2. Both architectures, CMakeLists.txt: `sed 's/-Wl,-z,noexecstack //'` (two
   lines, 495-496). It is an ELF linker option; the MinGW ld rejects it
   ("unrecognized option '-z'").
3. x86 only, cryptonight_aesni.h:
   - the line `#error You are trying to do a 32-bit build...` is deleted;
   - `#ifdef _WIN64` becomes `#ifdef _WIN32` (the Win32 includes at line 27
     and the VirtualAlloc/VirtualProtect/FlushInstructionCache branches at
     1228-1261; _WIN64 is undefined on i686);
   - xs_umul128's `unsigned __int128` body (no __int128 on i686) is replaced
     by the same 64x64->128 product from four 32x32->64 partial products.
4. x86 only, assembly: the main loops are 64-bit Intel-syntax gas
   (cryptonight_v8_main_loop.S and cnR/CryptonightR_template.S), which cannot
   assemble for i686. Both files are overwritten in the build tree with
   generated stubs, `.globl _name` / `_name: ret`, one per symbol upstream
   exports (3 main loops from the .S; the 525 `CryptonightR_*` and
   `CryptonightWOW_*` template labels read from CryptonightR_template.h).
   They are 64-bit-only stubs: 528 one-instruction `ret` functions (names
   containing CryptonightR_, CryptonightWOW_ or mainloop) in the x86 image,
   with no counterpart in a real build; they carry no information and
   share three PicHashes among themselves. Nothing runs them.
   On x64 the real .S files are assembled, but they are the SysV (Linux) ABI
   versions (`mov rcx, rdi`), which upstream's CMake selects for every
   non-MSVC compiler; a MinGW x64 image would call them with the Windows
   convention, so they would not run correctly. This is upstream's CMake
   choice, left as is, and does not affect the disassembly.

Force-included header (scripts/corpus/exercisers/xmr_stak_x86_compat.h, x86
only, `-include`): GCC's headers have no 64-bit-register intrinsics on i686,
and cryptonight_aesni.h uses _mm_cvtsi64_si128, _mm_cvtsi128_si64,
_addcarry_u64 and _subborrow_u64. The header defines them in plain C.

Counts (kept / removed as runtime / total): x64 1123 / 167 / 1290; x86 1964 /
172 / 2136. The x86 count includes the 528 stubs above and ~167 import
thunks; 637 x86 functions have ten instructions or more.

Overlap (PicHashes of functions of ten instructions or more): MinGW x64 shares
3 with Linux x64 (633 / 659) and 0 with MSVC x64 (1346); MinGW x86 shares 0
with MinGW x64, Linux x64 and MSVC x64. Surviving glue names in both:
`__mingw_has_sse` and `__dynamic_cast` (underscore-prefixed once more on
x86) and, on x86, `___register_frame_info`; they pass the glue baseline
because the baseline does not list them.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _stack_deps as deps

_SRC = "xmrstak/backend/cpu/crypto/cryptonight_aesni.h"

_CONFIG = ("-DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DXMR-STAK_COMPILE=generic "
           "-DCUDA_ENABLE=OFF -DOpenCL_ENABLE=OFF -DMICROHTTPD_ENABLE=OFF "
           "-DHWLOC_ENABLE=OFF")

_SHIM = BuildStep(
    "rm -rf deps-{arch}/stakhdr && mkdir -p deps-{arch}/stakhdr && "
    "ln -s /usr/{host}/include/winsock2.h deps-{arch}/stakhdr/WinSock2.h && "
    "ln -s /usr/{host}/include/shlobj.h deps-{arch}/stakhdr/Shlobj.h && "
    "printf '#pragma once\\n#define bswap_32(x) __builtin_bswap32(x)\\n"
    "#define bswap_64(x) __builtin_bswap64(x)\\n' > deps-{arch}/stakhdr/byteswap.h")

_PATCH = BuildStep(
    "sed -i -e 's/\\b_umul128(/xs_umul128(/g' " + _SRC
    + " && sed -i -e 's/-Wl,-z,noexecstack //' CMakeLists.txt")

_ASM = "xmrstak/backend/cpu/crypto/asm"

# 32-bit only. The body replaces the 128-bit multiply (no __int128 on i686)
# with the same product from four 32x32->64 partial products.
_UMUL32 = (
    "python3 -c \"import re,sys;p=sys.argv[1];s=open(p).read();"
    "a='unsigned __int128 r = (unsigned __int128)a * (unsigned __int128)b;';"
    "assert a in s;"
    "s=s.replace(a,'uint64_t al=(uint32_t)a,ah=a>>32,bl=(uint32_t)b,bh=b>>32;"
    "uint64_t ll=al*bl,lh=al*bh,hl=ah*bl,hh=ah*bh;"
    "uint64_t mid=(ll>>32)+(uint32_t)lh+(uint32_t)hl;"
    "*hi=hh+(lh>>32)+(hl>>32)+(mid>>32);return (ll&0xffffffffu)|(mid<<32);');"
    "s=s.replace('*hi = r >> 64;','').replace('return (uint64_t)r;','');"
    "open(p,'w').write(s)\" " + _SRC)

_PATCH_X86 = BuildStep(
    "if [ {bitness} = 32 ]; then "
    "sed -i -e '/#error You are trying to do a 32-bit build/d' "
    "-e 's/#ifdef _WIN64/#ifdef _WIN32/' " + _SRC + " && " + _UMUL32 + " && "
    "{ printf '.text\\n'; for f in cryptonight_v8_mainloop_ivybridge_asm "
    "cryptonight_v8_mainloop_ryzen_asm cryptonight_v8_double_mainloop_sandybridge_asm; do "
    "printf '.globl _%s\\n_%s:\\n\\tret\\n' $f $f; done; } > " + _ASM + "/cryptonight_v8_main_loop.S && "
    "{ printf '.text\\n'; for f in $(grep -o 'void [A-Za-z0-9_]*()' " + _ASM
    + "/cnR/CryptonightR_template.h | sed 's/void //;s/()//'); do "
    "printf '.globl _%s\\n_%s:\\n\\tret\\n' $f $f; done; } > " + _ASM + "/cnR/CryptonightR_template.S; fi")

_FLAGS = ('-DCMAKE_C_FLAGS="-isystem $PWD/deps-{arch}/stakhdr" '
          '-DCMAKE_CXX_FLAGS="-isystem $PWD/deps-{arch}/stakhdr $([ {bitness} = 32 ] && '
          'echo -include {repo}/scripts/corpus/exercisers/xmr_stak_x86_compat.h)"')

RECIPES = {
    "xmr-stak_2.10.8_mingw": Recipe(
        family="xmr-stak",
        version="2.10.8",
        upstream="https://github.com/fireice-uk/xmr-stak",
        license="GPL-3.0",
        source=Source(git_url="https://github.com/fireice-uk/xmr-stak.git",
                      git_ref="2.10.8"),
        extra_sources=dict(deps.OPENSSL_ONLY),
        build=(deps.mingw_openssl() + [
            _SHIM, _PATCH, _PATCH_X86,
            BuildStep(
                "cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
                "-DCMAKE_SYSTEM_PROCESSOR={platform} -DCMAKE_C_COMPILER={cc} "
                "-DCMAKE_CXX_COMPILER={cxx} -DCMAKE_RC_COMPILER={windres} "
                "-DCMAKE_FIND_ROOT_PATH=/usr/{host} " + _CONFIG + " "
                + deps.mingw_dep_options(uv=False) + " " + _FLAGS,
                env={"CFLAGS": "", "CXXFLAGS": ""}),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ]),
        artifacts=[Artifact(path="build-{arch}/bin/xmr-stak.exe",
                            component="xmr-stak.exe")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 -DNDEBUG (CMake Release), -msse2 -maes; build tree patched by the recipe "
                    "(_umul128 renamed, -Wl,-z,noexecstack removed; x86 also: 32-bit #error removed, "
                    "_WIN64 -> _WIN32, 32-bit umul128, x86 compat header, asm stubs)",
        notes="NOT byte-identical to a build of unmodified upstream: recipe-applied patch, see the "
              "recipe docstring. The x86 image is an unsupported configuration (upstream #errors on "
              "32-bit builds): its CryptoNight assembly is replaced by 528 one-instruction ret stubs.",
    ),
}
