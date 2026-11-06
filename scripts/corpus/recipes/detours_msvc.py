"""Detours built with MSVC (placeholder)."""

from ..recipe import Artifact, BuildStep, Recipe, Source

_OBJS = "detours modules disasm image creatwth disolx86 disolx64".split()

_COMPILE = ("cl /nologo /c /O2 /MD /Zi /Gy /Gm- /DWIN32_LEAN_AND_MEAN "
            "/D_WIN32_WINNT=0x501 /DDETOUR_DEBUG=0 /Fddetours.compiler.pdb "
            + " ".join("src\\%s.cpp" % o for o in _OBJS))
_LINK = ("link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF "
         "/OPT:NOICF /PDB:detours.pdb /OUT:detours.dll "
         + " ".join(o + ".obj" for o in _OBJS) + " kernel32.lib")

_NMAKE = "nmake /nologo"
_LINK_NMAKE = ("link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF "
               "/OPT:NOICF /PDB:detours.pdb /OUT:detours.dll "
               + " ".join("src\\obj.{arch}\\%s.obj" % o for o in _OBJS)
               + " msvcrt.lib vcruntime.lib ucrt.lib kernel32.lib")


def _direct(version, ref):
    return Recipe(
        family="Detours", version=version,
        upstream="https://github.com/microsoft/Detours",
        license="MIT",
        source=Source(git_url="https://github.com/microsoft/Detours.git",
                      git_ref=ref),
        build=[BuildStep(_COMPILE), BuildStep(_LINK)],
        artifacts=[Artifact(path="detours.dll", component="detours.dll",
                            pdb="detours.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi /Gy", notes="Placeholder.")


def _nmake(version, ref):
    return Recipe(
        family="Detours", version=version,
        upstream="https://github.com/microsoft/Detours",
        license="MIT",
        source=Source(git_url="https://github.com/microsoft/Detours.git",
                      git_ref=ref),
        build=[BuildStep(_NMAKE, cwd="src"),
               BuildStep("dir src\\obj.{arch}", allow_failure=True),
               BuildStep(_LINK_NMAKE)],
        artifacts=[Artifact(path="detours.dll", component="detours.dll",
                            pdb="detours.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="upstream Makefile: /Od /MT /Zl /Zi /Gy", notes="Placeholder.")


RECIPES = {
    "Detours_2026-09-29_msvc": _direct(
        "2026-09-29", "1dbd4ea281d73d478aa8d09a8b83fbd265f715f7"),
    "Detours_2026-09-29-nmake_msvc": _nmake(
        "2026-09-29-nmake", "1dbd4ea281d73d478aa8d09a8b83fbd265f715f7"),
    "Detours_4.0.1_msvc": _direct("4.0.1", "v4.0.1"),
}
