"""Identify compiler runtime glue so it is not attributed to a library family.

Every MinGW-linked DLL or EXE carries startup, unwind-registration and CRT
import glue that belongs to the compiler runtime, not to the project being
built. The MinGW runtime already has its own coverage in this repository
(data/MinGW), so leaving those functions labelled with a library's family name
would both duplicate existing reference data and mis-attribute it - the kind of
mistake commit 0108024 ("fixed two family mismappings") had to correct by hand.

Rather than hardcoding a symbol list that would rot with the next GCC, the
baseline is measured: an empty translation unit is linked with the same
toolchain, and the functions SMDA recovers from it define the glue set. A
function in a real build counts as glue only when both its symbol name and its
PicHash match the baseline, so a project that ships its own ``strlen`` keeps it.

The MSVC side is the same idea with three more things to measure, because
Microsoft's runtime is larger than GCC's in ways that matter here. ATL and
the MSVC STL have no GCC counterpart and are instantiated per type, so a
probe covers exactly the instantiations it names. And MSVC ships its C
runtime twice: ``/MT`` links it statically while ``/MD`` leaves it in
ucrtbase.dll and vcruntime140.dll behind a one-instruction import thunk, and
the two flavours are not the same bytes even for the startup and /GS code
that is statically linked either way. Both MSVC recipes in this repository
build ``/MD``, so the probes are built both ways and unioned.

What each MSVC probe is for was read off the committed reports rather than
guessed; the comment above each one says which measurement it answers.
"""

import functools
import logging
import os
import subprocess
import tempfile

from .toolchain import get_toolchain


LOGGER = logging.getLogger(__name__)


# The probe has to *use* the runtime, not merely link against it: MinGW pulls
# libmingwex objects in on demand, so a DLL that never formats a float never
# links the dtoa helpers that a library calling gzprintf() does. Touching a
# broad surface of the C runtime here is what keeps those helpers out of a
# library's function set.
_PROBE_DLL = """\
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#include <time.h>
#include <math.h>
#include <errno.h>
#include <locale.h>
#include <stdarg.h>

static int compare(const void *a, const void *b) { return *(const int *)a - *(const int *)b; }

static int probe_vscprintf(const char *format, ...)
{
    va_list arguments;
    int needed;
    va_start(arguments, format);
    needed = _vscprintf(format, arguments);
    va_end(arguments);
    return needed;
}

__declspec(dllexport) void probe_runtime(const char *text, double value)
{
    char buffer[256];
    wchar_t wide[64];
    int numbers[4] = {4, 2, 3, 1};
    FILE *stream;
    void *block;
    time_t now;

    snprintf(buffer, sizeof(buffer), "%s %f %e %g %d %x %p", text, value, value, value, 1, 2, text);
    sscanf(buffer, "%255s", buffer);
    swprintf(wide, 64, L"%s %f", L"w", value);
    strtod(buffer, NULL);
    strtol(buffer, NULL, 10);
    _strtoi64(buffer, NULL, 16);
    qsort(numbers, 4, sizeof(int), compare);
    bsearch(numbers, numbers, 4, sizeof(int), compare);
    block = malloc(64);
    block = realloc(block, 128);
    memset(block, 0, 128);
    memcpy(buffer, block, 16);
    memmove(buffer, block, 16);
    free(block);
    strncpy(buffer, text, 8);
    strcat(buffer, text);
    strchr(buffer, 'x');
    strstr(buffer, text);
    strcmp(buffer, text);
    wcslen(wide);
    wcscpy(wide, wide);
    setlocale(LC_ALL, "C");
    time(&now);
    localtime(&now);
    strftime(buffer, sizeof(buffer), "%Y", localtime(&now));
    stream = fopen("NUL", "rb");
    if (stream) { fread(buffer, 1, 1, stream); fseek(stream, 0, SEEK_SET); ftell(stream); fclose(stream); }
    fprintf(stderr, "%s", buffer);
    pow(value, 2.0); fmod(value, 2.0); floor(value); ceil(value); sqrt(value); log(value); exp(value);
    abs((int)value); labs((long)value); ldiv((long)value, 2);
    /* 64-bit division on a 32-bit target is a libgcc call, not an
       instruction: __divdi3, __moddi3, __udivmoddi4 and __umoddi3 are
       emitted into whatever links them. Without this they are absent from
       the baseline, and a cross-family sweep finds them sitting in 7-Zip,
       Lua, OpenSSL and libstdc++ at once - four of the eighty-four functions
       the whole corpus shares across three families or more. */
    {
        long long wide = (long long)value * 1000003LL + 7;
        unsigned long long uwide = (unsigned long long)wide | 1ULL;
        long long sdiv = (long long)(uwide | 3);
        unsigned long long udiv = (unsigned long long)(wide | 9);
        volatile long long sink64;
        /* Both shapes are needed. A quotient and a remainder over the same
           divisor fold into one __divmoddi4/__udivmoddi4 call; over
           different divisors they stay as __divdi3, __moddi3, __udivdi3 and
           __umoddi3. All six turn up in real builds. */
        sink64 = wide / sdiv;
        sink64 += wide % sdiv;
        sink64 += (long long)(uwide / udiv);
        sink64 += (long long)(uwide % udiv);
        sink64 += wide / (long long)(uwide | 5);
        sink64 += wide % (long long)(uwide | 7);
        sink64 += (long long)(uwide / (unsigned long long)(wide | 11));
        sink64 += (long long)(uwide % (unsigned long long)(wide | 13));
        (void)sink64;
    }
    /* Calling a math function is not enough to get its library
       implementation into the baseline. GCC knows sin, cos, floor and the
       rest as builtins and at -O2 folds a call on a known value, or emits an
       SSE instruction, so the libmingwex body is never linked - while a
       library that calls floor() on a value the compiler cannot see does
       link it. That is why floor, sin, cos, frexp, modf and atan2 were found
       sitting in Lua, LuaJIT, libpng, libxml2 and abseil at once, and in
       data/MinGW as well, after the division helpers had been dealt with.

       Taking the address defeats the builtin: the symbol has to exist to be
       pointed at, and calling through a volatile pointer stops the optimiser
       proving what it points to. sinl/cosl bring __sinl_internal and
       __cosl_internal, which are their own functions in libmingwex. */
    {
        volatile double (*const dd[])(double) = {
            sin, cos, tan, asin, acos, atan, sinh, cosh, tanh,
            floor, ceil, sqrt, log, log10, exp, fabs, round, trunc,
        };
        volatile double (*const dd2[])(double, double) = {pow, fmod, atan2, hypot};
        volatile long double (*const ld[])(long double) = {sinl, cosl, tanl, logl, expl};
        double accumulated = 0.0;
        size_t index;

        for (index = 0; index < sizeof(dd) / sizeof(dd[0]); index++)
            accumulated += dd[index](value);
        for (index = 0; index < sizeof(dd2) / sizeof(dd2[0]); index++)
            accumulated += dd2[index](value, 2.0);
        for (index = 0; index < sizeof(ld) / sizeof(ld[0]); index++)
            accumulated += (double)ld[index]((long double)value);
        {
            int exponent = 0;
            double integral = 0.0;
            accumulated += frexp(value, &exponent);
            accumulated += modf(value, &integral);
            accumulated += ldexp(value, 2);
            accumulated += integral + exponent;
        }
        snprintf(buffer, sizeof(buffer), "%f", accumulated);
    }
    /* The reentrant time conversions are separate functions from localtime()
       above, and are what a library actually calls: gmtime_s and
       localtime_s carry _int_gmtime64_s and friends behind them. */
    {
        struct tm parts;
        gmtime_s(&parts, &now);
        localtime_s(&parts, &now);
        gmtime(&now);
        mktime(&parts);
        difftime(now, now);
    }
    /* _vscprintf brings MinGW's emulation of it - _emu_vscprintf and
       _init_vscprintf - which turned up under abseil, libevent and libuv.
       It has to be reached through a real varargs function: handing it a
       va_list that was never started is undefined behaviour, and a probe
       that relies on undefined behaviour is not a measurement. */
    probe_vscprintf("%s %f %d", text, value, 1);
    /* Both time_t widths. MinGW's time_t is 64-bit by default, so a probe
       that only calls gmtime_s never links the 32-bit pair - and the 32-bit
       ones are exactly what turned up under abseil, libevent and mbedTLS,
       because a library built against an older header calls them by name. */
    {
        __time32_t narrow = 0;
        __time64_t wide64 = 0;
        struct tm parts;

        _gmtime32_s(&parts, &narrow);
        _gmtime64_s(&parts, &wide64);
        _localtime32_s(&parts, &narrow);
        _localtime64_s(&parts, &wide64);
        /* No _mktime32 here: it does not exist on the 64-bit target, and a
           probe that fails to link measures nothing at all - it took the
           whole x64 baseline from 2893 symbols down to 2812. mktime() is
           called above and covers the same ground. */
    }
    /* __get_errno, likewise its own function rather than a macro. */
    _get_errno(&(int){0});
    errno = 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

# The EXE variant of the same probe. MinGW's mainCRTStartup path pulls in a
# different object set from DllMainCRTStartup - __getmainargs, _setargv,
# __set_app_type, _gnu_exception_handler, exit, _cexit and friends - none of
# which a DLL-only baseline ever sees.
_PROBE_EXE = _PROBE_DLL.replace(
    "BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }",
    "int main(int argc, char **argv) { probe_runtime(argv[0], (double)argc); return 0; }")

# Anything linked with g++ drags in libstdc++ and the GCC unwinder, which are
# far larger than the C runtime and belong to the compiler just the same.
_PROBE_CXX = """\
#include <algorithm>
#include <exception>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

__declspec(dllexport) void probe_cxx_runtime(const char *text)
{
    std::string value(text);
    std::vector<std::string> items;
    std::map<std::string, int> counts;
    std::ostringstream out;

    items.push_back(value);
    items.push_back(value + "2");
    std::sort(items.begin(), items.end());
    for (const std::string &item : items) {
        counts[item] += 1;
        out << item << " " << counts[item] << "\\n";
    }
    std::unique_ptr<std::string> owned(new std::string(out.str()));
    std::shared_ptr<std::string> shared(new std::string(*owned));
    try {
        if (value.size() > 1000000) {
            throw std::runtime_error(value);
        }
        std::cerr << shared->substr(0, 1) << std::endl;
    } catch (const std::exception &error) {
        std::cerr << error.what() << std::endl;
    }
}
"""


# C++ EXE probe: libstdc++ plus the EXE startup path together.
_PROBE_CXX_EXE = _PROBE_CXX + """
int main(int argc, char **argv) { probe_cxx_runtime(argv[0]); return argc - argc; }
"""


# MSVC only, and only because two families here need ATL. A DLL that merely
# instantiates ATL's module object drags in CAtlBaseModule, CAtlWinModule,
# CComCriticalSection and the CSimpleArray instantiations behind them - around
# ninety functions that are Microsoft's, already covered by data/MSVC, and
# were being filed under VX-API and BlackBone. There is no MinGW equivalent:
# ATL does not exist for GCC, which is half the reason those families are
# built on a Windows runner at all.
_PROBE_ATL = """\
#include <windows.h>
#include <atlbase.h>

__declspec(dllexport) void probe_atl(const wchar_t *text)
{
    ATL::CComCriticalSection lock;
    ATL::CSimpleArray<int> items;

    lock.Init();
    lock.Lock();
    lock.Unlock();
    lock.Term();
    items.Add(1);
    items.Add(2);
    items.RemoveAll();
    ATL::AtlThrowImpl(S_OK);
    (void)text;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

# MSVC only. The rest of ATL that the committed artefacts actually wear.
#
# Measured, not guessed: reading the four committed MSVC reports back
# (VX-API and BlackBone, both architectures) and asking which ATL functions
# the filter still leaves behind gives 26 in VX-API x64 and 28 in x86, and
# they cluster. CComBSTR and CComVariant account for eight of them, the
# CSimpleArray<unsigned short> instantiation for two, the module objects'
# destructors and their compiler-generated atexit thunks for most of the
# rest. _PROBE_ATL above instantiates CSimpleArray<int> and the critical
# section only, so none of that is in the baseline.
#
# This is a separate translation unit rather than more lines in _PROBE_ATL
# because _PROBE_ATL already works: a probe that fails to build is not a
# neutral event, it silently shrinks the baseline and therefore the filter,
# which is how the MinGW x64 side lost 81 symbols in one commit. Splitting
# means a mistake here cannot take the working probe with it.
#
# ole32/oleaut32 are named explicitly: CComVariant calls VariantClear and
# VariantCopy, and nothing in the ATL headers guarantees a #pragma comment
# for them.
_PROBE_ATL_COM = """\
#include <windows.h>
#include <atlbase.h>
#include <atlcomcli.h>

__declspec(dllexport) HRESULT probe_atl_com(const wchar_t *text)
{
    ATL::CComBSTR empty;
    ATL::CComBSTR value(text);
    ATL::CComBSTR copy(value);
    ATL::CComVariant variant;
    ATL::CComVariant fromText(text);
    ATL::CComVariant fromLong((long)1);
    ATL::CComPtr<IUnknown> unknown;
    ATL::CAtlException error(E_FAIL);
    BSTR raw;

    value.Append(text);
    value.Empty();
    variant = fromText;
    variant.Clear();
    fromLong.Clear();
    raw = copy;
    (void)raw;
    (void)&empty;
    (void)&unknown;
    return error.m_hr;
}

__declspec(dllexport) int probe_atl_containers(unsigned short word)
{
    /* CSimpleArray is instantiated per element type, like every other C++
       template: the committed artefacts carry the unsigned short and the
       HINSTANCE instantiations, and _PROBE_ATL only has the int one. */
    ATL::CSimpleArray<unsigned short> words;
    ATL::CSimpleArray<HINSTANCE> instances;
    ATL::CComCriticalSection section;

    words.Add(word);
    words.Add((unsigned short)(word + 1));
    words.RemoveAt(0);
    words.RemoveAll();
    instances.Add((HINSTANCE)NULL);
    instances.RemoveAll();
    section.Init();
    {
        ATL::CComCritSecLock<ATL::CComCriticalSection> guard(section, false);
        guard.Lock();
        guard.Unlock();
    }
    section.Term();
    return words.GetSize() + instances.GetSize();
}

__declspec(dllexport) HINSTANCE probe_atl_modules(void)
{
    /* The module destructors and their atexit thunks are what survive in
       VX-API: ~CAtlComModule, CAtlWinModule::Term, ~CAtlWinModule,
       AtlWinModuleTerm and the "dynamic atexit destructor for" functions
       the compiler emits for ATL's own _AtlComModule / _AtlWinModule
       globals. Local instances give those destructors a second call site,
       which is what keeps them out of line at /O2. */
    ATL::CAtlWinModule window;
    ATL::CAtlComModule com;

    (void)window;
    (void)com;
    return ATL::_AtlBaseModule.GetModuleInstance();
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

# MSVC only, and deliberately one line of substance. ATL::AtlThrowImpl is an
# inline function; _PROBE_ATL calls it exactly once, so -O2 inlines it and
# the baseline never gets a body, while VX-API - which calls it from many
# places - keeps one out-of-line copy. That is the MinGW builtin trap in ATL
# clothing and the fix is the same one: take the address.
#
# It is alone in its own translation unit because it is the only place in
# this file that has to spell an ATL signature out by hand, and a wrong
# guess at the calling convention must cost one function rather than twenty.
_PROBE_ATL_THROW = """\
#include <windows.h>
#include <atlbase.h>

typedef void (WINAPI *probe_atl_thrower)(HRESULT);

__declspec(dllexport) probe_atl_thrower probe_atl_throw_address(int enabled)
{
    probe_atl_thrower thrower = ATL::AtlThrowImpl;
    return enabled ? thrower : (probe_atl_thrower)0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

# MSVC only. Everything the /MD artefacts reach through the C runtime that a
# call alone does not pin down.
#
# Two separate effects put these in the artefacts and not in the baseline,
# and the committed data distinguishes them. memcpy, memset, memmove,
# memcmp, strlen, __acrt_iob_func, _initterm, _purecall, _CxxThrowException,
# __std_terminate and the rest all appear in VX-API and BlackBone as
# *one-instruction* functions, every one of them carrying the same PicHash -
# they are the linker's `jmp [__imp_...]` import thunks, because the recipes
# build /MD and the runtime lives in ucrtbase.dll and vcruntime140.dll. The
# probe builds /MT, so its memcpy is the 338-instruction static body (the
# same one data/MSVC's merged .lib carries). Name matches, PicHash cannot.
# The /MD probe variants registered below fix that.
#
# The second effect only bites once they are fixed: /O2 implies /Oi, so
# memcpy and memset with a constant size are expanded inline and no thunk is
# emitted at all. Taking the address forces the reference, exactly as it had
# to for GCC's builtin sin and floor. An array of addresses is used rather
# than #pragma function or calls through volatile pointers because it needs
# no signature to be spelled out and no pragma to be accepted: a name that
# the headers declare is all it takes.
_PROBE_MSVCRT = """\
#define _CRT_SECURE_NO_WARNINGS 1
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

typedef void (*probe_symbol)(void);

/* Exported so nothing here can be dropped as unreferenced.

   Filled by a function rather than initialised where it is declared, which
   is not a style choice: cl's C frontend rejects a cast function pointer as
   a file-scope initializer with "error C2099: initializer is not a
   constant", so the whole translation unit failed to compile - on every run
   this probe has ever been part of. Taking the addresses in a function is
   C-legal and has the effect the file-scope version was meant to have: the
   address is referenced, so the linker has to bring in whatever stands for
   the function - under /MD a one-instruction "jmp [__imp_memcpy]" thunk,
   not a body, which is exactly the shape these names have in the artefacts
   and is what is matched there.

   What this recovers is narrower than the missing translation unit makes it
   sound, because probe_md.c calls most of the same functions and the
   baseline already removes memcpy from 95 artefacts, memset from 95, free
   from 83, malloc from 79, memmove 69, strchr 60, memchr 53, strlen 43,
   realloc 40, memcmp 32, strstr 30, strncpy 24, qsort 18, wcslen 11,
   bsearch 8 and wcscpy 3. The twelve this adds are strcpy, strcat, strcmp,
   strncmp, strrchr, wcscat, wcscmp, wcsncmp, wcschr, wcsstr, calloc and
   abort - and ten of those do currently leak, strncmp into 41 MSVC
   artefacts, calloc 39, strcmp 30, abort 26, strrchr 24, strcpy 12. */
__declspec(dllexport) probe_symbol probe_msvcrt_symbols[64];

__declspec(dllexport) void probe_msvcrt_take_addresses(void)
{
    probe_symbol *out = probe_msvcrt_symbols;

    *out++ = (probe_symbol)memcpy;
    *out++ = (probe_symbol)memmove;
    *out++ = (probe_symbol)memset;
    *out++ = (probe_symbol)memcmp;
    *out++ = (probe_symbol)memchr;
    *out++ = (probe_symbol)strlen;
    *out++ = (probe_symbol)strcpy;
    *out++ = (probe_symbol)strcat;
    *out++ = (probe_symbol)strcmp;
    *out++ = (probe_symbol)strncmp;
    *out++ = (probe_symbol)strncpy;
    *out++ = (probe_symbol)strchr;
    *out++ = (probe_symbol)strrchr;
    *out++ = (probe_symbol)strstr;
    *out++ = (probe_symbol)wcslen;
    *out++ = (probe_symbol)wcscpy;
    *out++ = (probe_symbol)wcscat;
    *out++ = (probe_symbol)wcscmp;
    *out++ = (probe_symbol)wcsncmp;
    *out++ = (probe_symbol)wcschr;
    *out++ = (probe_symbol)wcsstr;
    *out++ = (probe_symbol)malloc;
    *out++ = (probe_symbol)calloc;
    *out++ = (probe_symbol)realloc;
    *out++ = (probe_symbol)free;
    *out++ = (probe_symbol)qsort;
    *out++ = (probe_symbol)bsearch;
    *out++ = (probe_symbol)abort;
}

__declspec(dllexport) int probe_msvcrt_frames(const char *text, int value)
{
    /* A stack array is what makes the compiler emit the /GS cookie check.
       __security_check_cookie is not an import thunk - it is linked in - but
       its body still differs between the two runtime flavours: the copy in
       data/MSVC's static-CRT reference and the copy in these /MD artefacts
       are both eight instructions and have different PicHashes. */
    char buffer[256];
    wchar_t wide[64];
    int result;

    _snprintf(buffer, sizeof(buffer), "%s %d", text, value);
    swprintf(wide, 64, L"%d", value);
    __try {
        result = (int)strlen(buffer) + (int)wcslen(wide);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        result = -1;
    }
    fprintf(stderr, "%s", buffer);
    return result;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

# MSVC only. The STL, which MSVC instantiates per type, so a probe covers
# exactly the instantiations it names and nothing else.
#
# This is the direct analogue of the libstdc++ instantiations that make up 26
# of this corpus's 58 surviving cross-family collisions, and it is already
# the largest bucket on the MSVC side: of BlackBone x64's 1759 functions, 240
# are MSVC STL and 128 of those are instantiated over standard or built-in
# types alone, which is the part a probe can reach. (The other 112 are
# instantiated over blackbone's own structs - std::vector<blackbone::
# ProcessInfo>::... - and no baseline can ever contain them. That distinction
# matters for what success looks like here.)
#
# Every type below was read off that measurement rather than chosen:
# vector over unsigned char, unsigned long, unsigned long long, void *,
# std::pair of both widths, std::wstring, MEMORY_BASIC_INFORMATION64 and
# IMAGE_SECTION_HEADER; string and wstring; map keyed by unsigned long long,
# by a pair, and by a pair of wstrings; set<int>; unordered_map over wstring,
# unsigned long, unsigned long long and FARPROC - FARPROC because the PDB
# spells BlackBone's export map as __int64 (__cdecl*)(void) on x64 and
# int (__stdcall*)(void) on x86, which is that typedef on each.
#
# Split three ways, on the same reasoning as the ATL probes: one bad line
# should cost one container family, not all of them.
_PROBE_STL_SEQ = """\
#include <windows.h>
#include <algorithm>
#include <memory>
#include <random>
#include <sstream>
#include <string>
#include <vector>

__declspec(dllexport) std::size_t probe_stl_vector(const unsigned char *data,
                                                   std::size_t size)
{
    std::vector<unsigned char> bytes(data, data + size);
    std::vector<unsigned char> copy;
    std::vector<unsigned long> words;
    std::vector<unsigned long long> quads;
    std::vector<int> numbers;
    std::vector<void *> pointers;
    std::size_t index;

    bytes.reserve(size + 64);
    bytes.resize(size + 8);
    bytes.push_back((unsigned char)0x90);
    bytes.insert(bytes.end(), data, data + size);
    copy = bytes;
    copy.assign(data, data + size);
    copy.erase(copy.begin());
    copy.clear();
    for (index = 0; index < size; ++index) {
        words.push_back((unsigned long)data[index]);
        quads.push_back((unsigned long long)data[index]);
        numbers.push_back((int)data[index]);
        pointers.push_back((void *)(data + index));
    }
    words.resize(size + 4);
    quads.resize(size + 4);
    numbers.resize(size + 4);
    pointers.resize(size + 4);
    return bytes.size() + copy.capacity() + words.size() + quads.size()
           + numbers.size() + pointers.size();
}

__declspec(dllexport) std::size_t probe_stl_vector_records(std::size_t count,
                                                           const wchar_t *name)
{
    std::vector<MEMORY_BASIC_INFORMATION64> regions;
    std::vector<IMAGE_SECTION_HEADER> sections;
    std::vector<std::pair<unsigned long long, unsigned long long> > ranges;
    std::vector<std::pair<unsigned int, unsigned int> > pairs;
    std::vector<std::wstring> names;
    std::size_t index;

    regions.resize(count);
    sections.resize(count);
    for (index = 0; index < count; ++index) {
        ranges.push_back(std::make_pair((unsigned long long)index,
                                        (unsigned long long)index + 1));
        pairs.push_back(std::make_pair((unsigned int)index,
                                       (unsigned int)index + 1));
        names.push_back(std::wstring(name));
    }
    std::sort(names.begin(), names.end());
    std::sort(ranges.begin(), ranges.end());
    return regions.size() + sections.size() + ranges.size() + pairs.size()
           + names.size();
}

__declspec(dllexport) std::size_t probe_stl_string(const char *text,
                                                   const wchar_t *wide)
{
    /* substr() is what reaches _String_val::_Xran and growth is what
       reaches _Xlen_string; both survive the filter in BlackBone today. */
    std::string narrow(text);
    std::wstring wideText(wide);

    narrow.append(text);
    narrow.assign(text);
    narrow += text;
    narrow.reserve(narrow.size() + 128);
    narrow.resize(narrow.size() + 8, 'x');
    narrow.insert(narrow.begin(), 'y');
    wideText.append(wide);
    wideText.assign(wide);
    wideText += wide;
    wideText.reserve(wideText.size() + 128);
    wideText.resize(wideText.size() + 8, L'x');

    std::string joined = narrow + text;
    std::string part = joined.substr(1, 4);
    std::wstring wjoined = wideText + wide;
    std::wstring wpart = wjoined.substr(1, 4);
    std::wstring number = std::to_wstring((unsigned long long)joined.size());
    std::string narrowNumber = std::to_string((int)part.size());

    return joined.size() + part.size() + wjoined.size() + wpart.size()
           + number.size() + narrowNumber.size();
}

__declspec(dllexport) std::size_t probe_stl_stream(const wchar_t *text, int value)
{
    std::wstring source(text);
    std::wostringstream out;
    std::wstringstream both;
    std::wistringstream in(source);
    std::wstring token;

    out << text << L' ' << value << L' ' << (unsigned long long)value;
    both << out.str() << L' ' << value;
    in >> token;
    return out.str().size() + both.str().size() + token.size();
}

__declspec(dllexport) unsigned long long probe_stl_smart(std::size_t size)
{
    std::unique_ptr<unsigned char[]> buffer(new unsigned char[size]);
    std::unique_ptr<IMAGE_EXPORT_DIRECTORY> directory(new IMAGE_EXPORT_DIRECTORY());
    std::unique_ptr<IMAGE_DOS_HEADER> header(new IMAGE_DOS_HEADER());
    std::shared_ptr<std::vector<unsigned char> > shared(
        new std::vector<unsigned char>(size));

    buffer[0] = 0;
    directory->NumberOfNames = 0;
    header->e_magic = 0;
    shared->push_back(1);
    return (unsigned long long)buffer[0]
           + (unsigned long long)directory->NumberOfNames
           + (unsigned long long)header->e_magic
           + (unsigned long long)shared->size();
}

__declspec(dllexport) unsigned long long probe_stl_algorithm(unsigned long long seed)
{
    /* std::shuffle over a vector is what instantiates _Rng_from_urng_v2,
       which BlackBone carries on both architectures. */
    std::vector<unsigned long long> values;
    std::vector<unsigned char> bytes;
    std::random_device device;
    int index;

    for (index = 0; index < 16; ++index) {
        values.push_back(seed + (unsigned long long)index);
        bytes.push_back((unsigned char)index);
    }
    std::sort(values.begin(), values.end());
    std::sort(bytes.begin(), bytes.end());
    std::shuffle(values.begin(), values.end(), device);
    std::reverse(values.begin(), values.end());
    return values.front() + (unsigned long long)bytes.front()
           + (unsigned long long)std::count(bytes.begin(), bytes.end(), 0);
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

_PROBE_STL_ASSOC = """\
#include <windows.h>
#include <map>
#include <set>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

__declspec(dllexport) std::size_t probe_stl_tree(unsigned long long key,
                                                 unsigned int tag,
                                                 const wchar_t *name)
{
    /* _Tree_val::_Insert_node, _Tree_temp_node, _Tree_head_scoped_ptr,
       _Erase_tree and _Throw_tree_length_error all come from here. */
    std::map<unsigned long long, unsigned long long> byAddress;
    std::map<std::pair<unsigned long long, unsigned int>, unsigned long long> byRegion;
    std::map<std::pair<std::wstring, std::wstring>, unsigned long long> byName;
    std::map<std::wstring, unsigned long> byModule;
    std::set<int> identifiers;
    std::set<unsigned long long> addresses;
    std::size_t total;
    int index;

    byAddress[key] = key + 1;
    byAddress.insert(std::make_pair(key + 2, key + 3));
    byAddress.emplace(key + 4, key + 5);
    byAddress.erase(key + 2);
    if (byAddress.find(key) != byAddress.end()) {
        byAddress.erase(byAddress.begin());
    }
    byRegion[std::make_pair(key, tag)] = key;
    byName[std::make_pair(std::wstring(name), std::wstring(name))] = key;
    byModule[std::wstring(name)] = (unsigned long)tag;
    for (index = 0; index < 8; ++index) {
        identifiers.insert(index);
        addresses.insert(key + (unsigned long long)index);
    }
    identifiers.erase(1);
    addresses.erase(key);

    total = byAddress.size() + byRegion.size() + byName.size()
            + byModule.size() + identifiers.size() + addresses.size();
    byAddress.clear();
    byRegion.clear();
    byName.clear();
    byModule.clear();
    identifiers.clear();
    addresses.clear();
    return total;
}

__declspec(dllexport) std::size_t probe_stl_hash(unsigned long long key,
                                                 unsigned long id,
                                                 const wchar_t *name,
                                                 const char *symbol)
{
    /* MSVC builds unordered_map on std::list, so _Hash::*, _Hash_vec,
       _List_node_emplace_op2 and _Alloc_construct_ptr all arrive together -
       which is exactly the shape of what survives in BlackBone. */
    std::unordered_map<std::wstring, unsigned int> byName;
    std::unordered_map<std::wstring, std::vector<std::wstring> > byDirectory;
    std::unordered_map<unsigned long, int> byId;
    std::unordered_map<unsigned long long, std::pair<unsigned long long, bool> > byOffset;
    std::unordered_map<std::string, FARPROC> byExport;
    std::unordered_map<void *, void *> byPointer;
    std::size_t total;
    int index;

    for (index = 0; index < 8; ++index) {
        byName[std::wstring(name)] = (unsigned int)index;
        byId[id + (unsigned long)index] = index;
        byOffset.emplace(key + (unsigned long long)index,
                         std::make_pair(key, true));
    }
    byName.emplace(std::wstring(name), 2u);
    byDirectory[std::wstring(name)].push_back(std::wstring(name));
    byId.erase(id);
    byOffset.count(key);
    byOffset.find(key);
    byExport[std::string(symbol)] = (FARPROC)0;
    byPointer[(void *)name] = (void *)symbol;

    total = byName.size() + byDirectory.size() + byId.size()
            + byOffset.size() + byExport.size() + byPointer.size();
    byName.clear();
    byDirectory.clear();
    byId.clear();
    byOffset.clear();
    byExport.clear();
    byPointer.clear();
    return total;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

_PROBE_STL_FUNC = """\
#include <windows.h>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <vector>

static bool probe_stl_collect(unsigned long long address,
                              std::vector<unsigned long long> &found,
                              unsigned long long limit)
{
    found.push_back(address);
    return found.size() < (std::size_t)limit;
}

static void probe_stl_nothing(void)
{
}

static bool probe_stl_is_empty(const std::wstring &value)
{
    return value.empty();
}

/* An abstract class is what puts _purecall in an image; BlackBone carries
   it. No lambdas anywhere in this file: MSVC names a lambda after the
   enclosing scope in a spelling that starts with a backtick, which would
   make the probe's own functions harder to keep out of the baseline. */
struct ProbeInterface
{
    virtual ~ProbeInterface() {}
    virtual unsigned long long value() const = 0;
};

struct ProbeImplementation : ProbeInterface
{
    virtual unsigned long long value() const { return 1; }
};

static std::vector<unsigned long long> &probe_stl_shared_state(void)
{
    /* A function-local static with a non-trivial constructor is what emits
       _Init_thread_header, _Init_thread_footer and _Init_thread_abort. */
    static std::vector<unsigned long long> state(4);
    return state;
}

__declspec(dllexport) std::size_t probe_stl_callable(unsigned long long limit)
{
    /* std::bind over a free function taking a vector by reference is the
       shape BlackBone's pattern search uses, down to the _Binder arguments:
       a placeholder, a reference_wrapper and a bound lvalue. */
    std::vector<unsigned long long> found;
    unsigned long long bound = limit;
    std::function<bool(unsigned long long)> callback =
        std::bind(probe_stl_collect, std::placeholders::_1,
                  std::ref(found), bound);
    std::function<bool(unsigned long long)> copy(callback);
    std::function<void(void)> simple = probe_stl_nothing;
    std::function<bool(const std::wstring &)> byName = probe_stl_is_empty;

    callback(limit);
    copy(limit + 1);
    simple();
    byName(std::wstring(L"x"));
    callback = nullptr;
    return found.size();
}

__declspec(dllexport) std::size_t probe_stl_optional(const wchar_t *text)
{
    /* optional::value() is what reaches _Throw_bad_optional_access and the
       bad_optional_access constructors, three functions BlackBone carries
       on both architectures. */
    std::optional<std::wstring> maybe;
    std::optional<unsigned long long> number;
    ProbeImplementation implementation;
    ProbeInterface *held = &implementation;

    maybe = std::wstring(text);
    number = 1;
    return maybe.value().size()
           + (std::size_t)number.value_or(0)
           + (std::size_t)held->value()
           + probe_stl_shared_state().size();
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

# MSVC only, and the second round of STL probes. Everything below answers a
# measurement of what the *first* round left behind, so it is worth recording
# what that measurement said, because it is not what it looked like.
#
# Reading the committed exports back (scripts/corpus/baseline.py cannot do
# this itself - it was done by decompressing function_entries out of the four
# .mcrit files) and splitting the surviving runtime functions by whether the
# instantiating type is the project's own:
#
#     BlackBone x64   1677 functions   274 runtime   124 over standard types
#     BlackBone x86   1875 functions   254 runtime   125 over standard types
#     VX-API    x64    699 functions    17 runtime    17 over standard types
#     VX-API    x86    686 functions    20 runtime    20 over standard types
#
# The 124 and 125 are the reachable part. The surprise is in how they missed:
# of BlackBone x64's 124, exactly *three* carry a name that also appears in
# that artefact's removed_runtime_functions list. The other 121 have names
# the round-one probe never produced at all - not names it produced with a
# different body.
#
# The reason is that MSVC instantiates a member template on its argument
# category and width, not just on the container type. The round-one probe has
# std::unordered_map<std::wstring, unsigned int> and so does BlackBone, but
# the probe writes `byName.emplace(wstring, 2u)` and BlackBone writes the
# equivalent of `byName.emplace(wstring, someUnsignedLong)`, which is
# `emplace<wstring, unsigned long &>` - a different function with a different
# name, and name is half of what is_glue matches on. The same split explains
# vector (`push_back(x)` is `_Emplace_one_at_back<T &>`, `push_back(x + 1)`
# is `_Emplace_one_at_back<T>`), map (`emplace(a, b)` on lvalues versus
# prvalues) and unordered_map's operator[] (`_Try_emplace<K const &>` versus
# `_Try_emplace<K>`).
#
# Two smaller causes were measured alongside it and are fixed here too:
#
#   * The round-one hash probe assigned the *same* key in each iteration of
#     its loop - `byName[std::wstring(name)] = index` - so those maps never
#     held more than one element and _Forced_rehash, _Hash_vec::_Assign_grow
#     and the _List_node helpers they call were never instantiated at all.
#     Every loop below builds distinct keys and inserts enough of them to
#     force several rehashes.
#
#   * The mapped type of BlackBone's forwarder map is `unsigned __int64` on
#     x64 and `unsigned int` on x86; it is std::size_t on each. The round-one
#     probe spelled it `unsigned long long`, which is the x64 instantiation
#     on both architectures, so the x86 one was never in the baseline. Same
#     for its ptr_t-keyed unordered_map.
#
# Split four ways for the usual reason: a probe that will not build is not
# fatal, but it silently shrinks the baseline, so one bad line should cost
# one container family rather than all of them.
_PROBE_STL_GROW = """\
#include <windows.h>
#include <stdlib.h>
#include <memory>
#include <string>
#include <utility>
#include <vector>

static void *__stdcall probe_stl_grow_release(void *block)
{
    free(block);
    return NULL;
}

__declspec(dllexport) std::size_t probe_stl_grow_bytes(unsigned char *data,
                                                       const char *text,
                                                       std::size_t size)
{
    /* _Construct_n<char const *,char const *> and the
       _Copy_memmove<char const *,unsigned char *> it calls both need a
       *narrow* char range built into a vector of unsigned char, which is how
       BlackBone fills a buffer it has just read out of a process.
       _Assign_counted_range<unsigned char *> needs a non-const source. */
    std::vector<unsigned char> raw(text, text + size);
    std::vector<unsigned char> copy;
    std::vector<unsigned char> assigned;
    std::vector<unsigned char> bytes;
    std::size_t index;

    assigned.assign(data, data + size);
    copy = assigned;
    copy.reserve(size + 512);
    bytes.resize(size + 64);
    for (index = 0; index < 256; ++index) {
        bytes.push_back((unsigned char)index);
        raw.push_back((unsigned char)index);
    }
    bytes.resize(size + 4096);
    return raw.size() + copy.size() + assigned.size() + bytes.size();
}

__declspec(dllexport) std::size_t probe_stl_grow_words(std::size_t count)
{
    /* Every push_back here takes an *lvalue*. MSVC instantiates
       _Emplace_one_at_back and _Emplace_reallocate on the argument category,
       so push_back(x) and push_back(x + 1) are two different template
       instantiations with two different names; the committed artefacts carry
       the lvalue ones and the round-one probe only had the prvalue ones. */
    std::vector<unsigned long> words;
    std::vector<unsigned long long> quads;
    std::vector<std::size_t> sizes;
    std::vector<std::pair<unsigned long long, unsigned long long> > ranges;
    std::vector<std::pair<unsigned int, unsigned int> > pairs;
    std::size_t index;
    unsigned long word;
    unsigned long long quad;
    unsigned long long other;
    unsigned int low;
    unsigned int high;

    for (index = 0; index < 256; ++index) {
        word = (unsigned long)index;
        quad = (unsigned long long)index;
        other = quad + 1;
        low = (unsigned int)index;
        high = low + 1;
        words.push_back(word);
        quads.push_back(quad);
        sizes.push_back(index);
        ranges.emplace_back(quad, other);
        /* _Emplace_reallocate<int,unsigned __int64 &>, which is what an
           integer literal first element produces on x86. */
        ranges.emplace_back(0, other);
        pairs.emplace_back(low, high);
    }
    ranges.reserve(ranges.size() * 2 + count);
    quads.reserve(quads.size() * 2);
    return words.size() + quads.size() + sizes.size() + ranges.size()
           + pairs.size();
}

__declspec(dllexport) std::size_t probe_stl_grow_records(std::size_t count,
                                                         const wchar_t *name)
{
    /* push_back of a non-const lvalue record reaches
       _Emplace_reallocate<T &>, push_back of a const reference reaches
       _Emplace_reallocate<T const &>, and emplace_back of a temporary
       wstring reaches _Emplace_reallocate<wstring> and the
       _Uninitialized_move the reallocation runs. BlackBone carries all
       four. */
    std::vector<MEMORY_BASIC_INFORMATION64> regions;
    std::vector<IMAGE_SECTION_HEADER> sections;
    std::vector<std::wstring> names;
    MEMORY_BASIC_INFORMATION64 region;
    IMAGE_SECTION_HEADER section;
    const IMAGE_SECTION_HEADER &constSection = section;
    std::size_t index;

    ZeroMemory(&region, sizeof(region));
    ZeroMemory(&section, sizeof(section));
    for (index = 0; index < 64; ++index) {
        region.BaseAddress = (ULONGLONG)index;
        section.VirtualAddress = (DWORD)index;
        regions.push_back(region);
        sections.push_back(constSection);
        names.emplace_back(std::wstring(name));
    }
    regions.resize(count + 128);
    names.reserve(names.size() * 2);
    return regions.size() + sections.size() + names.size();
}

__declspec(dllexport) std::size_t probe_stl_grow_owned(std::size_t size)
{
    /* unique_ptr is instantiated on its deleter as well as its pointee, and
       BlackBone's are function pointers rather than default_delete:
       unique_ptr<_IMAGE_EXPORT_DIRECTORY,void (__cdecl*)(void *)> on both
       architectures and unique_ptr<void,void *(__stdcall*)(void *)> on x86,
       which is what holding a VirtualFree-style releaser looks like. The
       round-one probe only had the default_delete instantiations. */
    std::unique_ptr<IMAGE_EXPORT_DIRECTORY, void (__cdecl *)(void *)>
        directory((IMAGE_EXPORT_DIRECTORY *)malloc(sizeof(IMAGE_EXPORT_DIRECTORY)),
                  &free);
    std::unique_ptr<void, void *(__stdcall *)(void *)>
        region(NULL, &probe_stl_grow_release);
    std::unique_ptr<unsigned char[], void (__cdecl *)(void *)>
        buffer((unsigned char *)malloc(size + 1), &free);

    if (directory) {
        directory->NumberOfNames = 0;
    }
    if (buffer) {
        buffer[0] = 0;
    }
    return (std::size_t)(directory ? 1 : 0) + (region ? 2 : 0)
           + (buffer ? 4 : 0);
}

__declspec(dllexport) std::size_t probe_stl_grow_strings(const char *text,
                                                         const wchar_t *wide)
{
    /* push_back on a string is its own _Reallocate_grow_by instantiation,
       named after the lambda inside push_back rather than the one inside
       append, and BlackBone carries both. The loop count is what makes the
       reallocating path run often enough to stay out of line. */
    std::string narrow;
    std::wstring wideText;
    std::wstring built;
    std::string assigned;
    std::size_t index;

    narrow.assign(text);
    assigned = narrow;
    assigned.assign(text);
    wideText.assign(wide);
    wideText.reserve(4096);
    for (index = 0; index < 1024; ++index) {
        narrow.push_back((char)('a' + (index & 15)));
        built.push_back((wchar_t)(L'a' + (index & 15)));
        wideText.append(wide);
        narrow.append(text);
    }
    built = wideText;
    return narrow.size() + wideText.size() + built.size() + assigned.size()
           + std::to_wstring((unsigned long)narrow.size()).size()
           + std::to_wstring((int)built.size()).size()
           + std::to_wstring(built.size()).size();
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

_PROBE_STL_HASH = """\
#include <windows.h>
#include <cstddef>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

__declspec(dllexport) std::size_t probe_stl_hash_exports(const char *symbol)
{
    /* unordered_map<string, FARPROC> is BlackBone's export cache. FARPROC is
       spelled __int64 (__cdecl*)(void) on x64 and int (__stdcall*)(void) on
       x86, so naming the typedef covers both without spelling either. */
    std::unordered_map<std::string, FARPROC> byExport;
    std::string key;
    std::size_t index;
    std::size_t found = 0;

    for (index = 0; index < 96; ++index) {
        key = symbol;
        key.push_back((char)('a' + (index & 15)));
        key.push_back((char)('a' + ((index >> 4) & 15)));
        byExport.emplace(std::make_pair(key, (FARPROC)0));
        byExport[key] = (FARPROC)0;
    }
    for (index = 0; index < 96; ++index) {
        key = symbol;
        key.push_back((char)('a' + (index & 15)));
        key.push_back((char)('a' + ((index >> 4) & 15)));
        if (byExport.find(key) != byExport.end()) {
            ++found;
        }
        found += byExport.count(key);
    }
    byExport.erase(key);
    byExport.clear();
    return found + byExport.size();
}

__declspec(dllexport) std::size_t probe_stl_hash_modules(const wchar_t *name)
{
    /* emplace<wchar_t (&)[260],vector<wstring> > is the instantiation a
       WCHAR path[MAX_PATH] lvalue produces, and it is what BlackBone's
       module enumeration leaves behind on both architectures. */
    std::unordered_map<std::wstring, std::vector<std::wstring> > byDirectory;
    std::unordered_map<std::wstring, unsigned int> byName;
    wchar_t path[260];
    std::wstring key;
    std::size_t index;
    unsigned long tag = 0;

    for (index = 0; index < 96; ++index) {
        path[0] = (wchar_t)(L'a' + (index & 15));
        path[1] = (wchar_t)(L'a' + ((index >> 4) & 15));
        path[2] = L'\\0';
        byDirectory.emplace(path, std::vector<std::wstring>());
        byDirectory[path].push_back(std::wstring(name));

        key.assign(path);
        tag = (unsigned long)index;
        /* emplace<wstring,unsigned long &>: the mapped argument is an lvalue
           of a wider type than the mapped_type. */
        byName.emplace(key, tag);
        byName[key] = (unsigned int)index;
    }
    byName.erase(key);
    byDirectory.erase(key);
    byName.clear();
    byDirectory.clear();
    return byName.size() + byDirectory.size() + (std::size_t)tag;
}

__declspec(dllexport) std::size_t probe_stl_hash_offsets(std::size_t key,
                                                         unsigned long id)
{
    /* Two key widths on purpose. BlackBone's ptr_t-keyed map is
       unordered_map<unsigned __int64, ...> on x64 and
       unordered_map<unsigned int, ...> on x86 - std::size_t on each - while
       the round-one probe spelled it unsigned long long and so only ever
       produced the x64 instantiation. Both are kept: the wide one is a real
       instantiation in the x64 artefact. */
    std::unordered_map<std::size_t, std::pair<std::size_t, bool> > bySize;
    std::unordered_map<unsigned long long,
                       std::pair<unsigned long long, bool> > byOffset;
    std::unordered_map<unsigned long, int> byId;
    std::size_t index;
    std::size_t found = 0;

    for (index = 0; index < 96; ++index) {
        const std::size_t &constKey = key;
        unsigned long long wide = (unsigned long long)(key + index);

        /* _Try_emplace<size_t const &> from an lvalue subscript and
           _Try_emplace<size_t> from a prvalue one: two functions, two
           names, and the artefacts carry one of each. */
        bySize[constKey] = std::make_pair(key, true);
        bySize[key + index] = std::make_pair(key, false);
        bySize.emplace(key + index, std::make_pair(key, true));
        byOffset.emplace(wide, std::make_pair(wide, true));
        byOffset[wide] = std::make_pair(wide, false);
        byId[id + (unsigned long)index] = (int)index;
        found += bySize.count(key + index);
        found += byOffset.count(wide);
        if (byId.find(id + (unsigned long)index) != byId.end()) {
            ++found;
        }
    }
    byId.erase(id);
    bySize.erase(key);
    byOffset.erase((unsigned long long)key);
    bySize.clear();
    byOffset.clear();
    byId.clear();
    return found + bySize.size() + byOffset.size() + byId.size();
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

_PROBE_STL_TREE = """\
#include <windows.h>
#include <cstddef>
#include <map>
#include <set>
#include <string>
#include <utility>

__declspec(dllexport) std::size_t probe_stl_tree_names(wchar_t *first,
                                                       wchar_t *second,
                                                       unsigned long tag)
{
    /* map<pair<wstring,wstring>, size_t> is BlackBone's forwarder table. The
       mapped type is unsigned __int64 on x64 and unsigned int on x86, which
       is std::size_t on each.

       _Emplace<pair<wchar_t *,wchar_t *>,unsigned long &> needs exactly
       this: a pair of *non-const* wchar_t pointers and an unsigned long
       lvalue. Copying the map is what reaches _Copy, _Copy_nodes,
       _Tree_temp_node and _Tree_head_scoped_ptr, all four of which survive
       on both architectures today. */
    std::map<std::pair<std::wstring, std::wstring>, std::size_t> byName;
    std::size_t index;
    std::size_t total;

    for (index = 0; index < 64; ++index) {
        first[0] = (wchar_t)(L'a' + (index & 15));
        second[0] = (wchar_t)(L'a' + ((index >> 4) & 15));
        tag = (unsigned long)index;
        byName.emplace(std::make_pair(first, second), tag);
        byName[std::make_pair(std::wstring(first), std::wstring(second))] =
            (std::size_t)index;
    }

    std::map<std::pair<std::wstring, std::wstring>, std::size_t> copy(byName);
    std::map<std::pair<std::wstring, std::wstring>, std::size_t> assigned;

    assigned = copy;
    total = byName.size() + copy.size() + assigned.size();
    byName.erase(byName.begin());
    copy.clear();
    assigned.clear();
    return total;
}

__declspec(dllexport) std::size_t probe_stl_tree_regions(unsigned long long key,
                                                         unsigned long tag)
{
    /* map<unsigned __int64,bool>, and the lvalue-argument emplace on
       map<unsigned __int64,unsigned __int64>, are both in the residue on
       both architectures; the round-one probe only had the prvalue one. */
    std::map<unsigned long long, unsigned long long> byAddress;
    std::map<unsigned long long, bool> byFlag;
    std::map<std::pair<unsigned long long, unsigned int>,
             unsigned long long> byRegion;
    std::size_t index;
    std::size_t total = 0;

    for (index = 0; index < 64; ++index) {
        unsigned long long lo = key + (unsigned long long)index;
        unsigned long long hi = lo + 1;

        byAddress.emplace(lo, hi);
        byAddress[lo] = hi;
        byFlag[lo] = true;
        byRegion.emplace(std::make_pair(std::make_pair(lo, tag), hi));
        byRegion[std::make_pair(lo, (unsigned int)tag)] = hi;
        if (byAddress.lower_bound(lo) != byAddress.end()) {
            ++total;
        }
    }
    byAddress.erase(key);
    byAddress.erase(byAddress.begin());
    byFlag.erase(key);
    byRegion.clear();
    total += byAddress.size() + byFlag.size() + byRegion.size();
    byAddress.clear();
    byFlag.clear();
    return total;
}

__declspec(dllexport) std::size_t probe_stl_tree_identifiers(int seed)
{
    /* set<int>::emplace<int &> and _Find_lower_bound<int> are separate
       instantiations from the insert(int) the round-one probe called. */
    std::set<int> identifiers;
    std::set<unsigned long long> addresses;
    int index;
    std::size_t total = 0;

    for (index = 0; index < 64; ++index) {
        int value = seed + index;
        unsigned long long wide = (unsigned long long)value;

        identifiers.emplace(value);
        identifiers.insert(value + 1);
        addresses.emplace(wide);
        if (identifiers.lower_bound(value) != identifiers.end()) {
            ++total;
        }
    }
    identifiers.erase(seed);
    addresses.erase((unsigned long long)seed);
    total += identifiers.size() + addresses.size();
    identifiers.clear();
    addresses.clear();
    return total;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

# MSVC only. The standard exception objects and the compiler-generated array
# helpers, which are the one group that survives in *all four* committed
# artefacts - VX-API included, and VX-API is built with exactly the flags
# this probe uses (/O2 /MD /Zi /std:c++20), so nothing about optimisation
# settings explains its residue. It is pure coverage.
#
# Round one did reach the default constructors of bad_alloc,
# bad_array_new_length and bad_optional_access - all three are in BlackBone
# x64's removed_runtime_functions - and all three are still present as a
# *second* body of the same name. Those are the copy constructors, which is
# why every object below is both constructed and copied.
_PROBE_STL_THROW = """\
#include <windows.h>
#include <string.h>
#include <exception>
#include <new>
#include <optional>
#include <stdexcept>
#include <string>

/* A class with a non-trivial constructor *and* a non-trivial destructor is
   the only thing that makes the compiler emit `eh vector constructor
   iterator', `eh vector destructor iterator' and __ArrayUnwind, and all
   three survive in all four committed MSVC artefacts. The member has to be
   something the compiler cannot elide, hence a wstring rather than an int. */
struct ProbeArrayElement
{
    ProbeArrayElement() : text(L"probe"), value(0) {}
    ~ProbeArrayElement() { value = 0; }

    std::wstring text;
    int value;
};

__declspec(dllexport) std::size_t probe_stl_throw_arrays(std::size_t count)
{
    ProbeArrayElement onStack[8];
    ProbeArrayElement *onHeap = new ProbeArrayElement[count + 4];
    std::size_t total = 0;
    std::size_t index;

    for (index = 0; index < 8; ++index) {
        onStack[index].value = (int)index;
        total += onStack[index].text.size();
    }
    for (index = 0; index < count + 4; ++index) {
        onHeap[index].value = (int)index;
        total += onHeap[index].text.size();
    }
    delete[] onHeap;
    return total;
}

__declspec(dllexport) std::size_t probe_stl_throw_objects(int selector)
{
    std::bad_alloc allocation;
    std::bad_alloc allocationCopy(allocation);
    std::bad_array_new_length length;
    std::bad_array_new_length lengthCopy(length);
    std::bad_optional_access absent;
    std::bad_optional_access absentCopy(absent);
    std::exception plain;
    std::exception plainCopy(plain);
    /* Deleting through a base pointer is what emits the scalar deleting
       destructors, which are residue on the x86 side of both families. */
    std::exception *owned = new std::bad_alloc();
    std::exception *ownedLength = new std::bad_array_new_length();
    std::size_t total = 0;

    total += strlen(allocationCopy.what());
    total += strlen(lengthCopy.what());
    total += strlen(absentCopy.what());
    total += strlen(plainCopy.what());
    total += strlen(owned->what());
    total += strlen(ownedLength->what());
    delete owned;
    delete ownedLength;
    if (selector) {
        throw allocationCopy;
    }
    return total;
}

__declspec(dllexport) std::size_t probe_stl_throw_helpers(const wchar_t *text,
                                                          std::size_t where)
{
    /* _Xlen_string, _String_val::_Xran, _Throw_tree_length_error,
       _Throw_bad_array_new_length and _Throw_bad_optional_access are
       out-of-line throwers the headers call, and they only exist in an image
       that can reach them. */
    std::wstring wide(text);
    std::optional<std::wstring> maybe;
    std::size_t total = 0;

    try {
        total += wide.substr(where, 4).size();
        total += (std::size_t)wide.at(where);
        total += maybe.value().size();
    } catch (const std::out_of_range &) {
        total += 1;
    } catch (const std::bad_optional_access &) {
        total += 2;
    } catch (const std::length_error &) {
        total += 3;
    } catch (const std::bad_alloc &) {
        total += 4;
    }
    return total;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

# MSVC only, and the third round. `vector constructor iterator' - the one
# without the "eh" - is the array helper the probes above never emitted, and
# it sits in 7-Zip, abseil, cryptopp, protobuf and re2 at once (22
# instructions on x64) and in abseil, protobuf and re2 on x86 (20).
#
# The distinction is measured rather than assumed. _PROBE_STL_THROW's
# ProbeArrayElement holds a std::wstring, so its constructor can throw and
# the compiler has to be able to destroy the elements already built: that is
# `eh vector constructor iterator', and the provenance of all four round-two
# families shows it (and `eh vector destructor iterator', __ArrayUnwind and
# the $+0x fragment labels of both) being removed. `vector constructor
# iterator' is what the compiler emits instead when there is nothing to
# unwind - either because the element type has no destructor at all, or
# because its constructor is noexcept - and no probe here had an array of
# such a type.
#
# Both shapes are built because either one alone is an assumption about
# which rule MSVC applies. The constructors call an out-of-line function so
# that the array initialisation cannot be folded into a memset, which would
# leave no helper to emit; that is the same trap as GCC's builtin floor.
_PROBE_STL_ARRAY = """\
#include <windows.h>
#include <cstddef>

__declspec(noinline) unsigned long long probe_stl_array_seed(void)
{
    return 1;
}

__declspec(noinline) unsigned long long probe_stl_array_tag(void) noexcept
{
    return 2;
}

/* No destructor: if the constructor throws there is nothing to unwind, so
   the plain iterator is used. */
struct ProbeArrayPlain
{
    ProbeArrayPlain() : value(probe_stl_array_seed()), link(0) {}

    unsigned long long value;
    void *link;
};

/* A destructor, but a constructor that cannot throw, which is the other way
   of reaching the same helper. */
struct ProbeArrayGuarded
{
    ProbeArrayGuarded() noexcept : value(probe_stl_array_tag()) {}
    ~ProbeArrayGuarded() { value = 0; }

    unsigned long long value;
};

/* A member array is a third emission site, and the one a class with a fixed
   pool of sub-objects has. */
struct ProbeArrayHolder
{
    ProbeArrayHolder() : count(0) {}

    ProbeArrayPlain members[8];
    unsigned long long count;
};

__declspec(dllexport) unsigned long long probe_stl_array_plain(std::size_t count)
{
    ProbeArrayPlain onStack[8];
    ProbeArrayPlain *onHeap = new ProbeArrayPlain[count + 4];
    ProbeArrayHolder holder;
    unsigned long long total = 0;
    std::size_t index;

    for (index = 0; index < 8; ++index) {
        onStack[index].value += index;
        total += onStack[index].value;
    }
    for (index = 0; index < count + 4; ++index) {
        onHeap[index].value += index;
        total += onHeap[index].value;
    }
    delete[] onHeap;
    return total + holder.members[0].value + holder.count;
}

__declspec(dllexport) unsigned long long probe_stl_array_guarded(std::size_t count)
{
    ProbeArrayGuarded onStack[8];
    ProbeArrayGuarded *onHeap = new ProbeArrayGuarded[count + 4];
    unsigned long long total = 0;
    std::size_t index;

    for (index = 0; index < 8; ++index) {
        onStack[index].value += index;
        total += onStack[index].value;
    }
    for (index = 0; index < count + 4; ++index) {
        onHeap[index].value += index;
        total += onHeap[index].value;
    }
    /* delete[] of a type with a destructor is what emits
       `vector destructor iterator', which is already in the baseline from
       VX-API's side and is kept here so the two helpers stay together. */
    delete[] onHeap;
    return total;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

# MSVC only, third round. The <xstring> growth lambdas.
#
# MSVC gives an unnamed lambda a name derived from its source, so the same
# `<lambda_HEX>` appearing in nlohmann_json, protobuf, re2 and abseil - which
# share no code - means a lambda out of a header all four include. Reading
# the committed reports back identifies it exactly, because the function that
# takes the lambda carries it in its own name:
#
#     std::basic_string<char,...>::_Reallocate_grow_by<
#         <lambda_65e615be2a453ca0576c979606f46740>,char const *,unsigned __int64>
#
# The types after the lambda are the arguments the member forwards, so each
# one names a std::string member exactly:
#
#     <char>                              push_back(char)
#     <char const *,size_t>               append(const char *, size_t)
#     <size_t,char>                       append(size_t, char) / resize
#     <size_t,size_t,char>                insert(off, count, char)
#     <size_t,char const *,size_t>        insert(off, ptr, count)
#     <size_t,size_t,char const *,size_t> replace(off, count, ptr, count)
#
# and the bodies agree: the replace lambda is three memcpy calls (prefix,
# replacement, tail), the push_back one is a memcpy followed by storing one
# character and a NUL.
#
# Three of these are already in the baseline - the provenance of all four
# families shows the append, resize and insert(off,count,char) lambdas being
# removed - and they come from _PROBE_STL_SEQ's probe_stl_string, which calls
# append, resize and insert(begin(), ch) once each. So the mechanism works:
# a probe that calls the member emits the lambda, name and body both.
#
# replace and insert(off, ptr, count) are simply not called anywhere in this
# file, which accounts for the two residual replace lambdas outright.
#
# push_back is the one this cannot explain. _PROBE_STL_GROW does call
# std::string::push_back, in a loop, and that probe demonstrably builds - its
# unique_ptr<_IMAGE_EXPORT_DIRECTORY,void (__cdecl*)(void *)> destructor is
# in BlackBone x64's removed list and exists nowhere else here - yet no
# push_back lambda is in the glue set on either architecture. Nothing in the
# committed data says why. This is therefore a second attempt rather than a
# change to a probe that works: a small translation unit whose only subject
# is <xstring> growth, calling push_back from three separate exported
# functions so the compiler has no single obvious place to put the body.
# That is the same reasoning _PROBE_ATL_MODULES and _PROBE_ATL_THROW are
# written on.
#
# Every offset is 0 so no call can be out of range: replace and insert throw
# std::out_of_range past size(), and a probe whose behaviour is undefined is
# not a measurement.
_PROBE_STL_STRING = """\
#include <windows.h>
#include <cstddef>
#include <string>

__declspec(dllexport) std::size_t probe_stl_string_push(const char *text,
                                                        char letter)
{
    std::string narrow(text);
    std::size_t index;

    for (index = 0; index < 512; ++index) {
        narrow.push_back(letter);
    }
    return narrow.size();
}

__declspec(dllexport) std::size_t probe_stl_string_push_again(const char *text,
                                                              std::size_t count)
{
    std::string narrow(text);
    std::size_t index;

    for (index = 0; index < count + 512; ++index) {
        narrow.push_back((char)('a' + (index & 15)));
    }
    return narrow.size();
}

__declspec(dllexport) std::size_t probe_stl_string_push_wide(const wchar_t *text,
                                                             wchar_t letter)
{
    std::wstring wide(text);
    std::string narrow;
    std::size_t index;

    for (index = 0; index < 512; ++index) {
        wide.push_back(letter);
        narrow.push_back((char)letter);
        narrow += (char)letter;
    }
    return wide.size() + narrow.size();
}

__declspec(dllexport) std::size_t probe_stl_string_replace(const char *text,
                                                           std::size_t count)
{
    std::string narrow(text);
    std::size_t index;

    for (index = 0; index < 256; ++index) {
        narrow.replace(0, 1, text, count + 1);
        narrow.insert(0, text, count + 1);
        narrow.insert(0, count + 1, 'x');
        narrow.append(text, count + 1);
        narrow.append(count + 1, 'y');
    }
    return narrow.size();
}

__declspec(dllexport) std::size_t probe_stl_string_replace_wide(const wchar_t *text,
                                                                std::size_t count)
{
    std::wstring wide(text);
    std::size_t index;

    for (index = 0; index < 256; ++index) {
        wide.replace(0, 1, text, count + 1);
        wide.insert(0, text, count + 1);
        wide.insert(0, count + 1, L'x');
        wide.append(text, count + 1);
        wide.append(count + 1, L'y');
    }
    return wide.size();
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

# MSVC only. ATL's module objects, again - but with several call sites this
# time.
#
# _PROBE_ATL_COM's probe_atl_modules already builds a CAtlWinModule and a
# CAtlComModule, and on x86 that was enough: AtlWinModuleTerm and
# CAtlWinModule::Term are both in VX-API x86's removed list. On x64 they are
# not, and ~CAtlWinModule is in neither. One local object is one call site,
# and /O2 inlines a destructor it can only reach once; VX-API reaches these
# from many places and therefore keeps an out-of-line copy. This is the same
# problem, and the same fix, as the MinGW builtin trap: give the compiler no
# single obvious place to put the body.
#
# Separate from _PROBE_ATL_COM because that probe works and removed 287
# functions from VX-API x64; nothing here is worth risking it for.
_PROBE_ATL_MODULES = """\
#include <windows.h>
#include <atlbase.h>

__declspec(dllexport) HINSTANCE probe_atl_modules_first(void)
{
    ATL::CAtlWinModule window;
    ATL::CAtlComModule com;

    (void)window;
    (void)com;
    return ATL::_AtlBaseModule.GetModuleInstance();
}

__declspec(dllexport) HINSTANCE probe_atl_modules_second(int which)
{
    ATL::CAtlWinModule window;
    ATL::CAtlComModule com;

    (void)com;
    (void)window;
    return ATL::_AtlBaseModule.GetHInstanceAt(which);
}

__declspec(dllexport) int probe_atl_modules_third(HINSTANCE instance)
{
    ATL::CAtlWinModule window;

    (void)window;
    return ATL::_AtlBaseModule.AddResourceInstance(instance) ? 1 : 0;
}

__declspec(dllexport) int probe_atl_modules_fourth(HINSTANCE instance)
{
    ATL::CAtlWinModule window;
    ATL::CAtlComModule com;

    com.Term();
    (void)window;
    return ATL::_AtlBaseModule.RemoveResourceInstance(instance) ? 1 : 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

# ATL::CComTypeInfoHolder is NOT measured, and this is the record of why
# rather than a probe that pretends to.
#
# Its stringdispid destructor and vector deleting destructor are in both
# VX-API artefacts and nothing else in this file can reach them. A probe
# existed for it and never once compiled: v143's ATL declares
# CComTypeInfoHolder::Cleanup with at least one parameter (atlcom.h:4720),
# so the calls failed with "error C2660: function does not take 0
# arguments" and took the translation unit with them on every run.
#
# Removing the calls made it compile and measure nothing. The two locals
# were kept alive by "static volatile void *sink" - which is a pointer to
# volatile void, not a volatile pointer, so sink is an unread static, both
# stores are dead, and cl is free to emit the function as "mov eax,
# [esp+4]; ret" with the holders gone. Registering that costs two
# compilations and, since a probe that will not build now fails the run,
# carries the risk of failing every MSVC build for nothing.
#
# So it is unregistered. What it would have measured stays attributed to
# whichever family links ATL, and restoring it is a job for whoever next
# has atlcom.h in front of them: find Cleanup's real signature, or call
# GetTI(LCID), and keep the holders alive with "void * volatile sink".

# MSVC only. One function, because CComPtr is instantiated per interface and
# BlackBone's surviving instantiation is over ICLRMetaHost, which lives in
# the Windows SDK's metahost.h rather than in ATL.
_PROBE_ATL_METAHOST = """\
#include <windows.h>
#include <atlbase.h>
#include <metahost.h>

__declspec(dllexport) int probe_atl_metahost(int held)
{
    ATL::CComPtr<ICLRMetaHost> host;
    ATL::CComPtr<ICLRRuntimeInfo> runtime;

    (void)held;
    return !host && !runtime ? 0 : 1;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

# MSVC only. The wide half of the C runtime, which the narrow probe never
# referenced.
#
# swprintf_s and wmemcmp are not library exports: the UCRT headers define
# them inline, so a copy is emitted into whatever object calls them, and
# VX-API and BlackBone both carry such a copy. _vfwprintf_l and
# __stdio_common_vfwprintf arrive with any wide formatted output.
#
# Taking the address is the same trick the narrow probe uses, and for the
# same reason: /O2 implies /Oi, and an inline the compiler can see through is
# an inline the baseline never gets a body for.
_PROBE_MSVCRT_WIDE = """\
#define _CRT_SECURE_NO_WARNINGS 1
#include <windows.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

typedef void (*probe_symbol)(void);

__declspec(dllexport) probe_symbol probe_msvcrt_wide_symbols[] = {
    (probe_symbol)wmemcmp,
    (probe_symbol)wmemcpy,
    (probe_symbol)wmemmove,
    (probe_symbol)wmemset,
    (probe_symbol)wmemchr,
    (probe_symbol)wcsncpy,
    (probe_symbol)wcsrchr,
    (probe_symbol)wcstoul,
    (probe_symbol)_wcsicmp,
    (probe_symbol)_wcsnicmp,
};

__declspec(dllexport) int probe_msvcrt_wide_format(const wchar_t *text,
                                                   int value, ...)
{
    wchar_t wide[260];
    char narrow[260];
    va_list arguments;
    int result;

    va_start(arguments, value);
    result = vfwprintf(stderr, text, arguments);
    va_end(arguments);
    result += swprintf_s(wide, 260, L"%s %d", text, value);
    result += _snwprintf_s(wide, 260, 259, L"%s", text);
    result += fwprintf(stderr, L"%s %d", wide, value);
    result += sprintf_s(narrow, 260, "%d", value);
    result += (int)wcsnlen(wide, 260);
    return result;
}

__declspec(dllexport) int probe_msvcrt_wide_frames(const wchar_t *text)
{
    /* A second /GS frame shape, in its own translation unit. The narrow
       probe's __security_check_cookie never matched the artefacts' copy and
       nothing measurable from the committed data says why - VX-API is built
       with the probe's own flags and still carries it - so this is a second
       attempt rather than a change to a probe that does work. */
    wchar_t buffer[1024];
    int counts[64];
    int index;
    int total = 0;

    for (index = 0; index < 64; ++index) {
        counts[index] = index;
    }
    wcsncpy(buffer, text, 1023);
    buffer[1023] = L'\\0';
    for (index = 0; index < 64; ++index) {
        total += counts[index] + (int)buffer[index];
    }
    return total;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

# MSVC only, and x86 only in effect. The helper routines cl calls for things
# the 32-bit instruction set cannot do in one instruction: converting a
# floating-point value to a 64-bit integer, and shifting a 64-bit integer by
# a variable amount. They are the exact MSVC analogue of libgcc's
# __udivmoddi4, which round one of the MinGW work caught. On x64 every one of
# these is an instruction, so this unit compiles there and measures nothing.
#
# Which of them the probes already reach was measured from the committed
# provenance rather than guessed. _PROBE_DLL's 64-bit division block is
# compiled by cl as probe_md.c, and its removed_runtime_functions show that
# it already contributes _alldiv, _aulldiv, _allrem, _aullrem, _aulldvrm,
# _allmul, _allshl and _aullshr. The one missing member of that family is
# _allshr - the arithmetic right shift, which needs a *signed* 64-bit value
# and a variable count - and it is sitting in 7-Zip, LuaJIT and sqlite3.
#
# The conversion helpers need more care, because there are two sets of them
# and the probes only ever produced the wrong one. sqlite3, LuaJIT and libpng
# all have _ftol3, _dtol3, _ftoui3, _ftoul3 and _dtoul3_legacy removed by the
# existing baseline, while _ftol2, _ftoi2, _ftoui2 and _ftoul2 survive in
# Lua, LuaJIT, abseil, libpng and libtiff. The "3" set takes its argument in
# an XMM register, which is what /arch:SSE2 code has; the "2" set takes it on
# the x87 stack, which is where a __cdecl function that *returns* a double or
# a float leaves it on x86. That is what the surviving callers are:
# png_build_16bit_table converting the result of pow(), lj_cf_os_date and
# lj_cf_os_difftime converting the result of a function returning double.
# Hence the conversions below all run on the return value of an out-of-line
# function rather than on a variable.
#
# One reference is enough for all of them: libpng calls only _ftol2 and
# carries _ftoi2, _ftoui2, _ftoul2, _ftol2_sse, _ftol2_sse_excpt and
# _ftoul2_legacy beside it, so they arrive as one object. All four
# conversions are written out anyway, because a single line deciding the
# whole group is exactly the line that turns out not to be emitted.
_PROBE_MSVCRT_HELPERS = """\
#include <windows.h>

/* Out of line so the conversions below start from a value on the x87 stack,
   and so that nothing here can be constant-folded. */
__declspec(noinline) double probe_msvcrt_helper_double(double value)
{
    return value * 2.0 + 1.0;
}

__declspec(noinline) float probe_msvcrt_helper_float(float value)
{
    return value * 2.0f + 1.0f;
}

__declspec(dllexport) unsigned __int64 probe_msvcrt_helper_convert(double value,
                                                                   int count)
{
    volatile unsigned __int64 sink = 0;

    sink += (unsigned __int64)probe_msvcrt_helper_double(value);
    sink += (unsigned __int64)(__int64)probe_msvcrt_helper_double(value + 1.0);
    sink += (unsigned __int64)(unsigned int)probe_msvcrt_helper_double(value + 2.0);
    sink += (unsigned __int64)(int)probe_msvcrt_helper_double(value + 3.0);
    sink += (unsigned __int64)probe_msvcrt_helper_float((float)value);
    sink += (unsigned __int64)(__int64)probe_msvcrt_helper_float((float)value + 1.0f);
    sink += (unsigned __int64)(unsigned int)probe_msvcrt_helper_float((float)value + 2.0f);
    sink += (unsigned __int64)(int)probe_msvcrt_helper_float((float)value + 3.0f);
    return sink + (unsigned __int64)count;
}

__declspec(dllexport) __int64 probe_msvcrt_helper_shift(__int64 value,
                                                        unsigned __int64 wide,
                                                        int count)
{
    volatile __int64 sink = 0;

    /* _allshr is the only one of these not already in the baseline; the
       other three are kept so the group is measured together rather than
       depending on which one _PROBE_DLL happens to still emit. */
    sink += value >> count;
    sink += value << count;
    sink += (__int64)(wide >> count);
    sink += (__int64)(wide << count);
    return sink;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

# MSVC only. The formatted-output functions the UCRT headers define inline.
#
# sprintf and _vsprintf_l are not imports under /MD: <stdio.h> defines them
# as _CRT_STDIO_INLINE functions, so a body is compiled into every object
# that uses them. The committed reports show what that means precisely. In
# cJSON x64, sprintf has three callers and calls __local_stdio_printf_options
# and the __stdio_common_vsprintf import directly - the _vsprintf_l inside it
# was inlined - while _vsprintf_l and _vsnprintf_l are *also* in the image as
# full bodies with no callers at all. MSVC emits an out-of-line copy of every
# inline function it instantiated whether or not a call site survived, and
# these links pass /DEBUG, which turns /OPT:REF off, so nothing removes them.
# The probes link the same way, so the same copies will be kept there.
#
# So the rule is: calling the top of a chain emits the whole chain. _PROBE_DLL
# and _PROBE_MSVCRT already call snprintf, _snprintf and swprintf, which is
# why _vsnprintf_l is not among the leaked names - and why sprintf and
# _vsprintf_l are, in Lua, LuaJIT, OpenSSL, cJSON, libcurl, libuv and
# protobuf: nothing here has ever called sprintf or vsprintf. Adding more
# calls to _snprintf would have changed nothing.
#
# The varargs wrappers are real varargs functions rather than a va_list
# conjured from nothing, for the reason the MinGW _vscprintf probe records:
# handing a callee a va_list that was never started is undefined behaviour.
#
# Narrow only. Every name below is already called somewhere in this file or
# is plain C89/C99; the wide half is a separate translation unit because
# vswprintf has two declarations in the UCRT - the conforming four-argument
# one and a three-argument legacy form behind _CRT_NON_CONFORMING_SWPRINTFS -
# and every leaked name here is narrow. A wrong guess there must not cost
# sprintf.
_PROBE_MSVCRT_PRINTF = """\
#define _CRT_SECURE_NO_WARNINGS 1
#include <windows.h>
#include <stdarg.h>
#include <stdio.h>

__declspec(dllexport) int probe_msvcrt_printf_narrow(char *buffer,
                                                     size_t size,
                                                     const char *format, ...)
{
    va_list arguments;
    int total = 0;

    va_start(arguments, format);
    total += vsprintf(buffer, format, arguments);
    va_end(arguments);
    va_start(arguments, format);
    total += vsnprintf(buffer, size, format, arguments);
    va_end(arguments);
    va_start(arguments, format);
    total += _vsnprintf(buffer, size, format, arguments);
    va_end(arguments);
    total += sprintf(buffer, "%s %d", format, total);
    total += snprintf(buffer, size, "%s %d", format, total);
    total += _snprintf(buffer, size, "%s %d", format, total);
    return total;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

# The wide half of the same chain. None of these names is in the twenty
# leaked hashes - libuv's _snwprintf and _vsnwprintf_l are carried by two
# families rather than three - so this is coverage rather than a fix, and it
# is separate from the narrow probe so that it can fail on its own.
_PROBE_MSVCRT_PRINTF_WIDE = """\
#define _CRT_SECURE_NO_WARNINGS 1
#include <windows.h>
#include <stdarg.h>
#include <stdio.h>
#include <wchar.h>

__declspec(dllexport) int probe_msvcrt_printf_wide(wchar_t *buffer,
                                                   size_t size,
                                                   const wchar_t *format, ...)
{
    va_list arguments;
    int total = 0;

    va_start(arguments, format);
    total += vswprintf(buffer, size, format, arguments);
    va_end(arguments);
    va_start(arguments, format);
    total += _vsnwprintf(buffer, size, format, arguments);
    va_end(arguments);
    total += swprintf(buffer, size, L"%s %d", format, total);
    total += _snwprintf(buffer, size, L"%s %d", format, total);
    return total;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

# MSVC only, and x86 only in effect: __EH_prolog and _EH_prolog2 are the
# 32-bit C++ exception-handling frame helpers, and x64 has no such thing.
#
# They are in 7-Zip and in data/MSVC itself, which is as direct a statement
# that they are Microsoft's code as this corpus can make. 7-Zip is also the
# only family here that has them, and that is the measurement this probe is
# built on: every other MSVC C++ family here - abseil, protobuf, re2,
# cryptopp, nlohmann_json, BlackBone, VX-API - uses exceptions heavily and
# carries neither. What 7-Zip does differently is its flags, which its own
# CPP/Build.mak sets: -O1 and -GS-. Both are passed below, because the
# outlined prolog is a size optimisation and because /GS- is what selects the
# __except_handler3 frame these two helpers build, rather than the
# __except_handler4 one that the __EH_prolog3* family in data/MSVC builds.
#
# _EH_prolog2 is __EH_prolog plus a stack realignment - `neg ecx; and esp,
# ecx` - so it needs an over-aligned local as well as a frame to unwind; its
# single caller in 7-Zip x86 is NArchive::NApfs::CDatabase::ReadMap.
#
# It is registered twice, once with /GS- and once without, so that if the
# handler model is not what selects between the two families the /GS run
# still measures whichever __EH_prolog3* bodies cl emits. Neither run can
# lose anything: crt_glue maps a name to a set of hashes.
_PROBE_MSVCRT_EH = """\
#include <windows.h>

struct ProbeEhGuard
{
    ProbeEhGuard(int *counter) : counter(counter) { *counter += 1; }
    ~ProbeEhGuard() { *counter -= 1; }

    int *counter;
};

/* Over-aligned, which is what makes the frame need realigning. */
struct __declspec(align(16)) ProbeEhAligned
{
    unsigned __int64 lanes[4];
};

__declspec(noinline) void probe_msvcrt_eh_raise(int selector)
{
    if (selector) {
        throw selector;
    }
}

__declspec(dllexport) int probe_msvcrt_eh_frames(int selector)
{
    int counter = 0;
    ProbeEhGuard outer(&counter);

    try {
        ProbeEhGuard inner(&counter);
        probe_msvcrt_eh_raise(selector);
    } catch (int caught) {
        counter += caught;
    }
    return counter;
}

__declspec(dllexport) int probe_msvcrt_eh_aligned(int selector,
                                                  unsigned __int64 seed)
{
    int counter = 0;
    ProbeEhAligned aligned;
    ProbeEhGuard outer(&counter);
    int index;

    for (index = 0; index < 4; ++index) {
        aligned.lanes[index] = seed + (unsigned __int64)index;
    }
    try {
        ProbeEhGuard inner(&counter);
        probe_msvcrt_eh_raise(selector);
    } catch (int caught) {
        counter += caught;
    }
    return counter + (int)aligned.lanes[0];
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""


def _msvc_probes(toolchain):
    """The MSVC-only half of the baseline.

    Two things make it bigger than the MinGW side rather than smaller. ATL
    and the MSVC STL have no GCC equivalent, and MSVC ships its C runtime in
    two flavours: /MT links it statically, /MD leaves it in ucrtbase.dll and
    vcruntime140.dll with a one-instruction import thunk in its place. Both
    MSVC recipes here build /MD, so every probe registered below that is
    meant to match them says so.

    The /MT probes are kept as well, not replaced. They are what currently
    filters _DllMainCRTStartup, __security_init_cookie, __GSHandlerCheck,
    __report_gsfailure and about a hundred more out of VX-API and BlackBone,
    and that is measured from the committed reports - dropping them to
    "fix" the flavour mismatch would trade a known win for an unknown one.
    """
    probes = [
        (toolchain.cxx, "probe_atl.cpp", _PROBE_ATL, ["-shared"]),
        # The same four sources again against the DLL runtime. No new code,
        # and it is where most of the surviving CRT residue lives.
        (toolchain.cc, "probe_md.c", _PROBE_DLL, ["-shared", "/MD"]),
        (toolchain.cxx, "probe_md.cpp", _PROBE_CXX, ["-shared", "/MD", "/EHsc"]),
        (toolchain.cc, "probe_md_exe.c", _PROBE_EXE, ["/MD"]),
        (toolchain.cxx, "probe_md_exe.cpp", _PROBE_CXX_EXE, ["/MD", "/EHsc"]),
        (toolchain.cxx, "probe_atl_md.cpp", _PROBE_ATL,
         ["-shared", "/MD", "/EHsc"]),
        (toolchain.cc, "probe_msvcrt.c", _PROBE_MSVCRT, ["-shared", "/MD"]),
        (toolchain.cxx, "probe_atl_com.cpp", _PROBE_ATL_COM,
         ["-shared", "/MD", "/EHsc", "ole32.lib", "oleaut32.lib"]),
        (toolchain.cxx, "probe_atl_throw.cpp", _PROBE_ATL_THROW,
         ["-shared", "/MD", "/EHsc"]),
        (toolchain.cxx, "probe_atl_modules.cpp", _PROBE_ATL_MODULES,
         ["-shared", "/MD", "/EHsc"]),
        (toolchain.cxx, "probe_atl_metahost.cpp", _PROBE_ATL_METAHOST,
         ["-shared", "/MD", "/EHsc"]),
        (toolchain.cc, "probe_msvcrt_wide.c", _PROBE_MSVCRT_WIDE,
         ["-shared", "/MD"]),
        # Third round. All three are /MD because every family the leaked
        # names turned up in is /MD, and because sprintf's body only exists
        # at all in a /MD image - under /MT the UCRT's inline definitions
        # sit beside a statically linked copy rather than an import.
        (toolchain.cc, "probe_msvcrt_helpers.c", _PROBE_MSVCRT_HELPERS,
         ["-shared", "/MD"]),
        (toolchain.cc, "probe_msvcrt_printf.c", _PROBE_MSVCRT_PRINTF,
         ["-shared", "/MD"]),
        (toolchain.cc, "probe_msvcrt_printf_wide.c", _PROBE_MSVCRT_PRINTF_WIDE,
         ["-shared", "/MD"]),
        # /O1 and /GS- are 7-Zip's own settings, and 7-Zip is the only family
        # here that carries __EH_prolog. The second registration drops /GS-
        # so that whichever of the two frame models cl picks, one of the runs
        # measures it; /O1 overrides the /O2 in probe_command, which cl warns
        # about (D9025) and accepts.
        (toolchain.cxx, "probe_msvcrt_eh.cpp", _PROBE_MSVCRT_EH,
         ["-shared", "/MD", "/EHsc", "/O1", "/GS-"]),
        (toolchain.cxx, "probe_msvcrt_eh_gs.cpp", _PROBE_MSVCRT_EH,
         ["-shared", "/MD", "/EHsc", "/O1"]),
    ]
    # Fourth round, and the same source as probe_msvcrt_helpers.c compiled a
    # second way, because round three's conversions still reached the *3 set.
    #
    # The analysis above this probe is right and stands: the *2 set takes its
    # argument on the x87 stack, which is where a __cdecl function returning
    # a double leaves it, and that is what the surviving callers do. What it
    # did not account for is that cl is free to get the value off the x87
    # stack again before converting - at /O2 with the default /arch:SSE2 it
    # spills the return value to memory and reloads it into XMM, so the
    # conversion reaches _ftoul3 after all. /arch:IA32 removes that escape
    # route: with no XMM to reload into, the conversion has to go through the
    # x87 helpers.
    #
    # So the source is right and only the flag was missing. The body that
    # ends up in the image is the CRT's either way - these are library
    # functions, not generated code - so this costs nothing and changes
    # nothing else. It is a second registration rather than a rewrite for
    # that reason.
    #
    # x86 only: /arch:IA32 is not a valid x64 option, the x64 CRT has no *2
    # set at all, and no _fto* name of any kind appears in any x64 MSVC
    # report. Since a probe that will not build now fails the run,
    # registering this on x64 would fail every x64 run.
    if toolchain.arch == "x86":
        probes.append(
            (toolchain.cc, "probe_msvcrt_helpers_x87.c", _PROBE_MSVCRT_HELPERS,
             ["-shared", "/MD", "/arch:IA32"]))
    # Which templates the STL headers instantiate depends on the language
    # version, and the two recipes disagree: vxapi.py builds /std:c++20 and
    # BlackBone's own Release(DLL) project asks for /std:c++latest. Both are
    # measured and unioned rather than one being guessed at.
    parts = (("seq", _PROBE_STL_SEQ),
             ("assoc", _PROBE_STL_ASSOC),
             ("func", _PROBE_STL_FUNC),
             ("grow", _PROBE_STL_GROW),
             ("hash", _PROBE_STL_HASH),
             ("tree", _PROBE_STL_TREE),
             ("throw", _PROBE_STL_THROW),
             ("array", _PROBE_STL_ARRAY),
             ("string", _PROBE_STL_STRING))
    for standard, suffix in (("/std:c++20", "20"), ("/std:c++latest", "latest")):
        for part, code in parts:
            probes.append((toolchain.cxx,
                           "probe_stl_%s_%s.cpp" % (part, suffix), code,
                           ["-shared", "/MD", "/EHsc", standard]))
    # And once more under /GL, which BlackBone's Release(DLL) uses and this
    # probe otherwise does not. Whether it matters is an open question: 163
    # functions were filtered out of BlackBone x64 with a probe built without
    # it, so /GL plainly does not make matching impossible, but the bodies
    # still in the residue are the *large* ones, which are exactly where a
    # different inlining decision would show. Measuring costs seven more
    # compilations and cannot lose anything - crt_glue maps a name to a set
    # of PicHashes, so a second flavour only ever adds members to that set.
    #
    # /std:c++latest only, because /GL is BlackBone's setting and BlackBone
    # is the /std:c++latest recipe; VX-API is /std:c++20 and has no /GL.
    # /LTCG is not passed: cl hands it to the linker itself for /GL objects,
    # and it is a linker flag that would be spliced in front of /link here.
    for part, code in parts:
        probes.append((toolchain.cxx,
                       "probe_stl_%s_gl.cpp" % part, code,
                       ["-shared", "/MD", "/EHsc", "/std:c++latest", "/GL"]))
    return probes


# {toolchain_id: [probe filename, ...]} for probes that did not build, filled
# in by crt_glue and read by probe_failures below. A dict rather than a return
# value because crt_glue is lru_cached: the second caller gets the memoised
# glue set and would otherwise see no failures at all.
_PROBE_FAILURES = {}


def probe_failures():
    """Probes that did not build, per toolchain, for baselines measured here.

    Empty until something has asked for a baseline, and empty afterwards if
    every probe built. build_corpus.py reports this at the end of a run and
    fails on it.

    That it fails the run is the point. A probe that will not build is not
    fatal to the family being built - it costs precision in the glue filter
    and nothing else, so it must not take a recipe down with it - but the
    artefacts it produces are then filtered against a smaller baseline than
    the one the corpus is supposed to have, and are indistinguishable from
    correct ones afterwards. That has happened twice on this branch: the MSVC
    side once ran with no filter at all, and adding an _mktime32 call to a
    probe that then failed to build took the x64 baseline from 2893 symbols
    to 2812 with nothing but a warning in a fifty-thousand-line log to say
    so. A warning is what a person misses; a non-zero exit is not.
    """
    return {toolchain: list(names)
            for toolchain, names in sorted(_PROBE_FAILURES.items()) if names}


@functools.lru_cache(maxsize=None)
def crt_glue(toolchain_id):
    """Map symbol name -> set of PicHashes, measured from a project-free DLL."""
    from .smdaify import disassemble

    toolchain = get_toolchain(toolchain_id)
    # EXE and DLL startup are entirely different object sets in MinGW
    # (crt1.o/crtexe.c versus dllcrt1.o/crtdll.c), so a DLL-only baseline
    # misses every mainCRTStartup-side function and leaves ~21 runtime
    # functions in each EXE artefact. All four are measured and unioned.
    probes = [
        (toolchain.cc, "probe.c", _PROBE_DLL, ["-shared"]),
        (toolchain.cxx, "probe.cpp", _PROBE_CXX,
         ["-shared", "-static-libstdc++", "-static-libgcc"]),
        (toolchain.cc, "probe_exe.c", _PROBE_EXE, []),
        (toolchain.cxx, "probe_exe.cpp", _PROBE_CXX_EXE,
         ["-static-libstdc++", "-static-libgcc"]),
    ]
    if toolchain.kind == "msvc":
        probes += _msvc_probes(toolchain)
    glue = {}
    # Set before the loop, so that a toolchain whose probes all built is
    # recorded as measured-and-clean rather than as never measured.
    _PROBE_FAILURES.setdefault(toolchain_id, [])
    with tempfile.TemporaryDirectory() as tmp:
        for compiler, filename, code, extra in probes:
            source = os.path.join(tmp, filename)
            target = os.path.join(tmp, filename + ".out.exe")
            with open(source, "w") as handle:
                handle.write(code)
            shared = "-shared" in extra
            command = toolchain.probe_command(compiler, source, target, shared)
            if toolchain.kind == "msvc":
                # cl's own options and any extra .lib have to go in front of
                # the /link separator; everything after it belongs to the
                # linker, which would reject /MD and /std:c++20 outright.
                cl_arguments = [flag for flag in extra
                                if flag.startswith("/") or flag.endswith(".lib")]
                if cl_arguments and "/link" in command:
                    split = command.index("/link")
                    command[split:split] = cl_arguments
                else:
                    command += cl_arguments
            else:
                command += [flag for flag in extra if flag != "-shared"]
            built = subprocess.run(command, capture_output=True, cwd=tmp,
                                   text=True, errors="replace")
            if built.returncode != 0:
                # A probe is a measurement, not a deliverable. One that will
                # not build costs precision in the glue filter for this
                # toolchain and nothing else, so it must not take a family's
                # build down with it - but it must be loud, because a quietly
                # missing probe is how the MSVC side ended up with no filter
                # at all.
                LOGGER.warning(
                    "%s: the %s baseline probe did not build, so whatever it "
                    "would have measured stays in this toolchain's artefacts."
                    "\n%s", toolchain_id, filename,
                    (built.stderr or built.stdout or "").strip()[-2000:])
                _PROBE_FAILURES.setdefault(toolchain_id, []).append(filename)
                continue
            probe = disassemble(target, pdb_path=toolchain.probe_pdb(target))
            for function in probe.getFunctions():
                if not function.function_name:
                    continue
                glue.setdefault(function.function_name, set()).add(function.pic_hash)
    # The probe's own function is the one thing here that is not runtime code.
    #
    # The names the four shared probes contribute are still listed one by one
    # rather than matched by prefix, because the MinGW baseline is a measured
    # constant this branch is not allowed to move and a prefix rule does move
    # it: GCC emits `probe_vscprintf.constprop.0`, `probe_cxx_runtime(char
    # const*)` and a `.cold` partition of the same, none of which this list
    # catches, so three x86 and two x64 entries in the MinGW glue set are in
    # fact the probe's own code. Harmless - no library has a function called
    # `probe_cxx_runtime(char const*)` - but worth a separate decision rather
    # than being smuggled in with an MSVC change.
    for name in ("_probe_runtime", "probe_runtime", "_compare", "compare",
                 "_probe_vscprintf", "probe_vscprintf",
                 "_probe_cxx_runtime", "probe_cxx_runtime", "_main", "main",
                 "_probe_atl", "probe_atl"):
        glue.pop(name, None)
    # The MSVC-only probes below are matched by prefix instead. They have
    # helpers and classes of their own, and a hand-kept list is exactly the
    # kind that acquires a gap - the one name that is forgotten becomes a
    # function this repository starts deleting out of somebody's library.
    # None of these prefixes can reach a MinGW baseline: the sources that
    # define them are only ever compiled by cl.
    for name in [name for name in glue
                 if name.startswith(("probe_atl_", "_probe_atl_",
                                     "probe_msvcrt_", "_probe_msvcrt_",
                                     "probe_stl_", "_probe_stl_",
                                     "ProbeInterface", "ProbeImplementation",
                                     "ProbeArray", "ProbeEh"))]:
        glue.pop(name, None)
    return glue


def is_glue(function, toolchain_id):
    glue = crt_glue(toolchain_id)
    if not function.function_name:
        return False
    return function.pic_hash in glue.get(function.function_name, ())
