#!/bin/bash
# Build libgpg-error or libgcrypt with cl through the project's own autotools
# build, under MSYS2 (the windows-2022 image has it). Nothing is patched: every
# obstacle is met with a configure option or an environment variable.
#
# usage: gnupg_msvc.sh <arch x86|x64> <gpg-error|gcrypt> <source root> [libgpg-error tarball]
set -eu
arch=$1; pkg=$2; src=$(cygpath -u "$3"); gerr_tar=${4:+$(cygpath -u "$4")}
stamp() { echo "[$(date -u +%H:%M:%S)] $*"; }
# run <seconds> <logfile> cmd...: never waits on stdin, never runs forever, and
# on failure shows the end of the log so the job page is enough to diagnose it.
run() {
  local t=$1 log=$2; shift 2
  stamp "run: $*"
  local rc
  set +e
  timeout "$t" "$@" > "$log" 2>&1 < /dev/null
  rc=$?
  set -e
  if [ $rc -eq 0 ]; then stamp "ok ($log)"; return 0; fi
  stamp "FAILED exit $rc: $*"
  grep -n -E "error|Error|fatal|undefined|unrecognized" "$log" | head -40
  tail -30 "$log"
  return $rc
}

case $arch in x64) cpu=x86_64;; *) cpu=i686;; esac
# libgpg-error and libgcrypt select their Windows code on a *-mingw32* host
# (configure.ac: have_w32_system), so the triple has to be named even though
# the compiler is cl. Without it they build the POSIX code, which needs
# <unistd.h> and pthreads.
TRIPLE=$cpu-w64-mingw32
HOSTOPTS="--build=$TRIPLE --host=$TRIPLE"

MSVCBIN=$(dirname "$(command -v cl)")
GNUBIN=$(dirname "$(command -v windres)")
# MSVC first (MSYS's own /usr/bin/link would otherwise shadow link.exe), then
# MSYS, then the directory that carries windres, make and the gcc windres runs
# as its preprocessor. libtool's own tool searches are pinned below so it does
# not pick up the GNU ld and nm that directory also holds.
export PATH="$MSVCBIN:/usr/bin:$GNUBIN"
stamp "arch=$arch pkg=$pkg src=$src"
cl 2>&1 < /dev/null | head -1
make --version < /dev/null | head -1
windres --version < /dev/null | head -1

# ar-lib is not in either tarball; lib.exe takes its output as -OUT:<file>,
# which is what libtool's "$AR $AR_FLAGS$oldlib$oldobjs" becomes.
export AR=lib AR_FLAGS=-OUT: RANLIB=: STRIP=: NM="dumpbin -symbols" LD=link
export RC=windres
export lt_cv_path_LD=link lt_cv_path_NM="dumpbin -symbols"
# /MD, not /MT; /Z7 puts debug info in the objects so parallel compiles do not
# contend for one vc143.pdb; no /GL.
export CFLAGS="-O2 -MD -Z7 -FS"
export LDFLAGS="-Wl,-DEBUG -Wl,-INCREMENTAL:NO -Wl,-OPT:NOREF -Wl,-OPT:NOICF -Wl,-Brepro"
OPTS="--disable-static --enable-shared --disable-doc --disable-tests --disable-languages --disable-nls"

# Tarball extraction does not keep the order autotools expects, and make then
# tries to re-run autoconf and automake (neither is installed). Giving every
# file the timestamp of configure leaves nothing newer than anything else.
touchall() { find "$1" -type f -exec touch -r "$1/configure" {} +; }
NOREGEN="AUTOCONF=: AUTOMAKE=: ACLOCAL=: AUTOHEADER=: MAKEINFO=:"

build_pkg() {   # <srcdir> <builddir> <prefix> <extra configure options>
  local s=$1 b=$2 p=$3; shift 3
  touchall "$s"
  mkdir -p "$b"; cd "$b"
  export CC="$s/build-aux/compile cl -nologo"
  run 900 configure.out "$s/configure" $HOSTOPTS --prefix="$p" "$@"
  tail -12 configure.out
  run 1500 make.out make -j4 $NOREGEN
}

WORK=$src/msvc-$arch
rm -rf "$WORK"; mkdir -p "$WORK"
if [ "$pkg" = gpg-error ]; then
  build_pkg "$src" "$WORK" "$WORK/inst" $OPTS
  ls -la "$WORK/src/.libs" || true
else
  # libgcrypt wants libgpg-error installed; build the paired release the same way.
  tar xjf "$gerr_tar" -C "$WORK"
  GE=$(ls -d "$WORK"/libgpg-error-*)
  build_pkg "$GE" "$WORK/ge" "$WORK/inst" $OPTS
  run 300 install.out make -C "$WORK/ge/src" install $NOREGEN
  export PATH="$WORK/inst/bin:$PATH"
  # cl cannot assemble the GNU-syntax .S modules, so the generic C paths are
  # used (--disable-asm); that is a different code surface from the MinGW build.
  build_pkg "$src" "$WORK/gc" "$WORK/ginst" --disable-static --enable-shared \
     --disable-doc --disable-asm --with-libgpg-error-prefix="$WORK/inst"
  ls -la "$WORK/gc/src/.libs" || true
fi
stamp done
