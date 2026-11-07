//! Instantiates orion-rs/orion so its code is actually emitted.
//!
//! orion is a library crate: nothing of it exists in a binary until something
//! calls into it, and most of it is generic or `#[inline]`. This driver
//! exports one `extern "C"` function per public primitive of orion's
//! `hazardous` module, each taking raw pointers and lengths from the caller
//! so the compiler can fold nothing away. See ../../recipes/orion.py.
//!
//! The crate is `#![no_std]`. orion's high-level API (`orion::aead`,
//! `orion::hash`, ...) requires the `safe_api` feature, which turns on `std`
//! and `getrandom`; a stock Rust cdylib with std links all of std statically
//! and every one of those functions would be filed under orion's family. The
//! `hazardous` module is where the cryptography lives - the high-level layer
//! is thin wrappers over it - and it is available without std. Argon2 and
//! scrypt need an allocator, hence `extern crate alloc` and the bump
//! allocator below, which is the driver's own code and keeps `std` out.
//!
//! Every exported function is named `orion_x_*` and marked `#[inline(never)]`
//! so the driver's own code in a report is identifiable by name. The orion
//! 0.18 additions (BLAKE3, scrypt, Argon2 variants) sit behind the driver's
//! own `v18` feature, which only the 0.18 manifest turns on.

#![no_std]
#![allow(unexpected_cfgs)]

extern crate alloc;

use core::alloc::{GlobalAlloc, Layout};
use core::cell::UnsafeCell;
use core::panic::PanicInfo;

use orion::errors::UnknownCryptoError;
use orion::hazardous::{aead, ecc, hash, kdf, mac, stream};

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {}
}

// The precompiled `core` is built with unwinding, so it references the
// unwind personality routine even though this crate aborts on panic and
// never unwinds. Without a definition the cdylib links on Linux but fails to
// load ("undefined symbol: rust_eh_personality"). These are never called.
#[cfg(not(target_env = "msvc"))]
#[unsafe(no_mangle)]
pub extern "C" fn rust_eh_personality() {}

#[cfg(target_env = "msvc")]
#[unsafe(no_mangle)]
pub extern "C" fn __CxxFrameHandler3() {}

// A bump allocator over a static arena. Argon2 and scrypt allocate their
// working memory with `Vec`; the arena is sized for the small parameters
// the driver passes.
const ARENA: usize = 1 << 22;

// The arena is aligned: the allocator hands out offsets into it, so its base
// has to carry the strictest alignment any allocation asks for.
#[repr(align(64))]
#[allow(dead_code)]
struct Arena([u8; ARENA]);

struct Bump {
    mem: UnsafeCell<Arena>,
    next: UnsafeCell<usize>,
}

unsafe impl Sync for Bump {}

unsafe impl GlobalAlloc for Bump {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let next = unsafe { &mut *self.next.get() };
        let start = (*next + layout.align() - 1) & !(layout.align() - 1);
        match start.checked_add(layout.size()) {
            Some(end) if end <= ARENA => {
                *next = end;
                unsafe { (self.mem.get() as *mut u8).add(start) }
            }
            _ => core::ptr::null_mut(),
        }
    }
    unsafe fn dealloc(&self, _ptr: *mut u8, _layout: Layout) {}
}

#[global_allocator]
static HEAP: Bump = Bump { mem: UnsafeCell::new(Arena([0; ARENA])), next: UnsafeCell::new(0) };

fn st<T>(r: Result<T, UnknownCryptoError>) -> i32 {
    if r.is_ok() { 0 } else { -1 }
}

unsafe fn i<'a>(p: *const u8, n: usize) -> &'a [u8] {
    unsafe { core::slice::from_raw_parts(p, n) }
}

unsafe fn o<'a>(p: *mut u8, n: usize) -> &'a mut [u8] {
    unsafe { core::slice::from_raw_parts_mut(p, n) }
}

unsafe fn opt<'a>(p: *const u8, n: usize) -> Option<&'a [u8]> {
    if p.is_null() { None } else { Some(unsafe { i(p, n) }) }
}

macro_rules! ex {
    ($(#[$m:meta])* fn $name:ident($($a:ident: $t:ty),*) -> i32 $body:block) => {
        $(#[$m])*
        #[unsafe(no_mangle)]
        #[inline(never)]
        pub unsafe extern "C" fn $name($($a: $t),*) -> i32 $body
    };
}

// -- AEAD and stream ciphers -----------------------------------------------

ex! { fn orion_x_chacha20poly1305_seal(key: *const u8, nonce: *const u8, pt: *const u8, ptl: usize,
        adp: *const u8, adl: usize, out: *mut u8, outl: usize) -> i32 {
    use aead::chacha20poly1305 as m;
    let Ok(k) = m::SecretKey::from_slice(unsafe { i(key, 32) }) else { return -2 };
    let Ok(n) = m::Nonce::from_slice(unsafe { i(nonce, 12) }) else { return -3 };
    st(m::seal(&k, &n, unsafe { i(pt, ptl) }, unsafe { opt(adp, adl) }, unsafe { o(out, outl) }))
} }

ex! { fn orion_x_chacha20poly1305_open(key: *const u8, nonce: *const u8, ct: *const u8, ctl: usize,
        adp: *const u8, adl: usize, out: *mut u8, outl: usize) -> i32 {
    use aead::chacha20poly1305 as m;
    let Ok(k) = m::SecretKey::from_slice(unsafe { i(key, 32) }) else { return -2 };
    let Ok(n) = m::Nonce::from_slice(unsafe { i(nonce, 12) }) else { return -3 };
    st(m::open(&k, &n, unsafe { i(ct, ctl) }, unsafe { opt(adp, adl) }, unsafe { o(out, outl) }))
} }

ex! { fn orion_x_xchacha20poly1305_seal(key: *const u8, nonce: *const u8, pt: *const u8, ptl: usize,
        adp: *const u8, adl: usize, out: *mut u8, outl: usize) -> i32 {
    use aead::xchacha20poly1305 as m;
    let Ok(k) = m::SecretKey::from_slice(unsafe { i(key, 32) }) else { return -2 };
    let Ok(n) = m::Nonce::from_slice(unsafe { i(nonce, 24) }) else { return -3 };
    st(m::seal(&k, &n, unsafe { i(pt, ptl) }, unsafe { opt(adp, adl) }, unsafe { o(out, outl) }))
} }

ex! { fn orion_x_xchacha20poly1305_open(key: *const u8, nonce: *const u8, ct: *const u8, ctl: usize,
        adp: *const u8, adl: usize, out: *mut u8, outl: usize) -> i32 {
    use aead::xchacha20poly1305 as m;
    let Ok(k) = m::SecretKey::from_slice(unsafe { i(key, 32) }) else { return -2 };
    let Ok(n) = m::Nonce::from_slice(unsafe { i(nonce, 24) }) else { return -3 };
    st(m::open(&k, &n, unsafe { i(ct, ctl) }, unsafe { opt(adp, adl) }, unsafe { o(out, outl) }))
} }

// The streaming AEAD: new, rekey, seal_chunk, open_chunk.
ex! { fn orion_x_stream_aead(key: *const u8, nonce: *const u8, pt: *const u8, ptl: usize,
        out: *mut u8, outl: usize, back: *mut u8, backl: usize) -> i32 {
    use aead::streaming as m;
    let Ok(k) = m::SecretKey::from_slice(unsafe { i(key, 32) }) else { return -2 };
    let Ok(n) = m::Nonce::from_slice(unsafe { i(nonce, 24) }) else { return -3 };
    let mut enc = m::StreamXChaCha20Poly1305::new(&k, &n);
    let mut dec = m::StreamXChaCha20Poly1305::new(&k, &n);
    let r = enc.seal_chunk(unsafe { i(pt, ptl) }, None, unsafe { o(out, outl) }, &m::StreamTag::Message);
    if r.is_err() { return -1; }
    let r = dec.open_chunk(unsafe { i(out, outl) }, None, unsafe { o(back, backl) });
    if r.is_err() { return -4; }
    if enc.rekey().is_err() { return -5; }
    let r = enc.seal_chunk(unsafe { i(pt, ptl) }, None, unsafe { o(out, outl) }, &m::StreamTag::Finish);
    st(r)
} }

ex! { fn orion_x_chacha20_encrypt(key: *const u8, nonce: *const u8, ctr: u32, pt: *const u8, ptl: usize,
        out: *mut u8, outl: usize) -> i32 {
    use stream::chacha20 as m;
    let Ok(k) = m::SecretKey::from_slice(unsafe { i(key, 32) }) else { return -2 };
    let Ok(n) = m::Nonce::from_slice(unsafe { i(nonce, 12) }) else { return -3 };
    st(m::encrypt(&k, &n, ctr, unsafe { i(pt, ptl) }, unsafe { o(out, outl) }))
} }

ex! { fn orion_x_chacha20_decrypt(key: *const u8, nonce: *const u8, ctr: u32, ct: *const u8, ctl: usize,
        out: *mut u8, outl: usize) -> i32 {
    use stream::chacha20 as m;
    let Ok(k) = m::SecretKey::from_slice(unsafe { i(key, 32) }) else { return -2 };
    let Ok(n) = m::Nonce::from_slice(unsafe { i(nonce, 12) }) else { return -3 };
    st(m::decrypt(&k, &n, ctr, unsafe { i(ct, ctl) }, unsafe { o(out, outl) }))
} }

ex! { fn orion_x_xchacha20_encrypt(key: *const u8, nonce: *const u8, ctr: u32, pt: *const u8, ptl: usize,
        out: *mut u8, outl: usize) -> i32 {
    use stream::{chacha20, xchacha20 as m};
    let Ok(k) = chacha20::SecretKey::from_slice(unsafe { i(key, 32) }) else { return -2 };
    let Ok(n) = m::Nonce::from_slice(unsafe { i(nonce, 24) }) else { return -3 };
    st(m::encrypt(&k, &n, ctr, unsafe { i(pt, ptl) }, unsafe { o(out, outl) }))
} }

ex! { fn orion_x_xchacha20_decrypt(key: *const u8, nonce: *const u8, ctr: u32, ct: *const u8, ctl: usize,
        out: *mut u8, outl: usize) -> i32 {
    use stream::{chacha20, xchacha20 as m};
    let Ok(k) = chacha20::SecretKey::from_slice(unsafe { i(key, 32) }) else { return -2 };
    let Ok(n) = m::Nonce::from_slice(unsafe { i(nonce, 24) }) else { return -3 };
    st(m::decrypt(&k, &n, ctr, unsafe { i(ct, ctl) }, unsafe { o(out, outl) }))
} }

// -- Hashes ----------------------------------------------------------------

// Both the one-shot and the streaming (new/update/finalize) paths.
macro_rules! hash_fns {
    ($one:ident, $stream:ident, $t:ty) => {
        ex! { fn $one(data: *const u8, n: usize, out: *mut u8) -> i32 {
            match <$t>::digest(unsafe { i(data, n) }) {
                Ok(d) => { unsafe { o(out, d.as_ref().len()) }.copy_from_slice(d.as_ref()); 0 }
                Err(_) => -1,
            }
        } }
        ex! { fn $stream(data: *const u8, n: usize, out: *mut u8) -> i32 {
            let mut s = <$t>::new();
            let d = unsafe { i(data, n) };
            let half = d.len() / 2;
            if s.update(&d[..half]).is_err() || s.update(&d[half..]).is_err() { return -1; }
            match s.finalize() {
                Ok(d) => { unsafe { o(out, d.as_ref().len()) }.copy_from_slice(d.as_ref()); 0 }
                Err(_) => -1,
            }
        } }
    };
}

hash_fns!(orion_x_sha256, orion_x_sha256_stream, hash::sha2::sha256::Sha256);
hash_fns!(orion_x_sha384, orion_x_sha384_stream, hash::sha2::sha384::Sha384);
hash_fns!(orion_x_sha512, orion_x_sha512_stream, hash::sha2::sha512::Sha512);
hash_fns!(orion_x_sha3_224, orion_x_sha3_224_stream, hash::sha3::sha3_224::Sha3_224);
hash_fns!(orion_x_sha3_256, orion_x_sha3_256_stream, hash::sha3::sha3_256::Sha3_256);
hash_fns!(orion_x_sha3_384, orion_x_sha3_384_stream, hash::sha3::sha3_384::Sha3_384);
hash_fns!(orion_x_sha3_512, orion_x_sha3_512_stream, hash::sha3::sha3_512::Sha3_512);

ex! { fn orion_x_blake2b(data: *const u8, n: usize, size: usize, out: *mut u8) -> i32 {
    use hash::blake2::blake2b::Blake2b;
    let d = unsafe { i(data, n) };
    let Ok(one) = Blake2b::new(size) else { return -2 };
    let mut one = one;
    let half = d.len() / 2;
    if one.update(&d[..half]).is_err() || one.update(&d[half..]).is_err() { return -1; }
    match one.finalize() {
        Ok(h) => { unsafe { o(out, h.as_ref().len()) }.copy_from_slice(h.as_ref()); 0 }
        Err(_) => -1,
    }
} }

ex! { fn orion_x_blake2b_oneshot(data: *const u8, n: usize, size: usize, out: *mut u8) -> i32 {
    use hash::blake2::blake2b::Hasher;
    let Ok(h) = Hasher::Blake2b512.digest(unsafe { i(data, n) }) else { return -1 };
    let Ok(h2) = Hasher::Blake2b256.digest(unsafe { i(data, n) }) else { return -1 };
    let _ = size;
    unsafe { o(out, 64) }.copy_from_slice(h.as_ref());
    unsafe { o(out.add(64), 32) }.copy_from_slice(h2.as_ref());
    0
} }

ex! { fn orion_x_shake128(data: *const u8, n: usize, out: *mut u8, outl: usize) -> i32 {
    use hash::sha3::shake128::Shake128;
    let mut s = Shake128::new();
    if s.absorb(unsafe { i(data, n) }).is_err() { return -1; }
    st(s.squeeze(unsafe { o(out, outl) }))
} }

ex! { fn orion_x_shake256(data: *const u8, n: usize, out: *mut u8, outl: usize) -> i32 {
    use hash::sha3::shake256::Shake256;
    let mut s = Shake256::new();
    if s.absorb(unsafe { i(data, n) }).is_err() { return -1; }
    st(s.squeeze(unsafe { o(out, outl) }))
} }

// -- MACs ------------------------------------------------------------------

ex! { fn orion_x_hmac_sha256(key: *const u8, kl: usize, data: *const u8, n: usize, out: *mut u8) -> i32 {
    use mac::hmac::sha256 as m;
    let Ok(k) = m::SecretKey::from_slice(unsafe { i(key, kl) }) else { return -2 };
    let Ok(t) = m::HmacSha256::hmac(&k, unsafe { i(data, n) }) else { return -1 };
    unsafe { o(out, 32) }.copy_from_slice(t.unprotected_as_bytes());
    let mut s = m::HmacSha256::new(&k);
    if s.update(unsafe { i(data, n) }).is_err() { return -1; }
    let Ok(t2) = s.finalize() else { return -1 };
    st(m::HmacSha256::verify(&t, &k, unsafe { i(data, n) }).and(Ok(t2)))
} }

ex! { fn orion_x_hmac_sha384(key: *const u8, kl: usize, data: *const u8, n: usize, out: *mut u8) -> i32 {
    use mac::hmac::sha384 as m;
    let Ok(k) = m::SecretKey::from_slice(unsafe { i(key, kl) }) else { return -2 };
    let Ok(t) = m::HmacSha384::hmac(&k, unsafe { i(data, n) }) else { return -1 };
    unsafe { o(out, 48) }.copy_from_slice(t.unprotected_as_bytes());
    let mut s = m::HmacSha384::new(&k);
    if s.update(unsafe { i(data, n) }).is_err() { return -1; }
    let Ok(t2) = s.finalize() else { return -1 };
    st(m::HmacSha384::verify(&t, &k, unsafe { i(data, n) }).and(Ok(t2)))
} }

ex! { fn orion_x_hmac_sha512(key: *const u8, kl: usize, data: *const u8, n: usize, out: *mut u8) -> i32 {
    use mac::hmac::sha512 as m;
    let Ok(k) = m::SecretKey::from_slice(unsafe { i(key, kl) }) else { return -2 };
    let Ok(t) = m::HmacSha512::hmac(&k, unsafe { i(data, n) }) else { return -1 };
    unsafe { o(out, 64) }.copy_from_slice(t.unprotected_as_bytes());
    let mut s = m::HmacSha512::new(&k);
    if s.update(unsafe { i(data, n) }).is_err() { return -1; }
    let Ok(t2) = s.finalize() else { return -1 };
    st(m::HmacSha512::verify(&t, &k, unsafe { i(data, n) }).and(Ok(t2)))
} }

ex! { fn orion_x_poly1305(key: *const u8, data: *const u8, n: usize, out: *mut u8) -> i32 {
    use mac::poly1305 as m;
    let Ok(k) = m::OneTimeKey::from_slice(unsafe { i(key, 32) }) else { return -2 };
    let Ok(t) = m::Poly1305::poly1305(&k, unsafe { i(data, n) }) else { return -1 };
    unsafe { o(out, 16) }.copy_from_slice(t.unprotected_as_bytes());
    let mut s = m::Poly1305::new(&k);
    if s.update(unsafe { i(data, n) }).is_err() { return -1; }
    let Ok(t2) = s.finalize() else { return -1 };
    st(m::Poly1305::verify(&t, &k, unsafe { i(data, n) }).and(Ok(t2)))
} }

ex! { fn orion_x_blake2b_mac(key: *const u8, kl: usize, data: *const u8, n: usize, size: usize, out: *mut u8) -> i32 {
    use mac::blake2b as m;
    let Ok(k) = m::SecretKey::from_slice(unsafe { i(key, kl) }) else { return -2 };
    let Ok(mut s) = m::Blake2b::new(&k, size) else { return -3 };
    if s.update(unsafe { i(data, n) }).is_err() { return -1; }
    let Ok(t) = s.finalize() else { return -1 };
    unsafe { o(out, t.unprotected_as_bytes().len()) }.copy_from_slice(t.unprotected_as_bytes());
    st(m::Blake2b::verify(&t, &k, size, unsafe { i(data, n) }))
} }

// -- KDFs ------------------------------------------------------------------

ex! { fn orion_x_hkdf_sha256(salt: *const u8, sl: usize, ikm: *const u8, il: usize, info: *const u8, nl: usize,
        out: *mut u8, outl: usize) -> i32 {
    use kdf::hkdf::sha256 as m;
    let Ok(prk) = m::extract(unsafe { i(salt, sl) }, unsafe { i(ikm, il) }) else { return -1 };
    if m::expand(&prk, unsafe { opt(info, nl) }, unsafe { o(out, outl) }).is_err() { return -2; }
    st(m::derive_key(unsafe { i(salt, sl) }, unsafe { i(ikm, il) }, unsafe { opt(info, nl) }, unsafe { o(out, outl) }))
} }

ex! { fn orion_x_hkdf_sha384(salt: *const u8, sl: usize, ikm: *const u8, il: usize, info: *const u8, nl: usize,
        out: *mut u8, outl: usize) -> i32 {
    use kdf::hkdf::sha384 as m;
    let Ok(prk) = m::extract(unsafe { i(salt, sl) }, unsafe { i(ikm, il) }) else { return -1 };
    if m::expand(&prk, unsafe { opt(info, nl) }, unsafe { o(out, outl) }).is_err() { return -2; }
    st(m::derive_key(unsafe { i(salt, sl) }, unsafe { i(ikm, il) }, unsafe { opt(info, nl) }, unsafe { o(out, outl) }))
} }

ex! { fn orion_x_hkdf_sha512(salt: *const u8, sl: usize, ikm: *const u8, il: usize, info: *const u8, nl: usize,
        out: *mut u8, outl: usize) -> i32 {
    use kdf::hkdf::sha512 as m;
    let Ok(prk) = m::extract(unsafe { i(salt, sl) }, unsafe { i(ikm, il) }) else { return -1 };
    if m::expand(&prk, unsafe { opt(info, nl) }, unsafe { o(out, outl) }).is_err() { return -2; }
    st(m::derive_key(unsafe { i(salt, sl) }, unsafe { i(ikm, il) }, unsafe { opt(info, nl) }, unsafe { o(out, outl) }))
} }

ex! { fn orion_x_pbkdf2_sha256(pw: *const u8, pl: usize, salt: *const u8, sl: usize, iters: usize,
        out: *mut u8, outl: usize) -> i32 {
    use kdf::pbkdf2::sha256 as m;
    let Ok(p) = m::Password::from_slice(unsafe { i(pw, pl) }) else { return -2 };
    if m::derive_key(&p, unsafe { i(salt, sl) }, iters, unsafe { o(out, outl) }).is_err() { return -1; }
    st(m::verify(unsafe { i(out, outl) }, &p, unsafe { i(salt, sl) }, iters, unsafe { o(out, outl) }))
} }

ex! { fn orion_x_pbkdf2_sha384(pw: *const u8, pl: usize, salt: *const u8, sl: usize, iters: usize,
        out: *mut u8, outl: usize) -> i32 {
    use kdf::pbkdf2::sha384 as m;
    let Ok(p) = m::Password::from_slice(unsafe { i(pw, pl) }) else { return -2 };
    if m::derive_key(&p, unsafe { i(salt, sl) }, iters, unsafe { o(out, outl) }).is_err() { return -1; }
    st(m::verify(unsafe { i(out, outl) }, &p, unsafe { i(salt, sl) }, iters, unsafe { o(out, outl) }))
} }

ex! { fn orion_x_pbkdf2_sha512(pw: *const u8, pl: usize, salt: *const u8, sl: usize, iters: usize,
        out: *mut u8, outl: usize) -> i32 {
    use kdf::pbkdf2::sha512 as m;
    let Ok(p) = m::Password::from_slice(unsafe { i(pw, pl) }) else { return -2 };
    if m::derive_key(&p, unsafe { i(salt, sl) }, iters, unsafe { o(out, outl) }).is_err() { return -1; }
    st(m::verify(unsafe { i(out, outl) }, &p, unsafe { i(salt, sl) }, iters, unsafe { o(out, outl) }))
} }

#[cfg(not(feature = "v18"))]
ex! { fn orion_x_argon2i(pw: *const u8, pl: usize, salt: *const u8, sl: usize, iters: u32, mem: u32,
        out: *mut u8, outl: usize) -> i32 {
    use kdf::argon2i as m;
    if m::derive_key(unsafe { i(pw, pl) }, unsafe { i(salt, sl) }, iters, mem, None, None, unsafe { o(out, outl) }).is_err() { return -1; }
    let mut dst = [0u8; 64];
    let n = outl.min(64);
    st(m::verify(unsafe { i(out, n) }, unsafe { i(pw, pl) }, unsafe { i(salt, sl) }, iters, mem, None, None, &mut dst[..n]))
} }

// -- ECC and the committing AEAD -------------------------------------------

ex! { fn orion_x_x25519(sk: *const u8, pk: *const u8, out: *mut u8) -> i32 {
    use ecc::x25519 as m;
    let Ok(sk) = m::PrivateKey::from_slice(unsafe { i(sk, 32) }) else { return -2 };
    let Ok(pk) = m::PublicKey::from_slice(unsafe { i(pk, 32) }) else { return -3 };
    match m::key_agreement(&sk, &pk) {
        Ok(s) => { unsafe { o(out, 32) }.copy_from_slice(s.unprotected_as_bytes()); 0 }
        Err(_) => -1,
    }
} }

ex! { fn orion_x_x25519_basepoint(sk: *const u8, out: *mut u8) -> i32 {
    use ecc::x25519 as m;
    let Ok(sk) = m::PrivateKey::from_slice(unsafe { i(sk, 32) }) else { return -2 };
    let pk = m::PublicKey::try_from(&sk);
    match pk {
        Ok(p) => { unsafe { o(out, 32) }.copy_from_slice(&p.to_bytes()); 0 }
        Err(_) => -1,
    }
} }

ex! { fn orion_x_ctx_xchacha20poly1305_blake2b_seal(key: *const u8, nonce: *const u8, pt: *const u8, ptl: usize,
        adp: *const u8, adl: usize, out: *mut u8, outl: usize) -> i32 {
    use aead::xchacha20poly1305 as k;
    let _ = k::SecretKey::from_slice(unsafe { i(key, 32) });
    use orion::hazardous::cae::xchacha20poly1305blake2b as m;
    let Ok(sk) = m::SecretKey::from_slice(unsafe { i(key, 32) }) else { return -2 };
    let Ok(n) = m::Nonce::from_slice(unsafe { i(nonce, 24) }) else { return -3 };
    st(m::seal(&sk, &n, unsafe { i(pt, ptl) }, unsafe { opt(adp, adl) }, unsafe { o(out, outl) }))
} }

ex! { fn orion_x_ctx_xchacha20poly1305_blake2b_open(key: *const u8, nonce: *const u8, ct: *const u8, ctl: usize,
        adp: *const u8, adl: usize, out: *mut u8, outl: usize) -> i32 {
    use orion::hazardous::cae::xchacha20poly1305blake2b as m;
    let Ok(sk) = m::SecretKey::from_slice(unsafe { i(key, 32) }) else { return -2 };
    let Ok(n) = m::Nonce::from_slice(unsafe { i(nonce, 24) }) else { return -3 };
    st(m::open(&sk, &n, unsafe { i(ct, ctl) }, unsafe { opt(adp, adl) }, unsafe { o(out, outl) }))
} }
