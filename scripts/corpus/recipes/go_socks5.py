"""SOCKS5 servers in Go: armon/go-socks5 and its maintained fork things-go.

armon/go-socks5 was last touched in 2016 and has no go.mod; kost/revsocks and
jpillora/chisel both pin that exact commit. things-go/go-socks5 is a genuine
fork (its LICENSE still reads "Copyright (c) 2014 Armon Dadgar") that
yggstack requires at v0.1.0. They are one family because the fork keeps the
original's server shape - Config/New/ServeConn, Authenticator, CredentialStore,
NameResolver, RuleSet - and differs by functional options, a wire-format
package (statute), a buffer pool, UDP associate and middleware. The two
versions are told apart by version string (armon-e753329 and things-go-0.1.0)
and `validate --deep` shows how much of the code they share.

Neither is an application: each artefact is an exerciser (scripts/corpus/
exercisers/go/go_socks5_*/main.go) that builds a server with the library's own
authenticators, resolver and rule set and serves one CONNECT over net.Pipe.
Beyond the exerciser's own main package the only code in the images is the
library's packages (and one golang.org/x/net/context function in the armon
build). In the things-go build, 21 of the kept functions are named main.*
rather than github.com/things-go/...: the compiler inlined the library's
option closures into main.main, so they carry the caller's name.

armon has no module file, so the recipe places the exerciser's go.mod and
go.sum (golang.org/x/net v0.35.0, the version things-go requires) beside the
source. That is the module handling the dependency needs to be reproducible;
it adds files and changes none of upstream's.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._go import GO_BUILD_FLAGS, GO_ENV, GO_TOOLCHAINS


_EX = "{repo}/scripts/corpus/exercisers/go"


RECIPES = {
    "go_socks5_armon-e753329": Recipe(
        family="go_socks5",
        version="armon-e753329",
        upstream="https://github.com/armon/go-socks5",
        license="MIT",
        source=Source(git_url="https://github.com/armon/go-socks5.git",
                      git_ref="e75332964ef517daa070d7c38a9466a0d687e0a5"),
        build=[
            BuildStep("mkdir -p mcrit_exerciser && cp " + _EX +
                      "/go_socks5_armon/main.go mcrit_exerciser/main.go && "
                      "cp " + _EX + "/go_socks5_armon/go.mod "
                      + _EX + "/go_socks5_armon/go.sum ."),
            BuildStep("go build -trimpath -o go_socks5_exerciser "
                      "./mcrit_exerciser", env=GO_ENV),
        ],
        artifacts=[Artifact(path="go_socks5_exerciser",
                            component="go_socks5_exerciser")],
        toolchains=GO_TOOLCHAINS,
        glue_filter="go",
        build_flags=GO_BUILD_FLAGS,
        notes="Commit e753329 is the 2016-09-02 pseudo-version "
              "v0.0.0-20160902184237-e75332964ef5 that revsocks and chisel "
              "pin. Built with go1.24.7 (GOTOOLCHAIN=local). Upstream has no "
              "go.mod: the recipe adds the exerciser's go.mod (module "
              "github.com/armon/go-socks5, go 1.18, require golang.org/x/net "
              "v0.35.0) and go.sum (sha256 334675d2cdaee03effdf74145f9510c0110cb50b48b7b9fe96d9749babdac15d, see "
              "exercisers/go/go_socks5_armon/go.sum; x/net h1:T5GQRQb2y08kTAB"
              "yq9L4/bz8cipCdA8FbRTXewonqY8=). The artefact is an exerciser "
              "(Server with UserPass/NoAuth, StaticCredentials, DNSResolver, "
              "PermitCommand, one CONNECT over net.Pipe), not an application.",
    ),
    "go_socks5_things-go-0.1.0": Recipe(
        family="go_socks5",
        version="things-go-0.1.0",
        upstream="https://github.com/things-go/go-socks5",
        license="MIT",
        source=Source(git_url="https://github.com/things-go/go-socks5.git",
                      git_ref="v0.1.0"),
        build=[
            BuildStep("mkdir -p mcrit_exerciser && cp " + _EX +
                      "/go_socks5_things_go/main.go mcrit_exerciser/main.go"),
            BuildStep("go build -trimpath -o go_socks5_exerciser "
                      "./mcrit_exerciser", env=GO_ENV),
        ],
        artifacts=[Artifact(path="go_socks5_exerciser",
                            component="go_socks5_exerciser")],
        toolchains=GO_TOOLCHAINS,
        glue_filter="go",
        build_flags=GO_BUILD_FLAGS,
        notes="Tag v0.1.0 is what yggstack requires. Built with go1.24.7 "
              "(GOTOOLCHAIN=local) against upstream's own go.sum (sha256 "
              "1bc114a9324f4921146f6f04f7a8654085dcc6060fe3b713697e9522932b17cd; "
              "golang.org/x/net v0.35.0 h1:T5GQRQb2y08kTAByq9L4/bz8cipCdA8Fb"
              "RTXewonqY8=). The artefact is an exerciser (NewServer with the "
              "library's options, authenticators and middleware, one CONNECT "
              "over net.Pipe, the statute codecs), not an application.",
    ),
}
