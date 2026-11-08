"""Unchanged Havoc entry-wrapper sources as inert PE reference modules.

https://github.com/r0ny123/mcrit-data/issues/19

Only MainExe.c, MainSvc.c or MainDll.c is compiled, without DemonMain,
loader implementations, runtime or configuration bytes. PE entry RVA is
zero and omitted references remain unbound. SERVICE_NAME is an empty string,
not an operator service name. No profile, listener, generator or built image
is run. The SHELLCODE axis covers only that C wrapper, not a raw payload.

Final pipeline counts: all functions are named, removed runtime = 0;
kept = image total. No runtime was linked.
| target | functions | qualifying project PicHashes >=10 |
| --- | --- | --- |
| EXE entry/x86 | 1 | 1 |
| Service entry/x86 | 3 | 3 |
| Service entry/x64 | 3 | 3 |
| DLL entry/x86 | 2 | 2 |
| DLL entry/x64 | 2 | 2 |
| SHELLCODE entry/x86 | 1 | 1 |
| SHELLCODE entry/x64 | 1 | 1 |

Every qualifying hash is distinct, with zero intersection against the four
existing Demon core images. The x64 EXE entry compiles to just seven
instructions and adds no qualifying hash, so no reference is retained.
The one-function floor is deliberate: each retained image has at least one
upstream function of ten or more instructions, without compiler glue.

Measured function names and PicHashes:
x86 EXE: _WinMain@16 [10, 4362472911133097057].
x86 service: _SrvCtrlHandler@4 [18, 17298697321043775043];
_SvcMain@8 [17, 17366219502646337935]; _WinMain@16 [19, 12164371174352006398].
x64 service: SrvCtrlHandler [10, 18070645025870545331];
SvcMain [13, 1138264854922710682]; WinMain [16, 15508831345060118111].
x86 DLL: _DllMain@12 [25, 14830061058783605963]; _Start [14, 6712612406289215157].
x64 DLL: DllMain [23, 6918033854415606898]; Start [11, 12932720886135666993].
x86 SHELLCODE entry: _DllMain@12 [14, 12535287407231294578].
x64 SHELLCODE entry: DllMain [11, 7687964916825522465].
No runtime or unnamed glue survives. Final pipeline reports match every
probe function's name, instruction count and PicHash.
"""

from dataclasses import replace

from ..recipe import Artifact, BuildStep, Recipe, Source


_BUILD = r"""python - <<'PY'
from pathlib import Path
import os
import re
import shutil
import struct
import subprocess
kind = os.environ['CORPUS_WRAPPER']
source = {'exe': 'MainExe.c', 'service': 'MainSvc.c',
          'dll': 'MainDll.c', 'shellcode-entry': 'MainDll.c'}[kind]
defines = (['-DSERVICE_NAME=""'] if kind == 'service' else
           ['-DSHELLCODE'] if kind == 'shellcode-entry' else [])
flags = ('-Os -g -fno-asynchronous-unwind-tables -masm=intel -fno-ident '
         '-fpack-struct=8 -falign-functions=1 -ffunction-sections '
         '-fdata-sections -falign-jumps=1 -falign-labels=1 -fPIC '
         '-Iinclude -DTRANSPORT_HTTP').split()
out = Path('corpus_entry')
shutil.rmtree(out, ignore_errors=True)
out.mkdir(exist_ok=True)
cmd = ['{cc}', '-c'] + flags + defines + ['src/main/'+source,
                                        '-o', str(out/'entry.o')]
print('COMPILE:', subprocess.list2cmdline(cmd), flush=True)
subprocess.run(cmd, check=True)
cmd = ['{cc}', '-shared', '-nostdlib', '-Wl,--entry,0',
       '-Wl,--noinhibit-exec,--no-gc-sections,--no-insert-timestamp',
       '-Wl,--no-seh,--enable-stdcall-fixup', str(out/'entry.o'),
       '-o', str(out/'reference-entry.dll')]
print('LINK:', subprocess.list2cmdline(cmd), flush=True)
result = subprocess.run(cmd, text=True, capture_output=True, check=True)
print(result.stdout, end='')
print(result.stderr, end='')
assert not re.search(r'overflow|truncated|overlap|cannot|invalid|out of range|fatal', result.stderr, re.I)
data = (out/'reference-entry.dll').read_bytes()
pe = struct.unpack_from('<I', data, 60)[0]
assert data[pe:pe+4] == b'PE\0\0'
assert struct.unpack_from('<I', data, pe+40)[0] == 0
print('Verified: PE entry RVA is zero', flush=True)
PY"""

_SNAPSHOT = r"""
from pathlib import Path
import os
import shutil
source = Path('corpus_entry')
target = Path('corpus_entries')/os.environ['CORPUS_WRAPPER']
target.mkdir(parents=True, exist_ok=True)
for name in ['reference-entry.dll', 'reference-entry.pdb']:
    if (source/name).is_file():
        shutil.copy2(source/name, target/name)
"""


_base = Recipe(
    family='HavocDemon', version='0.7-c84f775-entry-analysis',
    upstream='https://github.com/HavocFramework/Havoc', license='GPL-3.0',
    source=Source(
        url='https://codeload.github.com/HavocFramework/Havoc/tar.gz/c84f7755a8b1c0f737576bdd3a0e982a296012f1',
        sha256='8aa6bb6002dfe0626f9c01a3a298192d0e932aa7b839cd76d9e14439454172c7'),
    build=[], artifacts=[], toolchains=['mingw_x86', 'mingw_x64'],
    requires=['python'], min_functions=1,
    build_flags='GCC -Os -g -fno-asynchronous-unwind-tables -masm=intel '
                '-fno-ident -fpack-struct=8 -falign-functions=1 '
                '-ffunction-sections -fdata-sections -falign-jumps=1 '
                '-falign-labels=1 -fPIC -DTRANSPORT_HTTP; -shared -nostdlib; '
                '--entry,0 --noinhibit-exec --no-gc-sections '
                '--no-insert-timestamp --no-seh --enable-stdcall-fixup',
    notes='Unchanged single entry-wrapper translation unit from pinned Havoc '
          '0.7. DemonMain, loader implementations, runtime and configuration '
          'bytes are absent. PE entry RVA is asserted zero and omitted '
          'references remain unbound. This is an inert reference module, '
          'not a release EXE, service, DLL or raw payload. No profile, '
          'listener, generator or compiled image is run. The one-function '
          'floor retains a measured upstream body of at least ten instructions; '
          'the x64 EXE wrapper has only seven instructions and is omitted. '
          'Components identify individual translation units; SERVICE_NAME is '
          'empty for the service wrapper, and SHELLCODE selects only the C '
          'entry wrapper. Components are separately linked translation units.')

RECIPES = {}
for _arch in ['x86', 'x64']:
    _steps, _artifacts = [], []
    _kinds = (['exe'] if _arch == 'x86' else [])+['service', 'dll', 'shellcode-entry']
    for _kind in _kinds:
        _label = _kind.replace('-', '_') + ('' if _kind.endswith('-entry') else '_entry')
        _extra = ('; -DSERVICE_NAME=""' if _kind == 'service' else
                  '; -DSHELLCODE' if _kind == 'shellcode-entry' else '')
        _environment = {'CORPUS_WRAPPER': _kind}
        _steps += [BuildStep(_BUILD, cwd='payloads/Demon', env=_environment),
                   BuildStep("python - <<'PY'\n"+_SNAPSHOT+"\nPY",
                             cwd='payloads/Demon', env=_environment)]
        _artifacts.append(Artifact(
            path='payloads/Demon/corpus_entries/'+_kind+'/reference-entry.dll',
            component=_label.replace('_', '-')+'-analysis',
            build_flags=_base.build_flags+_extra))
    RECIPES['HavocDemon_c84f775_entries_mingw_'+_arch] = replace(
        _base,
        build=_steps, artifacts=_artifacts, toolchains=['mingw_'+_arch])
