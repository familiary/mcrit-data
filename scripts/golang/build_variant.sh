#!/bin/bash
# Builds a cgo-enabled or race-instrumented variant of the Golang stdlib
# coverage reference (the same generated driver as build_references.sh), runs
# SMDA, removes the coverage driver's own main.* functions as the default
# 1.27.3 references do, and exports .mcrit.
#
# usage: build_variant.sh <go version> <goos> <goarch> <workdir> <cgo|race>
#   e.g. build_variant.sh 1.27.3 linux amd64 /tmp/gorefs race
#
# cgo:  CGO_ENABLED=1, so runtime/cgo and the cgo halves of net, os/user and
#       the other packages with a cgo implementation are linked (gcc for
#       Linux, the mingw-w64 gcc for Windows).
# race: CGO_ENABLED=1 plus -race, which instruments every function and links
#       the race runtime; Go supports it on linux/amd64 and windows/amd64 here.
# The driver source is generated exactly as for the default references, so the
# API surface is the same; only the build mode differs.
set -euo pipefail
VERSION=$1; GOOS=$2; GOARCH=$3; WORK=$4; VARIANT=$5
HERE=$(cd "$(dirname "$0")" && pwd)
case "$VERSION" in
  1.27.3) PIN=65efbc80fdc1fa2cd2631cad5b481777a68e8725f34e89f50fc6ac714e379b40 ;;
  *) echo "no sha256 pin for go$VERSION" >&2; exit 1 ;;
esac
TOOLCHAIN=$WORK/toolchains/go$VERSION
if [ ! -x "$TOOLCHAIN/bin/go" ]; then
  mkdir -p "$TOOLCHAIN"
  TARBALL=$WORK/toolchains/go$VERSION.linux-amd64.tar.gz
  curl -sSfL -o "$TARBALL" "https://go.dev/dl/go$VERSION.linux-amd64.tar.gz"
  [ "$(sha256sum "$TARBALL" | cut -d' ' -f1)" = "$PIN" ] || { echo "sha256 mismatch for $TARBALL" >&2; exit 1; }
  tar -xz -C "$TOOLCHAIN" --strip-components=1 -f "$TARBALL"
fi
export PATH=$TOOLCHAIN/bin:$PATH GOTOOLCHAIN=local GOENV=off
[ "$GOARCH" = amd64 ] && BITS=x64 || BITS=x86
case "$GOOS/$GOARCH" in
  linux/amd64) CC=gcc ;;
  linux/386) CC="gcc -m32" ;;
  windows/amd64) CC=x86_64-w64-mingw32-gcc ;;
  windows/386) CC=i686-w64-mingw32-gcc ;;
esac
FLAGS=""
case "$VARIANT" in
  cgo) ;;
  race) FLAGS="-race" ;;
  *) echo "variant must be cgo or race" >&2; exit 1 ;;
esac
[ "$GOOS" = windows ] && EXE=.exe || EXE=
if [ "$GOOS" = windows ]; then NAME=golang_${VERSION}-${VARIANT}_${BITS}; LABEL="$VERSION-$VARIANT $BITS"; else NAME=golang_${VERSION}-${VARIANT}_${GOOS}_${BITS}; LABEL="$VERSION-$VARIANT $GOOS $BITS"; fi
BIN=stdcov_go${VERSION}_${VARIANT}_${GOOS}_${GOARCH}$EXE
BUILD=$WORK/build/go${VERSION}_${VARIANT}_${GOOS}_${GOARCH}
mkdir -p "$BUILD" && cd "$BUILD"
go run "$HERE/gogen_stdlib_coverage.go" -goos "$GOOS" -goarch "$GOARCH" > main.go
printf 'module stdcov\n\ngo %s\n' "$(echo "$VERSION" | cut -d. -f1,2)" > go.mod
CGO_ENABLED=1 CC="$CC" GOOS=$GOOS GOARCH=$GOARCH go build -trimpath $FLAGS -o "$BIN" .
sha256sum "$BIN" main.go go.mod
python3 "$HERE/run_smda.py" "$BIN" "$NAME.raw.smda" "$LABEL" "$BIN"
python3 "$HERE/drop_driver.py" "$NAME.raw.smda" "$NAME.smda"
python3 "$HERE/smda2mcrit.py" "$NAME.mcrit" "$NAME.smda"
python3 -c "import py7zr,sys; z=py7zr.SevenZipFile(sys.argv[1]+'.7z','w'); z.write(sys.argv[1]+'.smda', sys.argv[1]+'.smda'); z.close()" "$NAME"
echo "$BUILD/$NAME.7z $BUILD/$NAME.mcrit"
