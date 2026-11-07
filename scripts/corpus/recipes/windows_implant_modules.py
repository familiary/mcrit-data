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

Counts, measured overlap and glue survivors require the Windows probe.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_FLAGS = '/nologo /c /MD /O2 /Zi /GL- /W3 /D_CRT_SECURE_NO_WARNINGS'
_LINK = ('/DLL /NOENTRY /FORCE:UNRESOLVED /DEBUG /Brepro '
         '/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF')


def _analysis_steps(selection, includes, defines):
    # Numbered object files preserve TUs that share a basename.
    prepare = (
        "from pathlib import Path; import json; "
        "Path('corpus_obj').mkdir(exist_ok=True); "
        "files=" + selection + "; "
        "assert files, 'no module source files selected'; "
        "assert all(p.is_file() for p in files), 'missing module source'; "
        "Path('corpus_sources.json').write_text(json.dumps([str(p) for p in files])); "
        "print('Module sources:',len(files))"
    )
    compile_sources = (
        "from pathlib import Path; import json,subprocess; "
        "files=json.loads(Path('corpus_sources.json').read_text()); "
        "[subprocess.run(['cl']+'" + _FLAGS + ' ' + includes + ' ' + defines +
        "'.split()+['/Focorpus_obj/'+str(i)+'.obj','/Fdcorpus_compile.pdb',p],"
        "check=True) for i,p in enumerate(files)]"
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
    'gh0st_managers_f434b0d_msvc': Recipe(
        family='Gh0st', version='2008-f434b0d-managers',
        upstream='https://github.com/sincoder/gh0st',
        license='No licence file in the selected mirror',
        source=Source(git_url='https://github.com/sincoder/gh0st.git',
                      git_ref='f434b0df9d08540c8d81d82892def50198aa8849'),
        build=_analysis_steps(
            "sorted(Path('Server/svchost/common').glob('*.cpp'))+"
            "[Path('Server/svchost/ClientSocket.cpp'),Path('common/Audio.cpp')]",
            '/I. /IServer/svchost /Icommon', '/D_WIN32_WINNT=0x0601'),
        artifacts=[Artifact(path='corpus.dll', component='manager-modules',
                            pdb='corpus.pdb')],
        toolchains=['msvc_x86'], requires=['cl', 'link', 'python'],
        build_flags=_FLAGS + ' /D_WIN32_WINNT=0x0601; ' + _LINK,
        notes='Pinned public mirror. Manager and socket translation units '
              'only; the DLL entry point, installer, kernel driver and '
              'vendored precompiled zlib library are excluded. The native '
              'server project declares UseOfMfc=false. References to excluded '
              'code remain unresolved in this analysis image. The published '
              'project is Win32-only; no x64 build is claimed.'),
    'r77_modules_1.8.2_msvc': Recipe(
        family='r77', version='1.8.2-modules',
        upstream='https://github.com/bytecode77/r77-rootkit', license='MIT',
        source=Source(git_url='https://github.com/bytecode77/r77-rootkit.git',
                      git_ref='cea145c1518784d95df8d7fe1808952b12e5cdb4'),
        build=_analysis_steps(
            "sorted(p for root in ['r77','r77api'] for p in Path(root).glob('*.c'))",
            '/Ir77 /Ir77api', '/DUNICODE /D_UNICODE'),
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
            "sorted(p for root in ['mimikatz/modules','modules'] "
            "for p in Path(root).rglob('*.c') "
            "if p.name.startswith(('kuhl_m_','kull_m_')))",
            '/Iinc /Imimikatz /Imodules', '/DUNICODE /D_UNICODE'),
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
