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
11,021 and 8,312 + 11,518; MinGW x86 5,176 + 11,297 and 8,440 + 11,793.

Four more versions, built on the Linux runner (runs 42774823191 and
42776975484, scratch branch scratch/s4-go-linux), all four targets each:

  * 0.52.3-go1.20.14 and 0.58.1-go1.22.12: the same two tags compiled by the
    Go release their go.mod names (the last patch of go1.20 and go1.22,
    pinned with GOTOOLCHAIN), beside the go1.24.7 images. The runtime is
    removed either way, but the compiler that lays out frp's own code is a
    different one: of the go1.24.7 image's distinct PicHashes (10+
    instructions) the go1.20.14 build shares 4.2 to 5.3 percent on x64,
    12 to 13 percent on Linux x86 and none on MinGW x86; go1.22.12 shares
    49 to 54 percent on x64 and 23 percent on x86.
  * 0.65.0: the first release of the go 1.24 band (go.mod go 1.24.0), built
    with go1.24.7; against v0.58.1 it shares 72 to 84 percent on x64 and 28
    to 34 percent on x86.
  * 0.72.0: the newest release (go 1.26.0), built with go1.26.10; its
    dashboard moved to web/frpc and web/frps behind `go:embed dist`, which
    upstream does not commit either, so it is built with upstream's own
    `noweb` tag as its Makefile does (no file added). Against v0.65.0 it
    shares 25 to 29 percent on x64 and 11 to 14 percent on x86.

Kept + removed = total (Linux x64 / Linux x86 / MinGW x64 / MinGW x86):

    0.52.3-go1.20.14 frpc 5909+9120 / 5769+9142 / 5791+9177 / 5650+9197
                     frps 9160+9660 / 9016+9678 / 9019+9739 / 8872+9730
    0.58.1-go1.22.12 frpc 6039+9970 / 5540+10006 / 5746+9878 / 5409+10119
                     frps 9982+10522 / 9507+10563 / 9555+10421 / 9350+10673
    0.65.0           frpc 6745+11055 / 6256+11106 / 6154+10936 / 5853+11211
                     frps 11409+11588 / 10949+11639 / 10685+11465 / 10521+11743
    0.72.0           frpc 7624+11914 / 7143+11950 / 6617+11773 / 6374+12076
                     frps 11980+12501 / 11530+12538 / 10829+12355 / 10734+12666

The releases between v0.65.0 and v0.72.0 (v0.66.0 to v0.71.1) are not built;
the family carries the two ends of the go 1.24-1.26 band.

frps embeds its dashboard from assets/frps/static, which upstream does not
commit (`make file` copies in a separately npm-built tree); `go:embed
static/*` fails with an empty directory, so the build adds one empty file
there. No Go source is touched.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._go import GO_BUILD_FLAGS, GO_ENV, GO_TOOLCHAINS


def _frp(version, git_ref, go_directive, notes_extra, go_version=None,
         extra_tags=""):
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
        build=([] if extra_tags else [
            BuildStep("mkdir -p assets/frps/static assets/frpc/static && "
                      "{ [ -n \"$(ls -A assets/frps/static)\" ] || "
                      "touch assets/frps/static/.keep; }")]) + [
            BuildStep("go build -trimpath -tags frpc%s -o frpc ./cmd/frpc"
                      % extra_tags, env=env),
            BuildStep("go build -trimpath -tags frps%s -o frps ./cmd/frps"
                      % extra_tags, env=env),
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
              "fork that replaces hashicorp/yamux. %s%s"
              % (git_ref, built_with, go_directive,
                 "" if extra_tags else
                 "assets/frps/static is empty upstream, so one empty .keep "
                 "file lets go:embed resolve (the dashboard is not "
                 "bundled). ", notes_extra),
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
        "go 1.24.0; armon/go-socks5 v0.0.0-20160902184237-e75332964ef5, "
        "hashicorp/yamux v0.1.1 replaced by fatedier/yamux "
        "v0.0.0-20250825093530-d0154be01cd6, golang.org/x/net v0.39.0, "
        "golang.org/x/crypto v0.37.0, quic-go v0.53.0",
        "Commit 2f5e1f79457b5e9d769f2ac063443b62640185a9; go.sum sha256 "
        "e36e4b1520f7542c63d23ec0d086c366111a6c0c2bb1b8087948dade0f777030."),
    # The newest release, whose go.mod says go 1.26.0: go1.26.10, the last
    # patch release of that line.
    "frp_0.72.0": _frp(
        "0.72.0", "v0.72.0",
        "go 1.26.0; armon/go-socks5 v0.0.0-20160902184237-e75332964ef5, "
        "fatedier/yamux v0.3.0 (a direct dependency here, no longer a "
        "replace of hashicorp/yamux), golang.org/x/net v0.62.0, "
        "golang.org/x/crypto v0.58.0, quic-go v0.65.0",
        "Commit bafec21abce5f91ae4a05b4bd19c55543c263128; go.sum sha256 "
        "d49411ae549c4023d847d68983ab384c314f921f576b54f0d208b965c24f5255. "
        "Toolchain golang.org/toolchain v0.0.1-go1.26.10.linux-amd64 "
        "h1:5VAGHlY8yl8pTPVSNIez3SNMy6fWabs+QMR25f3oMT0=. The dashboard "
        "moved to web/frpc/dist and web/frps/dist (`go:embed dist`), which "
        "upstream does not commit either; its Makefile then adds the noweb "
        "tag (NOWEB_TAG), and so does this build (-tags frpc,noweb and "
        "frps,noweb), so no file is added to the tree for it.",
        go_version="go1.26.10", extra_tags=",noweb"),
}
