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
"""

import base64
from dataclasses import replace

from ..recipe import Artifact, BuildStep
from .havoc_entry_wrappers import _base


def _python(script):
    encoded = base64.b64encode(script.encode()).decode('ascii')
    return 'python -c "import base64; exec(base64.b64decode(\''+encoded+'\'))"'


_BUILD_MSVC = r"""
from pathlib import Path
import os
import re
import struct
import subprocess
kind = os.environ['CORPUS_WRAPPER']
source = {'exe': 'MainExe.c', 'service': 'MainSvc.c',
          'dll': 'MainDll.c', 'shellcode-entry': 'MainDll.c'}[kind]
out = Path('corpus_entry')
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


RECIPES = {}
for _kind in ['exe', 'service', 'dll', 'shellcode-entry']:
    _label = _kind.replace('-', '_') + ('' if _kind.endswith('-entry') else '_entry')
    _extra = ('; SERVICE_NAME=""' if _kind == 'service' else
              '; SHELLCODE' if _kind == 'shellcode-entry' else '')
    RECIPES['HavocDemon_c84f775_'+_label+'_msvc'] = replace(
        _base,
        build=[BuildStep(_python(_BUILD_MSVC), cwd='payloads/Demon',
                         env={'CORPUS_WRAPPER': _kind})],
        artifacts=[Artifact(path='payloads/Demon/corpus_entry/reference-entry.dll',
                            component=_label.replace('_', '-')+'-analysis',
                            pdb='payloads/Demon/corpus_entry/reference-entry.pdb')],
        toolchains=['msvc_x86', 'msvc_x64'],
        requires=['cl', 'link', 'python'],
        build_flags='/TC /std:c11 /MD /O1 /Zi /GL- /Brepro; '
                    'narrow ABI include adapter, original macros and declarations; '
                    '/DLL /NOENTRY /NODEFAULTLIB /FORCE:UNRESOLVED /DEBUG '
                    '/Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF'+_extra,
        notes='MSVC isolated entry wrapper: '+_kind+'. '
              'The wrapper C source is unchanged. A narrow include adapter '
              'uses Windows SDK types, unchanged upstream Macros.h/Defines.h, '
              'and verbatim KAYN_ARGS/external prototypes from the pinned source. '
              'It implements no missing function. /O1 corresponds to upstream '
              'GCC size optimization. No default libraries or entry point; '
              'DemonMain, loaders and system imports remain unbound. '
              'No configuration bytes, operator profile, listener, generator '
              'or compiled program. This is an inert PE analysis module, '
              'not a configured release.'+
              (' SERVICE_NAME is empty.' if _kind == 'service' else
               ' SHELLCODE selects only the C entry wrapper, not a raw image.'
               if _kind == 'shellcode-entry' else ''))
