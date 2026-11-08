"""Writes the stand-in vncviewer\\ViewerBounds.h of the UltraVNC 1.8.3.2 recipe.

Usage: ultravnc_viewerbounds.py <path of the header to write>
(run by scripts/corpus/recipes/ultravnc_msvc.py inside the build tree; the
header is NOT part of upstream and is never committed into a source tree).

Upstream commit 6c44cfc ("harden code against buffer overruns") added
`#include "ViewerBounds.h"` to ClientConnection.cpp, ClientConnectionCursor.cpp,
ClientConnectionUltra2.cpp and FileTransfer.cpp and never committed the header.
Everything below is inferred from the 24 call sites in those four files and from
the code that 6c44cfc removed in their place; the recipe docstring has the table.
"""
import sys

HEADER = r"""// ViewerBounds.h - STAND-IN written by the mcrit-data recipe for UltraVNC 1.8.3.2.
//
// Upstream commit 6c44cfc added #include "ViewerBounds.h" to ClientConnection.cpp,
// ClientConnectionCursor.cpp, ClientConnectionUltra2.cpp and FileTransfer.cpp and
// never committed the header. This file is not upstream's. It defines only the
// six functions those sources call; the semantics are read off the call sites
// and off the checks 6c44cfc deleted in their place.
#pragma once

#include <climits>
#include <type_traits>

namespace ViewerBounds {

// 100 MiB: the literal the callers pass as the size limit of a temporary
// buffer (ReadCursorShape, DecompressJpegRect), and 4 more than the largest
// compressed-rectangle size ReadScreenUpdate accepts (104857596) before it
// asks for size + 4 bytes.
const long long kMaxPayload = 104857600;

// ReadNewFBSize's removed check: "a screensize > 20 000 is not possible with
// current OS".
const long long kMaxFramebufferSide = 20000;

namespace detail {

template <class T>
inline bool widen(T value, long long &out, std::true_type) {
    out = static_cast<long long>(value);
    return true;
}

template <class T>
inline bool widen(T value, long long &out, std::false_type) {
    if (value > static_cast<unsigned long long>(LLONG_MAX))
        return false;
    out = static_cast<long long>(value);
    return true;
}

// The callers pass int, CARD16, UINT, unsigned long and size_t.
template <class T>
inline bool widen(T value, long long &out) {
    return widen(value, out, std::integral_constant<bool, std::is_signed<T>::value>());
}

} // namespace detail

// Createdib, ReadNewFBSize: a framebuffer of width x height pixels.
template <class W, class H, class B>
inline bool framebuffer(W width, H height, B bytesPerPixel) {
    long long w, h, b;
    if (!detail::widen(width, w) || !detail::widen(height, h) ||
        !detail::widen(bytesPerPixel, b))
        return false;
    return w >= 0 && w <= kMaxFramebufferSide &&
           h >= 0 && h <= kMaxFramebufferSide && b >= 0;
}

// Sizes read from the wire that are used to allocate: 0 <= size <= kMaxPayload.
template <class T>
inline bool payload(T size) {
    long long n;
    return detail::widen(size, n) && n >= 0 && n <= kMaxPayload;
}

// [offset, offset + length) lies inside [0, size).
template <class O, class L, class S>
inline bool range(O offset, L length, S size) {
    long long o, l, s;
    if (!detail::widen(offset, o) || !detail::widen(length, l) ||
        !detail::widen(size, s))
        return false;
    return o >= 0 && l >= 0 && s >= 0 && o <= s && l <= s - o;
}

// width * height * bytesPerPixel <= limit, without overflow.
template <class W, class H, class B, class L>
inline bool pixels(W width, H height, B bytesPerPixel, L limit) {
    long long w, h, b, m;
    if (!detail::widen(width, w) || !detail::widen(height, h) ||
        !detail::widen(bytesPerPixel, b) || !detail::widen(limit, m))
        return false;
    if (w < 0 || h < 0 || b < 0 || m < 0)
        return false;
    if (w == 0 || h == 0 || b == 0)
        return true;
    if (h > m / w)
        return false;
    return b <= m / (w * h);
}

// Check_Rectangle_borders, Copyto0buffer: the rectangle (x, y, w, h) lies
// inside a framebuffer of fbWidth x fbHeight. Same test as the removed body of
// Check_Rectangle_borders (x, y >= 0; x + w <= width; y + h <= height; no
// wrap-around), written without the additions that could overflow.
template <class X, class Y, class W, class H, class FW, class FH>
inline bool rectangle(X x, Y y, W w, H h, FW fbWidth, FH fbHeight) {
    long long rx, ry, rw, rh, fw, fh;
    if (!detail::widen(x, rx) || !detail::widen(y, ry) ||
        !detail::widen(w, rw) || !detail::widen(h, rh) ||
        !detail::widen(fbWidth, fw) || !detail::widen(fbHeight, fh))
        return false;
    return rx >= 0 && ry >= 0 && rw >= 0 && rh >= 0 &&
           rx <= fw && ry <= fh && rw <= fw - rx && rh <= fh - ry;
}

// SoftCursorToScreen: clip one axis of the cursor rectangle to the framebuffer.
// position / length are in-out, offset is out (the caller starts it at 0).
// This is, verbatim in behaviour, the per-axis code that 6c44cfc removed from
// SoftCursorToScreen.
inline void clipAxis(int &position, int &length, int limit, int &offset) {
    if (position < 0) {
        offset = -position;
        length -= offset;
        position = 0;
    } else if (position + length > limit) {
        length = limit - position;
    }
    if (length < 0) {
        offset = 0;
        position = 0;
        length = 0;
    }
}

} // namespace ViewerBounds
"""

if __name__ == "__main__":
    with open(sys.argv[1], "w", newline="\n") as handle:
        handle.write(HEADER)
    print("wrote", sys.argv[1], len(HEADER), "bytes")
