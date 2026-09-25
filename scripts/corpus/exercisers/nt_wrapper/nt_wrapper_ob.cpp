// nt_wrapper exerciser, 2 of 5: the ntw::ob object model - object and
// object_ref, the two object-information classes, process, thread, token and
// job, with each type's access builder beside it. See README.md in this
// directory for the split and why it is safe for this library.
//
// Four pieces of this part of the API are deliberately never called, because
// they do not compile or link as published. Upstream source is not patched;
// a consumer that called any of them would not build either.
//
//   * basic_thread<H>::open declares "OBJECT_ATTRIBUTES attr = attr.get();",
//     shadowing its own parameter and initialising it from itself
//     (impl/thread.inl:256), and then returns "{ status, handle }" through a
//     constructor that is explicit. process::open, which is written
//     correctly, is used instead.
//   * basic_thread<H>::first(process, ...) and next(process, ...) - the
//     overloads taking a process - spell the namespace "::ntw::details"
//     rather than "::ntw::detail" (impl/thread.inl:373 and :400). Only the
//     current-process overloads are used.
//   * basic_token<H>::open(thread, ...) and open_as_self(thread, ...) call
//     "thread->get()" on a type that has no operator->. Only the process
//     overload of token::open is used.
//   * basic_object<S>::wait_until and ::name are declared in ob/object.hpp
//     and never defined anywhere, so calling either is LNK2019.
//
// job::query is asked only for accounting_info, as upstream's test_job.cpp
// does. query<T> default-constructs a ntw::result<T> whose default
// constructor is declared "constexpr ... = default"; ntw::job::limits has a
// user-provided, non-constexpr default constructor, so query<limits> asks for
// a defaulted constexpr function that cannot be constexpr.

#include <cstdint>
#include <utility>

#include <ntw/info/memory.hpp>
#include <ntw/ob/job.hpp>
#include <ntw/ob/job_info.hpp>
#include <ntw/ob/object.hpp>
#include <ntw/ob/object_info.hpp>
#include <ntw/ob/process.hpp>
#include <ntw/ob/thread.hpp>
#include <ntw/ob/token.hpp>

namespace {

// Two callbacks with the exact signatures the thread APIs demand. Written as
// named functions rather than as the captureless lambdas upstream's tests
// use, because a lambda contributes both a conversion operator and a static
// invoker to the image, and every function this exerciser adds is a function
// filed under nt_wrapper's name that nt_wrapper did not write.
NTSTATUS NTAPI thread_entry(void *) { return 0; }

VOID NTAPI apc_entry(PVOID, PVOID, PVOID) {}

} // namespace

extern "C" __declspec(dllexport) int exercise_ob(void *address)
{
    int sink = 0;

    // ---- access builders ---------------------------------------------------
    const auto process_rights = ntw::ob::process_access{}
                                    .terminate()
                                    .create_thread()
                                    .set_session_id()
                                    .vm_operation()
                                    .vm_read()
                                    .vm_write()
                                    .dup_handle()
                                    .create_process()
                                    .set_qouta()
                                    .set_info()
                                    .query_info()
                                    .suspend_resume()
                                    .query_limited_info()
                                    .set_limited_info()
                                    .all()
                                    .get();
    const auto thread_rights = ntw::ob::thread_access{}
                                   .terminate()
                                   .suspend_resume()
                                   .get_context()
                                   .set_context()
                                   .query()
                                   .set_info()
                                   .set_token()
                                   .impersonate()
                                   .direct_impersonate()
                                   .set_limited_info()
                                   .query_limited()
                                   .resume()
                                   .all()
                                   .get();
    // token_access derives from access_builder<process_access> upstream, so an
    // inherited flag would change the chain's type mid-way. Only its own flags
    // are chained here, exactly as upstream's test_token.cpp does.
    const auto token_rights = ntw::ob::token_access{}
                                  .adjust_default()
                                  .adjust_groups()
                                  .adjust_privileges()
                                  .adjust_sessionid()
                                  .assign_primary()
                                  .duplicate()
                                  .execute()
                                  .impersonate()
                                  .query()
                                  .query_source()
                                  .all()
                                  .get();
    const auto job_rights = ntw::ob::job_access{}
                                .assign_process()
                                .set_attributes()
                                .query()
                                .terminate()
                                .set_security_attr()
                                .impersonate()
                                .all()
                                .get();
    sink += static_cast<int>(process_rights ^ thread_rights ^ token_rights ^
                             job_rights);

    ntw::ob::attributes attrs;
    const auto obj_options = ntw::ob::attribute_options{}.inherit()
                                 .case_insensitive();
    attrs.options(obj_options);

    // ---- objects -----------------------------------------------------------
    // NtCurrentProcess() is the pseudo-handle -1, which unique_object_storage's
    // destructor deliberately does not close.
    ntw::ob::object object{ NtCurrentProcess() };
    ntw::ob::object_ref reference{ object };
    sink += object ? 1 : 0;
    sink += object.get() == reference.get() ? 1 : 0;
    sink += object.storage().get() != nullptr ? 1 : 0;
    ntw::ob::object moved{ std::move(object) };
    object = std::move(moved);
    object.reset(NtCurrentProcess());
    sink += static_cast<int>(object.make_temporary().get());
    sink += static_cast<int>(object.make_permanent().get());
    sink += static_cast<int>(object.wait().get());
    sink += static_cast<int>(object.wait(ntw::alertable).get());
    sink += static_cast<int>(object.wait_for(ntw::duration{ 1 }).get());
    sink += static_cast<int>(
        object.wait_for(ntw::duration{ 1 }, ntw::alertable).get());

    ntw::object::basic_info object_info;
    sink += static_cast<int>(object_info.acquire(object).get());
    sink += static_cast<int>(object_info.attributes() + object_info.access() +
                             object_info.handle_count() +
                             object_info.pointer_count() +
                             object_info.paged_pool_charge() +
                             object_info.non_page_pool_charge() +
                             object_info.name_info_size() +
                             object_info.type_info_size() +
                             object_info.security_desc_size());
    sink += static_cast<int>(object_info.creation_time());

    ntw::object::handle_flags_info handle_flags{ true, false };
    sink += static_cast<int>(handle_flags.acquire(object).get());
    sink += static_cast<int>(handle_flags.apply(object).get());

    // ---- process -----------------------------------------------------------
    const ntw::ob::process_ref self;
    std::size_t source = 6;
    std::size_t copy = 0;
    sink += static_cast<int>(self.read_mem(&source, &copy, sizeof(copy)).get());
    sink += static_cast<int>(self.read_mem(&source, std::span{ &copy, 1 }).get());
    sink += static_cast<int>(self.write_mem(&copy, &source, sizeof(source)).get());
    sink += static_cast<int>(self.write_mem(&copy, std::span{ &source, 1 }).get());
    // A std::uintptr_t rather than the 0ull upstream's test uses: query_mem
    // reinterpret_casts the address, and a 64-bit integer does not
    // reinterpret_cast to a 32-bit pointer on the x86 leg.
    auto region = self.query_mem<ntw::memory::basic_info>(
        reinterpret_cast<std::uintptr_t>(address));
    sink += region ? 1 : 0;
    sink += static_cast<int>(region->end());

    // All four duplicate_object overloads. The two that name an access mask
    // ask for "typename Object::access_type", which basic_object does not
    // have, so those two are spelled with ntw::ob::process as the target type
    // and the other two with ntw::ob::object.
    sink += self.duplicate_object<ntw::ob::object>(object) ? 1 : 0;
    sink += self.duplicate_object<ntw::ob::object>(object, obj_options) ? 1 : 0;
    sink += self.duplicate_object<ntw::ob::process>(
                object, ntw::ob::process_access{}.query_info()) ? 1 : 0;
    sink += self.duplicate_object<ntw::ob::process>(
                object, ntw::ob::process_access{}.query_info(), obj_options)
                ? 1 : 0;
    sink += static_cast<int>(self.close_object(reference).get());
    sink += static_cast<int>(self.suspend().get());
    sink += static_cast<int>(self.resume().get());
    sink += static_cast<int>(self.terminate(ntw::status{ STATUS_SUCCESS }).get());
    sink += ntw::ob::process::open(address,
                                   ntw::ob::process_access{}.query_info(),
                                   attrs) ? 1 : 0;

    // ---- thread ------------------------------------------------------------
    auto builder = ntw::ob::thread::create();
    builder.argument(address)
        .zero_bits(1)
        .stack_size(0x1000)
        .max_stack_size(0x100000)
        .suspended()
        .skip_attach()
        .hide_from_dbg()
        .has_security_desc()
        .access_check_in_target()
        .bypass_process_freeze()
        .initial_thread();
    // local() forwards to remote() with a raw HANDLE, so these four calls
    // instantiate remote twice over: once for void* and once for process_ref.
    sink += builder.local(thread_entry) ? 1 : 0;
    sink += builder.local(thread_entry, ntw::ob::thread_access{}.all(), attrs)
                ? 1 : 0;
    sink += builder.remote(self, thread_entry) ? 1 : 0;
    sink += builder.remote(self, thread_entry, ntw::ob::thread_access{}.all(),
                           attrs) ? 1 : 0;

    const ntw::ob::thread_ref current_thread;
    sink += static_cast<int>(current_thread.suspend().get());
    sink += static_cast<int>(current_thread.resume().get());
    sink += static_cast<int>(current_thread.alert().get());
    sink += static_cast<int>(current_thread.alert_resume().get());
    sink += static_cast<int>(*current_thread.suspend_with_prev());
    sink += static_cast<int>(*current_thread.resume_with_prev());
    sink += static_cast<int>(*current_thread.alert_resume_with_prev());
    sink += static_cast<int>(current_thread.queue_apc(apc_entry).get());
    sink += static_cast<int>(
        current_thread.queue_apc_force_signal(apc_entry).get());
    sink += static_cast<int>(
        current_thread.queue_apc_with_reserve(object, apc_entry).get());
    sink += static_cast<int>(
        current_thread.terminate(ntw::status{ STATUS_SUCCESS }).get());
    auto registers = current_thread.context(CONTEXT_CONTROL);
    sink += registers ? 1 : 0;
    sink += static_cast<int>(current_thread.context(*registers).get());
    auto first_thread = ntw::ob::thread::first(ntw::ob::thread_access{}.all());
    if (first_thread) {
        sink += first_thread->next(ntw::ob::thread_access{}.all()) ? 1 : 0;
    }

    // ---- token and privileges ----------------------------------------------
    const auto token = ntw::ob::token::open(
        self, ntw::ob::token_access{}.adjust_privileges().query());
    if (token) {
        sink += static_cast<int>(token->reset_privileges().get());
        auto adjusted =
            token->adjust_privilege(ntw::ob::privilege::debug().enable());
        sink += adjusted ? 1 : 0;
        sink += adjusted->enabled() ? 1 : 0;
        sink += adjusted->removed() ? 1 : 0;
        sink += adjusted->enabled_by_default() ? 1 : 0;
        sink += static_cast<int>(adjusted->enable().attributes);
        sink += static_cast<int>(adjusted->remove().attributes);
        sink += static_cast<int>(
            token->replace_privilege(
                       ntw::ob::privilege::load_driver().enable()).get());
        sink += static_cast<int>(
            token->replace_privilege(
                       ntw::ob::privilege::tcb().disable()).get());
        sink += static_cast<int>(
            token->replace_privilege(
                       ntw::ob::privilege::backup().remove()).get());
    }
    sink += static_cast<int>(ntw::ob::privilege::create_token().LowPart +
                             ntw::ob::privilege::assign_primary_token().LowPart +
                             ntw::ob::privilege::lock_memory().LowPart +
                             ntw::ob::privilege::increase_qouta().LowPart +
                             ntw::ob::privilege::machine_account().LowPart +
                             ntw::ob::privilege::security().LowPart +
                             ntw::ob::privilege::take_ownership().LowPart +
                             ntw::ob::privilege::system_profile().LowPart +
                             ntw::ob::privilege::restore().LowPart +
                             ntw::ob::privilege::shutdown().LowPart +
                             ntw::ob::privilege::change_notify().LowPart +
                             ntw::ob::privilege::impersonate().LowPart +
                             ntw::ob::privilege::create_global().LowPart +
                             ntw::ob::privilege::relabel().LowPart +
                             ntw::ob::privilege::time_zone().LowPart +
                             ntw::ob::privilege::create_symbolic_link().LowPart);

    // ---- job ---------------------------------------------------------------
    const ntw::unicode_string job_name(L"ntw_exerciser_job");
    auto job = ntw::ob::job::create(ntw::ob::job_access{}.all());
    sink += job ? 1 : 0;
    sink += ntw::ob::job::create(job_name, ntw::ob::job_access{}.all(), attrs)
                ? 1 : 0;
    sink += ntw::ob::job::open(job_name, ntw::ob::job_access{}.query(), attrs)
                ? 1 : 0;
    if (job) {
        sink += static_cast<int>(job->assign_curr_process().get());
        sink += static_cast<int>(job->assign_process(self).get());
        sink += *job->is_assigned(self) ? 1 : 0;
        sink += static_cast<int>(
            job->terminate(ntw::status{ STATUS_SUCCESS }).get());

        auto accounting = job->query<ntw::job::accounting_info>();
        sink += accounting ? 1 : 0;
        sink += static_cast<int>(accounting->processes +
                                 accounting->active_processes +
                                 accounting->terminated_processes +
                                 accounting->page_faults);
        sink += static_cast<int>(accounting->get().TotalProcesses);

        ntw::job::limits limits;
        limits.process_max_user_time(ntw::duration{ 1 })
            .max_user_time(ntw::duration{ 2 })
            .min_working_set(0x1000)
            .max_working_set(0x100000)
            .max_processes(4)
            .affinity(1)
            .priority(0)
            .scheduling(5);
        sink += static_cast<int>(job->set(limits).get());
        sink += limits.process_max_user_time() ? 1 : 0;
        sink += limits.max_user_time() ? 1 : 0;
        sink += limits.min_working_set() ? 1 : 0;
        sink += limits.max_working_set() ? 1 : 0;
        sink += limits.max_processes() ? 1 : 0;
        sink += limits.affinity() ? 1 : 0;
        sink += limits.priority() ? 1 : 0;
        sink += limits.scheduling() ? 1 : 0;

        ntw::job::extended_limits extended;
        extended.process_max_user_time(ntw::duration{ 1 })
            .max_user_time(ntw::duration{ 2 })
            .min_working_set(0x1000)
            .max_working_set(0x100000)
            .max_processes(8)
            .affinity(1)
            .priority(0)
            .scheduling(5)
            .process_max_memory(0x100000)
            .max_memory(0x200000);
        sink += static_cast<int>(job->set(extended).get());
        sink += extended.process_max_memory() ? 1 : 0;
        sink += extended.max_memory() ? 1 : 0;
        sink += static_cast<int>(extended.io_counters().ReadOperationCount);
        sink += static_cast<int>(extended.peak_memory() +
                                 extended.peak_process_memory());
    }

    return sink;
}
