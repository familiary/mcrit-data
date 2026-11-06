"""EddieIvan01/iox - port forwarder and SOCKS5 proxy used by Emperor Dragonfly,
Bronze Starlight and the JadeProx operator; Synacktiv identified an
obfuscated sample by its homemade cipher layer (`ExpandKey`, `shuffle`).

Pinned to the last commit, 64235af (2020-09-23): the repository is dormant.
The whole program is the family - 16 files, main + option + operate + netio +
socks5 + crypto (with Yawning/chacha20 vendored under crypto/chacha20) +
logger - and its only dependencies are xtaci/smux v1.5.14 (a second stream
multiplexer next to yamux) and golang.org/x/sys, so building the application
rather than an exerciser costs no dependency bloat.

One mechanical change is needed: upstream's module is named `iox`, with no dot
in the first path element. The Go glue filter reads such a path as the
standard library (baseline.is_go_runtime_symbol) and would delete the whole
program. The build therefore rewrites the module path and the import
strings to github.com/EddieIvan01/iox (go mod edit -module and a sed over the
`"iox/` import prefix). No statement, constant or type is touched; function
bodies are byte-identical, only symbol and package names carry the prefix.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._go import GO_BUILD_FLAGS, GO_ENV, GO_TOOLCHAINS


RECIPES = {
    "iox_0.4": Recipe(
        family="iox",
        version="0.4",
        upstream="https://github.com/EddieIvan01/iox",
        license="MIT",
        source=Source(git_url="https://github.com/EddieIvan01/iox.git",
                      git_ref="64235afced91be39c5436aee76271b0fdb725112"),
        build=[
            BuildStep("go mod edit -module github.com/EddieIvan01/iox && "
                      "grep -rl '\"iox/' --include='*.go' . | "
                      "xargs sed -i 's#\"iox/#\"github.com/EddieIvan01/iox/#'",
                      env=GO_ENV),
            BuildStep("go build -trimpath -o iox .", env=GO_ENV),
        ],
        artifacts=[Artifact(path="iox", component="iox")],
        toolchains=GO_TOOLCHAINS,
        glue_filter="go",
        build_flags=GO_BUILD_FLAGS,
        notes="Commit 64235afced91be39c5436aee76271b0fdb725112 (VERSION 0.4 in "
              "main.go), built with go1.24.7 (GOTOOLCHAIN=local) against "
              "upstream's go.mod (go 1.13) and go.sum (sha256 3ec2c167878322e9f7e7a796685a9a2bb353a307297fdb58abf1249af47d9659): "
              "xtaci/smux v1.5.14 h1:1j+zJYDZRv9FHaWqCJfH5RPizIm0fSzJIFbfVn8zsfg= and "
              "golang.org/x/sys v0.0.0-20200420163511-1957bb5e6d1f h1:gWF768j/LaZugp8dyS4UwsslYCYz9XgFxvlgsn0n9H8=. "
              "crypto/chacha20 is Yawning/chacha20 vendored by upstream. The "
              "module path was rewritten from `iox` to "
              "github.com/EddieIvan01/iox at build time so that the Go glue "
              "filter does not read the package paths as standard library; "
              "no code is changed. The artefact is the iox application.",
    ),
}
