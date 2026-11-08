// Force-included (-include) into the UltraVNC addon projects that use MSVC
// structured exception handling only as try/finally with __leave
// (addon/ms-logon/authSSP and MSLogonACL). GCC has no __try/__finally.
//
//   __try { body; if (x) __leave; body; } __finally { cleanup }
//
// becomes
//
//   do { body; if (x) break; body; } while (0); { cleanup }
//
// which runs the cleanup on the normal path and after __leave, as the SEH
// form does. The eight protected blocks of those sources contain no `return`,
// no loop or switch around a __leave, and no goto, so `break` always leaves
// the do-while (checked when the recipe was written). Nothing here is
// included into the other UltraVNC projects. Only an exception raised inside a
// block (which these blocks do not handle either: there is no __except) would
// behave differently.
#ifndef UVNC_MINGW_SEH_H
#define UVNC_MINGW_SEH_H
#define __try do
#define __leave break
#define __finally while (0);
#endif
