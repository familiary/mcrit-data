#!/bin/bash
# Run upstream's own configure for libgpg-error or libgcrypt with cl as the
# compiler, under MSYS2 (the windows-2022 image has it), and stop there: the
# generated config.h, gcrypt.h and Makefiles are what gnupg_cl.py reads. No
# `make` is run, because upstream's Makefiles loop on this runner (see
# gnupg_cl.py). Nothing is patched; every obstacle is met with a configure
# option or an environment variable.
#
# usage: gnupg_cl.sh <x86|x64> <source dir> <build dir> <prefix> [diag] -- <configure options>
set -u
arch=$1; src=$(cygpath -u "$2"); bld=$(cygpath -u "$3"); prefix=$(cygpath -u "$4"); shift 4
diag=0
if [ "${1:-}" = diag ]; then diag=1; shift; fi
[ "${1:-}" = -- ] && shift
stamp() { echo "[$(date -u +%H:%M:%S)] $*"; }

case $arch in x64) cpu=x86_64;; *) cpu=i686;; esac
# The Windows code of both packages is selected only by a *-mingw32* host
# triple (configure.ac: have_w32_system); without it the POSIX code is built.
TRIPLE=$cpu-w64-mingw32

MSVCBIN=$(dirname "$(command -v cl)")
GNUBIN=$(dirname "$(command -v windres)")
# MSVC first (MSYS's /usr/bin/link would shadow link.exe), then MSYS, then the
# directory with windres, which configure looks for on a mingw32 host.
export PATH="${GNUPG_EXTRA_PATH:+$(cygpath -u -p "$GNUPG_EXTRA_PATH"):}$MSVCBIN:/usr/bin:$GNUBIN"
stamp "arch=$arch src=$src bld=$bld"
cl 2>&1 < /dev/null | head -1
make --version < /dev/null | head -1
awk --version < /dev/null 2>&1 | head -1

export AR=lib AR_FLAGS=-OUT: RANLIB=: STRIP=: NM="dumpbin -symbols" LD=link
export RC=windres
export lt_cv_path_LD=link lt_cv_path_NM="dumpbin -symbols"
export CFLAGS="-O2 -MD -Z7 -FS"
export LDFLAGS="-Wl,-DEBUG -Wl,-INCREMENTAL:NO -Wl,-OPT:NOREF -Wl,-OPT:NOICF -Wl,-Brepro"
# GNUPG_CL_CC names the C compiler (default cl); GNUPG_CL_CCARGS adds its
# options (the clang-cl variant, see gnupg_cl.py ASM).
export CC="$src/build-aux/compile ${GNUPG_CL_CC:-cl} -nologo ${GNUPG_CL_CCARGS:-}"

mkdir -p "$bld"; cd "$bld" || exit 1
stamp "configure"
timeout 900 "$src/configure" --build=$TRIPLE --host=$TRIPLE --prefix="$prefix" "$@" \
    > configure.out 2>&1 < /dev/null
rc=$?
tail -25 configure.out
stamp "configure exit $rc"
[ $rc -eq 0 ] || exit $rc

if [ $diag -eq 1 ]; then
  # The earlier attempts ran `make` here and it re-ran configure until the
  # job timed out. Ask make why, in a bounded way, and show it.
  stamp "DIAG clock: $(date -u +%FT%T)"
  stat -c '%y %n' "$bld/config.status" "$bld/Makefile" "$bld/config.h" \
      "$src/configure" "$src/configure.ac" "$src/aclocal.m4" "$src/Makefile.in" \
      "$src/Makefile.am" "$src/config.h.in" "$src/src/Makefile.in" "$src/src/Makefile.am" 2>&1
  stamp "DIAG make --debug=b -n (100 s cap)"
  timeout 100 make --debug=b -n AUTOCONF=: AUTOMAKE=: ACLOCAL=: AUTOHEADER=: MAKEINFO=: \
      < /dev/null 2>&1 | grep -v "^ *$" | cut -c1-300 | head -120
  stamp "DIAG after make: $(stat -c '%y %n' "$bld/config.status" "$bld/Makefile")"
  stamp "DIAG make -q config.status"
  timeout 60 make -d -q config.status AUTOCONF=: AUTOMAKE=: ACLOCAL=: AUTOHEADER=: \
      < /dev/null 2>&1 | grep -i -E "newer|older|does not exist|must remake|no need|Prerequisite" | cut -c1-300 | head -40
  stamp "DIAG done"
fi
exit 0
