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
        probes.append((toolchain.cxx, "probe_atl.cpp", _PROBE_ATL, ["-shared"]))
    glue = {}
    with tempfile.TemporaryDirectory() as tmp:
        for compiler, filename, code, extra in probes:
            source = os.path.join(tmp, filename)
            target = os.path.join(tmp, filename + ".out.exe")
            with open(source, "w") as handle:
                handle.write(code)
            shared = "-shared" in extra
            command = toolchain.probe_command(compiler, source, target, shared)
            command += [flag for flag in extra if flag != "-shared"
                        and toolchain.kind != "msvc"]
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
                continue
            probe = disassemble(target, pdb_path=toolchain.probe_pdb(target))
            for function in probe.getFunctions():
                if not function.function_name:
                    continue
                glue.setdefault(function.function_name, set()).add(function.pic_hash)
    # The probe's own function is the one thing here that is not runtime code.
    for name in ("_probe_runtime", "probe_runtime", "_compare", "compare",
                 "_probe_vscprintf", "probe_vscprintf",
                 "_probe_cxx_runtime", "probe_cxx_runtime", "_main", "main",
                 "_probe_atl", "probe_atl"):
        glue.pop(name, None)
    return glue


def is_glue(function, toolchain_id):
    glue = crt_glue(toolchain_id)
    if not function.function_name:
        return False
    return function.pic_hash in glue.get(function.function_name, ())
