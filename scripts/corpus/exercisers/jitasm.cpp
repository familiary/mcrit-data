// Instantiates hikaru-i/jitasm so its code is actually emitted.
//
// jitasm is one header, jitasm.h, and nothing of it exists in a binary until a
// translation unit assembles something with it. Two things are emitted when
// it does, and this file is built to reach both:
//
//  * the encoder - jitasm::Backend::Assemble and EncodeInstr, which turn an
//    instruction list into bytes, and the Frontend::Assemble / GetCode path
//    that drives them. These are plain (non-template) inline members, so they
//    are emitted once per image, whichever functions are assembled.
//  * the front end - one Frontend member per instruction mnemonic, which
//    records an Instr. Each is tiny, and whether it survives optimisation as
//    a function or is folded into its caller is exactly what recipe
//    measurement is for.
//
// Upstream ships a consumer that covers the instruction set broadly:
// test/test_backend.cpp defines 60 jitasm::function structs, one per
// instruction family from SAL/SAR through x87, MMX, SSE to AVX2 gather, each
// with a naked_main that calls the mnemonics. Its test() function is empty
// unless MASM_TEST or NASM_TEST is defined and those need object files this
// corpus does not have, so it instantiates nothing by itself; it is included
// here, unmodified, and the structs are assembled by the loop below. Its
// "test.h" is found because the quoted include resolves next to it.
//
// The structs in test_backend.cpp use naked_main and so never reach the
// register allocator and calling-convention code (the compiler:: namespace,
// roughly 2000 lines of the header). Those are reached by the main()
// functions below, which are modelled on upstream's samples/fibonacci and
// test/test.cpp: If/Else/While control flow, arguments in registers and on
// the stack, floating point and SIMD arguments and returns.
//
// Nothing here is ever run. Assemble() is called, so the encoder is
// exercised in the sense of being compiled and linked, but the DLL's entry
// point is never invoked.

#if defined(_WIN32)
#include <windows.h>
#endif

#include "test/test_backend.cpp"

#include "corpus_export.h"

namespace {

struct ex_fibonacci : jitasm::function<unsigned int, ex_fibonacci, unsigned int>
{
	Result main(Reg32 n)
	{
		Reg32 r;
		If(n == 0);
			mov(r, 0);
		ElseIf(n == 1 || n == 2);
			mov(r, 1);
		Else();
			Reg32 a;
			Reg32 b;
			Reg32 i;
			mov(a, 1);
			mov(b, 1);
			mov(i, 2);
			While(i < n);
				mov(r, a);
				add(r, b);
				mov(b, a);
				mov(a, r);
				inc(i);
			EndW();
		EndIf();
		return r;
	}
};

struct ex_sum_args : jitasm::function_cdecl<int, ex_sum_args, int, int, int, int, int, int>
{
	Result main(Reg32 a, Reg32 b, Reg32 c, Reg32 d, Reg32 e, Reg32 f)
	{
		add(a, b);
		add(a, c);
		add(a, d);
		add(a, e);
		add(a, f);
		return a;
	}
};

struct ex_pressure : jitasm::function_cdecl<void, ex_pressure>
{
	void main()
	{
		Reg32 v1, v2, v3, v4, v5, v6, v7, v8;
		mov(v8, 2); mov(v7, 1);
		xor(v6, v6); xor(v5, v5); xor(v4, v4); xor(v3, v3);
		xor(v2, v2); xor(v1, v1);
		Reg32 a;
		mov(a, 10);
		L("head");
		cmp(v1, 5);
		jg("tail");
		inc(v1); add(v2, v1); add(v3, v2); add(v4, v3); add(v5, v4);
		dec(a);
		jnz("head");
		L("tail");
		dec(v1); add(v6, v5); add(v7, v6); add(v8, v7);
		dec(a);
		jnz("head");
	}
};

struct ex_float : jitasm::function_cdecl<float, ex_float, float>
{
	Result main(XmmReg x)
	{
		XmmReg t;
		xorps(t, t);
		addss(t, x);
		mulss(t, x);
		return t;
	}
};

struct ex_double : jitasm::function_cdecl<double, ex_double, double>
{
	Result main(XmmReg x)
	{
		XmmReg t;
		xorpd(t, t);
		addsd(t, x);
		mulsd(t, x);
		return t;
	}
};

struct ex_m128 : jitasm::function_cdecl<__m128, ex_m128, __m128, __m128, __m128>
{
	Result main(XmmReg a, XmmReg b, XmmReg c)
	{
		addps(a, b);
		addps(a, c);
		return a;
	}
};

struct ex_ptr : jitasm::function_cdecl<int, ex_ptr, int*, int>
{
	Result main(Addr p, Reg32 n)
	{
		Reg32 s;
		mov(s, dword_ptr[p]);
		add(s, dword_ptr[p + 4]);
		cmp(n, 2);
		If(n > 2);
			add(s, dword_ptr[p + 8]);
		EndIf();
		return s;
	}
};

template<class F>
size_t assemble_one()
{
	F f;
	f.Assemble();
	return f.GetCodeSize() + reinterpret_cast<size_t>(f.GetCode());
}

} // namespace

extern "C" CORPUS_EXPORT size_t jitasm_exercise()
{
	size_t n = 0;
	n += assemble_one<test_sal>();
	n += assemble_one<test_sar>();
	n += assemble_one<test_shl>();
	n += assemble_one<test_shr>();
	n += assemble_one<test_rcl>();
	n += assemble_one<test_rcr>();
	n += assemble_one<test_rol>();
	n += assemble_one<test_ror>();
	n += assemble_one<test_inc_dec>();
	n += assemble_one<test_push_pop>();
	n += assemble_one<test_add>();
	n += assemble_one<test_or>();
	n += assemble_one<test_adc>();
	n += assemble_one<test_sbb>();
	n += assemble_one<test_and>();
	n += assemble_one<test_sub>();
	n += assemble_one<test_xor>();
	n += assemble_one<test_cmp>();
	n += assemble_one<test_xchg>();
	n += assemble_one<test_test>();
	n += assemble_one<test_mov>();
	n += assemble_one<test_lea>();
	n += assemble_one<test_fld>();
	n += assemble_one<test_jmp>();
	n += assemble_one<test_movs>();
	n += assemble_one<test_mov_disp>();
	n += assemble_one<test_neg_not>();
	n += assemble_one<test_div_idiv_mul>();
	n += assemble_one<test_imul>();
	n += assemble_one<test_fst>();
	n += assemble_one<test_setcc>();
	n += assemble_one<test_cmovcc>();
	n += assemble_one<test_gpi_b>();
	n += assemble_one<test_gpi_e>();
	n += assemble_one<test_fpu>();
	n += assemble_one<test_mmx>();
	n += assemble_one<test_mmx2>();
	n += assemble_one<test_sse>();
	n += assemble_one<test_sse2_a>();
	n += assemble_one<test_sse2_d>();
	n += assemble_one<test_sse2_p>();
	n += assemble_one<test_sse2_s>();
	n += assemble_one<test_movd_movq>();
	n += assemble_one<test_movsd_movss>();
	n += assemble_one<test_sse3>();
	n += assemble_one<test_ssse3>();
	n += assemble_one<test_sse4_1>();
	n += assemble_one<test_sse4_2>();
	n += assemble_one<test_avx_a>();
	n += assemble_one<test_avx_b>();
	n += assemble_one<test_avx_d>();
	n += assemble_one<test_avx_o>();
	n += assemble_one<test_avx_r>();
	n += assemble_one<test_fma>();
	n += assemble_one<test_f16c>();
	n += assemble_one<test_xop>();
	n += assemble_one<test_fma4>();
	n += assemble_one<test_bmi>();
	n += assemble_one<test_avx2>();
	n += assemble_one<test_avx2_gather>();

	n += assemble_one<ex_fibonacci>();
	n += assemble_one<ex_sum_args>();
	n += assemble_one<ex_pressure>();
	n += assemble_one<ex_float>();
	n += assemble_one<ex_double>();
	n += assemble_one<ex_m128>();
	n += assemble_one<ex_ptr>();
	return n;
}
