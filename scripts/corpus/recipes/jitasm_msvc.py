"""jitasm built with MSVC (placeholder)."""

from ..recipe import Artifact, BuildStep, Recipe, Source

_COMPILE = ("cl /nologo /c /O2 /MD /Zi /EHsc /bigobj /I. "
            "/Fdjitasm.compiler.pdb /Fojitasm.obj "
            "{repo}/scripts/corpus/exercisers/jitasm.cpp")
_LINK = ("link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF "
         "/OPT:NOICF /PDB:jitasm.pdb /OUT:jitasm.dll jitasm.obj kernel32.lib")

RECIPES = {
    "jitasm_2018-11-24_msvc": Recipe(
        family="jitasm",
        version="2018-11-24",
        upstream="https://github.com/hikaru-i/jitasm",
        license="New BSD",
        source=Source(git_url="https://github.com/hikaru-i/jitasm.git",
                      git_ref="7cb9d72982c793374c49b804bec842deb1506d92"),
        build=[BuildStep(_COMPILE), BuildStep(_LINK)],
        artifacts=[Artifact(path="jitasm.dll", component="jitasm.dll",
                            pdb="jitasm.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi /EHsc /bigobj",
        notes="Placeholder.",
    ),
}
