r"""GnuTLS built with MSVC (v143, /MD), beside the MinGW and Linux builds of the same release.

Tracker issue #26. Upstream supports MinGW and not MSVC, and GnuTLS cannot be
built from a hand-written configuration the way GMP and Nettle can (it carries
about 240 gnulib replacement files whose configure results drive the build),
so the one part of this build that is GnuTLS's own is its own `configure`, run
for cl the way the GNU project documents it for MSVC: through MSYS2 bash with
automake's `compile` and `ar-lib` wrappers in front of cl and lib. Every
object is compiled by cl. The driver is
scripts/corpus/exercisers/gnutls_msvc_build.py; gnutls.py explains the
dependencies and the exclusion, which is the same here.

  * GMP 6.3.0 as static gmp.lib (the no-assembly build of gmp_msvc.py with
    `--static`) and Nettle 3.10.2 as static nettle.lib and hogweed.lib against
    that GMP (not mini-gmp; configured the way nettle_msvc_build.py configures
    it, with NETTLE_USE_MINI_GMP 0 and the real limb width in version.h and in
    the ecc tables).
  * GnuTLS's `configure` with `compile cl -nologo` as CC, `ar-lib lib` as AR,
    `LD=link`, `NM="dumpbin -symbols"`, build = host = <arch>-w64-mingw32 so
    that it runs what it compiles, the options of gnutls.py plus
    `--disable-shared --enable-static --disable-hardware-acceleration
    --disable-dependency-tracking --disable-rpath`, and the helper libraries
    found through NETTLE_*/HOGWEED_* variables. `make -C gl` and `make -C lib`
    build gnulib and every source of lib/ and its subdirectories.
  * libtool leaves one static archive, lib/.libs/gnutls.lib (cl has no "lib"
    prefix), which is linked to libgnutls-30.dll with the corpus flags:
    /WHOLEARCHIVE of the archive and of the convenience libraries libtool did
    not merge into it, gmp.lib, hogweed.lib and nettle.lib as ordinary
    archives (only referenced members come in, as with the static libraries of
    the Linux and MinGW builds), /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF
    /OPT:NOICF, and 1,885 exports from the objects by the rule of
    lib/Makefile.am for linkers without a version script, `^(gnutls|_gnutls)`.
    The link needed no /FORCE.

Build-tree additions (NOT part of GnuTLS; no upstream file is edited, but the
image is NOT byte-identical to a build of unmodified upstream, which does not
compile with cl). GnuTLS 3.8.13 has MSVC branches for most GNU-isms and misses
four, found by the runner builds:

    lib\x509\verify-high2.c(40): fatal error C1083: Cannot open include file: 'dirent.h': No such file or directory
    lib\global.c(546): error C2143: syntax error: missing ')' before '('      (static void _CONSTRUCTOR lib_init(void); also line 578, lib_deinit)
    lib\crau/crau.h(263): error C2146: syntax error: missing ')' before identifier 'CRAU_MAYBE_UNUSED'      (also lines 269, 279, 285, 290, 295)
    lib\audit.c(28): error C2054: expected '(' to follow '_Thread_local'

`global.c` puts `__attribute__((constructor))` on its two init functions
unless the compiler is Solaris's, `crau.h` leaves `CRAU_MAYBE_UNUSED`
undefined unless the compiler is GCC or C23, `audit.c` uses `_Thread_local`
without including gthreads.h (which defines it for MSVC), and the SDK has no
dirent.h. The exerciser writes two headers into the build tree and uses them
for the make phase only: a force-included one (`cl -FI`, found through -I)
defining `_Thread_local` as `__declspec(thread)`, `__attribute__(x)` as
nothing and `CRAU_MAYBE_UNUSED` as nothing, and a dirent.h of
FindFirstFile-based opendir/readdir/closedir plus the wide `_topendir`
family, `_TDIR` and `struct _tdirent` that verify-high2.c takes because the
build defines _UNICODE (the first run with only the narrow functions stopped
at `verify-high2.c(434): error C2065: '_TDIR': undeclared identifier` and
`(474): error C2037: left of 'd_name' specifies undefined struct/union
'_tdirent'`). With `__attribute__` empty the two init functions are plain
unused statics: this DLL would not run GnuTLS's initialisation at load. It is
reference data, not something to run. The three narrow dirent functions are in
`_STATICS` below, so any copy of them is excluded by name.

Exclusion. Nettle, hogweed and GMP code linked in from the static libraries is
removed by name (`_NAMESPACES_PE` of gnutls.py plus `_STATICS`), the statics
being the source-level static functions of both trees joined with the Linux
list, minus every name GnuTLS's own objects define; against the statics that
cl really produced in the three libraries (173 in gmp.lib, 124 in nettle.lib,
60 x64 or 57 x86 in hogweed.lib, listed in the build log as `STATICS`) the
list leaves only the CRT inline `time` uncovered. The names the pattern
leaves in the images are GnuTLS's own definitions of that shape:
nettle_tls10_prf, nettle_tls12_prf, nettle_write_be32, mpn_get_base256,
mpn_set_base256 and mpz_seed_sizeinbase_256_u.

Counts, kept + removed (the baseline's measured MSVC runtime) + excluded
(Nettle and GMP by name) = image total, from provenance.json:

    GnuTLS_3.8.13_msvc143_x64_libgnutls.dll   4611 + 190 + 994 = 5795   3322 functions of 10+ instructions, 2864 distinct PicHashes
    GnuTLS_3.8.13_msvc143_x86_libgnutls.dll   4648 + 204 + 993 = 5845   3415 / 2872

PicHash overlap of the kept 10+ instruction functions with the MSVC images of
the helper families: GMP 6.3.0 0 (x86), 0 (x64); Nettle 3.10.2 libnettle 9
(x86), 6 (x64); libhogweed 3 (x86), 0 (x64). (The Nettle family's MSVC images
carry mini-gmp, GnuTLS's helper hogweed here uses GMP, which is part of why
hogweed overlaps little.)

Runner builds (windows-2022, cl 19.44): runs 42749164007, 42750806400 and
42752272041 (GMP and GnuTLS; GnuTLS stopped in lib/ at the errors above and
then at the dirent shim), 42754505008 (a shim header that had the wide
functions in the wrong file), 42755679488 (every file of gl/ and lib/
compiled; the script looked for libgnutls.a while libtool left gnutls.lib) and
42756951311 (built; the data in the repository is from it).

Not built: other GnuTLS releases and the optional back ends.
"""

import re

from ..recipe import Artifact, BuildStep, Recipe, Source
from .gnutls import (_GMP_SHA256, _GMP_VERSION, _NAMESPACES_PE,
                     _NETTLE_SHA256, _NETTLE_VERSION, _VERSIONS, _url)


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
        source=Source(url=_url(version), sha256=_VERSIONS[version]),
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
                    "^(gnutls|_gnutls); build-tree shim headers: force-included "
                    "_Thread_local/__attribute__/CRAU_MAYBE_UNUSED definitions "
                    "and dirent.h",
        notes="Nettle, hogweed and GMP code linked in statically is removed "
              "by name (Recipe.exclude_functions) because the Nettle and GMP "
              "families carry it; libtasn1 and libunistring are GnuTLS's "
              "bundled copies and stay in. Sources are sha256-pinned and "
              "were checked against the upstream GPG signatures. No upstream "
              "file is edited, but GnuTLS does not compile with cl as it is: "
              "two build-tree headers (a force-included one defining "
              "_Thread_local as __declspec(thread) and __attribute__(x) and "
              "CRAU_MAYBE_UNUSED as nothing, and a dirent.h) are added for "
              "the make phase, so the image is NOT byte-identical to a build "
              "of unmodified upstream, and without __attribute__((constructor)) "
              "its init functions are not run at load. C only (no accelerated "
              "assembly).",
    )


RECIPES = {"GnuTLS_%s_msvc" % version: _recipe(version) for version in _VERSIONS}
