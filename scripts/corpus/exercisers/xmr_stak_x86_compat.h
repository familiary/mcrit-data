/* Force-included (-include) into the xmr-stak MinGW x86 build only.
 *
 * Upstream xmr-stak is 64-bit only. GCC's x86 intrinsic headers leave out the
 * 64-bit-register intrinsics on a 32-bit target, and cryptonight_aesni.h uses
 * four of them. These are plain C equivalents of what the instructions do, so
 * that the 32-bit objects compile; they are not what a 64-bit build runs.
 * The image is an unsupported configuration (see xmr_stak_mingw.py).
 */
#ifndef XMR_STAK_X86_COMPAT_H
#define XMR_STAK_X86_COMPAT_H
#include <stdint.h>
#include <immintrin.h>

static inline __m128i _mm_cvtsi64_si128(long long a)
{
	return _mm_set_epi64x(0, a);
}

static inline long long _mm_cvtsi128_si64(__m128i a)
{
	long long r[2];
	_mm_storeu_si128((__m128i*)r, a);
	return r[0];
}

static inline unsigned char _addcarry_u64(unsigned char c, unsigned long long a,
	unsigned long long b, unsigned long long* out)
{
	unsigned long long s = a + b;
	unsigned char c1 = s < a;
	unsigned long long t = s + c;
	*out = t;
	return c1 | (t < s);
}

static inline unsigned char _subborrow_u64(unsigned char c, unsigned long long a,
	unsigned long long b, unsigned long long* out)
{
	unsigned long long d = a - b;
	unsigned char b1 = a < b;
	unsigned long long t = d - c;
	*out = t;
	return b1 | (d < c);
}
#endif
