"""Havoc Demon source in an unconfigured PE analysis container.

https://github.com/r0ny123/mcrit-data/issues/19

No upstream builder, listener, profile or generator is run. CONFIG_BYTES
is a zero-length array, not a serialized configuration. The EXE, service,
DLL-entry and shellcode wrappers are omitted. The PE has entry RVA zero.
Unresolved references are retained as unbound addresses, not implemented.
This file describes a non-operational reference image, not a Demon payload.

The upstream -Os layout flags are retained, with symbols and all functions
kept for analysis. C and architecture-matching NASM translation units are
compiled unchanged. References affected by the empty config and unresolved
symbols limit matching fidelity. No built image is executed.

Measured reference coverage (kept + removed = image total):
| target | kept | removed | total | named project hashes >=10 |
| --- | --- | --- | --- | --- |
| HTTP/x64 | 343 | 0 | 343 | 301 |
| HTTP/x86 | 338 | 0 | 338 | 315 |
| SMB/x64 | 339 | 0 | 339 | 297 |
| SMB/x86 | 334 | 0 | 334 | 311 |

Qualifying named project PicHash intersections (functions >=10 instructions):
| target | HTTP/x64 | HTTP/x86 | SMB/x64 | SMB/x86 |
| --- | --- | --- | --- | --- |
| HTTP/x64 | - | 0 | 83 | 0 |
| HTTP/x86 | 0 | - | 0 | 93 |
| SMB/x64 | 83 | 0 | - | 0 |
| SMB/x86 | 0 | 93 | 0 | - |

Named one-instruction bodies (excluded by the instruction floor):
HTTP/x64: 10549330385929968764 [BeaconDataStoreProtectItem, BeaconDataStoreUnprotectItem, BeaconInformation]; 6102989692441836808 [PackageAddPtr, ParserGetString, ParserGetWString].
HTTP/x86: 10549330385929968764 [Spoof, _BeaconDataStoreProtectItem, _BeaconDataStoreUnprotectItem, _BeaconInformation]; 6102989692441836808 [_ParserGetString, _ParserGetWString].
SMB/x64: 10549330385929968764 [BeaconDataStoreProtectItem, BeaconDataStoreUnprotectItem, BeaconInformation]; 6102989692441836808 [PackageAddPtr, ParserGetString, ParserGetWString].
SMB/x86: 10549330385929968764 [Spoof, _BeaconDataStoreProtectItem, _BeaconDataStoreUnprotectItem, _BeaconInformation]; 6102989692441836808 [_ParserGetString, _ParserGetWString].

The listed short bodies remain. No named compiler CRT implementation
longer than one instruction was identified in these new images.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from dataclasses import replace


_BUILD = r"""python - <<'PY'
from pathlib import Path
import re
import shutil
import struct
import subprocess
objects = Path('corpus_obj')
shutil.rmtree(objects, ignore_errors=True)
objects.mkdir()
cc = '{cc}'
bits = '{bitness}'
flags = ('-Os -g -fno-asynchronous-unwind-tables -masm=intel -fno-ident '
         '-fpack-struct=8 -falign-functions=1 -ffunction-sections '
         '-fdata-sections -falign-jumps=1 -falign-labels=1 -fPIC '
         '-Iinclude -DTRANSPORT_HTTP -DCONFIG_BYTES={}').split()
sources = [Path('src/Demon.c')]
for directory in ['core', 'crypt', 'inject']:
    sources += sorted(Path('src', directory).glob('*.c'))
print('C source count:', len(sources), flush=True)
for i, source in enumerate(sources):
    subprocess.run([cc, '-c'] + flags + [str(source), '-o', str(objects / ('c'+str(i)+'.o'))], check=True)
suffix = 'x64' if bits == '64' else 'x86'
assembly = sorted(Path('src/asm').glob('*.' + suffix + '.asm'))
assert len(assembly) == 2
print('ASM sources:', [str(p) for p in assembly], flush=True)
for i, source in enumerate(assembly):
    subprocess.run(['nasm', '-f', 'win'+bits, str(source), '-o', str(objects / ('a'+str(i)+'.o'))], check=True)
link = [cc, '-shared', '-nostdlib', '-Wl,--entry,0',
        '-Wl,--noinhibit-exec,--no-gc-sections,--no-insert-timestamp',
        '-Wl,--no-seh,--enable-stdcall-fixup']
link += [str(p) for p in sorted(objects.glob('*.o'))]
link += ['-o', 'corpus-demon.dll']
result = subprocess.run(link, text=True, capture_output=True, check=True)
print(result.stdout, end='')
print(result.stderr, end='')
Path('corpus_link.log').write_text(result.stdout + result.stderr)
assert not re.search(r'overflow|truncated|overlap|cannot|invalid|out of range|fatal', result.stderr, re.I)
data = Path('corpus-demon.dll').read_bytes()
pe = struct.unpack_from('<I', data, 0x3c)[0]
assert data[pe:pe+4] == b'PE\0\0'
assert struct.unpack_from('<I', data, pe+40)[0] == 0, 'unexpected executable entry'
print('Verified: PE entry RVA is zero', flush=True)
PY"""


RECIPES = {
    'HavocDemon_c84f775_analysis_mingw': Recipe(
        family='HavocDemon', version='0.7-c84f775-analysis',
        upstream='https://github.com/HavocFramework/Havoc', license='GPL-3.0',
        source=Source(git_url='https://github.com/HavocFramework/Havoc.git',
                      git_ref='c84f7755a8b1c0f737576bdd3a0e982a296012f1'),
        build=[BuildStep(_BUILD, cwd='payloads/Demon')],
        artifacts=[Artifact(path='payloads/Demon/corpus-demon.dll',
                            component='demon-analysis')],
        toolchains=['mingw_x86', 'mingw_x64'], requires=['nasm', 'python'],
        build_flags='GCC -Os -g -fno-asynchronous-unwind-tables -masm=intel '
                    '-fno-ident -fpack-struct=8 -falign-functions=1 '
                    '-ffunction-sections -fdata-sections -falign-jumps=1 '
                    '-falign-labels=1 -fPIC -DTRANSPORT_HTTP '
                    '-DCONFIG_BYTES={}; NASM win32/win64; -shared -nostdlib; '
                    '--entry,0 --noinhibit-exec --no-gc-sections '
                    '--no-insert-timestamp --no-seh --enable-stdcall-fixup',
        notes='Unchanged Demon.c, core, crypt, inject and architecture-matching '
              'NASM sources. CONFIG_BYTES is an empty array, not a valid '
              'configuration. No listener, server, profile, generator, entry '
              'wrapper or shellcode assembly step. PE entry RVA is asserted '
              'zero. Unresolved references remain unbound; this is an inert '
              'analysis container, not an upstream release binary. The '
              'empty config and unresolved references limit matching fidelity. '
              'No compiled program is executed. Symbols and all functions are '
              'retained with -g and --no-gc-sections. NASM 2.16.01 tested.'),
}

# HTTP and SMB select different transport bodies and Instance layouts.
_http = RECIPES['HavocDemon_c84f775_analysis_mingw']
RECIPES['HavocDemon_c84f775_smb_analysis_mingw'] = replace(
    _http, version='0.7-c84f775-smb-analysis',
    build=[BuildStep(_BUILD.replace('-DTRANSPORT_HTTP', '-DTRANSPORT_SMB'),
                     cwd='payloads/Demon')],
    artifacts=[Artifact(path='payloads/Demon/corpus-demon.dll',
                        component='demon-smb-analysis')],
    build_flags=_http.build_flags.replace('TRANSPORT_HTTP', 'TRANSPORT_SMB'),
    notes='SMB transport selected. ' + _http.notes)
