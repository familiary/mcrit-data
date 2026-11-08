"""The zlib 1.3.2 that Win32-OpenSSH links statically, as exact names.

ssh, sshd, sshd-session and sshd-auth link the vcpkg build of zlib 1.3.2
(zs.lib, a copy of the installed zlib.lib; /MD, /Qspectre /guard:cf /sdl, as
built by openssh_win32_msvc.py) into the image, so its functions are in the
images under the OpenSSH family. Recipe.exclude_functions removes them by
name. LibreSSL is a DLL (libcrypto.dll in the import table of every program)
and libfido2 and libcbor are not linked into any of the eight programs, so
zlib is the only library there is to remove.

Basis, for every name below (x64 and x86 alike): the `report` step of the
build (scripts/corpus/exercisers/win32openssh.py, run 42512776170) dumped
`dumpbin /symbols` of zs.lib (163 function symbols) and of all 418 OpenSSH
objects of the build (2,852 names on x64, 2,884 on x86: libssh, openbsd_compat,
posix_compat and every program's own objects). A name is in the table if it
is a function of an image, defined by a zlib object, and defined by no
OpenSSH object. Three zs.lib names are also defined by OpenSSH objects
(`snprintf` and `vsnprintf`, the CRT inlines of stdio.h, and
`__local_stdio_printf_options`) and stay in the images, where the glue
baseline or data/MSVC deals with them. The x86 image names are undecorated
(no leading C underscore), so one table serves both architectures.

The evidence beyond that, counted per image (x64 / x86; the three images that
link zlib have the same 98 names):

  P  PicHash equals the PicHash of a same-named function (leading underscore
     ignored) in a data/libzlib MSVC image (1.2.8 to 1.3.1): 53 / 14.
  W  No PicHash match, but a same-named function of the same architecture in
     those images whose mnemonic sequence (nop/int3/ret/leave and the frame
     pointer set-up dropped; difflib ratio) is at least 0.80 similar: 33 / 59.
     zlib 1.3.2 built with /Qspectre /guard:cf /sdl is a different build
     from the 1.3.1 DLL and static builds in the corpus.
  N  Neither: the name is zlib's by archive membership alone (the basis
     above), no corpus image carries the code: 12 / 25.

98 names, 98 functions in each of the six images. The other 62 function names
of zs.lib (gz*, compress, compress2, uncompress ...) are not linked into any
program. Nothing else is excluded: the CRT is imported and the glue baseline
handles what it names.
"""

# Exact names, sorted. The pattern is anchored and has no prefix, suffix or
# underscore alternatives.
NAMES = (
    '_tr_align', '_tr_flush_bits', '_tr_flush_block', '_tr_init',
    '_tr_stored_block', '_tr_tally', 'adler32', 'adler32_combine',
    'adler32_combine64', 'adler32_combine_', 'adler32_z', 'bi_flush',
    'bi_reverse', 'bi_windup', 'build_bl_tree', 'build_tree', 'byte_swap',
    'compress_block', 'crc32', 'crc32_combine', 'crc32_combine64',
    'crc32_combine_gen', 'crc32_combine_gen64', 'crc32_combine_op',
    'crc32_z', 'crc_word', 'crc_word_big', 'deflate', 'deflateBound',
    'deflateBound_z', 'deflateCopy', 'deflateEnd', 'deflateGetDictionary',
    'deflateInit2_', 'deflateInit_', 'deflateParams', 'deflatePending',
    'deflatePrime', 'deflateReset', 'deflateResetKeep',
    'deflateSetDictionary', 'deflateSetHeader', 'deflateStateCheck',
    'deflateTune', 'deflateUsed', 'deflate_fast', 'deflate_huff',
    'deflate_rle', 'deflate_slow', 'deflate_stored', 'detect_data_type',
    'fill_window', 'flush_pending', 'gen_bitlen', 'gen_codes',
    'get_crc_table', 'inflate', 'inflateCodesUsed', 'inflateCopy',
    'inflateEnd', 'inflateGetDictionary', 'inflateGetHeader',
    'inflateInit2_', 'inflateInit_', 'inflateMark', 'inflatePrime',
    'inflateReset', 'inflateReset2', 'inflateResetKeep',
    'inflateSetDictionary', 'inflateStateCheck', 'inflateSync',
    'inflateSyncPoint', 'inflateUndermine', 'inflateValidate',
    'inflate_fast', 'inflate_fixed', 'inflate_table', 'init_block',
    'lm_init', 'longest_match', 'multmodp', 'pqdownheap', 'putShortMSB',
    'read_buf', 'scan_tree', 'send_all_trees', 'send_tree', 'slide_hash',
    'syncsearch', 'tr_static_init', 'updatewindow', 'x2nmodp', 'zError',
    'zcalloc', 'zcfree', 'zlibCompileFlags', 'zlibVersion',
)

# Evidence tier of each name in the x64 and the x86 images.
TIERS = {
 "x64": {
  "_tr_align": "P",
  "_tr_flush_bits": "P",
  "_tr_flush_block": "N",
  "_tr_init": "W",
  "_tr_stored_block": "N",
  "_tr_tally": "W",
  "adler32": "P",
  "adler32_combine": "N",
  "adler32_combine64": "P",
  "adler32_combine_": "P",
  "adler32_z": "P",
  "bi_flush": "P",
  "bi_reverse": "P",
  "bi_windup": "W",
  "build_bl_tree": "P",
  "build_tree": "P",
  "byte_swap": "P",
  "compress_block": "W",
  "crc32": "P",
  "crc32_combine": "W",
  "crc32_combine64": "W",
  "crc32_combine_gen": "N",
  "crc32_combine_gen64": "N",
  "crc32_combine_op": "W",
  "crc32_z": "N",
  "crc_word": "P",
  "crc_word_big": "P",
  "deflate": "W",
  "deflateBound": "N",
  "deflateBound_z": "N",
  "deflateCopy": "W",
  "deflateEnd": "W",
  "deflateGetDictionary": "P",
  "deflateInit2_": "W",
  "deflateInit_": "P",
  "deflateParams": "W",
  "deflatePending": "W",
  "deflatePrime": "P",
  "deflateReset": "W",
  "deflateResetKeep": "P",
  "deflateSetDictionary": "W",
  "deflateSetHeader": "P",
  "deflateStateCheck": "P",
  "deflateTune": "P",
  "deflateUsed": "N",
  "deflate_fast": "W",
  "deflate_huff": "P",
  "deflate_rle": "P",
  "deflate_slow": "W",
  "deflate_stored": "W",
  "detect_data_type": "P",
  "fill_window": "W",
  "flush_pending": "P",
  "gen_bitlen": "P",
  "gen_codes": "W",
  "get_crc_table": "P",
  "inflate": "W",
  "inflateCodesUsed": "P",
  "inflateCopy": "W",
  "inflateEnd": "W",
  "inflateGetDictionary": "P",
  "inflateGetHeader": "P",
  "inflateInit2_": "W",
  "inflateInit_": "P",
  "inflateMark": "P",
  "inflatePrime": "P",
  "inflateReset": "W",
  "inflateReset2": "W",
  "inflateResetKeep": "W",
  "inflateSetDictionary": "P",
  "inflateStateCheck": "P",
  "inflateSync": "W",
  "inflateSyncPoint": "P",
  "inflateUndermine": "P",
  "inflateValidate": "P",
  "inflate_fast": "P",
  "inflate_fixed": "N",
  "inflate_table": "N",
  "init_block": "P",
  "lm_init": "W",
  "longest_match": "W",
  "multmodp": "P",
  "pqdownheap": "P",
  "putShortMSB": "P",
  "read_buf": "P",
  "scan_tree": "P",
  "send_all_trees": "P",
  "send_tree": "P",
  "slide_hash": "W",
  "syncsearch": "P",
  "tr_static_init": "P",
  "updatewindow": "W",
  "x2nmodp": "P",
  "zError": "P",
  "zcalloc": "N",
  "zcfree": "P",
  "zlibCompileFlags": "W",
  "zlibVersion": "P"
 },
 "x86": {
  "_tr_align": "W",
  "_tr_flush_bits": "P",
  "_tr_flush_block": "W",
  "_tr_init": "W",
  "_tr_stored_block": "W",
  "_tr_tally": "W",
  "adler32": "P",
  "adler32_combine": "W",
  "adler32_combine64": "P",
  "adler32_combine_": "W",
  "adler32_z": "W",
  "bi_flush": "P",
  "bi_reverse": "W",
  "bi_windup": "W",
  "build_bl_tree": "W",
  "build_tree": "W",
  "byte_swap": "N",
  "compress_block": "N",
  "crc32": "N",
  "crc32_combine": "N",
  "crc32_combine64": "N",
  "crc32_combine_gen": "N",
  "crc32_combine_gen64": "N",
  "crc32_combine_op": "N",
  "crc32_z": "N",
  "crc_word": "W",
  "crc_word_big": "W",
  "deflate": "N",
  "deflateBound": "N",
  "deflateBound_z": "N",
  "deflateCopy": "N",
  "deflateEnd": "W",
  "deflateGetDictionary": "W",
  "deflateInit2_": "W",
  "deflateInit_": "P",
  "deflateParams": "W",
  "deflatePending": "W",
  "deflatePrime": "W",
  "deflateReset": "W",
  "deflateResetKeep": "W",
  "deflateSetDictionary": "W",
  "deflateSetHeader": "W",
  "deflateStateCheck": "P",
  "deflateTune": "W",
  "deflateUsed": "N",
  "deflate_fast": "N",
  "deflate_huff": "W",
  "deflate_rle": "N",
  "deflate_slow": "N",
  "deflate_stored": "N",
  "detect_data_type": "P",
  "fill_window": "W",
  "flush_pending": "W",
  "gen_bitlen": "W",
  "gen_codes": "W",
  "get_crc_table": "P",
  "inflate": "N",
  "inflateCodesUsed": "W",
  "inflateCopy": "W",
  "inflateEnd": "W",
  "inflateGetDictionary": "W",
  "inflateGetHeader": "W",
  "inflateInit2_": "W",
  "inflateInit_": "P",
  "inflateMark": "W",
  "inflatePrime": "W",
  "inflateReset": "W",
  "inflateReset2": "W",
  "inflateResetKeep": "W",
  "inflateSetDictionary": "W",
  "inflateStateCheck": "W",
  "inflateSync": "N",
  "inflateSyncPoint": "W",
  "inflateUndermine": "W",
  "inflateValidate": "W",
  "inflate_fast": "N",
  "inflate_fixed": "N",
  "inflate_table": "N",
  "init_block": "W",
  "lm_init": "W",
  "longest_match": "W",
  "multmodp": "W",
  "pqdownheap": "W",
  "putShortMSB": "P",
  "read_buf": "P",
  "scan_tree": "W",
  "send_all_trees": "W",
  "send_tree": "N",
  "slide_hash": "W",
  "syncsearch": "W",
  "tr_static_init": "P",
  "updatewindow": "W",
  "x2nmodp": "W",
  "zError": "W",
  "zcalloc": "N",
  "zcfree": "P",
  "zlibCompileFlags": "W",
  "zlibVersion": "P"
 }
}


def zlib_functions(names=NAMES):
    """One anchored regular expression over exact function names."""
    return r"^(?:%s)$" % "|".join(sorted(set(names)))
