// Instantiates nlohmann/json so its code is actually emitted.
//
// The library is header-only: nothing of it exists in a binary until a
// translation unit uses it. There is therefore no upstream artefact to
// disassemble, and the only way to get reference data is to compile a unit
// that exercises the templates. The functions that land in the binary are
// nlohmann's own; this file only decides which ones get instantiated.
//
// Coverage is chosen to match how the library is actually used: parse,
// serialise, iterate, convert to and from standard containers, and the
// error paths.

#include <nlohmann/json.hpp>

#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

using nlohmann::json;

extern "C" __declspec(dllexport) int exercise(const char *text)
{
    int sink = 0;

    json parsed = json::parse(text, nullptr, false);
    sink += parsed.is_discarded() ? 1 : 0;

    json built;
    built["string"] = "value";
    built["number"] = 42;
    built["real"] = 3.5;
    built["bool"] = true;
    built["null"] = nullptr;
    built["array"] = std::vector<int>{1, 2, 3};
    built["nested"]["deep"] = std::map<std::string, int>{{"a", 1}, {"b", 2}};

    sink += static_cast<int>(built.dump().size());
    sink += static_cast<int>(built.dump(4).size());
    sink += static_cast<int>(built.size());

    for (auto it = built.begin(); it != built.end(); ++it) {
        sink += static_cast<int>(it.key().size());
    }
    for (const auto &item : built.items()) {
        sink += static_cast<int>(item.key().size());
    }

    auto numbers = built["array"].get<std::vector<int>>();
    auto nested = built["nested"]["deep"].get<std::map<std::string, int>>();
    sink += static_cast<int>(numbers.size() + nested.size());

    std::istringstream in(built.dump());
    json streamed;
    in >> streamed;
    std::ostringstream out;
    out << streamed;
    sink += static_cast<int>(out.str().size());

    sink += static_cast<int>(json::to_cbor(built).size());
    sink += static_cast<int>(json::to_msgpack(built).size());
    sink += static_cast<int>(json::to_bson(built).size());
    sink += static_cast<int>(json::to_ubjson(built).size());

    json patched = built;
    patched.merge_patch(json{{"number", 7}});
    sink += patched["number"].get<int>();
    sink += static_cast<int>(json::diff(built, patched).size());

    try {
        (void)built.at("missing");
    } catch (const json::exception &error) {
        sink += error.id;
    }
    try {
        (void)json::parse("{invalid");
    } catch (const json::parse_error &error) {
        sink += static_cast<int>(error.byte);
    }

    sink += static_cast<int>(json::json_pointer("/nested/deep/a").to_string().size());
    sink += built.value("number", 0);
    sink += static_cast<int>(built.flatten().size());

    return sink;
}
