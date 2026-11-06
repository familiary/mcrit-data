/* One NT typedef the Windows SDK does not provide, force-included for the
 * SysWhispers4 MSVC builds.
 *
 * The generated SW_Types.h asserts that "CLIENT_ID, IO_STATUS_BLOCK,
 * PIO_APC_ROUTINE -- in <winternl.h> ... All are available after the
 * #includes above; do not redefine." For MSVC that is half right: the SDK's
 * <winternl.h> declares the CLIENT_ID struct and not the pointer typedef, so
 * SW4_NtOpenProcess and SW4_NtOpenThread - the two prototypes that take a
 * PCLIENT_ID - fail with
 *
 *   SW.h(32): error C2146: syntax error: missing ')' before identifier 'ClientId'
 *   SW.h(32): error C2081: 'PCLIENT_ID': name in formal parameter list illegal
 *
 * mingw-w64's headers do define it, which is why the GAS side never saw this.
 *
 * It is the only type missing: every other NT type in those prototypes -
 * POBJECT_ATTRIBUTES, PPS_ATTRIBUTE_LIST, MEMORY_INFORMATION_CLASS and the
 * rest - compiled without complaint in the same translation unit.
 *
 * Force-included with /FI rather than added to upstream's header, so the
 * generated source is untouched. /FI is processed before the file's own
 * includes, so this pulls in the two SDK headers itself.
 */

#include <windows.h>
#include <winternl.h>

#ifndef SW4_COMPAT_PCLIENT_ID
#define SW4_COMPAT_PCLIENT_ID
typedef CLIENT_ID *PCLIENT_ID;
#endif
