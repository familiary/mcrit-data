"""Standalone BLAKE2 reference and SSE2 implementations, all six variants.

The reference images compile the upstream ``ref/`` C units at the Makefile's
``-O2``; SSE images compile the separate upstream ``sse/`` units at ``-O3``.
Both preserve blake2b/s, bp/sp, and xb/xs implementations. The source pin is
2023-02-12 (ed1974ea83433eba7b2d95c5dcd9ac33cb847913). Existing libsodium
images already contain vendored BLAKE2b reference code; the standalone family
adds both BLAKE2b and BLAKE2s variants, including parallel and extended-output
implementations. The libsodium provenance records that vendored component.

Image totals are kept+removed=total. Ref: Linux x86 84+4=88, x64 60+6=66;
MinGW x86 42+50=92, x64 51+50=101; MSVC x86 73+35=108, x64 73+42=115. SSE:
Linux x86 80+6=86, x64 56+6=62; MinGW x86 38+50=88, x64 47+50=97; MSVC
x86 65+33=98, x64 65+42=107. The >=10-instruction functions / distinct
PicHashes are ref Linux x86 43/43, x64 34/34; MinGW x86 39/38, x64 37/37;
MSVC x86 51/45, x64 48/42. SSE Linux x86 39/39, x64 30/30; MinGW x86
36/35, x64 36/35; MSVC x86 45/41, x64 44/40.

At >=10 instructions, same-mode compiler pairs and cross-architecture pairs
share no hashes. Ref and SSE share hashes only within the same compiler and
architecture: Linux x64 12 (7479948891773896, 774461400286523667,
1683696317792702654, 1901333545194469325, 2106746542878578048,
2349569511763554200, 4448995478728049293, 5455402598862610226,
7115606618437008181, 14563878380153991857, 15331828404104534565,
15921859942079019047); MinGW x64 8 (3556785065081902843,
5739552467248598519, 9450931321098931376, 9478816987967410945,
11584176000006817668, 12166371338578747292, 12578432865501340970,
15646045006596362182); MSVC x64 20 (118463790781745593,
547918697158847784, 1516431085176943436, 2212372368648581401,
3090874284623527783, 3874557155317778465, 4952747726359933088,
6960042812382538783, 7332111378155661114, 8370392326124424275,
9314391816016409926, 9641080310167576344, 10643723651866569594,
11301195446031154368, 12133541295216415095, 12983274252010201048,
13807917860078595852, 15500094043754507584, 16776724936884294483,
18278085964489742151); MinGW x86 2 (274526237593242699,
16132965489037543538); MSVC x86 24 (19633694071432095,
991646560602557278, 1499835908946858364, 4010518019989291916,
4244772927363081496, 4497823313262644679, 5821709760240491124,
6859513794479955516, 8115236169317852973, 8158389882812112409,
9268665388221597996, 9295598395589078137, 11690363780039051853,
11926128978286997153, 12198495588762217161, 12456790168485175588,
13339877390089225172, 14429746693063561578, 15218678102026541512,
15329288195236732195, 16039635771174741053, 16758156269861299646,
17376249699674122376, 18078040131870129228). The shared MinGW x86 hashes
are named ``_blake2s`` (274526237593242699) and one unnamed function; the
other listed matches have the same named BLAKE2 functions on both sides.

The only standalone-to-libsodium >=10-instruction matches are unnamed hashes
12578432865501340970 on x64 MinGW and 16132965489037543538 on x86 MinGW; each
appears in both libsodium versions and both standalone modes. Deep validation
classifies them as no-symbol matches, with no named cross-family leakage.

No MSVC image retains a ``printf``/``vprintf`` wrapper or
``__scrt_common_main_seh``.

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
                 "/OPT:NOICF /Brepro /INCREMENTAL:NO; explicit vcruntime.lib, " \
                 "ucrt.lib and kernel32.lib at link"
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
