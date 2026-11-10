//! Instantiates orion-rs/orion 0.18's high-level API (the `safe_api`
//! feature): `orion::aead` (and its streaming API), `orion::auth`,
//! `orion::hash`, `orion::kdf`, `orion::pwhash`, and the 0.18 additions
//! `orion::kem` (ML-KEM/X-Wing), `orion::hpke` and `orion::signer` (ML-DSA),
//! which replace 0.17's `orion::kex`. Tracker issue #7 names `orion::aead`;
//! the `#![no_std]` driver of v18.rs covers only `orion::hazardous`, because
//! `safe_api` turns on `std` and `getrandom`. This driver is a std cdylib
//! instead; the recipe keeps only names in the `orion::` namespace, so the
//! statically linked std, core, alloc, getrandom and the driver's own
//! `orion_sx_*` exports are counted as excluded, not kept. See
//! ../../recipes/orion.py.
//!
//! Every export takes raw pointers and lengths from the caller, so the
//! compiler can fold nothing away, and is `#[inline(never)]`.

use orion::{aead, auth, hash, hpke, kdf, kem, pwhash, signer};
use orion::hpke::KP as _;

unsafe fn input<'a>(p: *const u8, n: usize) -> &'a [u8] {
    if p.is_null() { &[] } else { core::slice::from_raw_parts(p, n) }
}

unsafe fn output(out: *mut u8, cap: usize, data: &[u8]) -> isize {
    if out.is_null() || data.len() > cap { return -100; }
    core::ptr::copy_nonoverlapping(data.as_ptr(), out, data.len());
    data.len() as isize
}

#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn orion_sx_aead(m: *const u8, n: usize, out: *mut u8, cap: usize) -> isize {
    let Ok(key) = aead::SecretKey::generate() else { return -1 };
    let Ok(ct) = aead::seal(&key, input(m, n)) else { return -2 };
    let Ok(pt) = aead::open(&key, &ct) else { return -3 };
    output(out, cap, &pt)
}

#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn orion_sx_aead_stream(m: *const u8, n: usize, out: *mut u8, cap: usize) -> isize {
    use aead::streaming::{StreamOpener, StreamSealer, StreamTag};
    let Ok(key) = aead::SecretKey::generate() else { return -1 };
    let Ok((mut sealer, nonce)) = StreamSealer::new(&key) else { return -2 };
    let Ok(ct) = sealer.seal_chunk(input(m, n), &StreamTag::Finish) else { return -3 };
    let Ok(mut opener) = StreamOpener::new(&key, &nonce) else { return -4 };
    let Ok((pt, _tag)) = opener.open_chunk(&ct) else { return -5 };
    output(out, cap, &pt)
}

#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn orion_sx_auth(m: *const u8, n: usize) -> isize {
    let Ok(key) = auth::SecretKey::generate() else { return -1 };
    let Ok(tag) = auth::authenticate(&key, input(m, n)) else { return -2 };
    match auth::authenticate_verify(&tag, &key, input(m, n)) { Ok(()) => 0, Err(_) => -3 }
}

#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn orion_sx_hash(m: *const u8, n: usize, out: *mut u8, cap: usize) -> isize {
    let Ok(d) = hash::digest(input(m, n)) else { return -1 };
    let Ok(r) = hash::digest_from_reader(std::io::Cursor::new(input(m, n))) else { return -2 };
    if d != r { return -3; }
    output(out, cap, d.as_ref())
}

#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn orion_sx_kdf(p: *const u8, n: usize) -> isize {
    let Ok(password) = kdf::Password::try_from(input(p, n)) else { return -1 };
    let Ok(salt) = kdf::Salt::generate() else { return -2 };
    let cost = kdf::OWASP_ARGON2ID_1ST;
    match kdf::derive_key(&password, &salt, &cost, 32) { Ok(k) => k.len() as isize, Err(_) => -3 }
}

#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn orion_sx_pwhash(p: *const u8, n: usize) -> isize {
    let Ok(password) = pwhash::Password::try_from(input(p, n)) else { return -1 };
    let cost = pwhash::OWASP_ARGON2ID_1ST;
    let Ok(hashed) = pwhash::hash_password(&password, &cost) else { return -2 };
    match pwhash::hash_password_verify(&hashed, &password) { Ok(()) => 0, Err(_) => -3 }
}

#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn orion_sx_kem() -> isize {
    let Ok(kp) = kem::KeyPair::generate() else { return -1 };
    let Ok((ss_a, ct)) = kp.public().encap() else { return -2 };
    let Ok(ss_b) = kp.decap(&ct) else { return -3 };
    if ss_a == ss_b { 0 } else { -4 }
}

#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn orion_sx_hpke(m: *const u8, n: usize, out: *mut u8, cap: usize) -> isize {
    let Ok(kp) = hpke::KeyPair::generate() else { return -1 };
    let Ok((mut sender, enc)) = hpke::HpkeBase::new_sender(kp.public(), b"info") else { return -2 };
    let Ok(ct) = sender.seal(input(m, n), b"aad") else { return -3 };
    let Ok(mut recipient) = hpke::HpkeBase::new_recipient(&enc, kp.private(), b"info") else { return -4 };
    let Ok(pt) = recipient.open(&ct, b"aad") else { return -5 };
    output(out, cap, &pt)
}

#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn orion_sx_signer(m: *const u8, n: usize) -> isize {
    let Ok(kp) = signer::SigningKeyPair::generate() else { return -1 };
    let Ok(sig) = kp.sign(input(m, n), b"ctx") else { return -2 };
    match kp.verify(input(m, n), b"ctx", &sig) { Ok(()) => 0, Err(_) => -3 }
}
