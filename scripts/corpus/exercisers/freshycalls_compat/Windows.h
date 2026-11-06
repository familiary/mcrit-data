/* Case shim: utils.cpp includes <Windows.h>, which exists on MSVC's
   case-insensitive filesystem and not in a mingw-w64 sysroot on Linux,
   where the SDK header ships as <windows.h> and the capital-W spelling is
   a hard "No such file or directory". Upstream is not modified; this sits
   on the include path ahead of the sysroot and forwards. */
#include <windows.h>
