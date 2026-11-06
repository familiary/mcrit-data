"""Deterministic front end for the SysWhispers generators (v2, v3, v4).

Every generator in this lineage randomises part of its output, so none of
them produces the same source twice. Reference data records a sha256 per
artefact and is expected to rebuild byte-identically, so the randomness is
seeded here rather than left to the clock.

What each one draws, found by reading the generators and confirmed by
running each three times and diffing:

* **SysWhispers2** (``syswhispers.py:14``) takes
  ``random.randint(2**28, 2**32-1)`` as ``SW2_SEED``. That seed keys every
  function-name hash, so it changes the immediates in ``SW2_HashSyscall``
  and the whole hash table. Three runs, three outputs.
* **SysWhispers3** (``syswhispers.py:174-176``) takes the same seed plus a
  two-character ``egg`` from ``random.choices``.
* **SysWhispers4** (``core/generator.py:41`` and ``:668``) goes through
  ``os.urandom`` instead - the Obfuscator seed and the ``--encrypt-ssn``
  key - which ``random.seed`` does not reach, so it is stubbed out below.

Seeding matters for more than reproducibility. Measured without it, each
SysWhispers3 ``--method`` looked as though it contributed its own
``SW3_HashSyscall`` and ``SW3_PopulateSyscallList``; seeded, those collapse
to one body per project, because what differed was the seed and not the
code. An unseeded measurement would have justified four artefacts where the
evidence supports one.

Upstream is not modified. This imports upstream's entry point and hands argv
to it unchanged, which is the route a recipe takes when command-line options
alone cannot reach a build property.

``SW_SEED`` sets the seed; recipes pin it. The value is arbitrary - what
matters is that it is fixed and recorded in provenance.
"""

import os
import random
import runpy
import sys

_seed = int(os.environ.get("SW_SEED", os.environ.get("SW4_SEED", "20260101")))

# v2 and v3 draw from the module-level `random`.
random.seed(_seed)

# v4 draws from os.urandom, which random.seed() does not reach.
_rng = random.Random(_seed)
os.urandom = lambda n: bytes(_rng.getrandbits(8) for _ in range(n))

_generator = sys.argv[1]
sys.argv = [_generator] + sys.argv[2:]
runpy.run_path(_generator, run_name="__main__")
