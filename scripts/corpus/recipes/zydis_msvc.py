"""Zydis and Zycore built with MSVC (placeholder)."""

from ..recipe import Artifact, BuildStep, Recipe, Source

_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Z7"'
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
          '-DZYDIS_BUILD_EXAMPLES=OFF -DZYDIS_BUILD_TOOLS=OFF %s ' % _CFLAGS)
_ANCHOR_SRC = ('python -c "'
               "open('anchor.c','w').write("
               "'int zydis_msvc_anchor(void){return 0;}')"
               '"')
_ANCHOR = "cl /nologo /c /O2 /MD /Z7 /Foanchor.obj anchor.c"
_LINK = ('link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO '
         '/OPT:NOREF /OPT:NOICF '
         '/WHOLEARCHIVE:build-{arch}\\Zydis.lib '
         '/WHOLEARCHIVE:build-{arch}\\zycore\\Zycore.lib '
         '/PDB:zydis.pdb /OUT:zydis.dll anchor.obj kernel32.lib')


def _zydis(version, tag, extra=""):
    return Recipe(
        family="Zydis",
        version=version,
        upstream="https://github.com/zyantific/zydis",
        license="MIT",
        source=Source(git_url="https://github.com/zyantific/zydis.git",
                      git_ref=tag),
        build=[BuildStep(_CMAKE + extra),
               BuildStep("cmake --build build-{arch}"),
               BuildStep(_ANCHOR_SRC),
               BuildStep(_ANCHOR),
               BuildStep(_LINK),
               BuildStep("dir build-{arch} build-{arch}\\zycore", allow_failure=True)],
        artifacts=[Artifact(path="zydis.dll", component="zydis.dll",
                            pdb="zydis.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /Z7",
        notes="Placeholder.",
    )


RECIPES = {
    "Zydis_3.1.0_msvc": _zydis("3.1.0", "v3.1.0"),
    "Zydis_4.1.1_msvc": _zydis("4.1.1", "v4.1.1"),
    "Zydis_3.1.0-nolibc_msvc": _zydis("3.1.0-nolibc", "v3.1.0",
                                      "-DZYAN_NO_LIBC=ON"),
}
