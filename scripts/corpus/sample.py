"""Sample-derived reference data: the second track, and what it may not do.

Every family produced by ``recipe.Recipe`` was compiled here from pinned
source, which is what lets a report claim a body *is* zlib 1.3's ``inflate``
rather than merely resembling it. The family label is true by construction.

Some families cannot be reached that way: the code exists only as shipped
binaries, there is no source to pin and no build to run. This module describes
those, and it is a sibling of ``Recipe`` rather than a variant of it for one
reason - a ``SampleRecipe`` has no ``Source``, no ``BuildStep`` and no
``toolchains``, so it cannot express a build and therefore cannot quietly
become one.

Three things follow from the label no longer being free, and all three are
enforced here rather than left to a reviewer:

* **The attribution is a claim, and claims carry evidence.** With a build,
  getting the family wrong is impossible. With a sample it is one mislabelled
  file, after which MCRIT names the wrong family confidently, forever, in
  every investigation that touches those bodies. So ``attribution`` and
  ``attribution_source`` are required fields and the source has to be a URL
  someone else can open, not a sentence.

* **The producer slot says ``sample``.** ``Recipe.slug`` writes
  ``<family>_<version>_<producer>_<arch>_<component>`` and hardcodes ``msvc``
  for blobs, on the grounds that naming the toolchain which merely ran the
  extraction would be "a lie baked into the filename". The same reasoning
  applies here with more force: nothing compiled this. Every filename, README
  row and link therefore carries the track, and it survives a file being
  copied out of its directory.

* **Subtraction is mandatory.** A shipped binary is mostly not the project:
  static CRT, vendored libraries, compiler glue. ``baseline.py`` subtracts
  that for builds because the toolchain is known; here it is not. Left
  unsolved this is fatal and this repository has already refused data over it
  twice - monomorph dropped upstream's ``-static`` because a static link put
  1393 glibc and zlib bodies under monomorph's name, and VX-API's static CRT
  put 1947 Microsoft functions into one family. ``subtract`` may not be empty.

What this module deliberately does not do is acquire anything. The binary is a
local file the maintainer already holds, verified against the digest stated in
the recipe. Reaching out to a malware repository is a credentialed, audited
act and a build script is the wrong place for it.
"""

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

from .recipe import Artifact


# The producer segment written into every sample-derived filename. validate's
# _producer() reads this back out of a path, which is how the deep check tells
# the two tracks apart without opening provenance.
PRODUCER = "sample"

# Recorded in provenance.json. Absent on every build-derived entry, so a reader
# - human or script - can select one track without parsing filenames.
DERIVED_FROM = "sample"

_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")
_URL = re.compile(r"\Ahttps?://\S+\Z")


@dataclass
class SampleSource:
    """A binary the maintainer supplies, and the evidence for calling it this.

    ``sha256`` is the identity: there is no commit and no release, so the
    digest is the only thing that pins what was analysed. The file is verified
    against it before anything is disassembled.
    """

    sha256: str
    # Where the maintainer got it - "MalwareBazaar", "VirusTotal", an incident.
    # Free text, because the useful answer varies and a closed vocabulary would
    # only invite a wrong one to be picked.
    acquired_from: str
    # ISO date, for the same reason a build records `generated`.
    acquired: str
    # Why this binary is believed to be this family, in a sentence that says
    # what the belief rests on.
    attribution: str
    # Published analysis supporting it. A URL, so a reader can check rather
    # than take the recipe's word.
    attribution_source: str
    # Optional: what the file is called where it was acquired, purely to help
    # a maintainer find it again. Never used for identity.
    filename: Optional[str] = None

    def __post_init__(self):
        if not _SHA256.match(self.sha256 or ""):
            raise ValueError(
                "sha256 must be 64 lowercase hex digits, got %r. It is the "
                "only identity a sample has; a truncated or upper-case digest "
                "silently fails the verification it exists for."
                % (self.sha256,))
        for name in ("acquired_from", "acquired", "attribution"):
            if not (getattr(self, name) or "").strip():
                raise ValueError(
                    "%s is required on a SampleSource. Sample-derived data "
                    "asserts something about a binary nobody here compiled, "
                    "and an assertion with no provenance is the failure mode "
                    "this track exists to avoid." % (name,))
        if not _URL.match(self.attribution_source or ""):
            raise ValueError(
                "attribution_source must be a URL, got %r. The family name on "
                "sample-derived data is a claim; it is admitted because "
                "somebody published the analysis behind it, and the record has "
                "to point at that analysis rather than restate it."
                % (self.attribution_source,))

    def verify(self, path):
        """Check a local file against the recorded digest.

        Raises rather than returning a flag: a mismatch means the artefact
        being ingested is not the artefact the provenance describes, and there
        is nothing sensible to do with it.
        """
        import hashlib

        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        actual = digest.hexdigest()
        if actual != self.sha256:
            raise ValueError(
                "%s hashes to %s but the recipe pins %s. Either the wrong file "
                "was supplied or the recipe is stale; both are worth stopping "
                "for, because everything downstream is filed under a family "
                "name this digest is the only evidence for."
                % (path, actual, self.sha256))
        return actual


@dataclass
class SampleRecipe:
    """A family whose code can only be reached through a shipped binary."""

    family: str
    # There is no release to name. A campaign, a first-seen date or a vendor's
    # version designation - whatever the attribution_source calls it.
    version: str
    sample: SampleSource
    artifacts: List[Artifact]
    # Corpus families whose bodies must be subtracted before anything is
    # admitted. Not a hint: residue.py fails a run whose matched share is
    # implausibly low, because an ingest that cannot account for most of an
    # image has not established what the rest of it is.
    subtract: List[str] = field(default_factory=list)
    upstream: str = ""
    license: str = ""
    notes: str = ""
    # Same meaning as on Recipe, and the same rule: the count the project
    # genuinely has, never a number chosen to make a thin result pass.
    min_functions: Optional[int] = None
    # Deliberately absent, and absent on purpose rather than by oversight:
    # source, build, toolchains, requires, build_flags, drop_crt_glue. Nothing
    # here compiles, and the glue filter needs a known toolchain to subtract
    # against - which is what `subtract` replaces.

    def __post_init__(self):
        if not self.subtract:
            raise ValueError(
                "%s: subtract may not be empty. A shipped binary is mostly not "
                "the project - runtime, vendored libraries, glue - and with no "
                "toolchain known the corpus itself is the only thing that can "
                "tell which bodies those are. Name the families to subtract, "
                "at minimum the runtime the image was built against."
                % (self.family,))
        if not self.artifacts:
            raise ValueError("%s: no artifacts" % (self.family,))

    def slug(self, artifact, arch):
        """Corpus filename stem, with ``sample`` in the producer slot.

        Mirrors ``Recipe.slug`` including its hostile-character check, because
        the stem becomes a filename and then a URL in a README table.
        """
        family = artifact.family or self.family
        component = artifact.component or os.path.basename(artifact.path)
        parts = [family, self.version, PRODUCER, arch, component]
        slug = "_".join(p for p in parts if p)
        hostile = set(slug) & set(' ()[]<>"\'`|#?%')
        if hostile:
            raise ValueError(
                "%r is not usable as a filename or a URL: remove %s from the "
                "family, version or component" % (slug, "".join(sorted(hostile))))
        return slug

    def provenance(self, artifact, arch, report, paths):
        """The provenance entry for one ingested artefact.

        Shaped like the build-derived entry ``pipeline.run_recipe`` writes, so
        one reader handles both, minus every field that would have to be
        invented: no compiler, no toolchain, no build_flags, no source. Their
        absence is the record - a placeholder would read as knowledge.
        """
        entry = {
            "derived_from": DERIVED_FROM,
            "family": artifact.family or self.family,
            "version": self.version,
            "component": artifact.component,
            "architecture": arch,
            "is_blob": artifact.is_blob,
            "sha256": self.sample.sha256,
            "acquired_from": self.sample.acquired_from,
            "acquired": self.sample.acquired,
            "attribution": self.sample.attribution,
            "attribution_source": self.sample.attribution_source,
            "subtracted": sorted(self.subtract),
            "num_functions": report.num_functions,
            "smda_version": report.smda_version,
            "upstream": self.upstream,
            "license": self.license,
        }
        if self.sample.filename:
            entry["original_filename"] = self.sample.filename
        if self.notes:
            entry["notes"] = self.notes
        entry.update(paths)
        return entry
