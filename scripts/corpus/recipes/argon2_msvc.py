"""Argon2 built with MSVC, beside the MinGW build of the same tag.

PLACEHOLDER_DOC
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# The six translation units of upstream's own Argon2OptDll project
# (vs2015/Argon2OptDll/Argon2OptDll.vcxproj ClCompile list), in one cl
# invocation so /Fd names the single compiler PDB the linker turns into
# libargon2.pdb.
_SOURCES = ("src\\argon2.c src\\core.c src\\blake2\\blake2b.c src\\thread.c "
            "src\\encoding.c src\\opt.c")

# /O2 /Oi /Gy /sdl are the project's Release settings (MaxSpeed,
# IntrinsicFunctions, FunctionLevelLinking, SDLCheck), /MD replaces the cl
# default /MT, /Zi is for the PDB. -I include because the sources use
# "argon2.h". /LD builds a DLL; ARGON2_PUBLIC is __declspec(dllexport) under
# _MSC_VER, so no .def file is needed.
_BUILD = ('cl /nologo /LD /O2 /Oi /Gy /sdl /MD /Zi /Iinclude '
          '/D_CRT_SECURE_NO_WARNINGS /Fdlibargon2.pdb /Felibargon2.dll '
          + _SOURCES +
          ' /link /INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF')


RECIPES = {
    "argon2_20190702_msvc": Recipe(
        family="argon2",
        version="20190702",
        upstream="https://github.com/P-H-C/phc-winner-argon2",
        license="CC0-1.0 OR Apache-2.0",
        source=Source(git_url="https://github.com/P-H-C/phc-winner-argon2.git",
                      git_ref="20190702"),
        build=[
            BuildStep(_BUILD),
            BuildStep("dir", allow_failure=True),
        ],
        artifacts=[Artifact(path="libargon2.dll", component="libargon2.dll",
                            pdb="libargon2.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /Oi /Gy /sdl /MD /Zi (the vs2015 Release project's "
                    "settings), src/opt.c; /DEBUG /Brepro /OPT:NOREF "
                    "/OPT:NOICF at link",
        notes="Same tag as the MinGW recipe, opt.c, SSE2 baseline. See the "
              "recipe docstring.",
    ),
}
