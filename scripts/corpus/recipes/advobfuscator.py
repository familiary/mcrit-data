"""Current and legacy Andrivet ADVobfuscator header-only implementations.

The two source snapshots use the same family with distinct versions: current
upstream (2026-10-27) and the 2020-06-26 legacy layout. Both use the same
16-literal harness. Current is built at O0 because the x64 GCC probe retains
154 library functions / 32 PicHashes at >=10 instructions with no plaintext
hits; O2 retained 30 / 16. Legacy uses O2 plus no-inline because O0 exposes
the test literals in plaintext, while O2 alone removes its meaningful code.

The current O0 Linux x64 probe has 154 library functions / 32 PicHashes at >=10
instructions; the legacy O2/no-inline probe has 13 / 13. Both contain no
plaintext test literals. MinGW and MSVC measurements are added after their
pipeline builds. Named glue survivors are recorded with their PicHashes below
once the reference images are final.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_UPSTREAM = "https://github.com/andrivet/ADVobfuscator"
_SOURCES = {
    "current": Source(
        git_url="https://github.com/andrivet/ADVobfuscator.git",
        git_ref="9058623d0caf1fdf784d16e7f9233d29a5993acb",
    ),
    "legacy": Source(
        git_url="https://github.com/andrivet/ADVobfuscator.git",
        git_ref="1852a0eb75b03ab3139af7f938dfb617c292c600",
    ),
}


def _recipe(mode, flavor, toolchains):
    version = "2020-06-26" if mode == "legacy" else "2026-10-27"
    extension = "dll" if flavor in ("mingw", "msvc") else "so"
    command = (
        "python {repo}/scripts/corpus/exercisers/advobfuscator_build.py "
        "--mode %s --flavor %s --arch {arch} --bitness {bitness} "
        "--cxx {cxx} --repo {repo}"
        % (mode, flavor)
    )
    artifact_args = {
        "path": "build/advobfuscator-%s-{arch}.%s" % (mode, extension),
        "component": "advobfuscator-%s.%s" % (mode, extension),
    }
    if flavor == "msvc":
        artifact_args["pdb"] = "build/advobfuscator-%s-{arch}.pdb" % mode
    opt_flags = ("/Od /Ob0" if mode == "current" else "/O2 /Ob0")
    gcc_opt_flags = ("-O0" if mode == "current" else "-O2 -fno-inline")
    flags = (opt_flags + " /MD /Zi /GL-; /DLL /DEBUG /OPT:NOREF /OPT:NOICF "
             "/Brepro /INCREMENTAL:NO" if flavor == "msvc" else
             gcc_opt_flags + (" -std=c++20" if mode == "current" else
                              " -std=c++14"))
    if flavor == "linux":
        flags += "; -fPIC -shared"
    elif flavor == "mingw":
        flags += "; -shared; no inserted PE timestamp"
    return Recipe(
        family="ADVobfuscator",
        version=version,
        upstream=_UPSTREAM,
        license="See upstream source",
        source=_SOURCES[mode],
        build=[BuildStep(command)],
        artifacts=[Artifact(**artifact_args)],
        toolchains=toolchains,
        build_flags=flags,
        notes=("Header-only string obfuscation code instantiated through a "
               "16-literal corpus harness. The harness consumes every "
               "decoded string, and upstream sources are unchanged. "
               "Current uses C++20; legacy uses C++14 and disables inlining "
               "to retain meaningful template bodies."),
    )


RECIPES = {}
for _mode in ("current", "legacy"):
    RECIPES["ADVobfuscator_%s_linux" % _mode] = _recipe(
        _mode, "linux", ["linux_x86", "linux_x64"])
    RECIPES["ADVobfuscator_%s_msvc" % _mode] = _recipe(
        _mode, "msvc", ["msvc_x86", "msvc_x64"])
    if _mode == "legacy":
        RECIPES["ADVobfuscator_legacy_mingw"] = _recipe(
            _mode, "mingw", ["mingw_x86", "mingw_x64"])
