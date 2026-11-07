"""SoftEther VPN Stable 4.44, built from unmodified source.

The Stable release supplies vpnserver, vpnbridge, vpnclient and vpncmd. Its
Linux makefile preserves ELF symbols. The two development packages below
supply readline and ncurses headers and shared-library links on hosts that
do not install them globally; neither library is copied into the reports.

Coverage (unique PicHashes, functions with at least 10 instructions):
x64 server/client/cmd: 4306/4305/4305; server-client and server-cmd
share 4300, client-cmd share 4298. x86 server/bridge/client/cmd:
5043/5043/5042/5040; server-bridge share 5041 (two distinct hashes each),
server-client 1460, server-cmd 708, bridge-client 1460, bridge-cmd 708,
client-cmd 543. Every x86/x64 pair shares zero, justifying both axes.
The preliminary x64 bridge shared all 4922 qualifying hashes with the
preliminary server; it adds no coverage and is omitted.

Glue survivors: x86 __x86.get_pc_thunk.bp PicHash 8978313489863221434
in all four reports; x86 client _init PicHash 14231244029028250083.
No named startup glue survives in the x64 reports. These are reported
rather than changing the shared baseline. Windows builds failed before
producing a symbol-bearing image, so no MSVC overlap is available.

"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_DEBIAN = "https://deb.debian.org/debian/pool/main"
_WARNINGS = ("-Wno-error=incompatible-pointer-types "
             "-Wno-error=implicit-function-declaration "
             "-Wno-error=int-conversion")
_DEPS = {
    "readline_deb": Source(
        url=_DEBIAN + "/r/readline/libreadline-dev_8.2-6_amd64.deb",
        sha256="7ebffb08d6874dbed13665911fd43f2f7782d1ea55dd8f5399077c44a47ab123"),
    "ncurses_deb": Source(
        url=_DEBIAN + "/n/ncurses/libncurses-dev_6.5+20250216-2_amd64.deb",
        sha256="6bd7804e243fc08e2a2af380c341998bb6d21dd35550588ecc430d7c488a410d"),
    "readline_runtime_deb": Source(
        url=_DEBIAN + "/r/readline/libreadline8t64_8.2-6_amd64.deb",
        sha256="eeadf2b5e755c9f183883feea2d9b5b28560284275d5f54d3e55d0923b1d0967"),
    "ncurses_runtime_deb": Source(
        url=_DEBIAN + "/n/ncurses/libncurses6_6.5+20250216-2_amd64.deb",
        sha256="e00cbcc8c0826993f881f492c05f33ba8d79b5375dc5a2ab59c82e0c7b9179a9"),
    "tinfo_deb": Source(
        url=_DEBIAN + "/n/ncurses/libtinfo6_6.5+20250216-2_amd64.deb",
        sha256="8b9f6a7983e9418564e48a627518de4c03917b56efe68d7f3e93bd8fffa1cc10"),
}
_DEPS_X86 = {
    "readline32_deb": Source(url=_DEBIAN + "/r/readline/libreadline-dev_8.2-6_i386.deb",
        sha256="7e73ca3460f4f01a6c8978642a2cba60fe0816e6a59acebb892adc264ab5eedd"),
    "readline32_runtime_deb": Source(url=_DEBIAN + "/r/readline/libreadline8t64_8.2-6_i386.deb",
        sha256="87f68eeeadde39bc92baff9928b8d392b48b03a45f8027173dcfc46670cd1912"),
    "ncurses32_deb": Source(url=_DEBIAN + "/n/ncurses/libncurses-dev_6.5+20250216-2_i386.deb",
        sha256="9e7e2189dbe0b0440eb1e808ad78b6d6f410a12ea19cd34e118fb4cd03bad495"),
    "ncurses32_runtime_deb": Source(url=_DEBIAN + "/n/ncurses/libncurses6_6.5+20250216-2_i386.deb",
        sha256="c7d36a0324dcd06127d8e730e9c219c5950def935da0e362fd2506a1b92bda55"),
    "tinfo32_deb": Source(url=_DEBIAN + "/n/ncurses/libtinfo6_6.5+20250216-2_i386.deb",
        sha256="3488ab080c07056b2ddef81f3d75fac7358ebfd63ac04a224fa87571152f39b7"),
    "ssl32_deb": Source(url=_DEBIAN + "/o/openssl/libssl-dev_3.5.7-1~deb13u3_i386.deb",
        sha256="a78cd670a342b73ef4015361c1343f6b82da046c287057d7f0ddbf7ba996ca1b"),
    "ssl32_runtime_deb": Source(url=_DEBIAN + "/o/openssl/libssl3t64_3.5.7-1~deb13u3_i386.deb",
        sha256="c6988eab4110e14aa7306a9b32356bc9b699f7f657acdc0211a458f6d91819b5"),
    "zlib32_deb": Source(url=_DEBIAN + "/z/zlib/zlib1g-dev_1.3.dfsg+really1.3.1-1+b1_i386.deb",
        sha256="b5ca31bbc301f5f8be89ef90a1935c826bf562d6f6601e9169709366e3bad263"),
    "zlib32_runtime_deb": Source(url=_DEBIAN + "/z/zlib/zlib1g_1.3.dfsg+really1.3.1-1+b1_i386.deb",
        sha256="8950c79b1ade51f53b2f37863aec532cfaca3dff315e28f0c5b53902425c41ed"),
    "zstd32_deb": Source(url=_DEBIAN + "/libz/libzstd/libzstd1_1.5.7+dfsg-1_i386.deb",
        sha256="305f0ab5f16552c44906b3f3f6e9ad3eb33f6f857c3347fdf3bd987abd6989a9"),
}

_STAGE_X86 = ("mkdir -p deps32 && " + " && ".join(
    "dpkg-deb -x {%s} deps32" % key for key in _DEPS_X86))
_STAGE_X64 = ("mkdir -p deps64 && " + " && ".join(
    "dpkg-deb -x {%s} deps64" % key for key in _DEPS))

_ARTIFACTS = [
    Artifact(path="bin/%s/%s" % (component, component), component=component,
             is_library=True)
    for component in ("vpnserver", "vpnclient", "vpncmd")
]
_ARTIFACTS_X86 = _ARTIFACTS[:1] + [
    Artifact(path="bin/vpnbridge/vpnbridge", component="vpnbridge",
             is_library=True)
] + _ARTIFACTS[1:]

RECIPES = {
    "softether_vpn_stable_4.44_linux": Recipe(
        family="SoftEtherVPN",
        version="4.44-9807-rtm",
        upstream="https://github.com/SoftEtherVPN/SoftEtherVPN_Stable",
        license="Apache-2.0",
        source=Source(
            git_url="https://github.com/SoftEtherVPN/SoftEtherVPN_Stable.git",
            git_ref="ed17437af9719ac66acab30faa29e375d613c35f"),
        extra_sources=_DEPS,
        build=[
            BuildStep(_STAGE_X64),
            BuildStep(
                "make -f src/makefiles/linux_64bit.mak "
                "'CC={cc} " + _WARNINGS + "' -j2 build",
                env={
                    "CPATH": "{source_root}/deps64/usr/include",
                    "LIBRARY_PATH": "{source_root}/deps64/usr/lib/x86_64-linux-gnu",
                }),
        ],
        artifacts=_ARTIFACTS,
        toolchains=["linux_x64"],
        requires=["make", "dpkg-deb"],
        build_flags="-O2 -fsigned-char; GCC 14 compatibility diagnostics: " + _WARNINGS,
        notes="Stable 4.x RTM; the tracker report does not pin a narrower version.",
    ),
    "softether_vpn_stable_4.44_linux_x86": Recipe(
        family="SoftEtherVPN",
        version="4.44-9807-rtm",
        upstream="https://github.com/SoftEtherVPN/SoftEtherVPN_Stable",
        license="Apache-2.0",
        source=Source(
            git_url="https://github.com/SoftEtherVPN/SoftEtherVPN_Stable.git",
            git_ref="ed17437af9719ac66acab30faa29e375d613c35f"),
        extra_sources={**_DEPS, **_DEPS_X86},
        build=[
            BuildStep(_STAGE_X64),
            # hamcorebuilder is executed during the build. Generate the shared
            # resource archive with a native helper on hosts lacking 32-bit
            # ELF execution, then compile the four programs for i386.
            BuildStep("make -f src/makefiles/linux_64bit.mak "
                      "'CC={cc} " + _WARNINGS + "' -j2 tmp/hamcorebuilder && "
                      "tmp/hamcorebuilder src/bin/hamcore/ tmp/hamcore.se2 && "
                      "make -f src/makefiles/linux_64bit.mak clean && "
                      "mkdir -p src/bin/BuiltHamcoreFiles/unix && "
                      "cp tmp/hamcore.se2 src/bin/BuiltHamcoreFiles/unix/hamcore.se2",
                      env={"CPATH": "{source_root}/deps64/usr/include",
                           "LIBRARY_PATH": "{source_root}/deps64/usr/lib/x86_64-linux-gnu"}),
            BuildStep(_STAGE_X86),
            BuildStep("make -f src/makefiles/linux_32bit.mak "
                      "'CC={cc} -m32 " + _WARNINGS +
                      " -Wl,-rpath-link,{source_root}/deps32/usr/lib/i386-linux-gnu' "
                      "-j2 tmp/hamcorebuilder && "
                      "touch src/bin/BuiltHamcoreFiles/unix/hamcore.se2 && "
                      "make -f src/makefiles/linux_32bit.mak "
                      "'CC={cc} -m32 " + _WARNINGS +
                      " -Wl,-rpath-link,{source_root}/deps32/usr/lib/i386-linux-gnu' "
                      "-j2 build",
                      env={"CPATH": "{source_root}/deps32/usr/include:"
                                    "{source_root}/deps32/usr/include/i386-linux-gnu",
                           "LIBRARY_PATH": "{source_root}/deps32/usr/lib/i386-linux-gnu"}),
        ],
        artifacts=_ARTIFACTS_X86,
        toolchains=["linux_x86"],
        requires=["make", "dpkg-deb"],
        build_flags="-O2 -m32 -fsigned-char; GCC 14 compatibility diagnostics: " + _WARNINGS,
        notes="Native hamcore builder supplies the same resource archive before the i386 build.",
    ),
}
