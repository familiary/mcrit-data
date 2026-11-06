"""MIRACL's complete C library from the pinned 2019-08-21 source tree.

The upstream linux, mingw and MSVC command files define the library's C
translation units. The build helper compiles those same units out of tree,
selecting MIRACL's architecture-specific ``mirdef.h`` and ``mrmuldv.c``
variants through a build-only include directory. It does not modify upstream
files or compile the C++ examples.

Local reference measurements, functions >=10 instructions (SMDA 5.0.2,
MCRIT 1.16.0):
  Linux x86 1004+11=1015 total, 455 functions/451 PicHashes; Linux x64
  731+5=736, 427/421.
  MinGW x86 466+70=536, 452/445; MinGW x64 471+67=538, 438/431.
  Linux x86 versus MinGW x86 shares 26 hashes; every other architecture or
  compiler pair shares 0. The separate axes retain hundreds of unique hashes.
  Named C runtime glue survivors are recorded after the corpus builds.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_SOURCE = Source(
    git_url="https://github.com/miracl/MIRACL.git",
    git_ref="b9b8fd471de253cfd6313446cb490741edb069a7",
)
_UPSTREAM = "https://github.com/miracl/MIRACL"


def _recipe(flavor, toolchains, extension, flags):
    command = (
        "python {repo}/scripts/corpus/exercisers/miracl_build.py "
        "--flavor %s --arch {arch} --bitness {bitness} --cc {cc}" % flavor
    )
    artifact_args = {
        "path": "build_miracl/miracl-{arch}.%s" % extension,
        "component": "libmiracl.%s" % extension,
    }
    if flavor == "msvc":
        artifact_args["pdb"] = "build_miracl/miracl-{arch}.pdb"
    return Recipe(
        family="MIRACL",
        version="2019-08-21",
        upstream=_UPSTREAM,
        license="See upstream source",
        source=_SOURCE,
        build=[BuildStep(command)],
        artifacts=[Artifact(**artifact_args)],
        toolchains=toolchains,
        build_flags=flags,
        notes=("The complete upstream C library translation-unit set, built "
               "as a shared image from the upstream Linux/MinGW/MSVC command "
               "lists. Architecture configuration and mul/div code are copied "
               "to build_miracl only; upstream source is unchanged. C++ "
               "examples are excluded."),
    )


RECIPES = {
    "MIRACL_2019-08-21_linux": _recipe(
        "linux", ["linux_x86", "linux_x64"], "so",
        "-O2 -g -fPIC -fvisibility=hidden; upstream lib/linux and lib/linux64 "
        "source lists"),
    "MIRACL_2019-08-21_mingw": _recipe(
        "mingw", ["mingw_x86", "mingw_x64"], "dll",
        "-O2 -g; upstream lib/mingw.bat C units; no inserted PE timestamp; "
        "x86 uses mirdef.lnx/mrmuldv.gcc and x64 uses mirdef.mgw/mrmuldv.g64"),
    "MIRACL_2019-08-21_msvc": _recipe(
        "msvc", ["msvc_x86", "msvc_x64"], "dll",
        "/O2 /MD /Zi /GL-; /DLL /NOENTRY /DEBUG /OPT:NOREF /OPT:NOICF "
        "/Brepro /INCREMENTAL:NO; upstream MSVC C units and matching "
        "mirdef/mrmuldv variants"),
}
