"""Module-only Windows reference images.

Tracker: https://github.com/r0ny123/mcrit-data/issues/69 and
https://github.com/r0ny123/mcrit-data/issues/60.

These images have no entry point. TinyNuke includes only HiddenDesktop.cpp
and Socks.cpp, without its API initializer or banking body. The mimikatz
image includes only kuhl_m_* and kull_m_* translation units, without its
command dispatcher, SQLite amalgamation, or Meterpreter driver.

/FORCE:UNRESOLVED retains references to excluded code as unresolved symbols;
the resulting images are analysis containers, not upstream release binaries.
Those references and the missing initialization limit their reference value.
No source file is changed, and no compiled program is executed.

TinyNuke measured counts: x86 19 kept + 26 removed = 45 image functions;
x64 19 + 32 = 51. All nineteen kept functions have project symbols; no
named runtime glue survives. Both have eighteen unique >=10-instruction
PicHashes; their intersection is zero. Both architectures add coverage.

Measured r77 native counts: x86 128 kept + 28 removed = 156 image
functions; x64 127 + 33 = 160. Their >=10-instruction sets have 117 and
121 hashes, with intersection one: 9401389992967488103, carried by the
outlined FileInformationGetNextEntryOffset and FileInformationSetNextEntryOffset
blocks on both architectures. All four cross-compiler comparisons against
the MinGW collections images have intersection zero. No named runtime glue
survives in either MSVC image.

Measured mimikatz counts: x86 1340 kept + 43 removed = 1383; x64
1314 + 58 = 1372. The >=10-instruction unique sets have 1074 / 1060
hashes, with intersection zero. No named runtime glue survives. The
_RtlDecryptMemory symbols are the selected rapid7 fork's own wrapper,
not misattributed CRT code.

Gh0st MSVC x86 managers: 189 kept + 67 removed = 256; 123 unique
>=10-instruction hashes. Its intersections with each MinGW CBuffer image
are zero. Thirty-five one-instruction import thunks remain; the CRT one
is strstr, PicHash 6102989692441836808. The other 34 are OS imports,
all PicHash 1253497258561142223: _closesocket@4, _connect@12, _htons@4,
_ntohs@4, _recv@16, _select@20, _send@16, _setsockopt@20, _socket@12,
_gethostbyname@4, _WSAStartup@8, _WSACleanup@0, _WSAIoctl@36,
_waveInGetNumDevs@0, _waveOutGetNumDevs@0, _waveOutOpen@24,
_waveOutClose@4, _waveOutPrepareHeader@12, _waveOutUnprepareHeader@12,
_waveOutWrite@12, _waveOutReset@4, _waveInOpen@24, _waveInClose@4,
_waveInPrepareHeader@12, _waveInUnprepareHeader@12, _waveInAddBuffer@12,
_waveInStart@4, _waveInStop@4, _waveInReset@4, _ImmGetContext@4,
_ImmReleaseContext@8, _ImmGetCompositionStringA@16,
_WTSQuerySessionInformationA@20, _WTSFreeMemory@4.

Gh0st MSVC x64 CBuffer: 16 kept + 4 removed = 20 image functions;
12 unique >=10-instruction hashes. It shares none with the other three
Gh0st images above the instruction floor. The only named runtime residue
is the one-instruction strstr import thunk, PicHash 6102989692441836808.

The five excluded Gh0st TUs remain expected-failure compiler probes, and
are not linked. Unexpected failure of any included TU fails the recipe;
an excluded TU starting to compile also fails it so coverage can be reviewed.
Keeping the same compiler-PDB history reproduces the probe's linked image.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_FLAGS = '/nologo /c /MD /O2 /Zi /GL- /W3 /D_CRT_SECURE_NO_WARNINGS'
_LINK = ('/DLL /NOENTRY /FORCE:UNRESOLVED /DEBUG /Brepro '
         '/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF')


def _analysis_steps(selection, includes, defines, path_names=False, excluded=()):
    # Numbered object files preserve TUs that share a basename.
    prepare = (
        "from pathlib import Path; import json,shutil; "
        "shutil.rmtree('corpus_obj',ignore_errors=True); "
        "Path('corpus_obj').mkdir(exist_ok=True); "
        "files=" + selection + "; "
        "assert files, 'no module source files selected'; "
        "assert all(p.is_file() for p in files), 'missing module source'; "
        "Path('corpus_sources.json').write_text(json.dumps([str(p) for p in files])); "
        "print('Module sources:',len(files))"
    )
    object_name = ("__import__('hashlib').sha1(p.replace(chr(92),'/').encode()).hexdigest()"
                   if path_names else "str(i)")
    compile_sources = (
        "from pathlib import Path; import json,subprocess; "
        "files=json.loads(Path('corpus_sources.json').read_text()); "
        "excluded=" + repr(excluded) + "; "
        "results=[(p,subprocess.run(['cl']+'" + _FLAGS + ' ' + includes + ' ' + defines +
        "'.split()+['/Focorpus_obj/'+" + object_name +
        "+'.obj','/Fdcorpus_compile.pdb',p],"
        "check=p.replace(chr(92),'/') not in excluded).returncode) "
        "for i,p in enumerate(files)]; "
        "assert all(c!=0 for p,c in results if p.replace(chr(92),'/') in excluded), "
        "'previously excluded source compiled; revisit coverage'; "
        "print('SKIPPED_SOURCE_FILES:'+json.dumps([p for p,c in results if c]))"
    )
    link = (
        "from pathlib import Path; import subprocess; "
        "objects=sorted(Path('corpus_obj').glob('*.obj')); "
        "assert objects, 'no compiled objects'; "
        "subprocess.run(['link']+'" + _LINK + "'.split()+"
        "['/OUT:corpus.dll','/PDB:corpus.pdb']+[str(p) for p in objects],check=True)"
    )
    return [
        BuildStep('python -c "' + prepare + '"'),
        BuildStep('python -c "' + compile_sources + '"'),
        BuildStep('python -c "' + link + '"'),
    ]


RECIPES = {
    'gh0st_buffer_f434b0d_msvc': Recipe(
        family='Gh0st', version='2008-f434b0d-buffer',
        upstream='https://github.com/sincoder/gh0st',
        license='No licence file in the selected mirror',
        source=Source(git_url='https://github.com/sincoder/gh0st.git',
                      git_ref='f434b0df9d08540c8d81d82892def50198aa8849'),
        build=_analysis_steps("[Path('Server/svchost/common/Buffer.cpp')]",
                              '/IServer/svchost/common', ''),
        artifacts=[Artifact(path='corpus.dll', component='buffer', pdb='corpus.pdb')],
        toolchains=['msvc_x64'], requires=['cl', 'link', 'python'],
        build_flags=_FLAGS + '; ' + _LINK,
        notes='Only the reusable CBuffer translation unit. Its x86 MSVC '
              'functions are already in the manager image; this adds x64 '
              'MSVC coverage beside the MinGW references. No entry point, '
              'protocol handler, installer, driver or precompiled zlib. '
              'References remain unresolved in this analysis container.'),
    'gh0st_managers_f434b0d_msvc': Recipe(
        family='Gh0st', version='2008-f434b0d-managers',
        upstream='https://github.com/sincoder/gh0st',
        license='No licence file in the selected mirror',
        source=Source(git_url='https://github.com/sincoder/gh0st.git',
                      git_ref='f434b0df9d08540c8d81d82892def50198aa8849'),
        build=_analysis_steps(
            "sorted(Path('Server/svchost/common').glob('*.cpp'))+"
            "[Path('Server/svchost/ClientSocket.cpp'),Path('common/Audio.cpp')]",
            '/I. /IServer/svchost /Icommon',
            '/D_WIN32_WINNT=0x0601 /Zc:strictStrings- /Zc:forScope-',
            path_names=True,
            excluded=('Server/svchost/common/FileManager.cpp',
                      'Server/svchost/common/KernelManager.cpp',
                      'Server/svchost/common/ScreenManager.cpp',
                      'Server/svchost/common/ScreenSpy.cpp',
                      'Server/svchost/common/VideoManager.cpp')),
        artifacts=[Artifact(path='corpus.dll', component='manager-modules',
                            pdb='corpus.pdb')],
        toolchains=['msvc_x86'], requires=['cl', 'link', 'python'],
        build_flags=_FLAGS + ' /D_WIN32_WINNT=0x0601 '
                    '/Zc:strictStrings- /Zc:forScope-; ' + _LINK,
        notes='Pinned public mirror. Manager and socket translation units '
              'only; the DLL entry point, standalone installer project, kernel driver and '
              'vendored precompiled zlib library are excluded. The '
              'common/install.cpp manager helper is included. The native '
              'server project declares UseOfMfc=false. Five incompatible '
              'translation units are excluded explicitly: FileManager, '
              'KernelManager, ScreenManager, ScreenSpy and VideoManager. '
              'Their exact errors are recorded in the corpus README. '
              'References to excluded '
              'code remain unresolved in this analysis image. The published '
              'project is Win32-only; no x64 build is claimed.'),
    'r77_modules_1.8.2_msvc': Recipe(
        family='r77', version='1.8.2-modules',
        upstream='https://github.com/bytecode77/r77-rootkit', license='MIT',
        source=Source(git_url='https://github.com/bytecode77/r77-rootkit.git',
                      git_ref='cea145c1518784d95df8d7fe1808952b12e5cdb4'),
        build=_analysis_steps(
            "sorted(p for root in ['r77','r77api'] for p in Path(root).glob('*.c'))",
            '/Ir77 /Ir77api /IReflectiveDllMain', '/DUNICODE /D_UNICODE',
            path_names=True),
        artifacts=[Artifact(path='corpus.dll', component='native-modules',
                            pdb='corpus.pdb')],
        toolchains=['msvc_x86', 'msvc_x64'], requires=['cl', 'link', 'python'],
        build_flags=_FLAGS + ' /DUNICODE /D_UNICODE; ' + _LINK,
        notes='Native r77 and r77api translation units only, compiled with '
              'the runner compiler rather than the project v145 toolset. '
              'No installer, service, helper, reflective entry wrapper, '
              'post-build encryptor or precompiled Detours library. References '
              'to excluded code remain unresolved. No entry point; this is '
              'an analysis container, not an upstream release DLL.'),
    'TinyNuke_modules_c1e04c3_msvc': Recipe(
        family='TinyNuke', version='2017-c1e04c3-modules',
        upstream='https://github.com/rossja/TinyNuke',
        license='No licence file in the selected mirror',
        source=Source(git_url='https://github.com/rossja/TinyNuke.git',
                      git_ref='c1e04c36d3aa2dbd70fcb17063809798b00b1fcf'),
        build=_analysis_steps(
            "[Path('Bot/HiddenDesktop.cpp'),Path('Bot/Socks.cpp')]", '/I.', ''),
        artifacts=[Artifact(path='corpus.dll', component='hvnc-socks-modules',
                            pdb='corpus.pdb')],
        toolchains=['msvc_x86', 'msvc_x64'], requires=['cl', 'link', 'python'],
        build_flags=_FLAGS + '; ' + _LINK,
        notes='Pinned third-party mirror of the published source. Only the '
              'hidden-desktop and reverse SOCKS module translation units are '
              'compiled. No banking body, API initialization or entry point. '
              'References to excluded code remain unresolved in this analysis '
              'image; it is not an upstream release build.'),
    'mimikatz_modules_45c42c7_msvc': Recipe(
        family='mimikatz', version='2.2.0-45c42c7-modules',
        upstream='https://github.com/rapid7/mimikatz', license='CC-BY-4.0',
        source=Source(git_url='https://github.com/rapid7/mimikatz.git',
                      git_ref='45c42c710fc3a9d7acdcd1f7acf966cc4ce07a49'),
        build=_analysis_steps(
            "[Path('mimikatz')/e.attrib['Include'].replace(chr(92),'/') "
            "for e in __import__('xml.etree.ElementTree',fromlist=['ElementTree'])"
            ".parse('mimikatz/mimikatz.vcxproj').iter() "
            "if e.tag.endswith('ClCompile') and 'Include' in e.attrib "
            "and Path(e.attrib['Include'].replace(chr(92),'/')).name"
            ".startswith(('kuhl_m_','kull_m_'))]",
            '/Iinc /Imimikatz /Imodules', '/DUNICODE /D_UNICODE',
            path_names=True),
        artifacts=[Artifact(path='corpus.dll', component='kuhl-kull-modules',
                            pdb='corpus.pdb')],
        toolchains=['msvc_x86', 'msvc_x64'], requires=['cl', 'link', 'python'],
        build_flags=_FLAGS + ' /DUNICODE /D_UNICODE; ' + _LINK,
        notes='The consumer-pinned rapid7 fork. Only kuhl_m_* and kull_m_* '
              'translation units are compiled. The command dispatcher, '
              'SQLite amalgamation, drivers and Meterpreter wrapper are '
              'excluded. No entry point; references to excluded code remain '
              'unresolved. This analysis image is not mimikatz.exe or kiwi.'),
}
