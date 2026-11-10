"""golang.org/x/crypto - the cryptography every Go network tool links.

chisel's SSH-over-websocket transport, revsocks, frp's and tailcat's TLS and
WireGuard pieces, and the ransomware lineage built on Prince's ChaCha20 and
ECIES all reach it. v0.37.0 is the version ecies/go v2.0.11 requires and it
fits go1.24 (go.mod says go 1.23.0); newer releases ask for toolchains newer
than the one this host builds with.

The artefact is an exerciser (scripts/corpus/exercisers/go/x_crypto/main.go)
built inside the x/crypto module: it calls ChaCha20, ChaCha20-Poly1305 and
XChaCha20-Poly1305, Poly1305, Salsa20, HKDF, PBKDF2, scrypt, argon2, bcrypt,
SHA-3, BLAKE2, MD4, RIPEMD-160, Curve25519, NaCl box and secretbox, Blowfish,
Twofish, CAST5, TEA and XTEA, and runs an ssh server and client handshake over
net.Pipe. Everything outside those packages (x/crypto/ocsp, x509roots, openpgp,
pkcs12, acme, ...) is not referenced and so not in the image.

x/sys is the one other module in the image (cpu feature detection, a handful
of functions); it is a dependency, not a family.

v0.33.0 is the Go 1.22 band issue #10 asks for (Go 1.21.x/1.22.x pins): the
same exerciser built with go1.22.12, the last go1.22 patch release, pinned
with GOTOOLCHAIN (see recipes/_go.py). It is the newest x/crypto whose go.mod
a go1.22 toolchain accepts: v0.33.0 says go 1.20, v0.34.0 and every later
release say go 1.23.0 (proxy.golang.org .mod files), which go1.22.12 refuses
with GOTOOLCHAIN pinned. Its own go.sum pins x/sys v0.30.0 (go 1.18).
Kept + removed = total: linux/amd64 591 + 3,008 = 3,599, linux/386
577 + 3,025 = 3,602, windows/amd64 582 + 2,949 = 3,531, windows/386
577 + 3,007 = 3,584. PicHashes of ten instructions or more shared with
v0.37.0 on the same axis: 229 of 501 (linux/amd64), 229 of 500
(windows/amd64), 81 of 517 (linux/386), 83 of 519 (windows/386); no image is
identical to another.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._go import (GO122_BUILD_FLAGS, GO122_ENV, GO122_PIN, GO122_VERSION,
                  GO_BUILD_FLAGS, GO_ENV, GO_TOOLCHAINS)


RECIPES = {
    "golang_x_crypto_0.37.0": Recipe(
        family="golang_x_crypto",
        version="0.37.0",
        upstream="https://github.com/golang/crypto",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/golang/crypto.git",
                      git_ref="v0.37.0"),
        build=[
            BuildStep("mkdir -p mcrit_exerciser && cp "
                      "{repo}/scripts/corpus/exercisers/go/x_crypto/main.go "
                      "mcrit_exerciser/main.go"),
            BuildStep("go build -trimpath -o x_crypto_exerciser "
                      "./mcrit_exerciser", env=GO_ENV),
        ],
        artifacts=[Artifact(path="x_crypto_exerciser",
                            component="x_crypto_exerciser")],
        toolchains=GO_TOOLCHAINS,
        glue_filter="go",
        build_flags=GO_BUILD_FLAGS,
        notes="Commit 959f8f3db0fb8c3fb1f9507101058dda21e1fdcf (v0.37.0). Built "
              "with go1.24.7 (GOTOOLCHAIN=local) against upstream's own go.sum "
              "(sha256 44b3dd1413c4528376f4941a89daaf3354edbb30ca57fb742ba26596"
              "bb16623f): golang.org/x/sys v0.32.0 "
              "h1:s77OFDvIQeibCmezSnk/q6iAfkdiQaJi4VzroCFrN20=, x/term v0.31.0, "
              "x/net v0.21.0, x/text v0.24.0 (the last three are in the module "
              "graph and not linked). The artefact is an exerciser built "
              "inside the module, not an application; the Go runtime and "
              "standard library, including the private vendor/ copies of "
              "x/crypto packages, are removed by the Go glue filter.",
    ),
    "golang_x_crypto_0.33.0": Recipe(
        family="golang_x_crypto",
        version="0.33.0",
        upstream="https://github.com/golang/crypto",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/golang/crypto.git",
                      git_ref="v0.33.0"),
        build=[
            BuildStep("mkdir -p mcrit_exerciser && cp "
                      "{repo}/scripts/corpus/exercisers/go/x_crypto/main.go "
                      "mcrit_exerciser/main.go"),
            BuildStep("go build -trimpath -o x_crypto_exerciser "
                      "./mcrit_exerciser", env=GO122_ENV),
        ],
        artifacts=[Artifact(path="x_crypto_exerciser",
                            component="x_crypto_exerciser")],
        toolchains=GO_TOOLCHAINS,
        glue_filter="go",
        build_flags=GO122_BUILD_FLAGS,
        notes="Commit 9290511cd23ab9813a307b7f2615325e3ca98902 (v0.33.0, "
              "go.mod: go 1.20; the newest x/crypto a go1.22 toolchain "
              "accepts, v0.34.0 onwards declare go 1.23.0). Built with "
              + GO122_VERSION + " (" + GO122_PIN + ") against upstream's own "
              "go.sum (sha256 d78bc2613b5abfbfa260b564e26df01ef139a6d46779663"
              "386b123a61809817b): golang.org/x/sys v0.30.0 "
              "h1:QjkSwP/36a20jFYWkSue1YwXzLmsV5Gfq7Eiy72C1uc=, x/term "
              "v0.29.0, x/net v0.21.0, x/text v0.22.0 (the last three are in "
              "the module graph and not linked). The artefact is the same "
              "exerciser as 0.37.0, built inside the module; the Go runtime "
              "and standard library are removed by the Go glue filter.",
    ),
}
