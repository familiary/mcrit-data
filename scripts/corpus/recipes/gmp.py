"""GMP - the GNU Multiple Precision Arithmetic Library, MinGW and Linux ELF.

Follow-on of backlog issue #26 (Nettle): libhogweed, Nettle's public-key half
and GnuTLS's big-number back end, links GMP. The Nettle recipes build hogweed
with Nettle's own mini-gmp (nettle.py explains why: this host had no libgmp and
cl cannot build GMP), which files about a third of libhogweed's functions under
Nettle's name. A real GMP family is what a hogweed linked against libgmp.so
leaves out of its own image, and what the issue's "GMP 73 families / 168
samples" collisions point at. The issue suggests the order Nettle, libgcrypt,
GMP, GnuTLS.

Source. gmp-6.3.0.tar.xz from ftp.gnu.org (6.3.0, 2023-07-24, the latest
release), pinned by sha256; the detached .sig verified with gpgv against the GNU
keyring (https://ftp.gnu.org/gnu/gnu-keyring.gpg): good signature by Niels
Moller <nisse@lysator.liu.se>, RSA key
343C2FF0FBEE5EC2EDBEF399F3599FF828C67298. The pinned sha256 is of the verified
tarball. Nothing is patched.

Build. Upstream's configure, out of tree, one build directory per
architecture, libgmp as a shared library (the C++ wrapper libgmpxx is a
separate library and is not built; the MinGW legs also compile the static
archive, see the comment above _COMMON, which is not an artefact), with
--enable-fat. GMP selects its
assembly by the CPU the configure script runs on, which would tie the
reference data to whichever machine built it; --enable-fat (supported for x86
and x86_64) builds every x86 CPU variant into the one library and picks one at
run time through CPUID, so the output does not depend on the builder, and the
image holds all the variants (the cost is size: a fat libgmp is several times
the functions of a native one). On Linux x86 the build is ABI=32 with
CC="gcc -m32" (the corpus toolchain's -m32), on x64 ABI=64; MinGW goes
through --host=i686-w64-mingw32 and x86_64-w64-mingw32 and produces
libgmp-10.dll. On Linux the artefact is libgmp.so as libtool leaves it in
.libs/ (libgmp.so.10.5.0 and its symlink). MSVC is a separate recipe,
GMP_6.3.0_msvc (gmp_msvc.py): GMP's own configure and assembly (GNU as,
m4-processed .asm) do not run under cl, and the project documents MinGW, not
MSVC, for Windows, so that build compiles the portable C of mpn/generic from
a script. The MinGW legs carry the one libtool edit described above _COMMON.

Measured on the artefacts (SMDA 5.0.2), kept + removed = image total, removed
being the glue baseline's measured compiler runtime and CRT:

  GMP_6.3.0_gcc13_x64_libgmp.so    1,321 +   6 = 1,327   784 functions of 10+ instructions, 712 distinct PicHashes
  GMP_6.3.0_gcc13_x86_libgmp.so    1,576 +   5 = 1,581   776 / 743
  GMP_6.3.0_mingw13_x64_libgmp.dll   964 + 157 = 1,121   801 / 714
  GMP_6.3.0_mingw13_x86_libgmp.dll   923 + 161 = 1,084   760 / 715

(The MinGW DLL links the CRT start-up and mingw's printf/gdtoa/stdio import
shims, which the baseline removes: 157 and 161 functions.) PicHash overlap of
the 10+ instruction functions: Linux against MinGW 1 on x64 and 193 on x86
(26% of the Linux and 27% of the MinGW side), Linux x86 against Linux x64 0,
and against
Nettle 3.10.2's and 4.0's libhogweed (built with mini-gmp, so a different
implementation) 3 on x64 and 2 on x86. Named functions that are not GMP's API
(mpn_*, mpz_*, mpq_*, mpf_*, gmp_*) are GMP's own file-local statics
(hgcd_matrix_apply, block_resieve, findnext, randget_lc, perfpow, ...): 47 to
55 per image; the Linux x86 image also has the 32-bit PIC glue
(__do_global_dtors_aux, 21 instructions, per-image PicHash). Nothing named is
from outside GMP.

Not built: other releases (6.2.1 and 6.1.2 were not built or measured; one
release is the scope of this pass) and libgmpxx. GnuTLS has its own recipes
(gnutls.py; its MSVC attempt is described in gnutls_msvc.py).
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# MinGW needs --disable-static --enable-shared (configure refuses both: "cannot
# build both static and DLL, since gmp.h is different for each"), and with that
# this libtool writes the import library over the DLL itself: its link line
# ends "-o .libs/libgmp-10.dll ... -Xlinker --out-implib -Xlinker
# .libs/libgmp-10.dll", so the DLL ends up an `ar` archive and SMDA stops with
# "Input is not a PE, ELF, Mach-O, DEX or Delphi knowledge base". The one
# build-tree edit of the recipe: a sed over the libtool script that configure
# generated in the build directory (not upstream source), pointing
# --out-implib at libgmp.dll.a. The DLL's code is what the unedited link would
# produce; the image is nevertheless not byte-identical to a build of
# unmodified upstream, because that build produces no usable DLL.
_COMMON = "--enable-shared --disable-static --enable-fat"
_FIX_IMPLIB = (r"sed -i 's|-Xlinker --out-implib -Xlinker \\\$lib|-Xlinker "
               r"--out-implib -Xlinker \\\$output_objdir/libgmp.dll.a|' libtool")
_CONFIGURE_PE = ("mkdir -p build-{arch} && cd build-{arch} && "
                 "{source_root}/configure --host={host} " + _COMMON +
                 " && " + _FIX_IMPLIB)
_CONFIGURE_ELF = ("mkdir -p build-{arch} && cd build-{arch} && "
                  "ABI=$([ {bitness} = 32 ] && echo 32 || echo 64) "
                  "{source_root}/configure " + _COMMON)

# version -> sha256 of the GPG-verified tarball
_VERSIONS = {
    "6.3.0": "a3c2b80201b89e68616f4ad30bc66aee4927c3ce50e33929ca819d5c43538898",
}


def _recipe(version, linux):
    configure = (_CONFIGURE_ELF if linux else _CONFIGURE_PE)
    return Recipe(
        family="GMP",
        version=version,
        upstream="https://gmplib.org/",
        license="LGPL-3.0-or-later OR GPL-2.0-or-later (dual, licensee's choice)",
        source=Source(url="https://ftp.gnu.org/gnu/gmp/gmp-%s.tar.xz" % version,
                      sha256=_VERSIONS[version]),
        build=[BuildStep(configure),
               BuildStep("make -j$(nproc)", cwd="build-{arch}")],
        artifacts=[Artifact(
            path="build-{arch}/.libs/" + ("libgmp.so" if linux else "libgmp-10.dll"),
            component="libgmp.so" if linux else "libgmp.dll")],
        toolchains=["linux_x86", "linux_x64"] if linux else ["mingw_x86", "mingw_x64"],
        requires=["m4"],
        build_flags="-O2 -g (configure default), --enable-fat (all x86 CPU "
                    "variants, CPUID dispatch), shared library only"
                    + ("" if linux else "; generated libtool edited so the "
                       "import library is not written over the DLL"),
        notes="Shared libgmp from upstream's configure, unpatched" + (
              "" if linux else " except that the generated libtool script of the "
              "build directory is edited so that the import library is not "
              "written over the DLL (see the recipe; the image is NOT "
              "byte-identical to a build of unmodified upstream, which yields "
              "no usable DLL)") + ", built "
              "--enable-fat so the image does not depend on the CPU of the "
              "builder. The C++ wrapper libgmpxx is not built. Pinned by the "
              "sha256 of a GPG-verified release tarball.",
    )


RECIPES = {}
for _version in _VERSIONS:
    RECIPES["GMP_%s" % _version] = _recipe(_version, linux=False)
    RECIPES["GMP_%s_linux" % _version] = _recipe(_version, linux=True)
