"""Nettle built with MSVC, beside the MinGW and Linux builds of the same releases.

Nettle is autotools and GNU-assembler syntax, and upstream has no MSVC build
(its NEWS never mentions MSVC and 3.10.2's sources never test _MSC_VER). It still builds with cl, for
all five releases and both architectures, once the configure step is replaced
by what configure produces. The reasoning, and the versions and axes, are in
nettle.py; this records the Windows side.

What was read rather than assumed, and what the first two runner builds
(windows-2022, cl v143) showed:

  * configure writes config.h, version.h, config.make and the elliptic-curve
    tables; make compiles the two source lists in Makefile.in. There is no
    shell, m4 or make to run them with, and the x86 and x86_64 assembly is GNU
    as syntax through m4, so this is a C-only build (the configure option for
    that is --disable-assembler). `scripts/corpus/exercisers/nettle_msvc_build.py`
    does the steps in configure's and make's own order from the unmodified
    tree: config.h is config.h.in with every #undef resolved the way
    config.status resolves it; version.h is version.h.in with its four
    substitutions; the ecc-*.h tables come from compiling eccdata.c (it
    includes mini-gmp.c) with cl and running it with the arguments of the
    `ecc-<curve>.h: eccdata.stamp` rules in Makefile.in (checked identical,
    byte for byte, to the tables MinGW's make writes); the source lists are
    read out of Makefile.in. Everything it generates goes in gen/, outside the
    upstream files; nothing is patched. All of config.h's probes are LLP64
    Windows facts: long is 4 bytes, so mini-gmp's limb is 32 bits on x86
    and x64 alike, the same as the MinGW x64 build.
  * 2.7.1 compiles memxor.c only because configure's AC_REPLACE_FUNCS finds no
    memxor in libc (later releases list it in nettle_SOURCES), and expects a
    nettle-stdint.h that configure wrote; the helper handles both, the first
    by reading AC_REPLACE_FUNCS out of configure.ac. The first run failed at
    link on exactly this (`unresolved external symbol memxor`).
  * 4.0 uses C11 alignas through <stdalign.h>, which cl ships only under
    /std:c11 (the first run: error C2061 on `alignas` in nettle-types.h); that
    mode defines __STDC__, which hides alloca, so /D_CRT_DECLARE_NONSTDC_NAMES=1
    comes with it. Only trees whose nettle-types.h includes stdalign.h get both.
  * Flags, from the corpus mandates: /O2 /MD /Zi with an explicit /Fd, no /GL,
    no /LTCG, and at link /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF.
    /MD means the C runtime is imported rather than linked in.
  * Exports: every defined external function of the objects, from dumpbin
    /SYMBOLS, written to a .def: the rule MinGW's ld applies by default and
    lzo_msvc.py uses. 501 for libnettle and 440 for libhogweed in 3.10.2
    x64, 219 for 2.7.1.
  * libhogweed is a second DLL linked against libnettle's import library, as
    the MinGW and ELF ones are, with one exception that cl forces. hogweed
    code refers to three data objects libnettle defines, the hash descriptors
    nettle_sha256, nettle_sha384 and nettle_sha512 (used by RSA-PSS, OAEP and
    Ed25519). A DLL can export data, but cl code reaches it only through
    __declspec(dllimport), which Nettle's headers do not carry; MinGW's ld has
    auto-import for the case and link.exe has not (the first run: LNK2001
    `unresolved external symbol nettle_sha512`). The helper links the objects
    that define what the linker reports unresolved - sha256-meta.obj,
    sha384-meta.obj and sha512-meta.obj, which hold const tables of names,
    sizes and function pointers and no code - into libhogweed, and the
    functions they point at still resolve through the import library. Those
    descriptors therefore appear in both images as data. This is the same
    obstacle mbedtls_msvc.py hit with four data references, where the answer
    was one DLL; here it is three const tables, so the component split of the
    other toolchains is kept.
  * mini-gmp is compiled into libhogweed as in the other recipes
    (--enable-mini-gmp is the MinGW and Linux equivalent): 206 (x64) and 207
    (x86) of libhogweed's 569 and 572 kept functions in 3.10.2 are its
    mpz_*/mpn_*/gmp_* functions.

Counts, kept + removed = image total (removed is the baseline's measured MSVC
runtime: DllMain and the static vcruntime startup _DllMainCRTStartup,
__scrt_*, __castguard_*; SEH and GS-cookie helpers; and import thunks for CRT
and kernel32 functions such as malloc, free, memcpy, strlen, fprintf, time):

    version arch  libnettle              libhogweed
    2.7.1   x86   264 + 137 = 401         -
    2.7.1   x64   264 + 137 = 401         -
    3.4.1   x86   433 + 137 = 570         499 + 153 = 652
    3.4.1   x64   433 + 138 = 571         497 + 143 = 640
    3.7.3   x86   529 + 137 = 666         549 + 153 = 702
    3.7.3   x64   528 + 139 = 667         547 + 143 = 690
    3.10.2  x86   648 + 138 = 786         572 + 153 = 725
    3.10.2  x64   647 + 139 = 786         569 + 143 = 712
    4.0     x86   685 + 138 = 823         536 + 151 = 687
    4.0     x64   684 + 139 = 823         534 + 141 = 675

PicHash overlap of the 10+ instruction functions, per release, over libnettle
and libhogweed together (MSVC against MinGW / MSVC against Linux), x86: 0 / 0
for every release; x64: 2.7.1 0 / 0, 3.4.1 1 / 0, 3.7.3 to 4.0 1 / 0. The
MSVC build shares nothing worth the name with either GCC build: it is C only,
where they use Nettle's assembly for AES, SHA, memxor, ECC and (from 3.7.3 on
x86_64) the fat-build dispatch. The images are larger for the same reason:
3.10.2 x64 libnettle is 786 functions here against 663 on MinGW.

Glue survivors, by name and PicHash: _wassert (x64) / __wassert (x86), the
one-instruction import thunk for the CRT's assert, PicHash
1253497258561142223, in every artefact (it is below the cross-family
instruction floor, and the baseline does not carry it). No other named runtime
function survives. The names `ibcrypt$+0x5d1`, `_nettle_ecc_mod_random$+0x40`,
`mpn_base_power_of_two_p$+0x75`, `nettle_sexp_transport_iterator_first$+0x13a`
and `mpz_sizeinbase$+0x145` are PDB names of the form name$+offset: pieces of
Nettle and mini-gmp functions, not runtime.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from .nettle import _LICENSE, _LICENSES, _UPSTREAM, _VERSIONS


_BUILD = ("python {repo}/scripts/corpus/exercisers/nettle_msvc_build.py "
          "--arch {arch}")


def _recipe(version):
    sha256, _, pe_hogweed, _ = _VERSIONS[version]
    hogweed = pe_hogweed is not None
    artifacts = [Artifact(path="libnettle.dll", component="libnettle.dll",
                          pdb="libnettle.pdb")]
    if hogweed:
        artifacts.append(Artifact(path="libhogweed.dll",
                                  component="libhogweed.dll",
                                  pdb="libhogweed.pdb"))
    return Recipe(
        family="Nettle",
        version=version,
        upstream=_UPSTREAM,
        license=_LICENSES.get(version, _LICENSE),
        source=Source(url="https://ftp.gnu.org/gnu/nettle/nettle-%s.tar.gz" % version,
                      sha256=sha256),
        build=[BuildStep(_BUILD + ("" if hogweed else " --no-hogweed")),
               BuildStep("dir", allow_failure=True)],
        artifacts=artifacts,
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi, C only (no assembler), config.h and the ecc "
                    "tables generated from config.h.in and eccdata.c; /DEBUG "
                    "/Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link; "
                    "exports generated from the objects"
                    + ("; /std:c11 for 4.0" if version == "4.0" else ""),
        notes="No configure run: nettle_msvc_build.py reproduces its outputs "
              "and compiles the source lists from Makefile.in with cl, "
              "unpatched. C only, so none of Nettle's x86/x86_64 assembly or "
              "fat dispatch is present. "
              + ("libhogweed carries mini-gmp (about a third of it) and the "
                 "three const hash descriptors it cannot import from "
                 "libnettle; " if hogweed else
                 "No libhogweed: this release has no mini-gmp option; ")
              + "built against the DLL runtime, so the MSVC C runtime stays "
                "attributed to data/MSVC. Pinned by the sha256 of a "
                "GPG-verified release tarball.",
    )


RECIPES = {"Nettle_%s_msvc" % version: _recipe(version) for version in _VERSIONS}
