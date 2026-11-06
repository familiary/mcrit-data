// Instantiates crummie5/FreshyCalls so its code is emitted.
//
// The project is four headers and two translation units with no build system
// of any kind - no CMakeLists, no makefile, no project file - and its entry
// points are variadic templates on a singleton class, so nothing of the
// interesting half exists in a binary until something instantiates it.
// syscall.cpp and utils.cpp alone compile to the non-template members only.
//
// Coverage is every entry point the class exposes: CallSyscall and
// DirectCallSyscall at three arities each, because the variadic template
// builds a different stub thunk per argument count and arity is the only
// thing there is to vary; GetSyscallNumber and GetStubAddr, which are the
// lookups into the two maps; and get_instance, whose first call runs
// ExtractStubs and ExtractSyscallsNumbers - the export-directory parse and
// the sort-by-virtual-address that give the technique its name.
//
// Nothing here is ever run. The DLL is compiled and disassembled only, so
// the handles and lengths below are whatever makes each overload resolve.
//
// x64 only, and not by this file's choice: syscall.hpp opens with an
// #error on anything that is not __x86_64 or _M_AMD64.

#include <windows.h>

#include "syscall.hpp"
#include "utils.hpp"

#include "corpus_export.h"

static void* volatile corpus_sink;

CORPUS_EXPORT int corpus_exercise()
{
    auto& sc = freshycalls::Syscall::get_instance();

    // Three arities of each caller: the template emits a distinct stub
    // signature per argument count.
    HANDLE h = nullptr;
    SIZE_T len = 0;
    PVOID base = nullptr;

    sc.CallSyscall("NtTestAlert");
    sc.CallSyscall("NtClose", h);
    sc.CallSyscall("NtFreeVirtualMemory", h, &base, &len, (ULONG)0);

    sc.DirectCallSyscall("NtTestAlert");
    sc.DirectCallSyscall("NtClose", h);
    sc.DirectCallSyscall("NtFreeVirtualMemory", h, &base, &len, (ULONG)0);

    corpus_sink = (void*)(uintptr_t)sc.GetSyscallNumber("NtClose");
    corpus_sink = (void*)sc.GetStubAddr("NtClose");

    return corpus_sink != nullptr;
}
