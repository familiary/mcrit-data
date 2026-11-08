/* Force-included into the winvnc target only (UltraVNC MinGW-w64 recipe, C++),
 * after ultravnc_mingw_compat.h. MSVC's CRT provides array-size overloads of
 * the bounds-checked string functions; mingw-w64 does not. */
#ifndef ULTRAVNC_MINGW_WINVNC_COMPAT_H
#define ULTRAVNC_MINGW_WINVNC_COMPAT_H
#ifdef __cplusplus
#include <wchar.h>
#include <stddef.h>
/* vncmenu.cpp: wcsncat_s(m_tooltip, L" - ", _TRUNCATE) with m_tooltip a
 * wchar_t array (`too few arguments to function 'errno_t wcsncat_s(...)'`). */
template <size_t N> errno_t wcsncat_s(wchar_t (&d)[N], const wchar_t *s, size_t n) { return wcsncat_s(d, N, s, n); }
#endif
#endif
