"""Render README table rows for generated families.

The README lists every artefact in a per-project markdown table. Writing those
rows by hand is how a wrong filename ends up in the table (cf. commit e84966e),
so they are generated from the same provenance records the pipeline writes.

    python scripts/build_corpus.py readme libzlib
"""

import json
import os

from . import config


HEADER = ("| Library  | Version | Compiler | MCRIT | SMDA |\n"
          "| -------- | ------- | -------- | ----- | ---- |")


def _link(label, path):
    return "[%s](%s)" % (label, path)


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
        key = (entry["version"], entry["toolchain"].rsplit("_", 1)[0],
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
    if "mingw" in entry.get("toolchain", ""):
        version = compiler.split("(GCC)")[-1].strip().split("-")[0] if "(GCC)" in compiler else "?"
        return "MinGW-w64 GCC %s" % version
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
