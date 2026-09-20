"""RE2 - Google's regular expression engine.

The two versions here bracket the largest code-level split in this part of
the corpus: 2022-06-01 is the last release before RE2 took a dependency on
Abseil, so it is entirely standalone, while current RE2 is built on Abseil
throughout. They are effectively different code bases rather than adjacent
versions, and a matcher that only knows one of them recognises very little
of the other.

Neither is built through RE2's CMake. CMake produces a static archive, which
SMDA cannot read, and the shared-library option only relabels it on MinGW;
compiling the library sources straight into a DLL is both shorter and exactly
what is wanted, which is every function present rather than only those an
anchor happens to reference. re2/testing and re2/fuzzing are outside the
glob, and util/pcre.cc is a test helper that needs PCRE, so it is named out.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_SOURCES = "re2/*.cc util/rune.cc util/strutil.cc"

_COMMON = ("{cxx}-posix -std=c++17 -O2 -I. %s -shared -o re2.dll "
           + _SOURCES + " %s -lwinpthread -shared-libgcc")

_BUILD_STANDALONE = _COMMON % ("", "")

# Abseil is on the include path but is deliberately not linked. Its headers
# are all RE2 needs to compile, and leaving the references unresolved keeps
# Abseil's own object code out of a sample labelled re2 - the same reasoning
# as the VX-API recipe's /FORCE:UNRESOLVED. What Abseil contributes here is
# the inline and template code RE2 instantiates, which a real RE2 binary
# carries too. The DLL does not load, which reference data need not.
_BUILD_ABSL = _COMMON % ("-I{absl}", "-Wl,--unresolved-symbols=ignore-all")


RECIPES = {
    # Last standalone release, before the Abseil dependency.
    "re2_2022-06-01": Recipe(
        family="re2",
        version="2022-06-01",
        upstream="https://github.com/google/re2",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/google/re2.git",
                      git_ref="2022-06-01"),
        build=[BuildStep(_BUILD_STANDALONE)],
        artifacts=[Artifact(path="re2.dll", component="re2.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 -std=c++17",
        notes="Standalone; no Abseil. Built with the posix-threads compiler, "
              "because the win32-threads <mutex> is unusable.",
    ),
    # Current, and Abseil-based throughout.
    "re2_2025-11-05": Recipe(
        family="re2",
        version="2025-11-05",
        upstream="https://github.com/google/re2",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/google/re2.git",
                      git_ref="2025-11-05"),
        extra_sources={
            # Headers only - see _BUILD_ABSL. Pinned all the same, because
            # which Abseil release supplied those headers decides what
            # inline code ended up in the artefact.
            "absl": Source(git_url="https://github.com/abseil/abseil-cpp.git",
                           git_ref="20250814.2"),
        },
        build=[BuildStep(_BUILD_ABSL)],
        artifacts=[Artifact(path="re2.dll", component="re2.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 -std=c++17",
        notes="Abseil supplies headers only and is not linked, so calls into "
              "it are left unresolved and no Abseil object code is attributed "
              "to re2; the inline and template code RE2 instantiates is "
              "present, as it would be in any RE2 binary. Built with the "
              "posix-threads compiler.",
    ),
}
