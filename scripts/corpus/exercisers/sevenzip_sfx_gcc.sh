#!/bin/bash
# Builds one of 7-Zip's Windows SFX stubs with a MinGW-w64 cross compiler.
#
# 7-Zip ships no makefile.gcc for either stub (CPP/7zip/Bundles/SFXSetup and
# C/Util/SfxSetup have only the nmake `makefile`), so this reads the object
# list and the -D switches out of that makefile instead of restating them, and
# compiles each object with the flags 7zip_gcc.mak uses for MinGW. Nothing in
# the 7-Zip tree is modified; every file written lands in the output directory.
#
# usage: sevenzip_sfx_gcc.sh <cross-prefix> <stub dir> <extra -D flags> <out dir> <file>
#   cross-prefix   e.g. x86_64-w64-mingw32-
#   stub dir       CPP/7zip/Bundles/SFXSetup or C/Util/SfxSetup, from the root
#   extra -D       "-DUNICODE -D_UNICODE" for 23.01, which still takes them
#                  from Build.mak; empty for 26.03, whose headers define them
#   out dir        receives the objects and the linked stub
#   file           name of the linked stub inside it, e.g. 7zS.sfx
set -eu
PREFIX=$1
STUB=$2
EXTRA=$3
OUT=$4
FILE=$5
mkdir -p "$OUT/inc"
# absolute: windres below runs from inside the stub directory
OUT=$(cd "$OUT" && pwd)

# MinGW's headers are lower case and 7-Zip's GUI code includes <CommCtrl.h>,
# which only resolves on a case-insensitive filesystem. A forwarding header in
# the output directory fixes the include without touching 7-Zip's.
echo '#include <commctrl.h>' > "$OUT/inc/CommCtrl.h"

NMAKE="$STUB/makefile"
DEFS=$(grep -o '\-DZ7_[A-Z0-9_]*' "$NMAKE" | sort -u | tr '\n' ' ')
# Crc.mak adds these two for every stub (some makefiles also list them); the MASM variant is omitted exactly as
# in the 7z.dll recipe (USE_ASM=), so the C versions are the ones built.
OBJS=$( (grep -o 'O\\[A-Za-z0-9]*\.obj' "$NMAKE" | sed 's/^O.//; s/\.obj$//'; echo 7zCrc; echo 7zCrcOpt) | sort -u)

DIRS="$STUB C CPP/Common CPP/Windows CPP/Windows/Control CPP/7zip/Common
CPP/7zip/UI/Common CPP/7zip/UI/Explorer CPP/7zip/UI/FileManager
CPP/7zip/Archive/Common CPP/7zip/Archive/7z CPP/7zip/Compress"

# 7zip_gcc.mak CFLAGS_BASE, less -Werror/-Wall (see sevenzip.py) and -fPIC,
# which means nothing for a PE.
FLAGS="-O2 -c -DNDEBUG -D_REENTRANT -D_FILE_OFFSET_BITS=64 -D_LARGEFILE_SOURCE $DEFS $EXTRA -I$OUT/inc"

LINK=""
for name in $OBJS; do
  src=""
  for d in $DIRS; do
    for ext in cpp c; do
      if [ -f "$d/$name.$ext" ]; then src="$d/$name.$ext"; break 2; fi
    done
  done
  [ -n "$src" ] || { echo "no source for $name" >&2; exit 1; }
  case $src in
    *.c)   ${PREFIX}gcc $FLAGS -o "$OUT/$name.o" "$src" ;;
    *.cpp) ${PREFIX}g++ $FLAGS -o "$OUT/$name.o" "$src" ;;
  esac
  LINK="$LINK $OUT/$name.o"
done

(cd "$STUB" && ${PREFIX}windres -I "$OUT/inc" resource.rc -O coff -o "$OUT/resource.o")
LINK="$LINK $OUT/resource.o"

# -static is 7zip_gcc.mak's LDFLAGS_STATIC_2 for MinGW; -mwindows because both
# stubs are GUI-subsystem programs (WinMain). LIB2 is the makefile's.
${PREFIX}g++ -static -mwindows -o "$OUT/$FILE" $LINK \
  -loleaut32 -luuid -ladvapi32 -luser32 -lole32 -lgdi32 -lcomctl32 -lcomdlg32 -lshell32
