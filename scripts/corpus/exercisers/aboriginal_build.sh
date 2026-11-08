#!/bin/bash
# Runs INSIDE the pinned host container started by scripts/corpus/recipes/
# aboriginal_source.py. Usage: aboriginal_build.sh STAGE ARCH
#
#   STAGE  simple-cross-compiler (Aboriginal Linux 1.0.3 / 1.4.4) or
#          cross-compiler (Firmware Linux 0.9.6), the toolchain stage script
#          shipped in the unmodified distribution tarball mounted at /w.
#   ARCH   the distribution's own target name (i686, x86_64).
#
# /w holds the unpacked distribution with every component tarball already
# placed in /w/packages by the recipe (each verified by sha256 on the host).
# Nothing is downloaded here except the container's own apt packages. The
# distribution scripts, patches and component sources are not modified.
set -ex
STAGE="$1"
ARCH="$2"
cd /w
# Leave the tree owned by the invoking runner user, also after a failure, so
# the host side can read it and the runner can clean it up.
trap 'chown -R "$HOST_UID:$HOST_GID" /w' EXIT

export DEBIAN_FRONTEND=noninteractive
apt-get update || {
  sed -i 's|http://[a-z.]*archive.ubuntu.com|http://old-releases.ubuntu.com|;s|http://security.ubuntu.com|http://old-releases.ubuntu.com|' /etc/apt/sources.list
  apt-get update
}
apt-get install -y --no-install-recommends build-essential bzip2 patch bison flex \
  texinfo m4 gawk file ca-certificates
gcc --version | head -1

# Settings the distributions document in their own `config` files. The
# host-tools stage (busybox, toybox, distcc, e2fsprogs, squashfs build only
# helper programs for images) is skipped, as is C++ and the stage tarball.
export NO_HOST_TOOLS=1 NO_CPLUSPLUS=1 NO_STAGE_TARBALLS=1
export HOME=/tmp
./"$STAGE".sh "$ARCH"
