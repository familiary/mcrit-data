// nt_wrapper exerciser, 3 of 5: ntw::io - the blocking file API, the registry
// key API, and the three option builders that feed them. See README.md in this
// directory for the split and why it is safe for this library.
//
// The typed device_io_control/fs_control overloads are deliberately never
// called. They build a std::span<const std::uint8_t> from
// "{ ::std::addressof(input), sizeof(Input) }" for an arbitrary Input
// (io/impl/file.inl:88 and :118), which only compiles when Input is a byte
// type; a consumer passing anything else would not build either. The
// explicit-span overloads beside them are used instead. Upstream source is not
// patched.

#include <cstdint>

#include <ntw/io/file.hpp>
#include <ntw/io/registry_key.hpp>

extern "C" __declspec(dllexport) int exercise_io(unsigned long code)
{
    int sink = 0;

    ntw::ob::attributes attrs;
    attrs.case_insensitive().kernel_handle();

    // ---- file options ------------------------------------------------------
    ntw::io::file_options file_options;
    // The attribute setters live on file_attributes_builder and return a
    // reference to THAT base, so they cannot be chained onto the access and
    // share-mode setters; upstream's builder splits in two here.
    file_options.reset_attributes();
    file_options.archive().encrypted().hidden().normal().offline().readonly()
        .system().temporary();
    file_options.reset_share_access()
        .share_read()
        .share_write()
        .share_delete()
        .share_all()
        .reset_create_options()
        .write_trough()
        .sequential_access()
        .random_access()
        .create_tree_connection()
        .no_ea_knownledge()
        .open_reparse_point()
        .delete_on_close()
        .open_by_file_id()
        .open_for_backup()
        .reserve_opfilter()
        .requires_oplock()
        .complete_if_oplocked()
        .reset_access()
        .deleteable()
        .synchronizable()
        .executeable()
        .traversible()
        .listable_directory()
        .generic_readable()
        .generic_writeable()
        .generic_executeable()
        .readable_data()
        .readable_attributes()
        .readable_extended_attributes()
        .readable_access_control()
        .writeable_data()
        .writeable_attributes()
        .writeable_extended_attributes()
        .writeable_access_control()
        .writeable_ownership()
        .appendable_data()
        .full_access();
    sink += static_cast<int>(file_options.copy().data().access);
    sink += static_cast<int>(file_options.attributes());

    // pipe_options is the same builder template over a different base, so
    // every file_options_builder member above is instantiated a second time.
    ntw::io::pipe_options pipe_options;
    pipe_options.qouta(0x1000, 0x1000)
        .inbound_qouta(0x1000)
        .outbound_qouta(0x1000)
        .reset_type()
        .byte_stream()
        .message_stream()
        .accept_remote_clients()
        .reject_remote_clients()
        .instances_limit(4)
        .timeout(-500000);
    pipe_options.share_all().full_access();
    sink += static_cast<int>(pipe_options.pipe_data().instances_limit);

    // ---- files -------------------------------------------------------------
    const ntw::unicode_string path(L"\\??\\C:\\Windows\\Temp\\ntw_exerciser.tmp");
    // All six dispositions base_file exposes.
    auto file = ntw::io::file::open(path, attrs, file_options);
    sink += file ? 1 : 0;
    sink += ntw::io::file::create(path, attrs, file_options) ? 1 : 0;
    sink += ntw::io::file::supersede(path, attrs, file_options) ? 1 : 0;
    sink += ntw::io::file::overwrite(path, attrs, file_options) ? 1 : 0;
    sink += ntw::io::file::open_or_create(path, attrs, file_options) ? 1 : 0;
    sink += ntw::io::file::overwrite_or_create(path, attrs, file_options)
                ? 1 : 0;
    if (file) {
        std::uint8_t io_buffer[64] = { 0 };
        sink += static_cast<int>(*file->write(ntw::cbyte_span{ io_buffer }, 0));
        sink += static_cast<int>(*file->read(ntw::byte_span{ io_buffer }, 0));
        sink += static_cast<int>(*file->size());
        sink += static_cast<int>(file->flush().get());
        sink += static_cast<int>(*file->device_io_control(
            code, ntw::cbyte_span{ io_buffer }, ntw::byte_span{ io_buffer }));
        sink += static_cast<int>(*file->fs_control(
            code, ntw::cbyte_span{ io_buffer }, ntw::byte_span{ io_buffer }));
    }
    sink += static_cast<int>(ntw::io::file::destroy(path, attrs).get());

    // ---- registry ----------------------------------------------------------
    const auto reg_rights = ntw::io::reg_access{}
                                .create_link()
                                .create_sub_key()
                                .enum_sub_keys()
                                .notify()
                                .query_value()
                                .set_value()
                                .read()
                                .write()
                                .execute()
                                .wow64_32()
                                .wow64_64()
                                .all()
                                .get();
    sink += static_cast<int>(reg_rights);

    const ntw::unicode_string key_path(
        L"\\Registry\\Machine\\System\\CurrentControlSet\\Services");
    const ntw::unicode_string value_name(L"ntw_exerciser");
    const auto open_options = ntw::io::reg_open_options{}
                                  .backup_restore()
                                  .open_link()
                                  .dont_virtualize();
    const auto create_options = ntw::io::reg_create_options{}
                                    .backup_restore()
                                    .open_link()
                                    .dont_virtualize()
                                    .non_preserved()
                                    .create_link();
    sink += static_cast<int>(open_options.get() + create_options.get());

    auto key = ntw::io::unique_reg_key::open(
        key_path, ntw::io::reg_access{}.enum_sub_keys().query_value());
    sink += key ? 1 : 0;
    sink += ntw::io::unique_reg_key::open(
                key_path, ntw::io::reg_access{}.query_value(), open_options,
                attrs) ? 1 : 0;
    sink += ntw::io::unique_reg_key::create(
                key_path, ntw::io::reg_access{}.set_value(), create_options,
                attrs) ? 1 : 0;
    bool opened_existing = false;
    sink += ntw::io::unique_reg_key::create(
                key_path, ntw::io::reg_access{}.set_value(), create_options,
                attrs, opened_existing) ? 1 : 0;
    sink += opened_existing ? 1 : 0;
    if (key) {
        unsigned long value = 1;
        sink += static_cast<int>(
            key->set(value_name, REG_DWORD, &value,
                     static_cast<unsigned long>(sizeof(value))).get());
        sink += static_cast<int>(key->set(value_name, code).get());
    }

    return sink;
}
