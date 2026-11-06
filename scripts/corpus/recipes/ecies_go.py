"""ecies/go - the ECIES wrapper Prince-derived Go ransomware uses to seal a
per-file ChaCha20 key (Prince, Yurei, CrazyHunter and the other builds of that
lineage).

v2.0.11 is the newest tag and builds with go1.24 (go.mod: go 1.23.0, toolchain
go1.24.2). The mirrors of Prince-Ransomware the issue names were not needed:
the library is pinned directly, and its x/crypto is the golang_x_crypto
family (v0.37.0, the version this module requires).

With CGO_ENABLED=0 the library's secp256k1_nocgo.go selects
github.com/decred/dcrd/dcrec/secp256k1/v4 v4.4.0; that is the curve arithmetic
in the image. go-ethereum (required by the cgo variant) is in the module graph
and not linked. The decred package is not a family of its own in this corpus,
so its functions stay under ecies_go: on linux/amd64, 75 functions are kept,
17 of them ecies/go's own, 53 decred secp256k1, 4 x/crypto/hkdf (also in
golang_x_crypto) and the exerciser's main.

The artefact is an exerciser (scripts/corpus/exercisers/go/ecies_go/main.go)
built inside the module, calling key generation, hex/byte round-trips, ECDH,
Encapsulate/Decapsulate and Encrypt/Decrypt.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._go import GO_BUILD_FLAGS, GO_ENV, GO_TOOLCHAINS


RECIPES = {
    "ecies_go_2.0.11": Recipe(
        family="ecies_go",
        version="2.0.11",
        upstream="https://github.com/ecies/go",
        license="MIT",
        source=Source(git_url="https://github.com/ecies/go.git",
                      git_ref="v2.0.11"),
        build=[
            BuildStep("mkdir -p mcrit_exerciser && cp "
                      "{repo}/scripts/corpus/exercisers/go/ecies_go/main.go "
                      "mcrit_exerciser/main.go"),
            BuildStep("go build -trimpath -o ecies_go_exerciser "
                      "./mcrit_exerciser", env=GO_ENV),
        ],
        artifacts=[Artifact(path="ecies_go_exerciser",
                            component="ecies_go_exerciser")],
        toolchains=GO_TOOLCHAINS,
        glue_filter="go",
        build_flags=GO_BUILD_FLAGS,
        notes="Commit fa5c418edb5db72e763a21a38ca40ab1ed100149 (v2.0.11). Built "
              "with go1.24.7 (GOTOOLCHAIN=local, CGO_ENABLED=0) against "
              "upstream's go.sum (sha256 741987f26d4988dfe6e36834dce65541f74698d38dccdd8c12ab385c67a06fbd; the linked "
              "modules are decred/dcrd/dcrec/secp256k1/v4 v4.4.0 "
              "h1:NMZiJj8QnKe1LgsbDayM4UoHwbvwDRwnI3hwNaAHRnc= and "
              "golang.org/x/crypto v0.37.0 "
              "h1:kJNSjF/Xp7kU0iB2Z+9viTPMW4EqqsrywMXLJOOsXSE=). The "
              "artefact is an exerciser, not an application.",
    ),
}
