"""tailscale/tailcat - the netcat-like client over Tailscale's data plane that
Kothamine bundles unmodified and launches as tailcat.exe (Malwarebytes).

The application itself: cmd/tailcat, built the way upstream's releases are
(.goreleaser.yaml: CGO_ENABLED=0, -trimpath, the ts_omit_* tag list of
build-tags.txt, -X main.version) minus `-s -w`, because the Go glue filter and
the symbol check need the symbol table.

tailcat is a module client of tailscale.com, not a fork, so the image carries
the part of Tailscale's data plane it imports (magicsock, WireGuard, netstack
over gVisor, DERP, disco, netmon, ...) under tailcat's name: the dependency tail
is most of the kept functions. That is a stated property of the family, not
something this recipe can split; tailscale.com is not a family here.

v0.7.0 (commit 15ab9e68bfc6534a61797d7af28cedd42b54a3a5, 2026-09-17) is the
newest tag before the Malwarebytes report (2026-09-25) and the one whose
tailscale.com pin (v1.103.0-pre.0.20260916030321-a2263542f260) is the latest.
The report gives no version, so the build cannot be tied to the sample.

Toolchain: tailcat's go.mod declares go 1.27.1, newer than the host's
go1.24.7, so GOTOOLCHAIN is pinned to go1.27.1 (the go command fetches and
verifies that toolchain through the module proxy and checksum database); every
other Go recipe uses GOTOOLCHAIN=local.

Measured Go glue baseline (the Go runtime and standard library are removed by
symbol name, glue_filter="go"; see the Go half in scripts/corpus/README.md).
go1.27.1, release tags, kept + removed = total functions per image:

    mingw_x64 (windows/amd64)  9827 + 9018 = 18845
    mingw_x86 (windows/386)   10501 + 9273 = 19774
    linux_x64 (linux/amd64)   11078 + 9208 = 20286
    linux_x86 (linux/386)     11023 + 9223 = 20246

So 46 to 49 percent of every image is runtime or standard library and is not
tailcat's. What is kept is almost all tailscale.com and its dependencies, not
cmd/tailcat: on linux/amd64 the kept 11078 are 3219 gvisor.dev/gvisor/pkg
(netstack), about 2800 tailscale.com packages (net, wgengine, types, util, ipn,
control, derp), 462 golang.org/x/crypto, 331 pkg/sftp, 329
tailscale/wireguard-go, 245 godbus/dbus, 203 fxamacker/cbor, 172 x/net, 132
klauspost/compress, 123 peterbourgon/ff and gaissmai/bart each, 86
tailscale/gliderssh, and only 241 github.com/tailscale/tailcat plus 113 `main`
(the cmd/tailcat package). 402 are compiler-written `type:.eq.`/`.hash.`
functions of those packages. 764 (ELF x64), 748 (ELF x86) and 730 (PE x86)
functions are unnamed and sit between kept neighbours, so the filter keeps
them; the PE x64 image names all of its functions.

PicHashes of functions of 10 or more instructions (distinct): 6543 in linux/amd64,
7715 linux/386, 6144 windows/amd64, 7313 windows/386. The two 64-bit images
share 5696 of them (87 percent of the Linux one); no other pair shares more than
13, so the 32-bit images are independent references.

Overlap with the Go families (same architecture and toolchain, distinct
PicHashes of 10+ instructions): golang_x_crypto 0.37.0 holds 498 to 519, of
which 46 to 51 are in tailcat's image (tailcat links a different x/crypto);
chisel 43 to 51 of 956 to 1059, frpc 44 to 65, frps 91 to 110, yamux 1 to 2,
go_socks5 0. These are x/crypto, x/net and github.com/pkg shapes the
dependencies share; tailcat stays the only family with tailscale.com, gVisor
netstack and wireguard-go.

Not built from this graph: cmd/tailscale. tailscale.com is a dependency of
this module, but the go.sum of the pinned tailcat graph does not cover it:
`go build tailscale.com/cmd/tailscale` fails with `missing go.sum entry for
module providing package golang.org/x/oauth2/clientcredentials (imported by
tailscale.com/feature/oauthkey)` (also github.com/diskfs/go-diskfs and
github.com/skip2/go-qrcode). Fixing that needs `go get`, i.e. unpinned
resolution; cmd/tailscaled does link from this graph, but a Tailscale family
is built from tailscale/tailscale at its own tag and go.sum instead.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._go import GO_ENV, GO_TOOLCHAINS


GO_VERSION = "go1.27.1"

_ENV = dict(GO_ENV, GOTOOLCHAIN=GO_VERSION)

BUILD_FLAGS = (GO_VERSION + " gc, CGO_ENABLED=0, -trimpath, release tags of "
               "build-tags.txt, -X main.version, default optimisation, "
               "unstripped (upstream .goreleaser.yaml minus -s -w)")


def _tailcat(version, commit, go_sum_sha256, tailscale_pin):
    return Recipe(
        family="tailcat",
        version=version,
        upstream="https://github.com/tailscale/tailcat",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/tailscale/tailcat.git",
                      git_ref=commit),
        build=[
            BuildStep("go build -trimpath -tags \"$(cat build-tags.txt)\" "
                      "-ldflags \"-X main.version=v%s\" -o tailcat "
                      "./cmd/tailcat" % version, env=_ENV),
        ],
        artifacts=[Artifact(path="tailcat", component="tailcat")],
        toolchains=GO_TOOLCHAINS,
        glue_filter="go",
        build_flags=BUILD_FLAGS,
        notes="Tag v%s (commit %s), built with %s (GOTOOLCHAIN=%s; the host "
              "go is 1.24.7) against the tag's go.mod/go.sum (go.sum sha256 "
              "%s; tailscale.com %s). Application cmd/tailcat with upstream's "
              "release tags; the Go runtime and standard library are removed "
              "by the Go glue filter, the tailscale.com data plane and every "
              "other github.com/*, golang.org/x/*, gvisor.dev/* and "
              "go4.org/* dependency stays under tailcat's name."
              % (version, commit, GO_VERSION, GO_VERSION, go_sum_sha256,
                 tailscale_pin),
    )


RECIPES = {
    "tailcat_0.7.0": _tailcat(
        "0.7.0", "15ab9e68bfc6534a61797d7af28cedd42b54a3a5",
        "8a1b346e4a2f6b4bc9104aeb7939f13e274651ddcf002d9360fca32d6753feeb",
        "v1.103.0-pre.0.20260916030321-a2263542f260"),
}
