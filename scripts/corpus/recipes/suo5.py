"""zema1/suo5 v2.1.0 - the HTTP-tunnel SOCKS5 proxy (Go client) that Synacktiv
found beside a webshell named suo5.aspx and Group-IB recorded as
"suo5 v2.1.0 downloaded directly from github" in a JadeProx intrusion.

Only the client: suo5/ (the tunnel, stream factories and config), ctrl/ (the
SOCKS5 and forward handlers) and netrans/ (frame codec and readers). The
server half is JSP/PHP/ASPX templates, and gui/ is a separate Wails module;
operators deploy the CLI. The artefact is an exerciser
(scripts/corpus/exercisers/go/suo5/main.go) that does what the CLI does
after flag parsing - default config, ctrl.Run, the frame codec - so the
project's packages are linked without urfave/cli.

v2.1.0 only: it is the one version the evidence names, and HEAD declares
go 1.26.x, which this host cannot build and which would change the runtime
code in the image as much as the project's. The tag's go.mod says go 1.20 and
replaces gorilla/websocket v1.5.3 with zema1/websocket
v0.0.0-20240728051525-7fc49edb27c2. Its dependency graph needs go 1.21, which
go1.24 under -mod=readonly rejects, so the build raises the directive
(`go mod edit -go=1.21`) and nothing else; go.sum is unchanged.

The tag links a full uTLS stack (refraction-networking/utls v1.6.7,
HelloRandomizedNoALPN being what Synacktiv quotes), go-gost/gosocks5, the
chainreactors proxyclient and others: they are github.com/* code, so the Go
glue filter keeps them and they sit under suo5's name here. No other family
in this corpus carries utls, so nothing in the image has a better home; the
README row gives the split of project to dependency functions.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._go import GO_BUILD_FLAGS, GO_ENV, GO_TOOLCHAINS


RECIPES = {
    "suo5_2.1.0": Recipe(
        family="suo5",
        version="2.1.0",
        upstream="https://github.com/zema1/suo5",
        license="MIT",
        source=Source(git_url="https://github.com/zema1/suo5.git",
                      git_ref="v2.1.0"),
        build=[
            # The tag's go.mod says go 1.20 but its dependency graph needs
            # 1.21 (circl/utls), which go1.24 under -mod=readonly reports as
            # "updates to go.mod needed". Raising the directive is the whole
            # of the edit; go.sum is untouched.
            BuildStep("go mod edit -go=1.21", env=GO_ENV),
            BuildStep("mkdir -p mcrit_exerciser && cp "
                      "{repo}/scripts/corpus/exercisers/go/suo5/main.go "
                      "mcrit_exerciser/main.go"),
            BuildStep("go build -trimpath -o suo5_exerciser "
                      "./mcrit_exerciser", env=GO_ENV),
        ],
        artifacts=[Artifact(path="suo5_exerciser",
                            component="suo5_exerciser")],
        toolchains=GO_TOOLCHAINS,
        glue_filter="go",
        build_flags=GO_BUILD_FLAGS,
        notes="Tag v2.1.0 (commit 3f51e56b8ad1605458123fb3a8e5c7197a8de454), "
              "built with go1.24.7 (GOTOOLCHAIN=local) against the tag's "
              "go.mod/go.sum (go.sum sha256 227a27d1899d545b6df5cd99b9e209127d1fe49955c9b4001385f06c43e1e521; go 1.20, raised to 1.21 at build time because the "
              "dependency graph needs it; refraction-networking/utls v1.6.7 h1:zVJ7sP1dJx/WtVuITug3qYUq034cDq9B2MR1K67ULZM=, "
              "go-gost/gosocks5 v0.3.0 h1:Hkmp9YDRBSCJd7xywW6dBPT6B9aQTkuWd+3WCheJiJA=, chainreactors/proxyclient v1.0.2, "
              "zema1/rawhttp v0.2.0, golang.org/x/crypto v0.33.0). The "
              "artefact is an exerciser over the CLI's code path, not the CLI "
              "binary. Dependencies are github.com/* code and stay under "
              "suo5's name.",
    ),
}
