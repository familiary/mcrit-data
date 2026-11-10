r"""GnuTLS built with MSVC (v143, /MD): NOT BUILT, and therefore not registered.

Tracker issue #26. The recipe below is complete and was run three times on the
windows-2022 runner (cl 19.44), x86 and x64, but the last run still stopped at
one source file, and the dispatch budget for this item (three) is spent, so
`RECIPES` is left empty: a registered recipe that fails would turn every
`all-msvc` run red. To try it again, set `RECIPES` to `_CANDIDATES` and
dispatch `GnuTLS_3.8.13_msvc` on its own.

What was built, and how (scripts/corpus/exercisers/gnutls_msvc_build.py; the
Linux and MinGW recipe in gnutls.py explains the dependencies and the
exclusion):

  * GMP 6.3.0 as static gmp.lib (the no-assembly build of gmp_msvc.py with
    `--static`) and Nettle 3.10.2 as static nettle.lib and hogweed.lib against
    that GMP (not mini-gmp; configured the way nettle_msvc_build.py configures
    it, with NETTLE_USE_MINI_GMP 0 and the real limb width in version.h and in
    the ecc tables). Both built on both architectures in all three runs.
    gnutls.py's `_NAMESPACES_PE` plus the statics below exclude them from the
    image by name. The statics were listed from the three libraries as cl built
    them (symbols of storage class Static, printed to the build log as
    `STATICS`): 173 in gmp.lib, 124 in nettle.lib, 60 (x64) or 57 (x86) in
    hogweed.lib; the names of `_STATICS` below (224, and the three functions of the dirent shim), taken from the sources'
    own static functions and from the Linux list, cover all of them except the
    CRT inline `time`.
  * GnuTLS's own `configure`, run under MSYS2 bash (pacman provides make, m4
    and diffutils) with automake's `build-aux/compile cl -nologo` as CC and
    `build-aux/ar-lib lib` as AR, `LD=link`, `NM="dumpbin -symbols"`, build =
    host = <arch>-w64-mingw32 so that it runs what it compiles, the options of
    gnutls.py plus `--disable-shared --enable-static --disable-hardware-
    acceleration --disable-dependency-tracking --disable-rpath`, and the
    helper libraries found through NETTLE_*/HOGWEED_* variables. It completes
    on both architectures (cl is reported as "not GNU C"; every gnulib probe
    runs natively).
  * `make -C gl` builds all of gnulib's replacements with cl and no error, and
    `make -C lib` compiles every source of lib/ and of its subdirectories
    (x509, auth, ext, algorithms, extras, hpke, accelerated, nettle, minitasn1,
    unistring) except the ones listed next. The static archive is then to be
    linked to libgnutls-30.dll with the corpus flags (/WHOLEARCHIVE of the
    libtool archive, /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF,
    exports `^(gnutls|_gnutls)`); that step has never been reached.

What stopped it, in order (x64; the x86 text differs only in the path):

  Run 42749164007 (no shim yet), `make -C lib` -k, every error of the build:

    lib\x509\verify-high2.c(40): fatal error C1083: Cannot open include file: 'dirent.h': No such file or directory
    lib\global.c(546): error C2143: syntax error: missing ')' before '('      (static void _CONSTRUCTOR lib_init(void); also line 578, lib_deinit)
    lib\crau/crau.h(263): error C2146: syntax error: missing ')' before identifier 'CRAU_MAYBE_UNUSED'      (also lines 269, 279, 285, 290, 295)
    lib\audit.c(28): error C2054: expected '(' to follow '_Thread_local'
    make[2]: *** No rule to make target 'x509/libgnutls_x509.la', needed by 'libgnutls.la'.

  Each is a GCC-ism GnuTLS 3.8.13 does not guard for cl: `global.c` puts
  `__attribute__((constructor))` on its two init functions unless the compiler
  is Solaris's, `crau.h` leaves `CRAU_MAYBE_UNUSED` undefined unless the
  compiler is GCC or C23, `audit.c` uses `_Thread_local` without including
  gthreads.h (which would define it for MSVC), and the SDK has no dirent.h.
  They are answered without editing any upstream file, by a force-included
  header (`cl -FI`, found through -I) that defines `_Thread_local` as
  `__declspec(thread)`, `__attribute__(x)` as nothing and `CRAU_MAYBE_UNUSED`
  as nothing, and by a header-only dirent.h (FindFirstFile based) written into
  the build tree, both by the exerciser and only for the make phase. With
  `__attribute__` empty the two init functions are plain unused statics, so
  this DLL would not run GnuTLS's initialisation at load; it is reference
  data, not something to run.

  Run 42750806400: the shim was found through an absolute path that MSYS2's
  argument conversion mangled, so every file failed (`Cannot open include file:
  'D:A:/mcrit-data/.../deps/shim/msvc_shim.h'`); fixed by finding it through
  -I.

  Run 42752272041, `make -C lib`, the only errors left, both architectures:

    lib\x509\verify-high2.c(434): error C2065: '_TDIR': undeclared identifier
    lib\x509\verify-high2.c(434): error C2065: 'dirp': undeclared identifier
    lib\x509\verify-high2.c(473): error C2198: 'int _gnutls_ucs2_to_utf8(const void *,size_t,gnutls_datum_t *,unsigned int)': too few arguments for call
    lib\x509\verify-high2.c(474): error C2037: left of 'd_name' specifies undefined struct/union '_tdirent'
    lib\x509\verify-high2.c(474): error C2037: left of 'd_namlen' specifies undefined struct/union '_tdirent'
    make[2]: *** No rule to make target 'x509/libgnutls_x509.la', needed by 'libgnutls.la'.

  The build defines _UNICODE, so verify-high2.c takes its wide-character branch
  (`_TDIR`, `_topendir`, `_treaddir`, `_tclosedir`, `struct _tdirent` with
  `d_namlen`, which MinGW's dirent.h provides). The dirent shim of the three
  runs had the narrow functions only. The exerciser in the repository has the
  wide ones added (`_wopendir` and friends, mapped by the `_UNICODE` macros);
  that header compiles with MinGW gcc for both architectures with and without
  _UNICODE, but it has NOT been run on the runner, and what comes after it (the
  libtool archive, the link of the DLL) has never been reached, so nothing is
  known about those two steps.

Counts: none; no GnuTLS MSVC image exists.
"""

import re

from ..recipe import Artifact, BuildStep, Recipe, Source
from .gnutls import (_GMP_SHA256, _GMP_VERSION, _NAMESPACES_PE,
                     _NETTLE_SHA256, _NETTLE_VERSION, _VERSIONS)


# The file-local functions of GMP's generic C tree and of Nettle 3.10.2 as cl
# compiles them (the sources' own static function names, from compiling both
# trees and listing the local text symbols), joined with the statics of the
# assembly builds in gnutls.py, minus every name that an object of GnuTLS
# itself defines. cl does not decorate statics (no .isra/.part/.constprop
# suffixes) and 32-bit cl prefixes one underscore, which the pattern allows.
_STATICS = (
    # header-only dirent shim of the build tree (gnutls_msvc_build.py)
    'closedir',
    'opendir',
    'readdir',
    'DO_mpn_addlsh_n',
    'DO_mpn_sublsh_n',
    'DesSmallFipsDecrypt',
    'DesSmallFipsEncrypt',
    'LPSX',
    '_camellia256_set_encrypt_key',
    '_oaep_sec_decrypt_variable',
    '_siv_s2v',
    'abs_sub_add_n',
    'abs_sub_n',
    'add_signed_n',
    'asn1_der_iterator_init',
    'base16_decode_length',
    'base16_encode_final',
    'base16_encode_init',
    'base16_encode_length',
    'base16_encode_update_wrapper',
    'base64_decode_length',
    'base64_encode_in_place',
    'base64_encode_length',
    'base64url_decode_length',
    'base64url_encode_length',
    'bc_bin_uiui',
    'block16_bswap',
    'block16_mulx_be',
    'block16_mulx_ghash',
    'block16_mulx_le',
    'block16_set',
    'block16_xor',
    'block16_xor3',
    'block16_xor_bytes',
    'block16_zero',
    'block8_mulx_be',
    'block8_xor',
    'block8_xor3',
    'block8_xor_bytes',
    'block_resieve',
    'block_to_int',
    'calculate_sievelimit',
    'ccm_build_iv',
    'ccm_pad',
    'check_length',
    'cnd_mpn_zero',
    'cnd_neg',
    'compute_s',
    'compute_v',
    'ctr_fill',
    'ctr_fill16',
    'decround',
    'des_weak_p',
    'div1',
    'div2',
    'drbg_ctr_aes256_output',
    'drbg_ctr_aes256_update',
    'eax_aes128_set_nonce_wrapper',
    'ecdsa_in_range',
    'ed25519_dom',
    'ed448_dom',
    'encode_radix64',
    'encode_raw',
    'equal_h',
    'extract',
    'fat_init',
    'fill_bitpattern',
    'findnext',
    'findnext_small',
    'format_prefix',
    'format_string',
    'g',
    'gcd_hook',
    'gcm_aes128_set_nonce_wrapper',
    'gcm_aes192_set_nonce_wrapper',
    'gcm_aes256_set_nonce_wrapper',
    'gcm_camellia128_set_nonce_wrapper',
    'gcm_camellia256_set_nonce_wrapper',
    'gcm_fill',
    'gcm_gf_mul',
    'gcm_hash',
    'gcm_hash_sizes',
    'gcm_sm4_set_nonce_wrapper',
    'get',
    'getbits',
    'gf_multiply',
    'gost_block_compress',
    'gost_compute_sum_and_hash',
    'gosthash94_update_int',
    'gosthash94_write_digest',
    'h',
    'h_byte',
    'hash',
    'hash_ints',
    'hgcd_hook',
    'hgcd_jacobi_hook',
    'hgcd_jacobi_step',
    'hgcd_matrix_apply',
    'hgcd_mul_matrix_vector',
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
    'ibcrypt',
    'id_to_n',
    'invert_4by2',
    'is_kth_power',
    'is_zero_limb',
    'isprime',
    'jacobi_hook',
    'lc',
    'limb_apprsqrt',
    'log_n_max',
    'logbased_root',
    'mangle_seed',
    'md2_transform',
    'md4_compress',
    'md4_transform',
    'memxor3_common_alignment',
    'memxor3_different_alignment_ab',
    'memxor3_different_alignment_all',
    'memxor3_different_alignment_b',
    'memxor_common_alignment',
    'memxor_different_alignment',
    'miller_rabin_pocklington',
    'millerrabin',
    'mod',
    'mod_eq_m1',
    'mord_2exp',
    'mul1',
    'mul2',
    'mul3',
    'mul4',
    'mul5',
    'mul6',
    'mul7',
    'mul8',
    'n_cto_bit',
    'n_fto_bit',
    'n_to_bit',
    'ocb_checksum_n',
    'ocb_crypt_n',
    'ocb_fill_n',
    'omac_final',
    'omac_init',
    'omac_update',
    'pad_block',
    'perfpow',
    'poly128_mul',
    'poly1305_pad',
    'poly1305_update',
    'poly64_mul',
    'posmpz_dec_ui',
    'posmpz_inc_ui',
    'posmpz_init',
    'posmpz_rsh1',
    'pow_equals',
    'powlimb',
    'powsquaredlimb',
    'powtab_decide',
    'primesieve_size',
    'randclear_lc',
    'randget_lc',
    'randiset_lc',
    'randseed_lc',
    'randseed_mt',
    'redcify',
    'reduce',
    'rek_raising_fac4',
    'rsa_sec_blind',
    'rsa_sec_check_root',
    'rsa_sec_unblind',
    'scan',
    'sec_binvert_limb',
    'sec_equal',
    'sec_mod_mul',
    'sec_mod_mul_itch',
    'sec_mul',
    'sec_mul_itch',
    'sec_powm',
    'sec_powm_itch',
    'serpent_key_pad',
    'set_xkey',
    'sexp_iterator_init',
    'sexp_iterator_parse',
    'sexp_iterator_simple',
    'sha256_write_digest',
    'sha3_absorb',
    'sha512_write_digest',
    'siv_gcm_authenticate',
    'siv_gcm_derive_keys',
    'siv_gcm_fill',
    'siv_ghash_pad_update',
    'skip_white',
    'sm3_compress',
    'sm3_write_digest',
    'sm4_enc_lin_sub',
    'sm4_enc_sub',
    'sm4_key_lin_sub',
    'sm4_key_sub',
    'sm4_round',
    'sm4_set_key',
    'sm4_t_non_lin_sub',
    'step',
    'streebog512_compress',
    'streebog512_write_digest',
    'streebog_final',
    'strlen_u8',
    'submul',
    'table_init',
    'umac_kdf',
    'umac_l3_word',
    'unget',
    'update_offset',
    'win_size',
    'write_string',
    'yarrow_gate',
    'yarrow_generate_block',
    'yarrow_iterate',
)
_STATIC_RE = "^_?(?:%s)$" % "|".join(re.escape(n) for n in _STATICS)

_BUILD = ("python {repo}/scripts/corpus/exercisers/gnutls_msvc_build.py "
          "--arch {arch} --gmp-archive {gmp_archive} "
          "--nettle-archive {nettle_archive} --src .")


def _recipe(version):
    return Recipe(
        family="GnuTLS",
        version=version,
        upstream="https://www.gnutls.org/",
        license="LGPL-2.1-or-later",
        source=Source(
            url="https://www.gnupg.org/ftp/gcrypt/gnutls/v3.8/gnutls-%s.tar.xz" % version,
            sha256=_VERSIONS[version]),
        extra_sources={
            "gmp_archive": Source(
                url="https://ftp.gnu.org/gnu/gmp/gmp-%s.tar.xz" % _GMP_VERSION,
                sha256=_GMP_SHA256),
            "nettle_archive": Source(
                url="https://ftp.gnu.org/gnu/nettle/nettle-%s.tar.gz" % _NETTLE_VERSION,
                sha256=_NETTLE_SHA256)},
        build=[BuildStep(_BUILD), BuildStep("dir", allow_failure=True)],
        artifacts=[Artifact(path="libgnutls-30.dll", component="libgnutls.dll",
                            pdb="libgnutls-30.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        exclude_functions=[_NAMESPACES_PE, _STATIC_RE],
        build_flags="/O2 /MD /Z7, GnuTLS's own configure run under MSYS2 bash "
                    "with automake's compile/ar-lib wrappers around cl/lib, "
                    "--disable-shared --enable-static --disable-hardware-"
                    "acceleration and the options of the Linux/MinGW recipes; "
                    "GMP 6.3.0 (generic C) and Nettle 3.10.2 built with cl as "
                    "static libraries; libgnutls linked from the libtool "
                    "archive with /WHOLEARCHIVE /DEBUG /Brepro "
                    "/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF, exports "
                    "^(gnutls|_gnutls)",
        notes="Nettle, hogweed and GMP code linked in statically is removed "
              "by name (Recipe.exclude_functions) because the Nettle and GMP "
              "families carry it; libtasn1 and libunistring are GnuTLS's "
              "bundled copies and stay in. Sources are sha256-pinned and "
              "were checked against the upstream GPG signatures. No source "
              "is patched; the build is C only (no accelerated assembly).",
    )


_CANDIDATES = {"GnuTLS_%s_msvc" % version: _recipe(version) for version in _VERSIONS}

# Not registered: see the docstring.
RECIPES = {}
