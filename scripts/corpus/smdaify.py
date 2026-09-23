"""Turn built binaries into SMDA reports carrying corpus provenance.

This replaces the lib2smda/IDA Pro stage of the README pipeline for inputs
that are PE or ELF images. MinGW writes a COFF symbol table into unstripped
output and GCC-on-Linux an ELF one, both of which SMDA reads, so the
resulting reports carry function symbols of a quality comparable to the
IDA-with-symbols path; static .LIB/.A archives still need IDA and remain out
of reach here.
"""

import logging
import os

from . import config
from .baseline import is_glue


LOGGER = logging.getLogger(__name__)


class DisassemblyError(RuntimeError):
    pass


def disassemble(path, pdb_path=""):
    from smda.Disassembler import Disassembler
    from smda.SmdaConfig import SmdaConfig

    smda_config = SmdaConfig()
    smda_config.CALCULATE_SCC = True
    smda_config.CALCULATE_NESTING = True
    smda_config.TIMEOUT = config.DISASSEMBLY_TIMEOUT
    return Disassembler(smda_config).disassembleFile(path, pdb_path=pdb_path)


def disassemble_blob(path, bitness, base_addr):
    """Disassemble position-independent code that has no container header.

    Shellcode carries no PE/ELF header to read the architecture and bitness
    from, so both have to be supplied. This is the same route the aPLib
    reports in this repository came through, and their metadata records it
    with ``is_buffer: true``.
    """
    from smda.Disassembler import Disassembler
    from smda.SmdaConfig import SmdaConfig

    with open(path, "rb") as handle:
        content = handle.read()
    smda_config = SmdaConfig()
    smda_config.CALCULATE_SCC = True
    smda_config.CALCULATE_NESTING = True
    smda_config.TIMEOUT = config.DISASSEMBLY_TIMEOUT
    # oep=0 tells SMDA the blob is entered at its first byte, which is how
    # shellcode is invoked. Without it the recursive pass starts elsewhere and
    # recovers a fraction of the code (79 of ~750 instructions on sRDI x64).
    return Disassembler(smda_config).disassembleBuffer(
        content, base_addr, bitness=bitness, architecture="intel", oep=0)


def _call_offsets(function):
    """Offsets of the call instructions in ``function``.

    SMDA decides both "leaf" and "recursive" from call instructions
    specifically, not from control-flow references in general, so anything
    recomputing those counts has to find the calls again. CALL_INS comes from
    SMDA itself so the two cannot drift apart; the mnemonic's last token is
    what is matched, because a prefix such as ``bnd`` is written in front.
    """
    from smda.intel.definitions import CALL_INS

    return {instruction.offset
            for block in function.blocks.values()
            for instruction in block
            if (instruction.mnemonic or "").split(" ")[-1] in CALL_INS}


def _recompute_statistics(report):
    """Recompute the statistics block over the functions the report still has.

    The counts end up in the .mcrit sample entry, so leaving them describing a
    function set that is no longer in the report would ship metadata that does
    not match its own data.

    Every field is derived the way SMDA derives it, which matters more than it
    looks: a report this tooling rewrites sits in the same corpus as reports
    SMDA wrote itself, and a field that means one thing in some samples and
    another in the rest is worse than no field at all. In particular a leaf is
    a function containing no call instruction - not one with no outgoing
    references, which would misclassify every function whose only calls go to
    imports, and every tail-call - and a function is recursive when a *call*
    targets its own entry, not when any reference does.
    """
    from smda.DisassemblyStatistics import DisassemblyStatistics

    functions = list(report.getFunctions())
    statistics = DisassemblyStatistics()
    statistics.num_functions = len(functions)
    statistics.num_basic_blocks = sum(f.num_blocks for f in functions)
    statistics.num_instructions = sum(f.num_instructions for f in functions)
    statistics.num_api_calls = sum(len(f.apirefs) for f in functions)
    # SMDA counts every reference to a function start, without regard to where
    # it came from. Filtering to surviving callers would be defensible on its
    # own terms but would stop this field meaning the same thing it means in
    # every report already in the corpus, so SMDA's definition is kept.
    statistics.num_function_calls = sum(len(f.inrefs) for f in functions)
    calls = {f.offset: _call_offsets(f) for f in functions}
    statistics.num_recursive_functions = len(
        [f for f in functions
         if any(f.offset in f.outrefs.get(offset, ())
                for offset in calls[f.offset])]
    )
    statistics.num_leaf_functions = len([f for f in functions
                                         if not calls[f.offset]])
    statistics.num_thunk_functions = len([f for f in functions if f.isApiThunk()])
    # Failures are properties of the disassembly pass itself; the pass ran over
    # the whole binary regardless of what was retained afterwards.
    previous = report.statistics
    statistics.num_failed_functions = previous.num_failed_functions if previous else 0
    statistics.num_failed_instructions = previous.num_failed_instructions if previous else 0
    report.statistics = statistics

    # binweight and the cached block/instruction totals are computed once at
    # construction and would otherwise keep describing the pre-removal set;
    # binweight in particular is copied straight into the .mcrit sample entry.
    report.binweight = sum(f.binweight for f in functions)
    report._num_blocks = statistics.num_basic_blocks
    report._num_instructions = statistics.num_instructions


def _drop_crt_glue(report, toolchain_id):
    """Remove compiler runtime functions so they keep the compiler's family.

    A function is glue only when its symbol name and its PicHash both match a
    baseline measured from an otherwise empty DLL built with the same
    toolchain, so a project that provides its own version of a runtime symbol
    keeps it.
    """
    removed = []
    for offset, function in list(report.xcfg.items()):
        if is_glue(function, toolchain_id):
            removed.append(function.function_name)
            del report.xcfg[offset]
    # getFunctions() memoises its sorted list, so it has to be dropped or
    # everything downstream keeps seeing the functions just removed.
    report._sorted_functions = None
    if removed:
        _recompute_statistics(report)
        LOGGER.info("dropped %d compiler runtime functions: %s",
                    len(removed), ", ".join(sorted(removed)))
    return removed


def assert_symbols_survived(report, binary_path, min_named_ratio):
    """Refuse a report whose build stripped its symbols.

    MinGW writes a COFF symbol table unless the build strips it, and those
    symbols are what makes this data comparable to the IDA-with-symbols
    reports already in the corpus. A build system that strips by default
    (zlib's win32/Makefile.gcc does) would otherwise quietly yield anonymous
    reference data, so a symbol-poor report is treated as a build failure.

    Called before runtime glue is dropped: glue is almost entirely named, so
    removing it lowers the ratio without the build having changed. The
    question here is whether this build kept its symbols.

    The ratio is taken over functions of at least
    ``MIN_NAMED_SAMPLE_INSTRUCTIONS`` instructions, for the reason recorded
    at that constant: the one- and two-instruction fragments MSVC emits for
    x86 C++ exception handling carry no symbol in any build, so counting them
    measures how much C++ a project contains rather than whether this build
    was stripped.
    """
    if not min_named_ratio:
        return
    functions = [f for f in report.getFunctions()
                 if f.num_instructions >= config.MIN_NAMED_SAMPLE_INSTRUCTIONS]
    # A report with nothing above the floor is not a report that passes: it
    # is a truncated or stub build, and MIN_USEFUL_FUNCTIONS admits as few as
    # eight functions, so this is reachable. Returning here would have been a
    # division guard that quietly turned the gate off in exactly the case it
    # exists for.
    if not functions:
        raise DisassemblyError(
            "%s: not one of its %d functions reaches %d instructions, so "
            "there is nothing for the symbol check to measure; this is not a "
            "build that produced usable reference data"
            % (binary_path, report.num_functions,
               config.MIN_NAMED_SAMPLE_INSTRUCTIONS))
    named = len([f for f in functions if f.function_name])
    ratio = named / len(functions)
    if ratio >= min_named_ratio:
        return
    # The counts over every function are reported too. Without them a reader
    # cannot tell a stripped build from one where the floor was set wrong,
    # and that is the one distinction this message has to support.
    #
    # The remedy differs by toolchain and the message says all three: MinGW
    # and GCC-on-Linux keep symbols in a COFF or ELF symbol table that a
    # build system can strip, which STRIP=true is about, while MSVC keeps
    # them in a PDB that either exists or does not.
    #
    # An ELF shared object has a third way to fail this that is not a strip
    # at all, and the message names it because it is what actually happened
    # when this corpus gained its first ELF family: every global symbol is
    # exported by default, and an intra-object call to an exported symbol
    # goes through a three-instruction .plt stub that carries no name, so a
    # library whose own functions are all exported is mostly unnamed stubs
    # by count. StringObfuscatorCT's Linux x64 build was refused here at 113
    # of 256, and -fvisibility=hidden - which is what the PE side has had all
    # along, since a DLL with no .def exports only what is marked dllexport -
    # took the same source to 133 of 134.
    raise DisassemblyError(
        "%s: only %d of %d functions of at least %d instructions carry "
        "symbols (%.0f%%); the build most likely stripped them - pass "
        "STRIP=true to a MinGW or GCC build system, or check that an MSVC "
        "build compiled /Zi or /Z7 and that the link wrote the PDB this "
        "report was read with. For an ELF shared object, check "
        "-fvisibility=hidden as well: without it every intra-object call "
        "runs through an unnamed .plt stub. Over every function it is %d "
        "of %d."
        % (binary_path, named, len(functions),
           config.MIN_NAMED_SAMPLE_INSTRUCTIONS, 100 * ratio,
           len([f for f in report.getFunctions() if f.function_name]),
           report.num_functions))


def assert_not_incrementally_linked(report, binary_path):
    """Refuse a PE that was linked with /INCREMENTAL.

    ``link /DEBUG`` implies ``/INCREMENTAL`` and the ``/OPT:NO*`` forms these
    recipes pass do not suppress it - only ``/OPT:REF``, ``/OPT:ICF`` and
    ``/OPT:ORDER`` are documented to. An incrementally linked image reaches
    each function through a table of one-instruction jump thunks, every one
    of which SMDA recovers as a function in its own right. Seven recipes had
    this, and at the worst of them roughly half of what the corpus was
    calling a function was a thunk.

    It is worth a check of its own rather than trusting the recipes, for a
    reason the review of those recipes made plain: the symbol-coverage ratio
    above was the only thing in the pipeline that noticed, it noticed by
    accident, and the instruction floor it now uses would hide this entirely.
    bzip2 and libtomcrypt had been sitting within one percentage point of
    failing that gate for this reason and nobody had looked.

    The signature is what was measured on the artefacts the omission
    produced: a long unbroken run of unnamed single-instruction direct
    jumps, each exactly five bytes after the last, because that is what a
    table of ``E9 rel32`` is. In nlohmann_json 3.12.0 x64 the run is 2866
    entries from base+0x1005 with no other function inside its span.

    The run, not the count, is what separates it. Plenty of artefacts carry
    unnamed direct-jump functions without having a table - 7-Zip's MinGW x86
    reports carry 265 - but scattered through the image rather than packed.
    Over all 392 generated reports the longest such run outside an
    incrementally linked image is 18 and the shortest inside one is 70; see
    ``MAX_INCREMENTAL_THUNK_RUN`` for the full split.

    Kept unconditional now that the corpus has ELF artefacts as well, rather
    than narrowed to a PE: there is no /INCREMENTAL on ld, so it can only
    ever pass there, and a check that costs nothing is not worth making
    conditional on a format. It was measured rather than assumed - an ELF
    .plt entry is at a 16-byte stride, not five, and reaches its target
    through the GOT, so it is written "jmp qword ptr [...]" and
    _is_direct_target rejects it; the eight ELF artefacts in this corpus
    carry no unnamed direct-jump function at all, so their longest run is 0.
    """
    thunks = []
    for function in report.getFunctions():
        if function.num_instructions != 1 or function.function_name:
            continue
        instruction = next(iter(function.getInstructions()))
        # A direct jump. An import thunk jumps through memory and is written
        # "dword ptr [...]"; those are ordinary and are not what this is for.
        if instruction.mnemonic != "jmp" or not _is_direct_target(instruction):
            continue
        thunks.append(function.offset)

    run = longest = 1 if thunks else 0
    thunks.sort()
    for previous, offset in zip(thunks, thunks[1:]):
        run = run + 1 if offset - previous == _ILT_ENTRY_SIZE else 1
        longest = max(longest, run)
    if longest < config.MAX_INCREMENTAL_THUNK_RUN:
        return
    raise DisassemblyError(
        "%s: %d unnamed one-instruction jumps, %d of them consecutive at a "
        "%d-byte stride, which is an incremental link table. The link needs "
        "/INCREMENTAL:NO - /DEBUG implies /INCREMENTAL and /OPT:NOREF and "
        "/OPT:NOICF do not suppress it. Every function in this image is "
        "reached through that table, so its call graph and function count "
        "describe the table rather than the library."
        % (binary_path, len(thunks), longest, _ILT_ENTRY_SIZE))


# E9 rel32, on x86 and x64 alike, which is what an incremental link table is
# made of.
_ILT_ENTRY_SIZE = 5


def _is_direct_target(instruction):
    """True when the operand is an address rather than a memory reference."""
    return "[" not in instruction.operands and "ptr" not in instruction.operands


def smdaify(binary_path, family, version, component, is_library=True,
            toolchain_id=None, drop_crt_glue=True, filename=None,
            min_named_ratio=0.5, is_blob=False, bitness=None,
            base_addr=0x400000, pdb_path=""):
    """Disassemble ``binary_path`` and label it the way the corpus expects."""
    if is_blob:
        if bitness not in (32, 64):
            raise DisassemblyError(
                "%s: a raw code blob has no header to read bitness from, so the "
                "recipe must state it" % binary_path)
        report = disassemble_blob(binary_path, bitness, base_addr)
        # Nothing in a stripped shellcode blob carries a symbol, and no
        # compiler runtime was linked in, so neither pass applies.
        min_named_ratio = 0
        drop_crt_glue = False
    else:
        report = disassemble(binary_path, pdb_path=pdb_path)
    if report.status != "ok":
        raise DisassemblyError("SMDA did not finish cleanly for %s: %s"
                               % (binary_path, report.message))

    assert_symbols_survived(report, binary_path, min_named_ratio)
    # Not for a blob: a raw code buffer was never linked at all, so there is
    # no link line to be wrong and no PE for a table to sit at the front of.
    if not is_blob:
        assert_not_incrementally_linked(report, binary_path)

    removed = []
    if drop_crt_glue and toolchain_id:
        removed = _drop_crt_glue(report, toolchain_id)

    if is_blob:
        recovered = report.statistics.num_instructions if report.statistics else 0
        if recovered < config.MIN_USEFUL_BLOB_INSTRUCTIONS:
            raise DisassemblyError(
                "%s yielded only %d instructions, which is too little to be "
                "useful reference data" % (binary_path, recovered))
    elif report.num_functions < config.MIN_USEFUL_FUNCTIONS:
        raise DisassemblyError(
            "%s yielded only %d functions, which is too little to be useful reference data"
            % (binary_path, report.num_functions))

    report.family = family
    report.version = version
    report.component = component or ""
    report.is_library = is_library
    report.filename = filename or os.path.basename(binary_path)
    if is_blob:
        # Records how the report was produced, matching the aPLib entries.
        report.is_buffer = True
    return report, removed
