"""fatedier/frp - the fast reverse proxy that Volt Typhoon, Magic Hound,
AppleJeus, MirrorFace and Blue Mockingbird deploy, and that 3CX's supply-chain
intruders renamed to look like Defender (MITRE S1144).

Both programs, frpc and frps, built the way upstream's Makefile builds them
(CGO_ENABLED=0, -trimpath, `-tags frpc` / `-tags frps`) minus `-s -w`, because
the Go glue filter and the symbol check need the symbol table. They are
applications: the evidence is the program, whose pkg/msg control protocol and
pkg/transport are what identify it. The github.com/* and golang.org/x/*
closure stays in the image under frp's name (the filter removes only the Go
runtime and standard library): the fatedier forks of yamux (replace
github.com/hashicorp/yamux => github.com/fatedier/yamux), golib, kcp-go,
quic-go, gorilla/websocket and golang.org/x/crypto and /net. The fork of
yamux is not the hashicorp/yamux v0.1.2 of the yamux family - see the README
row for the PicHash overlap.

v0.58.1 (go 1.22, the last release of the 0.58 series): the newest release
of the band the issue's evidence sits in. pkg/msg changed between minor
versions, so each is a narrow band; v0.52.3 (go 1.20) is the older one the
issue names and builds the same way, but one version is already 8 artefacts
and 140 MB of reference data (10,000 functions per frps image, nearly all of
them dependencies), so it is left for a decision on size. Releases from
v0.65 need go 1.24.0 in go.mod and would build here too.

frps embeds its dashboard from assets/frps/static, which upstream does not
commit (`make file` copies in a separately npm-built tree); `go:embed
static/*` fails with an empty directory, so the build adds one empty file
there. No Go source is touched.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._go import GO_BUILD_FLAGS, GO_ENV, GO_TOOLCHAINS


def _frp(version, git_ref, go_directive, notes_extra):
    return Recipe(
        family="frp",
        version=version,
        upstream="https://github.com/fatedier/frp",
        license="Apache-2.0",
        source=Source(git_url="https://github.com/fatedier/frp.git",
                      git_ref=git_ref),
        build=[
            BuildStep("mkdir -p assets/frps/static assets/frpc/static && "
                      "{ [ -n \"$(ls -A assets/frps/static)\" ] || "
                      "touch assets/frps/static/.keep; }"),
            BuildStep("go build -trimpath -tags frpc -o frpc ./cmd/frpc",
                      env=GO_ENV),
            BuildStep("go build -trimpath -tags frps -o frps ./cmd/frps",
                      env=GO_ENV),
        ],
        artifacts=[Artifact(path="frpc", component="frpc"),
                   Artifact(path="frps", component="frps")],
        toolchains=GO_TOOLCHAINS,
        glue_filter="go",
        build_flags=GO_BUILD_FLAGS + " (upstream Makefile minus -s -w)",
        notes="Tag %s, built with go1.24.7 (GOTOOLCHAIN=local) against the "
              "tag's go.mod/go.sum (%s). Applications frpc and frps, not "
              "exercisers. The Go runtime and standard library are removed by "
              "the Go glue filter; the github.com/* and golang.org/x/* "
              "closure is kept under frp's name, including the fatedier/yamux "
              "fork that replaces hashicorp/yamux. assets/frps/static is "
              "empty upstream, so one empty .keep file lets go:embed "
              "resolve (the dashboard is not bundled). %s"
              % (git_ref, go_directive, notes_extra),
    )


RECIPES = {
    "frp_0.58.1": _frp(
        "0.58.1", "v0.58.1",
        "go 1.22; armon/go-socks5 v0.0.0-20160902184237-e75332964ef5, "
        "hashicorp/yamux v0.1.1 replaced by fatedier/yamux "
        "v0.0.0-20230628132301-7aca4898904d, golang.org/x/net v0.24.0, "
        "golang.org/x/crypto v0.22.0",
        "Commit e64969221784b97338e821f6f5606cfaa40177c5; go.sum sha256 "
        "d7ee172182dd6441f7a70d4e581781c4542840cf95dd687eaaf8e94a470e5e3b."),
}
