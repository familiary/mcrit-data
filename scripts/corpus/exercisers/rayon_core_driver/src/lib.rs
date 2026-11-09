//! Instantiates rayon-core so its code is actually emitted.
//!
//! rayon-core is a library crate: its scheduler is generic over the closures
//! it runs, so nothing of it exists in a binary until something calls into
//! it. This driver exports one `extern "C"` function per public entry point
//! of rayon-core 1.12.1 - the global and the explicit thread pool, join,
//! scope, spawn, broadcast and their FIFO and in-place variants - each
//! taking its work size from the caller so the compiler can fold nothing
//! away. See ../../../recipes/rayon_core.py.
//!
//! Every exported function is named `rc_x_*` and marked `#[inline(never)]`
//! so the driver's own code in a report is identifiable by name; the recipe
//! excludes it, with std, core and alloc, by name.

use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

use rayon_core::{ThreadPool, ThreadPoolBuilder};

#[inline(never)]
fn work(n: usize) -> usize {
    (0..n).fold(0usize, |a, b| a.wrapping_mul(31).wrapping_add(b))
}

#[no_mangle]
#[inline(never)]
pub extern "C" fn rc_x_pool_new(threads: usize) -> *mut ThreadPool {
    match ThreadPoolBuilder::new()
        .num_threads(threads)
        .thread_name(|i| format!("rc-{}", i))
        .stack_size(1 << 20)
        .panic_handler(|_| {})
        .start_handler(|_| {})
        .exit_handler(|_| {})
        .breadth_first()
        .build()
    {
        Ok(pool) => Box::into_raw(Box::new(pool)),
        Err(_) => std::ptr::null_mut(),
    }
}

#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn rc_x_pool_free(pool: *mut ThreadPool) {
    if !pool.is_null() {
        drop(Box::from_raw(pool));
    }
}

#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn rc_x_pool_install(pool: *const ThreadPool, n: usize) -> usize {
    let pool = &*pool;
    pool.install(|| {
        let (a, b) = pool.join(|| work(n), || work(n + 1));
        a ^ b ^ pool.current_num_threads() ^ pool.current_thread_index().unwrap_or(0)
    })
}

#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn rc_x_pool_scope(pool: *const ThreadPool, n: usize) -> usize {
    let pool = &*pool;
    let total = AtomicUsize::new(0);
    pool.scope(|s| {
        for i in 0..n {
            let total = &total;
            s.spawn(move |_| {
                total.fetch_add(work(i), Ordering::Relaxed);
            });
        }
    });
    pool.scope_fifo(|s| {
        for i in 0..n {
            let total = &total;
            s.spawn_fifo(move |_| {
                total.fetch_add(work(i), Ordering::Relaxed);
            });
        }
    });
    pool.in_place_scope(|s| {
        let total = &total;
        s.spawn(move |_| {
            total.fetch_add(1, Ordering::Relaxed);
        });
    });
    pool.in_place_scope_fifo(|s| {
        let total = &total;
        s.spawn_fifo(move |_| {
            total.fetch_add(1, Ordering::Relaxed);
        });
    });
    total.load(Ordering::Relaxed)
}

#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn rc_x_pool_spawn(pool: *const ThreadPool, n: usize) -> usize {
    let pool = &*pool;
    let total = Arc::new(AtomicUsize::new(0));
    let t = total.clone();
    pool.spawn(move || {
        t.fetch_add(work(n), Ordering::Relaxed);
    });
    let t = total.clone();
    pool.spawn_fifo(move || {
        t.fetch_add(work(n), Ordering::Relaxed);
    });
    let v = pool.broadcast(|ctx| ctx.index() ^ ctx.num_threads());
    let t = total.clone();
    pool.spawn_broadcast(move |ctx| {
        t.fetch_add(ctx.index(), Ordering::Relaxed);
    });
    pool.install(|| {
        let _ = rayon_core::yield_now();
        let _ = rayon_core::yield_local();
    });
    v.iter().sum::<usize>() ^ total.load(Ordering::Relaxed)
}

#[no_mangle]
#[inline(never)]
pub extern "C" fn rc_x_global(n: usize) -> usize {
    let _ = ThreadPoolBuilder::new().num_threads(n.max(1)).build_global();
    let (a, b) = rayon_core::join(|| work(n), || work(n * 2));
    let (c, d) = rayon_core::join_context(|ctx| ctx.migrated() as usize, |_| work(3));
    let total = AtomicUsize::new(a ^ b ^ c ^ d);
    rayon_core::scope(|s| {
        let total = &total;
        s.spawn(move |s2| {
            s2.spawn(move |_| {
                total.fetch_add(work(n), Ordering::Relaxed);
            });
        });
    });
    rayon_core::scope_fifo(|s| {
        let total = &total;
        s.spawn_fifo(move |_| {
            total.fetch_add(work(n), Ordering::Relaxed);
        });
    });
    rayon_core::in_place_scope(|s| {
        let total = &total;
        s.spawn(move |_| {
            total.fetch_add(1, Ordering::Relaxed);
        });
    });
    rayon_core::in_place_scope_fifo(|s| {
        let total = &total;
        s.spawn_fifo(move |_| {
            total.fetch_add(1, Ordering::Relaxed);
        });
    });
    rayon_core::spawn(move || {
        let _ = work(n);
    });
    rayon_core::spawn_fifo(move || {
        let _ = work(n);
    });
    let v = rayon_core::broadcast(|ctx| ctx.index());
    rayon_core::spawn_broadcast(|ctx| {
        let _ = ctx.num_threads();
    });
    total.load(Ordering::Relaxed)
        ^ v.len()
        ^ rayon_core::current_num_threads()
        ^ rayon_core::max_num_threads()
        ^ rayon_core::current_thread_index().unwrap_or(0)
}

#[no_mangle]
#[inline(never)]
pub extern "C" fn rc_x_scoped(n: usize) -> usize {
    ThreadPoolBuilder::new()
        .num_threads(n.max(1))
        .build_scoped(
            |thread| thread.run(),
            |pool| pool.install(|| work(n)),
        )
        .unwrap_or(0)
}
