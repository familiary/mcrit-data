"""Shared constants for the Go recipes.

A Go program rides the C toolchain ids for the platform it targets (see
corpus.toolchain: ``{goos}``/``{goarch}``), so every Go recipe declares the same
four and builds with the same environment. The Go version itself is the host's
and is stated in each recipe's notes, since the toolchain record only knows the
C compiler.
"""

# windows/amd64, windows/386, linux/amd64, linux/386
GO_TOOLCHAINS = ["mingw_x64", "mingw_x86", "linux_x64", "linux_x86"]

# GOTOOLCHAIN=local so a go.mod asking for a newer toolchain fails instead of
# silently downloading one; -mod=readonly so go.sum is the pin and nothing is
# resolved at build time. The dependency download (if any) is verified against
# go.sum like any other build.
GO_ENV = {
    "CGO_ENABLED": "0",
    "GOOS": "{goos}",
    "GOARCH": "{goarch}",
    "GOTOOLCHAIN": "local",
    "GOFLAGS": "-mod=readonly",
}

GO_BUILD_FLAGS = ("go1.24.7 gc, CGO_ENABLED=0, -trimpath, default "
                  "optimisation, unstripped")

# The older Go toolchain the Go 1.22 band of a library is built with: go1.22.12,
# the last go1.22 patch release. GOTOOLCHAIN=go1.22.12 makes the host go
# fetch golang.org/toolchain v0.0.1-go1.22.12.<goos>-<goarch> through the
# module proxy and verify it against the checksum database before running it
# (linux-amd64 zip h1:Hdh4VJAlDWzMnhKpqDwqJJr+sE7NgsJ86dyR4wrv2oY=, sha256
# d426bcf50497ae8665e741482aba04fc12782e8860857229d4005dcc480fd89b; the
# go.dev/dl tarball of the same release is sha256
# 4fa4f869b0f7fc6bb1eb2660e74657fbf04cdd290b5aef905585c86051b34d43). A go.mod
# asking for go 1.23 or newer fails under it instead of switching.
GO122_VERSION = "go1.22.12"
GO122_ENV = dict(GO_ENV, GOTOOLCHAIN=GO122_VERSION)
GO122_BUILD_FLAGS = GO_BUILD_FLAGS.replace("go1.24.7", GO122_VERSION)
GO122_PIN = ("GOTOOLCHAIN=go1.22.12: golang.org/toolchain "
             "v0.0.1-go1.22.12.linux-amd64 "
             "h1:Hdh4VJAlDWzMnhKpqDwqJJr+sE7NgsJ86dyR4wrv2oY=, zip sha256 "
             "d426bcf50497ae8665e741482aba04fc12782e8860857229d4005dcc480fd89b")
