"""libgcrypt - the GnuPG project's general-purpose crypto library.

The cryptographic core of GnuPG 2.x, also linked by systemd and cryptsetup
(optionally) and by GNOME's gcr/keyring stack. On Windows it ships as
libgcrypt-20.dll with Gpg4win, GnuPG VS-Desktop and every application that
bundles GnuPG. Nothing in the corpus covered it under any name.

Three versions, all signed release tarballs from
https://gnupg.org/ftp/gcrypt/libgcrypt/ (upstream publishes a detached .sig and
no checksum; each verified with gpg against the GnuPG release keys, the
EdDSA dist key 6DAA6E64A76D2840571B4902528897B826403ADA for all three, and the
sha256 pinned here is of the verified file):

    1.11.3  2026-04-21  the current stable branch
    1.10.4  2026-04-21  the long-term-support branch, the one distributions
                        ship (Debian 12 has 1.10.1, Ubuntu 24.04 1.10.3)
    1.8.14  2026-08-25  the last of 1.8.x, the widely embedded older line
                        (Debian 10 carries 1.8.4, Debian 11 1.8.7, Ubuntu
                        18.04 1.8.1, Ubuntu 20.04 and RHEL 8 1.8.5)

Measured, not assumed, and why each was kept or dropped. PicHash overlap of the
functions with 10 or more instructions, x64, per container:

    1.10.3 vs 1.10.4   ELF 99.3%   MinGW 99.2%   -> 1.10.3 dropped
    1.8.5  vs 1.8.14   ELF 96.7%   MinGW 95.8%   -> 1.8.5 dropped
    1.10.4 vs 1.11.3   ELF 59.4%   MinGW 67.0%   (x86 MinGW 70.4%)
    1.8.14 vs 1.10.4   ELF 40.8%   MinGW 37.2%   (x86 MinGW 41.9%)
    1.8.14 vs 1.11.3   ELF 30.2%   MinGW 33.2%   (x86 MinGW 38.2%)

1.10.3 and 1.8.5 (the versions distributions actually carry) were built for
this measurement and not committed: they are the same code as the kept
release. The three kept are at most about two thirds shared with each other,
the threshold libpcap used to keep a neighbour.

Which libgpg-error. libgcrypt imports libgpg-error, so each artefact is linked
against the paired release of the libgpg-error family, built here from the
same pinned tarball with the same configure options (see libgpg_error.py), on
the same axis: the MinGW DLLs import libgpg-error-0.dll (libgpg-error6-0.dll
on x64 for 1.35), the ELF objects NEED libgpg-error.so.0.

    1.11.3  (configure.ac NEED_GPG_ERROR_VERSION 1.49)  ->  libgpg-error 1.61
    1.10.4  (needs >= 1.27)                              ->  libgpg-error 1.61
    1.8.14  (needs >= 1.25)                              ->  libgpg-error 1.35

libgpg-error is its own family (data/libgpg-error): it is imported, not linked
into the libgcrypt artefact, so none of its functions are under this name. The
dependency is recorded in each provenance entry under "dependencies".

Shared, not static. SMDA has no COFF/ar loader, so libgcrypt.a cannot be read;
the shared object is also the form the Windows distributions and the Linux
packages ship (libgcrypt-20.dll, libgcrypt.so.20). The MinGW DLL imports
msvcrt, KERNEL32, ADVAPI32, USER32 and libgpg-error; the ELF object NEEDs glibc
and libgpg-error, so no libc body is linked in.

Axes built: MinGW x86/x64 and Linux ELF x86/x64 (gcc 13.3, glibc). They are
distinct reference data: PicHash overlap of the 10+ instruction functions
between the MinGW and the ELF artefact of the same version and architecture is

    x64  1.8.14 98 (10.5%)   1.10.4 96 (8.2%)   1.11.3 0
    x86  1.8.14 74 (8.6%)    1.10.4 87 (8.2%)   1.11.3 123 (9.9%)

of the smaller. Part of the x64 gap is the host gcc: it defaults to
-fcf-protection=full, so ELF x64 functions begin with endbr64 and MinGW's do
not. MSVC is not built: see "Targets investigated but not built" in
scripts/corpus/README.md.

Build. Upstream's own configure and make, out of tree, one directory per
architecture, assembler modules and hardware acceleration on (upstream's
default, and what a distribution package contains), no source patch.
`--disable-static --enable-shared --disable-doc`, and
`--with-libgpg-error-prefix` pointing at the paired libgpg-error built a step
earlier with PATH set so configure finds its gpgrt-config. Only the
subdirectories that make the shared object are built (compat mpi cipher random
src): doc and tests contribute nothing to it. MinGW is --host=<triple>. The
ELF build also gets --host=<cpu>-linux-gnu, and that is load-bearing for x86:
mpi/config.links chooses the assembler modules from the host, and a -m32 build
on an x86_64 machine without --host selects the amd64 .S files, which gas
rejects ("`adcq' is only supported in 64-bit mode").

Licence, as recorded upstream: the library is LGPL-2.1-or-later; the tests and
helper programs are GPL-2.0-or-later. No source from the tree is stored.

Measured on the artefacts (kept + removed = every function in the image; the
removed count is the compiler runtime the baseline recognised):

    1.8.14  x86 ELF 1395 + 6 = 1401    x64 ELF 1426 + 6 = 1432
            x86 PE  1208 + 138 = 1346  x64 PE  1358 + 132 = 1490
    1.10.4  x86 ELF 1650 + 8 = 1658    x64 ELF 1812 + 6 = 1818
            x86 PE  1451 + 139 = 1590  x64 PE  1652 + 132 = 1784
    1.11.3  x86 ELF 1854 + 8 = 1862    x64 ELF 2096 + 6 = 2102
            x86 PE  1649 + 137 = 1786  x64 PE  1942 + 130 = 2072

Named functions are 88% to 100% of every artefact (lowest: 1.8.14 x86 ELF,
1218 of 1389). The x64 DLLs carry 26 to 51 unnamed functions, 13 to 18 of
them over a thousand instructions (the largest 4278, and 5495 in 1.8.14); the
x86 DLLs, which build no amd64 modules, have 1 to 3, none over 55. That is consistent with
cipher/*-amd64.S, whose entry labels are not in the PE symbol table (nm lists
only .refptr entries for them), and those are libgcrypt's own code and stay.

Glue the baseline left in, by name and PicHash (hex, instructions in
brackets); not edited into the baseline.

  * MinGW, 1.11.3 only (it is the release that uses thread-local storage, so it
    pulls libgcc's emulated TLS in): __emutls_get_address on x64
    5fa875c9f1bc2682 (156) and ___emutls_get_address on x86 fcb4675f9c53b5d7
    (162), and the unnamed static helpers emutls_destroy, x64 964b047c100ae19f
    (24) and x86 cf0d1991e4b23478 (25), and emutls_alloc, x64 7250612fb353dc1a
    (53), matching the PicHashes recorded for libpcap. The x86 55-instruction
    unnamed body 65198615ff45cae4 is within one instruction of libpcap's
    emutls_alloc but not equal to it, and is not identified. 1.8.14 and 1.10.4
    leave nothing on the PE legs.
  * ELF x64: nothing, in all three.
  * ELF x86, every version: the crtstuff residue the README's "The Linux half"
    describes. __x86.get_pc_thunk.bp 7c99608cc56520ba, .cx 769f0aed4b5feefe and
    .si 99104660fd4df449 (2 each, identical across versions); then per version
    1.8.14 / 1.10.4 / 1.11.3: _init e61ce8a4f3c9d2ce / 5bb860f02cc69cc5 /
    f1dd827772c66db2 (11), register_tm_clones f4661b54fbc8b389 /
    f5fd1d77888292eb / a829d02088d0fa54 (26), deregister_tm_clones
    79cce8f56a9bccd6 / e6bf1ba602613a26 / eb18382b0c3dfcb2 (18),
    __do_global_dtors_aux aea7bf8bae2bd9cf / d63fc5d3297102cc /
    2487c637eb2240e4 (21), __stack_chk_fail_local f2a51fd449d7fa31 /
    c5a4c8001913d7bd / a293c53908502d4b (5), and _fini 7253a52a4cac819a /
    0df057fbb298e6db (7) in 1.10.4 and 1.11.3 only.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from .libgpg_error import configure_options as _gpgerr_options
from .libgpg_error import _BASE as _GPGERR_URL
from .libgpg_error import _SHA256 as _GPGERR_SHA256

_BASE = "https://gnupg.org/ftp/gcrypt/libgcrypt/libgcrypt-%s.tar.bz2"

_SHA256 = {
    "1.8.14": "9608d222917e3747336993a24ef9e18bf5aa6b2d35c67a13219f9172b5b84a77",
    "1.10.4": "d6d2f835a79711ceba54b53d1081d388d24fb0341d79a268a6557e12908a90a0",
    "1.11.3": "2c6d562e894b2b06eefbc427d12d51ee9d3e50e90012ad6596b4cb3e421a95f2",
    # Measured and left out as near-duplicates (1.10.3 vs 1.10.4 99.2% MinGW,
    # 1.8.5 vs 1.8.14 95.8%), carried since the final sweep, which commits
    # every image whose PicHash set is not identical to an existing one.
    # .sig verified: 1.10.3 good signatures by Werner Koch (dist signing
    # 2020) and Niibe Yutaka; 1.8.5 by Werner Koch (dist sig) and NIIBE Yutaka
    # with their expired RSA keys from keyserver.ubuntu.com.
    "1.10.3": "8b0870897ac5ac67ded568dcfadf45969cfa8a6beb0fd60af2a9eadc2a3272aa",
    "1.8.5": "3b4a2a94cb637eff5bdebbcaf46f4d95c4f25206f459809339cdada0eb577ac3",
}
_SO = {"1.8.14": "20.2.15", "1.10.4": "20.4.4", "1.11.3": "20.6.1",
       "1.10.3": "20.4.3", "1.8.5": "20.2.5"}
# libgcrypt version -> the libgpg-error it is built against.
PAIRING = {"1.8.14": "1.35", "1.10.4": "1.61", "1.11.3": "1.61",
           "1.10.3": "1.61", "1.8.5": "1.35"}

# Subdirectories of the top-level Makefile.am minus doc and tests: neither
# contributes to the shared object.
_SUBDIRS = 'SUBDIRS="compat mpi cipher random src"'


def _recipe(version, linux):
    err = PAIRING[version]
    # The MinGW dependency is cross-built and needs the triple. The ELF one
    # is built natively (CC carries -m32 for the 32-bit leg), but libgcrypt
    # itself must be given the triple on both: mpi/config.links picks the
    # assembler modules from the host, and without --host a -m32 build on an
    # x86_64 machine selects the amd64 .S files, which gas rejects in 32-bit
    # mode ("`adcq' is only supported in 64-bit mode").
    host = "" if linux else "--host={host} "
    gcrypt_host = "--host={host} "
    # libgpg-error is built (not just fetched) beside libgcrypt, shared, so the
    # artefact imports it rather than containing it - libgpg-error is its own
    # family. gpgrt-config is found through PATH, which is how libgcrypt's
    # AM_PATH_GPG_ERROR looks for it when the prefix is not a system one.
    deps = ("tar xjf {gpg_error} && mkdir -p ge-{arch} && cd ge-{arch} && "
            "../libgpg-error-%s/configure %s--prefix=$PWD/inst %s && "
            "make -j$(nproc) && make -C src install") % (err, host, _gpgerr_options(err))
    configure = ("mkdir -p build-{arch} && cd build-{arch} && "
                 "PATH=$PWD/../ge-{arch}/inst/bin:$PATH "
                 "{source_root}/configure %s--disable-static --enable-shared "
                 "--disable-doc --with-libgpg-error-prefix=$PWD/../ge-{arch}/inst"
                 % gcrypt_host)
    if linux:
        artifact = Artifact(path="build-{arch}/src/.libs/libgcrypt.so.%s" % _SO[version],
                            component="libgcrypt.so")
        toolchains = ["linux_x86", "linux_x64"]
    else:
        artifact = Artifact(path="build-{arch}/src/.libs/libgcrypt-20.dll",
                            component="libgcrypt-20.dll")
        toolchains = ["mingw_x86", "mingw_x64"]
    return Recipe(
        family="libgcrypt",
        version=version,
        upstream="https://gnupg.org/software/libgcrypt/",
        license="LGPL-2.1-or-later (library), GPL-2.0-or-later (tests and tools)",
        source=Source(url=_BASE % version, sha256=_SHA256[version]),
        extra_sources={"gpg_error": Source(url=_GPGERR_URL % err,
                                           sha256=_GPGERR_SHA256[err])},
        build=[BuildStep(deps), BuildStep(configure),
               BuildStep("make -j$(nproc) " + _SUBDIRS, cwd="build-{arch}")],
        artifacts=[artifact],
        toolchains=toolchains,
        build_flags="-O2, shared, upstream configure defaults otherwise "
                    "(assembler modules, jitter entropy and hardware "
                    "acceleration on)",
        notes="Shared libgcrypt, "
              + ("the glibc build (native gcc, -m32 for x86)" if linux else
                 "the MinGW-w64 build") + " of the signed GnuPG release "
              "tarball, assembler modules and hardware acceleration on "
              "(upstream's default). Links the paired libgpg-error %s, "
              "built from a pinned tarball in the same recipe and not "
              "contained in the artefact: it is the libgpg-error family. "
              "Only compat, mpi, cipher, random and src are built. See the "
              "module docstring for versions, pairing and glue left in by "
              "the baseline." % err,
    )


RECIPES = {}
for _v in _SHA256:
    RECIPES["libgcrypt_%s" % _v] = _recipe(_v, linux=False)
    RECIPES["libgcrypt_%s_linux" % _v] = _recipe(_v, linux=True)
