// Instantiates JustasMasiulis/wow64pp so its code is actually emitted.
//
// The library is header-only and its CMakeLists.txt declares it
// "add_library(wow64pp INTERFACE)": nothing of it exists in a binary until a
// translation unit uses it, so there is no upstream artefact to disassemble.
// Upstream's own consumer, test/main.cpp, is not usable for that - it needs
// the test/Catch submodule, which the repository references but does not
// contain, so cmake configure fails before anything is compiled. This file is
// the driver instead. The functions that land in the binary are wow64pp's;
// this file only decides which ones get emitted.
//
// Coverage is every entry point the header has: module_handle and import in
// both their error_code and exception spellings, and call_function in both
// its arities - it is a variadic template with no error_code overload, so
// arity is what there is to vary - plus the detail:: layer underneath them,
// which is where the Heaven's Gate work actually happens: the 64-bit PEB
// walk, the x64 ntdll export-directory parse and the far-call thunk in
// call_function.
//
// Nothing here is ever run. The exerciser is compiled and disassembled, so
// the arguments are whatever makes each overload resolve; they do not have to
// be meaningful and several deliberately are not.

// wow64pp.hpp includes only <system_error>, <memory> and <cstring>, and then
// uses HANDLE, CloseHandle and VirtualAlloc (detail::read_memory and
// call_function), std::numeric_limits (detail::read_memory),
// std::aligned_storage and std::alignment_of (detail::read_memory<T>),
// offsetof (module_handle), std::uint64_t throughout, and std::equal,
// std::string and std::runtime_error in the namespace-scope functions. All of
// those have to be declared before it is included or it does not compile; the
// header being consumed as-is, unmodified, is the point of this corpus, so the
// includes go here rather than there.
//
// <windows.h> lowercase: MSVC's filesystem is case-insensitive and does not
// care, but the mingw-w64 headers on a Linux cross build ship the name in
// lower case and <Windows.h> is a hard "No such file or directory" there.
//
// NO_STRICT is load-bearing, not tidiness. wow64pp.hpp re-declares five
// kernel32 functions itself inside `namespace wow64pp::detail extern "C"`,
// and two of them do not have the SDK's type: it writes GetModuleHandleA and
// GetProcAddress as taking void* where the SDK declares HMODULE. Under STRICT
// - which windef.h switches on by default - HMODULE is struct HINSTANCE__*,
// so those are two C-linkage declarations of one name with different types,
// which [dcl.link]/6 makes ill-formed and which MSVC diagnoses as C2733.
// NO_STRICT makes HANDLE, HMODULE and every other handle PVOID again, at
// which point all five declarations match the SDK's exactly. It changes
// typedefs only and not one byte of emitted code. Measured: the first cl
// build of this file (CI run 35858415869, x86) emitted no C2733, so NO_STRICT
// does do what it is here for - the declarations at wow64pp.hpp:188-205 all
// passed, and the first diagnostic was at line 356, 150 lines further down.
//
// NOMINMAX is load-bearing for cl and only for cl, and the MinGW build of
// this same file could not have found it. The SDK's shared/minwindef.h reads
//
//     #ifndef NOMINMAX
//     #ifndef max
//     #define max(a,b)            (((a) > (b)) ? (a) : (b))
//
// with no C++ guard, while mingw-w64's own minwindef.h wraps that same block
// in "#ifndef __cplusplus" (line 170) and so never defines it for a C++
// translation unit at all. wow64pp.hpp calls
// std::numeric_limits<std::uint32_t>::max() at lines 356 and 381, in the two
// detail::read_memory overloads, so under cl the macro is invoked with zero
// arguments and the header stops being parseable:
//
//     wow64pp.hpp(356): warning C4003: not enough arguments for
//                       function-like macro invocation 'max'
//     wow64pp.hpp(356): error C2589: '(': illegal token on right side of '::'
//
// - and then a hundred cascading errors until C1003 gives up. That is what
// failed the first MSVC x86 build; defining NOMINMAX is the whole fix. It
// suppresses two macro definitions and changes no emitted code, and on
// mingw-w64 it is a no-op over a block the C++ guard has already excluded.
#define NO_STRICT
#define NOMINMAX
#include <windows.h>

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <iterator>
#include <limits>
#include <stdexcept>
#include <string>
#include <system_error>
#include <type_traits>

#include <wow64pp.hpp>

namespace defs = wow64pp::defs;
namespace detail = wow64pp::detail;

// Every function in the header is `inline`, so a call site that the optimiser
// swallows leaves nothing in the image to disassemble - and at /O2 or -O2
// most of detail:: is small enough to be swallowed. Taking a function's
// address forces an out-of-line definition to be emitted, which /OPT:NOREF
// (MSVC) then keeps, so the addresses below are what actually guarantees the
// sample. The calls further down are what gives those bodies realistic call
// sites and pulls in the read_memory instantiations the public functions use.
//
// The array is exported so that nothing can conclude it is dead. The "= {}"
// is not decoration: an extern "C" variable declared without an initialiser
// is a declaration and not a definition, and the link fails on it.
extern "C" __declspec(dllexport) void *wow64pp_entry_points[32] = {};

extern "C" __declspec(dllexport) void wow64pp_take_addresses(void)
{
    void **out = wow64pp_entry_points;

    // Two of the three documented entry points, both spellings each.
    // call_function, the third, is below - it has only the one spelling.
    *out++ = (void *)static_cast<std::uint64_t (*)(const std::string &)>(
        &wow64pp::module_handle);
    *out++ = (void *)static_cast<std::uint64_t (*)(const std::string &,
                                                   std::error_code &)>(
        &wow64pp::module_handle);
    *out++ = (void *)static_cast<std::uint64_t (*)(std::uint64_t,
                                                   const std::string &)>(
        &wow64pp::import);
    *out++ = (void *)static_cast<std::uint64_t (*)(std::uint64_t,
                                                   const std::string &,
                                                   std::error_code &)>(
        &wow64pp::import);

    // call_function is a variadic template and each arity is its own body.
    // Four arguments and more than four are genuinely different code: the
    // >4 case is the one that walks arr_args backwards pushing the overflow
    // onto the 64-bit stack, and the <=4 case never reaches that loop.
    *out++ = (void *)static_cast<std::uint64_t (*)(std::uint64_t,
                                                   std::uint64_t,
                                                   std::uint64_t,
                                                   std::uint64_t,
                                                   std::uint64_t)>(
        &wow64pp::call_function<std::uint64_t, std::uint64_t, std::uint64_t,
                                std::uint64_t>);
    *out++ = (void *)static_cast<std::uint64_t (*)(std::uint64_t,
                                                   std::uint64_t,
                                                   std::uint64_t,
                                                   std::uint64_t,
                                                   std::uint64_t,
                                                   std::uint64_t,
                                                   std::uint64_t)>(
        &wow64pp::call_function<std::uint64_t, std::uint64_t, std::uint64_t,
                                std::uint64_t, std::uint64_t, std::uint64_t>);

    // detail::, in the order the header defines it.
    *out++ = (void *)static_cast<std::error_code (*)()>(&detail::get_last_error);
    *out++ = (void *)static_cast<void (*)(const char *)>(&detail::throw_last_error);
    *out++ = (void *)static_cast<void (*)(const char *, int)>(&detail::throw_if_failed);
    *out++ = (void *)static_cast<void *(*)()>(&detail::self_handle);
    *out++ = (void *)static_cast<void *(*)(std::error_code &)>(&detail::self_handle);
    *out++ = (void *)static_cast<void *(*)(const char *)>(&detail::native_module_handle);
    *out++ = (void *)static_cast<void *(*)(const char *, std::error_code &)>(
        &detail::native_module_handle);
    *out++ = (void *)static_cast<defs::NtQueryInformationProcessT (*)(const char *)>(
        &detail::native_ntdll_function<defs::NtQueryInformationProcessT>);
    *out++ = (void *)static_cast<defs::NtWow64ReadVirtualMemory64T (*)(
        const char *, std::error_code &)>(
        &detail::native_ntdll_function<defs::NtWow64ReadVirtualMemory64T>);
    *out++ = (void *)static_cast<std::uint64_t (*)()>(&detail::peb_address);
    *out++ = (void *)static_cast<std::uint64_t (*)(std::error_code &)>(&detail::peb_address);

    // read_memory has four forms: a buffer-and-size pair templated on the
    // pointee, and a return-by-value pair that copies into an
    // aligned_storage and blits it out. The <32-bit-address fast path that
    // memcpy()s directly and the NtWow64ReadVirtualMemory64 slow path are in
    // the same body, so one instantiation carries both.
    *out++ = (void *)static_cast<void (*)(std::uint64_t, defs::PEB_64 *, std::size_t)>(
        &detail::read_memory<defs::PEB_64>);
    *out++ = (void *)static_cast<void (*)(std::uint64_t, defs::PEB_64 *, std::size_t,
                                          std::error_code &)>(
        &detail::read_memory<defs::PEB_64>);
    *out++ = (void *)static_cast<defs::PEB_64 (*)(std::uint64_t)>(
        &detail::read_memory<defs::PEB_64>);
    *out++ = (void *)static_cast<defs::PEB_64 (*)(std::uint64_t, std::error_code &)>(
        &detail::read_memory<defs::PEB_64>);

    *out++ = (void *)static_cast<defs::IMAGE_EXPORT_DIRECTORY (*)(std::uint64_t)>(
        &detail::image_export_dir);
    *out++ = (void *)static_cast<defs::IMAGE_EXPORT_DIRECTORY (*)(std::uint64_t,
                                                                  std::error_code &)>(
        &detail::image_export_dir);
    *out++ = (void *)static_cast<std::uint64_t (*)()>(&detail::ldr_procedure_address);
    *out++ = (void *)static_cast<std::uint64_t (*)(std::error_code &)>(
        &detail::ldr_procedure_address);
}

// The README's own worked example, which is how the library is actually used
// and what a sighting of it in the wild looks like: resolve the 64-bit ntdll,
// resolve an export in it, then far-call it. Both call_function arities are
// here too - import() itself uses the four-argument form, and
// NtQueryVirtualMemory takes six.
extern "C" __declspec(dllexport) unsigned long long wow64pp_exercise(const char *name)
{
    std::uint64_t sink = 0;

    try {
        const auto ntdll = wow64pp::module_handle("ntdll.dll");
        const auto query_virtual_memory =
            wow64pp::import(ntdll, "NtQueryVirtualMemory");

        std::uint64_t info[12] = {};
        std::uint64_t written = 0;
        sink += wow64pp::call_function(query_virtual_memory,
                                       detail::self_handle(),
                                       std::uint64_t(0),
                                       std::uint64_t(0),
                                       &info[0],
                                       std::uint64_t(sizeof(info)),
                                       &written);
        sink += written;
    }
    catch (const std::system_error &error) {
        sink += static_cast<std::uint64_t>(error.code().value());
    }
    catch (const std::runtime_error &) {
        // image_export_dir throws this one rather than a system_error.
        sink += 1;
    }

    // The same sequence again through the non-throwing overloads, which are
    // separate bodies with their own error propagation rather than wrappers.
    std::error_code ec;
    const auto ntdll = wow64pp::module_handle(name ? name : "ntdll.dll", ec);
    sink += ntdll;
    sink += wow64pp::import(ntdll, "LdrLoadDll", ec);
    sink += static_cast<std::uint64_t>(ec.value());

    // The detail:: layer directly, so its bodies have real call sites and are
    // not only reachable through the four functions above.
    sink += detail::peb_address(ec);
    sink += reinterpret_cast<std::uint32_t>(detail::self_handle(ec));
    sink += reinterpret_cast<std::uint32_t>(
        detail::native_module_handle("ntdll.dll", ec));
    sink += reinterpret_cast<std::uint32_t>(
        detail::native_ntdll_function<defs::NtWow64ReadVirtualMemory64T>(
            "NtWow64ReadVirtualMemory64", ec));

    // Drives the read_memory instantiations for the loader structures, which
    // is the 64-bit PEB walk module_handle is built out of.
    const auto peb = detail::read_memory<defs::PEB_64>(detail::peb_address(ec), ec);
    sink += peb.Ldr;
    const auto ldr = detail::read_memory<defs::PEB_LDR_DATA_64>(peb.Ldr, ec);
    sink += ldr.InLoadOrderModuleList.Flink;
    defs::LDR_DATA_TABLE_ENTRY_64 entry = {};
    detail::read_memory(ldr.InLoadOrderModuleList.Flink, &entry, sizeof(entry), ec);
    sink += entry.DllBase;

    // The x64 ntdll export-directory parse, which is how the library reaches
    // LdrGetProcedureAddress without a 64-bit GetProcAddress.
    const auto exports = detail::image_export_dir(entry.DllBase, ec);
    sink += exports.NumberOfNames;
    sink += detail::ldr_procedure_address(ec);

    return sink;
}
