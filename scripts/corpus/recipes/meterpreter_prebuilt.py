"""Meterpreter as Rapid7 distributes it: the MSVC prebuilt (mcrit-data issue #31).

`data/Meterpreter`'s other artefacts are `metsrv` cross-compiled with MinGW,
which is upstream's own CMake path and real reference data - but it is not the
build anybody meets. Rapid7 compiles with MSVC and ships the result in the
`metasploit-payloads` RubyGem, which Metasploit then stages onto the target.
That is the image in the wild, and `scripts/corpus/README.md` says to prefer a
prebuilt where upstream publishes one.

It is also the only way this axis can exist at all. PR #96 recorded the MSVC
source build as unreachable here and why: `metsrv` declares its own
``struct _CLIENT_ID`` and the 10.0.26100 SDK now declares one too
(``pool_party_ext.h(22,16): error C2011``), while upstream's ``v141_xp`` and
Rapid7's own ``v120_xp`` toolsets are gone from every runner image. A source
fix means patching upstream, which this repository does not do. Harvesting the
published binary needs neither.

**The files in the gem are not PE images.** Since 2.0.x each one is an ``msf``
header over an AES-256-CBC ciphertext. The key is a constant committed in the
gem's own ``lib/metasploit-payloads/crypto.rb`` - the same bytes in every copy
of a given version, with nothing per-build or per-install in it - so
``scripts/corpus/decrypt_msf.py`` reads the key table out of the pinned file
and decrypts. No payload is generated, no listener is configured, nothing is
executed: one AES pass turns a file on disk into the image upstream compiled.

Pinned by the gem's published digest rather than a git ref, because the binary
is the thing being pinned and no commit identifies it. Version 2.0.258 is the
newest published gem; the MinGW recipe's 2.0.259 is the unreleased source
head, so the two rows in the README are a version apart by necessity.

What is deliberately **not** taken, of the 25 components the gem ships:

  * ``ext_server_python`` (7.1 MB x64) - a whole embedded CPython.
  * ``ext_server_kiwi`` (1.5 MB) - mimikatz, which is issue #60 and its own
    family, exactly as the MinGW recipe leaves ``BUILD_EXT_KIWI`` off.
  * ``ext_server_winpmem`` (1.4 MB) - the WinPmem memory acquisition driver
    stack.
  * ``ext_server_sniffer`` (495 KB) - built against the proprietary PSSDK,
    whose source upstream does not ship.

Those four are the four largest images in the gem and each is overwhelmingly
somebody else's code; filing them under `Meterpreter` would attribute it here.
The remaining 21 components are Meterpreter's own.

The ``.debug.dll`` half of every pair is skipped: same code with logging
compiled in, so it would enter the corpus as a near-duplicate of its release
twin and inflate every match count it took part in.

``min_named_ratio=0``, and this family is as close to fully unnamed as the
corpus gets: **2 recovered symbols across 28,892 functions.** MSVC keeps
symbols in a PDB and the gem publishes none, so the export table is the only
source left, and it yields almost nothing - ``elevator``'s ``a`` and
``ext_server_priv``'s ``control``. Everything else is reached from
``original_entry_point`` and named ``sub_*``. The stripped MinGW LibTomCrypt
artefacts set 0 for the same reason, but they at least keep an export table.

That is a real limit on what these reports are good for, and worth stating
plainly: they are PicHash and MinHash material, not something to read symbol
names out of. The MinGW rows in this same family are where the names are. What
this axis adds is the code *shape* a real Meterpreter has - 1029 functions in
``metsrv`` x64 against the MinGW build's 615 - which is what a match against
a live sample actually runs on.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Compiled by MSVC v142 - every one of the 98 files in the gem reports PE
# optional-header linker version 14.29, i.e. VS2019 16.11. Stated rather than
# inferred from the host that runs the extraction, which is this Linux box.
_PRODUCER = "msvc142"

# Meterpreter's own components. The four vendored giants the module docstring
# lists are not here; nothing else in the gem is left out.
_COMPONENTS = (
    "metsrv",
    "dump_sam",
    "elevator",
    "screenshot",
    "ext_server_bofloader",
    "ext_server_espia",
    "ext_server_extapi",
    "ext_server_incognito",
    "ext_server_lanattacks",
    "ext_server_peinjector",
    "ext_server_powershell",
    "ext_server_priv",
    "ext_server_stdapi",
    "ext_server_stdapi_audio",
    "ext_server_stdapi_fs",
    "ext_server_stdapi_net",
    "ext_server_stdapi_railgun",
    "ext_server_stdapi_sys",
    "ext_server_stdapi_ui",
    "ext_server_stdapi_webcam",
    "ext_server_unhook",
)

# The four PicHashes that kept the x86 leg out for two releases of this
# recipe, each audited by hand against the single symbol the census reports
# it under. Three are the statically linked 32-bit MSVC C runtime - upstream
# sets USE_STATIC_MSVC_RUNTIMES, and these are its x87 helpers, which is why
# only the 32-bit leg has them - and one is zlib's, out of metsrv's vendored
# 1.0.4P fork.
#
# What makes these admissible where the automatic rule was not: every one is
# reported by `validate --deep` under a *single* symbol ("appears under 3
# families as the same symbol X"), so the hash identifies one function rather
# than a shape shared by dozens of trivial bodies. That is the distinction
# the long comment below turns on, and it is the reason this list is written
# out by hand instead of being derived.
#
# _putShortMSB is the same function `vendors=["libzlib"]` removes from the
# MSVC *source* build in meterpreter_msvc.py; it is listed here because these
# reports have no symbol for that filter to match.
_EXCLUDED_PICHASHES = {
    18136989794466017840: "data/MSVC:__twoToTOS",
    11007584211390772839: "data/MSVC:__CIpow_pentium4",
    17085667784515999986: "data/MSVC:__EH_prolog",
    17596394674013296920: "data/libzlib:_putShortMSB",
}

_CRYPTO_RB = "lib/metasploit-payloads/crypto.rb"
_DECRYPT = ("python3 {repo}/scripts/corpus/decrypt_msf.py " + _CRYPTO_RB +
            " data/meterpreter/%(component)s.{arch}.dll"
            " plain/%(component)s.{arch}.dll")


def _build_steps():
    # A .gem is a tar of three members; fetch unpacks that much, and the
    # payload tree is one level further in. Only the two paths that are
    # actually needed come out of it - the gem also carries Android, Java,
    # PHP and Python stages that are not PE images.
    steps = [BuildStep("tar xzf data.tar.gz " + _CRYPTO_RB + " data/meterpreter")]
    steps.extend(BuildStep(_DECRYPT % {"component": component})
                 for component in _COMPONENTS)
    return steps


def _artifacts():
    # One artefact per component, with {arch} resolved per leg, rather than 42
    # artefacts naming both architectures in one list. Two reasons, and the
    # second is the binding one:
    #
    #   * it mirrors how every other two-architecture recipe here is written,
    #     the MinGW Meterpreter recipe included;
    #   * `component` has to identify an artefact uniquely inside a recipe.
    #     refresh_provenance._pick_artifact resolves a committed entry back to
    #     its artefact by component alone, to recover a build_flags override,
    #     and reports every entry whose component matches two - so listing
    #     metsrv.x86 and metsrv.x64 as separate artefacts left all 42 entries
    #     unmatched.
    return [Artifact(path="plain/%s.{arch}.dll" % component,
                     component=component,
                     producer=_PRODUCER)
            for component in _COMPONENTS]


RECIPES = {
    "Meterpreter_2.0.258_prebuilt": Recipe(
        family="Meterpreter",
        version="2.0.258",
        upstream="https://github.com/rapid7/metasploit-payloads",
        license="BSD-3-Clause",
        source=Source(
            url="https://rubygems.org/downloads/metasploit-payloads-2.0.258.gem",
            sha256="f6a3dc48278bb4932d4938d69c7ad0b6e06cd901b31633b03082d538eb69125e"),
        build=_build_steps(),
        artifacts=_artifacts(),
        # x64 only, and the x86 leg is a measurement rather than an
        # oversight. Both were built and gated; the x86 one added four
        # leakage findings to `validate --deep` and the x64 one added none:
        #
        #   _putShortMSB      (20 ins)  MSVC, Meterpreter, libzlib
        #   __twoToTOS        (11 ins)  (unknown), MSVC, Meterpreter
        #   __CIpow_pentium4  (10 ins)  (unknown), MSVC, Meterpreter
        #   __EH_prolog       (10 ins)  (unknown), MSVC, Meterpreter
        #
        # That is the statically linked 32-bit MSVC C runtime - upstream sets
        # USE_STATIC_MSVC_RUNTIMES - plus zlib's _putShortMSB out of metsrv's
        # vendored copy. __twoToTOS is in 20 of the 21 x86 artefacts, so there
        # is no subset to exclude: it is the whole leg or none of it. x64's
        # CRT has no equivalent of those x87 helpers, which is why only x86
        # trips it.
        #
        # What makes this unfixable *here* rather than deferrable: every one
        # of those bodies is **unnamed** in these reports, because no PDB is
        # published. corpus.baseline drops a function only when a symbol and
        # a PicHash both match a probe, so a baseline round - the fix that
        # ext_server_stdapi's MinGW C++ EH residue waits on - cannot reach
        # these at all. Lowering MIN_CROSS_FAMILY_INSTRUCTIONS to hide them
        # would be lowering a gate to admit data. So the x86 leg was held
        # back for two releases of this recipe while three routes to it were
        # measured and closed, and it is in now by a fourth - the audited
        # `exclude_pichashes` list above, which is the one mechanism none of
        # the three could substitute for. The three are kept on the record
        # below because each is a thing a reader will otherwise try.
        #
        # Re-measured after the RUNTIME_REFERENCE collision class landed, on
        # the theory that three of the four would reclassify: they are named
        # only by MSVC, and validate.is_generated_family is False for the
        # IDA-derived data/MSVC, which is exactly that class's condition. The
        # theory was wrong and the leg still costs four findings - the census
        # goes 26 -> 30 problems with all 21 x86 components built (15,835
        # functions). Two separate reasons, both worth recording because each
        # closes a route someone will otherwise try:
        #
        #   * `(unknown)` in those three rows is data/MSVC itself. Its
        #     2015_Pro_x86 and VC6_Express_x86 exports carry no `family`
        #     field - validate NOTEs this already - so one MSVC export
        #     resolves to `MSVC` and another to `(unknown)`, and
        #     is_generated_family("(unknown)") is True by design, for a tree
        #     checked out from somewhere other than data/. So the class does
        #     not fire. Making it fire by filling that field in would drop
        #     those collisions from three families to two, under
        #     find_cross_family_functions' threshold=3, and they would leave
        #     the census by disappearing rather than by being classified -
        #     hiding a true finding instead of explaining it, while the CRT
        #     bodies stay filed under Meterpreter.
        #   * _putShortMSB is a genuine three-family finding (MSVC,
        #     Meterpreter, libzlib) that no metadata change touches, and
        #     `vendors` cannot reach it either: that filter needs a symbol,
        #     and these reports have none.
        #
        # The harm these three would have left behind is concrete rather than
        # bookkeeping, which is why none of them was taken: __twoToTOS is in
        # 20 of the 21 x86 artefacts, so admitting the leg *with the bodies
        # still in it* files 32-bit MSVC CRT under Meterpreter across nearly
        # all of it, and any sample carrying that CRT would match this
        # family. That is the false-attribution the gate exists to catch, and
        # the gate was right every time. What changed is not the gate but the
        # artefact: the four bodies are now removed by name-checked hash and
        # keep the families they belong to.
        #
        # A third route was measured and is also closed, and it is the
        # interesting one because it looks obviously right. corpus.baseline
        # needs a symbol only because it matches a *probe*; data/MSVC already
        # *names* these bodies, so a filter that dropped an unnamed function
        # whose PicHash a non-generated reference family names would seem to
        # be the same act with MSVC's symbol standing in for the probe's. Its
        # blast radius is even reassuringly small: 207 functions corpus-wide
        # at the MIN_CROSS_FAMILY_INSTRUCTIONS floor, 204 of them in these 21
        # symbol-less x64 artefacts.
        #
        # It does not work, because the mapping is one PicHash to *many*
        # reference names. A single hash here matches about 28 MSVC symbols
        # at once - ??0bad_alloc@std@@, ??0bad_typeid@std@@,
        # ??0out_of_range@std@@ and a dozen Concurrency:: types - because
        # every one of them is an exception-class copy constructor with the
        # same trivial body. The hash identifies a *shape*, not a function.
        # The tell is that the same shapes also matched 7-Zip and
        # libtomcrypt, two unrelated projects: a signal that fires on three
        # unrelated codebases is not identifying a runtime.
        #
        # So the filter could not tell MSVC's bad_alloc copy constructor from
        # any other trivial copy constructor, Meterpreter's own included, and
        # would delete possibly-project code on an ambiguous match. Some of
        # the 204 are certainly CRT - fegetenv, sprintf_s, __CxxFrameHandler4
        # and UnwindNestedFrames are in there - but "some of these are CRT"
        # is not a rule. This is what the symbol half of is_glue's condition
        # is *for*: it disambiguates a generic shape, and dropping it is not
        # a relaxation but a loss of the only thing that made the match mean
        # anything. Correspondingly, the 204 must not be read as 204
        # misattributed functions: sharing a many-to-one hash is not evidence
        # of misattribution, and nothing here says the committed x64 data is
        # wrong.
        #
        # Otherwise a toolchain selects nothing here but which machine runs
        # the decryption - the command is python3 either way, as sRDI's
        # extraction is - and the architecture in the stem comes from the PE
        # header.
        #
        # **Both legs, as of the fourth attempt at this.** What finally
        # answers it is none of the three routes above but the pass they each
        # pointed at: `exclude_pichashes`, a hand-audited list rather than an
        # inferred rule. The four bodies are removed and keep data/MSVC's and
        # data/libzlib's families, the census returns to its baseline, and
        # 15,835 functions of the 32-bit build - the one a WOW64 or older
        # target actually runs - stop being absent for the sake of four
        # functions out of 15,835.
        toolchains=["mingw_x86", "mingw_x64"],
        # Audited one at a time; see _EXCLUDED_PICHASHES above. Declared for
        # both legs, and the x64 one loses nothing: its CRT has no x87
        # helpers and its copy of putShortMSB hashes differently, exactly as
        # `vendors` finds nothing on the x64 source build. provenance records
        # the declaration either way, so "the pass ran and matched nothing"
        # stays distinguishable from "no pass was applied".
        exclude_pichashes=_EXCLUDED_PICHASHES,
        build_flags="MSVC v142 (as distributed by Rapid7); exact flags not published",
        min_named_ratio=0,
        notes="Decrypted from the published metasploit-payloads gem with "
              "scripts/corpus/decrypt_msf.py, using the key table committed "
              "in the gem's own lib/metasploit-payloads/crypto.rb. Not "
              "rebuilt here: the MSVC source build needs an SDK older than "
              "any runner image carries. Release images only; the .debug.dll "
              "twins are skipped. ext_server_python (CPython), "
              "ext_server_kiwi (mimikatz, issue #60), ext_server_winpmem and "
              "ext_server_sniffer (proprietary PSSDK) are excluded as "
              "vendored third-party code. No PDBs are published, so only "
              "exported functions carry a name.",
    ),
}
