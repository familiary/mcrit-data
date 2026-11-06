"""Nettle - the GNU low-level cryptographic library, MinGW and Linux ELF.

Nettle is the crypto backend of GnuTLS and so ships in most Linux
distributions (Debian packages 2.7.1 in jessie, 3.4.1 in buster, 3.7.3 in
bullseye, 3.8.1 in bookworm, 3.10.1 in trixie, per sources.debian.org). No
Nettle was in the corpus under any name. This module is the MinGW and Linux
half; nettle_msvc.py is the MSVC half and carries the Windows-specific
reasoning. Upstream: https://git.lysator.liu.se/nettle/nettle, releases at
https://ftp.gnu.org/gnu/nettle/.

Sources. The release tarballs from ftp.gnu.org, pinned by sha256. Each
tarball's detached .sig verified (gpgv, GNU keyring from
https://ftp.gnu.org/gnu/gnu-keyring.gpg) as a good signature by Niels Moller
<nisse@lysator.liu.se>, RSA key 343C2FF0FBEE5EC2EDBEF399F3599FF828C67298; the
pinned sha256 values are of those verified tarballs.

Versions, and why these five. Built and measured on the way in: 2.7.1, 3.4.1,
3.7.3, 3.9.1, 3.10.2 and 4.0. PicHash overlap of the functions with 10 or more
instructions, as a share of the smaller image, on MinGW x64 (MinGW x86 in
brackets; the Linux x64 numbers are within a few points of the MinGW x64 ones):

    2.7.1 vs 3.4.1   21% (41)     3.7.3 vs 3.10.2  80% (82)
    3.4.1 vs 3.7.3   60% (61)     3.10.2 vs 4.0    65% (64)
    3.7.3 vs 3.9.1   84% (87)     3.9.1 vs 3.10.2  91% (91)

  * 2.7.1 (2013-05-28): the oldest release packaged by a Debian release
    that is still in use as a base image (jessie). 12-21% shared with every
    later release on x64, so it is a different code base. Its public-key
    code needs GMP and this release has no mini-gmp option, so it is
    libnettle only (--disable-public-key).
  * 3.4.1 (2018-12-04): Debian buster. Its NEWS makes the RSA private-key
    operations side-channel silent through GMP's mpn_sec_* family and adds
    rsa_sec_decrypt, so its hogweed code differs from earlier releases. 38-60% shared
    with the releases after it.
  * 3.7.3 (2021-06-07): Debian bullseye. Its NEWS: a bugfix release for RSA
    decryption functions that could crash on invalid ciphertext input
    ("upgrading ... is strongly recommended"). 80% shared with 3.10.2, kept
    because it is the Debian bullseye generation and the other 20% is more
    than a hundred functions; the cut for dropping a release is 90% (3.9.1).
  * 3.10.2 (2025-06-26): the last 3.x. Debian trixie ships 3.10.1; 3.10.2 is
    a maintenance release of it.
  * 4.0 (2026-02-05): the new major version. Its NEWS: SLH-DSA, new sonames,
    the *_digest functions no longer take a size, smaller context structs;
    65% shared with 3.10.2.
  * 3.9.1 was built, measured and left out: 91% of its functions share a
    PicHash with 3.10.2 on both MinGW architectures, as 1.10.1 was left out
    of libpcap against 1.10.5 (there at 77-80%). On Linux x86 every version pair
    shares only 6-12% because 32-bit PIC bodies carry a per-image GOT delta
    (see the README, "The Linux half"), so the near-duplicate test was read
    off the x64 and MinGW numbers.

Axes, measured rather than assumed.

  * MinGW x86 and x64 (mingw_x86, mingw_x64): the default axis.
  * Linux ELF x86 and x64 (linux_x86, linux_x64), the host gcc 13: Nettle is
    distributed through the Linux distributions (versions above), and the PicHash overlap of the
    10+ instruction functions between a MinGW and a Linux artefact of the
    same release is 0 or 1 on x64 for every version (the Microsoft and System
    V calling conventions differ) and 16-64 on x86, about 9-10% of the
    MinGW side's 10+ instruction functions and 6.5-7% of the Linux side's.
    The two are different reference data.
  * MSVC x86 and x64: nettle_msvc.py. Autotools and GNU as syntax would
    suggest cl cannot build it; the C sources can, with the configure step
    replaced by a script that does what configure does, and it builds for all
    five versions and both architectures. Overlap with MinGW is 0 on x86 and
    0-1 on x64, with Linux 0. The assembler is the reason it is distinct:
    MinGW and Linux x64 use Nettle's x86_64 assembly (AES, SHA, ECC, ...
    plus the fat-build CPU dispatch from 3.7.3 on), MSVC is C only.
  * Not built: macOS/Mach-O (no Darwin toolchain on the host, none faked).
    Non-fat x86_64 builds and the AES-NI / SHA-NI / PCLMUL assembly variants
    are not separate axes: configure's --enable-fat is on by default from 3.7.3
    (3.4.1 defaults to off and was built that way) and puts all of those
    paths in one image with a CPUID dispatch, so the default build already
    contains them.

Hogweed and GMP. libhogweed (RSA, DSA, ECDSA, EdDSA, curves) needs GMP, and
the choice is between linking libgmp, which this host does not have and which
cl cannot build, and --enable-mini-gmp, Nettle's own supported GMP-free mode
with mini-gmp.c from the tarball compiled into libhogweed. mini-gmp is built
for every leg, so the three toolchains describe the same configuration. The
cost, measured on 3.10.2: 166 (MinGW x64), 178 (MinGW x86), 188 (Linux, both
architectures) and 206-207 (MSVC) of libhogweed's functions are mini-gmp's
mpz_*/mpn_*/gmp_* (about a third of the PE images' kept functions); they are
attributed to Nettle because they are in the Nettle tarball and in the
artefact, and there is no GMP family for them to collide with. A hogweed
linked against libgmp.so does not contain them and shares only the
remaining two thirds. libnettle is unaffected. 2.7.1 has no
hogweed here for the reason above.

Build. Upstream's configure, out of tree, one build directory per
architecture, shared libraries only, no documentation, no OpenSSL glue, `make
SUBDIRS=` so the testsuite, tools and examples are not built. Nothing is
patched. On Linux the artefact is libnettle.so as make leaves it (the
versioned names are symlinks that only `make install` creates), built with the
host's own -O2 and upstream's -ggdb3. A shared object keeps glibc out of the
image, so no libc body is filed under Nettle; the exported API is reached
through .plt stubs inside the image, which are unnamed and 2-3 instructions
long (367 of 987 functions in 3.10.2 libnettle x64, 570 of 1074 in libhogweed;
at least 10 instructions: 1 and 2 unnamed). That is what a distribution's
libnettle.so looks like, so no -fvisibility flag is added.

Counts, kept + removed = image total (removed is the baseline's measured
compiler runtime):

    version toolchain arch  libnettle              libhogweed
    2.7.1   MinGW   x86   215 + 117 = 332         -
    2.7.1   MinGW   x64   217 + 111 = 328         -
    2.7.1   Linux   x86   449 + 6 = 455           -
    2.7.1   Linux   x64   345 + 5 = 350           -
    3.4.1   MinGW   x86   367 + 118 = 485         428 + 116 = 544
    3.4.1   MinGW   x64   363 + 112 = 475         430 + 110 = 540
    3.4.1   Linux   x86   713 + 6 = 719           960 + 5 = 965
    3.4.1   Linux   x64   562 + 6 = 568           706 + 5 = 711
    3.7.3   MinGW   x86   440 + 119 = 559         477 + 116 = 593
    3.7.3   MinGW   x64   448 + 115 = 563         477 + 110 = 587
    3.7.3   Linux   x86   868 + 6 = 874           1043 + 5 = 1048
    3.7.3   Linux   x64   826 + 5 = 831           1034 + 5 = 1039
    3.10.2  MinGW   x86   523 + 119 = 642         502 + 116 = 618
    3.10.2  MinGW   x64   548 + 115 = 663         503 + 110 = 613
    3.10.2  Linux   x86   1009 + 6 = 1015         1083 + 5 = 1088
    3.10.2  Linux   x64   987 + 5 = 992           1074 + 5 = 1079
    4.0     MinGW   x86   555 + 119 = 674         467 + 116 = 583
    4.0     MinGW   x64   589 + 115 = 704         468 + 110 = 578
    4.0     Linux   x86   1075 + 6 = 1081         994 + 5 = 999
    4.0     Linux   x64   1058 + 5 = 1063         983 + 5 = 988

(The MSVC counts are in nettle_msvc.py.)

Glue survivors, by name and PicHash. Every named function in the MinGW
artefacts is defined in the Nettle (or mini-gmp) source of its release; no
named runtime function survives there. What does:

  * MinGW, unnamed, libgcc's ___chkstk_ms: one per artefact, 15 instructions,
    PicHash 12578432865501340970 (x64) and 16132965489037543538 (x86). The
    x64 one was confirmed against the DLL's symbol table at its address; the
    libpcap recipe records the same unnamed stack probe. The baseline cannot
    match it because the report carries no name for it.
  * MinGW x64, unnamed, 29 and 254 instructions, and nothing else. The 29
    instruction one (PicHash 16807672506518420961, 2.7.1 and 3.4.1, and the
    same hash in the Linux x64 artefacts of those releases) is a call target
    inside nettle_salsa20_crypt's assembly, located in a rebuilt 2.7.1. The
    254 instruction one (PicHash 8091049778495821724, 3.7.3 and later) is a
    file-local function of streebog.c, located at a streebog_table
    reference in 3.10.2. Both are Nettle's.
  * Linux x86, named, the 32-bit PIC glue the README ("The Linux half")
    documents: __do_global_dtors_aux (21 instructions), deregister_tm_clones
    (18), register_tm_clones (26) and __stack_chk_fail_local (5) in every
    x86 artefact, and _fini (7) in libnettle, each with a per-image PicHash.
  * Linux x86 and x64, unnamed regions of 10 or more instructions: 0-4 per
    artefact on x86 (11 to 2,746 instructions), 0-4 on x64 in libhogweed and
    1 in libnettle. On x86 these are the .plt, which SMDA reads as functions;
    checked for the two in 3.7.3 libnettle x86 (1,178 and 2,746 instructions,
    at 0x8720 and 0x8a00, inside .plt 0x8020-0x8ba0). The rest are the same
    kind of region and were not each located. None carries a Nettle name,
    and all are specific to their image.

Cross-family check. `validate --deep` over Nettle with libtomcrypt, libsodium,
mbedTLS and wolfSSL checked out: 6 shared PicHashes at 10 instructions or
more, 0 leakage. Those with Nettle in them are the ___chkstk_ms probes above
(PicHashes 12578432865501340970 and 16132965489037543538, 15 instructions,
unnamed, shared with all four of the others) and short-body coincidences with
different names (11 to 13 instructions, e.g. _nettle_arctwo_set_key_gutmann
against _crypto_kdf_hkdf_sha256_extract_update and _sha256_wrap; mbedTLS's
*_init functions against nettle_sha3_init, nettle_dsa_params_init and others).
No Nettle function shares a PicHash with another family under the same name.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_UPSTREAM = "https://git.lysator.liu.se/nettle/nettle"
_LICENSE = ("LGPL-3.0-or-later OR GPL-2.0-or-later (dual: LGPLv3+ or GPLv2+, "
            "licensee's choice; 2.7.1 and 3.4.1 are LGPL-2.1-or-later and "
            "GPL-2.0-or-later)")

# Upstream's own configure, out of tree, one build directory per architecture.
_COMMON = ("--enable-shared --disable-static --disable-documentation "
           "--disable-openssl")
_CONFIGURE_PE = ("mkdir -p build-{arch} && cd build-{arch} && "
                 "{source_root}/configure --host={host} " + _COMMON)
_CONFIGURE_ELF = ("mkdir -p build-{arch} && cd build-{arch} && "
                  "{source_root}/configure " + _COMMON)
# SUBDIRS= keeps make to the libraries: tools, testsuite and examples are
# programs this corpus does not use, and the testsuite is most of the time.
_MAKE = "make -j$(nproc) SUBDIRS="

# version -> (sha256, libnettle PE, libhogweed PE, fat is configure's default)
# The Windows file names are what upstream's configure.ac gives the shared
# libraries (LIBNETTLE_MAJOR/MINOR, LIBHOGWEED_MAJOR/MINOR); 2.7.1 puts the
# minor in the name too, and has no mini-gmp option, so no hogweed here.
_VERSIONS = {
    "2.7.1": ("bc71ebd43435537d767799e414fce88e521b7278d48c860651216e1fc6555b40",
              "libnettle-4-7.dll", None, False),
    "3.4.1": ("f941cf1535cd5d1819be5ccae5babef01f6db611f9b5a777bae9c7604b8a92ad",
              "libnettle-6.dll", "libhogweed-4.dll", False),
    "3.7.3": ("661f5eb03f048a3b924c3a8ad2515d4068e40f67e774e8a26827658007e3bcf0",
              "libnettle-8.dll", "libhogweed-6.dll", True),
    "3.10.2": ("fe9ff51cb1f2abb5e65a6b8c10a92da0ab5ab6eaf26e7fc2b675c45f1fb519b5",
               "libnettle-8.dll", "libhogweed-6.dll", True),
    "4.0": ("3addbc00da01846b232fb3bc453538ea5468da43033f21bb345cb1e9073f5094",
            "libnettle-9.dll", "libhogweed-7.dll", True),
}

# Licence as the release states it, read in the source: 2.7.1's README names
# the LGPL with COPYING.LIB (version 2.1) and aes-set-encrypt-key.c says
# "version 2.1 of the License, or (at your option) any later version"; sha1.c
# of 3.4.1, 3.7.3, 3.10.2 and 4.0 offers either the LGPL version 3 or later or
# the GPL version 2 or later, and 3.10.2's mini-gmp.c (FSF copyright, "part of
# the GNU MP Library") offers the same two.
_LICENSES = {
    "2.7.1": "LGPL-2.1-or-later",
}
_LICENSE = "LGPL-3.0-or-later OR GPL-2.0-or-later"


def _recipe(version, linux):
    sha256, pe_nettle, pe_hogweed, fat = _VERSIONS[version]
    hogweed = pe_hogweed is not None
    option = " --enable-mini-gmp" if hogweed else " --disable-public-key"
    configure = (_CONFIGURE_ELF if linux else _CONFIGURE_PE) + option
    # make leaves the shared object as libnettle.so; the versioned names are
    # symlinks that only `make install` creates.
    artifacts = [Artifact(path="build-{arch}/" + ("libnettle.so" if linux else pe_nettle),
                          component="libnettle.so" if linux else "libnettle.dll")]
    if hogweed:
        artifacts.append(Artifact(
            path="build-{arch}/" + ("libhogweed.so" if linux else pe_hogweed),
            component="libhogweed.so" if linux else "libhogweed.dll"))
    return Recipe(
        family="Nettle",
        version=version,
        upstream=_UPSTREAM,
        license=_LICENSES.get(version, _LICENSE),
        source=Source(url="https://ftp.gnu.org/gnu/nettle/nettle-%s.tar.gz" % version,
                      sha256=sha256),
        build=[BuildStep(configure),
               BuildStep(_MAKE, cwd="build-{arch}")],
        artifacts=artifacts,
        toolchains=["linux_x86", "linux_x64"] if linux else ["mingw_x86", "mingw_x64"],
        build_flags="-O2 -ggdb3 (the toolchain's -O2, upstream's -ggdb3), upstream "
                    "configure defaults with the architecture's assembly"
                    + ((", fat build on x86_64 (configure default)" if fat
                        else ", non-fat (configure default)") if hogweed or fat
                       else "")
                    + (", --enable-mini-gmp" if hogweed else
                       ", --disable-public-key"),
        notes=("Shared libraries from upstream's configure, unpatched. "
               + ("libhogweed is built with --enable-mini-gmp, so about a third of "
                  "it is mini-gmp's own mpz_*/mpn_*/gmp_* code (see the recipe "
                  "docstring); " if hogweed else
                  "This release has no mini-gmp option, so there is no "
                  "libhogweed; ")
               + ("the ELF images keep their exported API behind unnamed .plt "
                  "stubs and carry the documented 32-bit PIC glue on x86."
                  if linux else
                  "libgcc's unnamed ___chkstk_ms survives the baseline.")
               + " Pinned by the sha256 of a GPG-verified release tarball."),
    )


RECIPES = {}
for _version in _VERSIONS:
    RECIPES["Nettle_%s" % _version] = _recipe(_version, linux=False)
    RECIPES["Nettle_%s_linux" % _version] = _recipe(_version, linux=True)
