"""Pantegana v0.1.0 fingerprinting helpers, Go 1.24.13.

https://github.com/r0ny123/mcrit-data/issues/71

The original GitHub source is unavailable. This is the surviving v0.1.0
module-proxy archive, pinned by SHA-256; no Git commit is invented for it.
The archive's module identity is github.com/elleven11/pantegana despite the
cassanof download namespace. The full client fails with undefined: Asset
because its generated certificate loader is absent. No certificates,
configuration, generator or client program are created or run here.

Only the unmodified client/fingerprinter.go is copied into an isolated module.
A deterministic exerciser retains references to its two exported functions;
it never calls them. Network, command-dispatch and upload/download code is
excluded. The exerciser's main.main is recorded separately from upstream
functions in the measured results.

Measured kept + removed = total: ELF x86 22 + 2491 = 2513; ELF x64
20 + 2469 = 2489; PE x86 6 + 2217 = 2223; PE x64 6 + 2148 = 2154.
Excluding the generated main.main and unnamed bodies, the >=10-instruction
unique sets contain 12, 12, 4 and 4 hashes respectively. ELF x64 / PE x64
share three hashes; PE x64 therefore adds one qualifying hash. Every other
pairwise intersection is zero, including both architecture pairs. This
supports retaining all four targets despite the small Windows surface.
The shared x64 hashes are GetCurrentSysInfo (3447971822550276658),
SysInfo equality (6968918267917478699), and different generated wrappers
(10090810199626105093): fingerprintLinux.func1.deferwrap1 versus
RunFingerprinter.gowrap1. The last is not identical source functionality.
PE x64's additional hash is RunFingerprinter, 9515341546036655739.

No named runtime/stdlib functions survive the Go filter. The retained
unnamed ELF x64 bodies are three four-instruction functions with PicHashes
466242121924152354 (twice) and 10209695728725523735. ELF x86 retains
three three-instruction bodies (6057988224881723664 twice,
16954392341414018250 once), one five-instruction body
15887320587343595534, and one 135-instruction body 4914378269895427466.
Their source identity is not inferred from location alone. PE retains no
unnamed functions.

The generated main.main is not included in coverage novelty: ELF x86 hash
13867234399740677848 (29 instructions), PE x86 12438267624702556364
(30), and both x64 targets 11359584896225716666 (26).

Go 1.24.13 is within the corpus's covered runtime range. Inlining is disabled
only for the client package to retain its small helper functions. The Go
glue filter removes standard-library and runtime functions. Existing
toolchain ids describe target containers; Go is the actual compiler, pinned
and checked by this recipe.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from dataclasses import replace


RECIPES = {
    'pantegana_fingerprint_0.1.0_go124': Recipe(
        family='Pantegana', version='0.1.0-go1.24.13-fingerprint',
        upstream='https://github.com/cassanof/pantegana',
        license='Custom BSD four-clause licence with a use restriction',
        source=Source(
            url='https://goproxy.cn/github.com/cassanof/pantegana/@v/v0.1.0.zip',
            sha256='9cd268855031a35ff3dd26cb37a801bdd7a2ad3fe11c6c3a64743341cdc95ba6',
            strip_prefix='cassanof/pantegana@v0.1.0'),
        build=[
            BuildStep('python -c "import subprocess; '
                      "assert subprocess.check_output(['go','version'],text=True).split()[2]"
                      "=='go1.24.13', 'Go 1.24.13 required'" + '"'),
            BuildStep('python -c "from pathlib import Path; import shutil; '
                      "r=Path('corpus-fingerprint'); (r/'client').mkdir(parents=True,exist_ok=True); "
                      "shutil.copy2('client/fingerprinter.go',r/'client/fingerprinter.go'); "
                      "shutil.copy2('go.mod',r/'go.mod'); shutil.copy2('go.sum',r/'go.sum'); "
                      "q=chr(34); code='package main'+chr(10)+'import ('+q+'fmt'+q+';'+q+"
                      "'github.com/elleven11/pantegana/client'+q+')'+chr(10)+"
                      "'func main() { fmt.Printf('+q+'%p %p'+q+"
                      "', client.RunFingerprinter, client.GetCurrentSysInfo) }'+chr(10); "
                      "(r/'main.go').write_text(code)" + '"'),
            BuildStep('go build -mod=readonly -trimpath '
                      '-gcflags=github.com/elleven11/pantegana/client=-l '
                      '-o corpus-client .', cwd='corpus-fingerprint',
                      env={'GOOS': '{goos}', 'GOARCH': '{goarch}',
                           'CGO_ENABLED': '0', 'GOTOOLCHAIN': 'local'}),
        ],
        artifacts=[Artifact(path='corpus-fingerprint/corpus-client',
                            component='fingerprint')],
        toolchains=['linux_x86', 'linux_x64', 'mingw_x86', 'mingw_x64'],
        requires=['go', 'python'], glue_filter='go',
        build_flags='Go 1.24.13; CGO_ENABLED=0 GOTOOLCHAIN=local; '
                    '-mod=readonly -trimpath '
                    '-gcflags=github.com/elleven11/pantegana/client=-l',
        notes='Only the unmodified client/fingerprinter.go is compiled with '
              'a generated exerciser referencing its exported functions. '
              'The exerciser never calls them, and no executable is run. '
              'No network, command-dispatch, upload/download, certificate '
              'loader or configuration code is included. Source is the surviving '
              'v0.1.0 module archive pinned by SHA-256, not a verified Git '
              'commit. Go 1.24.13 replaces the go.mod 1.16 language-era '
              'toolchain. Package-specific -l retains client helpers. '
              'The Go glue filter removes runtime and standard-library code; '
              'platform toolchain ids and the preserved wrapper banner '
              'identify the target container; the compiler field prefix '
              'records the actual Go 1.24.13 compiler.'),
}

# The Windows branch in the published helper is an empty TODO. Its exact
# retained surface is six functions: two exports, the empty Windows method,
# its goroutine wrapper, SysInfo equality, and the exerciser. This is a
# measured platform difference, not a failed or truncated client build.
_template = RECIPES.pop('pantegana_fingerprint_0.1.0_go124')
RECIPES = {
    'pantegana_fingerprint_0.1.0_go124_linux': replace(
        _template, toolchains=['linux_x86', 'linux_x64']),
    'pantegana_fingerprint_0.1.0_go124_windows': replace(
        _template, toolchains=['mingw_x86', 'mingw_x64'], min_functions=6,
        notes=_template.notes + ' The published Windows fingerprint method '
              'is empty. Its measured surface is six functions including '
              'the exerciser and generated wrappers; the per-platform '
              'function floor is six. Linux retains the default floor.'),
}
