"""MSVC reference modules for isolated Havoc entry-wrapper translation units.

https://github.com/r0ny123/mcrit-data/issues/19

A narrow ABI header shadows Demon.h for these wrappers only. It includes
the Windows SDK and the unchanged upstream Macros.h/Defines.h, and copies
the KAYN_ARGS declaration and three external prototypes verbatim from the
pinned source. It supplies no implementations. Wrapper C source is unchanged.
The MinGW adapter probe matches every original-header function's instruction
count and PicHash across all eight wrapper/architecture combinations.

Only one wrapper is linked, with no entry point or default libraries.
DemonMain, loader implementations and Windows imports remain unbound.
SERVICE_NAME is empty. No operator configuration, listener, generator or
compiled program is run; the SHELLCODE axis is a C wrapper, not a raw payload.
/O1 is the MSVC size-optimization axis corresponding to upstream GCC -Os.
Both MSVC EXE wrappers compile to seven instructions and contribute no
qualifying hash, so their probe reports are not retained or rebuilt here.

Final pipeline counts (kept + removed = image total):
| target | kept | removed | total | project hashes >=10 |
| --- | --- | --- | --- | --- |
| DLL/x86 | 2 | 0 | 2 | 2 |
| DLL/x64 | 2 | 0 | 2 | 2 |
| Service/x86 | 3 | 0 | 3 | 3 |
| Service/x64 | 3 | 0 | 3 | 3 |
| SHELLCODE entry/x86 | 1 | 0 | 1 | 1 |
| SHELLCODE entry/x64 | 1 | 0 | 1 | 1 |

All twelve qualifying hashes are distinct and absent from all eleven MinGW
core/wrapper images. Every pairwise intersection involving these six MSVC
images is zero. All retained functions are named upstream wrapper bodies;
there are no compiler-runtime or unnamed glue survivors.

Names, instruction counts and PicHashes:
x86 DLL: DllMain [21, 11478679369897697195]; Start [12, 10591290605386392827].
x64 DLL: DllMain [23, 18430308115402373341]; Start [11, 8409726247246470924].
x86 service: SrvCtrlHandler [12, 9179473813025253959];
SvcMain [12, 13611189387544418140]; WinMain [13, 7433608153378873844].
x64 service: SrvCtrlHandler [11, 12814594968443433547];
SvcMain [12, 4399200255458970354]; WinMain [13, 2994295849177101067].
x86 SHELLCODE entry: DllMain [12, 10359797890655294555].
x64 SHELLCODE entry: DllMain [10, 13643239936221682631].
"""

import base64
from dataclasses import replace

from ..recipe import Artifact, BuildStep
from .havoc_entry_wrappers import _base, _SNAPSHOT


def _python(script):
    encoded = base64.b64encode(script.encode()).decode('ascii')
    return 'python -c "import base64; exec(base64.b64decode(\''+encoded+'\'))"'


_BUILD_MSVC = r"""
from pathlib import Path
import os
import re
import shutil
import struct
import subprocess
kind = os.environ['CORPUS_WRAPPER']
source = {'exe': 'MainExe.c', 'service': 'MainSvc.c',
          'dll': 'MainDll.c', 'shellcode-entry': 'MainDll.c'}[kind]
out = Path('corpus_entry')
shutil.rmtree(out, ignore_errors=True)
adapter = out/'include'
adapter.mkdir(parents=True, exist_ok=True)
demon = Path('include/Demon.h').read_text()
win32 = Path('include/core/Win32.h').read_text()
start = demon.index('#pragma pack(1)')
end = demon.index('} KAYN_ARGS, *PKAYN_ARGS;')+len('} KAYN_ARGS, *PKAYN_ARGS;')
declarations = demon[start:end]+'\n'
for name, text, result in [('DemonMain', demon, 'VOID'),
                           ('LdrFunctionAddr', win32, 'PVOID'),
                           ('LdrModulePeb', win32, 'PVOID')]:
    matches = re.findall(result+r' '+name+r'\([^;]+;', text)
    assert len(matches) == 1, name
    declarations += matches[0]+'\n'
(adapter/'Demon.h').write_text(
    '#pragma once\n#include <windows.h>\n'
    '#include <common/Macros.h>\n#include <common/Defines.h>\n'+declarations)
defines = (['/DSERVICE_NAME=""'] if kind == 'service' else
           ['/DSHELLCODE'] if kind == 'shellcode-entry' else [])
cmd = ['cl', '/nologo', '/c', '/TC', '/std:c11', '/MD', '/O1', '/Zi',
       '/GL-', '/Brepro', '/W3', '/D_CRT_SECURE_NO_WARNINGS',
       '/I'+str(adapter), '/Iinclude', '/Focorpus_entry/entry.obj',
       '/Fdcorpus_entry/compile.pdb']+defines+['src/main/'+source]
print('COMPILE:', subprocess.list2cmdline(cmd), flush=True)
subprocess.run(cmd, check=True)
cmd = ['link', '/DLL', '/NOENTRY', '/NODEFAULTLIB', '/FORCE:UNRESOLVED',
       '/DEBUG', '/Brepro', '/INCREMENTAL:NO', '/OPT:NOREF', '/OPT:NOICF',
       '/OUT:corpus_entry/reference-entry.dll',
       '/PDB:corpus_entry/reference-entry.pdb', 'corpus_entry/entry.obj']
print('LINK:', subprocess.list2cmdline(cmd), flush=True)
subprocess.run(cmd, check=True)
data = (out/'reference-entry.dll').read_bytes()
pe = struct.unpack_from('<I', data, 60)[0]
assert data[pe:pe+4] == b'PE\0\0'
assert struct.unpack_from('<I', data, pe+40)[0] == 0
print('Verified: PE entry RVA is zero', flush=True)
"""


_MSVC_FLAGS = ('/TC /std:c11 /MD /O1 /Zi /GL- /Brepro; '
               'narrow ABI include adapter, original macros and declarations; '
               '/DLL /NOENTRY /NODEFAULTLIB /FORCE:UNRESOLVED /DEBUG '
               '/Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF')
_steps, _artifacts = [], []
for _kind in ['service', 'dll', 'shellcode-entry']:
    _label = _kind.replace('-', '_') + ('' if _kind.endswith('-entry') else '_entry')
    _extra = ('; /DSERVICE_NAME=""' if _kind == 'service' else
              '; /DSHELLCODE' if _kind == 'shellcode-entry' else '')
    _environment = {'CORPUS_WRAPPER': _kind}
    _steps += [BuildStep(_python(_BUILD_MSVC), cwd='payloads/Demon', env=_environment),
               BuildStep(_python(_SNAPSHOT), cwd='payloads/Demon', env=_environment)]
    _artifacts.append(Artifact(
        path='payloads/Demon/corpus_entries/'+_kind+'/reference-entry.dll',
        component=_label.replace('_', '-')+'-analysis',
        pdb='payloads/Demon/corpus_entries/'+_kind+'/reference-entry.pdb',
        build_flags=_MSVC_FLAGS+_extra))

RECIPES = {
    'HavocDemon_c84f775_entries_msvc': replace(
        _base,
        build=_steps, artifacts=_artifacts,
        toolchains=['msvc_x86', 'msvc_x64'],
        requires=['cl', 'link', 'python'],
        build_flags=_MSVC_FLAGS,
        notes='MSVC isolated entry wrappers, one translation unit per component. '
              'The wrapper C source is unchanged. A narrow include adapter '
              'uses Windows SDK types, unchanged upstream Macros.h/Defines.h, '
              'and verbatim KAYN_ARGS/external prototypes from the pinned source. '
              'It implements no missing function. /O1 corresponds to upstream '
              'GCC size optimization. No default libraries or entry point; '
              'DemonMain, loaders and system imports remain unbound. '
              'No configuration bytes, operator profile, listener, generator '
              'or compiled program. This is an inert PE analysis module, '
              'not a configured release. SERVICE_NAME is empty for the service '
              'wrapper; SHELLCODE selects only the C entry wrapper, not a raw '
              'image. Components are separately linked translation units.'),
}
