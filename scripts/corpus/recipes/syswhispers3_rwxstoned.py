"""SysWhispers3, RWXstoned's fork - the obfuscated export-directory accessors.

This is listed in SysWhispers4's reference table beside klezVirus's original
and is a separate family here rather than a second component of it, because
what it changes is the resolver's own code and not a build option of it.

The fork is five files different from upstream: ``.gitignore``,
``README.md``, ``syswhispers.py`` by one line, and - the reason it is worth
reference data - ``data/base.c`` and ``data/base.h``, the resolver template
that every generated artefact embeds.

What it adds there is four functions, and they are the family's whole
distinguishing feature. ``getNumberOfNames``, ``getAddressOfFunctions`` and
``getAddressOfNames`` each read one field of ``IMAGE_EXPORT_DIRECTORY``, and
none of them does it by naming the field: each runs a ten-iteration loop
that computes the field's offset arithmetically and takes the value on one
chosen iteration. ``moudge`` is a loop returning a constant. The effect is
that the resolver contains no direct reference to the export-directory
layout, which is what a signature keying on that layout looks for -
klezVirus's original reads ``expDir->NumberOfNames`` and this does not.

That is the shape worth matching, and it is why the fork measures larger
than its parent on the same options: nine bodies of ten instructions or
more against the original's five, at both widths.

The one-line ``syswhispers.py`` difference is in the ``ror8`` lambda, which
adds ``1 +`` and ``2 +`` to the two halves of the rotate. It changes the
name-hash constants and nothing structural; it is recorded here because it
means the fork's hashes are not the original's even at the same seed, so the
two families' ``SW3_HashSyscall`` bodies differ for that reason as well as
for the accessors.

**Points built and dropped**, on the same measurement as the parent:
``embedded`` and ``jumper`` at both widths are kept, nine bodies each;
``jumper_randomized`` contributed nothing ``jumper`` did not have and is
dropped; ``egg_hunter`` is refused by the generator under ``-c mingw``. The
seed is pinned by ``exercisers/syswhispers_gen.py`` for the reason
syswhispers3.py explains.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

from .syswhispers3 import _recipe


_UPSTREAM = "https://github.com/RWXstoned/SysWhispers3"
_REF = "3158bc2abb66276b0b9b1cfbab590dcd42ab2860"
_VERSION = "2024-04-03"
_EXTRA = (" This fork adds moudge, getNumberOfNames, getAddressOfFunctions "
          "and getAddressOfNames to the resolver template, which read "
          "IMAGE_EXPORT_DIRECTORY fields through arithmetic loops instead of "
          "naming them; that is what distinguishes it from klezVirus's "
          "original and why it measures nine bodies to the original's five.")


RECIPES = {
    "SysWhispers3RWXstoned_%s_x64" % _VERSION: _recipe(
        "x64", _UPSTREAM, _REF, "SysWhispers3RWXstoned", _VERSION, 50,
        _EXTRA),
    "SysWhispers3RWXstoned_%s_x86" % _VERSION: _recipe(
        "x86", _UPSTREAM, _REF, "SysWhispers3RWXstoned", _VERSION, 75,
        _EXTRA),
}
