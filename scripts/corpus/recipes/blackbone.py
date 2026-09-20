"""BlackBone (mcrit-data issue #8) - MSVC only.

A Windows memory-hacking library: process and module management, manual PE
mapping, local and remote hooking, pattern search. It needs ATL and the DIA
SDK, both of which ship with Visual Studio and neither of which exists for
GCC, and its syscall stubs are MASM.

The solution only exposes Debug and Release, both of which build BlackBone as
a static library that SMDA cannot read. The project file itself also carries
a Release(DLL) configuration, so it is built directly - which means
SolutionDir has to be passed explicitly, because the project's OutDir is
defined relative to it and building a .vcxproj on its own would otherwise
resolve it to the project directory.

Release(DLL) statically compiles the vendored AsmJit and rewolf-wow64ext
sources into the same image, so those functions are present in this reference
data under the BlackBone family. That matches what an analyst meets in the
wild - upstream ships no configuration that leaves them out - but it is
recorded in the notes so the attribution is not mistaken for BlackBone's own
code. BeaEngine is different: it is linked through a prebuilt import library,
so only its thunks appear and its code stays in its own DLL.

The kernel driver has its own solution and is not built here even though the
runner has a WDK.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CONFIG = "Release(DLL)"

# PlatformToolset has to be overridden: the project asks for v142, which the
# windows-2022 runner image does not carry - it ships VS2022 and v143 only.
_MSBUILD = ('msbuild src\\BlackBone\\BlackBone.vcxproj '
            '/p:Configuration="%s" /p:Platform={msbuild_platform} '
            '/p:PlatformToolset=v143 /p:SolutionDir=%%CD%%\\ '
            '/m /v:minimal' % _CONFIG)


RECIPES = {
    "BlackBone_2023-07-17": Recipe(
        family="BlackBone",
        version="2023-07-17",
        upstream="https://github.com/DarthTon/Blackbone",
        license="MIT",
        source=Source(git_url="https://github.com/DarthTon/Blackbone.git",
                      git_ref="5ede6ce50cd8ad34178bfa6cae05768ff6b3859b"),
        build=[BuildStep(_MSBUILD)],
        artifacts=[
            Artifact(path="build\\{msbuild_platform}\\%s\\BlackBone.dll" % _CONFIG,
                     component="BlackBone.dll",
                     pdb="build\\{msbuild_platform}\\%s\\BlackBone.pdb" % _CONFIG),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2, Release(DLL) configuration",
        notes="Release(DLL) links the vendored AsmJit and rewolf-wow64ext "
              "sources into the same image, so functions from those projects "
              "are present here under the BlackBone family; BeaEngine is "
              "imported from its own DLL and is not. The kernel driver is "
              "not built.",
    ),
}
