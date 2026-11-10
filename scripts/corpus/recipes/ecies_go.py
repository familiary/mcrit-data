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

v2.0.10 is the Go 1.22 band issue #10 asks for (Go 1.21.x/1.22.x pins): the
same exerciser built with go1.22.12, the last go1.22 patch release, pinned
with GOTOOLCHAIN (see recipes/_go.py). It is the newest tag a go1.22
toolchain accepts: its go.mod says go 1.22 (the toolchain go1.23.3 line is
ignored under a pinned GOTOOLCHAIN), v2.0.11 says go 1.23.0. Its go.sum links
decred secp256k1 v4.3.0 and golang.org/x/crypto v0.31.0, both go 1.20 or
older, so this image carries an x/crypto/hkdf that is not the golang_x_crypto
0.33.0 one.

2.0.10 is built for windows/amd64, windows/386 and linux/386 only. Its
linux/amd64 image was built and measured: the same 75 kept functions and the
same 71 distinct PicHashes of ten instructions or more as the windows/amd64
image (the set is identical, also counting the short functions), so it adds
nothing and is not carried. Kept + removed = total: windows/amd64 75 + 2,277 =
2,352, windows/386 77 + 2,326 = 2,403, linux/386 77 + 2,298 = 2,375 (the
dropped linux/amd64 75 + 2,281 = 2,356). Against 2.0.11 on the same axis
22 of 71 (amd64) and 22 of 76 (386) hashes are shared: decred secp256k1
v4.3.0 against v4.4.0 and x/crypto v0.31.0 against v0.37.0 compile to
different bodies under go1.22.12.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._go import (GO122_BUILD_FLAGS, GO122_ENV, GO122_PIN, GO122_VERSION,
                  GO_BUILD_FLAGS, GO_ENV, GO_TOOLCHAINS)


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
    "ecies_go_2.0.10": Recipe(
        family="ecies_go",
        version="2.0.10",
        upstream="https://github.com/ecies/go",
        license="MIT",
        source=Source(git_url="https://github.com/ecies/go.git",
                      git_ref="v2.0.10"),
        build=[
            BuildStep("mkdir -p mcrit_exerciser && cp "
                      "{repo}/scripts/corpus/exercisers/go/ecies_go/main.go "
                      "mcrit_exerciser/main.go"),
            BuildStep("go build -trimpath -o ecies_go_exerciser "
                      "./mcrit_exerciser", env=GO122_ENV),
        ],
        artifacts=[Artifact(path="ecies_go_exerciser",
                            component="ecies_go_exerciser")],
        # linux/amd64 is PicHash-identical to windows/amd64 (see above).
        toolchains=[t for t in GO_TOOLCHAINS if t != "linux_x64"],
        glue_filter="go",
        build_flags=GO122_BUILD_FLAGS,
        notes="Commit a2072b41c2aae788a740b4bc884fe399480494c5 (v2.0.10, "
              "go.mod: go 1.22, toolchain go1.23.3; the newest tag a go1.22 "
              "toolchain accepts, v2.0.11 declares go 1.23.0). Built with "
              + GO122_VERSION + " (" + GO122_PIN + ", CGO_ENABLED=0) against "
              "upstream's go.sum (sha256 7fb1a08003d2e0d7d48a76a79b784398e5685"
              "b356d2fa2d3deca7f52a2d0113b; the linked modules are "
              "decred/dcrd/dcrec/secp256k1/v4 v4.3.0 "
              "h1:rpfIENRNNilwHwZeG5+P150SMrnNEcHYvcCuK6dPZSg= and "
              "golang.org/x/crypto v0.31.0 "
              "h1:ihbySMvVjLAeSH1IbfcRTkD/iNscyz8rGzjF/E5hV6U=). The "
              "artefact is the same exerciser as 2.0.11, not an application.",
    ),
}
