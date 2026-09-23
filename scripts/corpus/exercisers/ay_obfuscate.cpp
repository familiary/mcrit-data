// Instantiates adamyaxley/Obfuscate so its code is actually emitted.
//
// The library is a single header whose whole machinery is constexpr: nothing
// of it exists in a binary until a translation unit expands AY_OBFUSCATE, and
// even then only the runtime half survives. There is therefore no upstream
// artefact to disassemble, and the only way to get reference data is to
// compile a unit that uses the macro. The functions that land in the binary
// are the library's own; this file only decides which ones get instantiated.
//
// Two properties of the header dictate the shape of this file.
//
// The obfuscated_data class is templated on <N, KEY, CHAR_TYPE> and the
// default key is ay::generate_key(__LINE__), so the instantiation is keyed on
// the source line. Two AY_OBFUSCATE calls sharing a line and a length collapse
// into one instantiation - measured: sixteen strings on one line emitted the
// same code as one. Every call below therefore sits on its own line.
//
// The emitted code is the four members that cannot run at compile time -
// the lambda, the constructor, the destructor and operator CHAR_TYPE*, plus
// decrypt() - against one shared ay::cipher<CHAR_TYPE>. Measured with GCC at
// -O0: 5 functions per string plus 1 shared, so 16 strings gave 81 functions.
//
// Lengths are spread from 2 to ~90 characters because N is a template
// parameter: the copy and cipher loops are unrolled per length, so short and
// long strings are genuinely different code rather than the same body twice.

#include <obfuscate.h>

namespace {

int narrow_sum(const char *text)
{
    int sum = 0;
    while (*text) {
        sum += static_cast<unsigned char>(*text++);
    }
    return sum;
}

int wide_sum(const wchar_t *text)
{
    int sum = 0;
    while (*text) {
        sum += static_cast<int>(static_cast<unsigned>(*text++));
    }
    return sum;
}

}  // namespace

extern "C" __declspec(dllexport) int exercise(void)
{
    int sink = 0;

    // Strings a real consumer hides: paths, registry keys, URLs, API names,
    // command fragments and messages. One per line, see the note above.
    sink += narrow_sum(AY_OBFUSCATE("a"));
    sink += narrow_sum(AY_OBFUSCATE("ok"));
    sink += narrow_sum(AY_OBFUSCATE("GET"));
    sink += narrow_sum(AY_OBFUSCATE("POST"));
    sink += narrow_sum(AY_OBFUSCATE("https"));
    sink += narrow_sum(AY_OBFUSCATE("Sleep0"));
    sink += narrow_sum(AY_OBFUSCATE("winhttp"));
    sink += narrow_sum(AY_OBFUSCATE("kernel32"));
    sink += narrow_sum(AY_OBFUSCATE("advapi32.d"));
    sink += narrow_sum(AY_OBFUSCATE("VirtualAlloc"));
    sink += narrow_sum(AY_OBFUSCATE("CreateFileMappingA"));
    sink += narrow_sum(AY_OBFUSCATE("NtQuerySystemInformation"));
    sink += narrow_sum(AY_OBFUSCATE("SeDebugPrivilege enabled"));
    sink += narrow_sum(AY_OBFUSCATE("SOFTWARE\\Microsoft\\Windows"));
    sink += narrow_sum(AY_OBFUSCATE("C:\\Windows\\System32\\cmd.exe"));
    sink += narrow_sum(AY_OBFUSCATE("HKEY_LOCAL_MACHINE\\SYSTEM\\Setup"));
    sink += narrow_sum(AY_OBFUSCATE("https://example.invalid/collect/v1"));
    sink += narrow_sum(AY_OBFUSCATE("Content-Type: application/octet-stream"));
    sink += narrow_sum(AY_OBFUSCATE("Mozilla/5.0 (Windows NT 10.0; Win64; x64)"));
    sink += narrow_sum(AY_OBFUSCATE("SELECT name, value FROM settings WHERE id = ?"));
    sink += narrow_sum(AY_OBFUSCATE("\\\\.\\pipe\\a-named-pipe-whose-name-is-long-enough"));
    sink += narrow_sum(AY_OBFUSCATE("the quick brown fox jumps over the lazy dog, twice over"));
    sink += narrow_sum(AY_OBFUSCATE("an error occurred while decrypting the configuration blob"));
    sink += narrow_sum(AY_OBFUSCATE("-----BEGIN CERTIFICATE----- not really a certificate at all"));
    sink += narrow_sum(AY_OBFUSCATE("a considerably longer literal, present so the unrolled cipher loop is large"));
    sink += narrow_sum(AY_OBFUSCATE("and one longer still, so that the copy and the cipher loops differ in length again"));

    // Explicit keys, the AY_OBFUSCATE_KEY half of the API. The key has to
    // span all eight bytes or the header's own static_assert rejects it.
    sink += narrow_sum(AY_OBFUSCATE_KEY("explicit key, short", 0xA1B2C3D4E5F60718ull));
    sink += narrow_sum(AY_OBFUSCATE_KEY("explicit key, a rather longer literal", 0xFEDCBA9876543210ull));
    sink += narrow_sum(AY_OBFUSCATE_KEY("explicit key on a third distinct length, longer again", 0x8877665544332211ull));

    // wchar_t instantiates a second ay::cipher<> and a second family of
    // obfuscated_data members; the Windows API surface is wide, so a real
    // consumer hits this path.
    sink += wide_sum(AY_OBFUSCATE(L"wide"));
    sink += wide_sum(AY_OBFUSCATE(L"LdrLoadDll"));
    sink += wide_sum(AY_OBFUSCATE(L"C:\\ProgramData\\cache.bin"));
    sink += wide_sum(AY_OBFUSCATE(L"\\Registry\\Machine\\System\\CurrentControlSet"));

    // decrypt()/encrypt()/is_encrypted() are the manual half of the runtime
    // API and are not reached through the implicit char* conversion.
    auto &manual = AY_OBFUSCATE("manual decrypt and re-encrypt cycle");
    manual.decrypt();
    sink += manual.is_encrypted() ? 1 : 0;
    sink += narrow_sum(manual);
    manual.encrypt();
    sink += manual.is_encrypted() ? 2 : 0;

    auto &manual_wide = AY_OBFUSCATE(L"manual wide decrypt and re-encrypt cycle");
    manual_wide.decrypt();
    sink += manual_wide.is_encrypted() ? 1 : 0;
    sink += wide_sum(manual_wide);
    manual_wide.encrypt();

    return sink;
}
