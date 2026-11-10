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

v0.1.0, v0.2.0 and v0.3.0 (commits 915c134b9604, a34089b378fe, cb1e0d753e9a,
2026-08-30) are the first three tags. They differ from v0.4.0 and later in
two ways, so they use their own recipe shape (_tailcat_untagged):

  * No build-tags.txt. Upstream's own build instructions for these tags are
    the README's

        $ go install github.com/tailscale/tailcat/cmd/tailcat@latest

    and the release config .goreleaser.yaml, whose only build settings are

        env:
          - CGO_ENABLED=0
        ldflags:
          - -s -w -X main.version=v{{ .Version }}

    with no `flags:` entry, so no -tags at all (v0.4.0 is the first tag
    whose .goreleaser.yaml has `flags: - -tags=netgo,...,ts_omit_*`). The
    build here is that: CGO_ENABLED=0, -X main.version, no tags, minus
    `-s -w` as for every Go recipe (the Go glue filter needs the symbol
    table). -trimpath is the corpus convention for every Go recipe and is
    kept so these images are comparable with v0.4.0 to v0.7.0; it changes
    file paths in the binary, not code. Without the ts_omit_* tags the images
    carry the tailscale.com features v0.4.0 drops (more tailscale.com code,
    hence 12,8xx kept functions on linux/amd64 against v0.4.0's 10,758).
  * go.mod reads `go 1.26.5` with no toolchain line, so a go1.26 toolchain
    builds them. They are pinned to go1.26.6 (GOTOOLCHAIN=go1.26.6, the same
    pin the tailscale recipe on the tailscale branch uses), fetched by the go
    command as module golang.org/toolchain@v0.0.1-go1.26.6.linux-amd64 and
    verified against the checksum database (h1:owmNw4SPM9h46FGOeGJVUWzFEEDSmO6g7gAtWoXp28s=,
    zip sha256 6347bdd1fdc7c659d955d8034cd82ec23a5b776bf48b9dfc3a75088d2dacfe0e;
    the go.dev/dl go1.26.6.linux-amd64.tar.gz sha256 is
    708effb774be8237570d0add163225abbdfaf4fca28b2611df167beba4feef89). Every
    one of the twelve binaries reports go1.26.6 (`go version`).

All three tags share one go.mod/go.sum (go.sum sha256 274f3f126eeb...,
tailscale.com v1.101.0-pre.0.20260720143344-246c82a658b3). Built locally by
cross-compiling from linux/amd64. Kept + removed = total:

               windows/amd64          windows/386            linux/amd64            linux/386
    v0.1.0  10959 + 10013 = 20972  11712 + 10287 = 21999  12820 + 10223 = 23043  12800 + 10244 = 23044
    v0.2.0  10959 + 10012 = 20971  11712 + 10287 = 21999  12820 + 10223 = 23043  12800 + 10244 = 23044
    v0.3.0  10986 + 10013 = 20999  11740 + 10287 = 22027  12848 + 10223 = 23071  12828 + 10244 = 23072

PicHash overlap (distinct PicHashes of functions of 10+ instructions; sets of
6807/8066/7603/8899 for v0.1.0 and v0.2.0, 6817/8080/7613/8913 for v0.3.0,
in the column order above). No two versions are PicHash-identical on any axis:

    v0.1.0 vs v0.2.0: 6806, 5253, 7602, 5724 shared (one hash differs on each
        64-bit axis: the only linked code change is the new length check in
        NodePublic.UnmarshalBinary; 64-65 percent on the 32-bit axes)
    v0.2.0 vs v0.3.0: 6774, 2424, 7570, 2682 shared (99.4-99.6 percent on
        64-bit, 30 percent on 32-bit)
    v0.3.0 vs v0.4.0: 1832, 1321, 2119, 1500 shared (27-33 percent on 64-bit,
        16-20 percent on 32-bit: the release tags and the newer tailscale.com
        pin of v0.4.0 change most of the image)

As with v0.4.0 against v0.5.0 (30 percent on 386, 99 percent on amd64), the
32-bit Go images move far more between near-identical sources than the
64-bit ones do, so v0.2.0 is kept beside v0.1.0 although its 64-bit images
are near-duplicates.

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

# v0.1.0 to v0.3.0: go.mod reads go 1.26.5 (no toolchain line); go1.26.6 is
# the go1.26 pin the tailscale recipe uses.
GO_VERSION_126 = "go1.26.6"

_ENV_126 = dict(GO_ENV, GOTOOLCHAIN=GO_VERSION_126)

BUILD_FLAGS_126 = (GO_VERSION_126 + " gc, CGO_ENABLED=0, -trimpath, no -tags "
                   "(the tag has no build-tags.txt), -X main.version, default "
                   "optimisation, unstripped (upstream .goreleaser.yaml minus "
                   "-s -w)")

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


def _tailcat_untagged(version, commit, go_sum_sha256, tailscale_pin):
    """v0.1.0 to v0.3.0: no build-tags.txt, no -tags, go1.26.6."""
    return Recipe(
        family="tailcat",
        version=version,
        upstream="https://github.com/tailscale/tailcat",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/tailscale/tailcat.git",
                      git_ref=commit),
        build=[
            BuildStep("go build -trimpath "
                      "-ldflags \"-X main.version=v%s\" -o tailcat "
                      "./cmd/tailcat" % version, env=_ENV_126),
        ],
        artifacts=[Artifact(path="tailcat", component="tailcat")],
        toolchains=GO_TOOLCHAINS,
        glue_filter="go",
        build_flags=BUILD_FLAGS_126,
        notes="Tag v%s (commit %s), built with %s (GOTOOLCHAIN=%s; the host "
              "go is 1.24.7, the tag's go.mod reads go 1.26.5) against the "
              "tag's go.mod/go.sum (go.sum sha256 %s; tailscale.com %s). "
              "Application cmd/tailcat with no build tags: this tag has no "
              "build-tags.txt and its .goreleaser.yaml passes no -tags, so "
              "the image carries the tailscale.com features that the "
              "ts_omit_* tags of v0.4.0 and later leave out. The Go runtime "
              "and standard library are removed by the Go glue filter, the "
              "tailscale.com data plane and every other github.com/*, "
              "golang.org/x/*, gvisor.dev/* and go4.org/* dependency stays "
              "under tailcat's name."
              % (version, commit, GO_VERSION_126, GO_VERSION_126,
                 go_sum_sha256, tailscale_pin),
    )


_GO_SUM_01X = "274f3f126eeba7dd81192ba6a20a10e1613a71910bc25163a995707d41efc41b"
_TAILSCALE_01X = "v1.101.0-pre.0.20260720143344-246c82a658b3"

RECIPES = {
    "tailcat_0.1.0": _tailcat_untagged(
        "0.1.0", "915c134b9604300ceefaff925d215f6dcfdfc94d",
        _GO_SUM_01X, _TAILSCALE_01X),
    "tailcat_0.2.0": _tailcat_untagged(
        "0.2.0", "a34089b378fea36d49ea2276d83b9237a32bb338",
        _GO_SUM_01X, _TAILSCALE_01X),
    "tailcat_0.3.0": _tailcat_untagged(
        "0.3.0", "cb1e0d753e9ace2ebc5bff147ccf1eee6ccdd463",
        _GO_SUM_01X, _TAILSCALE_01X),
    "tailcat_0.4.0": _tailcat(
        "0.4.0", "ce6fedcabc220bab3b94d470ab330219111eeae8",
        "ff7c683fd11ba420004e22437bcd6c4e7cd36f23eab8e7a68188a706fbc86d85",
        "v1.103.0-pre.0.20260830144538-72780705eda8"),
    "tailcat_0.5.0": _tailcat(
        "0.5.0", "cc6db4948e324e2c3434155a13d0d787ec9df7a4",
        "ff7c683fd11ba420004e22437bcd6c4e7cd36f23eab8e7a68188a706fbc86d85",
        "v1.103.0-pre.0.20260830144538-72780705eda8"),
    "tailcat_0.6.0": _tailcat(
        "0.6.0", "790406204c002a6f109ef7c6a30a436601a1f6a8",
        "ad835c5a36913f461826189746619fffbba97feef9ab18d9f7c51f10be9fb34f",
        "v1.103.0-pre.0.20260904030409-31d8badb3bfb"),
    "tailcat_0.7.0": _tailcat(
        "0.7.0", "15ab9e68bfc6534a61797d7af28cedd42b54a3a5",
        "8a1b346e4a2f6b4bc9104aeb7939f13e274651ddcf002d9360fca32d6753feeb",
        "v1.103.0-pre.0.20260916030321-a2263542f260"),
}
