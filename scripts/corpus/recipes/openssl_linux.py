"""OpenSSL for Linux (ELF), beside the Windows builds of the same releases.

Targeted by backlog issues #32 (the 1.0.x branch and a Linux ELF build) and
#58 (the 0.9.x branch as static ELF x86). data/OpenSSL held only PE
artefacts, MinGW and one MSVC version, and nothing older than 1.1.1.

Two shapes of build, both measured on this host (gcc 13.3, Ubuntu 24.04).

**Shared objects (1.0.1u onward).** Upstream's own ``Configure`` with the
``shared`` option, ``libcrypto.so.<soversion>`` and ``libssl.so.<soversion>``,
no ``no-asm``, no ``-fvisibility=hidden``. The asm stays on because it is what a
distribution build or a vendored copy contains and because, unlike the MSVC
leg, nothing here lacks an assembler: perlasm emits GAS. Unlike the header-only
C++ families, OpenSSL's own shared build already controls what it exports
(1.0.x through a version script, 1.1 and 3.x likewise), so the visibility flag
that README "The Linux half" asks of those would add nothing, and the issue
asks for the library as upstream builds it. A ``-shared`` object links glibc
dynamically, so no libc body enters the image.

``CFLAGS`` is emptied for these steps. The linux toolchain exports
``CFLAGS=-O2 -m64``; 1.1.1 and 3.x ``Configure`` take that as the user's
``CFLAGS`` and it *replaces* upstream's ``-Wall -O3`` (measured: the generated
Makefile reads ``CFLAGS=-O2`` with it, ``CFLAGS=-Wall -O3`` without), while
1.0.x ``Configure`` ignores it. The ABI flag travels in ``CC`` instead. So all
of these are upstream's default optimisation, ``-O3``.

**0.9.x as an archive linked whole into a .so.** The issue's suggestion, and
the only way to get a static OpenSSL into a file without putting a C runtime
into it too: a ``-static`` link resolves every libc reference from glibc's
archive and files those bodies under the family's name (README, "The Linux
half"). So ``no-shared`` builds ``libcrypto.a`` / ``libssl.a``, and
``gcc -m32 -shared -Wl,--whole-archive`` wraps each archive into a shared
object with its libc references left undefined. ``--whole-archive`` keeps
objects a real static link would drop as unreferenced, which is the price of
having something to disassemble; it is recorded in ``notes``.

Two accommodations, flags and make variables only, no source touched:

  * ``no-asm``. The x86 perlasm/assembler routes of 0.9.x predate PIC and
    gas 2.4x and the issue itself suggested it. The 0.9.x asm covers only
    SHA-1, MD5 and RIPEMD-160 in 0.9.6 and a few more primitives in 0.9.7e
    (``x86_elf_asm`` in Configure); everything else is C either way.
  * 0.9.x ``Configure`` ignores the ``CC`` environment variable, so without
    ``CC="gcc -m32"`` on the make line the objects come out 64-bit and the
    32-bit link fails with "file class ELFCLASS64 incompatible".
  * The 0.9.x make is serial. With -j the parallel ``ranlib`` runs of the
    FIPS and crypto subdirectories corrupted libcrypto.a on 0.9.7e (``Bus
    error`` from ranlib, then undefined references when the apps linked).
  * ``linux-elf`` carries ``-m486``, which GCC 13 rejects (``unrecognized
    command-line option '-m486'``). The ``CFLAG`` the generated Makefile
    names is passed back on the make command line with that one word removed;
    the Makefile itself is not edited. 0.9.7e's ``linux-pentium`` and
    ``linux-ppro`` targets use ``-mcpu=``, which x86 GCC rejects too.

0.9.x is built without ``-fPIC`` (0.9.6's ``linux-elf`` adds it by default and
it is taken out; 0.9.7e's ``no-shared`` has none), because the samples this
is meant to match link OpenSSL statically into a non-PIC executable, and 32-bit
PIC bodies reach the GOT through a per-image ``get_pc_thunk`` delta that would
make PicHashes differ for no reason of OpenSSL's.

**What was already there, and what this adds.** On main data/OpenSSL held
1.1.1w, 3.0.15 and 3.5.8 for MinGW x86/x64 and 1.1.1w for MSVC x86/x64 (16
artefacts), all PE. Added in the same change, as recipe names:

  * ELF x86/x64: ``OpenSSL_1.0.1u_linux``, ``_1.0.2u_linux``, ``_1.1.1w_linux``,
    ``_3.0.15_linux``, ``_3.5.8_linux``; ELF x86 only: ``_0.9.6_linux``,
    ``_0.9.7e_linux``, ``_0.9.8zh_linux``.
  * MinGW x86/x64: ``OpenSSL_1.0.2u`` (openssl.py).
  * MSVC x86/x64: ``OpenSSL_1.0.2u_msvc``, ``_3.0.15_msvc``, ``_3.5.8_msvc``
    (openssl_msvc_legacy.py).

Not built, with the reason: 1.0.1u for MinGW (its Makefile.shared links the
cygwin-shared flavour with ``-Wl,-s``, so both DLLs come out stripped and
ssleay32.dll fails the symbol-coverage gate, 254 of 624 named on x86; no flag
undoes a strip), 1.0.1u for MSVC (no Windows evidence for it, and it shares
64% of 1.0.2u's PicHashes), 0.9.x for x64 or Windows (the cited samples are
32-bit ELF; 0.9.6 has no x86_64 target), 1.0.0t (between two measured
neighbours; nothing cites it).

**Why every axis is its own reference** (PicHashes of 10+ instructions, shared
count as a share of the smaller artefact; libcrypto; the libssl numbers are
lower still). Same release, different axis:

    ELF vs MinGW    x64 1.0.2u 53 (2.0%)  1.1.1w 55 (1.6%)  3.0.15 63 (1.1%)  3.5.8 65 (1.0%)
                    x86 1.0.2u 109 (3.9%) 1.1.1w 98 (2.8%)  3.0.15 108 (1.8%) 3.5.8 108 (1.5%)
    ELF vs MSVC     x64 0 for all four;  x86 1.0.2u 5, the others 0
    MinGW vs MSVC   x64 1.0.2u 1, 1.1.1w 7, 3.0.15 7, 3.5.8 7;  x86 5, 7, 9, 7

Neighbouring releases on one axis (x64 ELF): 1.0.1u / 1.0.2u 1609 (64.3%,
libssl 38.6%), 1.0.2u / 1.1.1w 115 (4.3%), 1.1.1w / 3.0.15 2010 (42.3%),
3.0.15 / 3.5.8 4454 (56.0%). On MinGW x64 1.0.2u / 1.1.1w is 498 (17.6%) and on
MSVC x64 667 (21.7%). On x86 ELF every pair is 1-6% because 32-bit PIC bodies
reach the GOT through a per-image ``get_pc_thunk`` delta (README, "The Linux
half"); the 0.9.x pairs are 0.9.6 / 0.9.7e 93 (5.1%), 0.9.7e / 0.9.8zh 94
(3.5%), 0.9.8zh / 1.0.1u 88 (2.7%).

1.0.1u and 1.0.2u are both kept on the strength of the 64% and not in spite
of it: the issue's evidence names 1.0.1 (Kyber's 1.0.1e-fips; Penquin_x64's
1.0.1j), and about a third of libcrypto and 61% of libssl differ.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

# CFLAGS emptied: see the module docstring.
_NO_CFLAGS = {"CFLAGS": "", "CXXFLAGS": ""}

_TARGET = {
    "1.0": "$([ {bitness} = 64 ] && echo linux-x86_64 || echo linux-elf)",
    "1.1": "$([ {bitness} = 64 ] && echo linux-x86_64 || echo linux-x86)",
    "3": "$([ {bitness} = 64 ] && echo linux-x86_64 || echo linux-x86)",
}


def _licence(version):
    return "Apache-2.0" if version.startswith("3") else "OpenSSL / SSLeay"


def _shared(version, sha256, url, branch, soversion):
    no_tests = " no-tests" if branch != "1.0" else ""
    return Recipe(
        family="OpenSSL",
        version=version,
        upstream="https://github.com/openssl/openssl",
        license=_licence(version),
        source=Source(url=url, sha256=sha256),
        build=[
            BuildStep("./Configure %s shared%s" % (_TARGET[branch], no_tests),
                      env=_NO_CFLAGS),
            # OpenSSL's parallel make can lose a dependency-file rename; a
            # second invocation completes cleanly.
            BuildStep("make -j$(nproc) build_libs || make build_libs",
                      env=_NO_CFLAGS),
        ],
        artifacts=[
            Artifact(path="libcrypto.so.%s" % soversion, component="libcrypto"),
            Artifact(path="libssl.so.%s" % soversion, component="libssl"),
        ],
        toolchains=["linux_x86", "linux_x64"],
        requires=["perl"],
        build_flags="-O3 (upstream default), upstream's shared build with "
                    "asm, -fPIC; no -fvisibility change",
        notes="The Linux shared object of upstream's default configuration; "
              "the Windows builds are the sibling OpenSSL_%s recipes. glibc "
              "is NEEDED, not linked in. x86 is Configure's 32-bit ELF "
              "target with -m32 in CC." % version,
    )


# 0.9.x. The CFLAG of the generated Makefile, minus -m486 (rejected by GCC
# 13) and minus -fPIC, goes back on the make command line. sed edits the
# printed value, not the file.
_CFLAG_OVERRIDE = ("CF=\"$(sed -n 's/^CFLAG= *//p' Makefile | sed 's/ -m486//; "
                   "s/-fPIC//')\" && ")
# Both archives are wrapped whole so that every object counts; the libc
# references are left undefined and resolved by nothing, as in a .so that
# nobody loads. -z notext because no-PIC objects need text relocations.
_WRAP = ("gcc -m32 -shared -Wl,-z,notext -o libcrypto-whole.so "
         "-Wl,--whole-archive libcrypto.a -Wl,--no-whole-archive && "
         "gcc -m32 -shared -Wl,-z,notext -o libssl-whole.so "
         "-Wl,--whole-archive libssl.a -Wl,--no-whole-archive")


def _static(version, sha256, url):
    return Recipe(
        family="OpenSSL",
        version=version,
        upstream="https://github.com/openssl/openssl",
        license="OpenSSL / SSLeay",
        source=Source(url=url, sha256=sha256),
        build=[
            BuildStep("./Configure linux-elf no-asm no-shared",
                      env=_NO_CFLAGS),
            BuildStep(_CFLAG_OVERRIDE +
                      "make CC=\"$CC\" CFLAG=\"$CF\"",
                      env=_NO_CFLAGS),
            BuildStep(_WRAP),
        ],
        artifacts=[
            Artifact(path="libcrypto-whole.so", component="libcrypto"),
            Artifact(path="libssl-whole.so", component="libssl"),
        ],
        toolchains=["linux_x86"],
        requires=["perl"],
        build_flags="-O3 -fomit-frame-pointer (linux-elf), no-asm, no-shared, "
                    "no -fPIC, -m486 dropped; libcrypto.a / libssl.a wrapped "
                    "with -shared -Wl,--whole-archive",
        notes="Static x86 OpenSSL as an ELF file: the no-shared archives "
              "linked whole into a shared object so that glibc is not "
              "pulled in under this family's name. --whole-archive keeps "
              "objects a real static link would drop. no-asm and the "
              "removal of -m486 (rejected by GCC 13) are described in the "
              "recipe module docstring.",
    )


_URL_OLD = "https://www.openssl.org/source/old/"

RECIPES = {
    "OpenSSL_0.9.6_linux": _static(
        "0.9.6", "5215b670c2674df9a642565ea68a67e6d955d8efcca1aa1b4e6a5b4fd2744ee8",
        _URL_OLD + "0.9.x/openssl-0.9.6.tar.gz"),
    "OpenSSL_0.9.7e_linux": _static(
        "0.9.7e", "25121b5dbd2b830929519325e033086ce45861cff2d0000d928f48261b1e0b7c",
        _URL_OLD + "0.9.x/openssl-0.9.7e.tar.gz"),
    "OpenSSL_0.9.8zh_linux": _static(
        "0.9.8zh", "f1d9f3ed1b85a82ecf80d0e2d389e1fda3fca9a4dba0bf07adbf231e1a5e2fd6",
        _URL_OLD + "0.9.x/openssl-0.9.8zh.tar.gz"),
    "OpenSSL_1.0.1u_linux": _shared(
        "1.0.1u", "4312b4ca1215b6f2c97007503d80db80d5157f76f8f7d3febbe6b4c56ff26739",
        _URL_OLD + "1.0.1/openssl-1.0.1u.tar.gz", "1.0", "1.0.0"),
    "OpenSSL_1.0.2u_linux": _shared(
        "1.0.2u", "ecd0c6ffb493dd06707d38b14bb4d8c2288bb7033735606569d8f90f89669d16",
        _URL_OLD + "1.0.2/openssl-1.0.2u.tar.gz", "1.0", "1.0.0"),
    "OpenSSL_1.1.1w_linux": _shared(
        "1.1.1w", "cf3098950cb4d853ad95c0841f1f9c6d3dc102dccfcacd521d93925208b76ac8",
        "https://github.com/openssl/openssl/releases/download/OpenSSL_1_1_1w/openssl-1.1.1w.tar.gz",
        "1.1", "1.1"),
    "OpenSSL_3.0.15_linux": _shared(
        "3.0.15", "23c666d0edf20f14249b3d8f0368acaee9ab585b09e1de82107c66e1f3ec9533",
        "https://github.com/openssl/openssl/releases/download/openssl-3.0.15/openssl-3.0.15.tar.gz",
        "3", "3"),
    "OpenSSL_3.5.8_linux": _shared(
        "3.5.8", "a8f84a39918ec6415ce765d9b429d313ba97b8143169c172e734b9514464f5b2",
        "https://github.com/openssl/openssl/releases/download/openssl-3.5.8/openssl-3.5.8.tar.gz",
        "3", "3"),
}


# The final sweep.
# * 1.0.0t, shared, as 1.0.1u and 1.0.2u (it was skipped because nothing cites
#   it; the corpus commits any image that is not PicHash-identical).
RECIPES["OpenSSL_1.0.0t_linux"] = _shared(
    "1.0.0t", "5ab6e348c6c2a95d457e7a00e0aa653bfc7eb4df7b24e7c9ab63163ac0299097",
    _URL_OLD + "1.0.0/openssl-1.0.0t.tar.gz", "1.0", "1.0.0")


# * 0.9.7e and 0.9.8zh on x64: the same static no-asm build as their x86
#   recipes through Configure's linux-x86_64 target (both releases have it;
#   0.9.6 has none, see the README row), wrapped into a shared object the
#   same way, without -m32.
def _static_x64(version, sha256, url):
    recipe = _static(version, sha256, url)
    recipe.build = [
        BuildStep("./Configure linux-x86_64 no-asm no-shared", env=_NO_CFLAGS),
        BuildStep("CF=\"$(sed -n 's/^CFLAG= *//p' Makefile | sed 's/-fPIC//')\" && "
                  "make CC=\"$CC\" CFLAG=\"$CF -fPIC\"", env=_NO_CFLAGS),
        BuildStep(_WRAP.replace("gcc -m32 ", "gcc ")),
    ]
    recipe.toolchains = ["linux_x64"]
    recipe.build_flags = ("-O3 (linux-x86_64), no-asm, no-shared, -fPIC (a "
                          "64-bit shared object needs it); libcrypto.a / "
                          "libssl.a wrapped with -shared -Wl,--whole-archive")
    recipe.notes = ("Static x64 OpenSSL as an ELF file: the no-shared archives "
                    "linked whole into a shared object, as the x86 recipe of "
                    "this release does, so glibc is not filed under this "
                    "family. Configure's linux-x86_64 target, no-asm.")
    return recipe


RECIPES["OpenSSL_0.9.7e_linux64"] = _static_x64(
    "0.9.7e", "25121b5dbd2b830929519325e033086ce45861cff2d0000d928f48261b1e0b7c",
    _URL_OLD + "0.9.x/openssl-0.9.7e.tar.gz")
RECIPES["OpenSSL_0.9.8zh_linux64"] = _static_x64(
    "0.9.8zh", "f1d9f3ed1b85a82ecf80d0e2d389e1fda3fca9a4dba0bf07adbf231e1a5e2fd6",
    _URL_OLD + "0.9.x/openssl-0.9.8zh.tar.gz")

