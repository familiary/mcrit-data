"""TinyNuke's two selected modules with MinGW SDK compatibility adapters.

https://github.com/r0ny123/mcrit-data/issues/69

Only HiddenDesktop.cpp and Socks.cpp are compiled. An analysis copy
normalizes include separators and uses the SDK's existing LSA string
declaration, retaining the original UNICODE_STRING aliases. No algorithm,
dispatcher, API initializer, banking body or endpoint setting is changed.
The PE has no entry point; unresolved API pointers stay unbound. This is
an analysis container, not a deployable client. No executable is run.

Measured reference coverage (kept + removed = image total):
| target | kept | removed | total | named project hashes >=10 |
| --- | --- | --- | --- | --- |
| MinGW/x64/modules | 13 | 0 | 13 | 13 |
| MinGW/x86/modules | 13 | 0 | 13 | 13 |

Qualifying named project PicHash intersections (functions >=10 instructions):
| target | MinGW/x64/modules | MinGW/x86/modules | MSVC/x64/modules | MSVC/x86/modules |
| --- | --- | --- | --- | --- |
| MinGW/x64/modules | - | 0 | 0 | 0 |
| MinGW/x86/modules | 0 | - | 0 | 0 |
| MSVC/x64/modules | 0 | 0 | - | 0 |
| MSVC/x86/modules | 0 | 0 | 0 | - |

Named one-instruction bodies (excluded by the instruction floor):
MinGW/x64/modules: none.
MinGW/x86/modules: none.

The listed short bodies remain. No named compiler CRT implementation
longer than one instruction was identified in these new images.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_PREPARE = r"""python - <<'PY'
from pathlib import Path
import re
import shutil
out = Path('corpus-analysis')
shutil.rmtree(out, ignore_errors=True)
sources = [p for p in Path('.').rglob('*') if p.is_file() and
           p.suffix.lower() in ['.h', '.hpp', '.cpp', '.c', '.inl'] and
           '.git' not in p.parts and out.name not in p.parts]
for p in sources:
    target = out / p
    target.parent.mkdir(parents=True, exist_ok=True)
    data = p.read_bytes()
    data = re.sub(rb'(#\s*include\s*[<"])([^>"\r\n]+)([>"])',
                  lambda m: m[1] + m[2].replace(bytes([92]), b'/') + m[3], data)
    target.write_bytes(data)
p = out / 'Api.h'
data = p.read_bytes()
pattern = rb'typedef struct _LSA_UNICODE_STRING\s*\{[^}]*\}\s*LSA_UNICODE_STRING, \*PLSA_UNICODE_STRING, UNICODE_STRING, \*PUNICODE_STRING;'
replacement = (b'#ifndef __UNICODE_STRING_DEFINED\n'
               b'#define __UNICODE_STRING_DEFINED\n'
               b'typedef LSA_UNICODE_STRING UNICODE_STRING, *PUNICODE_STRING;\n'
               b'#endif')
data, count = re.subn(pattern, replacement, data)
assert count == 1, 'unexpected LSA declaration'
p.write_bytes(data)
for filename, begin, end in [
    ('Bot/HiddenDesktop.cpp', b'   char *isRelativeRead =', b'exit:\n   Funcs::pCloseHandle(hProfilesIni);'),
    ('Bot/Socks.cpp', b'   if(socksSocket == INVALID_SOCKET)', b'exit:\n   Funcs::pClosesocket(socksSocket);'),
]:
    p = out / filename
    data = p.read_bytes()
    assert data.count(begin) == data.count(end) == 1
    # Leave initialization order and cleanup code unchanged; gotos leave
    # this inner POD-only scope instead of crossing its declarations.
    data = data.replace(begin, b'   {\n' + begin).replace(end, b'   }\n' + end)
    p.write_bytes(data)
includes = out / 'corpus-include'
includes.mkdir()
for p in out.rglob('*'):
    if not p.is_file() or p.suffix.lower() not in ['.h', '.hpp', '.cpp']:
        continue
    for name in re.findall(r'#\s*include\s*<([^>]+)>', p.read_text(errors='replace')):
        if name != name.lower() and '/' not in name:
            (includes / name).write_text('#include <' + name.lower() + '>\n')
PY"""

_BUILD = ('{cxx} -shared -nostdlib -O2 -g -fms-extensions -fpermissive '
          '-I. -Icorpus-include '
          '-Wl,--entry,0,--noinhibit-exec,--no-gc-sections,--no-insert-timestamp '
          'Bot/HiddenDesktop.cpp Bot/Socks.cpp -o corpus-tinynuke.dll')


RECIPES = {
    'TinyNuke_modules_c1e04c3_mingw_analysis': Recipe(
        family='TinyNuke', version='2017-c1e04c3-modules-analysis',
        upstream='https://github.com/rossja/TinyNuke',
        license='No licence file in the selected mirror',
        source=Source(git_url='https://github.com/rossja/TinyNuke.git',
                      git_ref='c1e04c36d3aa2dbd70fcb17063809798b00b1fcf'),
        build=[BuildStep(_PREPARE), BuildStep(_BUILD, cwd='corpus-analysis'),
               BuildStep('python -c "import struct; from pathlib import Path; '
                         "b=Path('corpus-tinynuke.dll').read_bytes(); "
                         "p=struct.unpack_from('<I',b,60)[0]; "
                         "assert struct.unpack_from('<I',b,p+40)[0]==0" + '"',
                         cwd='corpus-analysis')],
        artifacts=[Artifact(path='corpus-analysis/corpus-tinynuke.dll',
                            component='hvnc-socks-modules')],
        toolchains=['mingw_x86', 'mingw_x64'], requires=['python'],
        build_flags='-shared -nostdlib -O2 -g -fms-extensions -fpermissive; '
                    'SDK LSA_UNICODE_STRING with original Unicode aliases; '
                    'include spelling/separator adapters; two POD inner scopes '
                    'for legacy goto compatibility; --entry,0 '
                    '--noinhibit-exec --no-gc-sections --no-insert-timestamp',
        notes='Only HiddenDesktop.cpp and Socks.cpp in an analysis copy. '
              'Include separators and SDK header case are adapted; the '
              'duplicate LSA_UNICODE_STRING definition uses the SDK type '
              'with unchanged field layout and Unicode aliases. Two inner '
              'POD-only scopes preserve initialization order and let gotos '
              'reach the existing cleanup labels without crossing declarations. No source '
              'algorithm or initialization is repaired. No dispatcher, '
              'banking body or API initializer. PE entry RVA is zero; '
              'unresolved API pointers remain unbound. This non-operational '
              'container is never executed. Upstream files are preserved.'),
}
