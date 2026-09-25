//! Instantiates CasualX/obfstr so its code is actually emitted.
//!
//! obfstr is a compiletime string obfuscator: the encoding runs in `const`
//! context and the decoder is generated per call site, so nothing of the
//! crate exists in a binary until something uses the macros. There is no
//! upstream artefact to disassemble and the reference data comes from
//! compiling this consumer.
//!
//! What lands in the image is `obfstr::xref::inner::<SEED>`, which upstream
//! marks `#[inline(never)]` and which is generic over `const SEED: u64`. One
//! monomorphisation is emitted per obfuscated item, in debug and release
//! alike, and each one is a different shape because the seed selects the
//! `obfchoice` arms and drives the `obfstmt!` control-flow flattening around
//! them. Everything else - the keystream generation, the per-byte decode
//! loops - is `#[inline(always)]` and folds into the caller.
//!
//! The crate is `#![no_std]`. This matters for the corpus, not for obfstr:
//! a normal Rust cdylib links thousands of Rust std and core functions into
//! the image, and every one of them would be filed under obfstr's family
//! name - the same trap the nlohmann recipe records for -static-libstdc++.
//! obfstr itself is `#![cfg_attr(not(test), no_std)]` and has no
//! dependencies, so a no_std driver costs nothing in coverage. Measured: the
//! x64 release DLL contains obfstr's monomorphisations, this file's three
//! functions and the mingw-w64 C runtime, and no Rust std symbol at all.
//!
//! `obfstring!` is the one public macro not exercised here: it is
//! `String::from(obfstr!(..))` and needs an allocator, which a no_std driver
//! does not have. It adds no obfstr code of its own beyond the `obfstr!` it
//! wraps.
//!
//! Every obfuscating macro yields a temporary that must be consumed in the
//! statement that produced it, so each use below is a single expression.

#![no_std]

use core::panic::PanicInfo;

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {}
}

/// Consumes a decoded buffer so the call cannot be optimised away.
fn sum(bytes: &[u8]) -> u32 {
    let mut total = 0u32;
    let mut index = 0;
    while index < bytes.len() {
        total = total.wrapping_add(bytes[index] as u32);
        index += 1;
    }
    total
}

/// Consumes a decoded utf16 buffer, the `obfwide!`/`wide!` half of the API.
fn sum_wide(words: &[u16]) -> u32 {
    let mut total = 0u32;
    let mut index = 0;
    while index < words.len() {
        total = total.wrapping_add(words[index] as u32);
        index += 1;
    }
    total
}

// Static data for the xref! macro, which obfuscates the reference to a
// 'static item rather than the item's contents.
static TABLE: [u32; 8] = [3, 5, 7, 11, 13, 17, 19, 23];
static BANNER: &str = "a static string reached through an obfuscated xref";
static MAGIC: [u8; 8] = [0x4d, 0x5a, 0x90, 0x00, 0x03, 0x00, 0x00, 0x00];

#[unsafe(no_mangle)]
pub extern "C" fn exercise() -> u32 {
    let mut sink = 0u32;

    // obfstr! - the headline macro. Lengths are spread because the decode
    // loop is const-sized, and each call gets its own seed from file!(),
    // line!() and column!().
    sink = sink.wrapping_add(sum(obfstr::obfstr!("a").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("id").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("ntdll.dll").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("kernel32.dll").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("VirtualAllocEx").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("NtCreateThreadEx").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("SeDebugPrivilege").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("C:\\Windows\\System32").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("SOFTWARE\\Microsoft\\Windows").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("https://example.invalid/collect").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("Content-Type: application/json").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("Mozilla/5.0 (Windows NT 10.0; Win64)").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("the configuration blob failed to decode").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("a literal long enough that the decode loop is unrolled wide").as_bytes()));
    // Non-ASCII: obfstr! works on the utf8 bytes, so a multibyte literal is
    // a different length to its character count.
    sink = sink.wrapping_add(sum(obfstr::obfstr!("Hello \u{1f30d} world").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("GET").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("POST").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("Authorization").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("advapi32.dll").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("RtlGetVersion").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("CreateRemoteThread").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("HKEY_CURRENT_USER\\Environment").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("cmd.exe /c whoami /groups").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("SELECT id, blob FROM records").as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfstr!("could not open the staging directory").as_bytes()));

    // obfcstr! - NUL-terminated, for FFI call sites.
    sink = sink.wrapping_add(sum(obfstr::obfcstr!(c"open").to_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfcstr!(c"LoadLibraryA").to_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfcstr!(c"\\\\.\\pipe\\named-pipe-example").to_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfcstr!(c"GetProcAddress").to_bytes()));
    sink = sink.wrapping_add(sum(obfstr::obfcstr!(c"/tmp/a-path-of-its-own-length").to_bytes()));

    // obfbytes! - raw byte strings, not required to be valid utf8.
    sink = sink.wrapping_add(sum(obfstr::obfbytes!(b"\x00\x01\x02\x03")));
    sink = sink.wrapping_add(sum(obfstr::obfbytes!(b"\xde\xad\xbe\xef\xca\xfe\xba\xbe")));
    sink = sink.wrapping_add(sum(obfstr::obfbytes!(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00")));

    // obfwide! - utf16, which is what the Windows API surface wants. This
    // goes through obfstr::words rather than obfstr::bytes and carries its
    // own keystream generator.
    sink = sink.wrapping_add(sum_wide(obfstr::obfwide!("wide")));
    sink = sink.wrapping_add(sum_wide(obfstr::obfwide!("LdrLoadDll")));
    sink = sink.wrapping_add(sum_wide(obfstr::obfwide!("C:\\ProgramData\\cache.bin")));
    sink = sink.wrapping_add(sum_wide(obfstr::obfwide!("\\Registry\\Machine\\System\\CurrentControlSet")));
    sink = sink.wrapping_add(sum_wide(obfstr::obfwide!("ntdll")));
    sink = sink.wrapping_add(sum_wide(obfstr::obfwide!("NtOpenProcessToken")));
    sink = sink.wrapping_add(sum_wide(obfstr::obfwide!("\\\\?\\GLOBALROOT\\Device\\HarddiskVolume1")));

    // xref! - obfuscates the reference itself, over several referent types:
    // a slice of a static array, a &'static str, a byte array and a single
    // element. The 'static nature of the data is preserved, which is the
    // lighter-weight alternative to obfstr!.
    sink = sink.wrapping_add(obfstr::xref!(&TABLE)[3]);
    sink = sink.wrapping_add(obfstr::xref!(&TABLE[..])[5]);
    sink = sink.wrapping_add(sum(obfstr::xref!(BANNER).as_bytes()));
    sink = sink.wrapping_add(sum(obfstr::xref!(&MAGIC)));
    sink = sink.wrapping_add(sum(obfstr::xref!(b"a byte string reached by xref")));
    sink = sink.wrapping_add(sum(obfstr::xref!("a str literal reached by xref").as_bytes()));

    // obfstmt! - control-flow flattening of a straight-line block into a
    // key-driven state machine. This one emits no xref::inner of its own;
    // it is the transformation the seeds above are threaded through.
    let mut value = 0i32;
    obfstr::obfstmt! {
        value = 5;
        value *= 24;
        value -= 10;
        value += 8;
        value *= 28;
        value -= 18;
        value += 1;
        value *= 21;
        value -= 11;
    }
    sink = sink.wrapping_add(value as u32);

    // The @seed form, so two otherwise identical blocks get different
    // control flow.
    let mut other = 1i32;
    obfstr::obfstmt! {
        @seed obfstr::random!(u32, "corpus");
        other *= 7;
        other += 3;
        other *= 5;
    }
    sink = sink.wrapping_add(other as u32);

    // random! and hash! are the compiletime primitives the rest is built
    // on; they fold to constants and emit nothing, but a consumer uses them
    // directly and they are part of the public surface.
    sink = sink.wrapping_add(obfstr::random!(u32));
    sink = sink.wrapping_add(obfstr::hash!("obfstr"));

    sink
}
