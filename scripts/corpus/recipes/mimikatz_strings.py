"""mimikatz's generic string/output helpers, MinGW x86/x64.

https://github.com/r0ny123/mcrit-data/issues/60

Only modules/kull_m_string.c and modules/kull_m_output.c are selected.
Compatibility definitions erase six legacy SAL annotations and omit the
MSVC-specific TEXT(__FUNCTION__) prefix from two diagnostic macros. The
affected callers are kull_m_string_displaySID and
kull_m_string_args_bool_byName; their error-message strings therefore differ
from the MSVC build. Upstream source files are unchanged.

Measured kept + removed = image total: x86 57 + 61 = 118; x64
94 + 53 = 147. Each has 43 named project functions, including the
displayFileTime split body. Their project-only >=10-instruction unique
PicHash sets contain 41 hashes each, with zero intersection. Every
comparison with either MSVC module image also has zero intersection.

Runtime residues are recorded rather than attributed to the project:
x86 __stub and _vsprintf_s share 11014068063174420889 (34 instructions);
x64 _stub and vsprintf_s share 10856058160947307867 (34 instructions),
and __ms_vsnprintf has 9021751946683680786 (36 instructions). The
one-instruction __int_vsprintf_s / _int_vsprintf_s thunks both have
6102989692441836808. The vfwprintf, vswprintf_s, vwprintf, wcschr,
wcsstr and wprintf import thunks (leading underscore on x86) have
1253497258561142223. The x86 ___register_frame_info and
___deregister_frame_info thunks have the same hash. RtlStringFromGUID
and RtlFreeUnicodeString are OS imports, also one instruction with that
hash. The unnamed 15-instruction residue has 16132965489037543538
on x86 and 12578432865501340970 on x64; x64 also retains unnamed
one-instruction thunks with 1253497258561142223. No origin is assigned
to unnamed bodies. Raw >=10-instruction sets including these residues
contain 43 and 44 hashes. No shared baseline code is changed here.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_PREPARE = r"""python - <<'PY'
from pathlib import Path
import re
compat = r'''
#include <sal.h>
#ifndef __reserved
#define __reserved
#endif
#define __deref_out_bcount_full(...)
#define __field_bcount(...)
#define __in_bcount_opt(...)
#define __out_bcount_opt(...)
#define __out_ecount_opt(...)
#define PRINT_ERROR(...) (kprintf(L"ERROR ; " __VA_ARGS__))
#define PRINT_ERROR_AUTO(func) (kprintf(L"ERROR ; " func L" (0x%08x)\n", GetLastError()))
'''
Path('corpus_compat.h').write_text(compat)
out = Path('corpus-include')
out.mkdir(exist_ok=True)
headers = list(Path('inc').rglob('*.h')) + list(Path('modules').rglob('*.h'))
for p in headers:
    for name in re.findall(r'#\s*include\s*<([^>]+)>', p.read_text(errors='replace')):
        if name != name.lower() and '/' not in name and chr(92) not in name:
            (out / name).write_text('#include <' + name.lower() + '>\n')
PY"""

_BUILD = ('{cc} -shared -shared-libgcc -O2 -g -fms-extensions -fcommon '
          '-DUNICODE -D_UNICODE -D__USE_MINGW_ANSI_STDIO=0 '
          '-include corpus_compat.h -Iinc -Imodules -Imimikatz -Icorpus-include '
          '-Wl,--no-insert-timestamp -Wl,--no-gc-sections '
          'modules/kull_m_string.c modules/kull_m_output.c '
          '-o corpus-strings.dll -ladvapi32 -lcrypt32 -lrpcrt4 -lntdll -lshlwapi')

RECIPES = {
    'mimikatz_strings_45c42c7_mingw': Recipe(
        family='mimikatz', version='2.2.0-45c42c7-strings',
        upstream='https://github.com/rapid7/mimikatz', license='CC-BY-4.0',
        source=Source(git_url='https://github.com/rapid7/mimikatz.git',
                      git_ref='45c42c710fc3a9d7acdcd1f7acf966cc4ce07a49'),
        build=[BuildStep(_PREPARE), BuildStep(_BUILD)],
        artifacts=[Artifact(path='corpus-strings.dll', component='string-output')],
        toolchains=['mingw_x86', 'mingw_x64'],
        build_flags='-shared -shared-libgcc -O2 -g -fms-extensions -fcommon '
                    '-DUNICODE -D_UNICODE -D__USE_MINGW_ANSI_STDIO=0; '
                    'six legacy SAL compatibility definitions; diagnostic '
                    'macros omit TEXT(__FUNCTION__); '
                    '-Wl,--no-insert-timestamp -Wl,--no-gc-sections',
        notes='Only generic kull_m_string.c and kull_m_output.c helpers. '
              'No credential-extraction modules, dispatcher, SQLite, driver '
              'or Meterpreter wrapper. Generated headers adapt Windows '
              'header spelling and legacy SAL annotations to the cross SDK; '
              '-fcommon preserves the headers\' tentative shared globals. '
              'Two diagnostic macros omit the MSVC function-name prefix; '
              'the displaySID and args_bool_byName error strings differ. '
              'Upstream source files remain unchanged.'),
}
