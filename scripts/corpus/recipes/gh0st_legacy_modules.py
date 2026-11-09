"""The five previously excluded Gh0st translation units, MSVC x86.

https://github.com/r0ny123/mcrit-data/issues/64

An analysis copy has four compiler-compatibility edits: two explicit
const-casts for the old string API convention, removal of a repeated int
specifier in a for declaration, and explicit int for a legacy implicit-int
static. A forced modern SDK include exposes existing cursor/input types;
winable.h forwards to windows.h. Algorithms and initialization are unchanged.

Only these five units are linked, without the DLL entry point, dispatcher,
installer, driver, socket implementation or precompiled zlib. Entry RVA is
zero; omitted references remain unresolved. No built image is executed.
Every selected translation unit must compile; failures stop before linking.

Measured reference coverage (kept + removed = image total):
| target | kept | removed | total | named project hashes >=10 |
| --- | --- | --- | --- | --- |
| MSVC/x86/legacy | 153 | 129 | 282 | 85 |

Qualifying named project PicHash intersections (functions >=10 instructions):
| target | MinGW/x64/buffer | MinGW/x86/buffer | MSVC/x64/buffer | MSVC/x86/legacy | MSVC/x86/managers |
| --- | --- | --- | --- | --- | --- |
| MinGW/x64/buffer | - | 0 | 0 | 0 | 0 |
| MinGW/x86/buffer | 0 | - | 0 | 0 | 0 |
| MSVC/x64/buffer | 0 | 0 | - | 0 | 0 |
| MSVC/x86/legacy | 0 | 0 | 0 | - | 0 |
| MSVC/x86/managers | 0 | 0 | 0 | 0 | - |

Named one-instruction bodies (excluded by the instruction floor):
MSVC/x86/legacy: 15243261928622582637 [std::_Destroy_in_place<std::_List_node<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,void *> *>, std::_List_val<std::_List_simple_types<std::basic_string<char,std::char_traits<char>,std::allocator<char> > > >::_Orphan_non_end]; 12704011947623138095 [std::_List_val<std::_List_simple_types<std::basic_string<char,std::char_traits<char>,std::allocator<char> > > >::_Orphan_ptr2]; 6102989692441836808 [strstr, strrchr].

Retained standard-library instantiations excluded from project novelty:
16621027110400376038 [std::_List_node_emplace_op2<std::allocator<std::_List_node<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,void *> > >::_List_node_emplace_op2<std::allocator<std::_List_node<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,void *> > ><std::basic_string<char,std::char_traits<char>,std::allocator<char> > >]
6259359701635636530 [std::list<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,std::allocator<std::basic_string<char,std::char_traits<char>,std::allocator<char> > > >::_Emplace<std::basic_string<char,std::char_traits<char>,std::allocator<char> > >]
333188890071714026 [std::_List_node<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,void *>::_Free_non_head<std::allocator<std::_List_node<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,void *> > >]
6928628064633114395 [std::_List_node<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,void *>::_Freenode<std::allocator<std::_List_node<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,void *> > >]
5957423828140537367 [std::_Default_allocator_traits<std::allocator<std::_List_node<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,void *> > >::construct<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,std::basic_string<char,std::char_traits<char>,std::allocator<char> > >]
8002372961226255603 [std::list<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,std::allocator<std::basic_string<char,std::char_traits<char>,std::allocator<char> > > >::list<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,std::allocator<std::basic_string<char,std::char_traits<char>,std::allocator<char> > > >]
1595785715623390050 [std::_List_node_emplace_op2<std::allocator<std::_List_node<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,void *> > >::~_List_node_emplace_op2<std::allocator<std::_List_node<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,void *> > >]
8124075510069741701 [std::list<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,std::allocator<std::basic_string<char,std::char_traits<char>,std::allocator<char> > > >::~list<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,std::allocator<std::basic_string<char,std::char_traits<char>,std::allocator<char> > > >, std::list<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,std::allocator<std::basic_string<char,std::char_traits<char>,std::allocator<char> > > >::_Tidy]
9251247188013654020 [std::list<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,std::allocator<std::basic_string<char,std::char_traits<char>,std::allocator<char> > > >::_Alloc_sentinel_and_proxy]
1834777072813856861 [std::_List_node_emplace_op2<std::allocator<std::_List_node<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,void *> > >::_Transfer_before]
9230993418869963414 [std::_List_val<std::_List_simple_types<std::basic_string<char,std::char_traits<char>,std::allocator<char> > > >::_Unlinknode]
4896389439578248039 [std::allocator<std::_List_node<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,void *> >::allocate]
14259354937851781454 [std::list<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,std::allocator<std::basic_string<char,std::char_traits<char>,std::allocator<char> > > >::clear]
8176078890369149677 [std::_Default_allocator_traits<std::allocator<std::_List_node<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,void *> > >::deallocate]
3911504322373172056 [std::allocator<std::_List_node<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,void *> >::deallocate]
974464522415550525 [std::list<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,std::allocator<std::basic_string<char,std::char_traits<char>,std::allocator<char> > > >::erase]
16108038024615946928 [std::list<std::basic_string<char,std::char_traits<char>,std::allocator<char> >,std::allocator<std::basic_string<char,std::char_traits<char>,std::allocator<char> > > >::push_back]

The listed short bodies remain. No named compiler CRT implementation
longer than one instruction was identified in these new images.
"""

import base64

from ..recipe import Artifact, BuildStep, Recipe, Source


def _python(script):
    # Keep the reviewed script readable here; encode only for cmd.exe quoting.
    encoded = base64.b64encode(script.encode()).decode('ascii')
    return 'python -c "import base64; exec(base64.b64decode(\'' + encoded + '\'))"'


_PREPARE = r"""
from pathlib import Path
import shutil
out = Path('corpus-analysis')
shutil.rmtree(out, ignore_errors=True)
sources = [p for p in Path('.').rglob('*') if p.is_file() and
           p.suffix.lower() in ['.h', '.hpp', '.cpp', '.c', '.inl'] and
           '.git' not in p.parts and out.name not in p.parts]
for p in sources:
    target = out / p
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, target)
edits = [
    ('Server/svchost/common/FileManager.cpp',
     b"strrchr(lpFile, '.')", b"const_cast<char *>(strrchr(lpFile, '.'))"),
    ('Server/svchost/common/loop.h',
     b"strrchr(lpURL, '/')", b"const_cast<char *>(strrchr(lpURL, '/'))"),
    ('Server/svchost/common/ScreenSpy.cpp',
     b'for (int i = 0, int\tnToJump = 0;', b'for (int i = 0,\tnToJump = 0;'),
    ('Server/svchost/common/VideoManager.cpp',
     b'static\tdwLastScreen = GetTickCount();', b'static int\tdwLastScreen = GetTickCount();'),
]
for name, before, after in edits:
    p = out / name
    data = p.read_bytes()
    count = 2 if name.endswith('/loop.h') else 1
    assert data.count(before) == count, name
    # The earlier loop.h occurrence operates on a mutable local URL.
    # Only UpdateServer's final occurrence needs the const conversion.
    if count == 2:
        left, right = data.rsplit(before, 1)
        data = left + after + right
    else:
        data = data.replace(before, after)
    p.write_bytes(data)
(out / 'corpus-include').mkdir()
(out / 'corpus-include/winable.h').write_text('#pragma once\n#include <windows.h>\n')
(out / 'corpus_sdk.h').write_text(
    '#pragma once\n#include <winsock2.h>\n#include <windows.h>\n')
(out / 'corpus_obj').mkdir()
"""

_COMPILE = r"""
from pathlib import Path
import json
import struct
import subprocess
flags = ('/nologo /c /MD /O2 /Zi /GL- /Brepro /W3 '
         '/D_CRT_SECURE_NO_WARNINGS /D_WIN32_WINNT=0x0601 /DWINVER=0x0601 '
         '/Zc:strictStrings- /Zc:forScope- /FIcorpus_sdk.h '
         '/Icorpus-include /I. /IServer/svchost /Icommon').split()
sources = ['FileManager.cpp', 'KernelManager.cpp', 'ScreenManager.cpp',
           'ScreenSpy.cpp', 'VideoManager.cpp']
objects = []
failed = []
for i, name in enumerate(sources):
    obj = 'corpus_obj/' + str(i) + '.obj'
    cmd = ['cl'] + flags + ['/Fo'+obj, '/Fdcorpus_compile.pdb',
                            'Server/svchost/common/'+name]
    print('COMPILE:', subprocess.list2cmdline(cmd), flush=True)
    result = subprocess.run(cmd, check=False)
    if result.returncode:
        failed.append(name)
    else:
        objects.append(obj)
print('FAILED_SOURCE_FILES:'+json.dumps(failed), flush=True)
assert not failed, 'legacy source failed: '+repr(failed)
assert objects, 'no legacy module compiled'
cmd = ['link', '/DLL', '/NOENTRY', '/FORCE:UNRESOLVED', '/DEBUG', '/Brepro',
       '/INCREMENTAL:NO', '/OPT:NOREF', '/OPT:NOICF',
       '/OUT:corpus-legacy.dll', '/PDB:corpus-legacy.pdb'] + objects
print('LINK:', subprocess.list2cmdline(cmd), flush=True)
subprocess.run(cmd, check=True)
data = Path('corpus-legacy.dll').read_bytes()
pe = struct.unpack_from('<I', data, 60)[0]
assert data[pe:pe+4] == b'PE\0\0'
assert struct.unpack_from('<I', data, pe+40)[0] == 0
"""


RECIPES = {
    'Gh0st_legacy_modules_f434b0d_msvc': Recipe(
        family='Gh0st', version='2008-f434b0d-legacy-analysis',
        upstream='https://github.com/sincoder/gh0st',
        license='No licence file in the selected mirror',
        source=Source(git_url='https://github.com/sincoder/gh0st.git',
                      git_ref='f434b0df9d08540c8d81d82892def50198aa8849'),
        build=[BuildStep(_python(_PREPARE)),
               BuildStep(_python(_COMPILE), cwd='corpus-analysis')],
        artifacts=[Artifact(path='corpus-analysis/corpus-legacy.dll',
                            component='legacy-manager-modules',
                            pdb='corpus-analysis/corpus-legacy.pdb')],
        toolchains=['msvc_x86'], requires=['cl', 'link', 'python'],
        build_flags='/MD /O2 /Zi /GL- /Brepro; WINVER/_WIN32_WINNT=0x0601; '
                    '/Zc:strictStrings- /Zc:forScope-; forced modern SDK header; '
                    'four legacy compiler-compatibility edits; '
                    '/DLL /NOENTRY /FORCE:UNRESOLVED /DEBUG /Brepro '
                    '/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF',
        notes='Analysis copy of the five previously failing manager units. '
              'Two explicit const-casts preserve the old string API convention; '
              'a repeated int in a for declaration is removed; an implicit-int '
              'static is made explicitly int. Modern SDK types are included '
              'before legacy version defines, and winable.h forwards to '
              'windows.h. No algorithm, dispatcher or initialization is '
              'repaired. No entry point, driver, installer, socket body or '
              'precompiled zlib. References to omitted code remain unresolved. '
              'This non-operational analysis image is never executed. '
              'All five selected translation units must compile.'),
}
