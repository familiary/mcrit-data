"""Current and legacy Andrivet ADVobfuscator header-only implementations.

The two source snapshots use the same family with distinct versions: current
upstream (2026-10-27) and the 2020-06-26 legacy layout. Both use the same
16-literal harness. Current is built at O0 because the x64 GCC probe retains
154 library functions / 32 PicHashes at >=10 instructions with no plaintext
hits; O2 retained 30 / 16. Legacy uses O2 plus no-inline because O0 exposes
the test literals in plaintext, while O2 alone removes its meaningful code.

The final current images retain 506 Linux x64 functions (5 removed; 172
functions / 47 distinct PicHashes at >=10 instructions), 765 Linux x86 (4
removed; 239/231), 616 MSVC x64 (140 removed; 323/60) and 616 MSVC x86 (134
removed; 402/66). Legacy retains 82 Linux x64 (6 removed; 27/18), 134 Linux
x86 (3 removed; 38/33), 61 MinGW x64 (48 removed; 20/20), 53 MinGW x86 (48
removed; 25/20), 88 MSVC x64 (133 removed; 54/42) and 88 MSVC x86 (127
removed; 40/35). Kept + removed equals the image total in every case. Current
MinGW x86 and x64 both fail with the upstream C++20
``operator""_obf_bytes`` deduction error recorded in the corpus README.

Among all built pairs, only legacy Linux/MinGW x86 share a >=10-instruction
PicHash: 3682465956104202752 (32 Linux-only and 19 MinGW-only hashes). Every
other compiler, architecture and version pair shares none, including current
versus legacy.

GCC x86 startup glue survives with these names and PicHashes. Current:
``_init`` 1007249484536421600, ``deregister_tm_clones`` 569991583881770807,
``register_tm_clones`` 10179453566455001527,
``__do_global_dtors_aux`` 7774818233878611077. Legacy:
``_init`` 16794956033002673114, ``deregister_tm_clones`` 4180412564719701528,
``register_tm_clones`` 5327937504806600116,
``__do_global_dtors_aux`` 12336397557569579703.

The current Linux images also retain ``std::exception::exception()`` at
PicHash 10659546382074989998 on x86 and 17836628882983317004 on x64.

Current MSVC retains these standard-library bodies at >=10 instructions. Both
``std::_Copy_unchecked`` specializations share PicHash 13776350814747620045 on
x86 and 9522421698474240033 on x64. The x86 ``std::exception`` scalar
deleting destructor, constructors, ``what`` and destructor have PicHashes
7409008809337139281, 8642803295137383776, 13625354785570543773,
7933004270128200859 and 17187247443211744792; the matching x64 bodies have
3015519046245316070, 82704443616455984, 3643287694256856300,
15342726656191981861 and 1780326638724384347. No ``printf``/``vprintf``
wrapper or ``__scrt_common_main_seh`` appears in these MSVC images.
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
