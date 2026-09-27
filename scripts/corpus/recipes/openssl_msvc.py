"""OpenSSL built with MSVC, beside the MinGW builds of the same release.

OpenSSL in the wild is overwhelmingly MSVC-built - the MinGW recipe's own
docstring says so - and data/OpenSSL carries twelve GCC artefacts and nothing
else. This is the highest-value family in the corpus and it was deliberately
held out of every earlier MSVC wave for two measured reasons. Both are real,
and this recipe answers them rather than ignoring them.

**NASM.** NOTES-WINDOWS.md at every pinned release says "NASM is the only
supported assembler", and windows-2022's toolset manifest does not list NASM.
That is not negotiable through flags - but it is not the whole story.
``Configurations/10-main.conf``'s ``vc_win64a_info`` was read at both 1.1.1w
and 3.5.8 and has three branches: nasm if ``nasm -v`` answers, **ml64 with
the masm perlasm scheme if ``$disabled{asm}``**, and ``$die->("NASM not
found")`` otherwise. ``vc_win32_info`` is the same shape, with the comment
"not actually used, uplink shim is inlined into C code". So ``no-asm`` is a
supported, in-tree configuration that needs no assembler beyond the ml64 that
ships with MSVC itself, and it is the only NASM-free route. No installer
step, no runner-image change.

**What no-asm costs, measured rather than asserted.** The survey called
no-asm "the wrong answer" on the grounds that it removes "a large and highly
recognisable share of libcrypto". The first half of that is right and the
second is not, and the difference decides this recipe. Two measurements:

  * Configuring the pinned 3.5.8 tree twice on this host, ``mingw64 shared
    no-tests`` against the same plus ``no-asm``, and diffing the object lists
    the two Makefiles name: 44 assembly modules leave, 12 C modules arrive,
    and 802 modules are common to both. So no-asm touches about 5% of
    libcrypto's translation units.
  * Extracting the ``.globl`` symbols from all 39 perlasm modules the x86_64
    build generates gives 182 entry points; of those, **158 appear by name in
    the committed MinGW x64 libcrypto artefact, out of 13206 functions** -
    1.2%. That artefact has 13067 named functions, so even if every one of
    the 139 unnamed ones were an interior label inside an assembly module,
    the ceiling is 2.2%.

The trade is therefore: give up at most ~2% of libcrypto's functions - the
AES/SHA/GHASH/montgomery cores, which are genuinely the distinctive ones -
to gain MSVC-compiled reference data for the other ~98%, which is the ASN.1,
X.509, EVP, BIO, provider and error machinery that dominates any libcrypto by
function count and which the corpus currently answers with GCC code only.
Those bodies are bit-for-bit the same source whether asm is on or off. Taken.

The honest cost is recorded in ``notes`` and it is twofold, because no-asm
does not only subtract: the 12 C modules it adds (aes_core, aes_cbc, bn_asm,
camellia, cmll_cbc, chacha_enc, rc4_enc, rc4_skey, keccak1600, wp_block,
mem_clr) are compiled into this artefact and are **not** present in a
stock Windows OpenSSL DLL. They are not wrong - they match a genuine no-asm
OpenSSL, of which there are many in embedded and vendored builds - but they
are extra rather than representative, and anyone comparing this artefact with
a shipped libcrypto should know which way each difference runs.

**Memory, and why 1.1.1w.** ``export_reports`` peaked at 9.4 GB resident on a
15 GB machine for the MinGW libcrypto and was OOM-killed once; a GitHub
windows runner has 16 GB. Peak scales with function count, and the committed
provenance gives those directly: 3.5.8 x64 libcrypto is 13206 functions,
3.0.15 is 10944, **1.1.1w is 6546** - half of 3.5.8. One version only, and
1.1.1w is the one: it halves the single measured failure mode, its .mcrit is
6.9 MB against 3.5.8's 13.9 MB so it is nowhere near
config.MAX_COMMITTED_FILE_SIZE, and the MinGW recipe already records that
1.1.1 "has no provider layer at all and is still by far the most encountered
OpenSSL". If this proves cheap on the runner, 3.0.15 and then 3.5.8 are
one-line additions.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

**What else was read rather than assumed, at the pinned tag:**
  * ``VC-common`` sets ``lib_cflags => add("/Zi /Fdossl_static.pdb")`` and
    ``LDFLAGS => add("/debug")`` on a BASE_Windows ``LDFLAGS => "/nologo"``.
    So OpenSSL's VC build already compiles /Zi and links /debug, and the
    survey's open question about "exact flag plumbing for /Zi" is answered:
    there is none to do.
  * ``VC-noCE-common`` adds ``/O2`` for release and ``/MD`` whenever shared
    is not disabled, so the runtime library needs no override either. This
    and libzlib are the only two families in the MSVC wave that already
    default to what this corpus wants.
  * ``Configure`` resolves ``$config{LDFLAGS} = user value || target value``,
    so an ``LDFLAGS=`` make-variable on the command line **replaces**
    "/nologo /debug" rather than adding to it - which is why both are
    restated below. (``-Wl,``-style arguments would append instead, but
    mixing the two styles is a hard error in Configure.)
  * ``windows-makefile.tmpl`` links the shared library with
    ``$(LD) $(LDFLAGS) $(LIB_LDFLAGS) /implib:... $(LDOUTFLAG)$dll /def:...``
    and declares ``$import: $dll``, so ``nmake build_libs`` - whose
    prerequisites are the static libs and the import libs - does build both
    DLLs. openssl.exe is not built.
  * ``build.info`` sets ``SHARED_NAME[libcrypto]=libcrypto-$sover_filename
    $target{multilib}`` for VC targets, and VC-WIN64A sets
    ``multilib => "-x64"`` where VC-WIN32 sets none. So the files are
    ``libcrypto-1_1-x64.dll`` / ``libssl-1_1-x64.dll`` on x64 and
    ``libcrypto-1_1.dll`` / ``libssl-1_1.dll`` on x86, with PDBs of the same
    stem - which is why the outputs are normalised to stable names, exactly
    as the MinGW recipe does for its own two spellings.

**Not verified here, and it cannot be:** ``perl Configure`` refuses to run
under a non-Windows perl ("This perl implementation doesn't produce Windows
like paths"), so the generated makefile could not be produced or inspected on
this host. Everything above comes from the configuration data and the
makefile template that generate it, not from a generated makefile.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# LDFLAGS replaces the target's "/nologo /debug", so both are restated.
# /Brepro drops the build timestamp MSVC stamps into the PE header, without
# which two runs over identical source record different sha256s. /OPT:NOREF
# keeps routines nothing references and /OPT:NOICF keeps two routines that
# compiled to identical bodies apart - folding them cost VX-API its
# StringConcat/StringCopy pair, and a crypto library is full of near-twin
# bodies. link /debug is documented to imply both, but the corpus says what
# it wants rather than relying on that.
#
# /INCREMENTAL:NO because /debug implies /INCREMENTAL and the /OPT:NO* forms do
# not suppress it - only /OPT:REF, /OPT:ICF and /OPT:ORDER are documented to.
# An incrementally linked image reaches each function through a jump table, and
# SMDA recovers every one of those one-instruction thunks as a function of its
# own, unnamed. That was measured on the artefacts this omission produced: 4882
# of libcrypto x86's 12,861 functions and 1097 of libssl x86's 3252, the worst
# of any family here. It is not what a released binary looks like, and it
# inflates the function count of the family it is filed under.
#
# It goes in LDFLAGS rather than anywhere else for the reason the block
# above gives: LDFLAGS replaces the target's value outright, so every flag
# this link needs has to be in this one string.
_LDFLAGS = ('"LDFLAGS=/nologo /debug /Brepro /INCREMENTAL:NO '
            '/OPT:NOREF /OPT:NOICF"')

# no-asm is the NASM-free configuration described at length above.
# no-tests matches the MinGW recipe. no-makedepend is upstream's own
# suggestion in NOTES-WINDOWS.md for a build that is never rebuilt
# incrementally; it changes no emitted code.
_CONFIGURE = "shared no-tests no-asm no-makedepend %s" % _LDFLAGS

# The Configure target name differs between the two legs and this tooling has
# no placeholder for it - {openssl_target} is the mingw pair. A Recipe has one
# build list for all of its toolchains, so the choice is made by cmd.exe's
# own "if", one step per architecture. A false "if" runs nothing and leaves
# the fresh cmd.exe's ERRORLEVEL at 0, so the skipped step is not a failure.
# No parentheses: a parenthesised cmd block would have to survive the quotes
# in LDFLAGS, and this form does not.
_CONFIGURE_X64 = 'if "{arch}"=="x64" perl Configure VC-WIN64A ' + _CONFIGURE
_CONFIGURE_X86 = 'if "{arch}"=="x86" perl Configure VC-WIN32 ' + _CONFIGURE

# The DLL and PDB names carry the soversion and, on 64-bit only, an -x64
# suffix, so they are copied to stable names rather than four Artifact
# variants being spelled out. Indexing the sorted glob rather than iterating
# it is deliberate: a missing file raises IndexError and fails the step, where
# an empty loop would leave build.py to report a missing artefact with no clue
# why. No % anywhere - cmd.exe would try to expand it.
_NORMALISE = (
    'python -c "'
    "import glob,shutil;"
    "[shutil.copy(sorted(glob.glob(n+'-*'+e))[0], n+e) "
    "for n in ('libcrypto','libssl') for e in ('.dll','.pdb')]"
    '"')


RECIPES = {
    "OpenSSL_1.1.1w_msvc": Recipe(
        family="OpenSSL",
        version="1.1.1w",
        upstream="https://github.com/openssl/openssl",
        license="OpenSSL / SSLeay",
        # The same release asset and the same digest the MinGW recipe pins,
        # taken from the SHA-256 upstream publishes beside it.
        source=Source(
            url="https://github.com/openssl/openssl/releases/download/"
                "OpenSSL_1_1_1w/openssl-1.1.1w.tar.gz",
            sha256="cf3098950cb4d853ad95c0841f1f9c6d3dc102dccfcacd521d93925208b76ac8"),
        build=[
            BuildStep(_CONFIGURE_X64),
            BuildStep(_CONFIGURE_X86),
            BuildStep("nmake build_libs"),
            BuildStep(_NORMALISE),
            # Cheap insurance, as in xz_msvc.py: build.py reports a missing
            # artefact by the path it expected and nothing else, and this
            # puts the names the build actually wrote into the log the
            # workflow prints on failure.
            BuildStep("dir", allow_failure=True),
        ],
        artifacts=[
            Artifact(path="libcrypto.dll", component="libcrypto",
                     pdb="libcrypto.pdb"),
            Artifact(path="libssl.dll", component="libssl",
                     pdb="libssl.pdb"),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        requires=["perl"],
        build_flags="/W3 /wd4090 /O2 /MD /Zi /Gs0 /GF /Gy (VC-WIN32 / "
                    "VC-WIN64A release defaults, unmodified), no-asm; "
                    "/nologo /debug /Brepro /OPT:NOREF /OPT:NOICF at link, "
                    "replacing upstream's /nologo /debug",
        notes="Built no-asm, which is the only configuration that needs no "
              "NASM: upstream's VC targets fall back to ml64 with the masm "
              "perlasm scheme for the uplink shim alone, and ml64 ships with "
              "MSVC. That changes what this artefact contains, in both "
              "directions, and the difference is about 5 per cent of "
              "libcrypto's translation units. Absent: the hand-written "
              "AES, SHA-1/256/512, Keccak, GHASH, ChaCha, Poly1305, RC4, "
              "Camellia, Whirlpool, bignum-montgomery and NIST-P256 "
              "assembly, which a stock Windows libcrypto does have - "
              "measured at 158 of 13206 named functions, 1.2 per cent, in "
              "the MinGW 3.5.8 x64 artefact of this family. Present instead: "
              "the portable C fallbacks for those primitives (aes_core, "
              "aes_cbc, bn_asm, camellia, cmll_cbc, chacha_enc, rc4_enc, "
              "rc4_skey, keccak1600, wp_block, mem_clr), which a stock "
              "Windows libcrypto does not - they match a genuine no-asm "
              "OpenSSL rather than nothing, but they are extra rather than "
              "representative. Everything above the primitives - ASN.1, "
              "X.509, EVP, BIO, the error tables, the engine and SSL layers "
              "- is the same source either way and is the overwhelming "
              "majority of both artefacts. One version only, because "
              "libcrypto is the largest sample in this corpus and its export "
              "peaked at 9.4 GB resident on a 15 GB machine; 1.1.1w is half "
              "the function count of 3.5.8. No dependencies: no zlib, and "
              "Windows supplies the entropy source. Built against the DLL "
              "runtime, so the MSVC C runtime is imported rather than linked "
              "in and stays attributed to data/MSVC. openssl.exe is not "
              "built.",
    ),
}
