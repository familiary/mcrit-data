#!/bin/bash
# Scratch probe: can the unmodified GnuPG tarballs be built by cl through
# autotools under MSYS2? Prints everything it learns; never patches anything.
# usage: gcrypt_msvc_probe.sh <variant A|B> <arch x86|x64> <libgcrypt tarball>
set -u
variant=$1; arch=$2; gtar=$(cygpath -u "$3")
SRC=$(pwd)
MSVCBIN=$(dirname "$(command -v cl)")
export PATH="$MSVCBIN:/usr/bin:$PATH"
echo "== variant=$variant arch=$arch src=$SRC"
echo "== tools"
for t in cl link lib rc dumpbin make sed awk gawk grep tar bzip2 m4 perl; do
  printf '%s: ' $t; command -v $t || echo MISSING
done
cl 2>&1 | head -1; echo "make is: $(make --version | head -1)"
echo "== libtool/automake aux scripts"
ls -la "$SRC/build-aux/compile" "$SRC/build-aux/ar-lib" 2>&1
case $arch in x64) cpu=x86_64;; *) cpu=i686;; esac
TRIPLE=$cpu-w64-mingw32
if [ "$variant" = A ]; then HOSTOPTS="--build=$TRIPLE --host=$TRIPLE"; else HOSTOPTS=""; fi
echo "== host options: $HOSTOPTS"
OPTS="--disable-static --enable-shared --disable-doc --disable-tests --disable-languages --disable-nls"
WORK=$SRC/../probe-$variant-$arch
rm -rf "$WORK"; mkdir -p "$WORK/ge" "$WORK/gc"
PREFIX=$WORK/inst
export CFLAGS="-O2 -MD -Zi -FS"
export LDFLAGS="-DEBUG -INCREMENTAL:NO -OPT:NOREF -OPT:NOICF -Brepro"
cd "$WORK/ge"
echo "== libgpg-error configure"
CC="$SRC/build-aux/compile cl -nologo" CXX="$SRC/build-aux/compile cl -nologo" \
  LD=link NM='dumpbin -symbols' STRIP=: AR=lib AR_FLAGS=-OUT: RANLIB=: \
  "$SRC/configure" $HOSTOPTS --prefix="$PREFIX" $OPTS > configure.out 2>&1
rc=$?; echo "configure exit $rc"
tail -40 configure.out
if [ $rc -ne 0 ]; then echo "== config.log tail"; tail -80 config.log; fi
echo "== libgpg-error make"
grep -n -E "^(CC|AR|AR_FLAGS|LD|archive_cmds|old_archive_cmds|host|build)=" libtool | head -20
make -k -j4 AUTOCONF=: AUTOMAKE=: ACLOCAL=: AUTOHEADER=: MAKEINFO=: > make.out 2>&1; echo "make exit $?"
grep -n -E "error|Error|fatal|warning: unrecog" make.out | head -60
tail -20 make.out
ls -la src/.libs 2>&1 | head -20
echo "== libgpg-error install"
make -C src install AUTOCONF=: AUTOMAKE=: ACLOCAL=: AUTOHEADER=: > install.out 2>&1; echo "install exit $?"; tail -5 install.out
ls "$PREFIX/lib" "$PREFIX/bin" 2>&1
echo "== libgcrypt (asm off: cl cannot assemble GNU .S)"
cd "$WORK/gc"
tar xjf "$gtar" -C "$WORK" 
GS=$(ls -d "$WORK"/libgcrypt-*)
export PATH="$PREFIX/bin:$PATH"
CC="$GS/build-aux/compile cl -nologo" LD=link NM='dumpbin -symbols' STRIP=: \
  AR=lib AR_FLAGS=-OUT: RANLIB=: \
  "$GS/configure" $HOSTOPTS --prefix="$WORK/ginst" --disable-static --enable-shared \
  --disable-doc --disable-asm --with-libgpg-error-prefix="$PREFIX" > configure.out 2>&1
rc=$?; echo "libgcrypt configure exit $rc"
tail -30 configure.out
if [ $rc -ne 0 ]; then echo "== config.log tail"; tail -60 config.log; fi
if [ $rc -eq 0 ]; then
  make -k -j4 AUTOCONF=: AUTOMAKE=: ACLOCAL=: AUTOHEADER=: MAKEINFO=: SUBDIRS="compat mpi cipher random src" > make.out 2>&1; echo "libgcrypt make exit $?"
  grep -n -E "error|Error|fatal" make.out | head -60
  tail -15 make.out
  ls -la src/.libs 2>&1 | head
fi
exit 0
