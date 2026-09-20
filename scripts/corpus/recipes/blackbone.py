"""BlackBone (mcrit-data issue #8) - MSVC only.

A Windows memory-hacking library: process and module management, manual PE
mapping, local and remote hooking, pattern search. It needs ATL and the DIA
SDK, both of which ship with Visual Studio and neither of which exists for
GCC, and its syscall stubs are MASM. The kernel driver additionally needs
the WDK, which the windows-2022 runner also carries.

AsmJit is vendored in src/3rd_party and would otherwise dominate this family
by function count, so it is not attributed to BlackBone - the artefact is
built from the library proper. BeaEngine is shipped only as a prebuilt MSVC
.lib and is excluded for the same reason.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_MSBUILD = ("msbuild src\\BlackBone.sln /p:Configuration=Release "
            "/p:Platform={msbuild_platform} /p:PlatformToolset=v143 "
            "/t:BlackBone /m /v:minimal")


RECIPES = {
    "BlackBone_2023-07-17": Recipe(
        family="BlackBone",
        version="2023-07-17",
        upstream="https://github.com/DarthTon/Blackbone",
        license="MIT",
        source=Source(git_url="https://github.com/DarthTon/Blackbone.git",
                      git_ref="5ede6ce50cd8ad34178bfa6cae05768ff6b3859b"),
        build=[BuildStep(_MSBUILD)],
        # The solution builds BlackBone as a static library, so the artefact
        # path is the test executable that links it; adjusted by the workflow
        # if upstream's output layout differs.
        artifacts=[Artifact(path="build\\{msbuild_platform}\\Release\\BlackBoneTest.exe",
                            component="BlackBoneTest.exe")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 (Release), PlatformToolset v143",
        notes="Vendored AsmJit and BeaEngine are not attributed to this "
              "family. The kernel driver is not built here.",
    ),
}
