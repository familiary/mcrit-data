"""ReflectiveDLLInjection built with MSVC, beside the MinGW builds.

Both repositories are Visual Studio projects first - upstream's README says
"open rdi.sln in Visual Studio and build in Release mode" - and
``ReflectiveLoader`` leans on MSVC specifics: the ``_ReturnAddress`` intrinsic
in ``caller()``, ``#pragma intrinsic(_rotr)``, ``__forceinline`` and SEH in the
injector. The MSVC artefact is the one analysts meet. The pins, the reasons for
two repositories and the function inventory are in reflectivedllinjection.py.

Why ``cl`` directly and not rdi.sln. The solutions are v110 (2013 pin) and
v120 (dismantl). Retargeting by ``/p:PlatformToolset=v143`` is a command-line
flag and was the first idea, but the projects set ``RuntimeLibrary
MultiThreaded`` and ``WholeProgramOptimization true`` as ItemDefinitionGroup
metadata, which a global MSBuild property does not override, and both are
against the corpus mandates (``/MD``; no ``/GL``). So ``cl`` and ``link`` are
driven by hand with the Release settings read out of the two ``.vcxproj``
files:

  2013 pin, reflective_dll: MaxSpeed (/O2), OnlyExplicitInline (/Ob1),
    IntrinsicFunctions (/Oi), FunctionLevelLinking (/Gy), /W3, defines
    NDEBUG;_WINDOWS;_USRDLL;REFLECTIVE_DLL_EXPORTS;
    REFLECTIVEDLLINJECTION_VIA_LOADREMOTELIBRARYR;
    REFLECTIVEDLLINJECTION_CUSTOM_DLLMAIN plus WIN32;WIN_X86 or
    WIN64;WIN_X64. On x64 the project additionally sets CompileAsCpp (/TP) and
    FavorSizeOrSpeed Size (/Os); both are reproduced. /Ob1 is the setting the
    ``caller()`` comment in ReflectiveLoader.c asks for ("compiled with /O2 and
    /Ob1"), and ``caller`` is also ``__declspec(noinline)``.
  2013 pin, inject: MaxSpeed with the default /Ob2, /Oi, /Gy, defines
    NDEBUG;_CONSOLE plus the same architecture pair.
  dismantl, both: MaxSpeed, /Oi, /Gy, NDEBUG; WIN32;_WINDOWS;_USRDLL;
    REFLECTIVE_DLL_EXPORTS (dll) or WIN32;_CONSOLE (inject), plus WIN_X86 /
    WIN_X64; inject on x64 sets BufferSecurityCheck false (/GS-).

Deviations, all from the corpus mandates: /MD for upstream's /MT, no /GL
(the 2013 x86 projects and dismantl set WPO), and at link /DEBUG /Brepro
/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF where upstream has /OPT:REF /OPT:ICF.
The per-architecture compiler switches go through a response file written by
a python step, because a define such as WIN_X86 is upper-case and cmd.exe
cannot fold {arch}; the style is lzo_msvc.py's.

The reflective DLL is a DLL with no .def: the single DLLEXPORT function is
exported by ``__declspec(dllexport)``. With /TP on x64 (2013 pin) that export
is a C++ decorated name; GetReflectiveLoaderOffset finds it with ``strstr``
for "ReflectiveLoader", so it works either way.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


def _rsp(name, x86, x64):
    """python -c line writing a per-architecture cl response file."""
    return ('python -c "open(\'%s\',\'w\').write(\'%s\' if \'{arch}\'==\'x86\' '
            'else \'%s\')"' % (name, x86, x64))


def _rdi_msvc(version, upstream, git_url, git_ref, dll_sources, dll_x86,
              dll_x64, inj_x86, inj_x64, dll_inline, notes):
    return Recipe(
        family="ReflectiveDLLInjection",
        version=version,
        upstream=upstream,
        license="BSD-3-Clause",
        source=Source(git_url=git_url, git_ref=git_ref),
        build=[
            BuildStep("mkdir dllobj injobj"),
            BuildStep(_rsp("dll.rsp", dll_x86, dll_x64)),
            BuildStep(_rsp("inj.rsp", inj_x86, inj_x64)),
            BuildStep("cl /nologo /c /O2 %s /Oi /Gy /MD /Zi /W3 /Fdvc_dll.pdb "
                      "/Fodllobj\\ @dll.rsp %s" % (dll_inline, dll_sources)),
            BuildStep("link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO "
                      "/OPT:NOREF /OPT:NOICF /PDB:reflective_dll.pdb "
                      "/OUT:reflective_dll.dll dllobj\\*.obj user32.lib"),
            BuildStep("cl /nologo /c /O2 /Oi /Gy /MD /Zi /W3 /Fdvc_inj.pdb "
                      "/Foinjobj\\ /D_CRT_SECURE_NO_WARNINGS @inj.rsp "
                      "inject\\src\\*.c"),
            BuildStep("link /nologo /DEBUG /Brepro /INCREMENTAL:NO "
                      "/OPT:NOREF /OPT:NOICF /PDB:inject.pdb /OUT:inject.exe "
                      "injobj\\*.obj advapi32.lib"),
            BuildStep("dir", allow_failure=True),
        ],
        artifacts=[
            Artifact(path="reflective_dll.dll", component="reflective_dll.dll",
                     pdb="reflective_dll.pdb"),
            Artifact(path="inject.exe", component="inject.exe", pdb="inject.pdb"),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        min_functions=3,
        build_flags="cl /O2 %s /Oi /Gy /MD /Zi /W3 (upstream Release settings "
                    "read from the .vcxproj; /MD and no /GL are the corpus's); "
                    "/DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at "
                    "link" % dll_inline,
        notes=notes,
    )


_X86_DLL = ("/DWIN32 /DNDEBUG /D_WINDOWS /D_USRDLL /DWIN_X86 "
            "/DREFLECTIVE_DLL_EXPORTS "
            "/DREFLECTIVEDLLINJECTION_VIA_LOADREMOTELIBRARYR "
            "/DREFLECTIVEDLLINJECTION_CUSTOM_DLLMAIN")
_X64_DLL = ("/DWIN64 /DNDEBUG /D_WINDOWS /D_USRDLL /DWIN_X64 "
            "/DREFLECTIVE_DLL_EXPORTS "
            "/DREFLECTIVEDLLINJECTION_VIA_LOADREMOTELIBRARYR "
            "/DREFLECTIVEDLLINJECTION_CUSTOM_DLLMAIN /TP /Os")

RECIPES = {
    "ReflectiveDLLInjection_2013-09-05_msvc": _rdi_msvc(
        "2013-09-05",
        "https://github.com/stephenfewer/ReflectiveDLLInjection",
        "https://github.com/stephenfewer/ReflectiveDLLInjection.git",
        "178ba2a6a9feee0a9d9757dcaa65168ced588c12",
        "dll\\src\\ReflectiveLoader.c dll\\src\\ReflectiveDll.c",
        _X86_DLL, _X64_DLL,
        "/DWIN32 /DNDEBUG /D_CONSOLE /DWIN_X86",
        "/DWIN64 /DNDEBUG /D_CONSOLE /DWIN_X64",
        "/Ob1",
        "The reflective DLL and the injector from upstream's Release "
        "configuration, compiled with cl directly; the x64 DLL is compiled "
        "as C++ as upstream's project does. Same sources as the MinGW "
        "artefacts, so the _ReturnAddress and Winsock2.h workarounds are not "
        "needed here."),
    "ReflectiveDLLInjection_2016-06-28-dismantl_msvc": _rdi_msvc(
        "2016-06-28-dismantl",
        "https://github.com/dismantl/ImprovedReflectiveDLLInjection",
        "https://github.com/dismantl/ImprovedReflectiveDLLInjection.git",
        "8b1bdbbc3c95174dda1591d66b5882942b527f94",
        "dll\\src\\ReflectiveLoader.c dll\\src\\ReflectiveDll.c "
        "dll\\src\\MyFunction.c",
        "/DWIN32 /DNDEBUG /D_WINDOWS /D_USRDLL /DWIN_X86 "
        "/DREFLECTIVE_DLL_EXPORTS",
        "/DWIN32 /DNDEBUG /D_WINDOWS /D_USRDLL /DWIN_X64 "
        "/DREFLECTIVE_DLL_EXPORTS",
        "/DWIN32 /DNDEBUG /D_CONSOLE /DWIN_X86",
        "/DWIN32 /DNDEBUG /D_CONSOLE /DWIN_X64 /GS-",
        "",
        "dismantl's fork, a different repository from the upstream head, "
        "filed under the same family. Release settings from its "
        "vcxproj files, which define WIN32 on both platforms."),
}
