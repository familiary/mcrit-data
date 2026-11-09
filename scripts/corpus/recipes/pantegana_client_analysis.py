"""Pantegana client source retained in an inert reference executable.

https://github.com/r0ny123/mcrit-data/issues/71

The client package is unchanged. The missing generated certificate loader
is represented by a nil function variable, not a working implementation.
ClientSetup therefore cannot initialize a client. Its indirect Asset call
differs from a configured upstream build and must not be treated as an
exact reference for that call site. No certificate or configuration is made.

A separate main retains function addresses without calling them. It never
calls RunClient, LoadClientConfig, a network operation or a command handler.
No built executable is run. This is an analysis container, not a deployable
client. The generated main.main is not upstream code.

Measured reference coverage (kept + removed = image total):
| target | kept | removed | total | named project hashes >=10 |
| --- | --- | --- | --- | --- |
| client/ELF/x64 | 41 | 6233 | 6274 | 23 |
| client/ELF/x86 | 42 | 6236 | 6278 | 25 |
| client/PE/x64 | 24 | 6097 | 6121 | 15 |
| client/PE/x86 | 28 | 6238 | 6266 | 17 |

Qualifying named project PicHash intersections (functions >=10 instructions):
| target | client/ELF/x64 | client/ELF/x86 | client/PE/x64 | client/PE/x86 | fingerprint/ELF/x64 | fingerprint/ELF/x86 | fingerprint/PE/x64 | fingerprint/PE/x86 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| client/ELF/x64 | - | 0 | 14 | 0 | 12 | 0 | 3 | 0 |
| client/ELF/x86 | 0 | - | 0 | 0 | 0 | 3 | 0 | 0 |
| client/PE/x64 | 14 | 0 | - | 0 | 3 | 0 | 4 | 0 |
| client/PE/x86 | 0 | 0 | 0 | - | 0 | 0 | 0 | 2 |
| fingerprint/ELF/x64 | 12 | 0 | 3 | 0 | - | 0 | 3 | 0 |
| fingerprint/ELF/x86 | 0 | 3 | 0 | 0 | 0 | - | 0 | 0 |
| fingerprint/PE/x64 | 3 | 0 | 4 | 0 | 3 | 0 | - | 0 |
| fingerprint/PE/x86 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | - |

Project-hash counts exclude generated main/entry wrappers, init routines,
unnamed bodies and functions outside the project module namespace.
Retained namespace counts (not all retained functions are project code):
client/ELF/x64: first_party=32, startup=2, unnamed=7.
client/ELF/x86: first_party=32, startup=2, unnamed=8.
client/PE/x64: first_party=21, generated=1, startup=2.
client/PE/x86: first_party=21, generated=1, startup=2, unnamed=4.

Measured changed entry/startup bodies, excluded from novelty:
client/ELF/x64: github.com/elleven11/pantegana/client.init [21 instructions, 5361203891044470350]; main.main [63 instructions, 18329123925316287233].
client/ELF/x86: github.com/elleven11/pantegana/client.init [24 instructions, 18339763922917829041]; main.main [64 instructions, 4154797354884597779].
client/PE/x64: github.com/elleven11/pantegana/client.init [21 instructions, 5361203891044470350]; main.main [63 instructions, 18329123925316287233].
client/PE/x86: github.com/elleven11/pantegana/client.init [25 instructions, 9636465576449246893]; main.main [65 instructions, 16787043664655807242].

Unscoped compiler-generated helpers (no project ownership is inferred):
type:.eq.[4]string: client/PE/x64 [50 instructions / 112253892832525255 x1]; client/PE/x86 [50 instructions / 12437469830097930878 x1].

Unassigned unnamed body hashes, grouped by instruction count and PicHash:
client/ELF/x64: 4 instructions / 466242121924152354 x2; 4 instructions / 4279976378107065028 x2; 4 instructions / 10209695728725523735 x1; 4 instructions / 17258110151367771384 x1; 8 instructions / 8968255406261624498 x1.
client/ELF/x86: 3 instructions / 4990884184229136202 x1; 3 instructions / 5411627868933477166 x1; 3 instructions / 6057988224881723664 x2; 3 instructions / 8686872467240596747 x2; 3 instructions / 16954392341414018250 x1; 176 instructions / 13305663080152205606 x1.
client/PE/x64: none.
client/PE/x86: 3 instructions / 4990884184229136202 x1; 3 instructions / 5411627868933477166 x1; 3 instructions / 8686872467240596747 x2.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_PREPARE = r"""python - <<'PY'
from pathlib import Path
import re
import shutil
import subprocess
assert subprocess.check_output(['go', 'version'], text=True).split()[2] == 'go1.24.13'
out = Path('corpus-client-analysis')
(out / 'client').mkdir(parents=True, exist_ok=True)
for name in ['go.mod', 'go.sum']:
    shutil.copy2(name, out / name)
exports = []
for source in sorted(Path('client').glob('*.go')):
    assert source.name != 'cert.go', 'unexpected certificate assets'
    text = source.read_text()
    assert not re.search(r'^func\s+init\s*\(', text, re.M), 'review package initializer'
    shutil.copy2(source, out / 'client' / source.name)
    exports.extend(re.findall(r'^func ([A-Z]\w*)\(', text, re.M))
assert len(exports) == len(set(exports))
(out / 'client/corpus_asset.go').write_text(
    'package client\nvar Asset func(string) ([]byte, error)\n')
args = ', '.join('client.' + name for name in sorted(exports))
(out / 'main.go').write_text(
    'package main\nimport ("fmt"; "github.com/elleven11/pantegana/client")\n'
    'func main() { fmt.Printf("' + '%p ' * len(exports) + '", ' + args + ') }\n')
print('Retained exports:', ', '.join(sorted(exports)))
PY"""


RECIPES = {
    'pantegana_client_analysis_0.1.0_go124': Recipe(
        family='Pantegana', version='0.1.0-go1.24.13-client-analysis',
        upstream='https://github.com/cassanof/pantegana',
        license='Custom BSD four-clause licence with a use restriction',
        source=Source(
            url='https://goproxy.cn/github.com/cassanof/pantegana/@v/v0.1.0.zip',
            sha256='9cd268855031a35ff3dd26cb37a801bdd7a2ad3fe11c6c3a64743341cdc95ba6',
            strip_prefix='cassanof/pantegana@v0.1.0'),
        build=[BuildStep(_PREPARE), BuildStep(
            'go build -mod=readonly -trimpath '
            '-gcflags=github.com/elleven11/pantegana/client=-l '
            '-o reference-client .', cwd='corpus-client-analysis',
            env={'GOOS': '{goos}', 'GOARCH': '{goarch}',
                 'CGO_ENABLED': '0', 'GOTOOLCHAIN': 'local'})],
        artifacts=[Artifact(path='corpus-client-analysis/reference-client',
                            component='client-analysis')],
        toolchains=['linux_x86', 'linux_x64', 'mingw_x86', 'mingw_x64'],
        requires=['go', 'python'], glue_filter='go',
        build_flags='Go 1.24.13; CGO_ENABLED=0 GOTOOLCHAIN=local; '
                    '-mod=readonly -trimpath '
                    '-gcflags=github.com/elleven11/pantegana/client=-l; '
                    'nil Asset function variable; inert address-only main',
        notes='All client/*.go from the pinned v0.1.0 archive, unchanged. '
              'The missing certificate loader is a nil function variable; '
              'ClientSetup cannot initialize a client and its indirect Asset '
              'call differs from a configured build. No certificates, '
              'operator configuration, server or upstream generator. '
              'A generated main retains exported function addresses without '
              'calling them; no executable is run. This is a non-operational '
              'reference image. Source is pinned by archive SHA-256; no Git '
              'commit is invented. Platform ids describe the target container; '
              'Go 1.24.13 is the actual compiler.'),
}
