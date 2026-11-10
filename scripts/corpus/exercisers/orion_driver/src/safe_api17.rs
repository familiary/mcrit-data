//! Instantiates orion-rs/orion's high-level API (the `safe_api` feature):
//! `orion::aead` (and its streaming API), `orion::auth`, `orion::hash`,
//! `orion::kdf`, `orion::pwhash` and `orion::kex`. Tracker issue #7 names
//! `orion::aead`; the `#![no_std]` driver of ../src/v17.rs and v18.rs covers
//! only `orion::hazardous`, because `safe_api` turns on `std` and `getrandom`.
//! This driver is a std cdylib instead; the recipe keeps only names in the
//! `orion::` namespace, so the statically linked std, core, alloc, getrandom
//! and the driver's own `orion_sx_*` exports are counted as excluded, not
//! kept. See ../../recipes/orion.py.
//!
//! Every export takes raw pointers and lengths from the caller, so the
//! compiler can fold nothing away, and is `#[inline(never)]`.

use orion::{aead, auth, hash, kdf, kex, pwhash};

unsafe fn input<'a>(p: *const u8, n: usize) -> &'a [u8] {
    if p.is_null() { &[] } else { core::slice::from_raw_parts(p, n) }
}

unsafe fn output(out: *mut u8, cap: usize, data: &[u8]) -> isize {
    if out.is_null() || data.len() > cap { return -100; }
    core::ptr::copy_nonoverlapping(data.as_ptr(), out, data.len());
    data.len() as isize
}

/// aead::seal with a fresh key, then aead::open; writes the plaintext back.
#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn orion_sx_aead(m: *const u8, n: usize, out: *mut u8, cap: usize) -> isize {
    let key = aead::SecretKey::default();
    let Ok(ct) = aead::seal(&key, input(m, n)) else { return -1 };
    let Ok(pt) = aead::open(&key, &ct) else { return -2 };
    output(out, cap, &pt)
}

/// The streaming AEAD: one sealed chunk per call, opened again.
#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn orion_sx_aead_stream(m: *const u8, n: usize, out: *mut u8, cap: usize) -> isize {
    use aead::streaming::{StreamOpener, StreamSealer, StreamTag};
    let key = aead::SecretKey::default();
    let Ok((mut sealer, nonce)) = StreamSealer::new(&key) else { return -1 };
    let Ok(ct) = sealer.seal_chunk(input(m, n), &StreamTag::Finish) else { return -2 };
    let Ok(mut opener) = StreamOpener::new(&key, &nonce) else { return -3 };
    let Ok((pt, _tag)) = opener.open_chunk(&ct) else { return -4 };
    output(out, cap, &pt)
}

/// auth::authenticate and authenticate_verify (BLAKE2b-256 keyed MAC).
#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn orion_sx_auth(m: *const u8, n: usize) -> isize {
    let key = auth::SecretKey::default();
    let Ok(tag) = auth::authenticate(&key, input(m, n)) else { return -1 };
    match auth::authenticate_verify(&tag, &key, input(m, n)) { Ok(()) => 0, Err(_) => -2 }
}

/// hash::digest (BLAKE2b-256).
#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn orion_sx_hash(m: *const u8, n: usize, out: *mut u8, cap: usize) -> isize {
    let Ok(d) = hash::digest(input(m, n)) else { return -1 };
    output(out, cap, d.as_ref())
}

/// kdf::derive_key (Argon2i) from a password and salt.
#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn orion_sx_kdf(p: *const u8, n: usize, out: *mut u8, cap: usize) -> isize {
    let Ok(password) = kdf::Password::from_slice(input(p, n)) else { return -1 };
    let salt = kdf::Salt::default();
    let Ok(key) = kdf::derive_key(&password, &salt, 3, 1 << 16, 32) else { return -2 };
    output(out, cap, key.unprotected_as_bytes())
}

/// pwhash::hash_password and hash_password_verify; writes the encoded hash.
#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn orion_sx_pwhash(p: *const u8, n: usize, out: *mut u8, cap: usize) -> isize {
    let Ok(password) = pwhash::Password::from_slice(input(p, n)) else { return -1 };
    let Ok(hashed) = pwhash::hash_password(&password, 3, 1 << 16) else { return -2 };
    if pwhash::hash_password_verify(&hashed, &password).is_err() { return -3; }
    let encoded = hashed.unprotected_as_encoded();
    let Ok(parsed) = pwhash::PasswordHash::from_encoded(encoded) else { return -4 };
    output(out, cap, parsed.unprotected_as_encoded().as_bytes())
}

/// kex: an ephemeral client and server session, both sides' session keys.
#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn orion_sx_kex(out: *mut u8, cap: usize) -> isize {
    let Ok(client) = kex::EphemeralClientSession::new() else { return -1 };
    let Ok(server) = kex::EphemeralServerSession::new() else { return -2 };
    let client_pk = client.public_key().clone();
    let server_pk = server.public_key().clone();
    let Ok(ck) = client.establish_with_server(&server_pk) else { return -3 };
    let Ok(sk) = server.establish_with_client(&client_pk) else { return -4 };
    if ck.receiving() != sk.transport() { return -5; }
    output(out, cap, ck.transport().unprotected_as_bytes())
}
