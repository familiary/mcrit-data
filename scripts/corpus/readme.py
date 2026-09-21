"""Render README table rows for generated families.

The README lists every artefact in a per-project markdown table. Writing those
rows by hand is how a wrong filename ends up in the table (cf. commit e84966e),
so they are generated from the same provenance records the pipeline writes.

    python scripts/build_corpus.py readme libzlib
"""

import json
import os
import re

from . import config


HEADER = ("| Name     | Version | Compiler | MCRIT | SMDA |\n"
          "|----------|---------|----------|-------|------|")

# A generated table is fenced in the README so it can be rewritten in place.
# The comments do not render. Only tables that come wholly from a
# provenance.json are fenced: libzlib and aPLib carry a Date column this
# tooling has no source for, and stay hand-maintained.
# Neither marker takes the surrounding newline with it. It did, and an empty
# fence - a section added before its data existed - then could not match at
# all: the opening marker had already eaten the newline the closing one was
# looking for, so the match ran on to the *next* fence's close and the
# rewrite swallowed every section in between. Six went missing that way.
FENCE = re.compile(
    r"(?P<open><!-- generated: (?P<family>[A-Za-z0-9_.+-]+) -->)"
    r".*?"
    r"(?P<close><!-- /generated -->)",
    re.DOTALL)


def _link(label, path):
    return "[%s](%s)" % (label, path)


def update_readme(path=None):
    """Rewrite every fenced table in the README from the provenance records.

    Returns the families whose block changed. A fence naming a family with no
    provenance is an error rather than a no-op: it means the data it
    describes has gone, and leaving the stale table in place is exactly the
    failure this is here to prevent.
    """
    path = path or os.path.join(config.REPO_ROOT, "README.md")
    with open(path, encoding="utf-8") as handle:
        original = handle.read()

    changed = []

    def _replace(match):
        family = match.group("family")
        new = "%s\n%s\n%s" % (match.group("open"), render_family(family),
                              match.group("close"))
        if new != match.group(0):
            changed.append(family)
        return new

    updated = FENCE.sub(_replace, original)
    # A rewrite may only ever change what is inside the fences. Checking the
    # headings survive is cheap and catches the class of bug that made this
    # function delete six sections: anything that makes a fence fail to match
    # lets the next match run past it and take real content with it.
    before = original.count("\n### ")
    after = updated.count("\n### ")
    if before != after:
        raise ValueError(
            "rewriting the README would change the number of sections from "
            "%d to %d; refusing to write it" % (before, after))
    if updated != original:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(updated)
    return changed


def render_family(family):
    """Return the markdown table for one family, newest version last."""
    path = os.path.join(config.DATA_DIR, family, "provenance.json")
    if not os.path.exists(path):
        raise FileNotFoundError("no provenance recorded for %s" % family)
    with open(path, encoding="utf-8") as handle:
        entries = json.load(handle)

    # Group the per-architecture artefacts of one build onto a single row.
    grouped = {}
    for entry in entries.values():
        # A blob records no toolchain at all - it was compiled upstream, and
        # the host that ran the extraction is not what produced the code - so
        # the grouping key falls back to the producer its filename names.
        toolchain = entry.get("toolchain") or "msvc"
        key = (entry["version"], toolchain.rsplit("_", 1)[0],
               _component_key(entry["component"]))
        grouped.setdefault(key, {})[entry["architecture"]] = entry

    rows = []
    for key in sorted(grouped, key=lambda k: (_version_key(k[0]), k[1], k[2])):
        version, toolchain, _ = key
        by_arch = grouped[key]
        # Raw shellcode is not a PE, so it must not be labelled as one.
        label = "code" if any(e.get("is_blob") for e in by_arch.values()) else "PE"
        mcrit_links = " / ".join(
            _link("%s %s" % (arch, label), by_arch[arch]["mcrit"])
            for arch in ("x86", "x64") if arch in by_arch)
        smda_links = " / ".join(
            _link("%s %s" % (arch, label), by_arch[arch]["smda"])
            for arch in ("x86", "x64") if arch in by_arch)
        compiler = _compiler_label(next(iter(by_arch.values())))
        rows.append("| %s | %s | %s | %s | %s |" % (family, version, compiler, mcrit_links, smda_links))
    return "\n".join([HEADER] + rows)


def _compiler_label(entry):
    """Human readable compiler column, e.g. "MinGW-w64 GCC 13"."""
    compiler = entry.get("compiler", "")
    if entry.get("is_blob"):
        # The blob was compiled by whoever committed it, not by the toolchain
        # that happened to run the extraction.
        return "MSVC (as committed upstream)"
    if "mingw" in (entry.get("toolchain") or ""):
        version = compiler.split("(GCC)")[-1].strip().split("-")[0] if "(GCC)" in compiler else "?"
        return "MinGW-w64 GCC %s" % version
    # cl.exe announces itself as "Microsoft (R) C/C++ Optimizing Compiler
    # Version 19.44.35228 for x64". Printing that verbatim would be wrong as
    # well as long: one row spans both architectures, and the entry this
    # label is taken from is whichever of the two came first, so the x86
    # links in the row would sit under a column saying "for x64". The
    # architectures are already named in the links themselves.
    #
    # The toolset is named because that is what a reader matching a binary
    # against this data wants, and it is derived rather than hardcoded: cl
    # 19.3x and 19.4x are Visual Studio 2022, i.e. v143. A compiler outside
    # that range - if this ever runs on a newer runner image - falls back to
    # the bare version rather than claiming a toolset nobody checked.
    match = re.search(r"Version (\d+)\.(\d+)", compiler)
    if "Microsoft" in compiler and match:
        major, minor = int(match.group(1)), int(match.group(2))
        toolset = " (Visual Studio 2022, v143)" if (major, minor // 10) == (19, 3) \
            or (major, minor // 10) == (19, 4) else ""
        return "MSVC %d.%d%s" % (major, minor, toolset)
    return compiler or entry.get("toolchain", "")


def _component_key(component):
    """Component name with any architecture suffix removed.

    A blob's component has to name its architecture, because the same source
    file yields a 32- and a 64-bit variant; for table grouping those are two
    halves of one row, not two rows.
    """
    for suffix in ("_x86", "_x64"):
        if component.endswith(suffix):
            return component[:-len(suffix)]
    return component


def _version_key(version):
    parts = []
    for chunk in version.replace("-", ".").split("."):
        parts.append((0, int(chunk)) if chunk.isdigit() else (1, 0))
    return parts
