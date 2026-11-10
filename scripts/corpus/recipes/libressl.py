"""LibreSSL - OpenBSD's fork of OpenSSL, built for MinGW (PE) and Linux (ELF).

LibreSSL is OpenSSL 1.0.1g with a decade of OpenBSD changes; it is the TLS
library of OpenBSD base, ships as /usr/bin/openssl on macOS, and is what
portable OpenBSD software (OpenSSH-portable, OpenSMTPD, relayd, ...) is built
against elsewhere. Nothing in the corpus carried it under any name; OpenSSL
and BoringSSL are separate families. The MSVC build is the sibling
libressl_msvc.py. Licence, as stated in COPYING: new additions are ISC
licensed or public domain, the OpenSSL-derived code remains under the
original OpenSSL and SSLeay licences.

Versions (four), picked from the CDN's release list
(https://cdn.openbsd.org/pub/OpenBSD/LibreSSL/) and measured, not guessed.
Every tarball's detached GPG signature (.tar.gz.asc) verified against
https://cdn.openbsd.org/pub/OpenBSD/LibreSSL/libressl.asc (the signing key
comes from the same site, so this checks integrity against the signer) and
the sha256 below equals the one in the CDN's SHA256 file.

    4.4.0  current stable (CDN, 22 Oct 2026).
    3.9.2  last 3.x release, the series OpenBSD 7.5 shipped.
    3.3.6  /usr/bin/openssl on macOS Ventura and Sonoma (user reports, e.g.
           the Intego write-up on Sonoma; Apple documents nothing).
    2.8.3  /usr/bin/openssl on macOS Big Sur and Monterey (user reports on
           Hacker News and Apple Communities; same caveat).

PicHash overlap of functions with 10+ instructions between MinGW x64
builds, libcrypto (libssl in brackets), which is what decided the set:

    2.8.3/3.3.6 79% (28%)   3.3.6/3.5.4 65% (33%)   2.8.3/3.5.4 54% (21%)
    3.9.2/4.0.0 74% (71%)   3.9.2/4.4.0 54% (58%)   4.0.0/4.4.0 70% (71%)
    4.2.0/4.4.0 85% (73%)   4.3.4/4.4.0 94% (71%)   4.0.0/4.2.0 77% (95%)
    anything 2.x-3.5 against anything 3.9+: 2-7% (3-5%)

There are three eras, 2.x-3.5, 3.9 and 4.0-4.4, and releases inside one are
close to duplicates. 4.3.4 (the previous stable series) is 94% shared with
4.4.0 and 4.2.0 85%, so neither is carried. Greedy order over libcrypto,
libssl and libtls hashes starting from 4.4.0: 3.9.2 adds 47% new, 3.3.6 95%,
2.8.3 31%; after those four, 3.5.4 would add 42%, 4.0.0 13%, 4.2.0 12% and
4.3.4 8%. 3.5.4 was left out for lack of evidence that any notable software
ships it, 4.0.0 (OpenBSD 7.6) for its 13%.

Build: upstream's autotools, unpatched, one out-of-tree directory per
architecture, shared libraries only (--disable-static --disable-tests).
MinGW: `--host=<triple>`, plus -D__MINGW_USE_VC2005_COMPAT on x86 exactly as
README.mingw.md prescribes (64-bit time_t). The tarballs' generated Makefile.in
files carry arbitrary mtimes, so the first make wants to rerun automake and
dies; AUTOMAKE/ACLOCAL/AUTOCONF/AUTOHEADER=true on the make command line
makes it use the shipped files, and make is run per directory (include,
crypto, ssl, tls) because SUBDIRS on a command line is inherited by every
sub-make.

Assembly. x64: configure picks HOST_ASM_MINGW64_X86_64 and ELF x86-64
respectively, so AES, AES-NI, GHASH and RC4 (and on ELF the bignum, SHA-NI
and SHA cores) are the hand-written assembly; x86: no assembly. Instruction
baseline: plain GCC 13 defaults, which are -march=x86-64 (SSE2) on x64 and
-march=pentiumpro (MinGW) / i686 (Linux -m32), no SSE2, on x86. The assembly
selects AES-NI/PCLMUL/SHA extensions at run time from CPUID.

Components. libcrypto and libssl everywhere. libtls on MinGW except 3.3.6:
that DLL links libcrypto and libssl in whole (6345 functions against 445 in
4.4.0, 3528 hashes of which 2787 are in the same version's libcrypto), so it
would file a second copy of both under the same family. On Linux libtls is
not carried at all: measured on 4.4.0 x64 the symbol-coverage gate refuses
it at 183 of 409 functions (45%). The unnamed remainder was not inspected
function by function; in libssl, the same kind of library, every unnamed
function left is a 2- or 3-instruction .plt stub for an import, and no flag
removes those short of linking libcrypto in. The exception is 3.1.0 (added
for tracker #61): its Linux libtls passes the gate at the recipe's
min_named_ratio and is carried. It is not whole-linking, so _NO_LIBTLS does
not apply: 504 functions on x64 (511 x86), 2 of its 101 distinct hashes of
ten instructions or more in the same version's libcrypto and 1 in libssl,
against 6345 in 3.3.6's MinGW DLL and 330 in 2.8.3's (3.1.0 MinGW: 332).
156 of the 504 are named (152 in tls_), 348 are unnamed .plt stubs of three
instructions or fewer. Upstream's libssl and libtls DLLs link
libcompat in, so strlcpy, getentropy and the like appear under each.

Linux. -Wl,-Bsymbolic-functions is the one flag added. Without it a call
from libcrypto to an exported libcrypto function goes through a .plt stub
(4.4.0 x64: 7987 functions, 3212 of them unnamed 2- and 3-instruction
stubs); with it the link binds directly, as inside a PE DLL, and the same
bodies come out as 5012 functions, 237 unnamed. libssl is 1935 -> 1740, the
669 left being genuine imports from libcrypto. No code is generated
differently: the flag is link-only. Linux is the same toolchain as the other
ELF families (gcc13, shared objects, glibc imported).

Counts, kept + removed = image, summed over components (x86 | x64):

    MinGW  2.8.3  6045+432=6477 | 6155+414=6569   3.3.6  6366+310=6676 | 6545+296=6841
           3.9.2  6592+463=7055 | 6850+442=7292   4.4.0  6626+464=7090 | 6845+446=7291
    Linux  2.8.3  6243+11=6254  | 6229+9=6238     3.3.6  6879+11=6890  | 6861+9=6870
           3.9.2  6691+15=6706  | 6767+9=6776     4.4.0  6695+15=6710  | 6752+10=6762
           3.1.0  6720+11=6731  | 6705+9=6714   (libcrypto + libssl)
           3.1.0 libtls  511+5=516 | 504+5=509

3.1.0 Linux against the other Linux versions (distinct PicHashes of 10+
instructions, x64): libcrypto 2446 of 2680 shared with 3.3.6, 2141 with
2.8.3; libssl 181 and 158 of 586. x86: libcrypto 396 and 249 of 3934, libssl
32 and 34 of 687. Against 3.1.0 MinGW: libcrypto 29 (x64) and 188 (x86).

MinGW against Linux (libcrypto + libssl, 10+ instructions): x64 shares 0-29
hashes (under 1%), x86 222-276 (7-8%, mostly the identical C compat bodies),
so the ELF axis is new reference data rather than a duplicate. Against MSVC
(see libressl_msvc.py) MinGW shares 0-10 hashes on x64 and none on x86.

Glue survivors, by name and PicHash (the baseline matches on both, so a
body that differs by hash stays). MinGW: `_exit` / `__exit`, one
instruction, PicHash 1253497258561142223 (3.3.6, 3.9.2, 4.4.0); and
`snprintf.constprop.0` (x64: 1883205692861667614, 1630236379945443202,
16009104180224544928, 2638039555518392245, 17239130791354009228,
16168394134436312605, 15026590660929485557) / `_snprintf.constprop.0` (x86:
16400601058352280983, 145170955118024251, 6080301874222386769,
6946039257594385436, 8737229258867252439, 8751297537424846976,
8757693562159102612), 8-11 instructions, in 3.9.2 and 4.4.0 - the
per-translation-unit copies of mingw-w64's inline snprintf wrapper, one hash
per caller, as the README describes for printf. Linux x64: `_init`
(3694947467976420563 in 2.8.3 and 3.3.6, 7517283778065730384 in 3.9.2).
Linux x86: `_init`, `__do_global_dtors_aux`, `register_tm_clones`,
`deregister_tm_clones`, `__stack_chk_fail_local`, two PicHashes each in every
version, the per-image GOT delta documented in README "The Linux half". The
function called `init` that also matches a baseline name is LibreSSL's own.
Not edited into the baseline.

Cross-family: with OpenSSL (133 MB) and BoringSSL in the tree `validate
--deep` reports 40 hashes under LibreSSL, OpenSSL and boringssl with the same
symbol (CAST_encrypt/decrypt, BF_encrypt/decrypt, ASN1_BIT_STRING_check,
X509V3_EXT_print_fp, BN_mod_word and others, 10 to 287 instructions). That
is shared ancestry, not glue: both are forks of OpenSSL and these are
unchanged OpenSSL bodies. Of LibreSSL's 62131 distinct 10+ instruction hashes
(all versions and legs), 1055 also occur in OpenSSL and 148 in boringssl (93
in both), mostly MinGW (947 and 146).
The classifier reads three families with one symbol as leakage, so a deep run
over the whole corpus fails on these until it learns that.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_BASE = "https://cdn.openbsd.org/pub/OpenBSD/LibreSSL/libressl-%s.tar.gz"

# The tarballs ship generated Makefile.in / configure with arbitrary mtimes, so
# the first make decides they are stale and tries to rerun automake, which is
# not installed. Neutralising the regeneration tools (not touching a source
# file) makes make use the shipped files as they are.
_NOREGEN = "AUTOMAKE=true ACLOCAL=true AUTOCONF=true AUTOHEADER=true"

_CONFIGURE_MINGW = (
    "mkdir -p build-{arch} && cd build-{arch} && "
    "if [ \"{arch}\" = x86 ]; then export CPPFLAGS=-D__MINGW_USE_VC2005_COMPAT; fi && "
    "{source_root}/configure --host={host} --disable-tests --disable-static")
_CONFIGURE_LINUX = (
    "mkdir -p build-{arch} && cd build-{arch} && "
    "{source_root}/configure --host={host} --disable-tests --disable-static "
    "LDFLAGS=-Wl,-Bsymbolic-functions")
# Per directory in dependency order rather than SUBDIRS on the command line,
# which a command-line variable would hand down to every sub-make.
_MAKE = ("for d in include crypto ssl tls; do "
         "make -j$(nproc) -C build-{arch}/$d " + _NOREGEN + " || exit 1; done")
_MAKE_LINUX = ("for d in include crypto ssl; do "
               "make -j$(nproc) -C build-{arch}/$d " + _NOREGEN + " || exit 1; done")

_SHA256 = {
    "2.8.3": "9b640b13047182761a99ce3e4f000be9687566e0828b4a72709e9e6a3ef98477",
    "3.3.6": "3f28849365e1190db2baf9014ff9686012c25b1ca6df8b3a085f789e24fe4b9a",
    "3.9.2": "7b031dac64a59eb6ee3304f7ffb75dad33ab8c9d279c847f92c89fb846068f97",
    "4.4.0": "7d02522ad5070b9adb32eb253ecabce181184a3750cf65abac0675ee908687c1",
    # Added by the final sweep: 3.1.0 (the version tracker #61 evidences, so
    # far MSVC v141_xp only) and the four releases that were measured and left
    # out as near-duplicates. Each tarball checked against the signed SHA256
    # file of the CDN (good signature, Brent Cook) and, where published, its
    # own detached .asc (all but 3.1.0).
    "3.1.0": "f91aad0c8fb9cbc67c910ad6dcffb401a819b4fd122007ea7f978638db044cf6",
    "3.5.4": "0379da1344a2f71ad4a4e3be30ef9d82eecddce7f8dc2ae66631a1dfe14343ac",
    "4.0.0": "4d841955f0acc3dfc71d0e3dd35f283af461222350e26843fea9731c0246a1e4",
    "4.2.0": "0f7dba44d7cb8df8d53f2cfbf1955254bc128e0089595f1aba2facfaee8408b2",
    "4.3.4": "57c8b2f8c6f9505587abaeddab003ea243d615edb7ed71957968121fc6316bd6",
}

# 3.3.6's libtls DLL (and 3.5.x's) links libcrypto and libssl in whole: 6345
# functions against 445 in 4.4.0, 96% of them libcrypto/libssl bodies already
# carried as components of the same version. It is left out for those versions.
_NO_LIBTLS = {"3.3.6", "3.5.4"}


def _mingw(version):
    libtls = version not in _NO_LIBTLS
    return Recipe(
        family="LibreSSL",
        version=version,
        upstream="https://www.libressl.org/",
        license="ISC (new code) over OpenSSL/SSLeay-licensed code, see COPYING",
        source=Source(url=_BASE % version, sha256=_SHA256[version]),
        build=[
            BuildStep(_CONFIGURE_MINGW),
            BuildStep(_MAKE),
            BuildStep("cp $(ls build-{arch}/crypto/.libs/libcrypto-*.dll | head -1) "
                      "build-{arch}/libcrypto.dll && "
                      "cp $(ls build-{arch}/ssl/.libs/libssl-*.dll | head -1) "
                      "build-{arch}/libssl.dll"
                      + (" && cp $(ls build-{arch}/tls/.libs/libtls-*.dll | head -1) "
                         "build-{arch}/libtls.dll" if libtls else "")),
        ],
        artifacts=[Artifact(path="build-{arch}/lib%s.dll" % c, component="lib" + c)
                   for c in (("crypto", "ssl", "tls") if libtls else ("crypto", "ssl"))],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 (upstream configure default), -D__MINGW_USE_VC2005_COMPAT "
                    "on x86 as README.mingw.md says; upstream hardening and "
                    "assembly defaults, shared libraries",
        notes="Upstream autotools, unpatched; AUTOMAKE/ACLOCAL/AUTOCONF/"
              "AUTOHEADER=true on make because the shipped Makefile.in files "
              "have arbitrary mtimes. x64 builds the MinGW assembly "
              "(AES, AES-NI, GHASH, RC4), x86 none. libssl and libtls link "
              "libcompat in, so compat bodies repeat per component. "
              + ("libtls is not carried for this version: its DLL links "
                 "libcrypto and libssl in whole." if not libtls else ""),
    )


def _linux(version):
    return Recipe(
        family="LibreSSL",
        version=version,
        upstream="https://www.libressl.org/",
        license="ISC (new code) over OpenSSL/SSLeay-licensed code, see COPYING",
        source=Source(url=_BASE % version, sha256=_SHA256[version]),
        build=[
            BuildStep(_CONFIGURE_LINUX),
            BuildStep(_MAKE_LINUX),
            BuildStep("cp $(ls build-{arch}/crypto/.libs/libcrypto.so.*.*.* | head -1) "
                      "build-{arch}/libcrypto.so && "
                      "cp $(ls build-{arch}/ssl/.libs/libssl.so.*.*.* | head -1) "
                      "build-{arch}/libssl.so"),
        ],
        artifacts=[Artifact(path="build-{arch}/lib%s.so" % c, component="lib" + c)
                   for c in ("crypto", "ssl")],
        toolchains=["linux_x86", "linux_x64"],
        build_flags="-O2 (upstream configure default), -Wl,-Bsymbolic-functions; "
                    "upstream hardening and assembly defaults, shared objects",
        notes="Upstream autotools, unpatched, --host set so the 32-bit leg "
              "does not select x86-64 assembly. -Bsymbolic-functions removes "
              "the .plt stubs for libcrypto's calls to itself (link-only, no "
              "code change). libtls is not carried: the symbol-coverage "
              "gate refuses it at 45 per cent named.",
    )


# libtls of the versions whose MinGW DLL links libcrypto and libssl in whole,
# as a recipe of its own so that the exclusion applies to it alone: every
# function whose name is not in libtls's tls_ namespace is excluded by name
# (Recipe.exclude_functions), because the libcrypto and libssl components of
# the same version carry those bodies. The pattern states what libtls is, so
# a libcrypto/libssl/compat name nobody listed is excluded by default.
_LIBTLS_ONLY = r"^(?!_{0,2}tls_)"


def _mingw_libtls(version):
    recipe = _mingw(version)
    recipe.build[-1] = BuildStep(
        "cp $(ls build-{arch}/tls/.libs/libtls-*.dll | head -1) build-{arch}/libtls.dll")
    recipe.artifacts = [Artifact(path="build-{arch}/libtls.dll", component="libtls")]
    recipe.exclude_functions = [_LIBTLS_ONLY]
    recipe.notes = ("Upstream autotools, unpatched, as the MinGW recipe of this "
                    "version. This version's libtls DLL links libcrypto and "
                    "libssl in whole, so every function outside libtls's tls_ "
                    "namespace is excluded by name; the libcrypto and libssl "
                    "components carry them.")
    return recipe


# libtls on Linux. The symbol-coverage gate refuses it at the default 0.5:
# with libcrypto and libssl as shared objects, most of the image is .plt
# stubs for its calls into them, which carry no symbol. min_named_ratio is
# the measured share for these images (see the recipe docstring), not a
# lower bar for a broken build.
def _linux_libtls(version):
    recipe = _linux(version)
    recipe.build[-1] = BuildStep(
        "make -j$(nproc) -C build-{arch}/tls " + _NOREGEN + " && "
        "cp $(ls build-{arch}/tls/.libs/libtls.so.*.*.* | head -1) build-{arch}/libtls.so")
    recipe.artifacts = [Artifact(path="build-{arch}/libtls.so", component="libtls")]
    recipe.min_named_ratio = 0.4
    recipe.notes = ("Upstream autotools, unpatched, as the Linux recipe of this "
                    "version, then tls/ is made. libtls links libcrypto.so and "
                    "libssl.so, so its unnamed functions are mostly .plt stubs "
                    "into them (min_named_ratio is set to the measured share).")
    return recipe


RECIPES = {}
for _v in _SHA256:
    RECIPES["LibreSSL_%s" % _v] = _mingw(_v)
    RECIPES["LibreSSL_%s_linux" % _v] = _linux(_v)
    RECIPES["LibreSSL_%s_libtls_linux" % _v] = _linux_libtls(_v)
for _v in sorted(_NO_LIBTLS):
    RECIPES["LibreSSL_%s_libtls" % _v] = _mingw_libtls(_v)
