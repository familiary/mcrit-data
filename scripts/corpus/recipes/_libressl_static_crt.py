"""Names of the statically linked MSVC C runtime in the LibreSSL /MT images.

Used by libressl_v141xp_mt_msvc.py, whose docstring has the measurement. A
/MT image carries the static UCRT and vcruntime beside the library. The glue
baseline removes the part of it its probes link (name and PicHash both
equal); the rest goes by name, through Recipe.exclude_functions, with the
patterns built here.

How the names were found. LibreSSL 3.1.0 is in data/LibreSSL twice from the
same tarball, compiler, toolset and flags: /MD (libressl_v141xp_msvc.py),
where the C runtime is imported, and /MT. A function name of the /MT image
that the /MD image of the same component and architecture does not hold
cannot come from the tarball; those names, over the three components, are
the candidates (2229 on x86, 2307 on x64, "$+0x.." fragment suffixes
stripped). Each was then checked against the identifiers of the tarball's
crypto/, ssl/, tls/ and include/ trees, and the full list was read. One
candidate was LibreSSL's and is not listed: general_allocate_string
(crypto/ui/ui_lib.c), a static function that is a function of its own in
the x64 /MT image only. strnlen is in the tree too (crypto/compat/strnlen.c)
but is not compiled, HAVE_STRNLEN being set; the body here is the UCRT's.

Three kinds of pattern, none of which matches a single function name of the
six /MD images other than the C runtime import thunks named below:

  * C++ names: anything with "::", "<", a backquote or a space. LibreSSL is
    C; the UCRT is C++ (lambdas, __crt_seh_guarded_call<>, common_*<>
    templates, __crt_stdio_output::...). 2084 of the candidate names.
  * The runtime's reserved prefixes __acrt_, __crt_, __vcrt_, __scrt_ and
    __dcrt_ (133 names).
  * Exact names, per architecture, below: C names of the UCRT and vcruntime
    (fwrite, _read_nolock, try_get_FlsAlloc ...) and, on x86, the decorated
    import thunks of kernel32 functions only the runtime calls
    (_CreateThread@24 ...).

x64 has no decoration, so there the /MD image's one-instruction thunk
"jmp [__imp_strerror]" and the /MT image's strerror body carry the same
name and the difference above does not see them. _X64_IMPORTED_UNDER_MD
lists the 26 names of that kind: every name that is a "jmp [mem]" thunk in
a /MD x64 image, is defined in no LibreSSL image, and is a C runtime
function rather than a Windows or Winsock import. (On x86 the thunk is
_strerror and the body strerror, so the first list already has them.)

x86 only: unnamed functions. The x86 /MD images hold none (x86 is built
with OPENSSL_NO_ASM), the /MT ones 7, 6 and 6, the runtime's assembly
fragments, so "^$" is part of the x86 pattern. It is not part of the x64
one: the 35 unnamed functions of the x64 libcrypto are LibreSSL's MASM
routines, 35 in the /MD image as well. That is why the recipe is split by
architecture.

Left in on purpose: GetFullPathNameW and GetModuleFileNameA. They are
one-instruction kernel32 import thunks; each is LibreSSL's own import in one
component (GetModuleFileNameA in libcrypto, GetFullPathNameW in libssl) and
only the runtime's in the others, and a per-recipe pattern cannot tell the
two apart.
"""

import re

_X86_NAMES = """
CountryEnumProc GetLcidFromLanguage GetLocaleNameFromDefault
GetLocaleNameFromLangCountry GetLocaleNameFromLanguage GetTableIndexFromLcid
GetTableIndexFromLocaleName InternalCompareStringA InternalGetLocaleInfoA
LangCountryEnumProc LangCountryEnumProcEx LanguageEnumProc
LanguageEnumProcEx LcidFromHexString LongLongSub ProcessCodePage
TestDefaultCountry TestDefaultLanguage TranslateName _87except _CIlog10
_CIlog10_default _CreateThread@24 _FileTimeToSystemTime@8
_FindFirstFileExA@24 _FindNextFileA@8 _GetConsoleCP@0
_GetCurrentDirectoryW@8 _GetDriveTypeW@4 _GetFullPathNameA@16
_OutputDebugStringA@4 _PeekNamedPipe@24 _SetCurrentDirectoryW@4
_SetEnvironmentVariableA@8 _SystemTimeToTzSpecificLocalTime@12
__SEH_epilog4_GS __SEH_prolog4_GS ___lc_codepage_func ___lc_collate_cp_func
___lc_locale_name_func ___mb_cur_max_func __abstract_cw_sse2
__abstract_sw_sse2 __clearfp_sse2 __clrfp_sse2 __control87_2
__control87_sse2 __ctrlfp_sse2 __doserrno __fFEXP __fFLN __fpe_flt_rounds
__get_abstract_control_sse2 __get_abstract_control_x87
__get_abstract_status_sse2 __get_abstract_status_x87 __get_fpsr_sse2
__get_machine_control __get_machine_control_sse2 __get_machine_status_sse2
__get_machine_status_x87 __hw_cw_sse2 __iscsym __iscsymf __iswcsym
__iswcsymf __lc_wcstolc __libm_error_support __libm_setusermatherr
__loctotime32_t __loctotime64_t __nan2 __nosnan2 __p___mb_cur_max
__p__mbcasemap __p__mbctype __pctype_func __rtatan2inf __rtindfpop
__rtinfpop __rtonepop __rttosnpop __rttospop __rtzerospop __set_fpsr_sse2
__set_statfp_sse2 __setusermatherr __statfp_sse2 __statusfp_sse2
__stdio_common_vfprintf __stdio_common_vfprintf_p __stdio_common_vfprintf_s
__stdio_common_vfscanf __stdio_common_vfwprintf __stdio_common_vfwprintf_p
__stdio_common_vfwprintf_s __stdio_common_vfwscanf
__stdio_common_vsnprintf_s __stdio_common_vsnwprintf_s
__stdio_common_vsprintf __stdio_common_vsprintf_p __stdio_common_vsprintf_s
__stdio_common_vswprintf __stdio_common_vswprintf_p
__stdio_common_vswprintf_s __strncnt __sys_errlist __sys_nerr __tosnan1
__tosnan2 __tzset __wcsnicmp_ascii _abstract_cw _abstract_sw _add_exp
_alloc_osfhnd _atoi64 _atoi64_l _atoi_l _atol_l _atoll_l _callnewh
_calloc_base _ceil_default _ceil_pentium4 _chdrive _chgsign _chgsignf
_chsize_nolock _chsize_s _chvalidchk_l _clearfp _close _close_nolock _commit
_control87 _controlfp _controlfp_s _copysign _copysignf _create_locale
_ctrlfp _d_int _d_inttype _decomp _dtest _errcode _errno _except1 _except2
_execute_onexit_table _expandlocale _fclose_nolock _fcloseall _fd_int
_fdopen _fdtest _fflush_nolock _fgetwc_nolock _fileno _finite _fpclass
_fperrraise _fpreset _fputc_nolock _fputwc_nolock _fread_nolock_s _free_base
_free_locale _free_osfhnd _frnd _fseek_nolock _fseeki64 _fseeki64_nolock
_fstat32 _fstat32i64 _fstat64 _fstat64i32 _ftell_nolock _ftelli64
_ftelli64_nolock _fullpath _fwrite_nolock _get_current_locale _get_exp
_get_fmode _get_fname _get_invalid_parameter_handler _get_osfhandle
_get_sys_err_msg _get_terminate _get_tzname _getcwd _getdcwd _getdrive
_getfpcontrolword _getfpstatusword _getmbcp _gmtime32 _gmtime64 _handle_exc
_hw_cw _i64toa _i64toa_s _i64tow _i64tow_s _initialize_onexit_table
_initterm _initterm_e _invalid_parameter _invoke_watson
_is_c_termination_complete _isalnum_l _isalpha_l _isatty _isblank_l
_ischartype_l _iscntrl_l _iscsym_l _iscsymf_l _isctype _isctype_l _isdigit_l
_isgraph_l _isindst _isindst_nolock _isleadbyte_l _islower_l _ismbbkana_l
_isnan _isprint_l _ispunct_l _isspace_l _isupper_l _iswalnum_l _iswalpha_l
_iswblank_l _iswcntrl_l _iswcsym_l _iswcsymf_l _iswdigit_l _iswgraph_l
_iswlower_l _iswprint_l _iswpunct_l _iswspace_l _iswupper_l _iswxdigit_l
_isxdigit_l _itoa _itoa_s _itow _itow_s _ld_int _ldtest _lock_locales _logb
_lseek _lseek_nolock _lseeki64 _lseeki64_nolock _ltoa _ltoa_s _ltow _ltow_s
_malloc_base _mbsdec_l _mbstowcs_l _mbstowcs_l_helper _mbstowcs_s_l
_mbtowc_l _msize _nextafter _open_osfhandle _powhlp _putc_nolock
_putwc_nolock _putwch _putwch_nolock _query_new_handler _query_new_mode
_raise_exc_ex _read _read_nolock _register_onexit_function
_register_thread_local_exe_atexit_callback _scalb _seh_filter_exe
_set_SSE2_enable _set_bexp _set_controlfp _set_errno_from_matherr
_set_error_mode _set_exp _set_invalid_parameter_handler _set_new_handler
_set_printf_count_output _setfpcontrolword _setfpstatusword _setmbcp
_setmbcp_nolock _setmode _setmode_nolock _snprintf _sopen _sopen_nolock
_sptype _startOneArgErrorHandling _startTwoArgErrorHandling _stat32
_stat32i64 _stat64 _stat64i32 _statusfp _statusfp2 _strdup _strnicmp
_strnicmp_l _strnicoll _strnicoll_l _strtoi64 _strtoi64_l _strtoimax_l
_strtol_l _strtoll_l _strtoui64 _strtoui64_l _strtoul_l _strtoull_l
_strtoumax_l _time32 _time64 _tolower_l _toupper_l _towlower_l _trandisp1
_trandisp2 _tzset _umask _umatherr _ungetc_nolock _ungetwc_nolock
_wcreate_locale _wcserror _wcserror_s _wcsicmp _wcsicmp_l _wcsnicmp
_wcsnicmp_l _wcsnicoll _wcsnicoll_l _wcstoi64 _wcstoi64_l _wcstoimax_l
_wcstol_l _wcstoll_l _wcstombs_l _wcstombs_l_helper _wcstombs_s_l _wcstoui64
_wcstoui64_l _wcstoul_l _wcstoull_l _wcstoumax_l _wctomb_l _wctomb_s_l
_wfdopen _wfullpath _wgetcwd _wgetdcwd _write _write_nolock _wsetlocale
_wsetlocale_get_all _wsetlocale_nolock _wsetlocale_set_cat _wsopen
_wsopen_nolock _wstat32 _wstat32i64 _wstat64 _wstat64i32 _wtoi _wtoi64
_wtoi64_l _wtoi_l _wtol _wtol_l _wtoll _wtoll_l abort atoi atol atoll
call_wfullpath ceil close_os_handle_nolock common_exit common_flush_all
common_fseek common_fseek_binary_mode_read_only_fast_track_nolock
common_fseek_nolock common_ftell_read_mode_nolock
common_ftell_translated_utf8_nolock common_lseek_do_seek_nolock compute_size
compute_year configure_text_mode construct_ptd convert_to_stat_mode
copy_string_into_buffer ctrlevent_capture cvtdate decode_access_flags
decode_open_create_flags decode_options decode_sharing_flags destroy_ptd
do_locale_initialization enum_system_locales_ex_nolock
exit_or_terminate_process fast_check fclose fegetexceptflag fegetround
feholdexcept feof ferror fesetenv fesetexceptflag fetestexcept fflush fgetc
fgets fgetwc fgetws find_or_allocate_unused_stream_nolock fix_grouping
fp_format_a fp_format_e fp_format_e_internal fp_format_f
fp_format_f_internal fp_format_g fp_format_nan_or_infinity fperrraise_with
fprintf fputc fputs fputwc fputwc_binary_nolock fread_s
free_crt_array_internal fseek ftell fwrite getSystemCP get_context_nolock
get_drive_number_from_path get_failure_string get_full_path_name
get_or_create_lc_time get_ptd_buffer get_ptd_head get_std_handle_id
get_terminate_or_default get_tz_environment_variable
has_executable_extension initialize_global_variables
initialize_inherited_file_handles_nolock initialize_lc_time
initialize_multibyte initialize_pointers initialize_stdio_handles_nolock
internal_getptd_noexit internal_islower_l internal_isupper_l
internal_map_lower internal_map_upper is_buffer_valid_nolock is_managed_app
is_root_or_empty is_root_unc_name is_slash is_text_mode
is_usable_drive_or_unc_root is_valid_drive isalnum isalpha isblank iscntrl
isdigit isgraph isleadbyte islower isprint ispunct isspace isupper iswalnum
iswalpha iswascii iswblank iswcntrl iswctype iswdigit iswgraph iswlower
iswprint iswpunct iswspace iswupper iswxdigit isxdigit ldexp localeconv
log10 mbstowcs mbstowcs_s mbtowc nextafter nexttoward pre_initialize putchar
putwchar qsort raise read_character_nolock setSBCS setSBUpLow set_terminate
setmbcp_internal shortsort should_call_terminate_process
should_copy_another_character should_write_error_to_console signal
signal_failed sscanf store_lookahead strcmp strcpy_s strerror strerror_s
strncmp strncpy_s strnlen strtoimax strtol strtoll strtoul strtoull
strtoumax swap terminate tolower toupper translate_ansi_or_utf8_nolock
translate_utf16_from_console_nolock truncate_ctrl_z_if_present
try_cor_exit_process try_get_AreFileApisANSI try_get_CompareStringEx
try_get_EnumSystemLocalesEx try_get_FlsAlloc try_get_FlsFree
try_get_FlsGetValue try_get_FlsSetValue try_get_GetActiveWindow
try_get_GetCurrentPackageId try_get_GetDateFormatEx
try_get_GetEnabledXStateFeatures try_get_GetFileInformationByHandleEx
try_get_GetLastActivePopup try_get_GetLocaleInfoEx
try_get_GetProcessWindowStation try_get_GetSystemTimePreciseAsFileTime
try_get_GetTimeFormatEx try_get_GetUserDefaultLocaleName
try_get_GetUserObjectInformationW try_get_GetXStateFeaturesMask
try_get_InitializeCriticalSectionEx try_get_IsValidLocaleName
try_get_LCIDToLocaleName try_get_LCMapStringEx try_get_LocaleNameToLCID
try_get_LocateXStateFeature try_get_MessageBoxA try_get_MessageBoxW
try_get_RoInitialize try_get_RoUninitialize try_get_SetThreadStackGuarantee
try_get_SystemFunction036 try_get_first_available_module try_get_function
try_get_module try_get_proc_address_from_first_available_module
try_get_ptd_head try_load_library_from_system_directory
tzset_from_environment_nolock tzset_from_system_nolock tzset_nolock ungetc
ungetwc ungetwc_binary_mode_nolock ungetwc_text_mode_nolock
uninitialize_allocated_memory vsnprintf wcscat_s wcscpy_s wcscspn wcsncmp
wcsncnt wcsncpy_s wcsnlen wcspbrk wcsrchr wcstoimax wcstol wcstoll wcstombs
wcstombs_s wcstoul wcstoull wcstoumax wctomb wctomb_s write_binary_nolock
write_double_translated_ansi_nolock write_double_translated_unicode_nolock
write_requires_double_translation_nolock write_string_to_console
write_text_ansi_nolock write_text_utf16le_nolock write_text_utf8_nolock
x_ismbbtype_l
""".split()

_X64_NAMES = """
CountryEnumProc CreateThread DecompFuncInfo FileTimeToSystemTime
FindFirstFileExA FindNextFileA GetConsoleCP GetCurrentDirectoryW
GetDriveTypeW GetFullPathNameA GetLcidFromCountry GetLcidFromLanguage
GetLocaleNameFromLangCountry GetLocaleNameFromLanguage GetTableIndexFromLcid
GetTableIndexFromLocaleName InternalCompareStringA InternalGetLocaleInfoA
LangCountryEnumProc LangCountryEnumProcEx LanguageEnumProc LcidFromHexString
LongLongSub OutputDebugStringA PeekNamedPipe ProcessCodePage ReadUnsigned
SetCurrentDirectoryW SetEnvironmentVariableA SystemTimeToTzSpecificLocalTime
TestDefaultCountry TestDefaultLanguage TranslateName __ascii_strnicmp
__doserrno __fpe_flt_rounds __get_machine_status __iscsym __iscsymf
__iswcsym __iswcsymf __lc_wcstolc __loctotime32_t __loctotime64_t
__p__mbcasemap __p__mbctype __setusermatherr __stdio_common_vfprintf
__stdio_common_vfprintf_p __stdio_common_vfprintf_s __stdio_common_vfwprintf
__stdio_common_vfwprintf_p __stdio_common_vfwprintf_s
__stdio_common_vsnprintf_s __stdio_common_vsnwprintf_s
__stdio_common_vsprintf __stdio_common_vsprintf_p __stdio_common_vsprintf_s
__stdio_common_vsscanf __stdio_common_vswprintf __stdio_common_vswprintf_p
__stdio_common_vswprintf_s __stdio_common_vswscanf __sys_errlist __sys_nerr
__tzset __wcsnicmp_ascii _abstract_cw _abstract_sw _add_exp _alloc_osfhnd
_atoi64 _atoi64_l _atoi_l _atol_l _atoll_l _call_matherr _callnewh _chdrive
_chsize_nolock _chsize_s _chvalidchk_l _clearfp _close_nolock _clrfp _commit
_configure_narrow_argv _configure_wide_argv _create_locale _ctrlfp
_ctrlfp$filt$0 _decomp _errcode _errno _except1 _except2 _exception_enabled
_execute_onexit_table _expandlocale _fclose_nolock _fcloseall _fclrf
_fflush_nolock _fgetwc_nolock _fgetwchar _fileno _flushall _fputc_nolock
_fputwc_nolock _fputwchar _fread_nolock_s _free_base _free_osfhnd _frnd
_fseek_nolock _fseeki64 _fseeki64_nolock _fstat32 _fstat32i64 _fstat64
_ftell_nolock _ftelli64 _ftelli64_nolock _fullpath _fwrite_nolock
_get_FMA3_enable _get_current_locale _get_doserrno _get_errno _get_exp
_get_fmode _get_fname _get_fpsr _get_initial_narrow_environment
_get_initial_wide_environment _get_invalid_parameter_handler _get_osfhandle
_get_sys_err_msg _get_tzname _getcwd _getdcwd _getdrive _getfpcontrolword
_getfpstatusword _handle_error _handle_errorf _handle_exc _handle_nan
_handle_nanf _hw_cw _initialize_onexit_table _initterm _initterm_e
_invalid_parameter _invoke_watson _invoke_watson_if_error
_is_c_termination_complete _isalnum_l _isalpha_l _isatty _isblank_l
_ischartype_l _iscntrl_l _iscsym_l _iscsymf_l _isctype _isctype_l _isdigit_l
_isgraph_l _isindst_nolock _isleadbyte_l _islower_l _ismbbkana _ismbbkana_l
_isprint_l _ispunct_l _isspace_l _isupper_l _iswalnum_l _iswalpha_l
_iswblank_l _iswcntrl_l _iswcsym_l _iswcsymf_l _iswdigit_l _iswgraph_l
_iswlower_l _iswprint_l _iswpunct_l _iswspace_l _iswupper_l _iswxdigit_l
_isxdigit_l _lock_locales _log_special_common _logf_special_common
_lseek_nolock _lseeki64 _lseeki64_nolock _mbsdec _mbsdec_l _mbstowcs_l
_mbstowcs_l_helper _mbstowcs_s_l _mbtowc_l _msize _open_osfhandle
_open_osfhandle$fin$0 _openfile _putc_nolock _putwch_nolock
_query_new_handler _query_new_mode _raise_exc _raise_exc_ex _read$fin$0
_read_nolock _realloc_base _recalloc_base
_register_thread_local_exe_atexit_callback _seh_filter_exe _set_FMA3_enable
_set_bexp _set_controlfp _set_doserrno _set_errno_from_matherr
_set_error_mode _set_exp _set_fpsr _set_new_handler _set_statfp
_setfpcontrolword _setfpstatusword _setmbcp _setmbcp_nolock _setmode
_setmode$fin$0 _setmode_nolock _snprintf _sopen _sopen_nolock _sptype
_stat32 _stat32i64 _stat64 _statfp _statusfp _strnicmp _strnicmp_l
_strnicoll _strnicoll_l _strtoi64 _strtoi64_l _strtoimax_l _strtol_l
_strtoll_l _strtoui64 _strtoui64_l _strtoul_l _strtoull_l _strtoumax_l
_time32 _time64 _timespec32_get _timespec64_get _tolower_l _toupper_l
_towlower_l _tzset _umask _umatherr _ungetc_nolock _ungetwc_nolock
_updatetlocinfoEx_nolock _wcscats _wcserror _wcserror_s _wcsicmp _wcsicmp_l
_wcsnicmp _wcsnicmp_l _wcsnicoll _wcsnicoll_l _wcstoi64 _wcstoi64_l
_wcstoimax_l _wcstol_l _wcstoll_l _wcstombs_l _wcstombs_l_helper
_wcstombs_s_l _wcstoui64 _wcstoui64_l _wcstoul_l _wcstoull_l _wcstoumax_l
_wctomb_l _wctomb_s_l _wfdopen _wfullpath _wgetcwd _wgetdcwd _wopen
_wopenfile _write$fin$0 _write_nolock _wsetlocale _wsetlocale_get_all
_wsetlocale_nolock _wsetlocale_set_cat _wsopen _wsopen_nolock _wstat32
_wstat32i64 _wstat64 _wstat64i32 _wtoi _wtoi64 _wtoi64_l _wtoi_l _wtol
_wtol_l _wtoll _wtoll_l abort atol atoll call_wfullpath ceil
close_os_handle_nolock common_control87 common_control87$filt$0 common_exit
common_flush_all common_flush_all$fin$0 common_flush_all$fin$1 common_fseek
common_fseek_binary_mode_read_only_fast_track_nolock common_fseek_nolock
common_ftell_read_mode_nolock common_ftell_translated_utf8_nolock
common_lseek_do_seek_nolock compute_size compute_year configure_text_mode
convert_to_stat_mode copy_string_into_buffer ctrlevent_capture cvtdate
decode_access_flags decode_options decode_sharing_flags
enum_system_locales_ex_nolock exit_or_terminate_process fast_check fclose
fclose$fin$0 fegetround feholdexcept fesetenv fflush fflush$fin$0 fgetc
fgetwc fgetws find_or_allocate_unused_stream_nolock fix_grouping fp_format_a
fp_format_e fp_format_e_internal fp_format_f fp_format_f_internal
fp_format_g fp_format_nan_or_infinity fputc fputc$fin$0 fputs fputwc
fputwc$fin$0 fputwc_binary_nolock fread_s free_crt_array_internal fseek
ftell get_context_nolock get_drive_number_from_path
get_failure_string get_full_path_name get_or_create_lc_time get_ptd_buffer
get_ptd_head get_tz_environment_variable has_executable_extension
initialize_inherited_file_handles_nolock initialize_lc_time
initialize_multibyte initialize_pointers initialize_stdio_handles_nolock
internal_getptd_noexit internal_islower_l internal_isupper_l
internal_map_lower internal_map_upper is_buffer_valid_nolock is_managed_app
is_root_or_empty is_root_unc_name is_slash is_text_mode
is_usable_drive_or_unc_root is_valid_drive isalpha isblank iscntrl isgraph
isleadbyte islower isprint ispunct isupper iswalnum iswalpha iswascii
iswblank iswcntrl iswctype iswdigit iswgraph iswlower iswprint iswpunct
iswspace iswupper iswxdigit mbstowcs mbtowc memcpy memcpy_s memset qsort
raise raise$fin$0 read_character_nolock setSBCS setSBUpLow setmbcp_internal
shortsort should_call_terminate_process should_write_error_to_console
signal_failed store_lookahead strcmp strcpy_s strerror_s strncmp strncpy_s
strpbrk strtoimax strtol strtoll strtoull strtoumax terminate toupper
translate_ansi_or_utf8_nolock translate_utf16_from_console_nolock
truncate_ctrl_z_if_present try_cor_exit_process try_get_AreFileApisANSI
try_get_CompareStringEx try_get_EnumSystemLocalesEx try_get_FlsAlloc
try_get_FlsFree try_get_FlsGetValue try_get_FlsSetValue
try_get_GetActiveWindow try_get_GetCurrentPackageId try_get_GetDateFormatEx
try_get_GetEnabledXStateFeatures try_get_GetFileInformationByHandleEx
try_get_GetLastActivePopup try_get_GetLocaleInfoEx
try_get_GetProcessWindowStation try_get_GetSystemTimePreciseAsFileTime
try_get_GetTimeFormatEx try_get_GetUserDefaultLocaleName
try_get_GetUserObjectInformationW try_get_GetXStateFeaturesMask
try_get_InitializeCriticalSectionEx try_get_IsValidLocaleName
try_get_LCIDToLocaleName try_get_LCMapStringEx try_get_LocaleNameToLCID
try_get_LocateXStateFeature try_get_MessageBoxA try_get_MessageBoxW
try_get_RoInitialize try_get_RoUninitialize try_get_SetThreadStackGuarantee
try_get_SystemFunction036 try_get_first_available_module try_get_function
try_get_module try_get_proc_address_from_first_available_module
try_get_ptd_head try_load_library_from_system_directory
tzset_from_environment_nolock tzset_from_system_nolock tzset_nolock ungetc
ungetwc ungetwc_binary_mode_nolock ungetwc_text_mode_nolock
uninitialize_allocated_memory wcscat_s wcscmp wcscpy_s wcscspn wcsncmp
wcsncnt wcsncpy_s wcsnlen wcspbrk wcsrchr wcstoimax wcstol wcstoll wcstombs
wcstoul wcstoull wcstoumax wctomb wctomb_s write_binary_nolock
write_double_translated_ansi_nolock write_double_translated_unicode_nolock
write_requires_double_translation_nolock write_string_to_console
write_text_ansi_nolock write_text_utf16le_nolock write_text_utf8_nolock
x_ismbbtype_l
""".split()

_X64_IMPORTED_UNDER_MD = """
_close _fdopen _fstat64i32 _lseek _open _read _set_errno _stat64i32 _strdup
_write atoi feof ferror fgets fwrite isalnum isdigit isspace isxdigit
mbstowcs_s signal strerror strnlen strtoul tolower wcstombs_s
""".split()

_GENERIC = [
    # C++ names; LibreSSL has none.
    r"::|<|`| ",
    # The runtime's reserved prefixes.
    r"^_{2,3}(?:acrt|crt|vcrt|scrt|dcrt)_",
]


def _exact(names):
    """One anchored alternation; a "$+0x.." suffix is SMDA's name for a
    fragment of the function before it."""
    return r"^(?:%s)(?:\$\+0x[0-9a-f]+)?$" % "|".join(
        re.escape(name) for name in sorted(set(names)))


STATIC_CRT_X86 = _GENERIC + [_exact(_X86_NAMES), r"^$"]
STATIC_CRT_X64 = _GENERIC + [_exact(_X64_NAMES + _X64_IMPORTED_UNDER_MD)]
