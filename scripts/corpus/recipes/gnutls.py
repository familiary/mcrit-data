"""GnuTLS 3.8.13 - the GNU TLS library (libgnutls), Linux ELF and MinGW DLL, x86 and x64.

Tracker issue #26 (the GnuTLS layer is the study's largest collision with
OpenSSL, 1,613 functions). This is the follow-on to the Nettle and GMP
families: the aim here is breadth of GnuTLS itself, with the Nettle and GMP
code that GnuTLS links in left to those two families.

Build: GnuTLS needs Nettle (with hogweed), GMP, libtasn1 and libunistring.
GMP 6.3.0 (--enable-fat --with-pic) and Nettle 3.10.2 (against that GMP,
--disable-shared, -fPIC) are built first as static helper libraries under
deps-{arch} of the build tree; libtasn1 and libunistring are GnuTLS's bundled
copies (--with-included-libtasn1 --with-included-unistring). GnuTLS is
configured --enable-shared --disable-static --without-p11-kit --without-idn
--without-zlib --without-brotli --without-zstd --without-tpm --without-tpm2
--disable-doc --disable-tests --disable-tools --disable-cxx --disable-libdane
--disable-nls --disable-guile, and only gl/ and lib/ are made. MinGW passes
lt_cv_deplibs_check_method=pass_all to configure: without it libtool refuses
the static helper archives for a DLL ("libtool will only create a static
version of it") and the DLL is never written. That is a configure variable,
not a source edit; no upstream file is patched in any leg.

Sources: gnutls-3.8.13.tar.xz, gmp-6.3.0.tar.xz and nettle-3.10.2.tar.gz are
pinned by sha256 and their detached signatures were verified with gpg against
the upstream keys (GnuTLS: Zoltan Fridrich and Alexander Sosedkin; GMP and
Nettle: Niels Moeller, whose key has expired since but was valid when the
signatures were made).

Exclusion: the helper libraries' code is in the image whatever the flags are,
and the Nettle and GMP families already carry it, so it is removed by name
through Recipe.exclude_functions (the namespaces and the file-local statics
below; see the comment on _NAMESPACES_ELF). kept + removed (compiler runtime
glue) + excluded = image total, recomputed from provenance.json:

  x64 Linux  3871 + 5   + 1181 = 5057
  x86 Linux  4520 + 9   + 1063 = 5592
  x64 MinGW  3351 + 161 + 1071 = 4583
  x86 MinGW  3221 + 166 + 1021 = 4408

PicHash overlap (functions of 10+ instructions) of the kept functions with
Nettle 3.10.2 and GMP 6.3.0 of the same toolchain and architecture: x64 Linux
16, x86 Linux 14, x64 MinGW 36, x86 MinGW 53 (before the 32-bit PE underscore
fix of the patterns the x86 MinGW image overlapped 434). What is left is
GnuTLS's own thin wrappers (_gnutls_cmac_magma_*, x86_hmac_sha*_set_key,
padlock_hmac_*), a few Nettle statics that are not on the list
(memxor3_different_alignment_b, mpn_get/set_base256 which GnuTLS defines
itself), and unnamed GMP assembly blocks in the PE images (9 on x64, 14 on
x86) that a name pattern cannot reach. Overlap between the four GnuTLS
images: Linux x86/x64 0, MinGW x86/x64 0, Linux x64/MinGW x64 27, Linux
x86/MinGW x86 158.

Not built: MSVC (upstream supports MinGW only), other GnuTLS releases and the
optional back ends; see scripts/corpus/README.md.
"""

import re

from ..recipe import Artifact, BuildStep, Recipe, Source


_GMP_VERSION = "6.3.0"
_GMP_SHA256 = "a3c2b80201b89e68616f4ad30bc66aee4927c3ce50e33929ca819d5c43538898"
_NETTLE_VERSION = "3.10.2"
_NETTLE_SHA256 = "fe9ff51cb1f2abb5e65a6b8c10a92da0ab5ab6eaf26e7fc2b675c45f1fb519b5"

# version -> sha256 of the GPG-verified tarball
_VERSIONS = {
    "3.8.13": "ffed8ec1bf09c2426d4f14aae377de4753b53e537d685e604e99a8b16ca9c97e",
}

# Name patterns of the code that GnuTLS links in statically from the helper
# libraries and that the Nettle and GMP families already carry: the public
# prefixes (nettle_*, _nettle_*, __gmp*, mpn_/mpz_/mpq_/mpf_*, ecc_*) minus the
# few names of that shape that GnuTLS itself defines (nettle_tls10_prf,
# nettle_tls12_prf, mpn_get_base256, mpn_set_base256, mpz_seed_sizeinbase_256_u,
# and _nettle_write_be32, which both define), plus the file-local statics of
# Nettle and GMP by exact name.  Both lists come from `nm` over the static
# libraries and over GnuTLS's own objects of the same build tree: a name is
# excluded only when a helper library defines it and no GnuTLS object does.
# The 32-bit PE ABI prefixes every C symbol with one more underscore, so the
# MinGW recipe allows up to three leading underscores (___gmpz_add) where the
# ELF recipes allow two.
_NAMESPACES_ELF = (r"^_?_?(?:nettle_(?!tls1[02]_prf$|write_be32$)|gmp)"
                   r"|^_?_?mp[nzqf]_(?!get_base256$|set_base256$|seed_sizeinbase_256_u$)"
                   r"|^ecc_")
_NAMESPACES_PE = (r"^_{0,3}(?:nettle_(?!tls1[02]_prf$|write_be32$)|gmp)"
                  r"|^_{0,3}mp[nzqf]_(?!get_base256$|set_base256$|seed_sizeinbase_256_u$)"
                  r"|^_{0,3}ecc_")
_STATICS = (
    '.rc',
    'LPSX',
    '_camellia256_set_encrypt_key',
    '_siv_s2v',
    'abs_sub_add_n',
    'abs_sub_n',
    'base16_decode_length',
    'base16_encode_final',
    'base16_encode_init',
    'base16_encode_length',
    'base16_encode_update_wrapper',
    'base64_decode_length',
    'base64_encode_length',
    'base64url_decode_length',
    'base64url_encode_length',
    'bc_bin_uiui',
    'block_resieve',
    'ccm_build_iv',
    'check_length.part.0',
    'ctr_fill',
    'ctr_fill16',
    'div2',
    'drbg_ctr_aes256_output',
    'eax_aes128_set_nonce_wrapper',
    'ecdsa_in_range',
    'ed25519_dom',
    'ed448_dom',
    'encode_raw',
    'equal_h',
    'fat_init',
    'findnext',
    'format_prefix',
    'g',
    'gcd_hook',
    'gcm_aes128_set_nonce_wrapper',
    'gcm_aes192_set_nonce_wrapper',
    'gcm_aes256_set_nonce_wrapper',
    'gcm_camellia128_set_nonce_wrapper',
    'gcm_camellia256_set_nonce_wrapper',
    'gcm_fill',
    'gcm_hash',
    'gcm_sm4_set_nonce_wrapper',
    'get',
    'gost_block_compress',
    'gost_compute_sum_and_hash',
    'gosthash94_update_int.part.0',
    'gosthash94_write_digest',
    'h',
    'h_byte',
    'hash',
    'hgcd_hook',
    'hgcd_jacobi_hook',
    'hgcd_jacobi_step',
    'hgcd_matrix_apply',
    'hmac_gosthash94_set_key_wrapper',
    'hmac_gosthash94cp_set_key_wrapper',
    'hmac_md5_set_key_wrapper',
    'hmac_ripemd160_set_key_wrapper',
    'hmac_sha1_set_key_wrapper',
    'hmac_sha224_set_key_wrapper',
    'hmac_sha256_set_key_wrapper',
    'hmac_sha384_set_key_wrapper',
    'hmac_sha512_set_key_wrapper',
    'hmac_sm3_set_key_wrapper',
    'hmac_streebog256_set_key_wrapper',
    'hmac_streebog512_set_key_wrapper',
    'ibcrypt.constprop.0',
    'is_kth_power',
    'jacobi_hook',
    'lc.isra.0',
    'md2_transform',
    'md4_compress',
    'md4_transform',
    'miller_rabin_pocklington.part.0',
    'millerrabin',
    'mod.part.0',
    'mod_eq_m1.isra.0',
    'mord_2exp.isra.0',
    'mul1',
    'mul2',
    'mul3',
    'mul4',
    'mul5',
    'mul6',
    'mul7',
    'mul8',
    'ocb_checksum_n',
    'ocb_crypt_n',
    'ocb_fill_n',
    'omac_update',
    'pad_block',
    'perfpow',
    'poly128_mul',
    'poly1305_pad',
    'poly64_mul.part.0',
    'posmpz_dec_ui',
    'posmpz_inc_ui',
    'pow_equals',
    'randclear_lc',
    'randget_lc',
    'randiset_lc',
    'randseed_lc',
    'randseed_mt',
    'redcify',
    'reduce',
    'rek_raising_fac4',
    'scan',
    'sec_mod_mul',
    'sec_powm',
    'set_xkey',
    'sexp_iterator_parse',
    'sexp_iterator_simple',
    'sha256_write_digest',
    'sha512_write_digest',
    'siv_gcm_authenticate',
    'siv_gcm_derive_keys.constprop.0',
    'siv_gcm_fill',
    'siv_ghash_pad_update',
    'skip_white',
    'sm3_compress',
    'sm4_set_key',
    'sm4_t_non_lin_sub',
    'step',
    'streebog512_compress',
    'streebog512_write_digest.part.0',
    'streebog_final',
    'submul',
    'umac_kdf',
    'unget',
)
_STATIC_RE = "^_?(?:%s)$" % "|".join(re.escape(n) for n in _STATICS)

# Helper libraries, static and position independent, installed under
# deps-{arch} of the build tree.
_UNPACK = ("mkdir -p deps-{arch}/src && cd deps-{arch}/src && "
           "tar xf {gmp_archive} && tar xf {nettle_archive}")
_GMP = ("D=$PWD/deps-{arch} && cd deps-{arch}/src && mkdir gmp-build && "
        "cd gmp-build && {gmp_abi}../gmp-" + _GMP_VERSION + "/configure{gmp_host} "
        "--prefix=$D --disable-shared --enable-static --enable-fat --with-pic "
        "&& make -j$(nproc) && make install")
_NETTLE = ("D=$PWD/deps-{arch} && cd deps-{arch}/src && mkdir nettle-build && "
           "cd nettle-build && ../nettle-" + _NETTLE_VERSION + "/configure{gmp_host} "
           "--prefix=$D --libdir=$D/lib --disable-shared --enable-static "
           "--disable-documentation --disable-openssl "
           "CFLAGS=\"$CFLAGS -fPIC\" CPPFLAGS=-I$D/include LDFLAGS=-L$D/lib "
           "&& make -j$(nproc) SUBDIRS= && make install SUBDIRS=")
_GNUTLS = ("D=$PWD/deps-{arch} && mkdir -p build-{arch} && cd build-{arch} && "
           "PKG_CONFIG_PATH=$D/lib/pkgconfig "
           "NETTLE_LIBS=\"-L$D/lib -lnettle\" NETTLE_CFLAGS=-I$D/include "
           "HOGWEED_LIBS=\"-L$D/lib -lhogweed -lnettle -lgmp\" HOGWEED_CFLAGS=-I$D/include "
           "CPPFLAGS=-I$D/include LDFLAGS=-L$D/lib "
           "{lt_env}{source_root}/configure{gmp_host} --enable-shared --disable-static "
           "--with-included-libtasn1 --with-included-unistring --without-p11-kit "
           "--without-idn --without-zlib --without-brotli --without-zstd "
           "--without-tpm --without-tpm2 --disable-doc --disable-tests "
           "--disable-tools --disable-cxx --disable-libdane --disable-nls "
           "--disable-guile")

_FLAGS = ("--enable-shared --disable-static --with-included-libtasn1 "
          "--with-included-unistring --without-p11-kit --without-idn --without-zlib "
          "--without-brotli --without-zstd --without-tpm --without-tpm2 --disable-doc "
          "--disable-tests --disable-tools --disable-cxx --disable-libdane "
          "--disable-nls --disable-guile; GMP 6.3.0 (--enable-fat --with-pic) and "
          "Nettle 3.10.2 (with GMP, --disable-shared, -fPIC) built as static helper "
          "libraries in the build tree and linked into libgnutls")
_NOTES = ("Nettle, hogweed and GMP code linked in statically is removed by name "
          "(Recipe.exclude_functions) because the Nettle and GMP families carry it; "
          "libtasn1 and libunistring are GnuTLS's bundled copies and stay in. "
          "Source tarballs are sha256-pinned and were checked against the upstream "
          "GPG signatures. No source is patched.")


def _recipe(version, linux):
    abi = "ABI=$([ {bitness} = 32 ] && echo 32 || echo 64) " if linux else ""
    host = "" if linux else " --host={host}"
    unpack = _UNPACK
    gmp = _GMP.replace("{gmp_abi}", abi).replace("{gmp_host}", host)
    nettle = _NETTLE.replace("{gmp_host}", host)
    gnutls = _GNUTLS.replace("{gmp_host}", host).replace(
        "{lt_env}", "" if linux else "lt_cv_deplibs_check_method=pass_all ")
    return Recipe(
        family="GnuTLS",
        version=version,
        upstream="https://www.gnutls.org/",
        license="LGPL-2.1-or-later",
        source=Source(url="https://www.gnupg.org/ftp/gcrypt/gnutls/v3.8/gnutls-%s.tar.xz" % version,
                      sha256=_VERSIONS[version]),
        extra_sources={
            "gmp_archive": Source(url="https://ftp.gnu.org/gnu/gmp/gmp-%s.tar.xz" % _GMP_VERSION,
                                  sha256=_GMP_SHA256),
            "nettle_archive": Source(
                url="https://ftp.gnu.org/gnu/nettle/nettle-%s.tar.gz" % _NETTLE_VERSION,
                sha256=_NETTLE_SHA256)},
        build=[BuildStep(unpack), BuildStep(gmp), BuildStep(nettle),
               BuildStep(gnutls),
               BuildStep("make -j$(nproc) -C gl && make -j$(nproc) -C lib", cwd="build-{arch}")],
        artifacts=[Artifact(
            path="build-{arch}/lib/.libs/" + ("libgnutls.so" if linux else "libgnutls-30.dll"),
            component="libgnutls.so" if linux else "libgnutls.dll")],
        toolchains=["linux_x86", "linux_x64"] if linux else ["mingw_x86", "mingw_x64"],
        requires=["m4", "pkg-config"],
        exclude_functions=[_NAMESPACES_ELF if linux else _NAMESPACES_PE, _STATIC_RE],
        build_flags=_FLAGS,
        notes=_NOTES,
    )


RECIPES = {}
for _version in _VERSIONS:
    RECIPES["GnuTLS_%s" % _version] = _recipe(_version, linux=False)
    RECIPES["GnuTLS_%s_linux" % _version] = _recipe(_version, linux=True)
