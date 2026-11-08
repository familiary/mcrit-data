"""tailscale/tailscale - the Tailscale node daemon (tailscaled) and its
command-line client (tailscale), built from the repository at its own tag and
its own go.mod/go.sum.

This is the application that tailcat (see tailcat.py) is a module client of:
tailcat imports tailscale.com packages for its data plane, tailscaled is those
packages plus the daemon around them. The two families therefore share
tailscale.com shapes; the overlap is measured in the README row, it is not
removed.

Tag v1.102.5 (tag object 8908149cab706b043db0a3ffb967fbf0bfa9f9eb, commit
5fb2a81b065b0a0bbbfc67ab20a0d9c6a1108115, 2026-09-24) is the newest release tag
before the Malwarebytes report (2026-09-25); v1.104.0 and later are dated after
it. The report gives no version, so the build cannot be tied to the sample.

Build flags follow build_dist.sh: no extra tags (a plain `go build`, TAGS
empty), -trimpath, and the two version stamps as -ldflags -X, minus the
`-w -s` that only the --extra-small/--min/--strip modes add and that would
remove the symbol table the Go glue filter needs. The stamps are
VERSION_SHORT=1.102.5 and VERSION_LONG=1.102.5-1-t5fb2a81b0 (the value
`go run ./cmd/mkversion` prints at the tag commit,
which is what build_dist.sh would stamp; the "-1" is mkversion's own).

Toolchain: go.mod declares go 1.26.6, newer than the host's go1.24.7, so
GOTOOLCHAIN is pinned to go1.26.6 (the go command fetches and verifies it
through the module proxy and checksum database); GOFLAGS=-mod=readonly keeps
go.sum the pin. No source is patched.

The Go runtime and standard library are removed by symbol name
(glue_filter="go"); the counts are in the README row and provenance.json.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._go import GO_ENV, GO_TOOLCHAINS


GO_VERSION = "go1.26.6"

_ENV = dict(GO_ENV, GOTOOLCHAIN=GO_VERSION)

BUILD_FLAGS = (GO_VERSION + " gc, CGO_ENABLED=0, -trimpath, no -tags "
               "(build_dist.sh default), -X version.longStamp/shortStamp, "
               "default optimisation, unstripped (build_dist.sh minus -w -s)")


def _tailscale(version, commit, long_stamp, go_sum_sha256):
    ldflags = ("-X tailscale.com/version.longStamp=%s "
               "-X tailscale.com/version.shortStamp=%s" % (long_stamp, version))
    return Recipe(
        family="tailscale",
        version=version,
        upstream="https://github.com/tailscale/tailscale",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/tailscale/tailscale.git",
                      git_ref=commit),
        build=[
            BuildStep("go build -trimpath -ldflags \"%s\" -o tailscaled "
                      "./cmd/tailscaled" % ldflags, env=_ENV),
            BuildStep("go build -trimpath -ldflags \"%s\" -o tailscale "
                      "./cmd/tailscale" % ldflags, env=_ENV),
        ],
        artifacts=[Artifact(path="tailscaled", component="tailscaled"),
                   Artifact(path="tailscale", component="tailscale")],
        toolchains=GO_TOOLCHAINS,
        glue_filter="go",
        build_flags=BUILD_FLAGS,
        notes="Tag v%s (commit %s), built with %s (GOTOOLCHAIN=%s; the host "
              "go is 1.24.7) against the tag's own go.mod/go.sum (go.sum "
              "sha256 %s). cmd/tailscaled and cmd/tailscale with the "
              "build_dist.sh flags (no tags, -trimpath, version stamps) "
              "minus -w -s; the Go runtime and standard library are removed "
              "by the Go glue filter, tailscale.com and every other "
              "dependency stays under the tailscale name."
              % (version, commit, GO_VERSION, GO_VERSION, go_sum_sha256),
    )


RECIPES = {
    "tailscale_1.102.5": _tailscale(
        "1.102.5", "5fb2a81b065b0a0bbbfc67ab20a0d9c6a1108115",
        "1.102.5-1-t5fb2a81b0",
        "b52dcc94289be95d6b2f1d3f5766b308bc1f9d99425c6f6dbb8df6bdee148816"),
}
