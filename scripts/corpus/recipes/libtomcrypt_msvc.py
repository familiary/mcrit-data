"""LibTomCrypt built with MSVC, beside the MinGW build of the same tag.

This is the one family in the corpus where the MSVC build is **better data
than the MinGW one it joins**. makefile.mingw hardcodes ``-s`` on the DLL
link, so the committed MinGW artefacts are stripped: their recipe has to set
``min_named_ratio=0``, most of their function names come from the export
table, and because the CRT-glue filter matches on names it cannot act on the
unnamed remainder - ``removed_runtime_functions`` is empty for both. An
MSVC build carries a PDB, so this artefact is fully named and the glue filter
works on it.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

What was read rather than assumed:
  * libtomcrypt 1.18.2's ``makefile.msvc``, in full. Its own comment says
    "this makefile builds only static libraries" and its only library target
    is ``tomcrypt.lib``; the default target is that library. ``LTC_CFLAGS``
    is ``/nologo /Isrc/headers/ /Itests/ /D_CRT_SECURE_NO_WARNINGS
    /D_CRT_NONSTDC_NO_DEPRECATE /DLTC_SOURCE /W3 $(CFLAGS)`` - note
    ``$(CFLAGS)`` last, so anything passed on the command line wins - and its
    usage block documents the exact override used here:
    ``CFLAGS="/DUSE_LTM /DLTM_DESC /I…"  EXTRALIBS=…\\tommath.lib``.
    It contains **no /M flag at all**, so cl's default /MT would apply: the
    /MD below is the only thing keeping the MSVC C runtime out of this
    artefact.
  * libtommath 1.3.0 ships its own ``makefile.msvc``, whose default target is
    ``tommath.lib``. Its ``LTM_CFLAGS`` ends ``/Wall /wd4146 /wd4127 /wd4668
    /wd4710 /wd4711 /wd4820 /wd5045 /WX $(CFLAGS)``. **/Wall with /WX** on
    2019 code compiled by v143 is a build failure waiting to happen - v143
    has warnings that suppression list predates - so ``/WX-`` is appended
    through CFLAGS, which lands after /WX and turns warnings back into
    warnings. No /W level is passed with it: overriding /Wall as well would
    earn a D9025 "overriding '/Wall'" command-line warning, and whether /WX
    promotes *that* to an error is precisely the sort of thing not worth
    finding out in CI. This makefile too has no /M flag, so it also needs
    /MD or LibTomMath's objects arrive built against the static CRT.
  * both makefiles compile with ``$(CC) … /c $< /Fo$@`` and nmake's built-in
    ``CC = cl``. Neither uses the VC6 ``cl -o`` spelling that made bzip2's
    makefile.msc unusable here.
  * libtomcrypt's object list is ``src/ciphers/aes/aes.obj`` and 407 more
    like it - objects in subdirectories, updated by a bare ``.c.obj:``
    inference rule. NMAKE's documentation is self-contradictory about
    whether a rule with no braces reaches a target that carries a path, and
    that would be the whole build. It does: upstream's own ``appveyor.yml``
    runs ``nmake -f makefile.msvc all`` against this layout on the Visual
    Studio 2015, 2017, 2019 **and 2022** images, i.e. including v143, and
    builds libtommath with its ``makefile.msvc`` first in the same way this
    recipe does. That is upstream's CI rather than a reading of a manual.

Turning the static library into something SMDA can read is the remaining
work, and it is done the way the survey describes: a one-function anchor
object, linked into a DLL that pulls both archives in whole with
``/WHOLEARCHIVE``. The DLL exports nothing - 1.18.2 has no dllexport
annotations and this recipe does not add any - which is fine because the
names come from the PDB, and it is closer to the real sighting than an
export table would be: LibTomCrypt in the wild is compiled into its host.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# cmake -E copy_directory rather than xcopy: CMake is on the runner anyway
# and this has no /E /I /Y incantation to get wrong. The MinGW recipe does
# the same thing with cp -r.
_STAGE_LTM = "cmake -E copy_directory {libtommath} ltm"

# Upstream's own MSVC makefile for LibTomMath. /O2 rather than its default
# /Ox to match the MinGW sibling's -O2 and the rest of the MSVC recipes here;
# /MD because it has none; /WX- for the reason the docstring gives.
_BUILD_LTM = ('nmake -f makefile.msvc '
              'CFLAGS="/O2 /MD /Zi /Fdtommath.pdb /WX-"')

# Upstream's own MSVC makefile for LibTomCrypt, with the override its usage
# block documents. /Iltm is relative to the source root, which is where nmake
# runs cl from.
_BUILD_LTC = ('nmake -f makefile.msvc '
              'CFLAGS="/O2 /MD /Zi /Fdtomcrypt.pdb /DUSE_LTM /DLTM_DESC '
              '/Iltm"')

# Written with python rather than "echo … > anchor.c" for the reason
# blackbone.py writes its props file that way: the text contains parentheses
# and braces, and cmd.exe's quoting rules around those are not worth
# relying on. Python is on the runner - the workflow installs it to run this
# tooling at all.
_ANCHOR = ('python -c "'
           "open('anchor.c','w').write('int anchor(void){return 0;}')"
           '"')

_COMPILE_ANCHOR = 'cl /nologo /c /O2 /MD /Zi /Fdtomcrypt.pdb anchor.c'

# /WHOLEARCHIVE because nothing references these archives' members: without
# it the linker would take the anchor and discard both libraries, and the
# artefact would be a DLL containing one function. advapi32 is what
# upstream's own LTC_LDFLAGS links, for the system RNG in rng_get_bytes.c.
#
# The rest is the link line sqlite3_msvc.py explains: /DEBUG so a PDB is
# written at all, /Brepro so the PE carries no build timestamp and two runs
# over identical source record the same sha256, and /OPT:NOREF /OPT:NOICF so
# unreferenced and identically-compiled routines both survive as separate
# reference samples - which matters more here than anywhere else, since
# nothing in this DLL is referenced at all.
#
# Both archives are named twice on purpose: once as an ordinary input file,
# so the linker certainly loads them from this directory, and once in
# /WHOLEARCHIVE, which selects an already-named library by the spelling it
# was given. Naming a library in /WHOLEARCHIVE that the command line does
# not otherwise mention relies on the linker's library search to find it,
# which is one more thing that can quietly not happen.
#
# /INCREMENTAL:NO because /DEBUG implies /INCREMENTAL and the /OPT:NO* forms
# do not suppress it - only /OPT:REF, /OPT:ICF and /OPT:ORDER are documented
# to. An incrementally linked image reaches each function through a jump
# table, and SMDA recovers every one of those one-instruction thunks as a
# function of its own, unnamed. That was measured on the artefacts this
# omission produced: 978 of libtomcrypt x86's 2030 functions and 966 of x64's 2017. It is not what a
# released binary looks like, and it inflates the function count of the
# family it is filed under.
_LINK = ('link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF '
         '/WHOLEARCHIVE:tomcrypt.lib /WHOLEARCHIVE:ltm\\tommath.lib '
         '/PDB:libtomcrypt.pdb /OUT:libtomcrypt.dll anchor.obj '
         'tomcrypt.lib ltm\\tommath.lib advapi32.lib')


RECIPES = {
    "libtomcrypt_1.18.2_msvc": Recipe(
        family="libtomcrypt",
        version="1.18.2",
        upstream="https://github.com/libtom/libtomcrypt",
        # Upstream's LICENSE offers a choice of two, and neither is the
        # Unlicense: "LibTomCrypt is public domain" or WTFPL v2.
        license="public domain / WTFPL-2.0 (dual, licensee's choice)",
        # The same tag the MinGW recipe pins; 1.18.2 is the newest there is.
        source=Source(git_url="https://github.com/libtom/libtomcrypt.git",
                      git_ref="v1.18.2"),
        # The same LibTomMath commit the MinGW recipe pins. Its code ends up
        # inside this artefact, so it is fetched and recorded rather than
        # cloned inside a build step.
        extra_sources={"libtommath": Source(
            git_url="https://github.com/libtom/libtommath.git",
            git_ref="v1.3.0")},
        build=[
            BuildStep(_STAGE_LTM),
            BuildStep(_BUILD_LTM, cwd="ltm"),
            BuildStep(_BUILD_LTC),
            BuildStep(_ANCHOR),
            BuildStep(_COMPILE_ANCHOR),
            BuildStep(_LINK),
            # Cheap insurance, as in xz_msvc.py: build.py reports a missing
            # artefact by the path it expected and nothing else, and this
            # puts the names the build actually wrote into the log the
            # workflow prints on failure.
            BuildStep("dir", allow_failure=True),
        ],
        artifacts=[Artifact(path="libtomcrypt.dll",
                            component="libtomcrypt.dll",
                            pdb="libtomcrypt.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi (both libtomcrypt and the bundled "
                    "libtommath), LTC_SOURCE /DUSE_LTM /DLTM_DESC, /W3 for "
                    "libtomcrypt and /Wall /WX- for libtommath (upstream's "
                    "own levels); /DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF "
                    "/WHOLEARCHIVE at link",
        # Deliberately left at the default 0.5, unlike the MinGW recipe: the
        # whole argument for this artefact is that a PDB makes it nameable,
        # so a build that came back unnamed is a build that failed to do the
        # one thing it was added for and should be rejected.
        notes="Statically links LibTomMath 1.3.0, as the MinGW artefact does, "
              "so roughly 175 of this sample's functions are "
              "mp_*/s_mp_*/fast_mp_* and belong to that project; there is no "
              "LibTomMath family here for them to collide with, and upstream "
              "ships no configuration that leaves them out. The two static "
              "libraries are upstream's own makefile.msvc targets, pulled "
              "into a DLL with /WHOLEARCHIVE against a one-function anchor "
              "because SMDA cannot read a .lib; the DLL exports nothing and "
              "its names come from the PDB. Unlike the MinGW artefact, which "
              "upstream's makefile.mingw strips, this one keeps symbols - so "
              "it is the first properly named libtomcrypt in the corpus and "
              "the CRT-glue filter can act on it. Built against the DLL "
              "runtime, so the MSVC C runtime is imported rather than linked "
              "in and stays attributed to data/MSVC.",
    ),
}
