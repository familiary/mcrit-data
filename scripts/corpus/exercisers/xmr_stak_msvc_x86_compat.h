/* Force-included (/FI) into the xmr-stak MSVC x86 build only.
 *
 * Upstream xmr-stak is 64-bit only. MSVC declares _umul128, _addcarry_u64,
 * _subborrow_u64, _mm_cvtsi64_si128 and _mm_cvtsi128_si64 for x64 targets
 * only, and cryptonight_aesni.h uses all five. Each is defined here in terms
 * of 32-bit operations under an xs_ name, and the macros below point the
 * upstream spelling at it. The headers are included first so that nothing
 * they declare is renamed. These are plain equivalents of what the
 * instructions compute, not what a 64-bit build runs. The image is an
 * unsupported configuration (see xmr_stak_msvc_x86.py).
 */
#ifndef XMR_STAK_MSVC_X86_COMPAT_H
#define XMR_STAK_MSVC_X86_COMPAT_H
#include <stdint.h>
#include <intrin.h>
#include <immintrin.h>

static inline unsigned long long xs_umul128(unsigned long long a, unsigned long long b,
	unsigned long long* hi)
{
	unsigned long long al = (uint32_t)a, ah = a >> 32, bl = (uint32_t)b, bh = b >> 32;
	unsigned long long ll = al * bl, lh = al * bh, hl = ah * bl, hh = ah * bh;
	unsigned long long mid = (ll >> 32) + (uint32_t)lh + (uint32_t)hl;
	*hi = hh + (lh >> 32) + (hl >> 32) + (mid >> 32);
	return (ll & 0xffffffffull) | (mid << 32);
}

static inline __m128i xs_cvtsi64_si128(long long a)
{
	return _mm_set_epi64x(0, a);
}

static inline long long xs_cvtsi128_si64(__m128i a)
{
	return ((long long)(unsigned)_mm_cvtsi128_si32(_mm_srli_si128(a, 4)) << 32)
		| (unsigned)_mm_cvtsi128_si32(a);
}

static inline unsigned char xs_addcarry_u64(unsigned char c, unsigned long long a,
	unsigned long long b, unsigned long long* out)
{
	unsigned long long s = a + b;
	unsigned char c1 = s < a;
	unsigned long long t = s + c;
	*out = t;
	return c1 | (t < s);
}

static inline unsigned char xs_subborrow_u64(unsigned char c, unsigned long long a,
	unsigned long long b, unsigned long long* out)
{
	unsigned long long d = a - b;
	unsigned char b1 = a < b;
	unsigned long long t = d - c;
	*out = t;
	return b1 | (d < c);
}

#define _umul128 xs_umul128
#define _mm_cvtsi64_si128 xs_cvtsi64_si128
#define _mm_cvtsi128_si64 xs_cvtsi128_si64
#define _addcarry_u64 xs_addcarry_u64
#define _subborrow_u64 xs_subborrow_u64
#endif
