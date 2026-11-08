/* Force-included for the UltraVNC MinGW-w64 build (C++ only). MSVC provides
 * these through its CRT; mingw-w64 does not. No source is changed by them. */
#ifndef ULTRAVNC_MINGW_COMPAT_H
#define ULTRAVNC_MINGW_COMPAT_H
#ifdef __cplusplus
#include <cstring>
#include <cstddef>
#include <time.h>
/* MSVC binds a temporary to a non-const lvalue reference; a patched call site
 * (ClientConnectionTLS.cpp) names this to say so explicitly. */
template <class T> T &uvnc_lvalue(T &&t) { return t; }
/* MSVC's array-size overloads (_CRT_SECURE_CPP_OVERLOADS_STANDARD_NAMES). */
template <size_t N> errno_t _strdate_s(char (&b)[N]) { return _strdate_s(b, N); }
template <size_t N> errno_t _strtime_s(char (&b)[N]) { return _strtime_s(b, N); }
#endif
#endif
