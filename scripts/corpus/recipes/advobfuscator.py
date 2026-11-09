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
x86 (3 removed; 38/33), 61 MinGW x64 (50 removed; 25/18), 53 MinGW x86 (49
removed; 28/19), 88 MSVC x64 (133 removed; 54/42) and 88 MSVC x86 (127
removed; 40/35). Kept + removed equals the image total in every case.
Current MinGW x64 retains 273 functions (51 removed, 324 total; 227
functions / 61 distinct PicHashes at >=10 instructions) and current MinGW x86
266 (49 removed, 315 total; 201/66); these two are PATCHED builds, described
below.

Current MinGW patch. GCC 13 (C++20, also gnu++20) cannot deduce the class-type
template parameter of the ``_obf`` and ``_obf_bytes`` literal operators from
the string literal: ``no matching function for call to
'operator""_obf_bytes<"63 7C ...">()'`` (aes.h) and, once that is past,
``operator""_obf<"corpus_alpha_01">()``. ``-std=gnu++17``, ``c++17`` and
``c++14`` fail earlier (``'consteval' does not name a type``; the library
needs C++20), and constructing ``ObfuscatedBytes<48>{"..."}`` explicitly
works, so only the literal-operator deduction is at fault.
``advobfuscator_build.py`` therefore compiles a copy of ``include/``
(``build/include-gcc13``, upstream checkout untouched) in which the two
operators take a char-array wrapper and construct the unchanged class::

  bytes.h
  -  template<ObfuscatedBytes block>
  -  consteval auto operator""_obf_bytes() { return block; }
  +  template<std::size_t N> struct ObfBytesLiteral {
  +    constexpr ObfBytesLiteral(const char (&str)[N]) { for(std::size_t i = 0; i < N; ++i) chars[i] = str[i]; }
  +    char chars[N]; };
  +  template<ObfBytesLiteral lit>
  +  consteval auto operator""_obf_bytes() { return ObfuscatedBytes<sizeof(lit.chars)>(lit.chars); }
  string.h
  -  template<ObfuscatedString str>
  -  consteval auto operator ""_obf() { return str; }
  +  template<std::size_t N> struct ObfStringLiteral { (same body) };
  +  template<ObfStringLiteral lit>
  +  consteval auto operator ""_obf() { return ObfuscatedString<sizeof(lit.chars)>(lit.chars); }

These two images are therefore NOT byte-identical to a build of unmodified
upstream (the obfuscation classes and AES tables are unchanged; only the
literal-operator wrappers differ). ``strings -a`` finds none of the 16
harness literals. Surviving libstdc++/libgcc import thunks, all PicHash
1253497258561142223: ``__gxx_personality_seh0``, ``__cxa_throw``,
``__cxa_allocate_exception`` (x64) and ``___gxx_personality_v0``,
``___cxa_throw``, ``___cxa_allocate_exception``, ``std::exception::~exception()``,
``___register_frame_info``, ``___deregister_frame_info`` (x86).

Among all built pairs, the >=10-instruction PicHash overlaps are: legacy
Linux/MinGW x86, 3682465956104202752 (32 Linux-only and 18 MinGW-only
hashes); legacy versus current MinGW, one unnamed 15-instruction function per
architecture (x64 12578432865501340970, x86 16132965489037543538). The
current MinGW images share no PicHash with current Linux, current MSVC or any
other legacy axis; every other pair shares none.

Optimisation level and reproducibility (tracker issue 28). Both snapshots seed
their pseudo-random generator from ``__TIME__`` (``include/advobfuscator/
random.h`` and ``Lib/MetaRandom.h``: hh:mm:ss, seconds included), so an unpinned
build is different from the next one by the key schedule of every literal.
Measured, current at -O0 on Linux x64 built three times: pinned to
1700000000 (22:13:20) twice, byte-identical; pinned to 1700003661 (23:14:21)
or unpinned, 763 functions against 749 and 198 against 186 of ten instructions
or more, with 65 of the 71 PicHashes of the first image shared. The MinGW
images rebuilt with the pin against the unpinned ones they replace: current x64
and x86 keep the same 273 and 266 functions and 227 and 201 at ten instructions
or more, but share 59 of 61 and 64 of 66 distinct PicHashes; legacy x64
changes from 20 to 25 (20 to 18 distinct, 11 shared) and x86 from 25 to 28 (20
to 19 distinct, 12 shared), and its removed count from 48 to 50 and 49. So the
pin is not cosmetic. ``advobfuscator_build.py`` sets ``SOURCE_DATE_EPOCH=
1700000000`` and ``TZ=UTC``, which GCC (7 and later) honours for ``__TIME__``,
and compiles a probe translation unit first: the build fails if the pinned
string 22:13:20 is not in the probe object. The seed value is arbitrary; it was
not chosen for the outcome (legacy -O2 -fno-inline leaves between 3 and 6
literal fragments in plaintext in the MinGW x64 image whichever of seven seeds
was tried, 1 on MinGW x86 in all seven, 1 or 2 on Linux x64).

cl does not honour ``SOURCE_DATE_EPOCH`` and cannot be made to: on the
windows-2022 runner (MSVC 19.44) the probe finds no pinned string, ``/D__TIME__=
"22:13:20"`` gives ``warning C4117: macro name '__TIME__' is reserved,
'#define' ignored`` and a forced-include header with ``#undef __TIME__`` /
``#define __TIME__`` gives the same warning for both directives (run
42683708448, scratch/partials-a3). Pinning cl would need a patch to
``random.h``/``MetaRandom.h``, which was not applied, so the four MSVC images
are NOT reproducible and carry whatever seed their build second gave. The
builder logs ``NOT PINNED`` for cl and goes on. The Linux images were built
before the pin existed (GCC 14, which the current snapshot needs: GCC 13
cannot deduce its literal-operator parameter, see the MinGW patch above) and
are unpinned too; they are reproducible only once rebuilt with this script. So
in the committed corpus only the four MinGW images are pinned.

Optimisation level, measured with GCC 13 (current built from the patched
include copy, so it compiles; seed pinned), counts being kept + removed =
total, then functions of ten instructions or more / distinct PicHashes, and
how many of the 16 harness literals are visible to ``strings -a``:

* current, Linux x64: -O0 749 + 5 = 754, 186/71, 0 literals; -O1 56 + 6 = 62,
  18/18; -O2 69 + 6 = 75, 31/18; -Os 125 + 6 = 131, 49/23 (none shows a
  literal). MinGW x64: -O0 273 + 51 = 324, 227/61; -O1 43 + 51, 30/18; -O2
  39 + 50, 26/17; -Os 66 + 49, 51/26. Linux x86: -O0 758 + 4, 229/229; -O1 72
  + 3, 33/33; -O2 73 + 4, 35/35; -Os 131 + 3, 57/56. Only -O0 keeps the
  AES and string-class machinery as functions; every optimised level folds
  it into 18 to 57 functions. So current stays at -O0 (the choice already
  made on the x64 probe, now confirmed on three targets).
* legacy, no -fno-inline: Linux x64 -O0 150 + 6 = 156, 43/26 with all 16
  literals in plaintext; -O1 6 + 5, 2/2; -O2 5 + 6, 1/1; -Os 6 + 6, 1/1.
  MinGW x64: -O0 61 + 50, 44/27, 16 literals; -O1 13 + 50, 3/3; -O2 12 +
  50, 2/2; -Os 13 + 50, 2/2. Linux x86: -O0 156 + 4, 47/47, 16 literals;
  -O1 12 + 3, 6/6; -O2 11 + 3, 5/5; -Os 12 + 3, 6/6. With -fno-inline (Linux
  x64): -O1 150 + 6, 30/23, no literal; -O2 126 + 6, 24/17, one literal
  fragment; -Os 126 + 6, 17/15, none. -O0 exposes the literals and the
  optimised levels without -fno-inline leave one to six functions, so legacy
  stays at -O2 -fno-inline, which the build flags already say. -O1 -fno-
  inline had more functions (30 against 24) and fewer plaintext fragments
  than -O2 in this measurement and was not adopted: it changes 4 images
  that are already built and the difference is small.

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
    patched = mode == "current" and flavor == "mingw"
    pinned = flavor == "mingw"
    notes = ("Header-only string obfuscation code instantiated through a "
             "16-literal corpus harness. The harness consumes every "
             "decoded string"
             + (", and upstream sources are unchanged. " if not patched else
                ". PATCHED BUILD: GCC 13 cannot deduce the class-type "
                "template parameter of the _obf and _obf_bytes literal "
                "operators, so the build compiles a patched copy of "
                "include/advobfuscator/{bytes,string}.h in which the two "
                "operators take a char-array wrapper and construct the "
                "unchanged ObfuscatedBytes/ObfuscatedString from it (diff "
                "in the module docstring). The image is NOT byte-identical "
                "to a build of unmodified upstream. ")
             + "Current uses C++20; legacy uses C++14 and disables inlining "
             "to retain meaningful template bodies. "
             + {"mingw": "__TIME__ (the generator's seed) is pinned with "
                         "SOURCE_DATE_EPOCH=1700000000, so this image is "
                         "reproducible; the optimisation levels are "
                         "measured in the module docstring.",
                "linux": "Built before __TIME__ was pinned, so this image is "
                         "not reproducible: rebuilding it with the current "
                         "advobfuscator_build.py pins SOURCE_DATE_EPOCH to "
                         "1700000000.",
                "msvc": "__TIME__ (the generator's seed) cannot be pinned "
                        "with cl (SOURCE_DATE_EPOCH is ignored, redefining "
                        "the macro gives warning C4117), so this image is "
                        "not reproducible."}[flavor])
    if patched:
        flags += "; patched include copy (literal operators)"
    if pinned:
        flags += "; SOURCE_DATE_EPOCH=1700000000 (__TIME__ 22:13:20)"
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
        notes=notes,
    )


RECIPES = {}
for _mode in ("current", "legacy"):
    RECIPES["ADVobfuscator_%s_linux" % _mode] = _recipe(
        _mode, "linux", ["linux_x86", "linux_x64"])
    RECIPES["ADVobfuscator_%s_msvc" % _mode] = _recipe(
        _mode, "msvc", ["msvc_x86", "msvc_x64"])
    RECIPES["ADVobfuscator_%s_mingw" % _mode] = _recipe(
        _mode, "mingw", ["mingw_x86", "mingw_x64"])
