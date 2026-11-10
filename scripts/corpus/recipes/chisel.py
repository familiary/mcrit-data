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

The go 1.25 band is built as well, with the Go release each tag's go.mod
toolchain line names (what a default `go build` selects), pinned by
GOTOOLCHAIN: v1.11.8 (the last v1.11.x, go 1.25.0, toolchain go1.25.7) with
go1.25.7 and v1.13.0 (the newest release, go 1.25.0, toolchain go1.27.0)
with go1.27.0. Built on the Linux runner (run 42774823191, scratch branch
scratch/s4-go-linux), kept + removed = total:

    v1.11.8  linux/amd64 1333 + 10551 = 11884   linux/386 1338 + 10595 = 11933
             windows/amd64 1284 + 10385 = 11669 windows/386 1350 + 10661 = 12011
    v1.13.0  linux/amd64 1717 + 11589 = 13306   linux/386 1701 + 11607 = 13308
             windows/amd64 1649 + 11375 = 13024 windows/386 1711 + 11646 = 13357

PicHash overlap (distinct, functions of 10+ instructions), v1.11.8 against
v1.10.1 on the same axis: 539 of 999 (linux/amd64), 549 of 1016
(windows/amd64), 356 of 1069 (linux/386), 370 of 1093 (windows/386); v1.13.0
against v1.11.8: 139 of 1265, 143 of 1280, 141 of 1386, 145 of 1408 (the
go1.27 compiler lays the same code out differently). No pair is identical.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._go import GO_BUILD_FLAGS, GO_ENV, GO_TOOLCHAINS


def _chisel(version, commit, go_version, toolchain_sum, go_sum_sha256,
            pins):
    return Recipe(
        family="chisel",
        version=version,
        upstream="https://github.com/jpillora/chisel",
        license="MIT",
        source=Source(git_url="https://github.com/jpillora/chisel.git",
                      git_ref="v" + version),
        build=[
            BuildStep("go build -trimpath -o chisel .",
                      env=dict(GO_ENV, GOTOOLCHAIN=go_version)),
        ],
        artifacts=[Artifact(path="chisel", component="chisel")],
        toolchains=GO_TOOLCHAINS,
        glue_filter="go",
        build_flags=GO_BUILD_FLAGS.replace("go1.24.7", go_version),
        notes="Tag v%s (commit %s), built with %s (GOTOOLCHAIN=%s, "
              "golang.org/toolchain v0.0.1-%s.linux-amd64 %s; the host go is "
              "1.24.7) against the tag's go.mod/go.sum (go.sum sha256 %s; "
              "%s; armon/go-socks5 v0.0.0-20160902184237-e75332964ef5 "
              "h1:0CwZNZbxp69SHPdPJAN/hZIm0C4OItdklCFmMRWYpio=). The artefact "
              "is the chisel application (client and server in one binary). "
              "The Go runtime and standard library are removed by the Go glue "
              "filter; the github.com/* and golang.org/x/* dependency closure "
              "is kept and is under chisel's name here."
              % (version, commit, go_version, go_version, go_version,
                 toolchain_sum, go_sum_sha256, pins),
    )


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
    # The go 1.25 band (v1.11.0 onwards), which go1.24.7 cannot build. Each tag
    # is built with the release its go.mod's toolchain line names, which is
    # what a default `go build` (GOTOOLCHAIN=auto) selects: GOTOOLCHAIN pins it
    # and the host go fetches it as golang.org/toolchain through the module
    # proxy, verified against the checksum database.
    "chisel_1.11.8": _chisel(
        "1.11.8", "310eec3696e82ef14048268d1d12f1cd99d6dbe9", "go1.25.7",
        "h1:Rn6vCeMS5u+S9P/orrxlLZKvBseZDeUz/S2Jyj+B1EQ=",
        "721c37f843025a94754ec5961a2df887bdeb0ebcedaa1d2a78c8f5ac2a4ab0fe",
        "go 1.25.0, toolchain go1.25.7; golang.org/x/crypto v0.52.0 "
        "h1:RMs7fP2rXdep0CftQlK8Uf+kibLm7qkCcradZWYz988=, golang.org/x/net "
        "v0.54.0, gorilla/websocket v1.5.3"),
    "chisel_1.13.0": _chisel(
        "1.13.0", "5ee6c74d60d96a75afb18bc866eb19327170aeed", "go1.27.0",
        "h1:fVts2HjYwzBWrJtkf1B9HRDAuCZcZLexWI6ZX6Ls/IU=",
        "b2eb96d4506e3c7953407fc62752206eca48f230abf5ea10736b0e043a8cabf6",
        "go 1.25.0, toolchain go1.27.0; golang.org/x/crypto v0.55.0 "
        "h1:+KWHjbgOaAQ66dh/YlkZKHlz9ZUlq61AFirAR9ntP8M=, golang.org/x/net "
        "v0.57.0, gorilla/websocket v1.5.3"),
}
