"""yggdrasil-network/yggdrasil-go and yggstack - the mesh node, and the
user-space wrapper around it, that MythicRatatoskr (UAC-0099 / Sandworm) is
based on; ESET says "based on yggstack" but cites yggdrasil-go files
(address.go, config.go). Which of the two is the subject is undecided, so
both are built as their own family.

yggdrasil: tag v0.5.15 (commit 2c7f050fc5398ecd8ac5f77e9bb5bd91aa2e9e35), the
tag yggstack 1.0.6 requires. cmd/yggdrasil (the node) and cmd/yggdrasilctl
(its admin client), built the way upstream's `build` script builds them
(CGO_ENABLED=0, -trimpath, -X version.buildName/buildVersion) minus `-s -w`,
because the Go glue filter and the symbol check need the symbol table. The
node's dependencies stay under its name: Arceliar/ironwood (the routing
protocol) and phony, quic-go, coder/websocket, gologme/log, hjson,
golang.org/x/{crypto,net,sys,text}, bits-and-blooms/bloom and, on Windows,
golang.zx2c4.com/wireguard (the tun package) and wireguard/windows. wintun.dll
is loaded at run time and is not part of the image; it is not harvested here.

yggstack: tag 1.0.6 (commit 91fc38063dd7044c1c18318d8907bcc68e95db0d),
cmd/yggstack, which links yggdrasil-go v0.5.15 as a module (so the node core is
inside every yggstack image, under yggstack's name) plus gVisor netstack
(gvisor.dev/gvisor), things-go/go-socks5 v0.1.3 (the go_socks5 family on the
Go group branch) and golang.org/x/time.

Both tags declare go 1.26.0, newer than the host's go1.24.7, so GOTOOLCHAIN is
pinned to go1.26.0 (fetched and verified through the module proxy and
checksum database) instead of the `local` the other Go recipes use.

Licences are recorded as facts: both repositories are LGPL-3.0 with the
"As a special exception to the GNU Lesser General Public License version 3"
text at the top of the LICENSE file; whether to ship them is a maintainer
decision, not a technical one.

Measured Go glue baseline (the Go runtime and standard library are removed by
symbol name, glue_filter="go"; see the Go half in scripts/corpus/README.md).
Kept + removed = total functions per image:

    yggdrasil    windows/amd64  2481 +  8429 = 10910   linux/amd64  2890 +  8700 = 11590
                 windows/386    2576 +  8633 = 11209   linux/386    2894 +  8694 = 11588
    yggdrasilctl windows/amd64  1235 +  7349 =  8584   linux/amd64  1220 +  7487 =  8707
                 windows/386    1226 +  7488 =  8714   linux/386    1198 +  7476 =  8674
    yggstack     windows/amd64  5556 +  8500 = 14056   linux/amd64  6037 +  8685 = 14722
                 windows/386    5824 +  8707 = 14531   linux/386    6022 +  8681 = 14703

So 59 to 87 percent of an image is runtime or standard library. What is kept is
mostly dependencies, not the project: on linux/amd64 yggdrasil's 2890 are 935
quic-go, 399 yggdrasil-go itself, 321 Arceliar/ironwood, 165 x/net, 160
compiler-written `type:` functions, 94 coder/websocket, 84 vishvananda/netlink,
77 x/sys, 65 hjson, 57 x/crypto; yggdrasilctl's 1220 are 586 goccy/go-json, 160
olekukonko/tablewriter and only 5 yggdrasil-go; yggstack's 6037 are 2875 gVisor
netstack, 935 quic-go, 372 yggdrasil-go, 323 ironwood, 48 yggstack, 47
things-go/go-socks5. Unnamed functions between kept neighbours are kept (105,
13 and 290 on linux/amd64; the PE x64 images name every function).

Distinct PicHashes of 10+ instructions, linux/amd64: yggdrasil 2111, yggdrasilctl
991, yggstack 3587 (windows/amd64 1889, 1014, 3447). The two 64-bit images of a
program share most of them (yggdrasil 1670, yggdrasilctl 940, yggstack 3306); the
32-bit pairs share 0, 0 and 9, and no 32-bit image shares any with a 64-bit one.
yggstack contains the node core: 1899 of yggdrasil's 2111 linux/amd64 PicHashes
(1773 of 1889 on windows/amd64; 770 and 716 on the 32-bit images) are also in
yggstack, so a yggstack match is a yggdrasil match plus gVisor. yggdrasil and
yggdrasilctl share 190 (linux/amd64). Against the Go group families on the same
axis: golang_x_crypto 16 to 28, chisel 26 to 42, go_socks5 things-go 1 to 13 (yggstack
links it), armon 1 to 4, yamux 1 to 2.

wintun.dll, which the node loads on Windows, is a prebuilt signed binary and is
not harvested here.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._go import GO_ENV, GO_TOOLCHAINS


GO_VERSION = "go1.26.0"

_ENV = dict(GO_ENV, GOTOOLCHAIN=GO_VERSION)

_VERSION_PKG = "github.com/yggdrasil-network/yggdrasil-go/src/version"

BUILD_FLAGS = (GO_VERSION + " gc, CGO_ENABLED=0, -trimpath, "
               "-X version.buildName/buildVersion, default optimisation, "
               "unstripped (upstream build script minus -s -w)")


def _ldflags(name, version):
    return ("-X %s.buildName=%s -X %s.buildVersion=%s"
            % (_VERSION_PKG, name, _VERSION_PKG, version))


def _recipe(family, version, upstream, commit, tag, go_sum, cmds, notes):
    return Recipe(
        family=family,
        version=version,
        upstream=upstream,
        license="LGPL-3.0-only WITH linking exception",
        source=Source(git_url=upstream + ".git", git_ref=commit),
        build=[BuildStep("go build -trimpath -ldflags \"%s\" -o %s ./cmd/%s"
                         % (_ldflags(family, version), c, c), env=_ENV)
               for c in cmds],
        artifacts=[Artifact(path=c, component=c) for c in cmds],
        toolchains=GO_TOOLCHAINS,
        glue_filter="go",
        build_flags=BUILD_FLAGS,
        notes="Tag %s (commit %s), built with %s (GOTOOLCHAIN=%s; the host go "
              "is 1.24.7) against the tag's go.mod/go.sum (go.sum sha256 %s). "
              "%s The Go runtime and standard library are removed by the Go "
              "glue filter; every github.com/*, golang.org/x/*, gvisor.dev/* "
              "and golang.zx2c4.com/* dependency stays under this family's "
              "name."
              % (tag, commit, GO_VERSION, GO_VERSION, go_sum, notes),
    )


RECIPES = {
    "yggdrasil_0.5.15": _recipe(
        "yggdrasil", "0.5.15",
        "https://github.com/yggdrasil-network/yggdrasil-go",
        "2c7f050fc5398ecd8ac5f77e9bb5bd91aa2e9e35", "v0.5.15",
        "5ce1bfaf024bfa09acb5643edb97229ec8e6896272384d09add7f17731f826a5",
        ["yggdrasil", "yggdrasilctl"],
        "Applications cmd/yggdrasil and cmd/yggdrasilctl."),
    "yggstack_1.0.6": _recipe(
        "yggstack", "1.0.6",
        "https://github.com/yggdrasil-network/yggstack",
        "91fc38063dd7044c1c18318d8907bcc68e95db0d", "1.0.6",
        "d1f52654de576caaf29a941ebde47e73b165844503e67d480567241143f2a389",
        ["yggstack"],
        "Application cmd/yggstack; yggdrasil-go v0.5.15 is linked as a "
        "module."),
}
