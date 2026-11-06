"""Standalone BLAKE2 reference and SSE2 implementations, all six variants.

The reference images compile the upstream ``ref/`` C units at the Makefile's
``-O2``; SSE images compile the separate upstream ``sse/`` units at ``-O3``.
Both preserve blake2b/s, bp/sp, and xb/xs implementations. The source pin is
2023-02-12 (ed1974ea83433eba7b2d95c5dcd9ac33cb847913). Existing libsodium
images already contain vendored BLAKE2b reference code; the standalone family
adds both BLAKE2b and BLAKE2s variants, including parallel and extended-output
implementations. The libsodium provenance records that vendored component.

Local measurements are functions with >=10 instructions / distinct PicHashes:
ref Linux x86 43/43, x64 34/34; ref MinGW x86 39/38, x64 37/37; SSE Linux x86
39/39, x64 30/30; SSE MinGW x86 36/35, x64 36/35. Ref versus SSE shares 12
hashes on Linux x64, 8 on MinGW x64, 2 on MinGW x86 and none on Linux x86.
Same-mode Linux/MinGW and cross-architecture pairs share no hashes.

The only standalone-to-libsodium >=10-instruction matches are unnamed hashes
12578432865501340970 on x64 MinGW and 16132965489037543538 on x86 MinGW; each
appears in both libsodium versions and both standalone modes. Deep validation
classifies them as no-symbol matches, with no named cross-family leakage.

GCC x86 startup glue survives with these names and PicHashes. Ref:
``_init`` 9608256718953870546, ``deregister_tm_clones`` 2780497305776452871,
``register_tm_clones`` 12755717022944402199,
``__do_global_dtors_aux`` 4810785454881136303. SSE:
``_init`` 15718644553860916983, ``deregister_tm_clones`` 8718169112306472195,
``register_tm_clones`` 12945903060382388116,
``__do_global_dtors_aux`` 17331431794667355242.
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
                 "/OPT:NOICF /Brepro /INCREMENTAL:NO; explicit ucrt.lib " \
                 "and kernel32.lib at link"
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
