/* Case shim for <Windows.h>.
 *
 * Several upstream projects here include the capital-W spelling, which
 * exists on MSVC's case-insensitive filesystem and not in a mingw-w64
 * sysroot on Linux, where the SDK header ships as <windows.h> and the
 * capital form is a hard "No such file or directory". Used by
 * crummie5/FreshyCalls (utils.cpp) and WKL-Sec/LayeredSyscall (all three
 * translation units).
 *
 * Upstream is not modified; this sits on the include path ahead of the
 * sysroot and forwards. wow64pp.cpp's docstring records the same obstacle,
 * solved there by editing the corpus's own exerciser rather than a shim,
 * because that include was the exerciser's to begin with.
 */
#include <windows.h>
