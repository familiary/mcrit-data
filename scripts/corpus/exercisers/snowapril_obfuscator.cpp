// Instantiates Snowapril/String-Obfuscator-In-Compile-Time so its code is
// actually emitted.
//
// Two headers, no build system, and the whole cipher runs in the type system:
// nothing of the library exists in a binary until a translation unit expands
// OBFUSCATE. There is therefore no upstream artefact to disassemble, and the
// reference data comes from compiling this consumer.
//
// Three properties of the header dictate the shape of this file.
//
// OBFUSCATE(str) builds a snowapril::MetaString temporary and returns
// decrypt()'s char* out of it. The temporary dies at the end of the full
// expression, so the pointer must be consumed inside the same expression -
// assigning it to a `const char*` variable and using it on the next line is a
// dangling read. Every use below is therefore a single call expression.
//
// MetaString is templated on <index_sequence<I...>, A, B>, where A and B come
// from MetaRandom<__COUNTER__, ...>. __COUNTER__ advances twice per macro
// expansion, so every call is its own instantiation even at the same length,
// and lengths are spread anyway because the decrypt loop is bounded by
// sizeof...(I).
//
// MetaRandom drives LinearCongruentialEngine<16807, N, seed, Limit>, which
// recurses N times, and N is __COUNTER__ - so template instantiation depth
// grows at roughly twice the number of OBFUSCATE calls in the unit. GCC's
// default -ftemplate-depth is 900, which caps a single translation unit at
// about 450 strings; the 40 below stay far under that.
//
// Measured with GCC 13 at -O0: 4 functions per string (the constructor, the
// public decrypt(), and the private encrypt(char)/decrypt(int) pair) plus one
// shared snowapril::positive_modulo. At -O1 and -O2 the count is zero -
// everything folds into the caller.

// obfuscator.hpp is not self-contained: it declares
// `template <size_t... I, ...>` with an unqualified size_t and includes only
// <array> and its own meta_random.hpp, neither of which is guaranteed to
// declare ::size_t. GCC 13 with mingw-w64 headers rejects it on its own, so
// the consumer has to provide the declaration - including <cstddef> first is
// enough.
#include <cstddef>

#include <obfuscator.hpp>

namespace {

int narrow_sum(const char *text)
{
    int sum = 0;
    while (*text) {
        sum += static_cast<unsigned char>(*text++);
    }
    return sum;
}

}  // namespace

extern "C" __declspec(dllexport) int exercise(void)
{
    int sink = 0;

    sink += narrow_sum(OBFUSCATE("a"));
    sink += narrow_sum(OBFUSCATE("id"));
    sink += narrow_sum(OBFUSCATE("key"));
    sink += narrow_sum(OBFUSCATE("host"));
    sink += narrow_sum(OBFUSCATE("token"));
    sink += narrow_sum(OBFUSCATE("secret"));
    sink += narrow_sum(OBFUSCATE("session"));
    sink += narrow_sum(OBFUSCATE("user32.d"));
    sink += narrow_sum(OBFUSCATE("ntdll.dll"));
    sink += narrow_sum(OBFUSCATE("kernel32.dl"));
    sink += narrow_sum(OBFUSCATE("VirtualAlloc"));
    sink += narrow_sum(OBFUSCATE("LoadLibraryExA"));
    sink += narrow_sum(OBFUSCATE("GetProcAddress()"));
    sink += narrow_sum(OBFUSCATE("CreateRemoteThread"));
    sink += narrow_sum(OBFUSCATE("NtQueryInformationF"));
    sink += narrow_sum(OBFUSCATE("SeShutdownPrivilege!!"));
    sink += narrow_sum(OBFUSCATE("\\Device\\HarddiskVolume"));
    sink += narrow_sum(OBFUSCATE("SOFTWARE\\Classes\\CLSID"));
    sink += narrow_sum(OBFUSCATE("C:\\Windows\\Temp\\stage.dat"));
    sink += narrow_sum(OBFUSCATE("HKCU\\Environment\\UserInitMpr"));
    sink += narrow_sum(OBFUSCATE("https://example.invalid/beacon"));
    sink += narrow_sum(OBFUSCATE("Accept-Encoding: identity, gzip"));
    sink += narrow_sum(OBFUSCATE("cmd.exe /c whoami /groups > NUL 2>&1"));
    sink += narrow_sum(OBFUSCATE("the configuration could not be decoded"));
    sink += narrow_sum(OBFUSCATE("SELECT id, blob FROM records ORDER BY id"));
    sink += narrow_sum(OBFUSCATE("Mozilla/5.0 (Windows NT 10.0; Win64; x64)"));
    sink += narrow_sum(OBFUSCATE("\\\\.\\pipe\\a-pipe-name-long-enough-to-differ"));
    sink += narrow_sum(OBFUSCATE("a literal chosen only for its length, forty-six"));
    sink += narrow_sum(OBFUSCATE("another literal, longer again, so the loop bound moves"));
    sink += narrow_sum(OBFUSCATE("and a third, longer still, keeping the unrolled bodies apart"));

    // The TEST macro is the other half of the public surface: it hands back
    // the MetaString itself rather than the decrypted pointer, so decrypt()
    // is called by the consumer. The object has to outlive the call, which is
    // exactly why OBFUSCATE's temporary cannot be stored the same way.
    auto held = TEST("held as an object, decrypted by the caller");
    sink += narrow_sum(held.decrypt());

    auto held_short = TEST("held, short");
    sink += narrow_sum(held_short.decrypt());
    // Decrypting twice re-runs the loop over the already-decrypted buffer,
    // which is the library's documented behaviour and a path a consumer hits.
    sink += narrow_sum(held_short.decrypt());

    return sink;
}
