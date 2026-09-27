// nt_wrapper exerciser, 5 of 5: ntw::clock and the sleep helpers, the ntw::se
// security types (SID, ACE, ACL, security descriptor), and the ntw::sys
// system-wide enumerations - processes and their threads, loaded modules, pool
// tags - plus the driver loader. See README.md in this directory for the split
// and why it is safe for this library.
//
// sys/driver.hpp is included here and nowhere else on purpose. Its two
// functions are the only definitions in the whole library written without
// NTW_INLINE (sys/impl/driver_loader.inl:22 and :27); they are declared
// NTW_INLINE in sys/driver.hpp before that .inl is included, so they are
// inline functions and could not collide anyway - but keeping them to one
// translation unit means the question cannot arise at all.
//
// <tuple> is included before the library because se/access_control_list.hpp
// declares "std::tuple<Aces...> aces" while including only <cstdint> and the
// library's own detail headers. That is a consumer supplying a standard header
// the library happens to need, not a modification of it.
//
// ntw::se::security_desc inherits base_security_desc PRIVATELY upstream, so
// control(), dacl_present() and the rest of that CRTP base are unreachable
// from a consumer; only security_desc's own members are called below. The ACE
// flag setters take "bool enable = true" and sit beside same-named getters, so
// a no-argument call is ambiguous: every setter here passes the bool
// explicitly, and the getters are read through a const reference, where the
// non-const setter drops out of the overload set.

#include <cstdint>
#include <tuple>
#include <vector>

#include <ntw/chrono.hpp>
#include <ntw/se/access_control_entry.hpp>
#include <ntw/se/access_control_list.hpp>
#include <ntw/se/security_descriptor.hpp>
#include <ntw/se/sid.hpp>
#include <ntw/sys/driver.hpp>
#include <ntw/sys/modules.hpp>
#include <ntw/sys/pool_tags.hpp>
#include <ntw/sys/processes.hpp>

namespace {

// 128 KiB, and at namespace scope so it does not become a stack frame.
// ntw::sys::loaded_modules wants a real array: it calls
// detail::range_byte_size with an explicit reference Range, where
// ntw::sys::processes and ntw::sys::pool_tags call it with a deduced by-value
// Range, and an array passed to the deduced form decays to a pointer and stops
// being a range at all.
alignas(16) std::uint8_t g_modules_buffer[0x1000 * 32];

} // namespace

extern "C" __declspec(dllexport) int exercise_sys(void)
{
    int sink = 0;

    // ---- chrono ------------------------------------------------------------
    const auto now = ntw::clock::now();
    sink += static_cast<int>(now.time_since_epoch().count());
    sink += static_cast<int>(ntw::sleep_for(ntw::duration{ 1 }).get());
    sink += static_cast<int>(
        ntw::sleep_for(ntw::duration{ 1 }, ntw::alertable).get());
    sink += static_cast<int>(ntw::sleep_until(now).get());
    sink += static_cast<int>(ntw::sleep_until(now, ntw::alertable).get());

    // ---- security descriptors ----------------------------------------------
    ntw::se::security_desc descriptor;
    descriptor.owner(descriptor.owner())
        .default_owner()
        .group(descriptor.group())
        .default_group()
        .sacl(descriptor.sacl())
        .default_sacl()
        .no_sacl()
        .protect_sacl()
        .dacl(descriptor.dacl())
        .default_dacl()
        .no_dacl()
        .protect_dacl()
        .rm_control(1)
        .no_rm_control();
    sink += descriptor.get()->Revision;

    ntw::se::rel_security_desc relative;
    sink += relative.get() == nullptr ? 1 : 0;

    // ---- SIDs --------------------------------------------------------------
    ntw::se::static_sid<4> account_sid(ntw::se::sid::authority::non_unique, 21u);
    account_sid.push_back(1);
    account_sid.resize(2);
    sink += account_sid.size() + account_sid.max_size();
    sink += static_cast<int>(account_sid.sub_authorities().size());
    sink += account_sid.identifier_authority().Value[5];
    constexpr auto world = ntw::se::sid::universal::world;
    sink += world.size();

    // ---- access control entries and lists ----------------------------------
    ntw::se::ace::access_allowed allowed(GENERIC_READ, world);
    allowed.object_inherit(true)
        .container_inherit(true)
        .no_propagate_inherit(true)
        .inherit_only(true)
        .critical(true);
    const auto &allowed_view = allowed;
    sink += allowed_view.container_inherit() ? 1 : 0;
    sink += allowed_view.no_propagate_inherit() ? 1 : 0;
    sink += allowed_view.inherit_only() ? 1 : 0;
    sink += allowed_view.critical() ? 1 : 0;
    sink += allowed_view.inherited() ? 1 : 0;
    sink += allowed.header.size;

    ntw::se::ace::access_denied denied(GENERIC_WRITE, world);
    denied.object_inherit(true).container_inherit(true).inherit_only(true);
    sink += denied.header.size;

    ntw::se::static_acl acl(allowed, denied);
    sink += static_cast<int>(acl.acl.AceCount);
    sink += static_cast<ACL *>(acl) != nullptr ? 1 : 0;

    // ---- system information ------------------------------------------------
    std::vector<std::uint8_t> buffer(0x100000);
    const auto process_list = ntw::sys::processes(buffer);
    sink += process_list ? 1 : 0;
    if (process_list) {
        for (auto &entry : *process_list) {
            sink += static_cast<int>(entry.id + entry.parent_id +
                                     entry.handle_count + entry.session_id);
            sink += static_cast<int>(entry.image_name.size());
            for (auto &thread : entry.threads()) {
                sink += static_cast<int>(thread.id + thread.process_id);
            }
        }
    }

    const auto tags = ntw::sys::pool_tags(buffer);
    sink += tags ? 1 : 0;
    if (tags) {
        for (auto &tag : *tags) {
            sink += static_cast<int>(tag.tag + tag.paged.allocations +
                                     tag.non_paged.frees);
        }
    }

    const auto modules = ntw::sys::loaded_modules(g_modules_buffer);
    sink += modules ? 1 : 0;
    if (modules) {
        for (const auto &loaded : *modules) {
            sink += loaded.name()[0];
            sink += static_cast<int>(loaded.name_view().size());
            sink += static_cast<int>(loaded.path_view().size());
            sink += static_cast<int>(loaded.image_size);
        }
    }

    // ---- driver loading ----------------------------------------------------
    const ntw::unicode_string service(
        L"\\Registry\\Machine\\System\\CurrentControlSet\\Services\\ntw");
    sink += static_cast<int>(ntw::sys::load_driver(service).get());
    sink += static_cast<int>(ntw::sys::unload_driver(service).get());

    return sink;
}
