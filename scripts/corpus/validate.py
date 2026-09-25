"""Post-generation checks on committed artefacts.

Runs standalone (``python scripts/build_corpus.py validate``) so the whole
data directory, including everything that was already in the repository, can
be re-checked after a contribution.
"""

import collections
import json
import os
import re
import subprocess
import tempfile

from . import config


class ValidationError(RuntimeError):
    pass


# What find_cross_family_functions reports per shared PicHash. A namedtuple
# rather than a bare tuple because the third field arrived after callers were
# written, and "which of these is the size" should not be a question.
Collision = collections.namedtuple("Collision",
                                   "families num_instructions names")

# The four kinds of cross-family PicHash, and the only one that fails a run.
# scripts/explain_collisions.py renders the same four; both get them from
# classify_collision below, so the report and the gate cannot drift apart -
# which they had already started to, the report calling a hash standard
# library code while the gate called it a problem.
LEAKAGE = "leakage"
STDLIB = "stdlib"
DIFFERENT_NAMES = "different-names"
UNNAMED = "unnamed"

# libstdc++, libsupc++ and their extensions. A symbol in one of these
# namespaces legitimately carries one name and one body across unrelated
# families: the header is instantiated into every binary that uses it.
_STD_NAMESPACES = ("std::", "__gnu_cxx::", "__cxxabiv1::")
# The same symbols when SMDA could not demangle them. _ZNSt/_ZSt is namespace
# std, _ZNSs/_ZNSb the string abbreviations, and the two lengths spell out
# __gnu_cxx and __cxxabiv1.
_STD_MANGLED = ("ZSt", "ZNSt", "ZNKSt", "ZNSb", "ZNKSb", "ZNSs", "ZNKSs",
                "ZTISt", "ZTVSt", "ZN9__gnu_cxx", "ZNK9__gnu_cxx",
                "ZN10__cxxabiv1", "ZNK10__cxxabiv1", "ZTVN10__cxxabiv1")

_TEMPLATE_ARGUMENTS = re.compile(r"<[^<>]*>")
_CALL_ARGUMENTS = re.compile(r"\([^()]*\)")


def _declaration(name):
    """The qualified name a demangled symbol declares, alone.

    ``void std::vector<int, std::allocator<int>>::_M_realloc_insert<int
    const&>(...)`` declares ``std::vector::_M_realloc_insert``; everything
    else in it is a return type, template arguments or parameters. Those have
    to go before the namespace can be read off, because a project's own
    function reads as standard library code the moment one of its arguments
    is a ``std::string`` - ``google::protobuf::StringAppendF(std::__cxx11::
    basic_string<...>*, char const*, ...)`` is protobuf's code, not
    libstdc++'s, and exempting it would be exempting exactly the kind of
    C++-into-C++ leakage this corpus can actually suffer.
    """
    bare = name
    for pattern in (_TEMPLATE_ARGUMENTS, _CALL_ARGUMENTS):
        while True:
            shorter = pattern.sub("", bare)
            if shorter == bare:
                break
            bare = shorter
    parts = bare.split()
    # What survives is "<return type> <qualified name>", or just the name.
    return parts[-1] if parts else ""


def _is_stdlib_symbol(name):
    """Whether one symbol belongs to the C++ standard library itself."""
    declaration = _declaration(name)
    # The declaration is tried undecorated as well, for the same reason
    # _same_symbol strips underscores: the 32-bit MinGW ABI puts one in front
    # of a symbol the 64-bit ABI leaves bare, and the standard library
    # namespaces are not exempt from that. Raw first, or __gnu_cxx:: and
    # __cxxabiv1:: would lose the underscores that are part of their names.
    if declaration.startswith(_STD_NAMESPACES):
        return True
    if declaration.lstrip("_").startswith(("std::", "gnu_cxx::", "cxxabiv1::")):
        return True
    # Mangled names carry no spaces or arguments to strip.
    return name.lstrip("_").startswith(_STD_MANGLED)


def _same_symbol(names):
    """Whether every family calls this function by the same name.

    Compared with a leading underscore stripped, because the 32-bit MinGW ABI
    decorates cdecl symbols with one and the 64-bit ABI does not - the same
    function is "_floor" in one artefact and "floor" in another, and treating
    those as different names would hide exactly what this looks for.
    """
    return len({name.lstrip("_") for name in names}) == 1


_LAMBDA = re.compile(r"<lambda_[0-9a-f]{32}>")


def _lambda_of(name):
    """The lambda id a bare ``<lambda_HEX>::operator()`` names, else None."""
    match = _LAMBDA.fullmatch(name.split("::")[0])
    return match.group(0) if match and name.endswith("::operator()") else None


# Standard library functions whose lambda argument can only have come from
# standard library source, which is the only thing that makes a host name
# evidence about a lambda at all.
#
# The distinction is not "the host is a std:: name" - that was the first
# version of this rule and it was wrong. MSVC emits an instantiation of
# std::invoke, std::move, std::forward, std::_Pass_fn, std::remove_if,
# std::find_if, std::unique_ptr's deleter and std::function's wrapper for
# *whatever callable it is handed*, so those names say who instantiated the
# lambda, not who wrote it. Keyed on them, this rule marked 707 lambda ids
# standard library across this corpus, 589 of which also carry a project
# host name - among them abseil's own lambda over its own VModuleInfo type,
# hosted by std::remove_if, and six abseil call_once lambdas that
# absl::base_internal::CallOnceImpl names and std::forward launders. That is
# exactly the misattribution the whole deep check exists to report.
#
# What is left is the narrow case that is real evidence: an *internal*
# member that a caller cannot hand a lambda to. _Reallocate_grow_by is a
# private basic_string member, called only from append, insert, replace,
# resize and push_back with lambdas written in <xstring>, so a lambda
# appearing in its name is standard library source by construction.
#
# Add to this list only with the same argument, and only with a measurement:
# a host that any user callable can reach belongs nowhere near it.
_STDLIB_LAMBDA_HOSTS = ("::_Reallocate_grow_by<",)


def stdlib_lambda_ids(names):
    """Lambda ids that some standard library symbol carries in its own name.

    MSVC names an unnamed lambda ``<lambda_HEX>``, where the hex is derived
    from its source, so the same id in two projects means the same source -
    but the id alone says nothing about *whose* source. A lambda out of a
    vendored third-party header would look exactly like one out of
    ``<xstring>``, and the first of those is leakage worth reporting.

    What separates them is already in the corpus. The function that takes the
    lambda carries it inside its own name, so ``<lambda_319d5e08...>`` is
    standard library code because something, somewhere in this data, is
    called::

        std::basic_string<char,...>::_Reallocate_grow_by<<lambda_319d5e08...>,char>

    But only because of *which* ``std::`` function that is, not because it is
    a ``std::`` one - see ``_STDLIB_LAMBDA_HOSTS`` for why keying on the
    namespace alone launders a project's own lambdas wholesale. A lambda
    whose only appearance is the bare ``operator()``, or which only ever
    turns up inside a template any caller could have instantiated, stays
    unexplained and stays a leakage candidate.

    Measured over this corpus: every one of the six lambdas that appears bare
    in three or more families has exactly one such host name, and all six are
    ``std::basic_string::_Reallocate_grow_by`` - the reallocating half of
    ``append``, ``insert``, ``replace``, ``resize`` and ``push_back``.
    """
    hosts = set()
    for name in names:
        if _lambda_of(name) or not _is_stdlib_symbol(name):
            continue
        if not any(host in name for host in _STDLIB_LAMBDA_HOSTS):
            continue
        hosts.update(_LAMBDA.findall(name))
    return hosts


def classify_collision(names, stdlib_lambdas=()):
    """Which kind of cross-family PicHash a set of symbol names describes.

    * Every family calls it the same thing, and it is not standard library
      code: one function wearing several project names, which is what
      misattribution looks like. ``floor``, ``__udivmoddi4`` and
      ``_emu_vscprintf`` were all found exactly this way, and this is the only
      kind that fails a run.
    * Every name is a libstdc++ symbol: expected. The same header is
      instantiated into every binary that uses it, so one body under several
      family names is correct rather than mistaken - and since a set of names
      that are all standard library symbols and all equal is still standard
      library code, this exemption can never launder a project's own symbol.
    * The names differ: not one function under several names but several
      functions that happen to hash alike, which the instruction floor bounds
      rather than removes.
    * No name anywhere: unclassifiable. Reported, never failed on, because
      nothing here can tell a stripped runtime helper from a stripped library
      function.
    """
    if not names:
        return UNNAMED
    if all(_is_stdlib_symbol(name)
           or _lambda_of(name) in stdlib_lambdas for name in names):
        return STDLIB
    if _same_symbol(names):
        return LEAKAGE
    return DIFFERENT_NAMES


def _iter_data_files(suffix, root=None):
    root = root or config.DATA_DIR
    for dirpath, dirnames, filenames in os.walk(root):
        # Scratch directories the in-place writers stage in are named with a
        # leading dot and removed on the way out, but a crash or an OOM kill
        # leaves one behind. Walking into it would find a copy of an export
        # that is also committed a level up, and report the sample as a
        # duplicate of itself - a confusing failure whose cause is not in the
        # message. Pruning dirnames in place is what stops os.walk descending.
        dirnames[:] = [name for name in dirnames if not name.startswith(".")]
        for filename in sorted(filenames):
            if filename.endswith(suffix):
                yield os.path.join(dirpath, filename)


def validate_mcrit_file(path):
    """Check one .mcrit export is well formed and importable."""
    problems = []
    with open(path, encoding="utf-8") as handle:
        try:
            export = json.load(handle)
        except ValueError as error:
            return ["%s: not valid JSON (%s)" % (path, error)]

    for key in ("config", "content", "family_mapping", "sample_entries", "function_entries"):
        if key not in export:
            problems.append("%s: missing top level key %r" % (path, key))
    if problems:
        return problems

    if export["config"].get("minhash") != config.EXPECTED_MINHASH_CONFIG:
        problems.append("%s: minhash config hash does not match the rest of the corpus" % path)
    if export["config"].get("shingler") != config.EXPECTED_SHINGLER_CONFIG:
        problems.append("%s: shingler config hash does not match the rest of the corpus" % path)

    samples = export["sample_entries"]
    functions = export["function_entries"]
    if export["content"]["num_samples"] != len(samples):
        problems.append("%s: content.num_samples=%s but %d sample entries"
                        % (path, export["content"]["num_samples"], len(samples)))
    if set(samples) != set(functions):
        problems.append("%s: sample_entries and function_entries disagree on sha256 keys" % path)

    families = set(export["family_mapping"].values())
    for sha256, sample in samples.items():
        if sample.get("sha256") != sha256:
            problems.append("%s: sample keyed by %s carries sha256 %s"
                            % (path, sha256, sample.get("sha256")))
        if not sample.get("family"):
            problems.append("%s: sample %s has no family" % (path, sha256[:12]))
        elif sample["family"] not in families:
            problems.append("%s: sample family %r is not in family_mapping"
                            % (path, sample["family"]))
        if not sample.get("version"):
            problems.append("%s: sample %s has no version recorded" % (path, sha256[:12]))
        # Every sample in this corpus is reference material. MCRIT keys its
        # library-only views and its library-versus-malware family counts off
        # this flag, so a false here makes a reference sample count as malware.
        if not sample.get("is_library"):
            problems.append("%s: sample %s is not marked is_library" % (path, sha256[:12]))
        if sample.get("statistics", {}).get("num_functions", 0) < 1:
            problems.append("%s: sample %s reports no functions" % (path, sha256[:12]))
    return problems


def validate_smda_archive(path):
    """Check a committed .7z holds a parsable SMDA report with provenance."""
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(["7z", "x", "-y", "-o%s" % tmp, path],
                                capture_output=True)
        if result.returncode != 0:
            return ["%s: 7z extraction failed" % path]
        reports = [os.path.join(dirpath, name)
                   for dirpath, _, names in os.walk(tmp) for name in names]
        if not reports:
            return ["%s: archive is empty" % path]
        for report_path in reports:
            with open(report_path, encoding="utf-8") as handle:
                try:
                    report = json.load(handle)
                except ValueError as error:
                    problems.append("%s: %s is not valid JSON (%s)"
                                    % (path, os.path.basename(report_path), error))
                    continue
            metadata = report.get("metadata", {})
            if not metadata.get("family"):
                problems.append("%s: report has no family" % path)
            if not metadata.get("version"):
                problems.append("%s: report has no version" % path)
            if report.get("status") != "ok":
                problems.append("%s: report status is %r" % (path, report.get("status")))
            if not report.get("xcfg"):
                problems.append("%s: report contains no functions" % path)
    return problems


def find_duplicate_samples(root=None):
    """Report sha256 values that appear in more than one .mcrit file."""
    seen = {}
    duplicates = []
    for path in _iter_data_files(".mcrit", root):
        with open(path, encoding="utf-8") as handle:
            try:
                export = json.load(handle)
            except ValueError:
                continue
        for sha256 in export.get("sample_entries", {}):
            if sha256 in seen:
                duplicates.append((sha256, seen[sha256], path))
            else:
                seen[sha256] = path
    return duplicates


def find_cross_family_functions(root=None, threshold=3, min_instructions=None,
                                stdlib_lambdas=None):
    """Report PicHashes that appear under more than one family name.

    A handful of shared hashes is normal - libraries do vendor each other, and
    tiny thunks collide. A hash under several unrelated families is the
    signature of compiler runtime or a statically linked dependency leaking in
    under the host project's name, which is what the glue filter exists to
    prevent and what commit 0108024 had to fix by hand.

    Functions shorter than ``min_instructions`` are not counted: see
    config.MIN_CROSS_FAMILY_INSTRUCTIONS for why, and for what the floor was
    measured to cost. Pass 0 to count every function, which is useful when
    investigating a specific collision by hand and useless as a gate.

    Returns {pichash: Collision(families, num_instructions, names)}. The size
    is the one thing that tells a reader whether a hit is worth opening; the
    symbol names are what classify_collision needs to tell leakage from the
    two kinds of sharing that are correct.

    ``stdlib_lambdas``, if a set is passed, is filled with the lambda ids
    that some standard library symbol names - see stdlib_lambda_ids. It is an
    out-parameter because that evidence lives in names this function walks
    past anyway, in functions that share no hash with anything; collecting it
    here costs one pass rather than a second one over every export.
    """
    if min_instructions is None:
        min_instructions = config.MIN_CROSS_FAMILY_INSTRUCTIONS
    by_hash = {}
    sizes = {}
    names = {}
    decompress_decode = None
    for path in _iter_data_files(".mcrit", root):
        with open(path, encoding="utf-8") as handle:
            try:
                export = json.load(handle)
            except ValueError:
                continue
        compressed = export.get("content", {}).get("is_compressed")
        for sha256, blob in export.get("function_entries", {}).items():
            # A sample with no family is already reported by validate_mcrit_file;
            # here it only needs a name that sorts, so the report still renders.
            family = export.get("sample_entries", {}).get(sha256, {}).get(
                "family") or "(unknown)"
            if compressed:
                if decompress_decode is None:
                    # Imported here rather than at the top of the function so
                    # this module keeps the property the rest of it has: usable
                    # without the analysis dependencies installed. Every export
                    # this pipeline writes is compressed, so in practice the
                    # import still happens on the first file - but a caller
                    # working over uncompressed exports, which is what the
                    # tests do, no longer needs mcrit to be present.
                    from mcrit.libs.utility import decompress_decode
                entries = json.loads(decompress_decode(blob))
            else:
                entries = blob
            for entry in entries.values():
                # Before the floor and before the hash check, because the
                # name that explains a lambda belongs to a different function
                # than the one sharing the hash - usually a large one that
                # collides with nothing - and would be filtered out by both.
                if stdlib_lambdas is not None and entry.get("function_name"):
                    stdlib_lambdas.update(
                        stdlib_lambda_ids([entry["function_name"]]))
                pichash = entry.get("pichash")
                if not pichash:
                    continue
                instructions = entry.get("num_instructions") or 0
                if instructions < min_instructions:
                    continue
                by_hash.setdefault(pichash, set()).add(family)
                sizes[pichash] = instructions
                if entry.get("function_name"):
                    names.setdefault(pichash, set()).add(entry["function_name"])
    return {h: Collision(sorted(f), sizes[h], sorted(names.get(h) or []))
            for h, f in by_hash.items() if len(f) >= threshold}


def group_cross_family_functions(root=None, min_instructions=None):
    """The cross-family PicHashes, sorted into the four kinds.

    Returns {kind: [(pichash, Collision), ...]}, every kind present even when
    empty, each list ordered by size so the largest - the ones worth opening
    first - come out at the top.
    """
    grouped = {kind: [] for kind in (LEAKAGE, STDLIB, DIFFERENT_NAMES, UNNAMED)}
    stdlib_lambdas = set()
    found = find_cross_family_functions(root, min_instructions=min_instructions,
                                        stdlib_lambdas=stdlib_lambdas)
    for pichash, collision in sorted(
            found.items(), key=lambda item: (-item[1].num_instructions, item[0])):
        grouped[classify_collision(collision.names,
                                   stdlib_lambdas)].append((pichash, collision))
    return grouped


def describe_collisions(grouped, min_instructions=None):
    """The non-failing half of the deep check, as lines for a caller to print."""
    if min_instructions is None:
        min_instructions = config.MIN_CROSS_FAMILY_INSTRUCTIONS
    total = sum(len(rows) for rows in grouped.values())
    return ["%d cross-family PicHash(es) at >= %d instructions: %d leakage, "
            "%d standard library instantiation(s), %d whose symbol names "
            "differ between families, %d carrying no symbol at all"
            % (total, min_instructions, len(grouped[LEAKAGE]),
               len(grouped[STDLIB]), len(grouped[DIFFERENT_NAMES]),
               len(grouped[UNNAMED]))]


def _counterpart(path, from_kind, to_kind, from_suffix, to_suffix):
    """Map data/<fam>/<arch>/smda/<slug>.7z to its .mcrit sibling, or back."""
    directory, filename = os.path.split(path)
    parent, kind = os.path.split(directory)
    if kind != from_kind or not filename.endswith(from_suffix):
        return None
    return os.path.join(parent, to_kind, filename[:-len(from_suffix)] + to_suffix)


def find_unpaired_artifacts(root=None):
    """Report a .7z without its .mcrit, or a .mcrit without its .7z.

    The two are written together and are only useful together: an archive on
    its own is a report nothing can import, an export on its own has no
    disassembly behind it. A half-written pair is what a run that died between
    the two writes leaves behind, and it is otherwise invisible.
    """
    problems = []
    for suffix, args in ((".7z", ("smda", "mcrit", ".7z", ".mcrit")),
                         (".mcrit", ("mcrit", "smda", ".mcrit", ".7z"))):
        for path in _iter_data_files(suffix, root):
            expected = _counterpart(path, *args)
            if expected and not os.path.exists(expected):
                problems.append("%s has no matching %s"
                                % (path, os.path.basename(expected)))
    return problems


def find_stale_provenance(root=None):
    """Report provenance records whose artefacts are not in the tree.

    write_provenance merges new records over the existing file and never
    prunes, so renaming a slug - a version string corrected, a component
    renamed - leaves the old record behind for good, describing a file that
    is no longer there.
    """
    problems = []
    for path in _iter_data_files("provenance.json", root):
        with open(path, encoding="utf-8") as handle:
            try:
                records = json.load(handle)
            except ValueError as error:
                problems.append("%s: not valid JSON (%s)" % (path, error))
                continue
        for slug, entry in sorted(records.items()):
            if not isinstance(entry, dict):
                continue
            for key in ("smda", "mcrit"):
                relative = entry.get(key)
                if relative and not os.path.exists(
                        os.path.join(config.REPO_ROOT, relative)):
                    problems.append("%s: record %s points at %s, which does not exist"
                                    % (path, slug, relative))
    return problems


def find_miscounted_provenance(root=None):
    """Report records whose num_functions disagrees with their own export.

    The count is written once when an artefact is built and then again by
    anything that removes functions from a committed report. corpus.refilter
    writes all three files that describe an artefact - the .7z, the .mcrit and
    this record - and the record goes last, so it is the one that can be left
    behind: an interruption after the data has landed leaves a record claiming
    a count the data no longer has. Re-running does not repair it, because the
    filtered archive no longer contains the glue and the artefact is skipped,
    so without a check the corpus keeps a description that quietly disagrees
    with what it describes.

    The export is read rather than the archive because it is plain JSON - no
    7z, no SMDA - which keeps this cheap enough to run with the rest of
    validate rather than behind --deep.
    """
    problems = []
    for path in _iter_data_files("provenance.json", root):
        with open(path, encoding="utf-8") as handle:
            try:
                records = json.load(handle)
            except ValueError:
                # find_stale_provenance already reports this file.
                continue
        for slug, entry in sorted(records.items()):
            if not isinstance(entry, dict):
                continue
            recorded = entry.get("num_functions")
            relative = entry.get("mcrit")
            if recorded is None or not relative:
                continue
            export_path = os.path.join(config.REPO_ROOT, relative)
            if not os.path.exists(export_path):
                continue  # find_stale_provenance reports this
            with open(export_path, encoding="utf-8") as handle:
                try:
                    export = json.load(handle)
                except ValueError:
                    continue  # validate_mcrit_file reports this
            counts = (export.get("content") or {}).get("num_functions")
            if counts is None or len(export.get("sample_entries") or {}) != 1:
                # The count in content covers every sample in the file, so it
                # only answers for a record when the file holds one sample.
                continue
            if counts != recorded:
                problems.append(
                    "%s: record %s says %d functions, %s holds %d"
                    % (path, slug, recorded, relative, counts))
    return problems


def _recorded_paths(family_dir):
    """Every artefact path data/<family>/provenance.json accounts for.

    None for a family that has no provenance.json: those predate this tooling
    (the IDA-derived families) and record nothing by design.
    """
    path = os.path.join(family_dir, "provenance.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        try:
            records = json.load(handle)
        except ValueError:
            # Reported by find_stale_provenance; an unreadable file cannot say
            # anything about which artefacts are recorded either way.
            return None
    recorded = set()
    for entry in records.values():
        if not isinstance(entry, dict):
            continue
        for key in ("smda", "mcrit"):
            if entry.get(key):
                recorded.add(entry[key])
    return recorded


def _producer(path):
    """The toolchain segment of a corpus filename, or None if it has none.

    Filenames follow recipe.slug(), <family>_<version>_<producer>_<arch>_..,
    and both family and version can contain underscores themselves - so the
    producer is located by the architecture that follows it rather than by
    counting fields from the left.
    """
    parts = os.path.basename(path).split("_")
    for index, part in enumerate(parts):
        if index >= 2 and part in ("x86", "x64"):
            return parts[index - 1]
    return None


def find_unrecorded_artifacts(root=None):
    """Report generated artefacts that no provenance record accounts for.

    find_stale_provenance checks the records against the tree; this checks the
    tree against the records, and nothing else does. An artefact with no
    record of how it was built cannot be retraced to upstream source, which is
    the whole claim this corpus makes about its generated data - and a record
    going missing is silent, where a missing file is not: a workflow that
    scopes its artifact upload wrongly commits both architectures' files while
    collecting only one architecture's records.

    Scoped to artefacts built by a toolchain the same family already records,
    because a family is not necessarily all one thing: data/libzlib holds the
    MSVC-built reports that came with this corpus long before this tooling
    alongside the MinGW ones generated here, and those record no provenance
    and cannot be made to.
    """
    problems = []
    by_family = {}
    paths = sorted(set(_iter_data_files(".7z", root))
                   | set(_iter_data_files(".mcrit", root)))
    for path in paths:
        # data/<family>/<arch>/<kind>/<file>
        family_dir = os.path.dirname(os.path.dirname(os.path.dirname(path)))
        if family_dir not in by_family:
            recorded = _recorded_paths(family_dir)
            by_family[family_dir] = (
                recorded,
                None if recorded is None else {_producer(p) for p in recorded})
        recorded, producers = by_family[family_dir]
        if recorded is None:
            continue
        relative = os.path.relpath(path, config.REPO_ROOT).replace(os.sep, "/")
        if relative in recorded or _producer(relative) not in producers:
            continue
        problems.append("%s is not recorded in %s/provenance.json"
                        % (relative, os.path.basename(family_dir)))
    return problems


_LINK = re.compile(r"\[[^\]]*\]\((data/[^)\s]+)\)")


def find_broken_readme_links():
    """Report README links that point at files which are not in the tree.

    The tables are the only index of this corpus, so a row pointing at a
    filename that no longer exists is silently useless - which is how twelve
    dead links survived in this README. Checking them here means a
    regeneration that renames an artefact cannot be committed without the
    table being brought along.
    """
    readme = os.path.join(config.REPO_ROOT, "README.md")
    if not os.path.exists(readme):
        return []
    with open(readme, encoding="utf-8") as handle:
        text = handle.read()
    missing = []
    for target in sorted(set(_LINK.findall(text))):
        if not os.path.exists(os.path.join(config.REPO_ROOT, target)):
            missing.append(target)
    return missing


def find_undocumented_families():
    """Report families present in data/ that no README link mentions.

    Data nobody can find from the README is data nobody will use.
    """
    readme = os.path.join(config.REPO_ROOT, "README.md")
    if not os.path.exists(readme) or not os.path.isdir(config.DATA_DIR):
        return []
    with open(readme, encoding="utf-8") as handle:
        linked = {target.split("/")[1] for target in _LINK.findall(handle.read())
                  if target.count("/") > 1}
    return sorted(name for name in os.listdir(config.DATA_DIR)
                  if os.path.isdir(os.path.join(config.DATA_DIR, name))
                  and name not in linked)


def is_generated_family(name):
    """Whether data/<name> is a family this tooling generates and can fix.

    A generated family carries a provenance.json saying where every artefact
    in it came from. The families that came with the corpus - data/MSVC,
    data/Golang, data/MinGW, data/Rust, data/nim, data/aPLib - are IDA-derived
    and carry none, by design.

    A name with no directory under data/ counts as generated, so that a tree
    checked from somewhere else - a staged build, a CI workspace - is held to
    the strict standard rather than excused wholesale by data/ not knowing
    what it is.
    """
    family_dir = os.path.join(config.DATA_DIR, name)
    if not os.path.isdir(family_dir):
        return True
    return os.path.exists(os.path.join(family_dir, "provenance.json"))


def _family_of(path):
    """The data/<family> component of a corpus path, or None if it has none."""
    relative = os.path.relpath(os.path.abspath(path),
                               os.path.abspath(config.DATA_DIR))
    first = relative.split(os.sep)[0]
    if first in (os.pardir, os.curdir):
        return None
    return first


def _is_generated_path(path):
    """Whether ``path`` belongs to a family this tooling generates.

    A path that is not under data/ at all counts as generated, so that
    anything unexpected fails the run rather than being quietly excused.
    """
    family = _family_of(path)
    return family is None or is_generated_family(family)


def validate_all(root=None, check_size=True, deep=False, min_instructions=None,
                 strict=False, notes=None):
    """Check everything under ``root`` (default data/).

    ``deep`` adds the cross-family PicHash check. It is opt-in because it
    loads and decompresses every .mcrit in the corpus, which is far too slow
    for the per-family check the Windows workflow runs after each build.
    ``min_instructions`` is passed to it; None takes the default floor.

    Two things are reported without failing the run, and ``notes`` - a list
    the caller passes in - is where they go:

    * Problems in the IDA-derived families, which carry no provenance.json.
      They are real - data/MSVC has reports with no family or version
      recorded, data/Golang four .7z files whose .mcrit never arrived - and
      they are in data this tooling did not generate and cannot regenerate,
      so no contribution here can clear them. Failing on them means the
      command can never pass, which is how it came to be run by hand and
      never by CI, and a check nobody runs catches nothing. They are still
      printed, and ``strict`` puts them back among the problems for whoever
      is actually repairing that data.
    * Cross-family PicHashes that are not leakage: standard library
      instantiations, short bodies whose names differ, and hashes carrying no
      symbol at all. Counting those as failures is what made --deep
      unusable; see classify_collision for what separates them.
    """
    problems = []
    unowned = []
    unowned_families = set()

    def record(message, path=None):
        """File one finding, under the family that owns the file it is about."""
        if strict or path is None or _is_generated_path(path):
            problems.append(message)
        else:
            unowned.append(message)
            unowned_families.add(_family_of(path))

    for path in _iter_data_files(".mcrit", root):
        for problem in validate_mcrit_file(path):
            record(problem, path)
        if check_size and os.path.getsize(path) > config.MAX_COMMITTED_FILE_SIZE:
            record("%s: exceeds the GitHub blob size limit" % path, path)
    for path in _iter_data_files(".7z", root):
        for problem in validate_smda_archive(path):
            record(problem, path)
        if check_size and os.path.getsize(path) > config.MAX_COMMITTED_FILE_SIZE:
            record("%s: exceeds the GitHub blob size limit" % path, path)
    for sha256, first, second in find_duplicate_samples(root):
        # Either copy being in a generated family makes it this tooling's
        # problem, so the one that is gets to decide.
        owner = first if _is_generated_path(first) else second
        record("duplicate sample %s in %s and %s" % (sha256[:12], first, second),
               owner)
    for problem in find_unpaired_artifacts(root):
        # The message is "<path> has no matching <name>", and corpus paths
        # carry no spaces - see recipe.slug, which refuses them.
        record(problem, problem.split(" ", 1)[0])
    # The next three read provenance.json and so only ever speak about
    # families that have one, which are generated by definition.
    problems.extend(find_stale_provenance(root))
    problems.extend(find_miscounted_provenance(root))
    problems.extend(find_unrecorded_artifacts(root))
    if deep:
        grouped = group_cross_family_functions(root,
                                               min_instructions=min_instructions)
        for pichash, collision in grouped[LEAKAGE]:
            message = ("PicHash %s (%d instructions) appears under %d families "
                       "as the same symbol %s: %s"
                       % (pichash, collision.num_instructions,
                          len(collision.families), sorted(collision.names)[0],
                          ", ".join(collision.families)))
            # Leakage among the IDA-derived families alone is somebody else's
            # data; anything touching a generated family is this one's.
            record(message, None if any(is_generated_family(family)
                                        for family in collision.families)
                   else os.path.join(config.DATA_DIR, collision.families[0]))
        if notes is not None:
            notes.extend(describe_collisions(grouped, min_instructions))
    # Only when the whole corpus is being checked: a run scoped to one family
    # cannot say anything about the README as a whole.
    if root is None:
        for target in find_broken_readme_links():
            record("README links %s, which does not exist" % target,
                   os.path.join(config.REPO_ROOT, target))
        for family in find_undocumented_families():
            record("data/%s is not linked from the README" % family,
                   os.path.join(config.DATA_DIR, family))
    if notes is not None and unowned:
        notes.append("%d problem(s) below are in %s, which this tooling does "
                     "not generate and cannot regenerate; --strict fails on "
                     "them too"
                     % (len(unowned),
                        ", ".join("data/%s" % family
                                  for family in sorted(unowned_families))))
        notes.extend(unowned)
    return problems
