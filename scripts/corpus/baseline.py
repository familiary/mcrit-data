"""Identify MinGW C runtime glue so it is not attributed to a library family.

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
import os
import subprocess
import tempfile

from .toolchain import get_toolchain


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

static int compare(const void *a, const void *b) { return *(const int *)a - *(const int *)b; }

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
            subprocess.run(command, check=True, capture_output=True,
                           cwd=tmp)
            for function in disassemble(target).getFunctions():
                if not function.function_name:
                    continue
                glue.setdefault(function.function_name, set()).add(function.pic_hash)
    # The probe's own function is the one thing here that is not runtime code.
    for name in ("_probe_runtime", "probe_runtime", "_compare", "compare",
                 "_probe_cxx_runtime", "probe_cxx_runtime", "_main", "main"):
        glue.pop(name, None)
    return glue


def is_glue(function, toolchain_id):
    glue = crt_glue(toolchain_id)
    if not function.function_name:
        return False
    return function.pic_hash in glue.get(function.function_name, ())
