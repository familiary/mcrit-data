// Instantiates SaulBerrenson/WinApiObfuscator so its code is actually emitted.
//
// The project is one 278-line header, winapi_import.hpp, with no build system
// of any kind: nothing of it exists in a binary until a translation unit uses
// it, so there is no upstream artefact to disassemble. The functions that land
// in the binary are the library's own; this file only decides which ones get
// instantiated.
//
// THIS MUST STAY A SINGLE TRANSLATION UNIT. win_api::detail::murmur_hash2_a
// and win_api::detail::parse_export_table are defined in the header as plain
// non-inline, non-static free functions with external linkage. Two translation
// units including winapi_import.hpp produce LNK2005 on both of them. That is
// an upstream property, not something this file works around - and it is also
// why those two are the only functions here that exist without a template
// argument.
//
// What is instantiated per distinct T, read out of the header rather than
// guessed: win_api::get<T>, win_api_import<T>'s constructor, get_function()
// and get_modules(), and seven members of the nested function_holder - the
// default constructor, the (HMODULE, T*) constructor, the move constructor,
// the move assignment operator, the destructor, cleanup() and
// explicit operator bool - plus one instantiation of the variadic
// operator()(Args&&...) per distinct argument pack. That is roughly twelve
// functions for each T at /Od, so twelve distinct T should be about 145
// functions, against MIN_USEFUL_FUNCTIONS = 8. Both of those are arithmetic
// over the header, not a count taken off an artefact: MSVC does not exist in
// the container this was written in.
//
// Twelve distinct T rather than three because the recipe builds at /Od (see
// winapi_obfuscator_msvc.py), and even there the margin is deliberate: at /O2
// most of function_holder is expected to collapse into its callers, and how
// much would survive is exactly what has not been measured.

#include "winapi_import.hpp"

#include <type_traits>
#include <utility>

namespace {

// win_api_import<T> stores a T* and does reinterpret_cast<T*>, so T is a
// function type rather than a function pointer. The pointer spelling
// "R(WINAPI *)(args)" is the one the header itself uses for t_load_library and
// is unambiguously accepted; the bare function-type spelling with a calling
// convention inside parentheses is not portable across front ends. Writing the
// pointer and removing the pointer again gets the function type, calling
// convention included, without relying on that spelling.
template<class Ptr>
using fn_t = std::remove_pointer_t<Ptr>;

// Twelve signatures that are pairwise distinct as types, so each one is a
// separate instantiation rather than a second name for the same code. They are
// the APIs this library exists to hide: module loading, export resolution,
// memory allocation, file and handle work, and a couple of user32 entries.
using t_load_library      = fn_t<HMODULE(WINAPI *)(LPCSTR)>;
using t_get_proc_address  = fn_t<FARPROC(WINAPI *)(HMODULE, LPCSTR)>;
using t_free_library      = fn_t<BOOL(WINAPI *)(HMODULE)>;
using t_sleep             = fn_t<void(WINAPI *)(DWORD)>;
using t_virtual_alloc     = fn_t<LPVOID(WINAPI *)(LPVOID, SIZE_T, DWORD, DWORD)>;
using t_virtual_free      = fn_t<BOOL(WINAPI *)(LPVOID, SIZE_T, DWORD)>;
using t_create_file       = fn_t<HANDLE(WINAPI *)(LPCSTR, DWORD, DWORD,
                                                  LPSECURITY_ATTRIBUTES, DWORD,
                                                  DWORD, HANDLE)>;
using t_write_file        = fn_t<BOOL(WINAPI *)(HANDLE, LPCVOID, DWORD, LPDWORD,
                                                LPOVERLAPPED)>;
using t_close_handle      = fn_t<BOOL(WINAPI *)(HANDLE)>;
using t_output_debug      = fn_t<void(WINAPI *)(LPCSTR)>;
using t_message_box       = fn_t<int(WINAPI *)(HWND, LPCSTR, LPCSTR, UINT)>;
using t_get_system_metric = fn_t<int(WINAPI *)(int)>;

} // namespace

// A macro rather than a function template on purpose. A helper template would
// itself be instantiated once per T and would put twelve functions of this
// exerciser's own into an artefact filed under the WinApiObfuscator family; a
// macro expands into exercise() and leaves only upstream code behind.
//
// The sequence is the whole life cycle of a resolved import: resolve it, test
// it, call it, move it, move-assign it over another holder, and let both
// destructors run cleanup(). win_api::get returns a prvalue, so C++17's
// guaranteed elision means the move constructor is never used on that path -
// hence the explicit std::move into `moved`, and the default-constructed
// `spare` that the move assignment operator needs as a target.
#define WAO_EXERCISE(alias, api, dll, seed, ...)                              \
    do {                                                                      \
        auto holder = win_api::get<alias>(api, dll, seed);                    \
        sink += holder ? 1 : 0;                                               \
        if (holder) {                                                         \
            (void)holder(__VA_ARGS__);                                        \
        }                                                                     \
        auto moved = std::move(holder);                                       \
        win_api::win_api_import<alias>::function_holder spare;                \
        sink += spare ? 1 : 0;                                                \
        spare = std::move(moved);                                             \
    } while (0)

extern "C" __declspec(dllexport) int exercise(const char *api_name)
{
    int sink = 0;

    // The two functions that exist once rather than once per T. Both are
    // reached through win_api::get below as well; calling them directly is
    // what makes the hash and the export-table walk legible in the report
    // independently of any instantiation. parse_export_table returns early on
    // a null module, so this is a safe call even if the DLL is ever loaded.
    sink += static_cast<int>(win_api::detail::murmur_hash2_a(api_name, 4, 7));
    sink += win_api::detail::parse_export_table(nullptr, 0u, 4, 7) ? 1 : 0;

    // seed 0 is the documented default and makes win_api_import use the name
    // length as the seed; the explicit seeds exercise the other branch of that
    // ternary. Neither changes the code that is emitted, only which constant
    // the constructor stores.
    WAO_EXERCISE(t_load_library, "LoadLibraryA", "kernel32.dll", 0, nullptr);
    WAO_EXERCISE(t_get_proc_address, "GetProcAddress", "kernel32.dll", 10,
                 nullptr, api_name);
    WAO_EXERCISE(t_free_library, "FreeLibrary", "kernel32.dll", 0, nullptr);
    WAO_EXERCISE(t_sleep, "Sleep", "kernel32.dll", 0, 0);
    WAO_EXERCISE(t_virtual_alloc, "VirtualAlloc", "kernel32.dll", 0,
                 nullptr, 0, 0, 0);
    WAO_EXERCISE(t_virtual_free, "VirtualFree", "kernel32.dll", 4919,
                 nullptr, 0, 0);
    WAO_EXERCISE(t_create_file, "CreateFileA", "kernel32.dll", 0,
                 nullptr, 0, 0, nullptr, 0, 0, nullptr);
    WAO_EXERCISE(t_write_file, "WriteFile", "kernel32.dll", 0,
                 nullptr, nullptr, 0, nullptr, nullptr);
    WAO_EXERCISE(t_close_handle, "CloseHandle", "kernel32.dll", 0, nullptr);
    WAO_EXERCISE(t_output_debug, "OutputDebugStringA", "kernel32.dll", 0,
                 nullptr);
    WAO_EXERCISE(t_message_box, "MessageBoxA", "user32.dll", 0,
                 nullptr, nullptr, nullptr, 0u);
    WAO_EXERCISE(t_get_system_metric, "GetSystemMetrics", "user32.dll", 3,
                 0);

    // The two-step form the README documents, beside the win_api::get
    // shorthand every line above uses. It reaches the same win_api_import<T>
    // members, but through the class rather than the helper, which is how a
    // consumer that wants to keep the importer around writes it.
    win_api::win_api_import<t_get_proc_address> importer(
        "GetProcAddress", "kernel32.dll", 1337);
    auto resolved = importer.get_function();
    sink += resolved ? 1 : 0;

    return sink;
}
