"""OpenSSL - the largest crypto body in the corpus.

Three versions, chosen for architecture rather than recency: 1.1.1 has no
provider layer at all and is still by far the most encountered OpenSSL, 3.0
introduced the provider architecture, and 3.5 is the current LTS. A 3.x point
release would add almost nothing next to these.

Upstream publishes a SHA-256 beside every release asset, and the digests
recorded here were taken from those files.

Honest caveat: OpenSSL in the wild is overwhelmingly MSVC-built, so a MinGW
reference matches those only weakly. Its strength here is matching
MinGW/GCC-built Windows binaries, and by proxy ELF builds.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# The DLL names carry both the soversion and, on 64-bit only, an -x64 suffix
# (libcrypto-3-x64.dll vs libcrypto-3.dll), so the outputs are normalised to
# stable names rather than spelling out four variants per version.
_NORMALISE = ("cp $(ls libcrypto-*.dll | head -1) libcrypto.dll && "
              "cp $(ls libssl-*.dll | head -1) libssl.dll")

# --cross-compile-prefix prepends the triple to the tool names itself, so the
# usual fully-qualified CC would come out doubled as
# x86_64-w64-mingw32-x86_64-w64-mingw32-gcc. Hand it the bare names.
_ENV = {"CC": "gcc", "CXX": "g++", "AR": "ar", "RANLIB": "ranlib",
        "WINDRES": "windres"}


def _openssl(version, sha256, url):
    return Recipe(
        family="OpenSSL",
        version=version,
        upstream="https://github.com/openssl/openssl",
        license="Apache-2.0" if version.startswith("3") else "OpenSSL / SSLeay",
        source=Source(url=url, sha256=sha256),
        build=[
            BuildStep("./Configure {openssl_target} "
                      "--cross-compile-prefix={prefix} shared no-tests",
                      env=_ENV),
            # OpenSSL's parallel make has a dependency-file race that can lose
            # a .d.tmp rename; a second invocation completes cleanly.
            BuildStep("make -j$(nproc) build_libs build_programs || "
                      "make -j$(nproc) build_libs build_programs", env=_ENV),
            BuildStep(_NORMALISE),
        ],
        artifacts=[
            Artifact(path="libcrypto.dll", component="libcrypto"),
            Artifact(path="libssl.dll", component="libssl"),
        ],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (upstream default)",
        requires=["perl"],
        notes="perlasm generates GAS assembly, so no nasm is needed for the "
              "mingw targets.",
    )


def _openssl_1_0(version, sha256, url):
    """1.0.x, MinGW. The legacy build system names things differently."""
    return Recipe(
        family="OpenSSL",
        version=version,
        upstream="https://github.com/openssl/openssl",
        license="OpenSSL / SSLeay",
        source=Source(url=url, sha256=sha256),
        build=[
            # 1.0.x Configure has no no-tests; the tests are a separate make
            # target and build_libs does not touch them.
            BuildStep("./Configure {openssl_target} "
                      "--cross-compile-prefix={prefix} shared", env=_ENV),
            BuildStep("make -j$(nproc) build_libs || make build_libs",
                      env=_ENV),
        ],
        # libeay32 / ssleay32 are 1.0.x's names for libcrypto / libssl, on
        # both bitnesses; the component keeps the family's own spelling.
        artifacts=[
            Artifact(path="libeay32.dll", component="libcrypto"),
            Artifact(path="ssleay32.dll", component="libssl"),
        ],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (upstream default; 1.0.x Configure ignores the "
                    "CFLAGS the toolchain exports), shared, asm",
        requires=["perl"],
        notes="1.0.x MinGW: the DLLs are libeay32.dll and ssleay32.dll on "
              "both x86 and x64. perlasm generates GAS assembly, so no nasm "
              "is needed.",
    )


RECIPES = {
    # No provider layer; still the most encountered OpenSSL by a wide margin.
    "OpenSSL_1.1.1w": _openssl(
        "1.1.1w", "cf3098950cb4d853ad95c0841f1f9c6d3dc102dccfcacd521d93925208b76ac8",
        "https://github.com/openssl/openssl/releases/download/OpenSSL_1_1_1w/openssl-1.1.1w.tar.gz"),
    # First LTS of the provider architecture.
    "OpenSSL_3.0.15": _openssl(
        "3.0.15", "23c666d0edf20f14249b3d8f0368acaee9ab585b09e1de82107c66e1f3ec9533",
        "https://github.com/openssl/openssl/releases/download/openssl-3.0.15/openssl-3.0.15.tar.gz"),
    # Current LTS.
    "OpenSSL_3.5.8": _openssl(
        "3.5.8", "a8f84a39918ec6415ce765d9b429d313ba97b8143169c172e734b9514464f5b2",
        "https://github.com/openssl/openssl/releases/download/openssl-3.5.8/openssl-3.5.8.tar.gz"),
    # The 1.0 branch. 1.0.1u is not built for MinGW: its Makefile.shared
    # links the cygwin-shared flavour with -Wl,-s (strip), which 1.0.2u
    # dropped, so both DLLs come out without a COFF symbol table and
    # ssleay32.dll fails the symbol-coverage gate (254 of 624 functions named
    # on x86, 190 of 563 on x64) while libeay32.dll passes it only on its
    # exports. No flag undoes a strip. The 1.0.1 branch is covered by ELF.
    "OpenSSL_1.0.2u": _openssl_1_0(
        "1.0.2u", "ecd0c6ffb493dd06707d38b14bb4d8c2288bb7033735606569d8f90f89669d16",
        "https://www.openssl.org/source/old/1.0.2/openssl-1.0.2u.tar.gz"),
}


# The final sweep: 1.0.1u (and 1.0.0t) for MinGW. Both releases' mingw targets
# carry -mno-cygwin, which GCC 13 rejects, and their Makefile.shared links the
# cygwin-shared flavour with -Wl,-s,-Bsymbolic, which strips the DLLs (1.0.2u
# dropped both). Neither needs a source edit: a compiler wrapper in the build
# tree passes every argument through to the toolchain's gcc except those two,
# -mno-cygwin dropped and -Wl,-s,-Bsymbolic given as -Wl,-Bsymbolic, so the
# code is what upstream's link produces and the COFF symbol table stays. The
# wrapper changes link and driver options only.
_WRAPPER = (
    "printf '%s\\n' '#!/bin/bash' 'a=()' "
    "'for x in \"$@\"; do case \"$x\" in -mno-cygwin) ;; "
    "-Wl,-s,-Bsymbolic) a+=(-Wl,-Bsymbolic) ;; *) a+=(\"$x\") ;; esac; done' "
    "'exec {cc} \"${a[@]}\"' > corpus-cc && chmod +x corpus-cc")


def _openssl_1_0_wrapped(version, sha256, url):
    recipe = _openssl_1_0(version, sha256, url)
    recipe.build = [
        BuildStep(_WRAPPER),
        BuildStep("./Configure {openssl_target} "
                  "--cross-compile-prefix={prefix} shared", env=_ENV),
        BuildStep("make -j$(nproc) CC=$PWD/corpus-cc build_libs || "
                  "make CC=$PWD/corpus-cc build_libs", env=_ENV),
    ]
    recipe.build_flags = ("-O3 (upstream default), shared, asm; built through "
                          "a gcc wrapper that drops -mno-cygwin and links "
                          "-Wl,-Bsymbolic instead of upstream's -Wl,-s,-Bsymbolic "
                          "(no strip)")
    recipe.notes = ("1.0.x MinGW: libeay32.dll and ssleay32.dll. The release's "
                    "mingw targets pass -mno-cygwin (rejected by GCC 13) and "
                    "its Makefile.shared strips the DLLs with -Wl,-s; a "
                    "compiler wrapper in the build tree drops the first and "
                    "the strip, so the DLLs keep their symbol table. No source "
                    "file is edited; the image differs from an upstream build "
                    "in its symbol table only.")
    return recipe


RECIPES["OpenSSL_1.0.1u"] = _openssl_1_0_wrapped(
    "1.0.1u", "4312b4ca1215b6f2c97007503d80db80d5157f76f8f7d3febbe6b4c56ff26739",
    "https://www.openssl.org/source/old/1.0.1/openssl-1.0.1u.tar.gz")
RECIPES["OpenSSL_1.0.0t"] = _openssl_1_0_wrapped(
    "1.0.0t", "5ab6e348c6c2a95d457e7a00e0aa653bfc7eb4df7b24e7c9ab63163ac0299097",
    "https://www.openssl.org/source/old/1.0.0/openssl-1.0.0t.tar.gz")


# The final sweep: 0.9.x for MinGW x86, built and wrapped the way
# openssl_linux.py's _static wraps the 0.9.x ELF builds. Configure's own
# MinGW target (Mingw32 in 0.9.6, mingw in 0.9.7e and 0.9.8zh) with no-asm
# no-shared, the Unix Makefile driven with the cross tools on the make line
# (0.9.x Configure has no --cross-compile-prefix), the CFLAG Configure wrote
# passed back without -mno-cygwin and -m486, which GCC 13 rejects; then
# libcrypto.a linked whole into libeay32.dll (every symbol exported, import
# library written) and libssl.a whole into ssleay32.dll against it. No
# release has a 64-bit MinGW target (0.9.8zh's 64-bit Windows targets are
# VC-WIN64A/VC-WIN64I), so there is no x64 leg here.
_CF09 = ("CF=\"$(sed -n 's/^CFLAG= *//p' Makefile | sed 's/-mno-cygwin//; "
         "s/ -m486//')\" && ")
_MAKE09 = ("make -k CC={cc} AR=\"{prefix}ar r\" RANLIB={prefix}ranlib "
           "CFLAG=\"$CF\" build_crypto build_ssl || true; "
           "test -f libcrypto.a && test -f libssl.a")
_DLL09 = ("{cc} -shared -o libeay32.dll -Wl,--whole-archive libcrypto.a "
          "-Wl,--no-whole-archive -Wl,--export-all-symbols "
          "-Wl,--out-implib,libeay32.dll.a -lws2_32 -lgdi32 && "
          "{cc} -shared -o ssleay32.dll -Wl,--whole-archive libssl.a "
          "-Wl,--no-whole-archive -Wl,--export-all-symbols libeay32.dll.a "
          "-lws2_32 -lgdi32")


def _openssl_09_mingw(version, sha256, target):
    return Recipe(
        family="OpenSSL",
        version=version,
        upstream="https://github.com/openssl/openssl",
        license="OpenSSL / SSLeay",
        source=Source(url="https://www.openssl.org/source/old/0.9.x/"
                          "openssl-%s.tar.gz" % version, sha256=sha256),
        build=[BuildStep("./Configure %s no-asm no-shared" % target, env=_ENV),
               BuildStep(_CF09 + _MAKE09, env=_ENV),
               BuildStep(_DLL09)],
        artifacts=[Artifact(path="libeay32.dll", component="libcrypto"),
                   Artifact(path="ssleay32.dll", component="libssl")],
        toolchains=["mingw_x86"],
        requires=["perl"],
        build_flags="-O3 (Configure's %s target), no-asm, no-shared, "
                    "-mno-cygwin and -m486 dropped from CFLAG; libcrypto.a / "
                    "libssl.a linked whole into libeay32.dll / ssleay32.dll "
                    "with --export-all-symbols" % target,
        notes="0.9.x for MinGW x86: the release's own %s target, the static "
              "archives wrapped into the two DLLs (the 0.9.x Unix Makefile "
              "builds no MinGW DLL). No source is edited." % target,
    )


RECIPES["OpenSSL_0.9.8zh"] = _openssl_09_mingw(
    "0.9.8zh", "f1d9f3ed1b85a82ecf80d0e2d389e1fda3fca9a4dba0bf07adbf231e1a5e2fd6", "mingw")
RECIPES["OpenSSL_0.9.7e"] = _openssl_09_mingw(
    "0.9.7e", "25121b5dbd2b830929519325e033086ce45861cff2d0000d928f48261b1e0b7c", "mingw")
RECIPES["OpenSSL_0.9.6"] = _openssl_09_mingw(
    "0.9.6", "5215b670c2674df9a642565ea68a67e6d955d8efcca1aa1b4e6a5b4fd2744ee8", "Mingw32")

