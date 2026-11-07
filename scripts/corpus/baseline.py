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

The Linux side is by far the smallest of the three, and measurably so: 28
symbols on x64 and 37 on x86, against 2893 for MinGW x64. A ``-shared`` ELF
object links glibc, libstdc++ and libm dynamically, so none of their bodies
are in the image at all - every call to them is a ``.plt`` stub, which
carries no symbol and is not what this filter is for. What is left is of two
kinds, and the measured split is the argument for building ``.so`` artefacts
on this side rather than static executables:

* The objects ld links in regardless, 7 of them on x64 and 18 on x86:
  crti/crtn's _init and _fini, Scrt1.o's _start, crtbeginS's
  register_tm_clones, deregister_tm_clones, __do_global_dtors_aux and
  frame_dummy, and on x86 __stack_chk_fail_local, the four
  __x86.get_pc_thunk.* PIC helpers, and libgcc.a's 64-bit division set -
  __divdi3, __moddi3, __divmoddi4, __udivdi3, __umoddi3, __udivmoddi4. That
  last one is why the division block from _PROBE_DLL is carried over into
  _PROBE_LINUX_C: libgcc is the one static archive still in play here, and
  those six were found leaking across four families on the Windows side.
* libstdc++ templates the headers instantiate into whatever uses them, 21 on
  x64 and 19 on x86. Those are in the image because they are compiled from
  the probe's own translation unit, exactly as they are on the MinGW side.

Nothing of glibc itself is in either list, which answers the question a
glibc probe set would have been for: there is no glibc body in a dynamically
linked .so to measure or to remove.
"""

import functools
import logging
import os
import re
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

# MinGW only, and the character-at-a-time half of stdio that _PROBE_DLL never
# touches. That probe formats, seeks and reads blocks; it never calls printf,
# puts, fgetc, fputc, feof, rewind or atoi, so none of those were in the
# baseline and all of them were being filed under whichever family linked
# them. It is measurable in the committed data: q3vm's MinGW x64 report is 20
# functions of which printf, puts and rewind are msvcrt import thunks wearing
# the q3vm family name, and 4g3nt47/Obfuscator - seven functions of its own -
# came out at 28 on x64 with feof, fgetc, printf twice, rewind and atoi among
# them.
#
# Two things about the printf family in particular, both measured rather than
# assumed, because they are what an obvious version of this probe gets wrong:
#
#   * The format has to be one the optimiser cannot see. mingw-w64's stdio.h
#     defines printf as a static inline wrapper around __mingw_vfprintf, and
#     given a literal format GCC clones it as printf.constprop.0 - so the
#     name the artefacts carry, plain "printf", is never in the probe image
#     at all. The first draft of this probe did exactly that and removed
#     nothing. Reading the format out of a volatile pointer defeats the clone
#     and is the same trick the math block above uses against builtins.
#   * The wrapper is compiled from the probe's own translation unit, so its
#     body is whatever the optimiser makes of it, and the PicHash follows:
#     on x64 the same wrapper is 25 instructions at -O0, 19 at -O1, 19 with a
#     different hash at -O2 and 18 at -Os, four distinct PicHashes for one
#     name. probe_command builds at -O2, which matches every recipe here
#     except Obfuscator's -O0, so this source is registered a second time at
#     -O0 below. That second registration is narrow and was measured: it adds
#     a second PicHash for exactly the mingw-w64 header wrappers - printf,
#     fprintf, sprintf, snprintf, vprintf, vfprintf, vsprintf, vsnprintf,
#     fscanf, strtof - and for nothing else, because everything else in the
#     image comes out of the prebuilt CRT archives rather than out of this
#     translation unit.
#
# One source rather than lines added to _PROBE_DLL, on the standing rule in
# this file: that probe already works, and a probe that fails to build does
# not fail the family being built - it silently shrinks the baseline.
_PROBE_STDIO = """\
/* winsock2.h before windows.h, or windows.h pulls in winsock.h and the two
   headers redeclare the same structures. ws2tcpip.h is here for
   gai_strerrorA and gai_strerrorW only, which mingw-w64 defines as static
   __inline wrappers over FormatMessage: they are compiled into every
   translation unit that calls them, so any library resolving a getaddrinfo
   error carries a body for them under its own name. OpenSSL, libevent and
   boringssl all did. No -lws2_32 is needed, because nothing here calls a
   function that is actually in the import library. */
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <ctype.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

/* Read through a volatile pointer so the format is not a constant the
   optimiser can specialise the wrapper on. See the note above. */
static volatile const char *probe_stdio_format = "%s %d %s";

static int probe_stdio_forward(const char *format, ...)
{
    char buffer[256];
    va_list arguments;
    int written;

    va_start(arguments, format);
    written = vprintf(format, arguments);
    va_end(arguments);
    va_start(arguments, format);
    written += vfprintf(stderr, format, arguments);
    va_end(arguments);
    va_start(arguments, format);
    written += vsnprintf(buffer, sizeof(buffer), format, arguments);
    va_end(arguments);
    va_start(arguments, format);
    written += vsprintf(buffer, format, arguments);
    va_end(arguments);
    return written;
}

__declspec(dllexport) int probe_stdio_streams(const char *path, const char *text)
{
    const char *format = (const char *)probe_stdio_format;
    char buffer[256];
    FILE *stream;
    int c = EOF;
    long where;

    printf(format, text, 1, text);
    fprintf(stderr, format, text, 1, text);
    sprintf(buffer, format, text, 1, text);
    snprintf(buffer, sizeof(buffer), format, text, 1, text);
    probe_stdio_forward(format, text, 1, text);
    puts(text);
    putchar('x');
    fputs(text, stderr);
    fflush(stderr);
    perror(text);

    stream = fopen(path, "rb");
    if (stream) {
        setvbuf(stream, NULL, _IOFBF, 4096);
        /* feof/fgetc in the shape a file walker writes them, which is what
           Obfuscator's obfs_read_until_null does. */
        while (!feof(stream)) {
            c = fgetc(stream);
            if (c == EOF)
                break;
        }
        getc(stream);
        ungetc(c, stream);
        fgets(buffer, sizeof(buffer), stream);
        fscanf(stream, "%255s", buffer);
        fread(buffer, 1, 1, stream);
        fseek(stream, 0, SEEK_SET);
        ferror(stream);
        clearerr(stream);
        rewind(stream);
        where = ftell(stream);
        fclose(stream);
        (void)where;
    }
    stream = fopen(path, "wb");
    if (stream) {
        fputc('y', stream);
        putc('z', stream);
        fwrite(text, 1, strlen(text), stream);
        fclose(stream);
    }
    remove(path);
    return c;
}

__declspec(dllexport) int probe_stdio_convert(const char *text)
{
    int total = 0;
    size_t index;

    total += atoi(text);
    total += (int)atol(text);
    total += (int)atoll(text);
    total += (int)atof(text);
    total += (int)strtoul(text, NULL, 10);
    total += (int)strtoull(text, NULL, 16);
    total += (int)strtof(text, NULL);
    total += abs(total);
    for (index = 0; index < strlen(text); index++) {
        total += toupper((unsigned char)text[index]);
        total += tolower((unsigned char)text[index]);
        total += isalpha((unsigned char)text[index]);
        total += isdigit((unsigned char)text[index]);
        total += isspace((unsigned char)text[index]);
        total += isupper((unsigned char)text[index]);
        total += islower((unsigned char)text[index]);
        total += isalnum((unsigned char)text[index]);
        total += isprint((unsigned char)text[index]);
        total += ispunct((unsigned char)text[index]);
        total += isxdigit((unsigned char)text[index]);
    }
    return total;
}

__declspec(dllexport) size_t probe_stdio_strings(char *destination,
                                                 const char *text)
{
    char *copy = strdup(text);

    strncat(destination, text, 8);
    strrchr(destination, 'x');
    strcspn(destination, text);
    strspn(destination, text);
    strpbrk(destination, text);
    strtok(destination, text);
    strncmp(destination, text, 4);
    memcmp(destination, text, 4);
    memchr(destination, 'x', 4);
    strerror(0);
    if (copy)
        free(copy);
    return strlen(destination);
}

/* Read through a volatile so the error code is not a constant the optimiser
   could fold the wrapper on, the same reason probe_stdio_format is volatile. */
static volatile int probe_stdio_gai_error = WSAHOST_NOT_FOUND;

__declspec(dllexport) size_t probe_stdio_gai(void)
{
    const char *narrow = gai_strerrorA(probe_stdio_gai_error);
    const wchar_t *wide = gai_strerrorW(probe_stdio_gai_error);

    return strlen(narrow) + wcslen(wide);
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

# The EXE variant, for the same reason _PROBE_EXE exists beside _PROBE_DLL:
# the two startup paths are different object sets, and the families that wear
# this residue - q3vm, Obfuscator - are executables.
_PROBE_STDIO_EXE = _PROBE_STDIO.replace(
    "BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }",
    "int main(int argc, char **argv)\n"
    "{\n"
    "    /* A scratch path rather than argv[0]: nothing runs a probe, but a\n"
    "       probe that would truncate and delete its own image if anyone did\n"
    "       is not worth the five characters it saves. */\n"
    "    char buffer[256] = \"probe\";\n"
    "    return probe_stdio_streams(\"probe_stdio.tmp\", argv[argc - 1])\n"
    "           + probe_stdio_convert(argv[0])\n"
    "           + (int)probe_stdio_strings(buffer, argv[0]);\n"
    "}")

# MinGW only: libmingwex and msvcrt entry points that neither probe above
# reaches, each found wearing a library's family name in committed data or in
# a family waiting to be published.
#
#   * stat() is not an msvcrt import on mingw-w64. The CRT wraps it (and
#     _wstat64i32 on x64, _stat on x86) with a path fix-up in front of the
#     real call, and the wrapper is 145-167 instructions: protobuf, libxml2
#     and miniz all carried it. The 64-bit-time variants and _stat32 (x86
#     only; there is no such import on x64, and a probe that fails to link
#     measures nothing) are plain import thunks, measured for completeness.
#   * gettimeofday is libmingwex's mingw_gettimeofday under a second name,
#     and drags in getntptimeofday. libevent, the x86 libstdc++ sample and
#     Jansson all carry the pair.
#   * cbrt and log2 are libmingwex bodies like the floor and sin of
#     _PROBE_DLL, and are reached through a volatile pointer for the reason
#     given there: GCC knows both as builtins. Duktape and abseil carry them.
#   * setjmp is a macro over msvcrt's _setjmp (x64) or _setjmp3 (x86); only
#     the import thunk is in the image. Lua, libpng and cryptopp carry it.
#
# Nothing here is compiled from this translation unit, so the bodies do not
# depend on the optimisation level and one -O2 build measures them. A separate
# source on the standing rule in this file: the probes above already work.
_PROBE_LIBC = """\
#include <windows.h>
#include <math.h>
#include <setjmp.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <wchar.h>

static jmp_buf probe_libc_jump;

__declspec(dllexport) int probe_libc_files(const char *path, const wchar_t *wide)
{
    struct stat plain;
    struct _stat64i32 mixed;
    struct _stat64 wide64;
    int total = 0;

    total += stat(path, &plain);
    total += _stat64i32(path, &mixed);
    total += _wstat64i32(wide, &mixed);
    total += _stat64(path, &wide64);
    total += _wstat64(wide, &wide64);
#ifndef _WIN64
    {
        struct _stat32 narrow;
        total += _stat32(path, &narrow);
    }
#endif
    return total;
}

__declspec(dllexport) int probe_libc_misc(double value)
{
    volatile double (*const dd[])(double) = {cbrt, log2};
    struct timeval now;
    double accumulated = 0.0;
    size_t index;

    for (index = 0; index < sizeof(dd) / sizeof(dd[0]); index++)
        accumulated += dd[index](value);
    if (gettimeofday(&now, NULL) != 0)
        return -1;
    if (setjmp(probe_libc_jump))
        return 1;
    return (int)accumulated + (int)now.tv_usec;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

# MinGW only, and the header wrappers _PROBE_STDIO cannot produce because of
# how it calls them. snprintf, sprintf and sscanf are static inline in
# mingw-w64's stdio.h, so their body is compiled in whatever translation unit
# calls them and GCC shapes it by the call sites it can see:
#
#   * every call passing the same constant argument gives a clone,
#     sprintf.constprop.0, with that argument folded in;
#   * any call passing a value it cannot see gives the plain body, sprintf.
#
# One translation unit gets one or the other per function, never both, and
# _PROBE_DLL and _PROBE_STDIO between them only ever produced the clone for
# snprintf and sscanf and only the plain body for sprintf. That is why plain
# snprintf sat in 26 libuv, libxml2 and libzlib artefacts, sscanf in OpenSSL
# and libxml2, and sprintf.constprop.0 in Lua, LuaJIT, OpenSSL, libcurl and
# libtiff. So this source is registered twice, with and without
# PROBE_STDIO_FMT_CONSTANT.
#
# And twice more at -Os, because the wrapper's shape follows the optimisation
# level as _PROBE_STDIO's note says, and Duktape builds at upstream's -Os: on
# x86 its snprintf, sprintf and sscanf.constprop.0 match none of the -O2
# bodies. -O3, which every CMake Release recipe here actually compiles at, was
# measured as well and gives the -O2 bodies exactly, so it is not registered.
#
# And once with __USE_MINGW_ANSI_STDIO=0, which is what a library gets when it
# asks for msvcrt's own printf: sprintf and sscanf are then not wrappers but
# msvcrt imports, and only their one-instruction thunks are in the image -
# OpenSSL, cJSON, libuv and libxml2 carry them. snprintf stays a wrapper in
# that mode, over _vsnprintf, and comes out with the same PicHash as the -O2
# build, so that registration adds only the thunks.
#
# The clone is per call site, not per function: snprintf.constprop.0 has a
# dozen distinct bodies in the committed data, one for each combination of
# arguments a library happens to fold. Only the one with constant size and
# format is reproduced here - it is what libtiff carries - and the rest stay
# where they are; a probe cannot guess a library's call sites.
_PROBE_STDIO_FMT = """\
#include <windows.h>
#include <stdio.h>
#include <string.h>

#ifdef PROBE_STDIO_FMT_CONSTANT
__declspec(dllexport) int probe_stdio_fmt(char *destination, const char *text,
                                          int number)
{
    char scanned[64];
    int total = 0;

    total += snprintf(destination, 32, "%d", number);
    total += sprintf(destination, "%d", number);
    total += sscanf(text, "%63s", scanned);
    return total;
}
#else
/* Volatile for the reason probe_stdio_format is: a size or format the
   optimiser can see is one it will fold into a clone. */
static volatile const char *probe_stdio_fmt_format = "%s %d";
static volatile size_t probe_stdio_fmt_size = 64;

__declspec(dllexport) int probe_stdio_fmt(char *destination, const char *text,
                                          int number)
{
    const char *format = (const char *)probe_stdio_fmt_format;
    char scanned[64];
    int total = 0;

    total += snprintf(destination, probe_stdio_fmt_size, format, text, number);
    total += sprintf(destination, format, text, number);
    total += sscanf(text, format, scanned, &number);
    return total;
}
#endif

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

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


# Linux only, and a separate source rather than an #ifdef over _PROBE_DLL.
# That probe is half MSVCRT: _vscprintf, _strtoi64, gmtime_s, _gmtime32_s,
# _localtime64_s, _get_errno, __time32_t and DllMain have no glibc spelling,
# and windows.h has no glibc header. Threading an #ifdef through it would put
# the two baselines that matter most - MinGW's, which this branch may not
# move, and MSVC's - one editing mistake away from changing.
#
# What it has to cover is narrower than the Windows probes, because the C
# runtime is not in the image: glibc, libm and libstdc++ are all shared
# objects here, so every call to them is a .plt stub with no body to match.
# The calls below are still made, for the same reason the MinGW probe makes
# them - a helper the compiler emits inline, or pulls out of a static
# archive, only appears if something asks for it - and there is exactly one
# static archive on this side.
#
# That archive is libgcc.a. The 64-bit division block is therefore carried
# over from _PROBE_DLL unchanged in substance: __divdi3, __moddi3,
# __udivmoddi4 and __umoddi3 are library calls rather than instructions on a
# 32-bit target, they are linked into whatever needs them, and on the Windows
# side they were found sitting in 7-Zip, Lua, OpenSSL and libstdc++ at once
# before the block was added. Nothing about that changes with the container.
_PROBE_LINUX_C = """\
#include <errno.h>
#include <locale.h>
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <wchar.h>

#define PROBE_EXPORT __attribute__((visibility("default")))

static int probe_linux_compare(const void *a, const void *b)
{
    return *(const int *)a - *(const int *)b;
}

static int probe_linux_vprintf(const char *format, ...)
{
    char buffer[256];
    va_list arguments;
    int written;
    va_start(arguments, format);
    written = vsnprintf(buffer, sizeof(buffer), format, arguments);
    va_end(arguments);
    return written;
}

PROBE_EXPORT void probe_linux_runtime(const char *text, double value)
{
    char buffer[256];
    wchar_t wide[64];
    int numbers[4] = {4, 2, 3, 1};
    FILE *stream;
    void *block;
    time_t now;

    snprintf(buffer, sizeof(buffer), "%s %f %e %g %d %x %p", text, value,
             value, value, 1, 2, (const void *)text);
    sscanf(buffer, "%255s", buffer);
    swprintf(wide, 64, L"%s %f", L"w", value);
    strtod(buffer, NULL);
    strtol(buffer, NULL, 10);
    strtoll(buffer, NULL, 16);
    qsort(numbers, 4, sizeof(int), probe_linux_compare);
    bsearch(numbers, numbers, 4, sizeof(int), probe_linux_compare);
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
    stream = fopen("/dev/null", "rb");
    if (stream) {
        fread(buffer, 1, 1, stream);
        fseek(stream, 0, SEEK_SET);
        ftell(stream);
        fclose(stream);
    }
    fprintf(stderr, "%s", buffer);
    abs((int)value);
    labs((long)value);
    ldiv((long)value, 2);
    /* libgcc.a, statically linked even here: 64-bit division on a 32-bit
       target is a call rather than an instruction. Both shapes are needed -
       a quotient and a remainder over one divisor fold into a single
       __divmoddi4/__udivmoddi4, over different divisors they stay as
       __divdi3, __moddi3, __udivdi3 and __umoddi3 - which is exactly the
       reasoning recorded on the MinGW probe, and the reason this block is
       the same block. */
    {
        long long signed_wide = (long long)value * 1000003LL + 7;
        unsigned long long unsigned_wide = (unsigned long long)signed_wide | 1ULL;
        long long sdiv = (long long)(unsigned_wide | 3);
        unsigned long long udiv = (unsigned long long)(signed_wide | 9);
        volatile long long sink64;

        sink64 = signed_wide / sdiv;
        sink64 += signed_wide % sdiv;
        sink64 += (long long)(unsigned_wide / udiv);
        sink64 += (long long)(unsigned_wide % udiv);
        sink64 += signed_wide / (long long)(unsigned_wide | 5);
        sink64 += signed_wide % (long long)(unsigned_wide | 7);
        sink64 += (long long)(unsigned_wide / (unsigned long long)(signed_wide | 11));
        sink64 += (long long)(unsigned_wide % (unsigned long long)(signed_wide | 13));
        (void)sink64;
    }
    /* Taking the address defeats the builtin, for the reason recorded on the
       MinGW probe: GCC folds sin() on a known value or emits an SSE
       instruction, and the library body is never referenced. Here the body
       lives in libm.so.6 and cannot be in the image either way, so what this
       costs is one PLT stub each - kept so the two C probes stay the same
       measurement asked of two runtimes rather than two different ones. */
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
    {
        struct tm parts;
        gmtime_r(&now, &parts);
        localtime_r(&now, &parts);
        gmtime(&now);
        mktime(&parts);
        difftime(now, now);
    }
    probe_linux_vprintf("%s %f %d", text, value, 1);
    errno = 0;
}
"""

# The executable variant. On Linux the split is smaller than MinGW's
# crt1.o/dllcrt1.o one - crtbeginS.o and crtbegin.o carry the same four
# functions - but _start comes from Scrt1.o and only an executable has it,
# so both are measured and unioned exactly as on the Windows side.
_PROBE_LINUX_C_EXE = _PROBE_LINUX_C + """
int main(int argc, char **argv)
{
    probe_linux_runtime(argv[0], (double)argc);
    return 0;
}
"""

# Anything linked with g++ brings in the unwinder's registration glue. The
# libstdc++ bodies themselves are in libstdc++.so.6 and cannot reach an
# artefact here, which is the whole reason the C++ recipes on this side do
# not need -static-libstdc++ and its thirteen thousand functions.
_PROBE_LINUX_CXX = """\
#include <algorithm>
#include <exception>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#define PROBE_EXPORT __attribute__((visibility("default")))

PROBE_EXPORT void probe_linux_cxx_runtime(const char *text)
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

_PROBE_LINUX_CXX_EXE = _PROBE_LINUX_CXX + """
int main(int argc, char **argv)
{
    probe_linux_cxx_runtime(argv[0]);
    return argc - argc;
}
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

# MSVC only. The half of <stdio.h> that writes to a stream it was not handed:
# printf, vprintf and vfprintf. _PROBE_MSVCRT_PRINTF above covers the
# buffer-filling half and _PROBE_DLL calls fprintf, so the chain below
# _vfprintf_l is already measured; what was never emitted by any MSVC probe is
# the wrapper that reaches stdout, which is the one a program actually calls.
#
# It is the same mechanism _PROBE_MSVCRT_PRINTF records - under /MD these are
# _CRT_STDIO_INLINE definitions in the UCRT header, so a body is compiled into
# every object that uses one and the /DEBUG link keeps it - and it is the
# largest single misattribution left on the MSVC side of this corpus. Measured
# in the committed reports, before this probe: printf carries one body of 25
# instructions on x64 under LuaJIT, MemoryModule, mbedTLS and q3vm, and one of
# 17 on x86 under LuaJIT, MemoryModule and mbedTLS, all four of them the same
# PicHash per architecture; vfprintf carries 19 instructions on x64 and 10 on
# x86 under LuaJIT and libtiff; vprintf carries 21 and 13 under LuaJIT.
#
# The cross-family check does not fail on those today, and the reason is worth
# writing down because it is not a reprieve: LuaJIT emits _printf_p and
# _wprintf_p as well, whose bodies hash to the same value as printf's, so the
# hash arrives at classify_collision carrying three names and is filed under
# "the names differ between families". One family dropping stdio would turn it
# into leakage. The names are Microsoft's either way.
#
# Measured on the runner, this probe emits exactly those bodies: printf at
# PicHash 121597203084696572 (25 instructions) on x64 and 14739679411554417350
# (17) on x86, vfprintf at 18319647447110778407 (19) and 15763949986211485148
# (10), vprintf at 3515039425838154103 (21) and 7807335352819369265 (13) -
# every one of them the hash the committed artefacts carry. Rebuilt, LuaJIT
# drops printf, vprintf and vfprintf, MemoryModule and q3vm drop printf, and
# fflush and fputs go with them as thunks.
#
# What it does not reach is the rest of the surface LuaJIT instantiates. Its
# images carry the whole UCRT inline set - printf_s, wprintf, wprintf_s,
# _printf_p and _wprintf_p share printf's body, and vfprintf_s, vfwprintf_s,
# vfscanf, vfwscanf, _vfprintf_p and _vfwprintf_p share vfprintf's - so those
# hashes stay in the cross-family census under LuaJIT's name until a probe
# calls them too. That is forty-odd names, half of them wide, and it is a
# measurement of its own rather than an addition to this one.
#
# Narrow only, and separate from the wide half for the reason
# _PROBE_MSVCRT_PRINTF gives: a wrong guess about vswprintf's two UCRT
# declarations must not cost printf. puts and fputs are in here as well
# because they sit beside printf in every program that prints and cost
# nothing; they are imports under /MD rather than inline bodies, so what they
# contribute is their thunks.
_PROBE_MSVCRT_STDIO = """\
#define _CRT_SECURE_NO_WARNINGS 1
#include <windows.h>
#include <stdarg.h>
#include <stdio.h>

/* Read through a volatile pointer so no part of the format is a constant the
   optimiser can fold into the wrapper. */
static volatile const char *probe_msvcrt_stdio_format = "%s %d %s";

static int probe_msvcrt_stdio_forward(const char *format, ...)
{
    va_list arguments;
    int written;

    /* Real varargs, started once per callee: handing a callee a va_list that
       was never started is undefined behaviour, and a probe that relies on
       undefined behaviour is not a measurement. */
    va_start(arguments, format);
    written = vprintf(format, arguments);
    va_end(arguments);
    va_start(arguments, format);
    written += vfprintf(stderr, format, arguments);
    va_end(arguments);
    return written;
}

__declspec(dllexport) int probe_msvcrt_stdio_streams(const char *text)
{
    const char *format = (const char *)probe_msvcrt_stdio_format;
    int total = 0;

    total += printf(format, text, 1, text);
    total += fprintf(stderr, format, text, 1, text);
    total += probe_msvcrt_stdio_forward(format, text, 1, text);
    total += puts(text);
    total += fputs(text, stderr);
    total += fflush(stdout);
    return total;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }
"""

# The EXE registration of the same source, derived the way _PROBE_EXE is
# derived from _PROBE_DLL rather than registered as a second entry point: an
# EXE needs a main, and the first version of this round registered the DLL
# source as an EXE and got LNK1561 out of every run - which probe_failures
# reported and failed the run for, which is what it is for.
#
# It is coverage rather than a fix, and the measurement says so: the wrapper
# bodies are compiled from this translation unit, and probe_md.c and
# probe_md_exe.c give fprintf the same PicHash (13953233625706420610 on x64),
# so DLL and EXE do not differ for them. What the EXE adds is the startup set
# beside them.
_PROBE_MSVCRT_STDIO_EXE = _PROBE_MSVCRT_STDIO.replace(
    "BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) { return TRUE; }",
    "int main(int argc, char **argv)\n"
    "{\n"
    "    return probe_msvcrt_stdio_streams(argv[0]) + argc;\n"
    "}")

# The EXE form of the probe above, and the one thing in this file that is
# shaped by what it has to match rather than by what it has to call.
#
# __scrt_common_main_seh is the MSVC CRT's x64 entry-point wrapper, 99
# instructions, and it is the one leakage finding validate --deep fails on:
# the same body sits under Hidden, Lua, MemoryModule and bzip2, with a second
# of 98 in q3vm and a third of 109 in CallObfuscator, which is wmain's startup
# object rather than main's. Its neighbours are all removed already -
# __scrt_initialize_crt, __scrt_acquire_startup_lock, __scrt_fastfail and a
# dozen more - so what the existing probe_md_exe.c registration measures is
# the right object set, from the right CRT flavour, and still not this body.
#
# What the name does in the baseline turned out to be the useful question, and
# it was measured rather than guessed: probe_md_exe.c emits
# __scrt_common_main_seh at 95 instructions, PicHash 470324384558745095, which
# is none of the three bodies in the corpus. The name was in the baseline all
# along and only the body disagreed, so the filter - symbol *and* PicHash -
# correctly kept the artefacts' copies.
#
# The cause is the link line, and the probe above proves it by elimination: the
# same translation unit linked /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF emits
# 11855707620856894801 at 99 instructions, which is exactly the leaking body,
# while the incrementally linked registration beside it still emits 95. Every
# MSVC recipe here passes /INCREMENTAL:NO and no probe did: link /DEBUG implies
# /INCREMENTAL, and this file's own note on that flag records what it does to
# an image - every call leaves through a table of five-byte jump thunks.
# __scrt_common_main_seh is the only function in the startup chain carrying an
# __except, so it is also the only one whose recovered extent follows the
# layout rather than the bytes, which is why its neighbours matched and it did
# not. On x86 the two links agree, at 14520804967954049952 and 112
# instructions, and no x86 artefact carries the name - consistent with the
# funclet being an x64 shape.
#
# Two registrations rather than one, because two things differed and both are
# worth having measured:
#
#   * This source is a plain console main that prints, which is what Lua's,
#     bzip2's and MemoryModule's are. exe_main.obj's invoke_main() is inlined
#     into __scrt_common_main_seh and calls main there, so main is the one
#     caller this body has, and probe_md_exe.c's main calls a 200-line
#     exported function instead.
#   * probe_md_exe_noincr.c is probe_md_exe.c's source relinked, so the whole
#     broad EXE surface - 237 named functions on x64 against 351 from the
#     incremental link - is measured non-incrementally too.
#
# Neither can lose anything: crt_glue maps a name to a set of PicHashes, so a
# registration that measures the same body twice adds nothing and one that
# measures a second body adds a member.
#
# What stays is the 98-instruction body in q3vm, which builds /GL, and the
# 109-instruction one in CallObfuscator, which is wmain's startup object. Both
# are single-family and neither has ever been leakage.
_PROBE_MSVCRT_MAIN = """\
#define _CRT_SECURE_NO_WARNINGS 1
#include <windows.h>
#include <stdarg.h>
#include <stdio.h>

static volatile const char *probe_msvcrt_main_format = "%s %d";

static int probe_msvcrt_main_forward(const char *format, ...)
{
    va_list arguments;
    int written;

    va_start(arguments, format);
    written = vprintf(format, arguments);
    va_end(arguments);
    return written;
}

int main(int argc, char **argv)
{
    const char *format = (const char *)probe_msvcrt_main_format;

    return printf(format, argv[0], argc)
         + probe_msvcrt_main_forward(format, argv[0], argc);
}
"""


# MSVC only. The rest of the UCRT's inline stdio surface, wide and narrow.
#
# swprintf_s was the finding: PicHash 10336305819058912646, 28 instructions,
# under BlackBone, EDRSandblast and al-khaser, the one hash validate --deep
# still failed on after the sixth round. It was never a missing name.
# _PROBE_MSVCRT_WIDE has called swprintf_s since the third round, and measured
# on the runner it emits one at 28 instructions on x64 as well - PicHash
# 13530071051526633694. Same name, same length, another hash, which is the
# case the symbol-and-PicHash filter exists to keep. The same wrapper built
# with /sdl emits 10336305819058912646 exactly, and no other flavour does:
# BlackBone's x64 configuration is documented as /sdl, and the other two
# reproduce only with it. The filter was right to keep the artefacts' copies
# and the probe was the part that was wrong.
#
# Which flags decide a body was measured, not read off the recipes. Every
# flavour in _STDIO_PLAN is there because it reproduced a hash an artefact
# carries, and the flavours that did not were dropped from the plan:
#
#   * /sdl on x64 (swprintf_s above) and, on x86, /sdl with /Oy- for
#     al-khaser's /O2 swprintf_s (19 instructions).
#   * /Oy- on x86 only. Keeping the frame pointer adds push ebp / mov ebp,esp
#     / pop ebp to every x86 wrapper, and that is exactly the difference
#     between the 20-instruction printf and wprintf in DiskCryptor and
#     al-khaser and the 17 everything built with cl's defaults emits.
#     BlackBone's fprintf (14 against 11) agrees. x64 has no frame-pointer
#     option, so x64 has no /Oy- flavour.
#   * /Od, because al-khaser is built twice and its /Od image carries the
#     wrappers un-inlined at 22 instructions on x86 and 25 on x64 (/Od /sdl).
#   * /Gs0 on x64 and /O1 on x64, which are OpenSSL's and libzlib's, found by
#     trying them against the survivors that nothing else reproduced; and
#     /std:c++20 as C++, which is how VX-API and protobuf compile the same
#     printf and wprintf into 22 instructions on x64 instead of 25.
#
# The wrappers are taken by address rather than called, for the reason
# _PROBE_MSVCRT_WIDE's note gives for the narrow set, and the groups are
# separate translation units so a name a future SDK stops declaring takes
# down one group and probe_failures names which. Several of the groups exist
# because a callee arrives with its caller: the print groups carry
# _vfprintf_l, the scan groups carry _vfscanf_l, and one probe image holds
# every body in the chain.
#
# What this does not reproduce is recorded in scripts/corpus/README.md next
# to the numbers, not here.
_STDIO_TABLE_HEAD = """\
#define _CRT_SECURE_NO_WARNINGS 1
#include <windows.h>
#include <stdarg.h>
#include <stdio.h>
#include <time.h>
#include <wchar.h>

typedef void (*probe_symbol)(void);

"""

_STDIO_NARROW_PRINT = (
    "printf", "vprintf", "fprintf", "vfprintf",
    "_printf_l", "_vprintf_l", "_fprintf_l", "_vfprintf_l",
    "printf_s", "vprintf_s", "fprintf_s", "vfprintf_s",
    "_printf_s_l", "_vprintf_s_l", "_fprintf_s_l", "_vfprintf_s_l",
    "_printf_p", "_vprintf_p", "_fprintf_p", "_vfprintf_p",
    "_printf_p_l", "_vprintf_p_l", "_fprintf_p_l", "_vfprintf_p_l")
_STDIO_NARROW_STRING = (
    "sprintf", "vsprintf", "snprintf", "vsnprintf", "_snprintf", "_vsnprintf",
    "sprintf_s", "vsprintf_s", "_snprintf_s", "_vsnprintf_s",
    "_sprintf_l", "_vsprintf_l", "_snprintf_l", "_vsnprintf_l",
    "_sprintf_s_l", "_vsprintf_s_l", "_snprintf_s_l", "_vsnprintf_s_l",
    "_sprintf_p", "_vsprintf_p", "_sprintf_p_l", "_vsprintf_p_l",
    "_scprintf", "_vscprintf", "_scprintf_l", "_vscprintf_l",
    "_scprintf_p", "_vscprintf_p")
_STDIO_WIDE_PRINT = (
    "wprintf", "vwprintf", "fwprintf", "vfwprintf",
    "_wprintf_l", "_vwprintf_l", "_fwprintf_l", "_vfwprintf_l",
    "wprintf_s", "vwprintf_s", "fwprintf_s", "vfwprintf_s",
    "_wprintf_s_l", "_vwprintf_s_l", "_fwprintf_s_l", "_vfwprintf_s_l",
    "_wprintf_p", "_vwprintf_p", "_fwprintf_p", "_vfwprintf_p",
    "_wprintf_p_l", "_vwprintf_p_l", "_fwprintf_p_l", "_vfwprintf_p_l")
_STDIO_WIDE_STRING = (
    "swprintf", "vswprintf", "swprintf_s", "vswprintf_s",
    "_snwprintf", "_vsnwprintf", "_snwprintf_s", "_vsnwprintf_s",
    "_swprintf_s_l", "_vswprintf_s_l", "_snwprintf_l", "_vsnwprintf_l",
    "_snwprintf_s_l", "_vsnwprintf_s_l")
_STDIO_WIDE_STRING_X = (
    "_swprintf", "_vswprintf", "_swprintf_c", "_vswprintf_c",
    "_swprintf_c_l", "_vswprintf_c_l", "_swprintf_p", "_vswprintf_p",
    "_swprintf_p_l", "_vswprintf_p_l", "_vswprintf_l", "_swprintf_l",
    "_scwprintf", "_vscwprintf", "_scwprintf_l", "_vscwprintf_l",
    "_scwprintf_p", "_vscwprintf_p")
_STDIO_PRINT_X = (
    "_snprintf_c", "_snprintf_c_l", "_vsnprintf_c", "_vsnprintf_c_l",
    "vsnprintf_s", "__swprintf_l", "__vswprintf_l",
    "_scprintf_p_l", "_scwprintf_p_l")
_STDIO_SCAN = (
    "scanf", "wscanf", "fscanf", "fwscanf", "sscanf", "swscanf",
    "vfscanf", "vfwscanf", "vsscanf", "vswscanf",
    "scanf_s", "wscanf_s", "fscanf_s", "fwscanf_s", "sscanf_s", "swscanf_s",
    "_vfscanf_l", "_vfwscanf_l")
_STDIO_SCAN_L = (
    "_scanf_l", "_wscanf_l", "_scanf_s_l", "_wscanf_s_l",
    "_fscanf_l", "_fwscanf_l", "_fscanf_s_l", "_fwscanf_s_l",
    "_sscanf_l", "_swscanf_l", "_sscanf_s_l", "_swscanf_s_l",
    "_snscanf", "_snwscanf", "_snscanf_l", "_snwscanf_l",
    "_snscanf_s", "_snwscanf_s", "_snscanf_s_l", "_snwscanf_s_l")
_STDIO_VSCAN = (
    "vscanf", "vwscanf", "vscanf_s", "vwscanf_s", "vfscanf_s", "vfwscanf_s",
    "vswscanf_s", "_vscanf_l", "_vwscanf_l", "_vscanf_s_l", "_vwscanf_s_l",
    "_vsscanf_l", "_vsnwscanf_l", "_vsnwscanf_s_l")
_STDIO_MISC = (
    "localtime_s", "gmtime_s", "__local_stdio_printf_options",
    "__local_stdio_scanf_options")

# Each source is its own translation unit and its own probe: a name that a
# future SDK stops declaring takes down one group, not the lot, and
# probe_failures names the group that went.
_STDIO_GROUPS = (
    ("narrow_print", _STDIO_NARROW_PRINT),
    ("narrow_string", _STDIO_NARROW_STRING),
    ("wide_print", _STDIO_WIDE_PRINT),
    ("wide_string", _STDIO_WIDE_STRING),
    ("wide_string_x", _STDIO_WIDE_STRING_X),
    ("print_x", _STDIO_PRINT_X),
    ("scan", _STDIO_SCAN),
    ("scan_l", _STDIO_SCAN_L),
    ("vscan", _STDIO_VSCAN),
    ("misc", _STDIO_MISC),
)

# Which groups are built under which flags, per architecture. Every entry is
# there because the probe it names emitted a body that an artefact carries
# (see the note above); a combination that emitted nothing new is not listed.
# The flags are the ones the artefacts' own projects turn out to have used,
# worked out from which probe flavour reproduced which hash, not read off the
# recipes.
_STDIO_ALL = tuple(tag for tag, _ in _STDIO_GROUPS if tag != "misc")
_STDIO_PLAN = {
    "x86": (
        ("", [], _STDIO_ALL),
        ("oy", ["/Oy-"], ("narrow_print", "narrow_string", "wide_print",
                           "wide_string", "scan")),
        ("sdl", ["/sdl"], ("narrow_print", "narrow_string", "wide_print",
                           "wide_string", "wide_string_x", "scan")),
        ("sdloy", ["/sdl", "/Oy-"], ("narrow_print", "narrow_string",
                                     "wide_print", "wide_string", "scan")),
        ("od", ["/Od"], ("narrow_print", "narrow_string", "wide_print",
                         "wide_string", "wide_string_x", "print_x", "misc")),
    ),
    "x64": (
        ("", [], _STDIO_ALL),
        ("sdl", ["/sdl"], _STDIO_ALL),
        ("odsdl", ["/Od", "/sdl"], ("narrow_print", "wide_print",
                                    "wide_string", "misc")),
        ("gs0", ["/Gs0"], ("narrow_print", "narrow_string")),
        ("o1", ["/O1"], ("narrow_string",)),
    ),
}

# The same print groups as C++ under /std:c++20, x64 only. VX-API and
# protobuf are the two families that build that way, and their wrappers are
# a different body from the C one (22 instructions against 25); the x86
# registration of the same source emitted nothing an artefact carries.
_STDIO_CXX20 = ("narrow_print", "wide_print")


def _stdio_table_source(tag, names, exe=False):
    """C source whose only content is the address of every name in ``names``.

    The address is the point. Called, a UCRT inline wrapper is inlined at
    /O2 or not depending on the caller, and an inline the compiler can see
    through is an inline the baseline never gets a body for; with its address
    taken it is emitted as a function in its own right, every time.
    """
    entries = "".join("    (probe_symbol)%s,\n" % name for name in names)
    if exe:
        tail = ("int main(int argc, char **argv)\n{\n"
                "    return probe_msvcrt_%s_symbols[argc] != 0;\n}\n" % tag)
    else:
        tail = ("BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, "
                "LPVOID reserved) { return TRUE; }\n")
    return (_STDIO_TABLE_HEAD +
            "__declspec(dllexport) probe_symbol probe_msvcrt_%s_symbols[] = {\n"
            "%s};\n\n%s" % (tag, entries, tail))


def _msvc_stdio_probes(toolchain):
    """The probe registrations for the groups above, as _msvc_probes wants."""
    names = dict(_STDIO_GROUPS)
    probes = []
    for flavour, flags, tags in _STDIO_PLAN[toolchain.arch]:
        for tag in tags:
            filename = "probe_msvcrt_wstdio_%s%s.c" % (
                tag, "_" + flavour if flavour else "")
            probes.append((toolchain.cc, filename,
                           _stdio_table_source("wstdio_" + tag, names[tag]),
                           ["-shared", "/MD"] + flags + _MSVC_RECIPE_LINK))
    if toolchain.arch == "x64":
        for tag in _STDIO_CXX20:
            probes.append((toolchain.cxx,
                           "probe_msvcrt_wstdio_%s_cpp20.cpp" % tag,
                           _stdio_table_source("wstdio_" + tag, names[tag]),
                           ["-shared", "/MD", "/EHsc", "/std:c++20"]
                           + _MSVC_RECIPE_LINK))
    # One EXE registration, for the reason _PROBE_MSVCRT_STDIO_EXE gives: an
    # executable is a different object set. The bodies it contributes are the
    # DLL's, hash for hash, so it carries the two print groups and no more.
    probes.append((toolchain.cc, "probe_msvcrt_wstdio_exe.c",
                   _stdio_table_source("wstdio_exe",
                                       _STDIO_NARROW_PRINT + _STDIO_WIDE_PRINT,
                                       exe=True),
                   ["/MD"] + _MSVC_RECIPE_LINK))
    return probes


def _probe_command(toolchain, compiler, source, target, extra):
    """The command line for one probe, with ``extra`` put where it belongs.

    Three kinds of entry live in a probe's ``extra`` list and the MSVC side
    has to tell them apart, because cl and link reject each other's options:

    * ``-shared`` selects a DLL and is read by probe_command itself.
    * Anything starting with ``/`` or ending in ``.lib`` is cl's, and goes in
      front of the ``/link`` separator - a ``/MD`` or ``/std:c++20`` after it
      is handed to the linker, which rejects it outright.
    * ``link:/FLAG`` is the linker's, and goes after everything else, which
      is after the separator. That spelling exists for /INCREMENTAL:NO: a
      linker flag cannot be told from a compiler flag by its shape, and
      /INCREMENTAL:NO spliced in front of /link is a cl option cl does not
      have.
    """
    shared = "-shared" in extra
    command = toolchain.probe_command(compiler, source, target, shared)
    if toolchain.kind != "msvc":
        return command + [flag for flag in extra if flag != "-shared"]
    cl_arguments = [flag for flag in extra
                    if flag.startswith("/") or flag.endswith(".lib")]
    if cl_arguments and "/link" in command:
        split = command.index("/link")
        command[split:split] = cl_arguments
    else:
        command += cl_arguments
    # After the cl arguments and after probe_command's own /DEBUG and /PDB,
    # which are already on the linker's side of the separator.
    return command + [flag[len("link:"):] for flag in extra
                      if flag.startswith("link:")]


# What every MSVC recipe in this repository passes to the linker and no probe
# passed before it. /INCREMENTAL:NO because link /DEBUG implies /INCREMENTAL
# and the /OPT:NO* forms do not suppress it; /OPT:NOREF and /OPT:NOICF to say
# in the command line what /DEBUG already defaults to, so the probe's link is
# the recipes' link rather than merely equivalent to it today.
_MSVC_RECIPE_LINK = ["link:/INCREMENTAL:NO", "link:/OPT:NOREF",
                     "link:/OPT:NOICF"]


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
        # Sixth round: the printf half of stdio, and the entry-point wrapper.
        # Both sources' notes say what each is for; the registrations are four
        # because the DLL and the EXE are different object sets here as
        # everywhere else in this file, and because the EXE pair is what
        # measures the link line rather than the translation unit.
        (toolchain.cc, "probe_msvcrt_stdio.c", _PROBE_MSVCRT_STDIO,
         ["-shared", "/MD"]),
        (toolchain.cc, "probe_msvcrt_stdio_exe.c", _PROBE_MSVCRT_STDIO_EXE,
         ["/MD"]),
        (toolchain.cc, "probe_msvcrt_main.c", _PROBE_MSVCRT_MAIN,
         ["/MD"] + _MSVC_RECIPE_LINK),
        # And the broad EXE surface a second time, linked the way the recipes
        # link rather than the way /DEBUG defaults. Same source as
        # probe_md_exe.c, so nothing new is compiled and nothing can be lost:
        # whatever this measures that the incremental link did not is a second
        # PicHash added to a name the baseline already carries.
        (toolchain.cc, "probe_md_exe_noincr.c", _PROBE_EXE,
         ["/MD"] + _MSVC_RECIPE_LINK),
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
    probes += _msvc_stdio_probes(toolchain)
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
    if toolchain.kind == "linux":
        # A separate list rather than the four below plus extras: every one
        # of those four is #include <windows.h> with a __declspec entry point
        # and MSVCRT-only calls, so under this toolchain all four would fail
        # to build - which does not fail the family being built but does fail
        # the run and leaves the artefacts filtered against nothing.
        #
        # No -static-libstdc++ here, unlike the MinGW C++ probes. There it
        # puts the libstdc++ bodies into the baseline because the artefacts
        # can contain them; here libstdc++.so.6 is a shared object that no
        # artefact links statically, so a static probe would measure bodies
        # that are not in anything and miss the shared-libgcc registration
        # glue that is.
        #
        # -lm is on both C probes and is load-bearing on the executable one.
        # A shared object may leave a symbol undefined and resolve it at load
        # time, so the .so probe links without it; an executable may not, and
        # the probe takes the address of sin, cos and twenty more for the
        # reason recorded in its math block - so without -lm it failed to
        # link with 27 undefined references, which is precisely the silent
        # baseline shrink probe_failures exists to catch.
        probes = [
            (toolchain.cc, "probe_linux.c", _PROBE_LINUX_C, ["-shared", "-lm"]),
            (toolchain.cxx, "probe_linux.cpp", _PROBE_LINUX_CXX, ["-shared"]),
            (toolchain.cc, "probe_linux_exe.c", _PROBE_LINUX_C_EXE, ["-lm"]),
            (toolchain.cxx, "probe_linux_exe.cpp", _PROBE_LINUX_CXX_EXE, []),
        ]
    else:
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
        else:
            # MinGW only, deliberately. The stdio surface below is plain C
            # and cl would compile it, but registering it there would move
            # the MSVC baseline on a change nobody here can measure - MSVC
            # is only available on the Windows runner - and a probe that
            # fails to build now fails the whole run. The residue this
            # answers was measured on MinGW artefacts; what the MSVC side
            # carries is its own measurement to make.
            #
            # The second registration is the same source at -O0, which
            # overrides the -O2 probe_command puts in front of it. It is
            # there for the header wrappers only: their bodies are compiled
            # from this translation unit, so their PicHash follows the
            # optimisation level, and Obfuscator is the one recipe here that
            # builds at -O0. crt_glue maps a name to a *set* of PicHashes,
            # so a second flavour only ever adds members to that set.
            # -lws2_32 is for gai_strerrorA/W and is not optional: mingw-w64
            # does not inline them, it ships them as compiled objects inside
            # libws2_32.a, so the probe has to link that archive to get a body
            # for them the way OpenSSL, libevent and boringssl do. Without it
            # the probe does not build at all, which probe_failures reports
            # and which would otherwise have quietly dropped the whole stdio
            # surface out of this baseline.
            probes += [
                (toolchain.cc, "probe_stdio.c", _PROBE_STDIO,
                 ["-shared", "-lws2_32"]),
                (toolchain.cc, "probe_stdio_exe.c", _PROBE_STDIO_EXE,
                 ["-lws2_32"]),
                (toolchain.cc, "probe_stdio_exe_o0.c", _PROBE_STDIO_EXE,
                 ["-O0", "-lws2_32"]),
                (toolchain.cc, "probe_libc.c", _PROBE_LIBC, ["-shared"]),
                # Plain and cloned header wrappers, at -O2 and at -Os, and
                # msvcrt's own; see the note above _PROBE_STDIO_FMT for why
                # all five.
                (toolchain.cc, "probe_stdio_fmt.c", _PROBE_STDIO_FMT,
                 ["-shared"]),
                (toolchain.cc, "probe_stdio_fmt_const.c", _PROBE_STDIO_FMT,
                 ["-shared", "-DPROBE_STDIO_FMT_CONSTANT"]),
                (toolchain.cc, "probe_stdio_fmt_os.c", _PROBE_STDIO_FMT,
                 ["-shared", "-Os"]),
                (toolchain.cc, "probe_stdio_fmt_const_os.c", _PROBE_STDIO_FMT,
                 ["-shared", "-Os", "-DPROBE_STDIO_FMT_CONSTANT"]),
                (toolchain.cc, "probe_stdio_fmt_msvcrt.c", _PROBE_STDIO_FMT,
                 ["-shared", "-D__USE_MINGW_ANSI_STDIO=0"]),
            ]
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
            command = _probe_command(toolchain, compiler, source, target, extra)
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
    # All but two of these prefixes cannot reach a MinGW baseline at all:
    # the sources that define them are only ever compiled by cl.
    #
    # probe_stdio_ and probe_libc_ are the exceptions, and are prefixes from
    # the start rather than a list for the reason the note above gives: GCC
    # does emit
    # `probe_stdio_forward.constprop.0` and `.cold` partitions, and a list
    # would miss them the way it misses probe_vscprintf's today.
    #
    # The Linux probes are matched by prefix for the same reason, and can be:
    # every function they define is named probe_linux_*, including the
    # helpers, and GCC's .constprop/.cold/.isra partitions keep the prefix.
    # None of these can reach a MinGW or MSVC baseline either - the source
    # that defines them is only ever compiled by the native gcc.
    for name in [name for name in glue
                 if name.startswith(("probe_atl_", "_probe_atl_",
                                     "probe_stdio_", "_probe_stdio_",
                                     "probe_libc_", "_probe_libc_",
                                     "probe_msvcrt_", "_probe_msvcrt_",
                                     "probe_stl_", "_probe_stl_",
                                     "probe_linux_", "_probe_linux_",
                                     "ProbeInterface", "ProbeImplementation",
                                     "ProbeArray", "ProbeEh"))]:
        glue.pop(name, None)
    # One line a person reads at the top of a build log, because the failure
    # this file is most afraid of is a baseline that quietly got smaller: the
    # counts are the measured constants the README quotes, and a run whose
    # number is below them filtered its artefacts against less than the
    # corpus was filtered against. probe_failures already fails the run when
    # a probe will not build; this says what the surviving probes measured,
    # which is the number a reader can compare.
    LOGGER.info("%s: glue baseline measured from %d probe(s): %d symbol(s), "
                "%d PicHash(es)", toolchain_id, len(probes), len(glue),
                sum(len(hashes) for hashes in glue.values()))
    return glue


# ---------------------------------------------------------------------------
# Kernel mode.
#
# Everything above measures a user-mode image: a DLL or EXE linked against the
# C runtime, which is not what a .sys is. A driver has no ucrt and no
# vcruntime; what the WDK links into it instead is a handful of static
# libraries (BufferOverflowFastFailK.lib or BufferOverflowK.lib for the /GS
# cookie and its failure reporters, GsDriverEntry, the memcpy/memset/memmove
# family and their cpu-feature dispatch, the guard-cast stubs) plus whatever
# ntstrsafe.h and ntintsafe.h compile into the translation unit that calls
# them. None of it is the driver's own code and none of it is in the
# user-mode baseline, which is why the five driver images in this repository
# each carried 6 to 17 functions of it under their own family's name.
#
# So the kernel baseline is measured the same way - build the thing with
# nothing of the project in it and read off what is there - and kept apart
# from the user-mode one: kernel_glue() is only ever consulted for an image
# that is a driver (see is_kernel_image), so no user-mode image can gain or
# lose a function because of anything in this section.
#
# Three kinds of probe, because the three kinds of survivor in the committed
# images came from three different link lines:
#
# * ``wdm`` - the WDK's own msbuild driver project, WDM, Release|x64,
#   TargetVersion Windows10, the forced props the driver recipes use. This is
#   how Hidden, BlackBoneDrv and APICallProxy are built, and it links
#   BufferOverflowFastFailK.lib and enters through GsDriverEntry.
# * ``wdm_nogs`` - the same project with BufferSecurityCheck off, which is
#   how DiskCryptorDrv is built: no cookie, no GsDriverEntry, but the same
#   libcntpr-side memcpy/memset and guard stubs.
# * ``cl_link`` - cl /kernel and link /NODEFAULTLIB by hand against
#   BufferOverflowK.lib, which is WinPmemDrv's line. Its report functions
#   and __security_init_cookie are different bodies from the FastFail ones.
#
# What the probes call is deliberately narrow. A kernel image reaches
# ntoskrnl through one-instruction import thunks named after the export, and a
# thunk to ExAllocatePoolWithTag is the driver using an API, not the compiler's
# runtime; a probe that called it would put the thunk in the baseline and take
# it out of every driver that imports the same function. So the probes
# reference the C runtime and the header-defined helpers and nothing from the
# Ex/Ke/Mm/Zw/Rtl export families, and _KERNEL_THUNK_NAME below keeps a
# one-instruction function only when its name is in the runtime's namespace
# (``__chkstk``, ``_local_unwind``, ``memcmp``), not the kernel API's.
#
# x64 only. WDK 10.0.26100 has no x86 kernel target at all (the playbook in
# this directory has the exact error), so there is no x86 .sys to measure or
# to filter, and kernel_glue("msvc..._x86") is empty by construction.
# ---------------------------------------------------------------------------

_KERNEL_INCLUDES = "#include <ntifs.h>\n"

_KERNEL_DRIVER_ENTRY = _KERNEL_INCLUDES + """\
DRIVER_INITIALIZE DriverEntry;
DRIVER_UNLOAD ProbeKernelUnload;

VOID ProbeKernelUnload(PDRIVER_OBJECT DriverObject)
{
    UNREFERENCED_PARAMETER(DriverObject);
}

NTSTATUS DriverEntry(PDRIVER_OBJECT DriverObject, PUNICODE_STRING RegistryPath)
{
    UNREFERENCED_PARAMETER(RegistryPath);
    DriverObject->DriverUnload = ProbeKernelUnload;
    return STATUS_SUCCESS;
}
"""

# The frame, the unwinder and the indirect call: what makes cl reference
# __chkstk, __C_specific_handler, _local_unwind and the guard-dispatch stubs.
# The array is larger than a page so that the prologue has to probe it, and
# every size that reaches memcpy and friends is a run-time value so that cl
# cannot expand it inline.
_KERNEL_RUNTIME = _KERNEL_INCLUDES + """\
#include <string.h>

typedef VOID (*PROBE_KERNEL_CALLBACK)(PVOID);

static volatile LONG ProbeKernelSink;
static PROBE_KERNEL_CALLBACK volatile ProbeKernelCallback;

NTSTATUS ProbeKernelFrame(PUCHAR input, SIZE_T length, PVOID context)
{
    UCHAR big[0x3000];
    SIZE_T i;

    for (i = 0; i < sizeof(big); i++) {
        big[i] = (UCHAR)(input[i % (length | 1)] + i);
    }
    memcpy(context, big, length);
    memmove(big + 1, big, length);
    memset(context, 0x5a, length);
    ProbeKernelSink += memcmp(big, context, length);

    __try {
        ProbeKernelSink += big[length & 0xfff];
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return GetExceptionCode();
    }
    __try {
        ProbeKernelSink++;
    } __finally {
        ProbeKernelSink--;
    }
    if (ProbeKernelCallback) {
        ProbeKernelCallback(context);
    }
    return STATUS_SUCCESS;
}
"""

# Names taken by address, one translation unit each, so that a name a given
# WDK does not declare costs that one unit and not the family it is listed
# with. Address-taking is the same device the wide-stdio round used: a call
# can be expanded in line, an address cannot, and for an inline function in a
# header it is what makes cl emit a body to be named at all.
# memchr, wcslen, wcscmp, wcscpy and wcscat are not here: the first measurement
# (run 42402246098, WDK 10.0.26100.0) listed them, and each of the five units
# failed to compile there. Only their one-instruction import thunks would have
# been measured, which is not what this baseline is for, so they were taken
# out rather than fixed.
_KERNEL_CRT_NAMES = (
    "memcpy", "memmove", "memset", "memcmp",
    "strlen", "strcmp", "strncmp", "strcpy", "strncpy", "strcat", "strchr",
    "strrchr", "strstr",
    "wcsncmp", "wcsncpy", "wcschr", "wcsrchr", "wcsstr",
)

_KERNEL_NTDDK_NAMES = ("RtlFailFast",)


def _strsafe_names():
    names = []
    for width in ("Cb", "Cch"):
        for operation in ("Cat", "CatN", "Copy", "CopyN", "Length",
                          "Printf", "VPrintf"):
            for suffix in ("A", "W"):
                names.append("RtlString%s%s%s" % (width, operation, suffix))
                if operation != "Length":
                    names.append("RtlString%s%sEx%s" % (width, operation, suffix))
    names += ["RtlStringCbCopyUnicodeString", "RtlStringCchCopyUnicodeString"]
    names += ["RtlUnicodeString%s" % operation for operation in (
        "Cat", "CatEx", "CatString", "CatStringEx", "Copy", "CopyEx",
        "CopyString", "CopyStringEx", "Init", "InitEx", "Printf", "PrintfEx",
        "VPrintf", "VPrintfEx", "Validate", "ValidateEx")]
    return tuple(names)


_KERNEL_STRSAFE_NAMES = _strsafe_names()

_KERNEL_INTSAFE_NAMES = (
    "RtlULongAdd", "RtlULongSub", "RtlULongMult",
    "RtlUIntAdd", "RtlUIntMult",
    "RtlSizeTAdd", "RtlSizeTSub", "RtlSizeTMult",
    "RtlULongLongAdd", "RtlULongLongMult",
    "RtlULongLongToULong", "RtlSizeTToULong",
)


def _kernel_symbol_source(header, name):
    return (_KERNEL_INCLUDES + header
            + "PVOID ProbeKernelSymbol_%s = (PVOID)%s;\n" % (name, name))


def _kernel_sources():
    """[(tag, source)] in a fixed order; the tag is the file stem."""
    sources = [("driver_entry", _KERNEL_DRIVER_ENTRY),
               ("runtime", _KERNEL_RUNTIME)]
    for names, header in ((_KERNEL_CRT_NAMES, "#include <string.h>\n"),
                          (_KERNEL_NTDDK_NAMES, ""),
                          (_KERNEL_STRSAFE_NAMES, "#include <ntstrsafe.h>\n"),
                          (_KERNEL_INTSAFE_NAMES, "#include <ntintsafe.h>\n")):
        for name in names:
            sources.append(("sym_" + name, _kernel_symbol_source(header, name)))
    return sources


# Forced into the msbuild flavours exactly as the driver recipes force it:
# BlackBoneDrv's list (compiler and linker PDBs apart, /OPT:NOREF /OPT:NOICF,
# no whole-program optimisation, /Brepro /INCREMENTAL:NO, warnings not errors),
# which Hidden and APICallProxy share, and DiskCryptorDrv's additions for the
# nogs flavour. RuntimeLibrary is left alone as it is there.
def _kernel_props(flavour):
    compile_extra = ""
    if flavour == "wdm_nogs":
        compile_extra = ("<BufferSecurityCheck>false</BufferSecurityCheck>"
                         "<Optimization>MaxSpeed</Optimization>")
    return (
        "<Project><ItemDefinitionGroup><ClCompile>"
        "<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>"
        "<ProgramDataBaseFileName>$(IntDir)probe.compiler.pdb"
        "</ProgramDataBaseFileName>"
        "<WholeProgramOptimization>false</WholeProgramOptimization>"
        "<TreatWarningAsError>false</TreatWarningAsError>"
        + compile_extra +
        "</ClCompile><Link>"
        "<GenerateDebugInformation>true</GenerateDebugInformation>"
        "<ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile>"
        "<OptimizeReferences>false</OptimizeReferences>"
        "<EnableCOMDATFolding>false</EnableCOMDATFolding>"
        "<LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration>"
        "<TreatLinkerWarningAsErrors>false</TreatLinkerWarningAsErrors>"
        "<AdditionalOptions>%(AdditionalOptions) /Brepro /INCREMENTAL:NO "
        "/IGNORE:4266</AdditionalOptions>"
        "</Link></ItemDefinitionGroup></Project>")


def _kernel_project(tags):
    items = "".join('<ClCompile Include="src\\%s.c" />' % tag for tag in tags)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Project DefaultTargets="Build" ToolsVersion="Current" '
        'xmlns="http://schemas.microsoft.com/developer/msbuild/2003">\n'
        '<ItemGroup Label="ProjectConfigurations">'
        '<ProjectConfiguration Include="Release|x64">'
        '<Configuration>Release</Configuration><Platform>x64</Platform>'
        '</ProjectConfiguration></ItemGroup>\n'
        '<PropertyGroup Label="Globals">'
        '<ProjectGuid>{3F0C6B2E-7A41-4C38-9E52-6D1B8A0F4C77}</ProjectGuid>'
        '<RootNamespace>probe</RootNamespace>'
        '<Configuration>Release</Configuration>'
        '<Platform Condition="\'$(Platform)\' == \'\'">x64</Platform>'
        '</PropertyGroup>\n'
        '<Import Project="$(VCTargetsPath)\\Microsoft.Cpp.Default.props" />\n'
        '<PropertyGroup Label="Configuration">'
        '<TargetVersion>Windows10</TargetVersion>'
        '<UseDebugLibraries>false</UseDebugLibraries>'
        '<PlatformToolset>WindowsKernelModeDriver10.0</PlatformToolset>'
        '<ConfigurationType>Driver</ConfigurationType>'
        '<DriverType>WDM</DriverType></PropertyGroup>\n'
        '<Import Project="$(VCTargetsPath)\\Microsoft.Cpp.props" />\n'
        '<PropertyGroup><TargetName>probe</TargetName></PropertyGroup>\n'
        '<ItemGroup>' + items + '</ItemGroup>\n'
        '<Import Project="$(VCTargetsPath)\\Microsoft.Cpp.targets" />\n'
        '</Project>\n')


# A one-instruction function in a driver is nearly always the thunk to an
# ntoskrnl export, named after it. Those are the driver using an API and are
# not baseline; the ones that are the runtime's own are the compiler helpers
# and C library names ntoskrnl happens to export, and those live in the
# compiler's namespace: __chkstk, _local_unwind, memcmp. The kernel API's are
# CamelCase with a family prefix (ExAllocatePoolWithTag, ZwClose).
def _kernel_thunk_is_runtime(name):
    letters = [character for character in name if character.isalpha()]
    return bool(letters) and not any(character.isupper() for character in letters)


def _wdk_layout():
    """(km include dir, km\\crt dir, shared dir, km lib dir) or None."""
    sdk = os.environ.get("WindowsSdkDir", "")
    if not sdk:
        sdk = r"C:\Program Files (x86)\Windows Kits\10" + os.sep
    versions = []
    wanted = os.environ.get("WindowsSDKVersion", "").strip("\\/")
    if wanted:
        versions.append(wanted)
    include = os.path.join(sdk, "Include")
    if os.path.isdir(include):
        versions += sorted((name for name in os.listdir(include)
                            if name.startswith("10.")), reverse=True)
    for version in versions:
        km = os.path.join(sdk, "Include", version, "km")
        lib = os.path.join(sdk, "Lib", version, "km", "x64")
        if os.path.isfile(os.path.join(km, "ntddk.h")) \
                and os.path.isfile(os.path.join(lib, "ntoskrnl.lib")):
            return (km, os.path.join(km, "crt"),
                    os.path.join(sdk, "Include", version, "shared"), lib,
                    version)
    return None


def _tail(completed, limit=3000):
    """What a failed tool said: its error lines, or failing that its tail.

    cl prints a warning per unit (C4117 for the reserved _KERNEL_MODE define
    on every one of them), so the last 3000 characters of a 110-unit compile
    are all warnings and say nothing about the five that failed. The error
    lines are what a reader needs.
    """
    text = ((completed.stdout or "") + (completed.stderr or "")).strip()
    errors = [line.strip() for line in text.splitlines()
              if re.search(r"\b(?:fatal )?error [A-Z]+\d+", line)]
    if errors:
        return "\n".join(errors[:60])[-limit:]
    return text[-limit:]


def _kernel_probe_images(toolchain_id, tmp, layout):
    """Build the three flavours; returns [(flavour, image, pdb)].

    Every failure is logged and recorded, never raised: the family being
    built should not go down with a probe, only the run, afterwards.
    """
    km, crt, shared, lib, version = layout
    failures = _PROBE_FAILURES.setdefault(toolchain_id, [])
    source_dir = os.path.join(tmp, "src")
    os.makedirs(source_dir)
    sources = _kernel_sources()
    for tag, code in sources:
        with open(os.path.join(source_dir, tag + ".c"), "w") as handle:
            handle.write(code)

    # Which units compile at all. Built together by one cl invocation: cl
    # carries on past a failing file, and a unit that failed leaves no object,
    # so the objects present afterwards are the units that compiled. The
    # flags are WinPmemDrv's, which is the one recipe here that invokes cl
    # directly.
    object_dir = os.path.join(tmp, "obj")
    os.makedirs(object_dir)
    compile_command = [
        "cl", "/nologo", "/c", "/O2", "/MD", "/Zi", "/GL-", "/kernel", "/Zl",
        "/GS", "/D_AMD64_", "/DAMD64", "/DWIN64", "/D_WIN64", "/D_KERNEL_MODE",
        "/I" + km, "/I" + crt, "/I" + shared,
        "/Fdobj\\compiler.pdb", "/Foobj\\"]
    compile_command += ["src\\%s.c" % tag for tag, _ in sources]
    built = subprocess.run(compile_command, capture_output=True, cwd=tmp,
                           text=True, errors="replace")
    compiled = [tag for tag, _ in sources
                if os.path.isfile(os.path.join(object_dir, tag + ".obj"))]
    for tag, _ in sources:
        if tag not in compiled:
            failures.append("kernel/%s.c" % tag)
    if len(compiled) != len(sources):
        LOGGER.warning("%s: %d kernel baseline probe unit(s) did not compile "
                       "and are missing from the baseline:\n%s", toolchain_id,
                       len(sources) - len(compiled), _tail(built))
    if "driver_entry" not in compiled:
        return []

    images = []

    # cl_link flavour. A unit naming an ntoskrnl export that does not exist
    # fails the link with LNK2001 naming its object, so the units it names are
    # dropped and the link repeated rather than losing the flavour.
    linked = list(compiled)
    for _ in range(4):
        link_command = [
            "link", "/nologo", "/DRIVER", "/SUBSYSTEM:NATIVE",
            "/ENTRY:DriverEntry", "/NODEFAULTLIB", "/MACHINE:X64", "/DEBUG",
            "/OPT:NOREF", "/OPT:NOICF", "/INCREMENTAL:NO", "/Brepro",
            "/OUT:probe_cl_link.sys", "/PDB:probe_cl_link.pdb"]
        link_command += ["obj\\%s.obj" % tag for tag in linked]
        link_command += ["/LIBPATH:" + lib, "ntoskrnl.lib", "hal.lib",
                         "wdmsec.lib", "BufferOverflowK.lib"]
        result = subprocess.run(link_command, capture_output=True, cwd=tmp,
                                text=True, errors="replace")
        if result.returncode == 0:
            images.append(("cl_link", os.path.join(tmp, "probe_cl_link.sys"),
                           os.path.join(tmp, "probe_cl_link.pdb")))
            break
        unresolved = set(re.findall(
            r"obj\\(\w+)\.obj\s*: error LNK\d+", (result.stdout or "")
            + (result.stderr or "")))
        unresolved.discard("driver_entry")
        if not unresolved & set(linked):
            LOGGER.warning("%s: the cl_link kernel baseline probe did not "
                           "link:\n%s", toolchain_id, _tail(result))
            failures.append("kernel/cl_link")
            break
        for tag in sorted(unresolved & set(linked)):
            failures.append("kernel/%s.c (link)" % tag)
        LOGGER.warning("%s: dropping kernel baseline probe unit(s) that did "
                       "not link: %s", toolchain_id,
                       ", ".join(sorted(unresolved)))
        linked = [tag for tag in linked if tag not in unresolved]
    else:
        failures.append("kernel/cl_link")

    # The two msbuild flavours, over the units that compiled and linked.
    for flavour in ("wdm", "wdm_nogs"):
        work = os.path.join(tmp, flavour)
        os.makedirs(os.path.join(work, "src"))
        for tag in linked:
            with open(os.path.join(work, "src", tag + ".c"), "w") as handle:
                handle.write(dict(sources)[tag])
        with open(os.path.join(work, "probe.vcxproj"), "w") as handle:
            handle.write(_kernel_project(linked))
        with open(os.path.join(work, "corpus-msvc.props"), "w") as handle:
            handle.write(_kernel_props(flavour))
        command = [
            "msbuild", "probe.vcxproj", "/nologo", "/p:Configuration=Release",
            "/p:Platform=x64", "/p:TargetVersion=Windows10",
            "/p:SignMode=Off", "/p:SkipPackageVerification=true",
            "/p:WholeProgramOptimization=false", "/p:OutDir=out\\",
            "/p:IntDir=obj\\",
            "/p:ForceImportBeforeCppTargets=" + os.path.join(
                work, "corpus-msvc.props"),
            "/m", "/v:minimal"]
        result = subprocess.run(command, capture_output=True, cwd=work,
                                text=True, errors="replace")
        image = os.path.join(work, "out", "probe.sys")
        if result.returncode != 0 or not os.path.isfile(image):
            LOGGER.warning("%s: the %s kernel baseline probe did not build:\n%s",
                           toolchain_id, flavour, _tail(result))
            failures.append("kernel/" + flavour)
            continue
        images.append((flavour, image, os.path.join(work, "out", "probe.pdb")))
    return images


@functools.lru_cache(maxsize=None)
def kernel_glue(toolchain_id):
    """Map symbol name -> set of PicHashes for kernel-mode (WDK) images.

    Separate from crt_glue and consulted only for a driver; empty on every
    toolchain that cannot build one.
    """
    from .smdaify import disassemble

    toolchain = get_toolchain(toolchain_id)
    if toolchain.kind != "msvc" or toolchain.arch != "x64":
        LOGGER.info("%s: no kernel-mode baseline (the WDK has no kernel "
                    "target for this architecture)", toolchain_id)
        return {}
    _PROBE_FAILURES.setdefault(toolchain_id, [])
    layout = _wdk_layout()
    if layout is None:
        LOGGER.warning("%s: no WDK (km headers and ntoskrnl.lib) found, so "
                       "the kernel-mode baseline is empty", toolchain_id)
        _PROBE_FAILURES[toolchain_id].append("kernel/wdk")
        return {}
    dump = os.environ.get("CORPUS_BASELINE_DUMP")
    glue = {}
    with tempfile.TemporaryDirectory() as tmp:
        images = _kernel_probe_images(toolchain_id, tmp, layout)
        for flavour, image, pdb in images:
            report = disassemble(image, pdb_path=pdb)
            before = len(glue)
            for function in report.getFunctions():
                name = function.function_name
                if not name:
                    continue
                if dump:
                    LOGGER.info("kernel probe %s: %s pic=%d instructions=%d",
                                flavour, name, function.pic_hash,
                                function.num_instructions)
                if function.num_instructions == 1 \
                        and not _kernel_thunk_is_runtime(name):
                    continue
                glue.setdefault(name, set()).add(function.pic_hash)
            LOGGER.info("%s: kernel probe %s (WDK %s): %d function(s), %d new "
                        "symbol(s)", toolchain_id, flavour, layout[4],
                        len(list(report.getFunctions())), len(glue) - before)
    glue.pop("DriverEntry", None)
    # ??_C@_ is an MSVC string-literal COMDAT that sits in a code section and
    # disassembles as a function. The two the probes emit are "" and L"": data
    # that any code using the literal carries, not the runtime's, so they are
    # not baseline - the same reason the playbook gives for not counting them
    # as the driver's own functions.
    for name in [name for name in glue
                 if name.startswith(("ProbeKernel", "_ProbeKernel", "??_C@_"))]:
        glue.pop(name, None)
    LOGGER.info("%s: kernel glue baseline measured from %d image(s): %d "
                "symbol(s), %d PicHash(es)", toolchain_id, len(images),
                len(glue), sum(len(hashes) for hashes in glue.values()))
    return glue


def is_kernel_image(name):
    """True for a driver by its file name, which is how recipes name them."""
    return str(name or "").lower().endswith(".sys")


def is_glue(function, toolchain_id, kernel=False):
    glue = crt_glue(toolchain_id)
    if not function.function_name:
        return False
    if function.pic_hash in glue.get(function.function_name, ()):
        return True
    # A driver is filtered against the user-mode set too, as it always was:
    # the kernel baseline adds to it and never replaces it.
    return bool(kernel) and function.pic_hash in kernel_glue(
        toolchain_id).get(function.function_name, ())
