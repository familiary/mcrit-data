"""kost/revsocks - reverse SOCKS5 over yamux, the tool ESET found copied into
the MythicRatatoskr backdoor.

This is the application, not an exerciser: the issue's evidence is the
program itself (rclient.go, rserver.go, tlshelp.go, rdns.go), and a reverse
proxy has no library API that would select its code. The image therefore
carries revsocks's dependency closure under revsocks's name - the github.com
code the Go glue filter keeps: hashicorp/yamux v0.1.2 and armon/go-socks5
(their own families, yamux and go_socks5),
nhooyr.io/websocket, kost/dnstun, miekg/dns, kost/go-ntlmssp and
golang.org/x/crypto (the golang_x_crypto family).

Measured on linux/amd64: 4170 functions kept, of
which 128 are revsocks's own (package main) and 88 are unnamed; the rest is
miekg/dns (887), google.golang.org/protobuf (about 2,100),
nhooyr.io/websocket (134), x/crypto's acme and autocert (156),
hashicorp/yamux (79) and armon/go-socks5 (35). Of the yamux
family's 65 distinct PicHashes of ten instructions or more, 58 are in this image;
of go_socks5's armon build's 40, 30.

v2.9 rather than HEAD because go.mod there says go 1.25.0 and this host builds
with go1.24.7 and GOTOOLCHAIN=local; v2.9 declares go 1.24.0 and already pins
yamux v0.1.2 and the 2016 armon/go-socks5 commit e753329. v2.7 and v2.8
(go 1.19) pin yamux v0.1.1, which is the older of the two in the wild.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._go import GO_BUILD_FLAGS, GO_ENV, GO_TOOLCHAINS


RECIPES = {
    "revsocks_2.9": Recipe(
        family="revsocks",
        version="2.9",
        upstream="https://github.com/kost/revsocks",
        license="MIT",
        source=Source(git_url="https://github.com/kost/revsocks.git",
                      git_ref="v2.9"),
        build=[
            BuildStep("go build -trimpath -o revsocks .", env=GO_ENV),
        ],
        artifacts=[Artifact(path="revsocks", component="revsocks")],
        toolchains=GO_TOOLCHAINS,
        glue_filter="go",
        build_flags=GO_BUILD_FLAGS,
        notes="Tag v2.9 (commit 0c58dfab9860e1435f7b6dd93552585aa74cbb38), built with go1.24.7 (GOTOOLCHAIN=local) against the "
              "tag's own go.mod/go.sum (go.sum sha256 5da55543ebfdb0121d1d66b37da33a9c0a3987ca89309b12a5167db47a451723; go 1.24.0; "
              "hashicorp/yamux v0.1.2 h1:XtB8kyFOyHXYVFnwT5C3+Bdo8gArse7j2AQ0DA0Uey8=, "
              "armon/go-socks5 v0.0.0-20160902184237-e75332964ef5 h1:0CwZNZbxp69SHPdPJAN/hZIm0C4OItdklCFmMRWYpio=, "
              "golang.org/x/crypto v0.48.0 h1:/VRzVqiRSggnhY7gNRxPauEQ5Drw9haKdM0jqfcCFts=). The artefact is the revsocks "
              "application (client and server in one binary); the Go "
              "runtime and standard library are removed by the Go glue "
              "filter, but github.com/* and golang.org/x/* dependencies are "
              "kept, so a large share of the functions here are yamux, "
              "go-socks5 and x/crypto, which have their own families.",
    ),
    # HEAD, the go 1.25.0 revision issue #75 describes (five commits after
    # v2.9: dependency bumps, golang.org/x/crypto v0.52.0, x/net v0.55.0).
    # go1.24.7 cannot build it, so GOTOOLCHAIN pins go1.25.14, the last patch
    # release of the go 1.25 line (go.mod has no toolchain line); the host go
    # fetches it as golang.org/toolchain through the module proxy, verified
    # against the checksum database.
    "revsocks_2.9-5-gfd268f2": Recipe(
        family="revsocks",
        version="2.9-5-gfd268f2",
        upstream="https://github.com/kost/revsocks",
        license="MIT",
        source=Source(git_url="https://github.com/kost/revsocks.git",
                      git_ref="fd268f2046f340f4bb671413ff589bbc7e94b2ec"),
        build=[
            BuildStep("go build -trimpath -o revsocks .",
                      env=dict(GO_ENV, GOTOOLCHAIN="go1.25.14")),
        ],
        artifacts=[Artifact(path="revsocks", component="revsocks")],
        toolchains=GO_TOOLCHAINS,
        glue_filter="go",
        build_flags=GO_BUILD_FLAGS.replace("go1.24.7", "go1.25.14"),
        notes="master at commit fd268f2046f340f4bb671413ff589bbc7e94b2ec "
              "(2026-07-26, git describe v2.9-5-gfd268f2), built with "
              "go1.25.14 (GOTOOLCHAIN=go1.25.14, golang.org/toolchain "
              "v0.0.1-go1.25.14.linux-amd64 "
              "h1:XriDgll2yv4W2YeUo2X/WuUuy+iGJkXGH0CQloMBEXo=; the host go "
              "is 1.24.7) against the commit's go.mod/go.sum (go.sum sha256 "
              "8ae0cdbcb0eda1a38a21211544abf3ede614d38b0a3453e0f2ccc2c32cfc6a2e; "
              "go 1.25.0; hashicorp/yamux v0.1.2 "
              "h1:XtB8kyFOyHXYVFnwT5C3+Bdo8gArse7j2AQ0DA0Uey8=, "
              "armon/go-socks5 v0.0.0-20160902184237-e75332964ef5 "
              "h1:0CwZNZbxp69SHPdPJAN/hZIm0C4OItdklCFmMRWYpio=, "
              "golang.org/x/crypto v0.52.0 "
              "h1:RMs7fP2rXdep0CftQlK8Uf+kibLm7qkCcradZWYz988=, "
              "nhooyr.io/websocket v1.8.17). The artefact is the revsocks "
              "application (client and server in one binary); the Go "
              "runtime and standard library are removed by the Go glue "
              "filter, but github.com/* and golang.org/x/* dependencies are "
              "kept, so a large share of the functions here are yamux, "
              "go-socks5 and x/crypto, which have their own families.",
    ),
}
