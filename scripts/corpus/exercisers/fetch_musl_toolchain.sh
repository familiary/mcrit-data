#!/bin/sh
# Download, verify and unpack the pinned musl.cc toolchains.
#
#   fetch_musl_toolchain.sh <directory> [x64|x86|all]
#
# The URLs and SHA-256 sums are the ones in corpus.toolchain.MUSL_PINS, which is
# what the provenance of every musl artefact points at; this script reads them
# from there so there is one copy. A tarball that does not match its sum is
# deleted and the script fails, which is the whole point of pinning a URL that
# a third party can replace.
#
# Afterwards put the bin directories at the END of PATH:
#
#   export PATH="$PATH:<directory>/x86_64-linux-musl-native/bin:<directory>/i686-linux-musl-cross/bin"
#
# At the end, not the front: the native x86_64 toolchain ships a plain `gcc`
# and `g++` in that directory, which at the front would replace the host's
# compiler and make the glibc Linux toolchain build with musl. The recipes
# name the triple-prefixed drivers (x86_64-linux-musl-gcc and so on), which
# are found wherever the directory sits.
set -eu
dest=${1:?usage: fetch_musl_toolchain.sh <directory> [x64|x86|all]}
which=${2:-all}
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$dest"
for arch in x64 x86; do
  case "$which" in all|"$arch") ;; *) continue ;; esac
  pin=$(python3 -I - "$here/../toolchain.py" "$arch" <<'PY'
import ast, sys
tree = ast.parse(open(sys.argv[1]).read())
for node in tree.body:
    if isinstance(node, ast.Assign) and node.targets[0].id == "MUSL_PINS":
        pin = ast.literal_eval(node.value)[sys.argv[2]]
        print(pin["name"], pin["url"], pin["sha256"])
PY
)
  set -- $pin
  name=$1; url=$2; sha=$3
  if [ -x "$dest/$name/bin/$(echo "$name" | sed 's/-native//; s/-cross//')-gcc" ]; then
    echo "$name already unpacked"; continue
  fi
  tmp=$(mktemp "$dest/$name.XXXXXX.tgz")
  curl -sSfL -o "$tmp" "$url"
  echo "$sha  $tmp" | sha256sum -c - || { rm -f "$tmp"; echo "checksum mismatch for $url" >&2; exit 1; }
  tar xzf "$tmp" -C "$dest"
  rm -f "$tmp"
done
