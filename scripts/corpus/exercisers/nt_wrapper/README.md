# nt_wrapper exerciser

Five translation units that instantiate JustasMasiulis/nt_wrapper so its code
is actually emitted. `scripts/corpus/recipes/nt_wrapper_msvc.py` compiles each
one separately with `allow_failure=True` and links whatever object files were
produced, following `vxapi.py`'s pattern, so a translation unit that will not
compile costs one slice of coverage rather than the whole family.

| file | what it instantiates |
| --- | --- |
| `nt_wrapper_core.cpp` | `ntw::status`, `ntw::result`, `ntw::result_ref`, `ntw::unicode_string`, `ntw::access_builder`, `ntw::ob::attributes` and `attribute_options` |
| `nt_wrapper_ob.cpp` | `ntw::ob::object`, `object_ref`, `ntw::object::basic_info`/`handle_flags_info`, `process`, `thread`, `token`, `job` and their access builders |
| `nt_wrapper_io.cpp` | `ntw::io::file`, `unique_reg_key`, `file_options`, `pipe_options`, `reg_access` and the registry option builders |
| `nt_wrapper_vm.cpp` | `ntw::vm::protection`, `allocation_builder`, the `ntw::vm` free operations, and `ntw::memory::basic_info` |
| `nt_wrapper_sys.cpp` | `ntw::clock`/`sleep_*`, the `ntw::se` SID/ACE/ACL/security-descriptor types, and `ntw::sys` process, module, pool-tag and driver enumeration |

Splitting the exerciser is safe for this library specifically, and it is worth
writing down why, because it is not safe in general. Every function nt_wrapper
provides is inline: `detail/config.hpp` defines `NTW_INLINE` as
`__forceinline`, and the only two definitions in the tree that omit it -
`ntw::sys::load_driver` and `ntw::sys::unload_driver`, in
`sys/impl/driver_loader.inl:22` and `:27` - are declared `NTW_INLINE` in
`sys/driver.hpp` before that `.inl` is included, so they are inline functions
too. No translation unit here emits an external definition another one could
collide with. `sys/driver.hpp` is nevertheless included by
`nt_wrapper_sys.cpp` alone, so the one place a reader would worry about is
also the one place that cannot arise.

The contrast is `scripts/corpus/exercisers/winapi_obfuscator.cpp`, which must
stay a single translation unit: `win_api::detail::murmur_hash2_a` and
`win_api::detail::parse_export_table` are plain non-inline free functions in
that project's header, so a second including translation unit is LNK2005 on
both.

Seven pieces of nt_wrapper's published API are deliberately never used,
because they do not compile or link as published. Upstream source is not
patched; a consumer reaching for any of them would not build either. Six are
named with their file and line in the translation unit that would otherwise
have used them — `thread::open`, the process-taking overloads of
`thread::first` and `thread::next`, `token::open`/`open_as_self` for threads,
the typed `device_io_control`/`fs_control` overloads, `result_ref`'s only
value-carrying constructor, and `object::wait_until`/`object::name`, which are
declared and never defined.

The seventh belongs to no one file and is recorded here instead:
**`<ntw/concepts.hpp>` is not included by any of these translation units and
must not be.** It is the one header in the library that nothing else includes,
and it does not compile — it names `Byte<std::ranges::range_value_t>` with the
alias template's argument missing.
