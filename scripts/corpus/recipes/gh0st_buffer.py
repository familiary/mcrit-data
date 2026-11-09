"""Gh0st's reusable CBuffer implementation, MinGW x86/x64.

https://github.com/r0ny123/mcrit-data/issues/64

This is only Server/svchost/common/Buffer.cpp: memory-buffer management and
critical-section synchronization, with no agent entry point or protocol
handler. It compiles independently of the rest of the published mirror.
The MSVC manager image includes this TU among others, so comparing their
PicHashes measures both a compiler change and a selected-source difference.

Measured counts: x86 23 kept + 50 removed = 73 image functions; x64
32 + 50 = 82. Each retains 17 named CBuffer functions. At >=10 instructions
the unique PicHash sets have 14 / 13 entries, with intersection zero, so both
architectures add coverage.

Surviving named import thunks all have PicHash 1253497258561142223 and one
instruction. x86: ___gxx_personality_v0, operator delete(void*, unsigned int),
___register_frame_info, ___deregister_frame_info, _strstr. x64:
__gxx_personality_seh0, operator delete(void*, unsigned long long), strstr.
No named CRT startup body survives. Each image also has an unnamed
15-instruction function: x86 16132965489037543538; x64
12578432865501340970. x64 has eleven additional unnamed one-instruction
thunks with PicHash 1253497258561142223. These are reported, not assigned a
source identity from their size alone.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


RECIPES = {
    'gh0st_buffer_f434b0d_mingw': Recipe(
        family='Gh0st', version='2008-f434b0d-buffer',
        upstream='https://github.com/sincoder/gh0st',
        license='No licence file in the selected mirror',
        source=Source(git_url='https://github.com/sincoder/gh0st.git',
                      git_ref='f434b0df9d08540c8d81d82892def50198aa8849'),
        build=[BuildStep(
            '{cxx} -shared -shared-libgcc -O2 -g '
            '-Wl,--no-insert-timestamp -Wl,--no-gc-sections '
            'Server/svchost/common/Buffer.cpp -o corpus-buffer.dll')],
        artifacts=[Artifact(path='corpus-buffer.dll', component='buffer')],
        toolchains=['mingw_x86', 'mingw_x64'],
        build_flags='-shared -shared-libgcc -O2 -g '
                    '-Wl,--no-insert-timestamp -Wl,--no-gc-sections',
        notes='Only the independently compilable CBuffer memory-management '
              'translation unit is selected. No protocol, agent entry point, '
              'installer, driver, or precompiled zlib library. MinGW runtime '
              'glue is removed with the measured baseline. libstdc++ and '
              'libgcc are linked dynamically.'),
}
