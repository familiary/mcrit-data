#!/bin/bash
# Builds the Golang stdlib coverage reference binaries, disassembles them with SMDA and exports .mcrit files.
#
# usage: build_references.sh <go version> <goos> <goarch> <workdir>
#   e.g. build_references.sh 1.26.8 windows amd64 /tmp/gorefs
#
# requirements: network access to go.dev (toolchain download), python3 with smda and mcrit installed.
# The references in this repository were disassembled with the SMDA and MCRIT versions of the
# mcrit-server docker image, to match what a live MCRIT instance produces for queried samples.
set -euo pipefail
VERSION=$1; GOOS=$2; GOARCH=$3; WORK=$4
HERE=$(cd "$(dirname "$0")" && pwd)
TOOLCHAIN=$WORK/toolchains/go$VERSION
if [ ! -x "$TOOLCHAIN/bin/go" ]; then
  mkdir -p "$TOOLCHAIN"
  curl -sL "https://go.dev/dl/go$VERSION.linux-amd64.tar.gz" | tar -xz -C "$TOOLCHAIN" --strip-components=1
fi
export PATH=$TOOLCHAIN/bin:$PATH GOTOOLCHAIN=local
[ "$GOARCH" = amd64 ] && BITS=x64 || BITS=x86
[ "$GOOS" = windows ] && EXE=.exe || EXE=
if [ "$GOOS" = windows ]; then NAME=golang_${VERSION}_${BITS}; LABEL="$VERSION $BITS"; else NAME=golang_${VERSION}_${GOOS}_${BITS}; LABEL="$VERSION $GOOS $BITS"; fi
BIN=stdcov_go${VERSION}_${GOOS}_${GOARCH}$EXE
BUILD=$WORK/build/go${VERSION}_${GOOS}_${GOARCH}
mkdir -p "$BUILD" && cd "$BUILD"
go run "$HERE/gogen_stdlib_coverage.go" -goos "$GOOS" -goarch "$GOARCH" > main.go
printf 'module stdcov\n\ngo %s\n' "$(echo "$VERSION" | cut -d. -f1,2)" > go.mod
CGO_ENABLED=0 GOOS=$GOOS GOARCH=$GOARCH go build -trimpath -o "$BIN" .
python3 "$HERE/run_smda.py" "$BIN" "$NAME.smda" "$LABEL" "$BIN"
python3 "$HERE/smda2mcrit.py" "$NAME.mcrit" "$NAME.smda"
python3 -c "import py7zr,sys; z=py7zr.SevenZipFile(sys.argv[1]+'.7z','w'); z.write(sys.argv[1]+'.smda', sys.argv[1]+'.smda'); z.close()" "$NAME"
echo "$BUILD/$NAME.7z $BUILD/$NAME.mcrit"
