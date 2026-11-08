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

# Firmware Linux 0.9.6 only. uClibc 0.9.30.1 builds a host tool,
# extra/scripts/unifdef.c, that defines its own getline(); glibc 2.19 of the
# host image declares the POSIX getline() and the compile stops with
# "conflicting types for 'getline'" (seen in CI). Without touching the uClibc
# source, a host-gcc wrapper renames that one identifier for that one file
# (-Dgetline=unifdef_getline); every other host compile passes through.
if [ "$STAGE" = cross-compiler ]; then
  mkdir -p /opt/hostfix
  cat > /opt/hostfix/gcc <<'WRAP'
#!/bin/sh
for a in "$@"; do
  case "$a" in
    *unifdef.c) set -- "$@" -Dgetline=unifdef_getline; break ;;
  esac
done
exec /usr/bin/gcc "$@"
WRAP
  chmod +x /opt/hostfix/gcc
  export PATH="/opt/hostfix:$PATH"
fi
./"$STAGE".sh "$ARCH"
