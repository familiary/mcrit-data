// nt_wrapper exerciser, 4 of 5: ntw::vm - the protection flag type, the
// allocation builder, the free memory operations - and ntw::memory::basic_info,
// the virtual-memory information class those operations describe. See README.md
// in this directory for the split and why it is safe for this library.
//
// basic_info is filled by ntw::ob::basic_process::query_mem, which is
// instantiated in nt_wrapper_ob.cpp. It is an aggregate, so its accessors can
// be reached here without pulling the whole ob tree into this translation
// unit - which is the point of the split.

#include <cstdint>

#include <ntw/info/memory.hpp>
#include <ntw/vm/allocation.hpp>
#include <ntw/vm/operation.hpp>
#include <ntw/vm/protection.hpp>

extern "C" __declspec(dllexport) int exercise_vm(void *address,
                                                 unsigned long code)
{
    int sink = 0;

    // ---- protection --------------------------------------------------------
    const auto protection = ntw::vm::protection::read_write()
                                .guard()
                                .disable_caching()
                                .combine_writes();
    sink += static_cast<int>(protection.get() +
                             ntw::vm::protection::no_access().get() +
                             ntw::vm::protection::read().get() +
                             ntw::vm::protection::execute().get() +
                             ntw::vm::protection::read_writecopy().get() +
                             ntw::vm::protection::read_execute().get() +
                             ntw::vm::protection::read_write_execute().get() +
                             ntw::vm::protection::read_writecopy_execute().get());
    sink += protection.accessible() ? 1 : 0;
    sink += protection.readable() ? 1 : 0;
    sink += protection.writeable() ? 1 : 0;
    sink += protection.executeable() ? 1 : 0;
    sink += protection.guarded() ? 1 : 0;
    sink += protection.non_cached() ? 1 : 0;
    sink += protection.write_combined() ? 1 : 0;
    // The converting constructor, reached with a value the compiler cannot
    // fold away.
    const ntw::vm::protection from_value{ static_cast<std::uint32_t>(code) };
    sink += static_cast<int>(from_value.get());

    // ---- allocation --------------------------------------------------------
    auto allocation = ntw::vm::allocate();
    allocation.at(address)
        .zero_bits(1)
        .top_down()
        .write_watch()
        .physical()
        .rotate()
        .large_pages();
    const auto committed = ntw::vm::allocate().commit_reserve(
        0x1000, ntw::vm::protection::read_write());
    sink += committed ? 1 : 0;
    sink += ntw::vm::allocate().reserve(0x1000, ntw::vm::protection::read())
                ? 1 : 0;
    sink += ntw::vm::allocate().commit(0x1000, ntw::vm::protection::read())
                ? 1 : 0;

    // ---- the free operations -----------------------------------------------
    if (committed) {
        sink += static_cast<int>(ntw::vm::reset(*committed, 0x1000).get());
        sink += static_cast<int>(ntw::vm::undo_reset(*committed, 0x1000).get());
        sink += static_cast<int>(ntw::vm::decommit(*committed, 0x1000).get());
        sink += static_cast<int>(ntw::vm::release(*committed).get());
    }
    sink += static_cast<int>(ntw::vm::unmap(address).get());

    // ---- memory information ------------------------------------------------
    ntw::memory::basic_info region{};
    region.base = reinterpret_cast<std::uintptr_t>(address);
    region.size = 0x1000;
    region.state = code;
    region.type = code;
    region.protect = protection;
    region.allocation_protect = ntw::vm::protection::read_execute();
    sink += static_cast<int>(region.end());
    sink += region.is_commited() ? 1 : 0;
    sink += region.is_reserved() ? 1 : 0;
    sink += region.is_free() ? 1 : 0;
    sink += region.is_mapped() ? 1 : 0;
    sink += region.is_private() ? 1 : 0;
    sink += region.is_image() ? 1 : 0;
    sink += region.allocation_protect.readable() ? 1 : 0;

    return sink;
}
