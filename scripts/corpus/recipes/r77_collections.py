"""r77's integer/string collection helpers, MinGW x86/x64.

https://github.com/r0ny123/mcrit-data/issues/17

Only r77api/clist.c is compiled: integer and string lists, allocation,
comparison and registry-value loading. No hook, injection, installer,
service or entry-point source is included. The generated include adapters
preserve Windows header spelling on the case-sensitive cross-build host.

Measured: x86 15 kept + 48 removed = 63 image functions; x64
31 + 48 = 79. Both contain twelve named collection functions and thirteen
unique >=10-instruction PicHashes, with intersection zero. Named glue
survivors on x86 are ___register_frame_info and ___deregister_frame_info,
both one-instruction import thunks with PicHash 1253497258561142223. There
are no named glue survivors on x64. Each has one unnamed 15-instruction
function: x86 16132965489037543538; x64 12578432865501340970. The x64 image
also has eighteen unnamed one-instruction thunks, all hash
1253497258561142223. At >=10 instructions the two MinGW components in this
group (r77 collections and Gh0st CBuffer) share only that unnamed function
on their corresponding architectures; their named project code does not
overlap.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


RECIPES = {
    'r77_collections_1.8.2_mingw': Recipe(
        family='r77', version='1.8.2-collections',
        upstream='https://github.com/bytecode77/r77-rootkit', license='MIT',
        source=Source(git_url='https://github.com/bytecode77/r77-rootkit.git',
                      git_ref='cea145c1518784d95df8d7fe1808952b12e5cdb4'),
        build=[
            BuildStep('mkdir -p corpus-include'),
            BuildStep("printf '%s\\n' '#include <windows.h>' > corpus-include/Windows.h"),
            BuildStep("printf '%s\\n' '#include <shlwapi.h>' > corpus-include/Shlwapi.h"),
            BuildStep('{cc} -shared -shared-libgcc -O2 -g -Icorpus-include '
                      '-Wl,--no-insert-timestamp -Wl,--no-gc-sections '
                      'r77api/clist.c -o corpus-collections.dll -ladvapi32 -lshlwapi'),
        ],
        artifacts=[Artifact(path='corpus-collections.dll', component='collections')],
        toolchains=['mingw_x86', 'mingw_x64'],
        build_flags='-shared -shared-libgcc -O2 -g -Icorpus-include '
                    '-Wl,--no-insert-timestamp -Wl,--no-gc-sections '
                    '-ladvapi32 -lshlwapi',
        notes='Only the reusable r77api/clist.c collection-management '
              'translation unit. Hooking, injection, services, installers '
              'and entry-point source are excluded. Two generated include '
              'adapters map Windows.h and Shlwapi.h to the cross SDK lower-case '
              'names; upstream files are unchanged. Compiler runtime glue '
              'is removed using the measured baseline.'),
}
