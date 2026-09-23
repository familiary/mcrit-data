// nt_wrapper exerciser, 1 of 5: status, result, unicode_string, access and
// object attributes. See README.md in this directory for the split and why it
// is safe for this library.
//
// Deliberately the narrowest include set of the five: nothing here pulls in
// ob/object.hpp or any of the syscall-issuing headers, so a failure anywhere
// in those cannot take this translation unit with it. access_builder is
// instantiated through a local CRTP derivative, exactly as upstream's
// test_access.cpp does with its "mock_access", rather than through
// ntw::ob::process_access - that would have dragged in the whole ob tree for
// one chain of flag setters.
//
// ntw::result_ref is reached only as far as it can be: its one value-carrying
// constructor is "template<class U> result_ref(status, T*)", and U appears
// nowhere in the parameter list, so it cannot be deduced, has no default and
// can never be called. The default constructor and the accessors are what is
// left. operator* is not called either, because on a default-constructed
// result_ref it dereferences a null pointer.

#include <cstdint>

#include <ntw/access.hpp>
#include <ntw/ob/attributes.hpp>
#include <ntw/result.hpp>
#include <ntw/status.hpp>
#include <ntw/unicode_string.hpp>

namespace {

// access_builder is a CRTP base and emits nothing on its own; this is the
// smallest derivative that makes it emit, and it is upstream's own test's.
struct core_access : ntw::access_builder<core_access> {};

} // namespace

extern "C" __declspec(dllexport) int exercise_core(const wchar_t *name,
                                                   void *address,
                                                   unsigned long code)
{
    int sink = 0;

    // ---- status ------------------------------------------------------------
    ntw::status status{ STATUS_UNSUCCESSFUL };
    status = static_cast<std::int32_t>(code);
    sink += status.success() ? 1 : 0;
    sink += status.information() ? 1 : 0;
    sink += status.warning() ? 1 : 0;
    sink += status.error() ? 1 : 0;
    sink += static_cast<int>(status.severity());
    sink += static_cast<int>(status.facility());
    sink += static_cast<int>(status.code());
    sink += static_cast<int>(status.get());
    sink += (status == STATUS_SUCCESS) ? 1 : 0;
    sink += status ? 1 : 0;
    sink += static_cast<int>(static_cast<std::int32_t>(status));
    // Two differently shaped lambdas, because Fn is a template parameter and
    // each distinct callable is a distinct instantiation.
    status.and_then([](ntw::status s) { return s.get(); });
    status.or_else([](ntw::status) {});

    // ---- result and result_ref ---------------------------------------------
    ntw::result<int> value{ status, 7 };
    sink += value ? 1 : 0;
    sink += static_cast<int>(value.status().get());
    sink += *value;
    sink += *value.operator->();
    sink += *value.then([](int v) { return v + 1; });

    ntw::result_ref<int> reference;
    sink += static_cast<int>(reference.status().get());
    sink += reference.operator->() == nullptr ? 1 : 0;

    // ---- unicode_string ----------------------------------------------------
    // All five constructors: default, string literal, UNICODE_STRING,
    // pointer + length, and wstring_view.
    ntw::unicode_string empty_string;
    ntw::unicode_string literal(L"ntw_exerciser");
    ntw::unicode_string from_native(literal.get());
    ntw::unicode_string from_pointer(name, 4);
    ntw::unicode_string from_view(std::wstring_view{ name, 4 });
    sink += empty_string.empty() ? 1 : 0;
    sink += literal.size() + literal.byte_size();
    sink += static_cast<int>(from_native.view().size());
    sink += static_cast<int>(from_pointer.end() - from_pointer.begin());
    sink += static_cast<int>(from_view.rend() - from_view.rbegin());

    // ---- access_builder ----------------------------------------------------
    const auto generic = core_access{}
                             .generic_read()
                             .generic_write()
                             .generic_execute()
                             .generic_all()
                             .system_security()
                             .destroy()
                             .read_security()
                             .synchronize()
                             .write_dac()
                             .write_owner()
                             .maximum_allowed()
                             .get();
    sink += static_cast<int>(generic);

    // ---- object attributes -------------------------------------------------
    const auto options = ntw::ob::attribute_options{}
                             .inherit()
                             .permanent()
                             .exclusive()
                             .case_insensitive()
                             .open()
                             .open_symlink()
                             .kernel_handle()
                             .enforce_access_check()
                             .ignore_impersonated_devicemap()
                             .dont_reparse();
    sink += static_cast<int>(options.get());

    ntw::ob::attributes attrs;
    // parent() takes anything detail::unwrap understands, and a raw handle is
    // one of those - which keeps this file clear of ob/object.hpp.
    attrs.parent(address)
        .security_desc(address)
        .security_quality(address)
        .options(options);
    // basic_attribute_options is instantiated a second time here, for
    // attributes rather than for attribute_options: they are separate CRTP
    // derivatives and share no emitted code.
    attrs.inherit().case_insensitive().kernel_handle().dont_reparse();
    sink += static_cast<int>(attrs.get().Attributes);
    sink += static_cast<int>(attrs.get().Length);

    return sink;
}
