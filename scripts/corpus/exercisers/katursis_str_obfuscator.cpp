// Instantiates katursis/StringObfuscator so its code is actually emitted.
//
// A single header whose encryption runs in constexpr: nothing of it exists in
// a binary until a translation unit calls cryptor::create(), so there is no
// upstream artefact to disassemble and the reference data comes from
// compiling this consumer.
//
// The file is laid out the way it is because of one design fact:
// string_encryptor is templated on the buffer size alone
// (`template <std::size_t S> class string_encryptor`, with the XOR key being
// S % 255). N obfuscated strings therefore do NOT give N functions - they
// give one function per distinct *length*. Everything below is therefore a
// sweep of distinct lengths, 4 through 63 characters, and the two extra
// literals at the end share a length already covered to keep the property
// visible: measured with GCC 13 at -O2, the sixty lengths emit exactly sixty
// decrypt() bodies and the two duplicates add none.
//
// decrypt() is the only member that survives, because it is the only one
// carrying __attribute__((noinline)) - which upstream applies under
// `#ifdef __GNUC__`. The constructor and detail::encryptor<> are constexpr
// and always_inline and evaporate into the caller.
//
// This unit is built at -O2, the opposite of the other string obfuscators in
// this corpus: upstream's README states "Requirements - O2", and it means it.
// At -O0 the obfuscation does not happen at all and the literals sit in the
// image in clear text.
//
// str_obfuscator.hpp is not self-contained: it names std::size_t and includes
// nothing at all, so <cstddef> has to come first.

#include "corpus_export.h"

#include <cstddef>

#include "str_obfuscator.hpp"

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

// cryptor::create() returns the string_encryptor by value and decrypt()
// hands back a pointer into it, so the object has to be alive when the
// pointer is read: every use is a single full expression.
extern "C" CORPUS_EXPORT int exercise(void)
{
    int sink = 0;

    sink += narrow_sum(cryptor::create("unlo").decrypt());  // 4
    sink += narrow_sum(cryptor::create("hash ").decrypt());  // 5
    sink += narrow_sum(cryptor::create("unwrap").decrypt());  // 6
    sink += narrow_sum(cryptor::create("seek te").decrypt());  // 7
    sink += narrow_sum(cryptor::create("chown so").decrypt());  // 8
    sink += narrow_sum(cryptor::create("recv shut").decrypt());  // 9
    sink += narrow_sum(cryptor::create("unmap lock").decrypt());  // 10
    sink += narrow_sum(cryptor::create("kill reap h").decrypt());  // 11
    sink += narrow_sum(cryptor::create("derive wrap ").decrypt());  // 12
    sink += narrow_sum(cryptor::create("close flush s").decrypt());  // 13
    sink += narrow_sum(cryptor::create("rmdir chmod ch").decrypt());  // 14
    sink += narrow_sum(cryptor::create("connect send re").decrypt());  // 15
    sink += narrow_sum(cryptor::create("free map unmap l").decrypt());  // 16
    sink += narrow_sum(cryptor::create("spawn exec kill r").decrypt());  // 17
    sink += narrow_sum(cryptor::create("encrypt decrypt de").decrypt());  // 18
    sink += narrow_sum(cryptor::create("read write close fl").decrypt());  // 19
    sink += narrow_sum(cryptor::create("link mkdir rmdir chm").decrypt());  // 20
    sink += narrow_sum(cryptor::create("listen accept connect").decrypt());  // 21
    sink += narrow_sum(cryptor::create("poll alloc free map un").decrypt());  // 22
    sink += narrow_sum(cryptor::create("wait signal spawn exec ").decrypt());  // 23
    sink += narrow_sum(cryptor::create("sign verify encrypt decr").decrypt());  // 24
    sink += narrow_sum(cryptor::create("seal open read write clos").decrypt());  // 25
    sink += narrow_sum(cryptor::create("tell stat link mkdir rmdir").decrypt());  // 26
    sink += narrow_sum(cryptor::create("socket bind listen accept c").decrypt());  // 27
    sink += narrow_sum(cryptor::create("shutdown select poll alloc f").decrypt());  // 28
    sink += narrow_sum(cryptor::create("lock unlock wait signal spawn").decrypt());  // 29
    sink += narrow_sum(cryptor::create("reap hash sign verify encrypt ").decrypt());  // 30
    sink += narrow_sum(cryptor::create("wrap unwrap seal open read writ").decrypt());  // 31
    sink += narrow_sum(cryptor::create("flush seek tell stat link mkdir ").decrypt());  // 32
    sink += narrow_sum(cryptor::create("chmod chown socket bind listen ac").decrypt());  // 33
    sink += narrow_sum(cryptor::create("send recv shutdown select poll all").decrypt());  // 34
    sink += narrow_sum(cryptor::create("map unmap lock unlock wait signal s").decrypt());  // 35
    sink += narrow_sum(cryptor::create("exec kill reap hash sign verify encr").decrypt());  // 36
    sink += narrow_sum(cryptor::create("decrypt derive wrap unwrap seal open ").decrypt());  // 37
    sink += narrow_sum(cryptor::create("write close flush seek tell stat link ").decrypt());  // 38
    sink += narrow_sum(cryptor::create("mkdir rmdir chmod chown socket bind lis").decrypt());  // 39
    sink += narrow_sum(cryptor::create("accept connect send recv shutdown select").decrypt());  // 40
    sink += narrow_sum(cryptor::create("alloc free map unmap lock unlock wait sig").decrypt());  // 41
    sink += narrow_sum(cryptor::create("signal spawn exec kill reap hash sign veri").decrypt());  // 42
    sink += narrow_sum(cryptor::create("verify encrypt decrypt derive wrap unwrap s").decrypt());  // 43
    sink += narrow_sum(cryptor::create("open read write close flush seek tell stat l").decrypt());  // 44
    sink += narrow_sum(cryptor::create("stat link mkdir rmdir chmod chown socket bind").decrypt());  // 45
    sink += narrow_sum(cryptor::create("bind listen accept connect send recv shutdown ").decrypt());  // 46
    sink += narrow_sum(cryptor::create("select poll alloc free map unmap lock unlock wa").decrypt());  // 47
    sink += narrow_sum(cryptor::create("unlock wait signal spawn exec kill reap hash sig").decrypt());  // 48
    sink += narrow_sum(cryptor::create("hash sign verify encrypt decrypt derive wrap unwr").decrypt());  // 49
    sink += narrow_sum(cryptor::create("unwrap seal open read write close flush seek tell ").decrypt());  // 50
    sink += narrow_sum(cryptor::create("seek tell stat link mkdir rmdir chmod chown socket ").decrypt());  // 51
    sink += narrow_sum(cryptor::create("chown socket bind listen accept connect send recv sh").decrypt());  // 52
    sink += narrow_sum(cryptor::create("recv shutdown select poll alloc free map unmap lock u").decrypt());  // 53
    sink += narrow_sum(cryptor::create("unmap lock unlock wait signal spawn exec kill reap has").decrypt());  // 54
    sink += narrow_sum(cryptor::create("kill reap hash sign verify encrypt decrypt derive wrap ").decrypt());  // 55
    sink += narrow_sum(cryptor::create("derive wrap unwrap seal open read write close flush seek").decrypt());  // 56
    sink += narrow_sum(cryptor::create("close flush seek tell stat link mkdir rmdir chmod chown s").decrypt());  // 57
    sink += narrow_sum(cryptor::create("rmdir chmod chown socket bind listen accept connect send r").decrypt());  // 58
    sink += narrow_sum(cryptor::create("connect send recv shutdown select poll alloc free map unmap").decrypt());  // 59
    sink += narrow_sum(cryptor::create("free map unmap lock unlock wait signal spawn exec kill reap ").decrypt());  // 60
    sink += narrow_sum(cryptor::create("spawn exec kill reap hash sign verify encrypt decrypt derive ").decrypt());  // 61
    sink += narrow_sum(cryptor::create("encrypt decrypt derive wrap unwrap seal open read write close ").decrypt());  // 62
    sink += narrow_sum(cryptor::create("read write close flush seek tell stat link mkdir rmdir chmod ch").decrypt());  // 63

    // The same length twice, to keep the collapsing property visible in the
    // data: these two share string_encryptor<32> with the sweep entry above
    // and add no new function.
    sink += narrow_sum(cryptor::create("a thirty-one character literal!").decrypt());
    sink += narrow_sum(cryptor::create("another one of the same length.").decrypt());

    return sink;
}
