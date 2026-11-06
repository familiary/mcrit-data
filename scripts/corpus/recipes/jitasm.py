"""jitasm - header-only runtime x86/x64 assembler, built with MinGW.

Placeholder docstring, rewritten after measurement.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_BUILD = ("{cxx} -O2 -fno-operator-names -mmmx -msse -msse2 -shared -I. "
          "-o jitasm.dll {repo}/scripts/corpus/exercisers/jitasm.cpp "
          "-shared-libgcc")

RECIPES = {
    "jitasm_2018-11-24": Recipe(
        family="jitasm",
        version="2018-11-24",
        upstream="https://github.com/hikaru-i/jitasm",
        license="New BSD",
        source=Source(git_url="https://github.com/hikaru-i/jitasm.git",
                      git_ref="7cb9d72982c793374c49b804bec842deb1506d92"),
        build=[BuildStep(_BUILD)],
        artifacts=[Artifact(path="jitasm.dll", component="jitasm.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 -fno-operator-names -mmmx -msse -msse2 -shared "
                    "-shared-libgcc",
        notes="Placeholder.",
    ),
}
