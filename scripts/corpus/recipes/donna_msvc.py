"""ed25519-donna and curve25519-donna built with MSVC, beside the MinGW and
Linux builds of the same two commits (donna.py).

MinGW and MSVC compile the same source to different machine code, so a donna
linked into a cl-built sample matches the MinGW reference data on nothing.
Measured on the artefacts below, against the MinGW ones of donna.py: 0 shared
PicHashes at ten instructions or more in every pairing, on both architectures
(ed25519-donna 75 MSVC against 33 MinGW on x86 and 73 against 31 on x64; the
SSE2 builds 84 against 34 and 81 against 34; curve25519-donna 17 against 8 and
17 against 7). That is what this module is for.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh. Both families live here, as in donna.py,
because they share a build shape: a handful of C files compiled with cl
straight into a DLL, no build system.

What the premise got wrong, established by building rather than assumed. The
expectation was that cl could build only the generic 32-bit field code,
because the x64 field code uses `__int128` and the SSE2 variant uses GCC
inline asm. Neither holds, and neither needed a patch:

  * ed25519-donna-portable.h has a full COMPILER_MSVC branch. It defines
    `uint128_t` as a lo/hi struct over `_umul128`, `__shiftright128` and
    `__shiftleft128`, `DONNA_INLINE` as `__forceinline`, and `ALIGN` as
    `__declspec(align)`. So on x64 cl takes the same ED25519_64BIT path GCC
    takes, not the 32-bit code. Checked in the artefact rather than inferred
    from the header: the x64 report contains `curve25519_mul_noinline` and
    `U8TO64_LE`, which exist only in curve25519-donna-64bit.h and under
    HAVE_UINT128, and the x86 one does not.
  * The inline asm is not reached. Every `__asm__` block in the tree is
    behind ED25519_GCC_64BIT_X86_CHOOSE, ED25519_GCC_64BIT_32BIT_CHOOSE,
    ED25519_GCC_32BIT_SSE_CHOOSE or ED25519_GCC_64BIT_SSE_CHOOSE, and
    ed25519-donna.h defines each only under COMPILER_GCC. cl therefore gets
    the portable C `ge25519_scalarmult_base_choose_niels` (552 instructions
    on x64) where the MinGW builds carry the assembly one. The SSE2 field
    arithmetic itself (`curve25519-donna-sse2.h`) is written with emmintrin
    intrinsics, not asm, so `-DED25519_SSE2` builds on both x86 and x64 and
    is a genuinely different code shape: 30 of 75 PicHashes shared with the
    generic build on x86 and 26 of 73 on x64.
  * cl compiled all of it with no diagnostics at all (the build logs show the
    file names and nothing else), at the default /W1.

So all three ed25519-donna variants donna.py builds are built here, and for
the same reason as there: the SSE2 build is the likelier one on x86 and
upstream's own benchmark prefers the 64-bit generic one on x64.

What cl cannot build, measured on the runner (windows-2022, MSVC 14.3):

  * agl/curve25519-donna `curve25519-donna-c64.c`, on x86 and on x64 alike:
    97 diagnostics before `fatal error C1003: error count exceeds 100`, the
    first being
        curve25519-donna-c64.c(33): error C2061: syntax error: identifier
        '__attribute__'
    at `typedef unsigned uint128_t __attribute__((mode(TI)))`, followed by
    C2059 at the same line, then C2143/C2059/C2091 at line 39 where
    `static inline void force_inline` expands to `__attribute__((
    always_inline))`, and a cascade of C2065 (`t` undeclared) through line
    246. The file has no MSVC branch, unlike the ed25519-donna tree.
    `/Dinline=__inline` does not change the first error. It is not patched,
    and it was a one-function file under GCC anyway (see the README's table).
    Recorded there.
  * Nothing else failed. `-DED25519_FORCE_32BIT` on x64 also compiles (compile
    only, not linked, not built as an artefact): it is not a component for
    the reason donna.py gives, nothing recommends it.

Flags, each read back from the build log the tracker keeps rather than
assumed (`$ (.) cl /nologo /c /O2 /MD /Zi /Fded25519-donna.pdb
/DED25519_REFHASH /DED25519_CUSTOMRANDOM  /I. /Foobj-generic\\ ed25519.c
<rng>` and `link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF
/OPT:NOICF /DEF:<def> /PDB:... /OUT:...`):

  * /O2, the level the rest of the corpus uses, which cl documents as
    /Og /Oi /Ot /Oy /Ob2 /Gs /GF /Gy. It does not imply /GL, and neither /GL
    nor /LTCG is passed: whole-program optimisation would fold the static
    helpers into their callers across translation units, which is not how a
    sample that vendors these files compiles them.
  * /MD, not cl's default /MT: a static CRT put 1947 of VX-API's 4219
    functions into that artefact, duplicating data/MSVC. The runtime stays
    imported, and the 124 to 131 functions removed below are the thin
    start-up and security glue every DLL still carries.
  * /Zi with /Fd and a matching link /PDB, so the PDB carries the names
    (without one SMDA recovers nothing by name).
  * /Brepro for a build-time-independent hash; /INCREMENTAL:NO because /DEBUG
    implies /INCREMENTAL and /OPT:NO* does not suppress it, which would put a
    jump-thunk table in front of every function; /OPT:NOREF /OPT:NOICF, so
    nothing unreferenced is dropped and no two identical bodies are folded -
    stated rather than left to /DEBUG's implication, and comparable with the
    MinGW builds, which fold nothing either. /OPT:REF and /OPT:ICF are off.
  * -DED25519_REFHASH and -DED25519_CUSTOMRANDOM exactly as donna.py, and for
    the same reasons (upstream's reference SHA-512 rather than a libcrypto
    dependency; the consumer-supplied `ed25519_randombytes_unsafe`, which is
    donna.py's `scripts/corpus/exercisers/ed25519_donna_rng.c` stub, outside
    the upstream tree). On x86 it is 6 instructions and on x64 3, under the
    ten-instruction floor, and it is the one function in the artefact that is
    not upstream's. ED25519_SUFFIX is not set. Optimisation level: one,
    -O2; donna.py measured how much that matters and the finding carries over
    in kind if not in number.

Exports. A MinGW DLL exports every global symbol; link.exe exports only what
it is told, and neither donna tree has a `__declspec(dllexport)` anywhere.
The exports come from two .def files in scripts/corpus/exercisers, beside the
rng stub and so outside the upstream tree: `ed25519_donna.def` lists the
public API of ed25519.h (`ed25519_publickey`, `ed25519_sign`,
`ed25519_sign_open`, `ed25519_sign_open_batch`, `curved25519_scalarmult_basepoint`
and the `ed25519_randombytes_unsafe` hook), which is every non-static
function in ed25519.c, and `curve25519_donna.def` lists `curve25519_donna`.
(The header declares `curved25519_scalarmult_basepoint` - with the d - and
that is the spelling exported.) No upstream file is touched. An export list
does not decide the function count: SMDA recovers names from the PDB, and the
unexported static helpers are named in it.

Counts, kept + removed = image total. "Removed" is the baseline's MSVC
runtime filter (corpus.baseline), the glue every DLL linked with /MD carries:
`_DllMainCRTStartup` and the `dllmain_*` and `__scrt_*` start-up, `__security_
*`, `__GSHandlerCheck`, `__castguard_*`, `_guard_*`, `__chkstk`, `_RTC_*`,
`__C_specific_handler` and the Win32 import thunks (`GetCurrentProcess`,
`QueryPerformanceCounter`, ...), plus `memcpy` and `memset` (and `memcmp` on
x64), which are thunks into the DLL runtime.

    artefact                        kept  removed  image  >=10 instr
    ed25519-donna.dll        x86      80      127    207      77
                             x64      81      131    212      75
    ed25519-donna-sse2.dll   x86      90      127    217      85
                             x64      90      131    221      82
    curve25519-donna.dll     x86      20      124    144      17
                             x64      20      129    149      17

Survivors: none. All 381 kept functions across the six artefacts have a name,
and every one of those names occurs as an identifier in the donna sources, so
there is no unnamed function and no MSVC runtime function left in a report to
list by name and PicHash.

curve25519-donna is not thin here. Under GCC the 32-bit file keeps 6 to 7
separate functions because `curve25519_donna` absorbs the rest (donna.py);
cl keeps 20 on both architectures - `cmult`, `crecip`, `fcontract`,
`fexpand`, `fmonty`, `fproduct` (406 instructions on x64), `fsquare_inner`
and the rest, with `curve25519_donna` itself 76 instructions - of which 17
are ten instructions or more. That clears the floor of eight by its own
count, so `min_functions` is not set here.

Existing coverage. data/cryptopp 8.9.0 carries Crypto++'s C++ port of part of
ed25519-donna, and it has an MSVC build. Against it, PicHashes at ten
instructions or more shared with this module's MSVC artefacts: ed25519-donna
12 of 75 on x86 and 10 of 73 on x64 (`add256_modm`, `contract256_slidingwindow_
modm`, `contract256_window4_modm`, `curve25519_contract`, `curve25519_sub`,
`curve25519_pow_two5mtwo0_two250mtwo0`, `curve25519_square_times`, ...), the
SSE2 build 5 of 84 and 5 of 81 (the modm routines), curve25519-donna none.
Against Crypto++'s MinGW build the MSVC artefacts share none, and the MinGW
donna artefacts share 12 of 33 and 9 of 31 with it - the compiler, not the
library, decides which of the two Crypto++ builds a donna function matches.
So Crypto++'s MSVC build already recognises about a sixth of an MSVC-built
ed25519-donna (the modm and field arithmetic), and this fills in the rest:
the public API, `ge25519_pack`, `ge25519_unpack_negative_vartime`, the hash,
and the whole of agl's curve25519-donna.

Not covered: the 64-bit curve25519-donna (above), the -O3 and -Os builds,
Mach-O, and a stripped sample. These artefacts carry names from a PDB.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_ED_COMMIT = "8757bd4cd209cb032853ece0ce413f122eef212c"
_CV_COMMIT = "28772f37a4b8a57ab9439b9e79b19f9abee686da"

# Outside the upstream tree, like the rng stub donna.py compiles beside
# ed25519.c. {repo} is the checkout; cl and link take forward slashes.
_RNG = "{repo}/scripts/corpus/exercisers/ed25519_donna_rng.c"
_ED_DEF = "{repo}/scripts/corpus/exercisers/ed25519_donna.def"
_CV_DEF = "{repo}/scripts/corpus/exercisers/curve25519_donna.def"
_TOR_DEF = "{repo}/scripts/corpus/exercisers/ed25519_donna_tor.def"
_TOR_HASH = "{repo}/scripts/corpus/exercisers/ed25519_donna_tor_hash.h"
_TOR_DEFINES = ("/DED25519_CUSTOMHASH /DED25519_CUSTOMRANDOM "
                "/DED25519_SUFFIX=_donna "
                "/DED25519_RNG_NAME=ed25519_randombytes_unsafe_donna")

# The compile and link lines every recipe in the corpus uses for a lone
# translation unit; see sqlite3_msvc.py for the reasoning behind each flag
# and the module docstring above for what they cost here.
_CL = "cl /nologo /c /O2 /MD /Zi"
_LINK = "link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF"


def _ed_steps(name, objdir, defines):
    # ed25519.c includes every header; the rng stub is a second translation
    # unit. cl's /Fo with a trailing backslash is a directory, which has to
    # exist, hence the mkdir. Both are compiled by one cl so they share one
    # compiler PDB (/Fd), which the link then overwrites under the same name.
    return [
        BuildStep("if not exist %s mkdir %s" % (objdir, objdir)),
        BuildStep("%s /Fd%s.pdb /DED25519_REFHASH /DED25519_CUSTOMRANDOM %s"
                  "/I. /Fo%s\\ ed25519.c %s"
                  % (_CL, name, defines, objdir, _RNG)),
        BuildStep("%s /DEF:%s /PDB:%s.pdb /OUT:%s.dll "
                  "%s\\ed25519.obj %s\\ed25519_donna_rng.obj"
                  % (_LINK, _ED_DEF, name, name, objdir, objdir)),
    ]


def _tor_steps():
    # The Tor-style component: CUSTOMHASH instead of REFHASH, the _donna suffix,
    # and the digest wrapper forced in with /FI (ed25519_donna_tor_hash.h; see
    # donna.py). Not _ed_steps(): that hard-codes /DED25519_REFHASH.
    name = "ed25519-donna-tor"
    return [
        BuildStep("if not exist obj-tor mkdir obj-tor"),
        BuildStep("%s /Fd%s.pdb %s /FI%s /I{repo}/scripts/corpus/exercisers "
                  "/I. /Foobj-tor\\ ed25519.c %s"
                  % (_CL, name, _TOR_DEFINES, _TOR_HASH, _RNG)),
        BuildStep("%s /DEF:%s /PDB:%s.pdb /OUT:%s.dll "
                  "obj-tor\\ed25519.obj obj-tor\\ed25519_donna_rng.obj"
                  % (_LINK, _TOR_DEF, name, name)),
    ]


def _ed25519():
    return Recipe(
        family="ed25519-donna",
        version="2015-03-16",
        upstream="https://github.com/floodyberry/ed25519-donna",
        license="public domain, as declared in the header of each source "
                "file (Andrew M.); the repository ships no licence file",
        source=Source(git_url="https://github.com/floodyberry/ed25519-donna.git",
                      git_ref=_ED_COMMIT),
        build=(_ed_steps("ed25519-donna", "obj-generic", "")
               + _ed_steps("ed25519-donna-sse2", "obj-sse2",
                           "/DED25519_SSE2 ")
               + _tor_steps()),
        artifacts=[
            Artifact(path="ed25519-donna.dll", component="ed25519-donna.dll",
                     pdb="ed25519-donna.pdb"),
            Artifact(path="ed25519-donna-sse2.dll",
                     component="ed25519-donna-sse2.dll",
                     pdb="ed25519-donna-sse2.pdb",
                     build_flags="/O2 /MD /Zi -DED25519_SSE2 "
                                 "-DED25519_REFHASH -DED25519_CUSTOMRANDOM; "
                                 "/DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF "
                                 "/OPT:NOICF at link"),
            Artifact(path="ed25519-donna-tor.dll",
                     component="ed25519-donna-tor.dll",
                     pdb="ed25519-donna-tor.pdb",
                     build_flags="/O2 /MD /Zi -DED25519_CUSTOMHASH "
                                 "-DED25519_CUSTOMRANDOM "
                                 "-DED25519_SUFFIX=_donna; /DEBUG /Brepro "
                                 "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at "
                                 "link"),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi -DED25519_REFHASH -DED25519_CUSTOMRANDOM; "
                    "/DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at "
                    "link",
        notes="The same commit and defines as the MinGW and Linux recipes, "
              "built with cl into a DLL, once as upstream's default code for "
              "the target and once with -DED25519_SSE2. cl builds upstream's "
              "own MSVC branch: __int128 is replaced by _umul128 so x64 takes "
              "the 64-bit field code, and the SSE2 variant uses intrinsics; "
              "the GCC inline-asm ge25519_scalarmult_base_choose_niels is "
              "not compiled (it is behind COMPILER_GCC), so cl gets the C "
              "version. No upstream file is patched. Exports come from "
              "scripts/corpus/exercisers/ed25519_donna.def, because the "
              "source declares none. ed25519_randombytes_unsafe is the stub "
              "from scripts/corpus/exercisers and must never run. Measured "
              "against the MinGW artefacts: no PicHash of ten instructions "
              "or more is shared on either architecture; against data/"
              "cryptopp 8.9.0 MSVC, 12 of 75 (x86) and 10 of 73 (x64). "
              "Built against the DLL runtime, so the MSVC C runtime is "
              "imported and stays attributed to data/MSVC.",
    )


def _curve25519():
    name = "curve25519-donna"
    return Recipe(
        family="curve25519-donna",
        version="1.3",
        upstream="https://github.com/agl/curve25519-donna",
        license="BSD-3-Clause, Copyright 2008 Google Inc.",
        source=Source(git_url="https://github.com/agl/curve25519-donna.git",
                      git_ref=_CV_COMMIT),
        build=[BuildStep("%s /Fd%s.pdb /Fo%s.obj curve25519-donna.c"
                         % (_CL, name, name)),
               BuildStep("%s /DEF:%s /PDB:%s.pdb /OUT:%s.dll %s.obj"
                         % (_LINK, _CV_DEF, name, name, name))],
        artifacts=[Artifact(path="curve25519-donna.dll",
                            component="curve25519-donna.dll",
                            pdb="curve25519-donna.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi; /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF "
                    "/OPT:NOICF at link",
        notes="Tag 1.3, the 32-bit curve25519-donna.c, built with cl. Not "
              "thin under MSVC: 20 functions are kept on both architectures "
              "(17 of ten instructions or more), all of them the project's, "
              "against 6 to 7 under GCC, which folds the rest into "
              "curve25519_donna. The 64-bit curve25519-donna-c64.c is not "
              "built: it does not compile with cl (C2061 on its "
              "__attribute__((mode(TI))) typedef, 97 diagnostics). Export "
              "from scripts/corpus/exercisers/curve25519_donna.def. No "
              "PicHash of ten instructions or more is shared with the "
              "MinGW artefact, with ed25519-donna or with Crypto++.",
    )


RECIPES = {
    "ed25519-donna_2015-03-16_msvc": _ed25519(),
    "curve25519-donna_1.3_msvc": _curve25519(),
}
