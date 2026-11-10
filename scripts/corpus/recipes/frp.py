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
versions, so each is a narrow band; v0.52.3 (go 1.20, the last release of the
0.52 series, the older pin the issue names) builds the same way and was added
afterwards (the first pass had left it for a decision on size: one version is
8 artefacts and 140 MB of reference data, 10,000 functions per frps image,
nearly all of them dependencies). Measured on the artefacts (PicHash, functions
of 10 or more instructions, frpc and frps together): 75% of v0.52.3's hashes
are in v0.58.1 on x64 (4,536 of 6,042 on Linux, 4,425 of 5,917 on MinGW) and
24% on x86 (2,165 of 8,915 and 2,126 of 8,765); Linux x64 against MinGW x64 of
the same version 92-97% per program. Counts, kept + removed = image total
(removed is the Go glue filter): v0.52.3 frpc x64 Linux 5,438 + 11,141, frps
8,683 + 11,645; x86 Linux 5,303 + 11,189 and 8,591 + 11,689; MinGW x64 5,148 +
11,021 and 8,312 + 11,518; MinGW x86 5,176 + 11,297 and 8,440 + 11,793. Releases from v0.65 need go 1.24.0 in
go.mod and would build here too.

frps embeds its dashboard from assets/frps/static, which upstream does not
commit (`make file` copies in a separately npm-built tree); `go:embed
static/*` fails with an empty directory, so the build adds one empty file
there. No Go source is touched.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._go import GO_BUILD_FLAGS, GO_ENV, GO_TOOLCHAINS


def _frp(version, git_ref, go_directive, notes_extra, go_version=None):
    # go_version None: the host's go1.24.7 with GOTOOLCHAIN=local, like every
    # other Go family. Otherwise GOTOOLCHAIN pins that release, which the host
    # go fetches as golang.org/toolchain through the module proxy and verifies
    # against the checksum database before running it.
    env = GO_ENV if go_version is None else dict(GO_ENV,
                                                 GOTOOLCHAIN=go_version)
    flags = (GO_BUILD_FLAGS if go_version is None
             else GO_BUILD_FLAGS.replace("go1.24.7", go_version))
    built_with = ("go1.24.7 (GOTOOLCHAIN=local)" if go_version is None
                  else "%s (GOTOOLCHAIN=%s; the host go is 1.24.7)"
                  % (go_version, go_version))
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
                      env=env),
            BuildStep("go build -trimpath -tags frps -o frps ./cmd/frps",
                      env=env),
        ],
        artifacts=[Artifact(path="frpc", component="frpc"),
                   Artifact(path="frps", component="frps")],
        toolchains=GO_TOOLCHAINS,
        glue_filter="go",
        build_flags=flags + " (upstream Makefile minus -s -w)",
        notes="Tag %s, built with %s against the "
              "tag's go.mod/go.sum (%s). Applications frpc and frps, not "
              "exercisers. The Go runtime and standard library are removed by "
              "the Go glue filter; the github.com/* and golang.org/x/* "
              "closure is kept under frp's name, including the fatedier/yamux "
              "fork that replaces hashicorp/yamux. assets/frps/static is "
              "empty upstream, so one empty .keep file lets go:embed "
              "resolve (the dashboard is not bundled). %s"
              % (git_ref, built_with, go_directive, notes_extra),
    )


RECIPES = {
    "frp_0.52.3": _frp(
        "0.52.3", "v0.52.3",
        "go 1.20; armon/go-socks5 v0.0.0-20160902184237-e75332964ef5, "
        "hashicorp/yamux v0.1.1 replaced by fatedier/yamux "
        "v0.0.0-20230628132301-7aca4898904d, golang.org/x/net v0.12.0, "
        "quic-go v0.37.4",
        "Commit 44985f574dd3924e9cb48a969fddbd72b3afe2b3; go.sum sha256 "
        "f07603dc26c5f80dd138a7f3bedba270ca500fa87fa5040964286e8720c31f19."),
    "frp_0.58.1": _frp(
        "0.58.1", "v0.58.1",
        "go 1.22; armon/go-socks5 v0.0.0-20160902184237-e75332964ef5, "
        "hashicorp/yamux v0.1.1 replaced by fatedier/yamux "
        "v0.0.0-20230628132301-7aca4898904d, golang.org/x/net v0.24.0, "
        "golang.org/x/crypto v0.22.0",
        "Commit e64969221784b97338e821f6f5606cfaa40177c5; go.sum sha256 "
        "d7ee172182dd6441f7a70d4e581781c4542840cf95dd687eaaf8e94a470e5e3b."),
    # The same two tags with the Go release their go.mod names (go1.20.14 and
    # go1.22.12, the last patch release of each line), beside the go1.24.7
    # images above: the runtime is removed by the filter either way, but the
    # compiler that laid out frp's own code is not the same.
    "frp_0.52.3-go1.20.14": _frp(
        "0.52.3-go1.20.14", "v0.52.3",
        "go 1.20; armon/go-socks5 v0.0.0-20160902184237-e75332964ef5, "
        "hashicorp/yamux v0.1.1 replaced by fatedier/yamux "
        "v0.0.0-20230628132301-7aca4898904d, golang.org/x/net v0.12.0, "
        "quic-go v0.37.4",
        "Commit 44985f574dd3924e9cb48a969fddbd72b3afe2b3; go.sum sha256 "
        "f07603dc26c5f80dd138a7f3bedba270ca500fa87fa5040964286e8720c31f19. "
        "Toolchain golang.org/toolchain v0.0.1-go1.20.14.linux-amd64 "
        "h1:8qw1ZS9f0CG9ty0SLWhGEERyjMSNgfMIR+e1g5RRYb0=.",
        go_version="go1.20.14"),
    "frp_0.58.1-go1.22.12": _frp(
        "0.58.1-go1.22.12", "v0.58.1",
        "go 1.22; armon/go-socks5 v0.0.0-20160902184237-e75332964ef5, "
        "hashicorp/yamux v0.1.1 replaced by fatedier/yamux "
        "v0.0.0-20230628132301-7aca4898904d, golang.org/x/net v0.24.0, "
        "golang.org/x/crypto v0.22.0",
        "Commit e64969221784b97338e821f6f5606cfaa40177c5; go.sum sha256 "
        "d7ee172182dd6441f7a70d4e581781c4542840cf95dd687eaaf8e94a470e5e3b. "
        "Toolchain golang.org/toolchain v0.0.1-go1.22.12.linux-amd64 "
        "h1:Hdh4VJAlDWzMnhKpqDwqJJr+sE7NgsJ86dyR4wrv2oY=.",
        go_version="go1.22.12"),
    # The go 1.24 band: v0.65.0 is the first release whose go.mod says go
    # 1.24.0, built with the host's go1.24.7 like the images above.
    "frp_0.65.0": _frp(
        "0.65.0", "v0.65.0",
        "go 1.24.0",
        "Commit 2f5e1f79457b5e9d769f2ac063443b62640185a9; go.sum sha256 "
        "e36e4b1520f7542c63d23ec0d086c366111a6c0c2bb1b8087948dade0f777030."),
    # The newest release, whose go.mod says go 1.26.0: go1.26.10, the last
    # patch release of that line.
    "frp_0.72.0": _frp(
        "0.72.0", "v0.72.0",
        "go 1.26.0",
        "Commit bafec21abce5f91ae4a05b4bd19c55543c263128; go.sum sha256 "
        "d49411ae549c4023d847d68983ab384c314f921f576b54f0d208b965c24f5255. "
        "Toolchain golang.org/toolchain v0.0.1-go1.26.10.linux-amd64 "
        "h1:5VAGHlY8yl8pTPVSNIez3SNMy6fWabs+QMR25f3oMT0=.",
        go_version="go1.26.10"),
}
