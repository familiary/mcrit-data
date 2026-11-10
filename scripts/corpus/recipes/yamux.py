"""hashicorp/yamux - the stream multiplexer under revsocks, chisel's relatives
and a number of backconnect tools.

v0.1.2 is the tag kost/revsocks pins and the newest release; the library is six
non-test files, 74 top-level functions, so the whole of it is the family.
yamux has no main package, so the artefact is exerciser/go/yamux/main.go
copied into the checkout as its own package (same module, so every
github.com/hashicorp/yamux symbol in the image is the library's): a Server and
Client over an in-memory pipe, one stream echoed, Ping, GoAway and the
remaining exported surface.

Go dependencies: none - go.mod requires nothing, the image is yamux plus the
Go runtime and standard library, which glue_filter="go" removes.

Built on all four Go targets (windows and linux, amd64 and 386) because the
library is pure Go and each is one `go build`; they differ in the compiler's
choices for 32- and 64-bit words in the 12-byte header codec and window
arithmetic.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._go import GO_BUILD_FLAGS, GO_ENV, GO_TOOLCHAINS


RECIPES = {
    "yamux_0.1.2": Recipe(
        family="yamux",
        version="0.1.2",
        upstream="https://github.com/hashicorp/yamux",
        license="MPL-2.0",
        source=Source(git_url="https://github.com/hashicorp/yamux.git",
                      git_ref="v0.1.2"),
        build=[
            BuildStep("mkdir -p mcrit_exerciser && cp "
                      "{repo}/scripts/corpus/exercisers/go/yamux/main.go "
                      "mcrit_exerciser/main.go"),
            BuildStep("go build -trimpath -o yamux_exerciser ./mcrit_exerciser",
                      env=GO_ENV),
        ],
        artifacts=[Artifact(path="yamux_exerciser",
                            component="yamux_exerciser")],
        toolchains=GO_TOOLCHAINS,
        glue_filter="go",
        build_flags=GO_BUILD_FLAGS,
        notes="Built with go1.24.7 (GOTOOLCHAIN=local). go.mod declares go 1.20 "
              "and no requirements, so there is no go.sum and no dependency "
              "beyond the standard library. The artefact is an exerciser "
              "(a Server/Client pair over net.Pipe, one echoed stream, Ping, "
              "GoAway) built inside the yamux module, not a yamux "
              "application; the Go runtime and standard library are removed "
              "by the Go glue filter (by symbol name).",
    ),
}
