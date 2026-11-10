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

Image totals are kept+removed=total: Linux x86 67+7=74 and x64 50+5=55;
MinGW x86 36+114=150 and x64 48+108=156; MSVC x86 87+44=131 and x64 88+50=138.
Functions with >=10 instructions / distinct PicHashes: Linux x86 38/38, x64
29/29; MinGW x86 33/33, x64 26/26; MSVC x86 61/58, x64 54/51. The only
cross-build overlap at this floor is Linux/MinGW x86: three shared hashes
(35 Linux-only and 30 MinGW-only), ``hashx_siphash_rng_init`` (12052320502482513257),
``build_solution`` (12171589145970997990), and ``build_solution_stage2``
(2163312168133937849). All other compiler and architecture pairs, including
MSVC, share no hashes.

GCC x86 startup glue survives with these names and PicHashes: ``_init``
1190297631016324560, ``deregister_tm_clones`` 1854011519951462340,
``register_tm_clones`` 12965823927437490162, and
``__do_global_dtors_aux`` 2827890300630113428.

The MSVC ``printf`` wrapper (PicHash 14739679411554417350 on x86 and
121597203084696572 on x64) is removed by the glue baseline once its stdio
probes cover it; ``vprintf`` and ``__scrt_common_main_seh`` do not appear in
either image.
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
             "explicit vcruntime.lib, ucrt.lib and kernel32.lib at link" if flavor == "msvc" else
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


# The final sweep: the pins of the tracker issue (r0ny123/mcrit-data#49).
#
# * tevador/equix with its HashX submodule at bba97f9: upstream's own tree,
#   at fb00f156a6020675f2fbc43fb108261df8ff6a47 (the newest commit, "deprecation
#   note"; every commit from c0b0d2b on carries hashx bba97f9cbfee). Upstream's
#   CMakeLists.txt also builds with HASHX_SIZE=8, so the defines are the
#   same; the code is not: 28 of the .c/.h files differ from Tor's vendored
#   copy (equix.c's solution check, for one, uses & where Tor uses &&).
# * Tor commit 8dbbbe6e86a6ca0d058ec3c6a4e937859857d7bb (main, 2026-10-07,
#   0.5.0.0-alpha-dev): its src/ext/equix C and header files are byte for
#   byte the ones of tor-0.4.8.25 (checked with cmp; the git tree only adds
#   CMake/Cargo files, tests and benchmarks), so a build of it would be the
#   images above again. It is recorded, not built.
_TEVADOR_REF = "fb00f156a6020675f2fbc43fb108261df8ff6a47"


def _tevador(flavor, toolchains):
    recipe = _recipe(flavor, toolchains)
    recipe.version = "tevador-fb00f15"
    recipe.source = Source(git_url="https://github.com/tevador/equix.git",
                           git_ref=_TEVADOR_REF)
    recipe.build = [BuildStep(recipe.build[0].command + " --root .")]
    recipe.notes = ("Compiled from upstream tevador/equix at fb00f156 with the "
                    "HashX submodule at bba97f9 (the pins of the tracker "
                    "issue), the same 14 translation units and HASHX_SIZE=8 as "
                    "upstream's CMakeLists.txt and Tor use; upstream source is "
                    "unchanged."
                    + (" MSVC's intrinsics header is force-included with "
                       "corrected architecture-test macros for program_exec.c."
                       if flavor == "msvc" else ""))
    return recipe


RECIPES.update({
    "EquiX_tevador-fb00f15_linux": _tevador("linux", ["linux_x86", "linux_x64"]),
    "EquiX_tevador-fb00f15_mingw": _tevador("mingw", ["mingw_x86", "mingw_x64"]),
    "EquiX_tevador-fb00f15_msvc": _tevador("msvc", ["msvc_x86", "msvc_x64"]),
})

