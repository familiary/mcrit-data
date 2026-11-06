"""jpillora/chisel - the TCP/UDP tunnel over HTTP and SSH that PYSA and a
number of actors deploy, sometimes wrapped in a DLL (SentinelOne).

The application itself, as the issue's evidence is: its client/, server/ and
share/tunnel/ packages plus the SSH-over-websocket transport. v1.10.1 is the
newest release whose go.mod (go 1.21) the host's go1.24.7 builds with
GOTOOLCHAIN=local: v1.11.0 onwards declares go 1.25, and HEAD asks for
toolchain go1.25.7. chisel's github.com/* and golang.org/x/* dependencies are
kept by the Go glue filter and sit in the image under chisel's name:
golang.org/x/crypto/ssh (golang_x_crypto family) and armon/go-socks5
(go_socks5 family) dominate, then gorilla/websocket and the jpillora
helpers. See the README row for the measured overlap.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._go import GO_BUILD_FLAGS, GO_ENV, GO_TOOLCHAINS


RECIPES = {
    "chisel_1.10.1": Recipe(
        family="chisel",
        version="1.10.1",
        upstream="https://github.com/jpillora/chisel",
        license="MIT",
        source=Source(git_url="https://github.com/jpillora/chisel.git",
                      git_ref="v1.10.1"),
        build=[
            BuildStep("go build -trimpath -o chisel .", env=GO_ENV),
        ],
        artifacts=[Artifact(path="chisel", component="chisel")],
        toolchains=GO_TOOLCHAINS,
        glue_filter="go",
        build_flags=GO_BUILD_FLAGS,
        notes="Tag v1.10.1 (commit 3208da347e4f7d38aa5d9e3def45c4b032dd0b86), built with go1.24.7 (GOTOOLCHAIN=local) against "
              "the tag's go.mod/go.sum (go.sum sha256 97b1535f14475250b3cf37247a7959c4023b8be0178561ea232fa9be23cb817f; go 1.21; armon/go-socks5 "
              "v0.0.0-20160902184237-e75332964ef5 h1:0CwZNZbxp69SHPdPJAN/hZIm0C4OItdklCFmMRWYpio=, golang.org/x/crypto "
              "v0.16.0 h1:mMMrFzRSCF0GvB7Ne27XVtVAaXLrPmgPC7/v0tkwHaY=, golang.org/x/net v0.14.0). The artefact is the "
              "chisel application (client and server in one binary). The Go "
              "runtime and standard library are removed by the Go glue "
              "filter; the github.com/* and golang.org/x/* dependency "
              "closure is kept and is under chisel's name here.",
    ),
}
