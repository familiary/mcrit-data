"""Code the three miners compile in that other corpus families also carry, as exact names.

XMRig, xmrig-proxy and xmr-stak vendor or instantiate code that is not theirs:
llhttp (src/3rdparty/llhttp), the Argon2 and Blake2b helpers of
src/3rdparty/argon2, rapidjson (header-only, compiled into all three), C++
standard library templates (libstdc++ regex, sort and heap code; the MSVC STL's
destructors and regex nodes) and one MSVC CRT start-up function. `validate
--deep` fails on a PicHash that three families carry under one symbol name,
and with the llhttp, argon2 and BLAKE2 families present these were 266 of its
findings for this stack: 125 shared by the three miners (83 rapidjson, 41
standard library, 1 __scrt_common_main_seh), 121 with llhttp, 7 with OpenSSL
and 13 with RandomX, argon2, BLAKE2 and libsodium (10 Argon2/Blake2b helpers
and 3 MinGW CRT helpers).

Each recipe of the three families now sets Recipe.exclude_functions (PR #94)
to anchored patterns over exact function names, one per category, built by
exact_names(); the musl recipes append them to their libuv/OpenSSL rules,
which are unchanged. The names are in NAMES below, per recipe, because the
test is per recipe: an identifier is in a recipe's table only if EVERY function
of that exact name in the recipe's images (x86 and x64) is the library's, and
only if at least one of them is a function `validate --deep` reported (a
PicHash of ten instructions or more under three families). The rest of each
library stays in the image. The images were re-derived from their committed
.7z archives, not rebuilt: functions removed from the report and the export,
provenance gains exclude_functions, excluded_function_count and
num_functions_before_exclusion, so kept + removed as runtime + excluded is the
image total as before.

The evidence comes in three kinds, counted separately:

  P  PicHash confirmation. The function's PicHash is the PicHash of a
     same-named function (leading underscores ignored, as validate does) in
     the library's own family: llhttp -> data/llhttp 9.3.0 (MinGW and MSVC,
     x86 and x64; XMRig and the proxy vendor 9.3.0), the Argon2 helpers ->
     data/argon2 20190702, the Blake2b helpers -> data/BLAKE2. Stricter than
     the zlib helper's first test, which accepts any name.
  W  Weaker. No PicHash match, but a same-named function of the same
     architecture in that family whose mnemonic sequence (frame-pointer set-up,
     leave and nop/int3 padding dropped; difflib ratio) is at least 80%
     similar, and only for an identifier of which another function in the same
     recipe is P. It is the same code built by another compiler or with other
     flags: the families have no GCC ELF or musl build, and some MSVC x64
     functions differ in PicHash at 100% opcode similarity (llhttp_errno_name,
     llhttp_method_name, llhttp_status_name). The lowest ratio used is 0.89.
  N  Name. No corpus family carries rapidjson, the C++ standard library or the
     MSVC CRT start-up code: data/libstdc++ is one MinGW x86 DLL, has 3 of the
     31 standard library names below and none with a matching PicHash. The
     identifier is the library's by where it is declared - namespace
     rapidjson::, std:: or __gnu_cxx::, or the reserved __scrt_ prefix of
     vcruntime - spelled out in full with its template arguments, so a miner
     function that merely takes a std::string never matches, and no listed name
     has a miner type in it (tests/test_stack_vendored.py). The PicHash
     evidence is the finding itself: the same-named function has one PicHash in
     XMRig, xmr-stak and xmrig-proxy, each of which vendors its own copy of
     rapidjson and builds the same standard library headers. This is the
     weakest tier for the standard library and the CRT, and is the only one
     there is. (`validate`'s own classifier is meant to treat standard library
     symbols as expected, but _declaration() reads the last token of the
     stripped name, so a trailing `const`, a `[clone .isra.0]` suffix or an
     MSVC `scalar deleting destructor' hides the namespace from it and these
     are reported as leakage; fixing that classifier is a separate change.)

What is removed: 1,091 functions from the 21 images, 173 identifiers.

  llhttp           92 identifiers, 512 functions: 425 P, 87 W
  Argon2/Blake2b    7 identifiers,  18 functions:  18 P
  rapidjson        42 identifiers, 333 functions:      N
  C++ standard     31 identifiers, 225 functions:      N
  MSVC CRT          1 identifier,    3 functions:      N  (__scrt_common_main_seh, x64)

By family: XMRig 479 (MinGW 60 + 40, Linux 48 + 40, MSVC 121 + 116, musl 31 +
23, x64 + x86), xmr-stak 163 (Linux 20, MinGW 7 + 5, MSVC 68 + 63), xmrig-proxy
449 (MinGW 56 + 39, Linux 47 + 37, MSVC 113 + 108, musl 29 + 20). The counts
are data/<family>/provenance.json's excluded_function_count (for the musl
images the libuv/OpenSSL ones plus these).

Measured and deliberately left in:

  * ge_p1p1_to_p2, ge_p1p1_to_p3, slide, load_3, load_4 (7 PicHashes, the
    OpenSSL findings). Equal to data/OpenSSL 1.1.1w's by PicHash in the MSVC
    images, and for slide on MinGW x64, but they are not OpenSSL's code in
    these images. XMRig and xmrig-proxy compile a complete ed25519 implementation: 61
    ge_*, fe_*, sc_*, load_* and slide names in the MSVC images, of which 26
    do not exist in OpenSSL at all (ge_fromfe_frombytes_vartime, sc_reduce32,
    ge_mul8, ge_double_scalarmult_precomp_vartime2 ...). Two programs derived
    from the same ref10 code compile a few of the same small helpers to the
    same bytes; neither is the other's library. Removing the five names would
    cut holes in the miner's own set (and the musl images hold OpenSSL's own
    copies under the same names beside the miner's; see xmrig.py).
  * rotr64 and blake2b_increment_counter. Both are Blake2b helpers, P against
    data/BLAKE2. blake2b_increment_counter is excluded where all its
    functions are P (MSVC), but RandomX, BLAKE2 and argon2 carry the same
    PicHash, so that finding stands without XMRig. rotr64 has a second
    function in the MSVC images (75% and 56% similar to BLAKE2's), so it is
    kept, and its five-family finding with it.
  * copy_block and xor_block on the GCC and musl images: a second function of
    the same name that is neither P nor 80% similar (RandomX's own Argon2
    reference code), or one the family has no build to compare with.
  * llhttp identifiers with a function that is neither P nor W, so the
    identifier stays whole: 2 on MinGW (XMRig and proxy), 25 and 24 on the Linux
    recipes, 41 on musl, 12 on MSVC. They hold two of the findings that remain:
    llhttp_should_keep_alive (MSVC; the x64 function is 45% similar) and
    llhttp_settings_init (GCC x86 and musl x86; the x64 function is 67% and 70%).
    The others have no P function in that recipe, so no PicHash of theirs is
    shared and they are not findings; they stay in whole.
  * _feclearexcept, _fesetround, ___mingw_has_sse (MinGW x86; shared with
    RandomX): libmingwex and libgcc code the glue baseline does not list. No
    corpus family carries it to compare with and no namespace says whose it
    is; there is no evidence beyond the name, so it stays.
"""

import re


# llhttp: XMRig_6.25.0, xmrig-proxy_6.26.0
_LLHTTP_1 = (
    '_llhttp__before_headers_complete',
    '_llhttp__debug',
    '_llhttp__internal__c_mul_add_status_code',
    '_llhttp__internal_execute',
    '_llhttp__on_body',
    '_llhttp__on_chunk_complete',
    '_llhttp__on_chunk_extension_name',
    '_llhttp__on_chunk_extension_name_complete',
    '_llhttp__on_chunk_extension_value',
    '_llhttp__on_chunk_extension_value_complete',
    '_llhttp__on_chunk_header',
    '_llhttp__on_header_field',
    '_llhttp__on_header_field_complete',
    '_llhttp__on_header_value',
    '_llhttp__on_header_value_complete',
    '_llhttp__on_headers_complete',
    '_llhttp__on_message_begin',
    '_llhttp__on_message_complete',
    '_llhttp__on_method',
    '_llhttp__on_method_complete',
    '_llhttp__on_protocol',
    '_llhttp__on_protocol_complete',
    '_llhttp__on_reset',
    '_llhttp__on_status',
    '_llhttp__on_status_complete',
    '_llhttp__on_url',
    '_llhttp__on_url_complete',
    '_llhttp__on_version',
    '_llhttp__on_version_complete',
    '_llhttp_finish',
    '_llhttp_init',
    '_llhttp_message_needs_eof',
    '_llhttp_reset',
    '_llhttp_settings_init',
    '_llhttp_should_keep_alive',
    '_llhttp_status_name',
    'llhttp__after_message_complete',
    'llhttp__before_headers_complete',
    'llhttp__debug',
    'llhttp__internal__c_mul_add_content_length',
    'llhttp__internal__c_mul_add_content_length_1',
    'llhttp__internal__c_mul_add_status_code',
    'llhttp__internal_execute',
    'llhttp__internal_init',
    'llhttp__on_body',
    'llhttp__on_chunk_complete',
    'llhttp__on_chunk_extension_name',
    'llhttp__on_chunk_extension_name_complete',
    'llhttp__on_chunk_extension_value',
    'llhttp__on_chunk_extension_value_complete',
    'llhttp__on_chunk_header',
    'llhttp__on_header_field',
    'llhttp__on_header_field_complete',
    'llhttp__on_header_value',
    'llhttp__on_header_value_complete',
    'llhttp__on_headers_complete',
    'llhttp__on_message_begin',
    'llhttp__on_message_complete',
    'llhttp__on_method',
    'llhttp__on_method_complete',
    'llhttp__on_protocol',
    'llhttp__on_protocol_complete',
    'llhttp__on_reset',
    'llhttp__on_status',
    'llhttp__on_status_complete',
    'llhttp__on_url',
    'llhttp__on_url_complete',
    'llhttp__on_version',
    'llhttp__on_version_complete',
    'llhttp_finish',
    'llhttp_init',
    'llhttp_message_needs_eof',
    'llhttp_method_name',
    'llhttp_reset',
    'llhttp_set_lenient_chunked_length',
    'llhttp_set_lenient_data_after_close',
    'llhttp_set_lenient_headers',
    'llhttp_set_lenient_keep_alive',
    'llhttp_set_lenient_optional_cr_before_lf',
    'llhttp_set_lenient_optional_crlf_after_chunk',
    'llhttp_set_lenient_optional_lf_after_cr',
    'llhttp_set_lenient_spaces_after_chunk_size',
    'llhttp_set_lenient_transfer_encoding',
    'llhttp_set_lenient_version',
    'llhttp_settings_init',
    'llhttp_should_keep_alive',
    'llhttp_status_name',
)

# argon2: XMRig_6.25.0
_ARGON2_1 = (
    'copy_block',
    'xor_block',
)

# rapidjson: XMRig_6.25.0, xmr-stak_2.10.8_mingw, xmrig-proxy_6.26.0
_RAPIDJSON_1 = (
    'rapidjson::internal::Stack<rapidjson::CrtAllocator>::Destroy()',
    'void rapidjson::internal::Stack<rapidjson::CrtAllocator>::Expand<char>(unsigned long long)',
)

# stdlib: XMRig_6.25.0, xmr-stak_2.10.8_mingw, xmrig-proxy_6.26.0
_STDLIB_1 = (
    'std::__cxx11::regex_traits<char>::_RegexMask std::__cxx11::regex_traits<char>::lookup_classname<char const*>(char const*, char const*, bool) const',
    'std::__cxx11::regex_traits<char>::isctype(char, std::__cxx11::regex_traits<char>::_RegexMask) const (.isra.0)',
    'std::__cxx11::regex_traits<char>::value(char, int) const (.isra.0)',
)

# llhttp: XMRig_6.25.0_linux
_LLHTTP_2 = (
    'llhttp__before_headers_complete',
    'llhttp__internal__c_mul_add_status_code',
    'llhttp__on_chunk_complete',
    'llhttp__on_chunk_extension_name_complete',
    'llhttp__on_chunk_extension_value_complete',
    'llhttp__on_chunk_header',
    'llhttp__on_header_field_complete',
    'llhttp__on_header_value_complete',
    'llhttp__on_message_begin',
    'llhttp__on_message_complete',
    'llhttp__on_method_complete',
    'llhttp__on_protocol_complete',
    'llhttp__on_reset',
    'llhttp__on_status_complete',
    'llhttp__on_url_complete',
    'llhttp__on_version_complete',
    'llhttp_message_needs_eof',
    'llhttp_set_lenient_chunked_length',
    'llhttp_set_lenient_data_after_close',
    'llhttp_set_lenient_headers',
    'llhttp_set_lenient_keep_alive',
    'llhttp_set_lenient_optional_cr_before_lf',
    'llhttp_set_lenient_optional_crlf_after_chunk',
    'llhttp_set_lenient_optional_lf_after_cr',
    'llhttp_set_lenient_spaces_after_chunk_size',
    'llhttp_set_lenient_transfer_encoding',
    'llhttp_set_lenient_version',
    'llhttp_should_keep_alive',
)

# rapidjson: XMRig_6.25.0_linux, XMRig_6.25.0_musl, xmr-stak_2.10.8_linux, xmrig-proxy_6.26.0_linux, xmrig-proxy_6.26.0_musl
_RAPIDJSON_2 = (
    'rapidjson::internal::Stack<rapidjson::CrtAllocator>::Destroy()',
    'void rapidjson::internal::Stack<rapidjson::CrtAllocator>::Expand<char>(unsigned long)',
)

# stdlib: XMRig_6.25.0_linux, xmr-stak_2.10.8_linux, xmrig-proxy_6.26.0_linux
_STDLIB_2 = (
    '__gnu_cxx::__normal_iterator<char*, std::vector<char, std::allocator<char> > > std::__unique<__gnu_cxx::__normal_iterator<char*, std::vector<char, std::allocator<char> > >, __gnu_cxx::__ops::_Iter_equal_to_iter>(__gnu_cxx::__normal_iterator<char*, std::vector<char, std::allocator<char> > >, __gnu_cxx::__normal_iterator<char*, std::vector<char, std::allocator<char> > >, __gnu_cxx::__ops::_Iter_equal_to_iter) [clone .isra.0]',
    'std::_Rb_tree<long, std::pair<long const, long>, std::_Select1st<std::pair<long const, long> >, std::less<long>, std::allocator<std::pair<long const, long> > >::_M_get_insert_unique_pos(long const&) [clone .isra.0]',
    'std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > std::__cxx11::regex_traits<char>::lookup_collatename<char const*>(char const*, char const*) const',
    'std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > std::__cxx11::regex_traits<char>::transform_primary<char const*>(char const*, char const*) const',
    'std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::operator=(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&) [clone .isra.0]',
    'std::__cxx11::regex_traits<char>::_RegexMask std::__cxx11::regex_traits<char>::lookup_classname<char const*>(char const*, char const*, bool) const',
    'std::__cxx11::regex_traits<char>::isctype(char, std::__cxx11::regex_traits<char>::_RegexMask) const [clone .isra.0]',
    'std::vector<std::__cxx11::sub_match<__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >, std::allocator<std::__cxx11::sub_match<__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > > >::operator=(std::vector<std::__cxx11::sub_match<__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >, std::allocator<std::__cxx11::sub_match<__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > > > const&) [clone .isra.0]',
    'void std::__adjust_heap<__gnu_cxx::__normal_iterator<char*, std::vector<char, std::allocator<char> > >, long, char, __gnu_cxx::__ops::_Iter_less_iter>(__gnu_cxx::__normal_iterator<char*, std::vector<char, std::allocator<char> > >, long, long, char, __gnu_cxx::__ops::_Iter_less_iter) [clone .isra.0]',
    'void std::__adjust_heap<__gnu_cxx::__normal_iterator<unsigned short*, std::vector<unsigned short, std::allocator<unsigned short> > >, long, unsigned short, __gnu_cxx::__ops::_Iter_less_iter>(__gnu_cxx::__normal_iterator<unsigned short*, std::vector<unsigned short, std::allocator<unsigned short> > >, long, long, unsigned short, __gnu_cxx::__ops::_Iter_less_iter) [clone .isra.0]',
    'void std::__adjust_heap<std::reverse_iterator<unsigned long*>, long, unsigned long, __gnu_cxx::__ops::_Iter_less_iter>(std::reverse_iterator<unsigned long*>, long, long, unsigned long, __gnu_cxx::__ops::_Iter_less_iter) [clone .isra.0]',
    'void std::__introsort_loop<__gnu_cxx::__normal_iterator<char*, std::vector<char, std::allocator<char> > >, long, __gnu_cxx::__ops::_Iter_less_iter>(__gnu_cxx::__normal_iterator<char*, std::vector<char, std::allocator<char> > >, __gnu_cxx::__normal_iterator<char*, std::vector<char, std::allocator<char> > >, long, __gnu_cxx::__ops::_Iter_less_iter) [clone .isra.0]',
    'void std::__introsort_loop<std::reverse_iterator<unsigned long*>, long, __gnu_cxx::__ops::_Iter_less_iter>(std::reverse_iterator<unsigned long*>, std::reverse_iterator<unsigned long*>, long, __gnu_cxx::__ops::_Iter_less_iter) [clone .isra.0]',
)

# llhttp: XMRig_6.25.0_msvc, xmrig-proxy_6.26.0_msvc
_LLHTTP_3 = (
    'llhttp__after_headers_complete',
    'llhttp__before_headers_complete',
    'llhttp__debug',
    'llhttp__internal__c_mul_add_content_length',
    'llhttp__internal__c_mul_add_content_length_1',
    'llhttp__internal__c_mul_add_status_code',
    'llhttp__internal_execute',
    'llhttp__internal_init',
    'llhttp__on_chunk_complete',
    'llhttp__on_chunk_extension_name_complete',
    'llhttp__on_chunk_extension_value_complete',
    'llhttp__on_chunk_header',
    'llhttp__on_header_field_complete',
    'llhttp__on_header_value_complete',
    'llhttp__on_headers_complete',
    'llhttp__on_message_begin',
    'llhttp__on_message_complete',
    'llhttp__on_method_complete',
    'llhttp__on_protocol_complete',
    'llhttp__on_reset',
    'llhttp__on_status_complete',
    'llhttp__on_url_complete',
    'llhttp__on_version_complete',
    'llhttp_errno_name',
    'llhttp_finish',
    'llhttp_init',
    'llhttp_message_needs_eof',
    'llhttp_method_name',
    'llhttp_reset',
    'llhttp_set_lenient_chunked_length',
    'llhttp_set_lenient_data_after_close',
    'llhttp_set_lenient_headers',
    'llhttp_set_lenient_keep_alive',
    'llhttp_set_lenient_optional_cr_before_lf',
    'llhttp_set_lenient_optional_crlf_after_chunk',
    'llhttp_set_lenient_optional_lf_after_cr',
    'llhttp_set_lenient_spaces_after_chunk_size',
    'llhttp_set_lenient_transfer_encoding',
    'llhttp_set_lenient_version',
    'llhttp_settings_init',
    'llhttp_status_name',
    'llparse__match_sequence_id',
    'llparse__match_sequence_to_lower',
    'llparse__match_sequence_to_lower_unsafe',
)

# argon2: XMRig_6.25.0_msvc
_ARGON2_2 = (
    'b64_byte_to_char',
    'b64_char_to_byte',
    'blake2b_increment_counter',
    'blake2b_init0',
    'copy_block',
    'decode_decimal',
    'xor_block',
)

# rapidjson: XMRig_6.25.0_msvc, xmr-stak_2.10.8_msvc, xmr-stak_2.10.8_msvc_x86, xmrig-proxy_6.26.0_msvc
_RAPIDJSON_3 = (
    'rapidjson::CrtAllocator::Realloc',
    'rapidjson::GenericDocument<rapidjson::UTF8<char>,rapidjson::MemoryPoolAllocator<rapidjson::CrtAllocator>,rapidjson::CrtAllocator>::ClearStack',
    'rapidjson::GenericDocument<rapidjson::UTF8<char>,rapidjson::MemoryPoolAllocator<rapidjson::CrtAllocator>,rapidjson::CrtAllocator>::ClearStackOnExit::~ClearStackOnExit',
    "rapidjson::GenericMember<rapidjson::UTF8<char>,rapidjson::MemoryPoolAllocator<rapidjson::CrtAllocator> >::`scalar deleting destructor'",
    'rapidjson::GenericValue<rapidjson::UTF8<char>,rapidjson::MemoryPoolAllocator<rapidjson::CrtAllocator> >::GenericValue<rapidjson::UTF8<char>,rapidjson::MemoryPoolAllocator<rapidjson::CrtAllocator> >',
    'rapidjson::GenericValue<rapidjson::UTF8<char>,rapidjson::MemoryPoolAllocator<rapidjson::CrtAllocator> >::SetArrayRaw',
    'rapidjson::GenericValue<rapidjson::UTF8<char>,rapidjson::MemoryPoolAllocator<rapidjson::CrtAllocator> >::SetNull',
    'rapidjson::GenericValue<rapidjson::UTF8<char>,rapidjson::MemoryPoolAllocator<rapidjson::CrtAllocator> >::SetObjectRaw',
    'rapidjson::GenericValue<rapidjson::UTF8<char>,rapidjson::MemoryPoolAllocator<rapidjson::CrtAllocator> >::StringEqual<rapidjson::MemoryPoolAllocator<rapidjson::CrtAllocator> >',
    "rapidjson::GenericValue<rapidjson::UTF8<char>,rapidjson::MemoryPoolAllocator<rapidjson::CrtAllocator> >::`scalar deleting destructor'",
    'rapidjson::GetParseError_En',
    'rapidjson::SkipWhitespace<rapidjson::GenericInsituStringStream<rapidjson::UTF8<char> > >',
    'rapidjson::Transcoder<rapidjson::UTF8<char>,rapidjson::UTF8<char> >::Transcode<rapidjson::GenericInsituStringStream<rapidjson::UTF8<char> >,rapidjson::GenericInsituStringStream<rapidjson::UTF8<char> > >',
    'rapidjson::UTF8<char>::Encode<rapidjson::GenericInsituStringStream<rapidjson::UTF8<char> > >',
    'rapidjson::internal::BigInteger::BigInteger',
    'rapidjson::internal::BigInteger::Compare',
    'rapidjson::internal::BigInteger::Difference',
    'rapidjson::internal::BigInteger::MulAdd64',
    'rapidjson::internal::BigInteger::MultiplyPow5',
    'rapidjson::internal::BigInteger::operator*=',
    'rapidjson::internal::BigInteger::operator+=',
    'rapidjson::internal::BigInteger::operator==',
    'rapidjson::internal::CheckWithinHalfULP',
    'rapidjson::internal::DiyFp::operator*',
    'rapidjson::internal::Double::EffectiveSignificandSize',
    'rapidjson::internal::Double::IntegerExponent',
    'rapidjson::internal::Double::IntegerSignificand',
    'rapidjson::internal::Double::IsNormal',
    'rapidjson::internal::Double::NextPositiveDouble',
    'rapidjson::internal::FastPath',
    'rapidjson::internal::GetCachedPower10',
    'rapidjson::internal::GetCachedPowerByIndex',
    'rapidjson::internal::Stack<rapidjson::CrtAllocator>::Expand<char>',
    'rapidjson::internal::Stack<rapidjson::CrtAllocator>::Expand<rapidjson::GenericValue<rapidjson::UTF8<char>,rapidjson::MemoryPoolAllocator<rapidjson::CrtAllocator> > >',
    'rapidjson::internal::Stack<rapidjson::CrtAllocator>::Expand<unsigned int>',
    'rapidjson::internal::Stack<rapidjson::CrtAllocator>::Resize',
    'rapidjson::internal::Stack<rapidjson::CrtAllocator>::ShrinkToFit',
    'rapidjson::internal::StrtodFast',
    'rapidjson::internal::StrtodNormalPrecision',
)

# stdlib: XMRig_6.25.0_msvc, xmr-stak_2.10.8_msvc, xmrig-proxy_6.26.0_msvc
_STDLIB_3 = (
    "`std::_Builder<char const *,char,std::regex_traits<char> >::_Add_equiv'::`1'::dtor$2",
    "`std::_Lookup_equiv<char,std::regex_traits<char> >'::`1'::dtor$4",
    "`std::collate<char>::do_transform'::`1'::dtor$0",
    "`std::getline<char,std::char_traits<char>,std::allocator<char> >'::`1'::catch$4",
    "std::_Buf<char>::`scalar deleting destructor'",
    "std::_Node_assert::`scalar deleting destructor'",
    "std::_Node_class<char,std::regex_traits<char> >::`scalar deleting destructor'",
    "std::_Node_if::`scalar deleting destructor'",
    "std::_Node_str<char>::`scalar deleting destructor'",
    "std::_Root_node::`scalar deleting destructor'",
    "std::_Sequence<char>::`scalar deleting destructor'",
    "std::basic_ifstream<char,std::char_traits<char> >::`scalar deleting destructor'",
    "std::basic_ifstream<char,std::char_traits<char> >::`vbase destructor'",
    "std::basic_ofstream<char,std::char_traits<char> >::`scalar deleting destructor'",
    "std::basic_ofstream<char,std::char_traits<char> >::`vbase destructor'",
    "std::collate<char>::`scalar deleting destructor'",
)

# crt: XMRig_6.25.0_msvc, xmr-stak_2.10.8_msvc, xmrig-proxy_6.26.0_msvc
_CRT_1 = (
    '__scrt_common_main_seh',
)

# llhttp: XMRig_6.25.0_musl, xmrig-proxy_6.26.0_musl
_LLHTTP_4 = (
    'llhttp_message_needs_eof',
    'llhttp_set_lenient_chunked_length',
    'llhttp_set_lenient_data_after_close',
    'llhttp_set_lenient_headers',
    'llhttp_set_lenient_keep_alive',
    'llhttp_set_lenient_optional_cr_before_lf',
    'llhttp_set_lenient_optional_crlf_after_chunk',
    'llhttp_set_lenient_optional_lf_after_cr',
    'llhttp_set_lenient_spaces_after_chunk_size',
    'llhttp_set_lenient_transfer_encoding',
    'llhttp_set_lenient_version',
    'llhttp_should_keep_alive',
)

# stdlib: XMRig_6.25.0_musl, xmrig-proxy_6.26.0_musl
_STDLIB_4 = (
    '__gnu_cxx::__normal_iterator<char*, std::vector<char, std::allocator<char> > > std::__unique<__gnu_cxx::__normal_iterator<char*, std::vector<char, std::allocator<char> > >, __gnu_cxx::__ops::_Iter_equal_to_iter>(__gnu_cxx::__normal_iterator<char*, std::vector<char, std::allocator<char> > >, __gnu_cxx::__normal_iterator<char*, std::vector<char, std::allocator<char> > >, __gnu_cxx::__ops::_Iter_equal_to_iter) [clone .isra.0]',
    'std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > std::__cxx11::regex_traits<char>::lookup_collatename<char const*>(char const*, char const*) const',
    'std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > std::__cxx11::regex_traits<char>::transform_primary<char const*>(char const*, char const*) const',
    'std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::operator=(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&) [clone .isra.0]',
    'std::__cxx11::regex_traits<char>::_RegexMask std::__cxx11::regex_traits<char>::lookup_classname<char const*>(char const*, char const*, bool) const',
    'std::__cxx11::regex_traits<char>::isctype(char, std::__cxx11::regex_traits<char>::_RegexMask) const [clone .isra.0]',
    'std::vector<std::__cxx11::sub_match<__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >, std::allocator<std::__cxx11::sub_match<__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > > >::operator=(std::vector<std::__cxx11::sub_match<__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >, std::allocator<std::__cxx11::sub_match<__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > > > const&) [clone .isra.0]',
    'void std::__adjust_heap<__gnu_cxx::__normal_iterator<char*, std::vector<char, std::allocator<char> > >, long, char, __gnu_cxx::__ops::_Iter_less_iter>(__gnu_cxx::__normal_iterator<char*, std::vector<char, std::allocator<char> > >, long, long, char, __gnu_cxx::__ops::_Iter_less_iter) [clone .isra.0]',
    'void std::__adjust_heap<__gnu_cxx::__normal_iterator<unsigned short*, std::vector<unsigned short, std::allocator<unsigned short> > >, long, unsigned short, __gnu_cxx::__ops::_Iter_less_iter>(__gnu_cxx::__normal_iterator<unsigned short*, std::vector<unsigned short, std::allocator<unsigned short> > >, long, long, unsigned short, __gnu_cxx::__ops::_Iter_less_iter) [clone .isra.0]',
    'void std::__adjust_heap<std::reverse_iterator<unsigned long*>, long, unsigned long, __gnu_cxx::__ops::_Iter_less_iter>(std::reverse_iterator<unsigned long*>, long, long, unsigned long, __gnu_cxx::__ops::_Iter_less_iter) [clone .isra.0]',
    'void std::__introsort_loop<__gnu_cxx::__normal_iterator<char*, std::vector<char, std::allocator<char> > >, long, __gnu_cxx::__ops::_Iter_less_iter>(__gnu_cxx::__normal_iterator<char*, std::vector<char, std::allocator<char> > >, __gnu_cxx::__normal_iterator<char*, std::vector<char, std::allocator<char> > >, long, __gnu_cxx::__ops::_Iter_less_iter) [clone .isra.0]',
    'void std::__introsort_loop<std::reverse_iterator<unsigned long*>, long, __gnu_cxx::__ops::_Iter_less_iter>(std::reverse_iterator<unsigned long*>, std::reverse_iterator<unsigned long*>, long, __gnu_cxx::__ops::_Iter_less_iter) [clone .isra.0]',
)

# stdlib: xmr-stak_2.10.8_msvc_x86
_STDLIB_5 = (
    "std::_Buf<char>::`scalar deleting destructor'",
    "std::_Node_assert::`scalar deleting destructor'",
    "std::_Node_class<char,std::regex_traits<char> >::`scalar deleting destructor'",
    "std::_Node_if::`scalar deleting destructor'",
    "std::_Node_str<char>::`scalar deleting destructor'",
    "std::_Root_node::`scalar deleting destructor'",
    "std::_Sequence<char>::`scalar deleting destructor'",
    "std::basic_ifstream<char,std::char_traits<char> >::`scalar deleting destructor'",
    "std::basic_ifstream<char,std::char_traits<char> >::`vbase destructor'",
    "std::basic_ofstream<char,std::char_traits<char> >::`scalar deleting destructor'",
    "std::basic_ofstream<char,std::char_traits<char> >::`vbase destructor'",
    "std::collate<char>::`scalar deleting destructor'",
)

# llhttp: xmrig-proxy_6.26.0_linux
_LLHTTP_5 = (
    'llhttp__before_headers_complete',
    'llhttp__internal__c_mul_add_status_code',
    'llhttp__on_chunk_complete',
    'llhttp__on_chunk_extension_name_complete',
    'llhttp__on_chunk_extension_value_complete',
    'llhttp__on_chunk_header',
    'llhttp__on_header_field_complete',
    'llhttp__on_header_value_complete',
    'llhttp__on_headers_complete',
    'llhttp__on_message_begin',
    'llhttp__on_message_complete',
    'llhttp__on_method_complete',
    'llhttp__on_protocol_complete',
    'llhttp__on_reset',
    'llhttp__on_status_complete',
    'llhttp__on_url_complete',
    'llhttp__on_version_complete',
    'llhttp_message_needs_eof',
    'llhttp_set_lenient_chunked_length',
    'llhttp_set_lenient_data_after_close',
    'llhttp_set_lenient_headers',
    'llhttp_set_lenient_keep_alive',
    'llhttp_set_lenient_optional_cr_before_lf',
    'llhttp_set_lenient_optional_crlf_after_chunk',
    'llhttp_set_lenient_optional_lf_after_cr',
    'llhttp_set_lenient_spaces_after_chunk_size',
    'llhttp_set_lenient_transfer_encoding',
    'llhttp_set_lenient_version',
    'llhttp_should_keep_alive',
)


NAMES = {
    'XMRig_6.25.0': {
        'llhttp': _LLHTTP_1,
        'argon2': _ARGON2_1,
        'rapidjson': _RAPIDJSON_1,
        'stdlib': _STDLIB_1,
    },
    'XMRig_6.25.0_linux': {
        'llhttp': _LLHTTP_2,
        'rapidjson': _RAPIDJSON_2,
        'stdlib': _STDLIB_2,
    },
    'XMRig_6.25.0_msvc': {
        'llhttp': _LLHTTP_3,
        'argon2': _ARGON2_2,
        'rapidjson': _RAPIDJSON_3,
        'stdlib': _STDLIB_3,
        'crt': _CRT_1,
    },
    'XMRig_6.25.0_musl': {
        'llhttp': _LLHTTP_4,
        'rapidjson': _RAPIDJSON_2,
        'stdlib': _STDLIB_4,
    },
    'xmr-stak_2.10.8_linux': {
        'rapidjson': _RAPIDJSON_2,
        'stdlib': _STDLIB_2,
    },
    'xmr-stak_2.10.8_mingw': {
        'rapidjson': _RAPIDJSON_1,
        'stdlib': _STDLIB_1,
    },
    'xmr-stak_2.10.8_msvc': {
        'rapidjson': _RAPIDJSON_3,
        'stdlib': _STDLIB_3,
        'crt': _CRT_1,
    },
    'xmr-stak_2.10.8_msvc_x86': {
        'rapidjson': _RAPIDJSON_3,
        'stdlib': _STDLIB_5,
    },
    'xmrig-proxy_6.26.0': {
        'llhttp': _LLHTTP_1,
        'rapidjson': _RAPIDJSON_1,
        'stdlib': _STDLIB_1,
    },
    'xmrig-proxy_6.26.0_linux': {
        'llhttp': _LLHTTP_5,
        'rapidjson': _RAPIDJSON_2,
        'stdlib': _STDLIB_2,
    },
    'xmrig-proxy_6.26.0_msvc': {
        'llhttp': _LLHTTP_3,
        'rapidjson': _RAPIDJSON_3,
        'stdlib': _STDLIB_3,
        'crt': _CRT_1,
    },
    'xmrig-proxy_6.26.0_musl': {
        'llhttp': _LLHTTP_4,
        'rapidjson': _RAPIDJSON_2,
        'stdlib': _STDLIB_4,
    },
}


CATEGORIES = ("llhttp", "argon2", "rapidjson", "stdlib", "crt")


def exact_names(names):
    """One anchored regular expression over exact function names.

    The names are escaped and joined, so nothing but those strings match: not
    a prefix, not a method of the same class, not a decorated variant that is
    not listed (the x86 MinGW ``_llhttp_init`` is a name of its own).
    """
    return r"^(?:%s)$" % "|".join(re.escape(name) for name in sorted(set(names)))


def patterns(recipe):
    """The exclude_functions patterns of one recipe, one per category."""
    table = NAMES[recipe]
    return [exact_names(table[category])
            for category in CATEGORIES if table.get(category)]
