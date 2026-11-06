#!/bin/sh
# Compiler driver wrapper for the miner recipes' MinGW builds.
#
# XMRig and xmrig-proxy append -static to CMAKE_EXE_LINKER_FLAGS for every
# GNU build on Windows, after any value given on the command line, and CMake's
# Windows-GNU platform file defines the executable link rule unconditionally,
# so neither the variable nor CMAKE_CXX_LINK_EXECUTABLE can take it out. -static
# links libstdc++ and libgcc into the executable, which files about 13,500
# runtime functions under the miner's name (scripts/corpus/README.md).
#
# This drops -static, -static-libgcc and -static-libstdc++ from every command
# line it is handed and, when the command links, appends $XM_LINK_EXTRA (the
# shared-libgcc switch and the import library libuv needs after the archives
# that call it). Nothing in the upstream tree is touched.
#
# XM_REAL_CXX is the real compiler driver.
real=${XM_REAL_CXX:?XM_REAL_CXX not set}
link=1
for a in "$@"; do
  case "$a" in -c|-E|-S) link=0 ;; esac
done
n=$#
while [ "$n" -gt 0 ]; do
  a=$1; shift; n=$((n - 1))
  case "$a" in
    -static|-static-libgcc|-static-libstdc++) ;;
    *) set -- "$@" "$a" ;;
  esac
done
if [ "$link" = 1 ]; then
  # shellcheck disable=SC2086
  exec "$real" "$@" $XM_LINK_EXTRA
fi
exec "$real" "$@"
