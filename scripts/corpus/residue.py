"""Subtract what the corpus already knows, and admit only what is left.

For a build, ``baseline.py`` knows which bodies are the compiler's because it
knows the compiler. For a shipped binary nobody here compiled, that is not
available - and a malware image is mostly not the malware: statically linked
runtime, vendored libraries, glue. Admitting it wholesale would file all of
that under one family name, which is the misattribution this corpus exists to
prevent and which it has already refused data over twice (monomorph's
``-static``, VX-API's static CRT).

So the subtraction runs the other way round. The corpus now holds ~60 library
families plus ``data/MSVC``, ``data/MinGW``, ``data/Rust``, ``data/Golang``
and ``data/libstdc++``, and every one of them is build-verified. Match the
candidate against those first: a body whose PicHash is already filed under a
known family is, by construction, not this family's. What survives is the
candidate's own code.

This is stronger here than it would be in a fresh tool, and it is the reason
sample-derived data is worth attempting at all. It is also not magic, and the
two honest limits are worth stating where they will be read:

* A body that matches nothing is *not* thereby the project's. It may be a
  library this corpus does not carry. The residue is a candidate set for a
  human, not a verdict.
* PicHash equality is exact. It catches the same body compiled the same way
  and misses the same body compiled differently, which is precisely the case a
  statically linked dependency built with other flags presents. So a low
  matched share means "this did not work", not "this image is unusually
  original", and ``ACCOUNTED_FLOOR`` fails the run rather than letting an
  unexplained image through.
"""

import collections
import json
import logging
import os

from . import config


LOGGER = logging.getLogger(__name__)

# The share of an image's functions that must land in a known family before
# the residue is worth anything. An ingest that explains a quarter of what it
# is looking at has not established that the other three quarters are the
# project; it has established that the subtraction set is wrong or the image
# was built with flags the corpus does not carry. Deliberately a hard failure
# and deliberately not in config.py, because it governs this track alone.
ACCOUNTED_FLOOR = 0.5

# Functions below this are not counted on either side of the ratio. A
# one-instruction import thunk matches everything and means nothing; counting
# them would let an image of thunks pass the floor while explaining none of
# its code. Mirrors config.MIN_CROSS_FAMILY_INSTRUCTIONS in intent.
MIN_INSTRUCTIONS = 10


Match = collections.namedtuple("Match", "pichash family name num_instructions")


def _iter_mcrit(families, root=None):
    """Every .mcrit export belonging to one of ``families``."""
    root = root or config.DATA_DIR
    for family in families:
        family_dir = os.path.join(root, family)
        if not os.path.isdir(family_dir):
            raise ValueError(
                "subtract names %r but %s does not exist. The subtraction set "
                "has to be families this corpus actually carries, or the "
                "matched share below is measuring nothing."
                % (family, family_dir))
        for dirpath, _, filenames in os.walk(family_dir):
            for name in sorted(filenames):
                if name.endswith(".mcrit"):
                    yield family, os.path.join(dirpath, name)


def build_index(families, root=None, min_instructions=MIN_INSTRUCTIONS):
    """PicHash -> (family, symbol name) over the named corpus families.

    Reads the same exports ``validate.find_cross_family_functions`` reads, in
    the same way, including the compressed-entry path - so what this subtracts
    is exactly what the deep check would later call a collision.
    """
    index = {}
    decompress_decode = None
    for family, path in _iter_mcrit(families, root):
        with open(path, encoding="utf-8") as handle:
            try:
                export = json.load(handle)
            except ValueError:
                LOGGER.warning("%s is not readable JSON; skipped", path)
                continue
        compressed = export.get("content", {}).get("is_compressed")
        for blob in export.get("function_entries", {}).values():
            if compressed:
                if decompress_decode is None:
                    from mcrit.libs.utility import decompress_decode
                entries = json.loads(decompress_decode(blob))
            else:
                entries = blob
            for entry in entries.values():
                pichash = entry.get("pichash")
                if not pichash:
                    continue
                if (entry.get("num_instructions") or 0) < min_instructions:
                    continue
                # First writer wins, so the reported family is stable across
                # runs rather than depending on directory order. Which family
                # claimed a shared body first does not change the verdict -
                # either way it is not the candidate's.
                index.setdefault(pichash, (family, entry.get("function_name") or ""))
    return index


def partition(report, index, min_instructions=MIN_INSTRUCTIONS):
    """Split a candidate report into what the corpus knows and what is left.

    Returns (matched, residue, ignored):

    * ``matched``  - [Match], bodies already filed under a known family
    * ``residue``  - the candidate's own functions, the only admissible part
    * ``ignored``  - below the instruction floor, counted on neither side
    """
    matched, residue, ignored = [], [], []
    for function in report.getFunctions():
        if (function.num_instructions or 0) < min_instructions:
            ignored.append(function)
            continue
        known = index.get(function.pic_hash)
        if known:
            matched.append(Match(function.pic_hash, known[0], known[1],
                                 function.num_instructions))
        else:
            residue.append(function)
    return matched, residue, ignored


def accounted_share(matched, residue):
    """Share of counted functions the corpus explained. 0.0 when there are none."""
    counted = len(matched) + len(residue)
    return len(matched) / counted if counted else 0.0


def assert_accounted(report, matched, residue, binary_path,
                     floor=ACCOUNTED_FLOOR):
    """Refuse an ingest whose image the corpus could not mostly explain."""
    share = accounted_share(matched, residue)
    if share >= floor:
        return share
    by_family = collections.Counter(m.family for m in matched)
    raise ValueError(
        "%s: only %d of %d functions of at least %d instructions are already "
        "known to the corpus (%.0f%%, floor %.0f%%); %d are not. The "
        "subtraction set did not explain this image, so the remainder cannot "
        "be called this family's code - it is as likely to be a library the "
        "corpus does not carry, or the same libraries compiled with flags it "
        "does not hold. Widen `subtract`, or establish what the unexplained "
        "bodies are before recording any of them. Matched so far: %s"
        % (binary_path, len(matched), len(matched) + len(residue),
           MIN_INSTRUCTIONS, 100 * share, 100 * floor, len(residue),
           ", ".join("%s %d" % pair for pair in by_family.most_common()) or "nothing"))


def summarise(matched, residue, ignored):
    """One block of lines for a log or a recipe's notes, with the counts."""
    by_family = collections.Counter(m.family for m in matched)
    lines = ["%d functions counted (%d below %d instructions, not counted)"
             % (len(matched) + len(residue), len(ignored), MIN_INSTRUCTIONS),
             "%d already in the corpus:" % (len(matched),)]
    lines.extend("    %-24s %d" % (family, count)
                 for family, count in by_family.most_common())
    lines.append("%d unexplained, the candidate set" % (len(residue),))
    return lines
