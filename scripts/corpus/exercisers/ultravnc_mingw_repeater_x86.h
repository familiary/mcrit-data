// Force-included (-include) into the UltraVNC repeater project, 32-bit only.
// The i686 mingw-w64 import library for msvcrt.dll has no _ltoa_s (the
// x86-64 one does); repeater.cpp:61 calls `_ltoa_s(value, buf, 10)`. The call
// is replaced by the equivalent _ltoa, whose result the caller ignores.
#ifndef UVNC_MINGW_REPEATER_X86_H
#define UVNC_MINGW_REPEATER_X86_H
#include <stdlib.h>
#define _ltoa_s(value, buffer, radix) (_ltoa((value), (buffer), (radix)), 0)
#endif
