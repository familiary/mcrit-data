//! Driver for the Arti reference data: a consumer of arti-client's public API.
//!
//! This copy is for rustc 1.75 (the 1.1.13-rust1.75 driver): it is ../src/lib.rs
//! with #[no_mangle] in place of #[unsafe(no_mangle)], which rustc accepts only
//! from 1.82 on, and is otherwise the same.
//!
//! A library emits no code until something uses it, and a cdylib keeps only
//! what its exports reach. Each export below calls into arti-client so the
//! linker keeps the client, circuit, directory and protocol code behind it.
//! Nothing here is copied from or changes Arti.

use arti_client::{DataStream, TorClient, TorClientConfig};
use tokio::io::{AsyncReadExt, AsyncWriteExt};

fn host_str<'a>(host: *const u8, len: usize) -> Option<&'a str> {
    if host.is_null() {
        return None;
    }
    let bytes = unsafe { core::slice::from_raw_parts(host, len) };
    core::str::from_utf8(bytes).ok()
}

/// Bootstrap a client, open an anonymised stream to host:port, send `req`
/// and read the reply into `out`. Returns the number of bytes read or a
/// negative error code.
#[no_mangle]
#[inline(never)]
pub extern "C" fn arti_x_fetch(
    host: *const u8,
    host_len: usize,
    port: u16,
    req: *const u8,
    req_len: usize,
    out: *mut u8,
    out_len: usize,
) -> isize {
    let Some(host) = host_str(host, host_len) else { return -1 };
    let Ok(rt) = tokio::runtime::Builder::new_current_thread().enable_all().build() else {
        return -2;
    };
    rt.block_on(async {
        let config = TorClientConfig::default();
        let client = match TorClient::create_bootstrapped(config).await {
            Ok(c) => c,
            Err(_) => return -3,
        };
        let mut stream: DataStream = match client.connect((host, port)).await {
            Ok(s) => s,
            Err(_) => return -4,
        };
        let req = unsafe { core::slice::from_raw_parts(req, req_len) };
        if stream.write_all(req).await.is_err() || stream.flush().await.is_err() {
            return -5;
        }
        let out = unsafe { core::slice::from_raw_parts_mut(out, out_len) };
        match stream.read(out).await {
            Ok(n) => n as isize,
            Err(_) => -6,
        }
    })
}

/// Bootstrap a client and resolve `host` through the Tor network; writes the
/// first address as text into `out`.
#[no_mangle]
#[inline(never)]
pub extern "C" fn arti_x_resolve(
    host: *const u8,
    host_len: usize,
    out: *mut u8,
    out_len: usize,
) -> isize {
    let Some(host) = host_str(host, host_len) else { return -1 };
    let Ok(rt) = tokio::runtime::Builder::new_current_thread().enable_all().build() else {
        return -2;
    };
    rt.block_on(async {
        let client = match TorClient::create_bootstrapped(TorClientConfig::default()).await {
            Ok(c) => c,
            Err(_) => return -3,
        };
        match client.resolve(host).await {
            Ok(addrs) => {
                let text = addrs.first().map(|a| a.to_string()).unwrap_or_default();
                let n = text.len().min(out_len);
                unsafe { core::ptr::copy_nonoverlapping(text.as_ptr(), out, n) };
                n as isize
            }
            Err(_) => -4,
        }
    })
}
