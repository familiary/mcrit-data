"""Probe the published SoftEther Stable Visual Studio solution."""

from ..recipe import Artifact, BuildStep, Recipe, Source


RECIPES = {
    "softether_stable_msvc_probe": Recipe(
        family="SoftEtherVPN",
        version="4.44-9807-rtm",
        source=Source(
            git_url="https://github.com/SoftEtherVPN/SoftEtherVPN_Stable.git",
            git_ref="ed17437af9719ac66acab30faa29e375d613c35f"),
        build=[BuildStep("msbuild src\\vpnserver\\vpnserver.vcproj "
                         "/p:Configuration=Release "
                         "/p:Platform={msbuild_platform} /m:2")],
        artifacts=[Artifact(path="src\\bin\\vpnserver.exe", component="vpnserver")],
        toolchains=["msvc_x86", "msvc_x64"],
        requires=["msbuild"],
    ),
}
