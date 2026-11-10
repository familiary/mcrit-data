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
