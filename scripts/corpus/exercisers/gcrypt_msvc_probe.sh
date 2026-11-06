#!/bin/bash
# Scratch probe: can the unmodified GnuPG tarballs be built by cl through
# autotools under MSYS2? Prints everything it learns; never patches anything.
# usage: gcrypt_msvc_probe.sh <variant A> <arch x86|x64> <libgcrypt tarball>
set -u
variant=$1; arch=$2; gtar=$(cygpath -u "$3")
SRC=$(pwd)
MSVCBIN=$(dirname "$(command -v cl)")
export PATH="$MSVCBIN:/usr/bin:$PATH"
stamp() { echo "[$(date -u +%H:%M:%S)] $*"; }
# run <seconds> <logfile> cmd...: never waits on stdin, never runs forever.
run() { local t=$1 log=$2; shift 2; timeout "$t" "$@" > "$log" 2>&1 < /dev/null; local rc=$?; stamp "exit $rc: $* (log $log)"; return $rc; }
stamp "variant=$variant arch=$arch src=$SRC"
cl 2>&1 < /dev/null | head -1
echo "make is: $(make --version < /dev/null | head -1)"
case $arch in x64) cpu=x86_64;; *) cpu=i686;; esac
TRIPLE=$cpu-w64-mingw32
HOSTOPTS="--build=$TRIPLE --host=$TRIPLE"
OPTS="--disable-static --enable-shared --disable-doc --disable-tests --disable-languages --disable-nls"
WORK=$SRC/../probe-$variant-$arch
rm -rf "$WORK"; mkdir -p "$WORK/ge" "$WORK/gc"
PREFIX=$WORK/inst
export CFLAGS="-O2 -MD -Zi -FS"
export LDFLAGS="-DEBUG -INCREMENTAL:NO -OPT:NOREF -OPT:NOICF -Brepro"
NOREGEN="AUTOCONF=: AUTOMAKE=: ACLOCAL=: AUTOHEADER=: MAKEINFO="

cd "$WORK/ge"
stamp "== libgpg-error configure"
CC="$SRC/build-aux/compile cl -nologo" LD=link NM='dumpbin -symbols' STRIP=: AR=lib AR_FLAGS=-OUT: RANLIB=: \
  run 600 configure.out "$SRC/configure" $HOSTOPTS --prefix="$PREFIX" $OPTS
rc=$?
tail -15 configure.out
if [ $rc -ne 0 ]; then echo "== config.log tail"; tail -60 config.log; fi
grep -n -E "^(CC|AR|AR_FLAGS|LD|host|build)=" libtool | head
stamp "== libgpg-error make"
run 1200 make.out make -k $NOREGEN
grep -n -E "error|Error|fatal|warning: unrecog" make.out | head -50
tail -12 make.out
ls -la src/.libs 2>&1 | head -20
stamp "== libgpg-error install"
run 300 install.out make -C src install $NOREGEN
tail -5 install.out
ls "$PREFIX/lib" "$PREFIX/bin" 2>&1

stamp "== libgcrypt (asm off: cl cannot assemble GNU .S)"
cd "$WORK"
tar xjf "$gtar" -C "$WORK"
GS=$(ls -d "$WORK"/libgcrypt-*)
cd "$WORK/gc"
export PATH="$PREFIX/bin:$PATH"
CC="$GS/build-aux/compile cl -nologo" LD=link NM='dumpbin -symbols' STRIP=: AR=lib AR_FLAGS=-OUT: RANLIB=: \
  run 600 configure.out "$GS/configure" $HOSTOPTS --prefix="$WORK/ginst" --disable-static --enable-shared \
  --disable-doc --disable-asm --with-libgpg-error-prefix="$PREFIX"
rc=$?
tail -25 configure.out
if [ $rc -ne 0 ]; then echo "== config.log tail"; tail -60 config.log; fi
if [ $rc -eq 0 ]; then
  run 1800 make.out make -k $NOREGEN SUBDIRS="compat mpi cipher random src"
  grep -n -E "error|Error|fatal" make.out | head -60
  tail -15 make.out
  ls -la src/.libs 2>&1 | head
fi
stamp done
exit 0
