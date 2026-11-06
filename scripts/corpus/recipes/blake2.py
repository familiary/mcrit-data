"""Standalone BLAKE2 reference and SSE2 implementations, all six variants.

The reference images compile the upstream ``ref/`` C units at the Makefile's
``-O2``; SSE images compile the separate upstream ``sse/`` units at ``-O3``.
Both preserve blake2b/s, bp/sp, and xb/xs implementations. The source pin is
2023-02-12 (ed1974ea83433eba7b2d95c5dcd9ac33cb847913). Existing libsodium
images already contain vendored BLAKE2b reference code; the standalone family
adds both BLAKE2b and BLAKE2s variants, including parallel and extended-output
implementations. The libsodium provenance records that vendored component.

Overlap evidence (>=10 instructions, final per-axis values added after builds):
  standalone ref versus SSE on the same compiler/architecture;
  Linux versus MinGW and MSVC for each source variant.
Named glue survivors and their PicHashes are recorded after the images build.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_SOURCE = Source(
    git_url="https://github.com/BLAKE2/BLAKE2.git",
    git_ref="ed1974ea83433eba7b2d95c5dcd9ac33cb847913",
)
_UPSTREAM = "https://github.com/BLAKE2/BLAKE2"


def _recipe(mode, flavor, toolchains):
    version = "2023-02-12-%s" % mode
    extension = "dll" if flavor in ("mingw", "msvc") else "so"
    command = (
        "python {repo}/scripts/corpus/exercisers/blake2_build.py "
        "--mode %s --flavor %s --arch {arch} --bitness {bitness} --cc {cc}"
        % (mode, flavor)
    )
    artifact_args = {
        "path": "build/blake2-%s-{arch}.%s" % (mode, extension),
        "component": "blake2-%s.%s" % (mode, extension),
    }
    if flavor == "msvc":
        artifact_args["pdb"] = "build/blake2-%s-{arch}.pdb" % mode
    flags = ("upstream ref/makefile -O2" if mode == "ref" else
             "upstream sse/makefile -O3; SSE2 enabled with compiler flags")
    if flavor == "msvc":
        flags += "; /O2 /MD /Zi /GL-; /DLL /NOENTRY /DEBUG /OPT:NOREF " \
                 "/OPT:NOICF /Brepro /INCREMENTAL:NO"
    elif flavor == "linux":
        flags += "; -g -fPIC -shared"
    else:
        flags += "; -g; -shared; no inserted PE timestamp"
    return Recipe(
        family="BLAKE2",
        version=version,
        upstream=_UPSTREAM,
        license="See upstream source",
        source=_SOURCE,
        build=[BuildStep(command)],
        artifacts=[Artifact(**artifact_args)],
        toolchains=toolchains,
        build_flags=flags,
        notes=("All six upstream %s C translation units are combined into a "
               "single shared image without the self-test mains. "
               "The upstream source tree is unchanged." % mode),
    )


RECIPES = {}
for _mode in ("ref", "sse"):
    RECIPES["BLAKE2_2023-02-12-%s_linux" % _mode] = _recipe(
        _mode, "linux", ["linux_x86", "linux_x64"])
    RECIPES["BLAKE2_2023-02-12-%s_mingw" % _mode] = _recipe(
        _mode, "mingw", ["mingw_x86", "mingw_x64"])
    RECIPES["BLAKE2_2023-02-12-%s_msvc" % _mode] = _recipe(
        _mode, "msvc", ["msvc_x86", "msvc_x64"])
