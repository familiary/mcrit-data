"""Equi-X and its HashX engine as vendored by Tor 0.4.8.25.

The 14 C translation units are the exact lists in Tor's ``src/ext/include.am``:
11 HashX units and 3 Equi-X units. Tor's configuration uses ``HASHX_SIZE=8``
and marks both libraries static; this standalone image keeps those consumer
settings rather than building the upstream default 32-byte HashX variant.
The source archive also pins the exact vendored HashX snapshot used by Tor.

The family is kept separate from Tor because the Tor client configuration
does not link the GPL-gated PoW service module; ``nm`` on the client image has
no Equi-X or HashX symbols. This yields the candidate's ~73 functions without
duplicating them under the Tor family.

Local measurements (>=10 instructions / distinct PicHashes): Linux x86 38/38,
x64 29/29; MinGW x86 33/33, x64 26/26. The x86 Linux/MinGW builds share three
hashes (35 and 30 unique); x64 and cross-architecture pairs share none. The
shared x86 functions are ``hashx_siphash_rng_init`` (PicHash
12052320502482513257), ``build_solution`` (12171589145970997990), and
``build_solution_stage2`` (2163312168133937849).

GCC x86 startup glue survives with these names and PicHashes: ``_init``
1190297631016324560, ``deregister_tm_clones`` 1854011519951462340,
``register_tm_clones`` 12965823927437490162, and
``__do_global_dtors_aux`` 2827890300630113428.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_VERSION = "tor-0.4.8.25"
_URL = "https://dist.torproject.org/tor-0.4.8.25.tar.gz"
_SHA256 = "371cd22178fa4b35e64b03933403890795ce3e304c5850a5b59adcc68820a799"
_SOURCE = Source(url=_URL, sha256=_SHA256)
_UPSTREAM = "https://github.com/tevador/equix"


def _recipe(flavor, toolchains):
    extension = "dll" if flavor in ("mingw", "msvc") else "so"
    command = (
        "python {repo}/scripts/corpus/exercisers/equix_build.py "
        "--flavor %s --arch {arch} --bitness {bitness} --cc {cc}"
        % flavor
    )
    artifact_args = {
        "path": "build_equix/equix-hashx-{arch}.%s" % extension,
        "component": "equix-hashx.%s" % extension,
    }
    if flavor == "msvc":
        artifact_args["pdb"] = "build_equix/equix-hashx-{arch}.pdb"
    flags = ("/O2 /MD /Zi /GL-; /DLL /NOENTRY /DEBUG /OPT:NOREF "
             "/OPT:NOICF /Brepro /INCREMENTAL:NO; program_exec.c uses a "
             "forced include to normalize its MSVC architecture checks; "
             "explicit ucrt.lib and kernel32.lib at link" if flavor == "msvc" else
             "-O2 -g -fPIC -std=gnu11; HASHX_SIZE=8; "
             "EQUIX_STATIC=1; HASHX_STATIC=1")
    if flavor == "mingw":
        flags += "; shared PE without inserted timestamp"
    return Recipe(
        family="EquiX",
        version=_VERSION,
        upstream=_UPSTREAM,
        license="See upstream source",
        source=_SOURCE,
        build=[BuildStep(command)],
        artifacts=[Artifact(**artifact_args)],
        toolchains=toolchains,
        build_flags=flags,
        notes=("Compiled from Tor 0.4.8.25's vendored HashX and Equi-X C "
               "sources with the consumer's eight-byte HashX output size. "
               "Only the C translation units in src/ext/include.am are "
               "included; upstream source is unchanged. MSVC's intrinsics "
               "header is force-included with corrected architecture-test "
               "macros for program_exec.c, avoiding its x64 parse error "
               "without changing the source."),
    )


RECIPES = {
    "EquiX_tor-0.4.8.25_linux": _recipe(
        "linux", ["linux_x86", "linux_x64"]),
    "EquiX_tor-0.4.8.25_mingw": _recipe(
        "mingw", ["mingw_x86", "mingw_x64"]),
    "EquiX_tor-0.4.8.25_msvc": _recipe(
        "msvc", ["msvc_x86", "msvc_x64"]),
}
