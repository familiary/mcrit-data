"""nlohmann/json - ubiquitous in modern C++ tooling.

Header-only, so none of it exists in a binary until a translation unit uses
it: there is no upstream artefact to disassemble. The only way to get
reference data is to compile a unit that instantiates the templates, which
is what scripts/corpus/exercisers/nlohmann_json.cpp does. The functions that
end up in the binary are nlohmann's; the exerciser only selects which.

Linked with -shared-libgcc on purpose: -static-libstdc++ would pull roughly
thirteen thousand libstdc++ and libgcc functions into the sample and
attribute them to this family.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_BUILD = ("{cxx} -std=c++17 -O2 -shared -Iinclude "
          "-o nlohmann_json.dll {repo}/scripts/corpus/exercisers/nlohmann_json.cpp "
          "-shared-libgcc")


def _nlohmann(version, git_ref):
    return Recipe(
        family="nlohmann_json",
        version=version,
        upstream="https://github.com/nlohmann/json",
        license="MIT",
        source=Source(git_url="https://github.com/nlohmann/json.git",
                      git_ref=git_ref),
        build=[BuildStep(_BUILD)],
        artifacts=[Artifact(path="nlohmann_json.dll",
                            component="nlohmann_json.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 -std=c++17",
        notes="Built from an exerciser translation unit, since the library is "
              "header-only; the emitted functions are the library's own.",
    )


RECIPES = {
    # Three releases that emit measurably different instantiations: 3.11
    # changed the inline-namespace macro and the serialiser, 3.12 added
    # std::optional conversions.
    "nlohmann_json_3.10.5": _nlohmann("3.10.5", "v3.10.5"),
    "nlohmann_json_3.11.3": _nlohmann("3.11.3", "v3.11.3"),
    "nlohmann_json_3.12.0": _nlohmann("3.12.0", "v3.12.0"),
}
