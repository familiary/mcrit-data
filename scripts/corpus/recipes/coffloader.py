"""trustedsec/COFFLoader - RunCOFF and the COFF relocation machinery
(mcrit-data issue #13).

A re-implementation of a COFF object loader with a Cobalt Strike
Beacon-Object-File compatibility layer. ESET's FamousSparrow write-up reports
the SparroWocky backdoor running BOFs through a modified ``RunCOFF`` taken from
this project; that is a structural attribution, not a code-level match, which
is the reason a reference build is worth having.

Pinned at edfa763, 2026-09-28, the head when this was written. The repository
has no tags.

The function count was the open question in the tracker issue, and it was
measured, not read from the source: COFFLoader.c has the loader proper
(``RunCOFF``, ``process_symbol``, ``unhexlify``, ``getContents``,
``starts_with``, the two ``coff_symbol_is_*`` predicates, ``main``) and
``beacon_compatibility.c`` is another thirty-odd ``Beacon*`` API functions
that RunCOFF exposes to loaded objects. Both are part of the project and both
are linked into ``COFFLoader.exe``, exactly as upstream's Makefile does. The
measured counts are in the notes of each provenance record.

Built the way upstream's Makefile builds it (``-DCOFF_STANDALONE``, no
``-DDEBUG``) except for the optimisation level: the Makefile passes no ``-O``
and so builds at ``-O0``, which is not the shape a loader copied into an
implant is compiled at. ``-O2`` as every other recipe here. Upstream's
Makefile also hard-codes ``x86_64-w64-mingw32-gcc`` / ``i686-w64-mingw32-gcc``
and ``test.c`` is a BOF test object, not a program, so the two commands are
reproduced directly with ``{cc}`` instead of invoking ``make``.

The Makefile's ``nix`` target builds the same sources for Linux; it is a
``-DDEBUG`` test harness for the COFF parser (the Win32 resolver and the
mapping code are all under ``_WIN32``), not something shipped, and Linux ELF
is out of scope for a Windows loader.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


RECIPES = {
    "COFFLoader_2026-09-28": Recipe(
        family="COFFLoader",
        version="2026-09-28",
        upstream="https://github.com/trustedsec/COFFLoader",
        license="BSD-3-Clause",
        source=Source(git_url="https://github.com/trustedsec/COFFLoader.git",
                      git_ref="edfa7639a137bee639e535732a1aa67cc2b33549"),
        build=[
            BuildStep("{cc} -O2 -g -Wall -DCOFF_STANDALONE "
                      "beacon_compatibility.c COFFLoader.c -o COFFLoader.exe"),
        ],
        artifacts=[Artifact(path="COFFLoader.exe", component="COFFLoader.exe")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 -g -Wall -DCOFF_STANDALONE (upstream Makefile line "
                    "at its default -O0)",
        notes="COFFLoader.c plus beacon_compatibility.c, as upstream's "
              "Makefile links them.",
    ),
}
